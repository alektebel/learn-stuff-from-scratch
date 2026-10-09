"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
    "sessions.py": {
        "SessionStore.create": "Generate a token with `secrets.token_urlsafe(32)` and store {token: {user_id, expires_at: now + ttl}}. Return the token.",
        "SessionStore.validate": "Look the token up; return None if unknown OR if now >= expires_at; otherwise the stored user_id.",
        "SessionStore.revoke": "Delete the stored token (pop with a default). Return whether it existed.",
        "SessionStore.cleanup": "Collect tokens whose now >= expires_at, delete them, and return how many you removed. Leave live sessions alone.",
    },
    "jwt_tokens.py": {
        "b64url_encode": "base64.urlsafe_b64encode, then strip the '=' padding, then decode to ASCII.",
        "b64url_decode": "Re-pad to a multiple of 4 and decode with altchars=b'-_' and validate=True so illegal characters raise. Wrap binascii/ValueError failures in JWTError.",
        "_load_json": "json.loads the bytes; a parse error or a non-dict result is a JWTError.",
        "_sign": "hmac.new(secret-as-bytes, message, hashlib.sha256).digest().",
        "encode_jwt": "Reject alg not in ALLOWED_ALGS. Build header {alg, typ}; base64url the compact JSON of header and claims; sign 'header.payload'; append the base64url signature: header.payload.signature.",
        "decode_jwt": "Split on '.'; require exactly 3 parts; decode the header; REJECT any alg not in ALLOWED_ALGS (never trust it); recompute the HMAC over the first two segments and compare with hmac.compare_digest; only then parse the payload and check nbf (now + leeway < nbf) and exp (now - leeway >= exp).",
    },
    "oauth.py": {
        "pkce_challenge": "Only S256: sha256(code_verifier) -> base64url without padding. Reject any other method.",
        "OAuthServer.authorize": "Reject an unknown client; require redirect_uri to be EXACTLY in the registered list (no prefix match); require a code_challenge and method=S256; store a random single-use code bound to {client_id, redirect_uri, scope, user_id, challenge, method, expires_at, used=False}; echo state back.",
        "OAuthServer.exchange": "Reject an unknown code; a code from another client; a redirect_uri that differs; one already used; one expired (now >= expires_at); a missing or wrong code_verifier (compare pkce_challenge(code_verifier, method) to the stored challenge with hmac.compare_digest). Mark used and issue a random access token.",
        "OAuthServer.introspect": "Return {'active': False} for an unknown token, else {'active': True, client_id, scope, user_id} from the stored record.",
    },
}
