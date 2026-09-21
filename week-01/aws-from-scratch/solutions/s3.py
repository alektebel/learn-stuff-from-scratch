"""
S3 — object storage. Complete Solution.

DESIGN DECISION — a filesystem, or a flat key-value store?
  S3 looks like it has folders. It does not. `reports/2024/q1.csv` is one
  opaque key that happens to contain slashes; "folders" are an illusion the
  console builds by splitting on a delimiter at list time.
  CHOSEN: a flat dict, with prefix/delimiter emulated in list_objects. Building
  it flat is what makes the consequences obvious — renaming a "folder" is
  O(objects), not O(1), and there is no such thing as an empty one.

DESIGN DECISION — how to model versioning?
  Simplest is a per-key list of versions with a pointer to the current one.
  CHOSEN: that, plus the detail that makes versioning surprising: DELETE does
  not delete. It pushes a DELETE MARKER on top. The data is still billed for,
  still there, and a plain GET now 404s while a versioned GET succeeds. That
  single behaviour explains most "why is my bucket still huge" tickets.
"""

import hashlib
import time
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Tuple


class S3Error(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class Version(NamedTuple):
    version_id: str
    body: Optional[bytes]        # None means this is a delete marker
    etag: str
    size: int
    last_modified: float
    metadata: Dict[str, str]

    @property
    def is_delete_marker(self) -> bool:
        return self.body is None


def compute_etag(body: bytes, parts: Optional[List[bytes]] = None) -> str:
    """S3's ETag is an MD5 — except for multipart uploads.

    A multipart ETag is the MD5 of the concatenated part MD5s, followed by
    "-<part count>". That is why you cannot verify a multipart object by
    md5-ing the file you uploaded: the ETag is not the object's MD5, and the
    part size changes the answer.
    """
    if parts is None:
        return hashlib.md5(body).hexdigest()
    digests = b"".join(hashlib.md5(part).digest() for part in parts)
    return f"{hashlib.md5(digests).hexdigest()}-{len(parts)}"


class Bucket:
    def __init__(self, name: str, versioning: bool = False):
        self.name = name
        self.versioning = versioning
        self.objects: Dict[str, List[Version]] = {}
        self.uploads: Dict[str, Dict[int, bytes]] = {}
        self._counter = 0

    def _next_version(self) -> str:
        self._counter += 1
        return f"v{self._counter:06d}"


class S3:
    """A tiny object store with versioning, prefixes and multipart upload."""

    def __init__(self):
        self.buckets: Dict[str, Bucket] = {}
        self.stats = {"puts": 0, "gets": 0, "deletes": 0, "lists": 0}

    # -- buckets ------------------------------------------------------------

    def create_bucket(self, name: str, versioning: bool = False) -> Bucket:
        if name in self.buckets:
            raise S3Error("BucketAlreadyExists", name)
        self.buckets[name] = Bucket(name, versioning)
        return self.buckets[name]

    def _bucket(self, name: str) -> Bucket:
        if name not in self.buckets:
            raise S3Error("NoSuchBucket", name)
        return self.buckets[name]

    def set_versioning(self, bucket: str, enabled: bool) -> None:
        """Versioning can be suspended but never turned OFF — existing versions
        stay, and stay billable. Modelled here because it is the part that
        surprises people on the invoice."""
        self._bucket(bucket).versioning = enabled

    # -- objects ------------------------------------------------------------

    def put_object(self, bucket: str, key: str, body: bytes,
                   metadata: Optional[Dict[str, str]] = None) -> str:
        b = self._bucket(bucket)
        self.stats["puts"] += 1
        version = Version(b._next_version(), body, compute_etag(body),
                          len(body), time.time(), dict(metadata or {}))
        history = b.objects.setdefault(key, [])
        if b.versioning:
            history.append(version)
        else:
            history[:] = [version]        # unversioned: overwrite in place
        return version.etag

    def get_object(self, bucket: str, key: str,
                   version_id: Optional[str] = None) -> Version:
        b = self._bucket(bucket)
        self.stats["gets"] += 1
        history = b.objects.get(key)
        if not history:
            raise S3Error("NoSuchKey", key)

        if version_id is not None:
            for version in history:
                if version.version_id == version_id:
                    return version
            raise S3Error("NoSuchVersion", version_id)

        latest = history[-1]
        if latest.is_delete_marker:
            # The bytes are still there, under the marker. A plain GET cannot
            # see them; a versioned GET can.
            raise S3Error("NoSuchKey", f"{key} (a delete marker is on top)")
        return latest

    def delete_object(self, bucket: str, key: str,
                      version_id: Optional[str] = None) -> Optional[str]:
        """Unversioned: really deletes. Versioned: pushes a delete marker.

        Deleting a specific version_id in a versioned bucket is the only way to
        actually remove bytes — which is why "empty the bucket" scripts that
        only issue plain DELETEs leave the storage bill untouched.
        """
        b = self._bucket(bucket)
        self.stats["deletes"] += 1
        history = b.objects.get(key)
        if not history:
            raise S3Error("NoSuchKey", key)

        if version_id is not None:
            b.objects[key] = [v for v in history if v.version_id != version_id]
            if not b.objects[key]:
                del b.objects[key]
            return None

        if not b.versioning:
            del b.objects[key]
            return None

        marker = Version(b._next_version(), None, "", 0, time.time(), {})
        history.append(marker)
        return marker.version_id

    def list_object_versions(self, bucket: str, key: str) -> List[Version]:
        return list(self._bucket(bucket).objects.get(key, []))

    # -- listing ------------------------------------------------------------

    def list_objects(self, bucket: str, prefix: str = "", delimiter: str = "",
                     max_keys: int = 1000,
                     continuation_token: Optional[str] = None
                     ) -> Dict[str, Any]:
        """Prefix and delimiter listing, with pagination.

        The delimiter is what invents folders: keys sharing a prefix up to the
        next delimiter are collapsed into one "common prefix". No directory
        exists anywhere — which is why you cannot have an empty one, and why
        listing a huge "folder" costs the same as listing the bucket.
        """
        b = self._bucket(bucket)
        self.stats["lists"] += 1

        live = sorted(key for key, history in b.objects.items()
                      if history and not history[-1].is_delete_marker
                      and key.startswith(prefix))
        if continuation_token:
            live = [k for k in live if k > continuation_token]

        keys: List[str] = []
        common: List[str] = []
        for key in live:
            if delimiter:
                rest = key[len(prefix):]
                if delimiter in rest:
                    folder = prefix + rest.split(delimiter)[0] + delimiter
                    if folder not in common:
                        common.append(folder)
                    continue
            keys.append(key)
            if len(keys) + len(common) >= max_keys:
                break

        truncated = (len(keys) + len(common)) >= max_keys and \
            len(live) > len(keys) + len(common)
        return {"keys": keys, "common_prefixes": common,
                "is_truncated": truncated,
                "next_continuation_token": keys[-1] if truncated and keys else None}

    # -- multipart ----------------------------------------------------------

    def create_multipart_upload(self, bucket: str, key: str) -> str:
        b = self._bucket(bucket)
        upload_id = f"upload-{len(b.uploads) + 1}"
        b.uploads[upload_id] = {}
        return upload_id

    def upload_part(self, bucket: str, upload_id: str, part_number: int,
                    body: bytes) -> str:
        b = self._bucket(bucket)
        if upload_id not in b.uploads:
            raise S3Error("NoSuchUpload", upload_id)
        b.uploads[upload_id][part_number] = body
        return compute_etag(body)

    def complete_multipart_upload(self, bucket: str, key: str,
                                  upload_id: str) -> str:
        b = self._bucket(bucket)
        if upload_id not in b.uploads:
            raise S3Error("NoSuchUpload", upload_id)
        parts = [b.uploads[upload_id][n] for n in sorted(b.uploads[upload_id])]
        body = b"".join(parts)
        del b.uploads[upload_id]

        version = Version(b._next_version(), body, compute_etag(body, parts),
                          len(body), time.time(), {})
        history = b.objects.setdefault(key, [])
        if b.versioning:
            history.append(version)
        else:
            history[:] = [version]
        return version.etag

    def abandoned_uploads(self, bucket: str) -> Dict[str, int]:
        """Incomplete uploads still occupy storage and are still billed.

        Nothing lists them by default, which is why a lifecycle rule to abort
        them is close to mandatory on any bucket that takes large uploads.
        """
        b = self._bucket(bucket)
        return {upload_id: sum(len(p) for p in parts.values())
                for upload_id, parts in b.uploads.items()}


def _demo() -> None:
    s3 = S3()
    s3.create_bucket("reports")

    print("=== It is flat. Folders are a listing trick. ===")
    for key in ["2024/q1.csv", "2024/q2.csv", "2025/q1.csv", "README.md"]:
        s3.put_object("reports", key, f"data for {key}".encode())
    listing = s3.list_objects("reports")
    print(f"  no delimiter:  keys={listing['keys']}")
    listing = s3.list_objects("reports", delimiter="/")
    print(f"  delimiter '/': keys={listing['keys']} "
          f"folders={listing['common_prefixes']}")
    listing = s3.list_objects("reports", prefix="2024/", delimiter="/")
    print(f"  prefix 2024/:  keys={listing['keys']}")
    print("  There is no directory object anywhere — which is why an empty")
    print("  folder cannot exist and renaming one is O(objects), not O(1).")

    print("\n=== ETags: not always the MD5 you expect ===")
    body = b"x" * 300
    simple = s3.put_object("reports", "simple.bin", body)
    upload = s3.create_multipart_upload("reports", "multi.bin")
    for number, start in enumerate(range(0, 300, 100), start=1):
        s3.upload_part("reports", upload, number, body[start:start + 100])
    multi = s3.complete_multipart_upload("reports", "multi.bin", upload)
    print(f"  same 300 bytes, single PUT: {simple}")
    print(f"  same 300 bytes, 3 parts:    {multi}")
    print(f"  identical content: {s3.get_object('reports', 'simple.bin').body == s3.get_object('reports', 'multi.bin').body}")
    print("  A multipart ETag is the MD5 of the part MD5s plus '-<count>'. You")
    print("  cannot verify a multipart object by md5-ing your local file.")

    print("\n=== Versioning: DELETE does not delete ===")
    s3.create_bucket("archive", versioning=True)
    s3.put_object("archive", "doc.txt", b"version one")
    s3.put_object("archive", "doc.txt", b"version two")
    print(f"  get -> {s3.get_object('archive', 'doc.txt').body!r}")

    marker = s3.delete_object("archive", "doc.txt")
    print(f"  delete -> pushed marker {marker}")
    try:
        s3.get_object("archive", "doc.txt")
    except S3Error as exc:
        print(f"  get   -> {exc}")

    versions = s3.list_object_versions("archive", "doc.txt")
    print(f"  versions still stored: {len(versions)} "
          f"({sum(v.size for v in versions)} bytes, all billable)")
    first = versions[0]
    print(f"  versioned get -> {s3.get_object('archive', 'doc.txt', first.version_id).body!r}")
    print("  This is why 'I emptied the bucket' and 'the bill went down' are")
    print("  different claims. Only deleting a version_id removes bytes.")

    print("\n=== Incomplete uploads are invisible and billable ===")
    forgotten = s3.create_multipart_upload("reports", "big.bin")
    s3.upload_part("reports", forgotten, 1, b"y" * 5_000)
    print(f"  list_objects sees: {len(s3.list_objects('reports')['keys'])} keys")
    print(f"  abandoned uploads: {s3.abandoned_uploads('reports')}")
    print("  Nothing lists these by default. A lifecycle rule to abort them is")
    print("  close to mandatory on any bucket that takes large uploads.")


if __name__ == "__main__":
    _demo()
