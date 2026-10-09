"""
Progress checker for the authentication-templates module.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.
"""

import base64
import hashlib
import hmac
import json
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

SECRET = b"test-secret"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _hs256(signing_input: bytes, secret=SECRET) -> str:
    return _b64(hmac.new(secret, signing_input, hashlib.sha256).digest())


def _oauth_server(**kwargs):
    from oauth import OAuthServer
    clients = {"app": {"redirect_uris": ["https://app.example/cb"], "secret": "s"}}
    return OAuthServer(clients, **kwargs)


# ---------------------------------------------------------------------------
# Steps 1-4: sessions.py
# ---------------------------------------------------------------------------

def check_session_roundtrip() -> None:
    from sessions import SessionStore

    store = SessionStore()
    alice = store.create("alice", ttl=100, now=0.0)
    bob = store.create("bob", ttl=100, now=0.0)
    assert store.validate(alice, now=0.0) == "alice"
    assert store.validate(bob, now=50.0) == "bob", "a session must stay valid until its deadline"
    assert store.validate(alice, now=99.999) == "alice"
    assert store.validate("not-a-real-token", now=0.0) is None, (
        "an unknown token must validate to None, not raise and not return a user")
    assert store.validate(alice, now=0.0) == store.validate(alice, now=0.0)


def check_session_expiry() -> None:
    from sessions import SessionStore

    store = SessionStore()
    token = store.create("carol", ttl=10, now=0.0)
    assert store.validate(token, now=9.0) == "carol"
    assert store.validate(token, now=10.0) is None, (
        "a ttl of 10 must expire AT now+10 (now >= expires_at), not a moment later")
    zero = store.create("dan", ttl=0, now=0.0)
    assert store.validate(zero, now=0.0) is None, "ttl=0 means already expired"
    # expiry is absolute, not refreshed by use
    assert store.validate(token, now=5.0) == "carol"
    assert store.validate(token, now=10.0) is None, "reading a session must not extend its life"


def check_session_revoke() -> None:
    from sessions import SessionStore

    store = SessionStore()
    alice = store.create("alice", ttl=100, now=0.0)
    bob = store.create("bob", ttl=100, now=0.0)
    assert store.revoke(alice) is True
    assert store.validate(alice, now=1.0) is None, (
        "a revoked token must be rejected immediately (server-side sessions are revocable)")
    assert store.validate(bob, now=1.0) == "bob", "revoking one session must not touch another"
    assert store.revoke(alice) is False, "revoking an already-revoked token reports not-found"
    assert store.revoke("never-existed") is False


def check_session_cleanup() -> None:
    from sessions import SessionStore

    store = SessionStore()
    tokens = [store.create(f"u{i}", ttl=1000, now=0.0) for i in range(200)]
    assert len(set(tokens)) == 200, (
        "two sessions share a token: the token source is not random (use secrets, not random)")
    assert all(len(t) >= 32 for t in tokens), (
        "tokens shorter than 32 chars cannot carry enough randomness to resist guessing")
    expired_a = store.create("a", ttl=10, now=0.0)
    live = store.create("b", ttl=1000, now=0.0)
    expired_c = store.create("c", ttl=5, now=0.0)
    removed = store.cleanup(now=10.0)
    assert removed == 2, f"cleanup removed {removed} sessions, expected exactly the 2 expired ones"
    assert store.validate(expired_a, now=10.0) is None
    assert store.validate(expired_c, now=10.0) is None
    assert store.validate(live, now=10.0) == "b", "cleanup deleted a live session"
    assert store.cleanup(now=10.0) == 0, "cleanup must be idempotent"


# ---------------------------------------------------------------------------
# Steps 5-9: jwt_tokens.py
# ---------------------------------------------------------------------------

_B64URL = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def check_jwt_roundtrip() -> None:
    from jwt_tokens import decode_jwt, encode_jwt

    claims = {"sub": "alice", "scope": "read write", "n": 42, "admin": False}
    token = encode_jwt(claims, SECRET)
    assert token.count(".") == 2, "a JWT is header.payload.signature"
    head, body, sig = token.split(".")
    for segment in (head, body, sig):
        assert segment and "=" not in segment, "base64url segments must be non-empty and unpadded"
        assert set(segment) <= _B64URL, f"segment {segment!r} is not URL-safe base64"
    assert decode_jwt(token, SECRET, now=0) == claims, "round-trip changed the claims"
    # str and bytes secrets must be interchangeable
    assert decode_jwt(encode_jwt(claims, "test-secret"), "test-secret", now=0) == claims
    parsed_header = json.loads(base64.urlsafe_b64decode(head + "=="))
    assert parsed_header.get("alg") == "HS256", f"header alg should be HS256, got {parsed_header}"


def check_jwt_signature() -> None:
    from jwt_tokens import JWTError, decode_jwt, encode_jwt

    token = encode_jwt({"sub": "alice", "role": "user"}, SECRET)
    head, body, sig = token.split(".")
    # Rewrite the payload (privilege escalation) and keep the old signature.
    claims = json.loads(base64.urlsafe_b64decode(body + "=="))
    claims["role"] = "admin"
    forged = f"{head}.{_b64(json.dumps(claims).encode())}.{sig}"
    try:
        decode_jwt(forged, SECRET, now=0)
        raise AssertionError("a rewritten payload kept a valid signature: the signature is not covering it")
    except JWTError:
        pass
    # Flip one bit of the signature.
    raw = bytearray(base64.urlsafe_b64decode(sig + "=="))
    raw[0] ^= 0x01
    try:
        decode_jwt(f"{head}.{body}.{_b64(bytes(raw))}", SECRET, now=0)
        raise AssertionError("a flipped signature byte was accepted")
    except JWTError:
        pass
    # Correct token under the wrong secret.
    try:
        decode_jwt(token, b"other-secret", now=0)
        raise AssertionError("a token verified under the wrong secret")
    except JWTError:
        pass


def check_jwt_algorithm_allowlist() -> None:
    from jwt_tokens import JWTError, decode_jwt

    def crafted(alg, signature=""):
        head = _b64(json.dumps({"alg": alg, "typ": "JWT"}).encode())
        body = _b64(json.dumps({"sub": "attacker"}).encode())
        return f"{head}.{body}.{signature}"

    for alg in ("none", "None", "NONE", "RS256", "HS512", "", "ES256"):
        try:
            decode_jwt(crafted(alg), SECRET, now=0)
            raise AssertionError(f"alg={alg!r} was accepted; a verifier may only accept HS256")
        except JWTError:
            pass
    # A header that claims RS256 but carries a *valid* HMAC must still be rejected: this is
    # the algorithm-confusion attack (reject by allow-list, never trust the header).
    head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps({"sub": "attacker"}).encode())
    try:
        decode_jwt(f"{head}.{body}.{_hs256(f'{head}.{body}'.encode())}", SECRET, now=0)
        raise AssertionError("a token whose header claims RS256 was accepted (algorithm confusion)")
    except JWTError:
        pass


def check_jwt_expiry() -> None:
    from jwt_tokens import JWTError, decode_jwt, encode_jwt

    token = encode_jwt({"sub": "alice", "exp": 1000}, SECRET)
    assert decode_jwt(token, SECRET, now=999)["sub"] == "alice"
    for moment in (1000, 2000):
        try:
            decode_jwt(token, SECRET, now=moment)
            raise AssertionError(f"an expired token was accepted at now={moment}")
        except JWTError:
            pass
    assert decode_jwt(token, SECRET, now=1005, leeway=10)["sub"] == "alice"
    try:
        decode_jwt(token, SECRET, now=1011, leeway=10)
        raise AssertionError("the clock-skew leeway was applied more widely than requested")
    except JWTError:
        pass
    nbf = encode_jwt({"sub": "alice", "nbf": 2000, "exp": 3000}, SECRET)
    try:
        decode_jwt(nbf, SECRET, now=1999)
        raise AssertionError("a not-yet-valid token (nbf in the future) was accepted")
    except JWTError:
        pass
    assert decode_jwt(nbf, SECRET, now=2000)["sub"] == "alice"
    forever = encode_jwt({"sub": "alice"}, SECRET)
    assert decode_jwt(forever, SECRET, now=10**9)["sub"] == "alice", (
        "a token without exp must not be treated as expired")


def check_jwt_malformed() -> None:
    from jwt_tokens import JWTError, b64url_decode, decode_jwt

    for bad in ("", "abc", "a.b", "a.b.c.d", "...", "not a jwt"):
        try:
            decode_jwt(bad, SECRET, now=0)
            raise AssertionError(f"{bad!r} was accepted as a JWT")
        except JWTError:
            pass
    head = _b64(b'{"alg":"HS256","typ":"JWT"}')
    # A non-JSON header.
    try:
        decode_jwt(f"{_b64(b'not json')}.{_b64(b'{}')}.x", SECRET, now=0)
        raise AssertionError("a non-JSON header was accepted")
    except JWTError:
        pass
    # A JSON payload that is not an object (an array is not a claims set).
    body = _b64(b"[1,2,3]")
    try:
        decode_jwt(f"{head}.{body}.{_hs256(f'{head}.{body}'.encode())}", SECRET, now=0)
        raise AssertionError("a JSON array payload was accepted")
    except JWTError:
        pass
    # The base64url decoder itself must reject characters outside its alphabet.
    try:
        b64url_decode("!!!!")
        raise AssertionError("b64url_decode accepted characters outside the URL-safe alphabet")
    except JWTError:
        pass


# ---------------------------------------------------------------------------
# Steps 10-14: oauth.py
# ---------------------------------------------------------------------------

def check_oauth_happy_path() -> None:
    from oauth import pkce_challenge

    server = _oauth_server(code_ttl=60)
    verifier = "verifier-0123456789-abcdefghijklmnopqrstuvwxyz"
    grant = server.authorize(client_id="app", redirect_uri="https://app.example/cb",
                             scope="read write", state="xyz", user_id="alice",
                             code_challenge=pkce_challenge(verifier), now=0)
    assert grant["state"] == "xyz", "the state parameter must be echoed back to the client"
    tokens = server.exchange(code=grant["code"], client_id="app",
                             redirect_uri="https://app.example/cb",
                             code_verifier=verifier, now=1)
    assert tokens["token_type"] == "Bearer"
    assert tokens["scope"] == "read write"
    info = server.introspect(tokens["access_token"])
    assert info["active"] is True and info["client_id"] == "app" and info["user_id"] == "alice"
    assert server.introspect("nope") == {"active": False}


def check_oauth_redirect_uri() -> None:
    from oauth import OAuthError, pkce_challenge

    server = _oauth_server()
    verifier = "v" * 40
    challenge = pkce_challenge(verifier)
    for evil in ("https://app.example/cb.evil.com",
                 "https://app.example/cb/../admin",
                 "https://app.example/cbextra",
                 "https://app.example/cb?x=1",
                 "https://app.example/CB",
                 "http://app.example/cb"):
        try:
            server.authorize(client_id="app", redirect_uri=evil, scope="read", state="s",
                             user_id="alice", code_challenge=challenge, now=0)
            raise AssertionError(
                f"redirect_uri {evil!r} was accepted; only the exact registered URI may be")
        except OAuthError:
            pass
    grant = server.authorize(client_id="app", redirect_uri="https://app.example/cb",
                             scope="read", state="s", user_id="alice",
                             code_challenge=challenge, now=0)
    try:
        server.exchange(code=grant["code"], client_id="app",
                        redirect_uri="https://app.example/cb.evil.com",
                        code_verifier=verifier, now=1)
        raise AssertionError("exchange accepted a redirect_uri different from the authorization request")
    except OAuthError:
        pass


def check_oauth_code_single_use() -> None:
    from oauth import OAuthError, pkce_challenge

    server = _oauth_server()
    verifier = "v" * 40
    grant = server.authorize(client_id="app", redirect_uri="https://app.example/cb",
                             scope="read", state="s", user_id="alice",
                             code_challenge=pkce_challenge(verifier), now=0)
    first = server.exchange(code=grant["code"], client_id="app",
                            redirect_uri="https://app.example/cb",
                            code_verifier=verifier, now=1)
    assert first["access_token"]
    try:
        server.exchange(code=grant["code"], client_id="app",
                        redirect_uri="https://app.example/cb",
                        code_verifier=verifier, now=2)
        raise AssertionError("the same authorization code was exchanged twice (a leaked code must not work)")
    except OAuthError:
        pass


def check_oauth_pkce() -> None:
    from oauth import OAuthError, pkce_challenge

    server = _oauth_server()
    verifier = "correct-verifier-1234567890"
    challenge = pkce_challenge(verifier)
    for bad in ({"code_challenge": None}, {"code_challenge": "x", "code_challenge_method": "plain"}):
        try:
            server.authorize(client_id="app", redirect_uri="https://app.example/cb",
                             scope="read", state="s", user_id="alice", now=0, **bad)
            raise AssertionError(f"authorize accepted {bad}; PKCE with S256 is required")
        except OAuthError:
            pass
    grant = server.authorize(client_id="app", redirect_uri="https://app.example/cb",
                             scope="read", state="s", user_id="alice",
                             code_challenge=challenge, now=0)
    for wrong in (None, "wrong-verifier", verifier + "x"):
        try:
            server.exchange(code=grant["code"], client_id="app",
                            redirect_uri="https://app.example/cb",
                            code_verifier=wrong, now=1)
            raise AssertionError(f"exchange accepted code_verifier={wrong!r}; PKCE was not verified")
        except OAuthError:
            pass
    # None of those rejected attempts may have consumed the code.
    ok = server.exchange(code=grant["code"], client_id="app",
                         redirect_uri="https://app.example/cb",
                         code_verifier=verifier, now=2)
    assert ok["access_token"]


def check_oauth_binding_and_expiry() -> None:
    from oauth import OAuthError, pkce_challenge

    server = _oauth_server(code_ttl=60)
    verifier = "v" * 40
    grant = server.authorize(client_id="app", redirect_uri="https://app.example/cb",
                             scope="read", state="s", user_id="alice",
                             code_challenge=pkce_challenge(verifier), now=0)
    try:
        server.exchange(code=grant["code"], client_id="other",
                        redirect_uri="https://app.example/cb",
                        code_verifier=verifier, now=1)
        raise AssertionError("a code issued to 'app' was redeemed by a different client")
    except OAuthError:
        pass
    server.exchange(code=grant["code"], client_id="app",
                    redirect_uri="https://app.example/cb", code_verifier=verifier, now=1)
    verifier2 = "w" * 40
    late = server.authorize(client_id="app", redirect_uri="https://app.example/cb",
                            scope="read", state="s", user_id="alice",
                            code_challenge=pkce_challenge(verifier2), now=0)
    try:
        server.exchange(code=late["code"], client_id="app",
                        redirect_uri="https://app.example/cb",
                        code_verifier=verifier2, now=60)
        raise AssertionError("an expired authorization code (now >= expires_at) was exchanged")
    except OAuthError:
        pass
    try:
        server.exchange(code="never-issued", client_id="app",
                        redirect_uri="https://app.example/cb",
                        code_verifier=verifier, now=0)
        raise AssertionError("an unknown authorization code was exchanged")
    except OAuthError:
        pass


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("sessions.py", "create / validate / unknown token", check_session_roundtrip),
    ("sessions.py", "absolute expiry, ttl=0", check_session_expiry),
    ("sessions.py", "revoke, and isolation between sessions", check_session_revoke),
    ("sessions.py", "unguessable tokens, cleanup of expired", check_session_cleanup),
    ("jwt_tokens.py", "encode/decode round-trip, URL-safe wire format", check_jwt_roundtrip),
    ("jwt_tokens.py", "tampered payload / signature / secret", check_jwt_signature),
    ("jwt_tokens.py", "algorithm allow-list (none, RS256 confusion)", check_jwt_algorithm_allowlist),
    ("jwt_tokens.py", "exp / nbf / clock-skew leeway", check_jwt_expiry),
    ("jwt_tokens.py", "malformed tokens and segments", check_jwt_malformed),
    ("oauth.py", "authorize + exchange + introspect", check_oauth_happy_path),
    ("oauth.py", "exact redirect_uri match at both endpoints", check_oauth_redirect_uri),
    ("oauth.py", "authorization code is single-use", check_oauth_code_single_use),
    ("oauth.py", "PKCE S256 verification", check_oauth_pkce),
    ("oauth.py", "code bound to client, short-lived", check_oauth_binding_and_expiry),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}Authentication From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<15} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<15} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<15} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the three auth mechanisms.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
