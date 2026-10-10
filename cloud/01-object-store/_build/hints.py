"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "store.py": {
  "ObjectStore.create_bucket": "A bucket name is a namespace: reject a duplicate (BucketAlreadyExists), otherwise store a new empty Bucket.",
  "ObjectStore.delete_bucket": "Refuse with BucketNotEmpty if ANY key still has stored versions — a key hidden behind a delete marker counts. Only then remove the bucket.",
  "ObjectStore.put_bucket_versioning": "Set the bucket's versioning flag; accept only \"Enabled\" or \"Suspended\" and reject anything else.",
  "ObjectStore.put_object": "Require bytes. ETag = md5 of the bytes (hex). With versioning on assign a fresh version id and append to the chain; with it off replace the chain with a single \"null\" version.",
  "ObjectStore.get_object": "Look up the version chain. Without a version id, the current version is the last; a delete marker makes it NoSuchKey. With one, search the chain and honour the marker.",
  "ObjectStore.delete_object": "With a version id, remove exactly that version (NoSuchVersion if absent). Without one: versioned -> append a delete marker and return it; unversioned -> remove the object (idempotent if it is missing).",
  "ObjectStore.list_objects": "Walk sorted keys, skip a current delete marker, filter by prefix; with a delimiter, fold any remaining delimiter in the key into a common prefix instead of listing it.",
  "ObjectStore.list_versions": "Every (key, Version) pair in sorted key order, delete markers included — this is ListObjectVersions, not ListObjects.",
 },
 "presign.py": {
  "presign": "Encode [bucket, key, method, expires_at] as compact JSON, sign those exact bytes with HMAC-SHA256, and return base64url(payload) + '.' + hex digest. Default expires_at to now + ttl.",
  "verify": "Split on '.', check the HMAC with hmac.compare_digest BEFORE decoding or trusting the payload, then decode and return (bucket, key, method); raise ExpiredSignatureError only after the signature is good.",
 },
}
