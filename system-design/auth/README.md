# Authentication From Scratch

Three authentication mechanisms implemented without a framework, each one showing the
failure mode that makes it hard: server-side **sessions** (revocable, stateful), **JWT**
bearer tokens (stateless, hard to revoke), and the OAuth 2.0 **authorization code flow
with PKCE** (delegated access without sharing a password).

Everything is standard-library only (`hashlib`, `hmac`, `base64`, `json`, `secrets`) and
deterministic: callers pass `now` explicitly, so expiry tests never race the clock.

## Run it

```bash
cd system-design/auth
python3 check.py          # stop at the first unimplemented step
python3 check.py --all    # run every check
python3 check.py 7        # just step 7
```

A step that raises `NotImplementedError` is reported as TODO, not a failure. Find the
next one, read the docstring in its file, implement it, re-run. Compare with
`solutions/` only after trying.

## The steps

| Step | File | What you implement |
|---|---|---|
| 1 | `sessions.py` | `SessionStore.create` / `validate`: token -> user, unknown token is `None` |
| 2 | `sessions.py` | absolute expiry: `now >= expires_at`, `ttl=0` is already dead, reads do not extend life |
| 3 | `sessions.py` | `revoke`, and isolation: revoking one session leaves the others |
| 4 | `sessions.py` | `secrets`-based tokens (200 sessions, 200 distinct) and `cleanup` of expired rows |
| 5 | `jwt_tokens.py` | `encode_jwt` / `decode_jwt` round-trip and the unpadded base64url wire format |
| 6 | `jwt_tokens.py` | the signature covers the bytes: rewritten payload, flipped signature, wrong secret all rejected |
| 7 | `jwt_tokens.py` | algorithm allow-list: `alg=none` and an `RS256`-labelled HMAC token are rejected |
| 8 | `jwt_tokens.py` | `exp` / `nbf` / bounded clock-skew `leeway` |
| 9 | `jwt_tokens.py` | malformed tokens, non-JSON header, non-object payload, bad base64url |
| 10 | `oauth.py` | `authorize` -> `exchange` -> `introspect` (the happy path) |
| 11 | `oauth.py` | `redirect_uri` matched **exactly**, at authorize and at exchange |
| 12 | `oauth.py` | the authorization code is single-use |
| 13 | `oauth.py` | PKCE `S256`: challenge required, wrong/missing verifier rejected, failures do not consume the code |
| 14 | `oauth.py` | the code is bound to its client and expires quickly |

## Design decisions

Each file's docstring names the questions and the cost of the answer; the short version:

- **Sessions, token source.** `secrets.token_urlsafe(32)` (256 bits, OS CSPRNG). `random`
  is a Mersenne Twister and is predictable from a handful of outputs.
- **Sessions, expiry.** Absolute (`expires_at = now + ttl`), not sliding. Sliding keeps
  active users in but splits "idle" and "absolute" timeouts into two policies.
- **Sessions, revoke.** Delete the row. Immediate revocation is the reason to pay for a
  shared store at all.
- **JWT, algorithm.** HS256 only, chosen from an allow-list. Trusting the header is the
  `alg=none` and RS256/HS256-confusion attack.
- **JWT, compare.** `hmac.compare_digest`; `==` leaks the matching prefix through timing.
- **JWT, claims.** Verify the signature *before* parsing the payload; then `nbf`, then
  `exp` with a bounded `leeway`. No `exp` means no expiry (a policy choice).
- **OAuth, redirect_uri.** Exact match (RFC 6749 §3.1.2.3). A prefix match lets
  `https://app.example/cb.evil.com` steal codes.
- **OAuth, PKCE.** Required, `S256` only; `plain` offers nothing if the code leaks.
- **OAuth, code.** Single-use and short-lived (60 s default), bound to client and
  redirect URI.

## Mutation table

`_build/mutations.py` plants 11 mistakes; `mutate.py` confirms each is caught by the step
that should catch it. All CAUGHT:

| Mistake | Caught by |
|---|---|
| session expiry never checked | 2 |
| `revoke` is a no-op | 3 |
| predictable tokens (constant) | 4 |
| `alg:none` accepted / header trusted | 7 |
| signature not verified | 6 |
| `exp` not checked | 8 |
| `redirect_uri` prefix match | 11 |
| authorization code reusable | 12 |
| PKCE not verified | 13 |
| code not bound to its client | 14 |
| authorization code never expires | 14 |

## Questions to answer yourself (there is no check for these)

- Sessions scale by sharing a store (Redis, DB). What breaks first under 100k requests/s,
  and does the token need to be encrypted or only random?
- A JWT is verified by any replica with the secret. How do you revoke one *before* it
  expires, and what does that do to the "stateless" advantage? (Sketch a denylist keyed by
  `jti` with TTL = remaining lifetime.)
- Why is a JWT's payload readable by anyone? When is that a feature (federated identity)
  and when is it a leak (putting an email or role in it)?
- In OAuth, the *client* stores the `code_verifier`. What happens if it is a public mobile
  app, and why does PKCE still help?
- The resource server must decide whether an access token is valid. Compare opaque tokens +
  introspection (stateful, revocable) with JWT access tokens (stateless, verifiable
  offline). Which would you choose for a 5 ms p99 budget?

## Limits (not implemented / deliberately simplified)

- No TLS, cookies, CSRF tokens, or `HttpOnly`/`SameSite` handling: this is the protocol
  layer, not the transport.
- HS256 only; no asymmetric signing, so verifiers need the signing secret.
- The authorization endpoint takes `user_id` as an argument instead of rendering a
  login/consent page.
- Auth-code replay only rejects the second exchange; RFC 6749 §4.1.2 suggests revoking all
  tokens issued from a replayed code.
- No refresh tokens, scopes are stored but never enforced, no rate limiting.
