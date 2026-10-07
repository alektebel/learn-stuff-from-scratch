"""Turn a checker's failure text into a category you can see patterns in.

Run enough courses and the interesting signal is not "stage 5 failed" — it is
"boundary/off-by-one has now bitten you in sampling, preference lists and route
lookup." That sentence only exists if failures are classified consistently.
"""

import re

# (label, [needles]) — first match wins. Needles are lowercased substrings.
_RULES = [
    ("test-setup", ["setup:"]),
    ("boundary/off-by-one", [
        "off-by-one", "cross", ">=", "inclusive", "boundary", "threshold",
        "at least", "exactly k", "in the nucleus",
    ]),
    ("numerical stability", [
        "overflow", "nan", "finite", "stability", "logsumexp", "exp(",
    ]),
    ("masking", ["mask", "causal", "future", "leak"]),
    ("ordering/determinism", [
        "rank", "order", "deterministic", "same corpus", "lowest-rank",
        "tie", "reproducib",
    ]),
    ("aliasing/ownership", [
        "alias", "mutat", "copy", "shared", "clone", "shallow", "isolation",
    ]),
    ("exactness", [
        "exact", "identical", "bit-identical", "approximate", "differs",
        "must equal",
    ]),
    ("cost model", [
        "quadratic", "linear", "complexity", "cost", " o(", "overlap",
    ]),
    ("stateful vs stateless", ["stateful", "stateless", "nacl", "security group"]),
    ("quorum/consistency", [
        "quorum", "sloppy", "durab", "consisten", "reconcil", "vector clock",
    ]),
    ("lifecycle/state", [
        "evict", "expire", "timeout", "ttl", "reset", "redeliver", "cold start",
        "visibility",
    ]),
    ("concurrency", ["deadlock", "barrier", "race", "lock", "atomic", "divergen"]),
    ("shape/indexing", [
        "shape", "dimension", "index", "length", "size", "off the end",
    ]),
    ("symbol resolution", ["label", "undefined", "unknown instruction", "register"]),
]

_ERROR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(Error|Exception)\b")


def classify(detail: str) -> str:
    """Return a short category label for a failure detail string."""
    text = (detail or "").lower()
    for label, needles in _RULES:
        if any(n in text for n in needles):
            return label
    return "logic/edge case"


def is_exception(detail: str) -> bool:
    """True if a FAIL/ERROR detail looks like an uncaught Python exception."""
    return bool(_ERROR_RE.match((detail or "").strip()))


def signature(detail: str) -> str:
    """A stable fingerprint so the SAME bug on repeat runs collapses to one key.

    Numbers, hex, paths and quoted values are dropped; the first sentence is
    kept. Two runs of the same misconception produce the same signature, while
    genuinely different failures do not.
    """
    text = (detail or "").strip().splitlines()[0] if detail else ""
    text = text.lower()
    text = re.sub(r"0x[0-9a-f]+", "0xN", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", "N", text)
    text = re.sub(r"[\"'][^\"']*[\"']", "'S'", text)
    text = re.sub(r"[\w./-]+\.py", "F.py", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:72]


def condense(detail: str, limit: int = 220) -> str:
    """One readable line from a multi-line checker detail, for the nudge."""
    if not detail:
        return ""
    flat = " ".join(detail.split())
    if len(flat) <= limit:
        return flat
    cut = flat[:limit]
    for sep in (". ", "; ", " — ", ", "):
        i = cut.rfind(sep)
        if i > limit // 2:
            return cut[:i + 1].strip()
    return cut.rstrip() + "..."
