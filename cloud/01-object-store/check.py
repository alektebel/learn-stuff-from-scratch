"""
Progress checker for the object-store templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The steps map one-to-one onto the module's accept criteria and limit cases:
  1  CRUD and list honour prefix and delimiter           (accept)
  2  versioning keeps every version; a delete marker hides it (accept)
  3  the ETag is a hash of the content and changes with it    (accept)
  4  deleting a non-empty bucket is refused, not destructive   (limit case)
  5  read-after-write of a just-put key is visible             (limit case)
  6  a presigned-style capability token is signed and expires  (build item)
"""

import os
import pathlib
import shutil
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def tmpdir() -> str:
    return tempfile.mkdtemp(prefix="objstore-check-")


# ---------------------------------------------------------------------------
# Step 1: buckets, keys, CRUD, prefix and delimiter listing
# ---------------------------------------------------------------------------

def check_crud_and_listing() -> None:
    from store import (
        BucketAlreadyExists,
        NoSuchBucket,
        NoSuchKey,
        ObjectStore,
    )

    s = ObjectStore()
    s.create_bucket("media")
    try:
        s.create_bucket("media")
        raise AssertionError("create_bucket accepted a duplicate name: a bucket name is a namespace, "
                             "creating it twice must not silently reset its contents")
    except BucketAlreadyExists:
        pass

    s.put_object("media", "photos/a.txt", b"a")
    s.put_object("media", "photos/b.txt", b"b")
    s.put_object("media", "photos/2024/c.txt", b"c")
    s.put_object("media", "notes.txt", b"n")

    assert s.get_object("media", "photos/a.txt").data == b"a", "get did not return what put stored"
    try:
        s.get_object("missing", "photos/a.txt")
        raise AssertionError("get on a bucket that does not exist succeeded")
    except NoSuchBucket:
        pass

    # overwrite replaces, and the new bytes are what a GET sees
    s.put_object("media", "photos/a.txt", b"A")
    assert s.get_object("media", "photos/a.txt").data == b"A", "put on an existing key must overwrite"

    # delete removes
    s.delete_object("media", "notes.txt")
    try:
        s.get_object("media", "notes.txt")
        raise AssertionError("delete left a readable object behind")
    except NoSuchKey:
        pass

    assert s.list_objects("media").keys == [
        "photos/2024/c.txt", "photos/a.txt", "photos/b.txt",
    ], ("list_objects must return visible keys in sorted order; a dict-iteration order "
        "is not sorted and not deterministic")

    got = s.list_objects("media", prefix="photos/")
    assert got.keys == ["photos/2024/c.txt", "photos/a.txt", "photos/b.txt"], (
        f"prefix=photos/ returned {got.keys}; notes.txt should have been excluded")

    got = s.list_objects("media", prefix="photos/", delimiter="/")
    assert got.keys == ["photos/a.txt", "photos/b.txt"], (
        f"delimiter=/ should have folded photos/2024/ into a common prefix, got keys {got.keys}")
    assert got.common_prefixes == ["photos/2024/"], (
        f"delimiter=/ should return common_prefixes=['photos/2024/'], got {got.common_prefixes}")

    got = s.list_objects("media", delimiter="/")
    assert got.keys == [] and got.common_prefixes == ["photos/"], (
        f"a root listing with delimiter=/ is all common prefixes; got keys={got.keys}, "
        f"prefixes={got.common_prefixes}")


# ---------------------------------------------------------------------------
# Step 2: versioning and delete markers
# ---------------------------------------------------------------------------

def check_versioning_and_delete_markers() -> None:
    from store import NoSuchKey, ObjectStore

    s = ObjectStore()
    s.create_bucket("v")

    # Without versioning a put overwrites: there is no history to keep.
    s.put_object("v", "k", b"v1")
    s.put_object("v", "k", b"v2")
    assert len(s.list_versions("v")) == 1, (
        "an unversioned bucket kept a version history: without versioning, put overwrites")
    assert s.get_object("v", "k").data == b"v2"

    s.put_bucket_versioning("v", "Enabled")
    v3 = s.put_object("v", "k", b"v3")
    v4 = s.put_object("v", "k", b"v4")
    assert v3.version_id != v4.version_id, "two puts under versioning got the same version id"
    assert s.get_object("v", "k").data == b"v4", "get must return the newest version"
    assert s.get_object("v", "k", version_id=v3.version_id).data == b"v3", (
        "an older version must stay readable by its version id: versioning keeps every version, "
        "not only the latest")
    assert len(s.list_versions("v")) == 3, (
        f"expected 3 versions (the retained unversioned one plus v3 and v4), got {len(s.list_versions('v'))}")

    marker = s.delete_object("v", "k")
    assert marker is not None and marker.is_delete_marker, (
        "a versioned delete must return a delete marker, not None")
    assert marker.version_id != v4.version_id, "the delete marker reused a version id"
    assert marker.etag == "", "a delete marker carries no content, so its etag must be empty"
    assert len(s.list_versions("v")) == 4, "a delete marker is itself a version and must be listed"

    try:
        s.get_object("v", "k")
        raise AssertionError("the delete marker did not hide the current object from get")
    except NoSuchKey:
        pass
    assert s.get_object("v", "k", version_id=v4.version_id).data == b"v4", (
        "the delete marker must not remove the bytes: the named version stays readable")
    assert s.list_objects("v").keys == [], (
        "a delete marker hid the key from get but not from list_objects")

    # A new put after the marker is visible again, and keeps the old chain intact.
    v5 = s.put_object("v", "k", b"v5")
    assert s.get_object("v", "k").data == b"v5", "a put after a delete marker must be the new current object"
    assert len(s.list_versions("v")) == 5

    # Deleting a named version is permanent and reaps it from the chain.
    s.delete_object("v", "k", version_id=v5.version_id)
    assert len(s.list_versions("v")) == 4, (
        "removing a named version must drop exactly that version from the chain")
    try:
        s.get_object("v", "k")
        raise AssertionError("removing the newest version should expose the delete marker again")
    except NoSuchKey:
        pass
    assert s.get_object("v", "k", version_id=v4.version_id).data == b"v4", (
        "removing one named version must not touch the others")


# ---------------------------------------------------------------------------
# Step 3: the ETag is a content hash
# ---------------------------------------------------------------------------

def check_etag_is_content_hash() -> None:
    import hashlib

    from store import ObjectStore

    s = ObjectStore()
    s.create_bucket("e")

    version = s.put_object("e", "k", b"hello world")
    want = hashlib.md5(b"hello world").hexdigest()
    assert version.etag == want, (
        f"the ETag of a simple PUT is the MD5 of the bytes: expected {want}, got {version.etag!r}. "
        "A tag derived from the key, the version id or a counter is not a content hash")
    assert s.get_object("e", "k").etag == want, "get must report the stored ETag"

    changed = s.put_object("e", "k", b"hello world!")
    assert changed.etag != version.etag, "the ETag did not change when the content did"

    same = s.put_object("e", "other-key", b"hello world")
    assert same.etag == want, "identical bytes in a different key must hash to the same ETag"

    assert s.put_object("e", "k2", b"hello world").etag == want, "the ETag must be deterministic"


# ---------------------------------------------------------------------------
# Step 4 (limit case): deleting a non-empty bucket is refused
# ---------------------------------------------------------------------------

def check_nonempty_bucket_refused() -> None:
    from store import BucketNotEmpty, NoSuchBucket, ObjectStore

    s = ObjectStore()
    s.create_bucket("b")
    s.put_object("b", "k", b"v")
    try:
        s.delete_bucket("b")
        raise AssertionError(
            "delete_bucket silently destroyed a non-empty bucket: S3 returns BucketNotEmpty "
            "and the caller must delete the objects first")
    except BucketNotEmpty:
        pass
    assert s.get_object("b", "k").data == b"v", "the object was destroyed even though the delete was refused"

    s.delete_object("b", "k")
    s.delete_bucket("b")  # now genuinely empty
    try:
        s.get_object("b", "k")
        raise AssertionError("delete_bucket left an empty bucket in place")
    except NoSuchBucket:
        pass

    # A versioned bucket whose current key is only a delete marker still holds bytes:
    # S3 counts versions, so it is NOT empty.
    s.create_bucket("v")
    s.put_bucket_versioning("v", "Enabled")
    s.put_object("v", "k", b"v1")
    s.put_object("v", "k", b"v2")
    s.delete_object("v", "k")
    assert s.list_objects("v").keys == [], "precondition: the key is hidden by the delete marker"
    try:
        s.delete_bucket("v")
        raise AssertionError(
            "delete_bucket treated a versioned bucket as empty because its key is hidden by a "
            "delete marker: the older versions are still stored, so the bucket is non-empty")
    except BucketNotEmpty:
        pass


# ---------------------------------------------------------------------------
# Step 5 (limit case): read-after-write
# ---------------------------------------------------------------------------

def check_read_after_write() -> None:
    from store import NoSuchKey, ObjectStore

    s = ObjectStore()
    s.create_bucket("rw")
    for i in range(100):
        key = "k%03d" % i
        body = ("value-%d" % i).encode()
        s.put_object("rw", key, body)
        assert s.get_object("rw", key).data == body, (
            f"read-after-write: get({key!r}) immediately after put returned nothing. "
            "A store that writes behind a queue and reads the committed state is eventually "
            "consistent; this model must be strongly consistent (see the DESIGN DECISION)")

    s.put_object("rw", "k000", b"overwritten")
    assert s.get_object("rw", "k000").data == b"overwritten", (
        "an overwrite was not visible to the next read")

    s.delete_object("rw", "k001")
    assert "k001" not in s.list_objects("rw").keys, "a delete was not visible to the next list"
    try:
        s.get_object("rw", "k001")
        raise AssertionError("a delete was not visible to the next read")
    except NoSuchKey:
        pass

    s.put_bucket_versioning("rw", "Enabled")
    s.put_object("rw", "fresh", b"x")
    assert s.get_object("rw", "fresh").data == b"x", (
        "read-after-write must hold for a versioned put too")


# ---------------------------------------------------------------------------
# Step 6: a presigned-style capability token
# ---------------------------------------------------------------------------

def check_presigned_capability() -> None:
    from presign import ExpiredSignatureError, InvalidSignatureError, presign, verify

    secret = b"a shared signing secret"
    token = presign(secret, "media", "photos/a.txt", method="GET", expires_at=1000, now=900)
    assert verify(secret, token, now=999) == ("media", "photos/a.txt", "GET"), (
        "a valid token did not round-trip its (bucket, key, method) scope")

    other = presign(secret, "media", "photos/b.txt", method="PUT", expires_at=1000)
    assert verify(secret, other, now=999) == ("media", "photos/b.txt", "PUT"), (
        "the token scope must include the method and the key, not only the bucket")

    try:
        verify(b"a different secret", token, now=999)
        raise AssertionError(
            "a token 'signed' with the wrong secret was accepted: the signature is not tied to "
            "the shared secret, so anyone can mint a capability")
    except InvalidSignatureError:
        pass

    body, _, signature = token.partition(".")
    cut = len(body) // 2
    flipped = "A" if body[cut] != "A" else "B"
    tampered = body[:cut] + flipped + body[cut + 1:] + "." + signature
    try:
        verify(secret, tampered, now=999)
        raise AssertionError(
            "a token whose payload was edited was accepted: the signature must cover the "
            "payload, so widening the expiry or retargeting the key invalidates it")
    except InvalidSignatureError:
        pass

    try:
        verify(secret, "not-a-token", now=999)
        raise AssertionError("a token with no signature was accepted")
    except InvalidSignatureError:
        pass

    try:
        verify(secret, token, now=1001)
        raise AssertionError(
            "an expired token was accepted: verify must reject it after the signature checks out")
    except ExpiredSignatureError:
        pass


# ---------------------------------------------------------------------------

CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("store.py", "CRUD; list honours prefix and delimiter", check_crud_and_listing),
    ("store.py", "versioning keeps every version; delete marker hides current", check_versioning_and_delete_markers),
    ("store.py", "ETag is the MD5 of the content and changes with it", check_etag_is_content_hash),
    ("store.py", "limit: deleting a non-empty bucket is refused", check_nonempty_bucket_refused),
    ("store.py", "limit: read-after-write is strongly consistent", check_read_after_write),
    ("presign.py", "presigned capability: signed, scoped, expiring", check_presigned_capability),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}Object Store From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<11} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<11} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<11} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built an object store.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
