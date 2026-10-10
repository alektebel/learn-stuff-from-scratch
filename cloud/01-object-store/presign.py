"""
A presigned-style capability token
===================================

Source: awsdocs:s3 -- "Sharing objects using presigned URLs" and the notion that a
presigned URL grants time-limited access to a single object without exposing the
signing key. Restated here in our own words.

A presigned URL is a *capability*: possession of the token is as good as the
permission it encodes, so the token itself must be unforgeable and must not be
widenable. It carries the operation it authorises (GET/PUT), the bucket and key it
is scoped to, and an expiry. A signature over all of that, keyed by a secret the
issuer and verifier share, is what stops a holder from editing the expiry outward
or aiming a GET token at someone else's key.

This is deliberately *not* AWS Signature Version 4. SigV4 is a canonicalisation
minefield -- a strict ordering of headers, a credential scope, a signing date --
and reproducing it byte-for-byte teaches header sorting, not capability design.
The security-relevant shape is the same and that is what the module keeps: sign a
canonical byte string with HMAC-SHA256, verify it in constant time, and check the
expiry only after the signature is trusted.

DESIGN DECISION - verify the signature before anything else it contains
The token is ``base64url(payload) + "." + hex(hmac_sha256(secret, payload))``. To
verify, recompute the HMAC over the raw payload bytes and compare with
``hmac.compare_digest`` *before* decoding or trusting the JSON. The rejected
alternative -- parse first, then check -- means an attacker controls a parser
feeding on unauthenticated input, and a malformed or hostile payload can raise
before the check ever runs. Cost: an expired-but-forged token is reported as a
bad signature rather than as expired, which is the honest answer.

DESIGN DECISION - the signature covers the payload bytes, not a re-serialised dict
We sign the exact bytes that the token carries, so verification never has to
reproduce a JSON encoder's whitespace or key order. The rejected alternative --
decode to a dict, re-encode, and sign that -- makes the signature depend on
``json.dumps`` options (``sort_keys``, separators, unicode escaping) that must
match on both sides forever; a single version skew silently invalidates every
token. Cost: the payload is opaque until verified, so no one can read the scope of
a token without the secret. That is a feature: the scope of a capability is not
public.

DESIGN DECISION - expiry is a logical ``now``, injected by the caller
``verify`` takes an explicit ``now`` (and ``presign`` an explicit ``now`` when
computing a default expiry) instead of calling ``time.time()`` internally. The
rejected alternative -- read the wall clock inside -- makes every expiry test
either sleep or monkeypatch the clock. Injecting ``now`` lets check step 6 expire a
token deterministically and lets a caller in another timezone verify against the
same instant. Cost: a careless caller who omits ``now`` gets a wall-clock check,
so the deterministic path is opt-in; we default to the wall clock so the simple
call site still works.

DESIGN DECISION - base64url of a compact JSON array plus a hex digest
The payload is a JSON array ``[bucket, key, method, expires_at]`` encoded
base64url without padding, and the signature is lowercase hex. Array order is
fixed by construction rather than by a sorted join, so a bucket named ``"a:b"``
cannot be smuggled into a different field of a colon-joined string. The rejected
alternative -- concatenate with a separator -- needs escaping rules for that
separator in bucket and key names, and every escaping rule is a place to get the
delimiter wrong. Cost: the token is longer and the JSON is not human-readable
without decoding.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional, Tuple


class InvalidSignatureError(Exception):
    """The token was tampered with or signed by a different secret."""


class ExpiredSignatureError(Exception):
    """The signature is valid but the token's expiry has passed."""


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def presign(
    secret: bytes,
    bucket: str,
    key: str,
    method: str = "GET",
    expires_at: Optional[int] = None,
    now: Optional[int] = None,
    ttl: int = 3600,
) -> str:
    """Return a capability token for ``method bucket/key``.

    If ``expires_at`` is omitted it is ``now + ttl``; ``now`` defaults to the wall
    clock (pass it explicitly for a deterministic token).
    """
    # TODO: Encode [bucket, key, method, expires_at] as compact JSON, sign those exact bytes with HMAC-SHA256, and return base64url(payload) + '.' + hex digest. Default expires_at to now + ttl.
    raise NotImplementedError("presign")


def verify(secret: bytes, token: str, now: Optional[int] = None) -> Tuple[str, str, str]:
    """Return ``(bucket, key, method)`` for a valid token.

    Raises ``InvalidSignatureError`` if the token is malformed or forged, and
    ``ExpiredSignatureError`` if the signature is good but the expiry has passed.
    ``now`` defaults to the wall clock.
    """
    # TODO: Split on '.', check the HMAC with hmac.compare_digest BEFORE decoding or trusting the payload, then decode and return (bucket, key, method); raise ExpiredSignatureError only after the signature is good.
    raise NotImplementedError("verify")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    secret = b"a shared signing secret"
    token = presign(secret, "media", "photos/cat.jpg", method="GET",
                    expires_at=1000, now=900)
    print("Presign a capability, then verify it")
    print(f"  token              {token}")
    print(f"  verify(now=999)    {verify(secret, token, now=999)}")

    body, _, signature = token.partition(".")
    cut = len(body) // 2
    flipped = "A" if body[cut] != "A" else "B"
    tampered = body[:cut] + flipped + body[cut + 1:] + "." + signature
    print("Tampering and forging are refused before the payload is trusted")
    for label, probe in (
        ("tampered payload", lambda: verify(secret, tampered, now=999)),
        ("forged secret", lambda: verify(b"wrong secret", token, now=999)),
        ("no signature", lambda: verify(secret, "not-a-token", now=999)),
    ):
        try:
            probe()
            print(f"  {label:16s} -> ACCEPTED (wrong!)")
        except InvalidSignatureError as exc:
            print(f"  {label:16s} -> InvalidSignatureError: {exc}")

    print("Expiry is checked only after the signature is trusted")
    try:
        verify(secret, token, now=1001)
        print("  expired token    -> ACCEPTED (wrong!)")
    except ExpiredSignatureError as exc:
        print(f"  expired token    -> ExpiredSignatureError: {exc}")


if __name__ == "__main__":
    _demo()
