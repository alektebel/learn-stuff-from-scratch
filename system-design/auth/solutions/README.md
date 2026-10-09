# Solutions

Complete implementations of the three authentication mechanisms. Copy any file over the
template of the same name to see its steps pass.

Run each file directly for its demo:

```bash
python3 sessions.py     # sessions.py  -> token randomness and absolute expiry
python3 jwt_tokens.py   # jwt_tokens.py -> token size, tampering, expiry
python3 oauth.py        # oauth.py     -> PKCE challenge, exchange, replay rejection
```

## Expected demo output

```
$ python3 sessions.py
100000 sessions -> 100000 distinct tokens
token length: 43 chars (32 random bytes, base64url, no padding)
validate at t+59: 'alice'
validate at t+60: None  (absolute expiry, no sliding window)
revoke(): True  validate after: None

$ python3 jwt_tokens.py
claims {'sub': 'alice', 'scope': 'read', 'exp': 1000} -> 136 byte token (3.3x the JSON)
header+payload: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjEwMDAsInNjb3BlIjoicmVhZCIsInN1YiI6ImFsaWNlIn0
valid at t=999: {'exp': 1000, 'scope': 'read', 'sub': 'alice'}
tampered signature rejected: signature does not match
expired rejected: token is expired

$ python3 oauth.py
verifier: 43 chars -> challenge 2bhgYAqnlqPG866i... (SHA-256, base64url, no padding)
authorize returned state='csrf-123' (echoed verbatim for the client)
exchange: Bearer token for scope 'read write'
introspect: {'active': True, 'client_id': 'app', 'scope': 'read write', 'user_id': 'alice'}
code replay rejected: authorization code already used
prefix-stealing redirect_uri rejected: redirect_uri does not exactly match a registered URI
```

(The OAuth challenge prefix is random every run; the shape is what matters.)

## Verification

```bash
# against the solutions, in a temp copy:
cp check.py solutions/*.py /tmp/auth && cd /tmp/auth && python3 check.py --all   # 14/14

# the checker's own bugs: plant each mutation and confirm the step catches it
python3 ../../../.claude/skills/graded-module/scripts/mutate.py .. ../_build/mutations.py
```

Mutation result: `11/11 CAUGHT, 0 MISSED`.
