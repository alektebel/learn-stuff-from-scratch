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
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text):
    if isinstance(text, str):
        text = text.encode("ascii")
    pad = b"=" * (-len(text) % 4)
    try:
        # validate=True rejects any character outside the URL-safe alphabet, so a
        # tampered segment fails here instead of being silently repaired.
        return base64.b64decode(text + pad, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise JWTError("segment is not valid base64url") from exc


def _load_json(raw, what):
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise JWTError(f"{what} is not JSON") from exc
    if not isinstance(obj, dict):
        raise JWTError(f"{what} is not a JSON object")
    return obj


def _sign(message, secret):
    return hmac.new(_as_bytes(secret), message, hashlib.sha256).digest()


def encode_jwt(claims, secret, *, alg=DEFAULT_ALG):
    if alg not in ALLOWED_ALGS:
        raise JWTError(f"cannot encode with algorithm {alg!r}")
    header = {"alg": alg, "typ": "JWT"}
    head = b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    body = b64url_encode(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{head}.{body}".encode("ascii")
    return f"{head}.{body}.{b64url_encode(_sign(signing_input, secret))}"


def decode_jwt(token, secret, *, now, leeway=0):
    parts = token.split(".")
    if len(parts) != 3:
        raise JWTError("a JWT has three dot-separated segments")
    head, body, signature = parts
    header = _load_json(b64url_decode(head), "header")
    alg = header.get("alg")
    if alg not in ALLOWED_ALGS:
        raise JWTError(f"algorithm {alg!r} is not allowed")
    signing_input = f"{head}.{body}".encode("ascii")
    expected = _sign(signing_input, secret)
    try:
        given = b64url_decode(signature)
    except JWTError:
        given = b""
    if not hmac.compare_digest(given, expected):
        raise JWTError("signature does not match")
    # Only now is the payload worth parsing: a forged claims blob never gets this far.
    payload = _load_json(b64url_decode(body), "payload")
    if "nbf" in payload and now + leeway < payload["nbf"]:
        raise JWTError("token is not valid yet (nbf)")
    if "exp" in payload and now - leeway >= payload["exp"]:
        raise JWTError("token is expired")
    return payload


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
