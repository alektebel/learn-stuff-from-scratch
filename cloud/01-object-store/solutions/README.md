# Object Store From Scratch — Solutions

Complete versions of every template in the parent directory. Pure Python 3,
standard library only. Run them from inside this directory (they import each
other by name):

```bash
python3 store.py     # put/get/list with delimiter, version chain, refused delete
python3 presign.py   # sign a capability, tamper with it, let it expire
```

## Expected output

`python3 store.py`:

```
Put and ETag
  photos/cat.jpg      etag=78b51f009dc6844fa82b264a9869de74 (md5 of the 9 bytes)
ListObjectsV2: prefix and delimiter fold the fake folders
  prefix=photos/ delimiter=/  keys=['photos/cat.jpg', 'photos/dog.jpg']
                              common_prefixes=['photos/2024/']
Versioning: every PUT is kept; DELETE hides via a marker
  versions of notes.txt before delete: ['null', 'v0000000000000001', 'v0000000000000002', 'v0000000000000003']
  delete_object        -> version v0000000000000003 is_delete_marker=True
  current get          -> NoSuchKey (hidden)
  get(version=v0000000000000001) -> b'notes-v2'
  get(version=v0000000000000002) -> b'notes-v3'
  list_objects keys    -> ['photos/2024/party.jpg', 'photos/cat.jpg', 'photos/dog.jpg']
Deleting a non-empty bucket is refused, not destructive
  delete_bucket(media) -> BucketNotEmpty; 7 versions still stored
```

`python3 presign.py` (the token text is stable across runs — `now` and
`expires_at` are passed in, and the only randomness-free encoding is compact JSON):

```
Presign a capability, then verify it
  token              WyJtZWRpYSIsInBob3Rvcy9jYXQuanBnIiwiR0VUIiwxMDAwXQ.1ee5b71f2346abeeab2ebc0de9914151d5f341d383a0150def1a0056fdc836af
  verify(now=999)    ('media', 'photos/cat.jpg', 'GET')
Tampering and forging are refused before the payload is trusted
  tampered payload -> InvalidSignatureError: signature does not match
  forged secret    -> InvalidSignatureError: signature does not match
  no signature     -> InvalidSignatureError: malformed token: no signature
Expiry is checked only after the signature is trusted
  expired token    -> ExpiredSignatureError: token expired at 1000 (now 1001)
```

## What the numbers mean

- **`etag=78b51f…`** is `md5(b"cat-bytes")`. The demo's first note proves the tag
  is a function of the bytes, not of the key or the version id.
- **`common_prefixes=['photos/2024/']`** is the flat-namespace trick: no directory
  exists, but `photos/2024/party.jpg` contains the `/` delimiter after the
  `photos/` prefix, so it is folded into a common prefix and the literal string
  `photos/2024/` is reported as though it were a folder.
- **`['null', v1, v2, v3]`** is the version chain after enabling versioning on a
  key that already existed. `"null"` is the version id S3 uses before versioning
  is turned on; `v1` and `v2` are the two versioned puts; `v3` is the delete
  marker the delete appended.
- **`7 versions still stored`** is why `delete_bucket(media)` is refused: three
  visible objects plus the four-version `notes.txt` chain. A delete marker does
  not free the bytes it hides.
- **the signature is the last 64 hex characters** of the token; everything before
  the `.` is the base64url payload it covers. Changing one payload character, as
  the demo does, invalidates the signature before the JSON is ever parsed.
