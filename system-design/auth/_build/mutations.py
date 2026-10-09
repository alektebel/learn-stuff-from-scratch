"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

Each mutation is a mistake a learner plausibly makes, and the step that must catch it.
"""
MUTATIONS = [
    # --- sessions.py -------------------------------------------------------
    ("session expiry never checked", "sessions.py",
     '        if now >= record["expires_at"]:\n            return None\n',
     '',
     "2"),
    ("revoke is a no-op", "sessions.py",
     '        return self.sessions.pop(token, None) is not None',
     '        return True',
     "3"),
    ("predictable tokens", "sessions.py",
     '        token = secrets.token_urlsafe(32)',
     '        token = "fixed-token"',
     "4"),
    # --- jwt_tokens.py ----------------------------------------------------
    ("alg:none accepted / header trusted", "jwt_tokens.py",
     '    if alg not in ALLOWED_ALGS:\n'
     '        raise JWTError(f"algorithm {alg!r} is not allowed")\n'
     '    signing_input = f"{head}.{body}".encode("ascii")\n'
     '    expected = _sign(signing_input, secret)\n'
     '    try:\n'
     '        given = b64url_decode(signature)\n'
     '    except JWTError:\n'
     '        given = b""\n'
     '    if not hmac.compare_digest(given, expected):\n'
     '        raise JWTError("signature does not match")',
     '    signing_input = f"{head}.{body}".encode("ascii")\n'
     '    if alg == "none":\n'
     '        given = expected = b""\n'
     '    else:\n'
     '        expected = _sign(signing_input, secret)\n'
     '        try:\n'
     '            given = b64url_decode(signature)\n'
     '        except JWTError:\n'
     '            given = b""\n'
     '    if given != expected:\n'
     '        raise JWTError("signature does not match")',
     "7"),
    ("signature not verified", "jwt_tokens.py",
     '    if not hmac.compare_digest(given, expected):\n'
     '        raise JWTError("signature does not match")',
     '    if False:\n        raise JWTError("signature does not match")',
     "6"),
    ("expiry not checked", "jwt_tokens.py",
     '    if "exp" in payload and now - leeway >= payload["exp"]:\n'
     '        raise JWTError("token is expired")',
     '    if False:\n        raise JWTError("token is expired")',
     "8"),
    # --- oauth.py ---------------------------------------------------------
    ("redirect_uri prefix match", "oauth.py",
     '        if redirect_uri not in client["redirect_uris"]:',
     '        if not any(redirect_uri.startswith(u) for u in client["redirect_uris"]):',
     "11"),
    ("authorization code reusable", "oauth.py",
     '        if record["used"]:\n'
     '            raise OAuthError("authorization code already used")',
     '        if False:\n            raise OAuthError("authorization code already used")',
     "12"),
    ("PKCE not verified", "oauth.py",
     '        expected = pkce_challenge(code_verifier, record["method"])\n'
     '        if not hmac.compare_digest(expected, record["code_challenge"]):\n'
     '            raise OAuthError("PKCE verification failed")',
     '        if False:\n            raise OAuthError("PKCE verification failed")',
     "13"),
    ("code not bound to its client", "oauth.py",
     '        if record["client_id"] != client_id:\n'
     '            raise OAuthError("code was issued to another client")',
     '        if False:\n            raise OAuthError("code was issued to another client")',
     "14"),
    ("authorization code never expires", "oauth.py",
     '        if now >= record["expires_at"]:\n'
     '            raise OAuthError("authorization code expired")',
     '        if False:\n            raise OAuthError("authorization code expired")',
     "14"),
]
