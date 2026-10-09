"""OAuth 2.0 Authorization Code flow with PKCE.

Source: RFC 6749 (OAuth 2.0) section 4.1, RFC 7636 (PKCE), RFC 8252 (native apps), and
the OAuth 2.1 draft that makes PKCE mandatory and drops the implicit flow. The
authorization code flow trades a short-lived, single-use `code` (which travels through
the browser and can leak via referrers/history) for an `access_token` delivered over a
back channel that only the client can reach.

DESIGN DECISION - who authenticates the resource owner?
    In a full system the authorization endpoint renders a login/consent page and reads
    the user from a session (see `sessions.py`). To keep this module about the protocol,
    `authorize(..., user_id=...)` takes the already-authenticated user as an argument.
    Cost: no login UI, but the token binding (which user the code is for) is still real.

DESIGN DECISION - is PKCE required?
    Yes, always, and only `S256`. PKCE protects public clients (mobile/SPA) that cannot
    keep a secret: a stolen code is useless without the `code_verifier` that never left
    the client. Requiring it for confidential clients too is the OAuth 2.1 direction and
    removes a downgrade path. `plain` is rejected because it offers no protection if the
    code leaks. Cost: clients must generate and store one extra random value.

DESIGN DECISION - how is `redirect_uri` matched?
    Exact string equality against the registered URI, per RFC 6749 section 3.1.2.3. No
    prefix, no suffix, no normalization. A prefix match lets an attacker who controls
    `https://app.example/cb.evil.com` (or a path traversal) receive the code. This is a
    top cause of real OAuth account takeovers. Cost: clients cannot add query parameters.

DESIGN DECISION - authorization code lifetime and reuse.
    Codes are single-use and short-lived (default 60 s). We mark `used` on exchange and
    reject any later use. RFC 6749 section 4.1.2 says that replaying a code SHOULD revoke
    every token already issued from it (the code may have been stolen); we implement the
    simpler "reject the replay" and note the stronger rule as an exercise. Cost: a code
    stolen after the legitimate exchange is not detected here.
"""
import base64
import hashlib
import hmac
import secrets

__all__ = ["OAuthError", "pkce_challenge", "OAuthServer"]


class OAuthError(Exception):
    """The authorization request or code exchange is invalid."""


def pkce_challenge(code_verifier, method="S256"):
    # TODO: Only S256: sha256(code_verifier) -> base64url without padding. Reject any other method.
    raise NotImplementedError("pkce_challenge")


class OAuthServer:
    def __init__(self, clients, *, code_ttl=60):
        # clients: {client_id: {"redirect_uris": [...], "secret": ...}}
        self.clients = clients
        self.code_ttl = code_ttl
        self.codes = {}          # code -> authorization record
        self.access_tokens = {}  # token -> {"client_id", "scope", "user_id"}

    def authorize(self, *, client_id, redirect_uri, scope, state, user_id,
                  code_challenge, code_challenge_method="S256", now):
        # TODO: Reject an unknown client; require redirect_uri to be EXACTLY in the registered list (no prefix match); require a code_challenge and method=S256; store a random single-use code bound to {client_id, redirect_uri, scope, user_id, challenge, method, expires_at, used=False}; echo state back.
        raise NotImplementedError("OAuthServer.authorize")

    def exchange(self, *, code, client_id, redirect_uri, code_verifier, now):
        # TODO: Reject an unknown code; a code from another client; a redirect_uri that differs; one already used; one expired (now >= expires_at); a missing or wrong code_verifier (compare pkce_challenge(code_verifier, method) to the stored challenge with hmac.compare_digest). Mark used and issue a random access token.
        raise NotImplementedError("OAuthServer.exchange")

    def introspect(self, access_token):
        # TODO: Return {'active': False} for an unknown token, else {'active': True, client_id, scope, user_id} from the stored record.
        raise NotImplementedError("OAuthServer.introspect")


if __name__ == "__main__":
    clients = {"app": {"redirect_uris": ["https://app.example/cb"], "secret": "s"}}
    server = OAuthServer(clients, code_ttl=60)
    verifier = secrets.token_urlsafe(32)
    challenge = pkce_challenge(verifier)
    print(f"verifier: {len(verifier)} chars -> challenge {challenge[:16]}... "
          f"(SHA-256, base64url, no padding)")
    grant = server.authorize(client_id="app", redirect_uri="https://app.example/cb",
                             scope="read write", state="csrf-123", user_id="alice",
                             code_challenge=challenge, now=0)
    print(f"authorize returned state={grant['state']!r} (echoed verbatim for the client)")
    tokens = server.exchange(code=grant["code"], client_id="app",
                             redirect_uri="https://app.example/cb",
                             code_verifier=verifier, now=1)
    print(f"exchange: {tokens['token_type']} token for scope {tokens['scope']!r}")
    print(f"introspect: {server.introspect(tokens['access_token'])}")
    try:
        server.exchange(code=grant["code"], client_id="app",
                        redirect_uri="https://app.example/cb",
                        code_verifier=verifier, now=2)
    except OAuthError as exc:
        print(f"code replay rejected: {exc}")
    try:
        server.authorize(client_id="app", redirect_uri="https://app.example/cb.evil",
                         scope="read", state="x", user_id="alice",
                         code_challenge=challenge, now=3)
    except OAuthError as exc:
        print(f"prefix-stealing redirect_uri rejected: {exc}")
