"""
An S3-shaped object store: buckets, keys, versions, delete markers, ETags
==========================================================================

Source: awsdocs:s3 -- the Amazon S3 API reference for PutObject, GetObject,
DeleteObject, ListObjectsV2 (prefix/delimiter), object versioning
(VersioningConfiguration), delete markers and ETag. Restated here in our own
words; this is a model, not the wire protocol.

S3 groups objects into **buckets** and names each object with a **key**. A bucket
is flat -- there are no real directories. The `/` that looks like a path is just a
character in the key, and S3 only *pretends* the hierarchy exists when you pass a
`delimiter` to ListObjects: keys containing the delimiter are folded into a
"common prefix" instead of being listed individually. That is why `photos/2024/`
can appear in a listing as though it were a folder when nothing of the sort was
ever created.

Two features make the model more than a dictionary:

- **Versioning.** With versioning off, a PUT overwrites; the object's version id
  is the literal string ``"null"``. With versioning on, every PUT keeps the old
  bytes and assigns a fresh, opaque version id, and a DELETE does not remove
  anything -- it inserts a **delete marker**, a zero-byte version whose only job
  is to hide the older versions from an ordinary GET. The bytes are still there
  and reachable by version id until the versions themselves are deleted.
- **ETag.** S3's ETag for a simple (non-multipart) PUT is the MD5 of the object's
  bytes, lowercase hex. It is a content hash, so identical bytes in two keys get
  the same tag, and an overwrite with different bytes changes it. (A multipart
  upload gets a different, ETag-of-ETags form; we do not model multipart.)

DESIGN DECISION - strong read-after-write, never eventual consistency
S3 since December 2020 is strongly consistent for every read after a successful
write, and for list operations. The rejected alternative is the historical
"eventually consistent for overwrites and deletes" model, where a GET just after
a PUT could return the old bytes or 404. We choose strong consistency because an
in-process store has no replication delay to hide, and because modeling a stale
window would require a clock and a queue for no lesson: the interesting fact is
that the naive "write behind a queue, read from the committed map" design is
*wrong*, and check step 5 constructs exactly that read. Cost: the model says
nothing about what a real eventually-consistent system looked like, and the
in-process guarantee is free rather than earned.

DESIGN DECISION - a delete marker is a first-class version, not a missing-object bit
When versioning is on, DELETE appends a delete-marker Version (empty bytes,
``is_delete_marker=True``) and returns it, exactly as S3 reports a new version id
on a delete of a versioned object. The alternative -- flip a boolean
``deleted`` on the bucket entry -- loses the ordering of put/delete/put and makes
it impossible to answer "what was the current version on Tuesday?". Keeping the
marker in the same version chain means GET is simply "look at the newest version
and refuse it if it is a marker". Cost: a bucket whose every key ends in a
marker looks empty to LIST but is still non-empty to DELETE-bucket, which is
correct S3 behaviour but surprising the first time (check step 4 builds it).

DESIGN DECISION - version ids come from a store-wide counter, not a clock
Version ids are opaque in S3 and carry no meaning; clients must not parse them.
We generate ``"v" + 16-digit counter`` from a single counter shared by the store,
which makes every check deterministic and reproducible regardless of wall time or
hash seed. The rejected alternative is a timestamp or a content hash: a timestamp
is nondeterministic, and a content hash collides for two identical puts and leaks
the bytes. Cost: the ids are guessable and monotonic, so they reveal the order
and a rough global count of writes. Real S3 does not promise otherwise, so this
is safe here.

DESIGN DECISION - DELETE of a missing key is idempotent
S3's DeleteObject returns success whether or not the key existed (it is
idempotent), and in a versioned bucket it still records a delete marker. We
mirror that: an unversioned delete of an absent key is a no-op that returns
``None``; a versioned delete of an absent key appends a marker. The rejected
alternative -- raise NoSuchKey -- makes retries of a delete unsafe, which is
exactly why S3 chose idempotence. Cost: a caller cannot distinguish "deleted
something" from "deleted nothing" by the return value of an unversioned delete.

DESIGN DECISION - LIST returns only current, visible objects
``list_objects`` walks the newest version of every key and skips delete markers,
so a versioned bucket whose current state is "deleted" lists nothing even though
the bucket still holds the old bytes. Listing *versions* is a separate call
(``list_versions``), mirroring S3's ListObjectVersions. Cost: a caller that wants
to see the retained bytes must ask for versions explicitly, and a full scan of
current objects touches every key (they are sorted first, so it is deterministic
but O(n)).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Errors. Named after the S3 error codes they stand for.
# ---------------------------------------------------------------------------

class NoSuchBucket(Exception):
    """The bucket does not exist (S3: NoSuchBucket)."""


class BucketAlreadyExists(Exception):
    """create_bucket was called on a name already in use (S3: BucketAlreadyExists)."""


class BucketNotEmpty(Exception):
    """delete_bucket was called on a bucket that still holds versions (S3: BucketNotEmpty)."""


class NoSuchKey(Exception):
    """No visible object with that key, or the current version is a delete marker."""


class NoSuchVersion(Exception):
    """A version id was requested that is not in the key's version chain."""


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class Version:
    """One version of one object.

    ``data`` is the raw bytes. ``is_delete_marker`` marks the zero-byte version a
    versioned DELETE appends: it has no data, and getting it as "the current
    object" is a NoSuchKey.
    """

    version_id: str
    data: bytes
    etag: str
    is_delete_marker: bool = False
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Bucket:
    """Buckets are flat: ``objects`` maps a key to its version chain, oldest first."""

    name: str
    versioning: bool = False
    objects: Dict[str, List[Version]] = field(default_factory=dict)


@dataclass
class Listing:
    """The result of a LIST: visible keys and the delimiter-folded common prefixes."""

    keys: List[str] = field(default_factory=list)
    common_prefixes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# The store
# ---------------------------------------------------------------------------

class ObjectStore:
    """An in-process, strongly consistent object store with an S3-shaped API."""

    def __init__(self) -> None:
        self._buckets: Dict[str, Bucket] = {}
        self._version_counter = 0

    # -- internal helpers (provided scaffolding) -----------------------------

    def _require_bucket(self, name: str) -> Bucket:
        bucket = self._buckets.get(name)
        if bucket is None:
            raise NoSuchBucket(name)
        return bucket

    def _next_version_id(self) -> str:
        self._version_counter += 1
        return "v%016d" % self._version_counter

    # -- buckets -------------------------------------------------------------

    def create_bucket(self, name: str) -> Bucket:
        """Create an empty bucket. A duplicate name is an error, not a reset."""
        # TODO: A bucket name is a namespace: reject a duplicate (BucketAlreadyExists), otherwise store a new empty Bucket.
        raise NotImplementedError("ObjectStore.create_bucket")

    def delete_bucket(self, name: str) -> None:
        """Delete an empty bucket; refuse if any version survives (BucketNotEmpty).

        "Empty" means *no stored versions at all*: an object hidden behind a
        delete marker still counts, exactly as S3 counts object versions.
        """
        # TODO: Refuse with BucketNotEmpty if ANY key still has stored versions — a key hidden behind a delete marker counts. Only then remove the bucket.
        raise NotImplementedError("ObjectStore.delete_bucket")

    def put_bucket_versioning(self, name: str, status: str) -> None:
        """Enable or suspend versioning: status is "Enabled" or "Suspended"."""
        # TODO: Set the bucket's versioning flag; accept only "Enabled" or "Suspended" and reject anything else.
        raise NotImplementedError("ObjectStore.put_bucket_versioning")

    # -- objects -------------------------------------------------------------

    def put_object(
        self,
        bucket_name: str,
        key: str,
        data: bytes,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Version:
        """Store ``data`` at ``key``; return the new Version (with its ETag).

        Without versioning the new object replaces the old one. With versioning
        the old version is kept and a fresh version id is assigned.
        """
        # TODO: Require bytes. ETag = md5 of the bytes (hex). With versioning on assign a fresh version id and append to the chain; with it off replace the chain with a single "null" version.
        raise NotImplementedError("ObjectStore.put_object")

    def get_object(
        self, bucket_name: str, key: str, version_id: Optional[str] = None
    ) -> Version:
        """Return the current version, or a named one; a delete marker is NoSuchKey."""
        # TODO: Look up the version chain. Without a version id, the current version is the last; a delete marker makes it NoSuchKey. With one, search the chain and honour the marker.
        raise NotImplementedError("ObjectStore.get_object")

    def delete_object(
        self, bucket_name: str, key: str, version_id: Optional[str] = None
    ) -> Optional[Version]:
        """Delete an object.

        With no version id: a versioned bucket gets a new delete marker (returned);
        an unversioned bucket loses the object (returns the removed Version, or
        ``None`` if it was already absent). With a version id: that specific
        version is removed permanently.
        """
        # TODO: With a version id, remove exactly that version (NoSuchVersion if absent). Without one: versioned -> append a delete marker and return it; unversioned -> remove the object (idempotent if it is missing).
        raise NotImplementedError("ObjectStore.delete_object")

    # -- listing -------------------------------------------------------------

    def list_objects(
        self, bucket_name: str, prefix: str = "", delimiter: Optional[str] = None
    ) -> Listing:
        """List visible objects whose key starts with ``prefix``.

        With a ``delimiter``, any key that contains it after the prefix is
        replaced by the common prefix up to and including that delimiter, and
        returned in ``common_prefixes`` rather than ``keys``.
        """
        # TODO: Walk sorted keys, skip a current delete marker, filter by prefix; with a delimiter, fold any remaining delimiter in the key into a common prefix instead of listing it.
        raise NotImplementedError("ObjectStore.list_objects")

    def list_versions(
        self, bucket_name: str, prefix: str = ""
    ) -> List[Tuple[str, Version]]:
        """Every stored version, delete markers included, as (key, Version) pairs."""
        # TODO: Every (key, Version) pair in sorted key order, delete markers included — this is ListObjectVersions, not ListObjects.
        raise NotImplementedError("ObjectStore.list_versions")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    s = ObjectStore()
    s.create_bucket("media")

    original = s.put_object("media", "photos/cat.jpg", b"cat-bytes")
    s.put_object("media", "photos/dog.jpg", b"dog-bytes")
    s.put_object("media", "photos/2024/party.jpg", b"party-bytes")
    s.put_object("media", "notes.txt", b"notes")
    print("Put and ETag")
    print(f"  photos/cat.jpg      etag={original.etag} (md5 of the {len(original.data)} bytes)")

    print("ListObjectsV2: prefix and delimiter fold the fake folders")
    flat = s.list_objects("media", prefix="photos/", delimiter="/")
    print(f"  prefix=photos/ delimiter=/  keys={flat.keys}")
    print(f"                              common_prefixes={flat.common_prefixes}")

    print("Versioning: every PUT is kept; DELETE hides via a marker")
    s.put_bucket_versioning("media", "Enabled")
    v1 = s.put_object("media", "notes.txt", b"notes-v2")
    v2 = s.put_object("media", "notes.txt", b"notes-v3")
    marker = s.delete_object("media", "notes.txt")
    print(f"  versions of notes.txt before delete: "
          f"{[v.version_id for _, v in s.list_versions('media', 'notes.txt')]}")
    print(f"  delete_object        -> version {marker.version_id} "
          f"is_delete_marker={marker.is_delete_marker}")
    print(f"  current get          -> NoSuchKey (hidden)")
    print(f"  get(version={v1.version_id}) -> {s.get_object('media', 'notes.txt', v1.version_id).data!r}")
    print(f"  get(version={v2.version_id}) -> {s.get_object('media', 'notes.txt', v2.version_id).data!r}")
    print(f"  list_objects keys    -> {s.list_objects('media').keys}")

    print("Deleting a non-empty bucket is refused, not destructive")
    try:
        s.delete_bucket("media")
    except BucketNotEmpty:
        kept = len(s.list_versions("media"))
        print(f"  delete_bucket(media) -> BucketNotEmpty; {kept} versions still stored")


if __name__ == "__main__":
    _demo()
