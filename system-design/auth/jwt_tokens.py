"""Stateless bearer tokens, JWT style.

Source: RFC 7519 (JSON Web Token), RFC 7515 (JWS), RFC 8725 (JWT BCP), OWASP JSON Web
Token Cheat Sheet. A JWT is `header.payload.signature`: two base64url-encoded JSON
objects and an HMAC over the first two segments, all joined by dots. The server keeps no
state, so any replica can verify any token with a shared secret - that is the scaling
win, and also the revocation problem: a valid, unexpired token cannot be cancelled
without a denylist.

DESIGN DECISION - which algorithms?
    Only HS256 (HMAC-SHA256) with a symmetric secret. Every other `alg` value is
    rejected, including `none` and the asymmetric names (RS256, ES256). The classic
    attacks both hinge on trusting the header: `alg: none` means "no signature", and the
    RS256/HS256 confusion makes a verifier use an RSA *public* key as an HMAC secret. A
    verifier must pick the algorithm from a fixed allow-list, never from the token.
    Cost: no asymmetric signing, so a verifier would need the signing secret (fine for a
    single issuer, wrong when third parties must verify).

DESIGN DECISION - how is the signature compared?
    `hmac.compare_digest`, which is constant-time. `==` short-circuits on the first
    differing byte and leaks how many leading bytes matched through timing, enough to
    recover a valid signature byte by byte. Cost: negligible.

DESIGN DECISION - claim checks.
    `nbf` (not before) and `exp` (expiry) are Unix seconds; `now` is passed in so tests
    are deterministic. `leeway` forgives small clock skew between issuer and verifier.
    A token with no `exp` is allowed (a caller's policy problem, not a parse error).
    Cost: the leeway window is a small replay window.

DESIGN DECISION - one exception type.
    Every failure raises `JWTError` with a short reason. Tests may branch on the reason,
    but production callers should treat any JWTError as "reject": distinguishing
    "bad signature" from "expired" in an API response helps an attacker. Cost: coarser
    error handling.
"""
import base64
import binascii
import hashlib
import hmac
import json

__all__ = [
    "JWTError", "ALLOWED_ALGS", "DEFAULT_ALG",
    "b64url_encode", "b64url_decode", "encode_jwt", "decode_jwt",
]

ALLOWED_ALGS = frozenset({"HS256"})
DEFAULT_ALG = "HS256"


class JWTError(Exception):
    """Any reason a token is not acceptable. Treat every one as 'reject'."""


def _as_bytes(secret):
    return secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)


def b64url_encode(data):
    # TODO: base64.urlsafe_b64encode, then strip the '=' padding, then decode to ASCII.
    raise NotImplementedError("b64url_encode")


def b64url_decode(text):
    # TODO: Re-pad to a multiple of 4 and decode with altchars=b'-_' and validate=True so illegal characters raise. Wrap binascii/ValueError failures in JWTError.
    raise NotImplementedError("b64url_decode")


def _load_json(raw, what):
    # TODO: json.loads the bytes; a parse error or a non-dict result is a JWTError.
    raise NotImplementedError("_load_json")


def _sign(message, secret):
    # TODO: hmac.new(secret-as-bytes, message, hashlib.sha256).digest().
    raise NotImplementedError("_sign")


def encode_jwt(claims, secret, *, alg=DEFAULT_ALG):
    # TODO: Reject alg not in ALLOWED_ALGS. Build header {alg, typ}; base64url the compact JSON of header and claims; sign 'header.payload'; append the base64url signature: header.payload.signature.
    raise NotImplementedError("encode_jwt")


def decode_jwt(token, secret, *, now, leeway=0):
    # TODO: Split on '.'; require exactly 3 parts; decode the header; REJECT any alg not in ALLOWED_ALGS (never trust it); recompute the HMAC over the first two segments and compare with hmac.compare_digest; only then parse the payload and check nbf (now + leeway < nbf) and exp (now - leeway >= exp).
    raise NotImplementedError("decode_jwt")


if __name__ == "__main__":
    secret = b"demo-secret"
    claims = {"sub": "alice", "scope": "read", "exp": 1000}
    token = encode_jwt(claims, secret)
    raw = json.dumps(claims, separators=(",", ":")).encode()
    print(f"claims {claims} -> {len(token)} byte token ({len(token)/len(raw):.1f}x the JSON)")
    print(f"header+payload: {token.split('.')[0]}.{token.split('.')[1]}")
    print(f"valid at t=999: {decode_jwt(token, secret, now=999)}")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    try:
        decode_jwt(tampered, secret, now=999)
        print("tampered signature: ACCEPTED (bug!)")
    except JWTError as exc:
        print(f"tampered signature rejected: {exc}")
    try:
        decode_jwt(token, secret, now=1000)
    except JWTError as exc:
        print(f"expired rejected: {exc}")
