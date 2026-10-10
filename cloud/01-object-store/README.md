# Object Store From Scratch

An S3-shaped object store in pure Python (standard library only): buckets, keys,
object **versioning** with **delete markers**, an **ETag**, and a presigned-style
**capability token**, built one mechanism at a time so each can be verified offline.

It exists to close a gap in the repo's cloud material: `aws-from-scratch/` covers
compute and `cloud/03-queue-fanout/` covers messaging, but storage — the service
most systems are built around — had no from-scratch model. This one keeps the
parts that teach something (flat keys pretending to be folders, the version chain,
content addressing) and drops the parts that are wire-protocol trivia (HTTP,
SigV4, multipart).

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Buckets and keys | put / get / delete in a flat namespace | `store.py` | 1 |
| Prefix and delimiter | ListObjectsV2 folding `a/b/c` into a common prefix | `store.py` | 1 |
| Versioning | a per-key version chain, an opaque version id per put | `store.py` | 2 |
| Delete markers | a zero-byte version that hides the current object | `store.py` | 2 |
| Content addressing | ETag = MD5 of the bytes | `store.py` | 3 |
| Capability tokens | base64url payload + HMAC-SHA256, scoped and expiring | `presign.py` | 6 |

## How to use this directory

The top-level `store.py` and `presign.py` are **templates**: each function you
write keeps its signature and docstring, has a `TODO` with a hint, and raises
`NotImplementedError`. `solutions/` holds working versions for when you are stuck
or to compare afterwards.

```bash
cd cloud/01-object-store
python3 check.py        # what to build next; stops at the first gap
python3 check.py 3      # one step
python3 check.py --all  # everything
```

`check.py` runs 6 checks against **your** code and never imports `solutions/`.
Two of them are the module's **limit cases**: deleting a non-empty bucket is
refused rather than silently destructive, and a read-after-write of a just-put key
is visible immediately (the model is strongly consistent, never eventually
consistent).

**The checker was itself tested.** Eight classic bugs were planted in copies of
the solutions, and each one must be caught by its check:

| Planted bug | Caught by |
|---|---|
| `delete_bucket` wipes a non-empty bucket | step 4 |
| a versioned delete removes the current version instead of adding a marker | step 2 |
| `put` is write-behind, so a read sees a stale store | step 5 |
| `list` ignores the delimiter | step 1 |
| the ETag is a constant, not a content hash | step 3 |
| versioning is enabled but each put still overwrites | step 2 |
| `verify` accepts any signature | step 6 |
| `verify` never checks the expiry | step 6 |

## Design decisions, named

Each file opens with its decisions and what they cost. In short:

- **Strong read-after-write, never eventual consistency** (`store.py`). The
  historical "eventually consistent for overwrites and deletes" model is rejected;
  an in-process store has no replication delay to hide. The lesson is that the
  naive write-behind design is *wrong*, and step 5 constructs exactly that read.
  Cost: the model says nothing about the stale window a real system once had.
- **A delete marker is a first-class version** (`store.py`), not a boolean on the
  entry. Put/delete/put keeps its order, and the retained bytes stay reachable by
  version id. Cost: a bucket whose keys all end in markers lists empty but is
  still non-empty to `delete_bucket` — step 4 builds that case.
- **Version ids from a store-wide counter** (`store.py`), not a clock or a content
  hash, so every check is deterministic. Cost: the ids are guessable and reveal
  write order and a rough global count.
- **Delete is idempotent** (`store.py`), as S3's DeleteObject is, so retries are
  safe. Cost: an unversioned delete cannot tell "removed" from "was absent" by its
  return value.
- **Verify the signature over the payload bytes before parsing them**
  (`presign.py`), so unauthenticated input never reaches the JSON parser.
- **Expiry is a logical `now` injected by the caller** (`presign.py`), so an
  expiry test never sleeps or monkeypatches the clock.

## Questions to answer before reading the solutions

1. A bucket lists empty because every key ends in a delete marker, yet
   `delete_bucket` refuses to delete it. Which is "empty" — the view a client sees,
   or the bytes the store holds? What does S3 choose, and why?
2. Under versioning, `put`, `put`, `delete` leaves **four** versions on a key whose
   chain started unversioned. Which one is the delete marker hiding, and how would
   you restore the object by deleting the marker rather than re-uploading?
3. The ETag is the MD5 of the bytes. Why does a *multipart* upload in real S3 get a
   different, non-MD5 ETag, and what has to change about your verification if it
   does?
4. The token signs `base64url(payload)`, and the signature is a hex digest over the
   raw payload bytes. What breaks if you base64-decode first and sign the decoded
   bytes? What breaks if you re-encode the JSON with `sort_keys=True` before signing?
5. Step 5 writes 100 keys and reads each back. Why is that test *sufficient* to
   catch a write-behind queue, and what would a randomised version of the same test
   fail to catch?

## Limits

- **Single process, no concurrency.** There is no locking and no durable storage;
  the store is a dict of lists. It models the API's *semantics*, not a server.
- **No wire protocol, no SigV4.** The capability token keeps the security shape
  (HMAC over a canonical scope, constant-time compare, expiry after signature) but
  is not AWS Signature Version 4 and would not interoperate.
- **ETag is MD5 of the whole object.** Multipart uploads, which produce an
  ETag-of-ETags, are not modeled; neither is server-side encryption or checksums.
- **Versioning is a boolean, not a lifecycle.** "Suspended" behaves like off; S3's
  exact suspended-version interaction with the `"null"` version is not reproduced.
- **No ACLs, policies, CORS or lifecycle rules.** Access control in this module is
  exactly the capability token.
