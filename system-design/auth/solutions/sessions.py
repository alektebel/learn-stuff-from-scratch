"""Server-side sessions: the stateful half of authentication.

Source: OWASP Session Management Cheat Sheet; RFC 6265 (HTTP state management);
OWASP ASVS v4 section 3. A session is a random opaque token the server stores and looks
up on every request. The client only ever holds the token, so all authority lives on the
server. That is what makes revocation trivial (delete the row) and horizontal scaling
hard (every request needs the shared store).

DESIGN DECISION - how is the token generated?
    `secrets.token_urlsafe(32)` gives 256 bits from the OS CSPRNG, URL-safe, no padding.
    Alternatives: uuid4 (122 bits, fine but designed as an identifier, not as a bearer
    credential); `random.random()` / `randint` (Mersenne Twister, NOT cryptographic - an
    attacker who observes a few tokens can predict the next). We take the CSPRNG.
    Cost: tokens are 43 characters; we never parse them, so the length is free.

DESIGN DECISION - absolute vs sliding expiry?
    We store `expires_at = now + ttl` and never move it. Sliding expiry (refresh the
    deadline on every use) keeps active users logged in, but then "idle timeout" and
    "absolute timeout" become two separate policies to track. We implement the simple
    absolute one; the sliding variant is an exercise. Cost: an active user is logged out
    `ttl` seconds after login even if they never stop clicking.

DESIGN DECISION - what does revoke do?
    It deletes the stored record. Any copy the client holds is useless immediately.
    Alternative: mark a `revoked` flag and keep the row for audit. We delete; a real
    system appends to an audit log before deleting. Cost: no history for forensics.

DESIGN DECISION - exact comparison of `now` to `expires_at`.
    `now >= expires_at` expires, so a `ttl` of 0 means "already expired", which is what
    tests want. Using `>` would leave a zero-TTL token alive until `now + epsilon`.
    Cost: none.
"""
import secrets

__all__ = ["SessionStore"]


class SessionStore:
    def __init__(self):
        # token -> {"user_id": str, "expires_at": float}
        self.sessions = {}

    def create(self, user_id, *, ttl=3600, now):
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {"user_id": user_id, "expires_at": now + ttl}
        return token

    def validate(self, token, *, now):
        record = self.sessions.get(token)
        if record is None:
            return None
        if now >= record["expires_at"]:
            return None
        return record["user_id"]

    def revoke(self, token):
        return self.sessions.pop(token, None) is not None

    def cleanup(self, now):
        dead = [token for token, record in self.sessions.items()
                if now >= record["expires_at"]]
        for token in dead:
            del self.sessions[token]
        return len(dead)


if __name__ == "__main__":
    store = SessionStore()
    tokens = {store.create(f"user{i}", ttl=3600, now=0.0) for i in range(100_000)}
    # A 256-bit token should essentially never collide: expected collisions ~ n^2 / 2^257.
    print(f"100000 sessions -> {len(tokens)} distinct tokens")
    print(f"token length: {len(next(iter(tokens)))} chars "
          f"(32 random bytes, base64url, no padding)")
    token = store.create("alice", ttl=60, now=1000.0)
    print(f"validate at t+59: {store.validate(token, now=1059.0)!r}")
    print(f"validate at t+60: {store.validate(token, now=1060.0)!r}  "
          f"(absolute expiry, no sliding window)")
    print(f"revoke(): {store.revoke(token)}  validate after: {store.validate(token, now=1059.0)!r}")
