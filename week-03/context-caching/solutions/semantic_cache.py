"""
Exact & Semantic Response Caching — Complete Solution

A different layer from the KV cache. The KV cache makes *computing* an answer
cheaper; a response cache skips the model entirely. Exact caching is safe and
boring. Semantic caching — "this question is close enough to one I answered" —
is neither, and the interesting part is measuring exactly how unsafe it is.
"""

import hashlib
import math
import time
from typing import Dict, List, Optional, Sequence, Tuple

EMBED_DIM = 64


# ---------------------------------------------------------------------------
# A hashing-trick embedding (no model, no dependencies)
# ---------------------------------------------------------------------------

def tokenize(text: str) -> List[str]:
    cleaned = "".join(c.lower() if c.isalnum() else " " for c in text)
    return [word for word in cleaned.split() if word]


def embed(text: str, dim: int = EMBED_DIM) -> List[float]:
    """Bag-of-words + character-trigram hashing, L2-normalised.

    This is a stand-in for a real sentence encoder. It captures lexical overlap
    only — it has no idea that "cheap" and "inexpensive" are related, and it
    cannot tell "flights to Paris" from "flights from Paris". A real deployment
    would call an embedding model here, but the *failure modes* demonstrated
    below are the same ones real encoders have; they just move around.
    """
    vector = [0.0] * dim
    words = tokenize(text)
    for word in words:
        index = int(hashlib.md5(word.encode()).hexdigest(), 16) % dim
        vector[index] += 1.0
        padded = f"  {word}  "
        for i in range(len(padded) - 2):
            trigram = padded[i:i + 3]
            index = int(hashlib.md5(trigram.encode()).hexdigest(), 16) % dim
            vector[index] += 0.3
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# The caches
# ---------------------------------------------------------------------------

class CacheEntry:
    __slots__ = ("prompt", "response", "vector", "created", "last_used", "hits")

    def __init__(self, prompt: str, response: str, vector: List[float],
                 created: float):
        self.prompt = prompt
        self.response = response
        self.vector = vector
        self.created = created
        self.last_used = created
        self.hits = 0


class ExactCache:
    """Hash the prompt, serve the stored response. Safe, and often enough.

    Before reaching for embeddings, measure this. Production traffic is far more
    repetitive than people expect, and an exact cache can never return a wrong
    answer — the worst it does is miss.
    """

    def __init__(self, capacity: int = 1000, ttl_seconds: float = 3600):
        self.capacity = capacity
        self.ttl = ttl_seconds
        self.entries: Dict[str, CacheEntry] = {}
        self.stats = {"hits": 0, "misses": 0, "expired": 0, "evictions": 0}

    @staticmethod
    def key(prompt: str, model: str = "", temperature: float = 0.0) -> str:
        """Everything that changes the answer belongs in the key.

        Temperature above 0 arguably should not be cached at all: the caller
        asked for variety and a cache gives them the opposite.
        """
        payload = f"{model}|{temperature}|{prompt}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, prompt: str, model: str = "", temperature: float = 0.0,
            now: Optional[float] = None) -> Optional[str]:
        now = time.time() if now is None else now
        entry = self.entries.get(self.key(prompt, model, temperature))
        if entry is None:
            self.stats["misses"] += 1
            return None
        if now - entry.created > self.ttl:
            self.stats["expired"] += 1
            self.stats["misses"] += 1
            del self.entries[self.key(prompt, model, temperature)]
            return None
        entry.last_used = now
        entry.hits += 1
        self.stats["hits"] += 1
        return entry.response

    def put(self, prompt: str, response: str, model: str = "",
            temperature: float = 0.0, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        while len(self.entries) >= self.capacity:
            victim = min(self.entries.items(), key=lambda kv: kv[1].last_used)[0]
            del self.entries[victim]
            self.stats["evictions"] += 1
        self.entries[self.key(prompt, model, temperature)] = \
            CacheEntry(prompt, response, [], now)

    @property
    def hit_rate(self) -> float:
        total = self.stats["hits"] + self.stats["misses"]
        return self.stats["hits"] / total if total else 0.0


class SemanticCache:
    """Serve a stored response when a new prompt is 'close enough'.

    The threshold is a direct trade between hit rate and wrong answers, and
    there is no setting that avoids both. Treat it as a product decision, not a
    tuning parameter: what is the cost of confidently answering a slightly
    different question?
    """

    def __init__(self, threshold: float = 0.95, capacity: int = 1000,
                 ttl_seconds: float = 3600):
        self.threshold = threshold
        self.capacity = capacity
        self.ttl = ttl_seconds
        self.entries: List[CacheEntry] = []
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, prompt: str, now: Optional[float] = None
            ) -> Tuple[Optional[str], float, Optional[str]]:
        """Returns (response, best similarity, the prompt that matched)."""
        now = time.time() if now is None else now
        self.entries = [e for e in self.entries if now - e.created <= self.ttl]
        if not self.entries:
            self.stats["misses"] += 1
            return None, 0.0, None

        vector = embed(prompt)
        best = max(self.entries, key=lambda e: cosine(vector, e.vector))
        similarity = cosine(vector, best.vector)
        if similarity >= self.threshold:
            best.last_used = now
            best.hits += 1
            self.stats["hits"] += 1
            return best.response, similarity, best.prompt
        self.stats["misses"] += 1
        return None, similarity, best.prompt

    def put(self, prompt: str, response: str, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        while len(self.entries) >= self.capacity:
            victim = min(self.entries, key=lambda e: e.last_used)
            self.entries.remove(victim)
            self.stats["evictions"] += 1
        self.entries.append(CacheEntry(prompt, response, embed(prompt), now))

    @property
    def hit_rate(self) -> float:
        total = self.stats["hits"] + self.stats["misses"]
        return self.stats["hits"] / total if total else 0.0


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

# (query, cached prompt, should_it_hit)
EVAL_PAIRS: List[Tuple[str, str, bool]] = [
    # Genuine paraphrases — a hit is correct.
    ("how do I reset my password", "how do i reset my password?", True),
    ("How do I reset my password!", "how do i reset my password?", True),
    ("what is your refund policy", "what's your refund policy", True),
    ("how do I cancel my subscription", "how do i cancel my subscription", True),
    # Superficially similar, semantically opposite — a hit is a WRONG ANSWER.
    ("how do I enable two factor auth", "how do I disable two factor auth", False),
    ("flights from Paris to Rome", "flights from Rome to Paris", False),
    ("convert 100 USD to EUR", "convert 100 EUR to USD", False),
    ("is this covered under warranty", "is this not covered under warranty", False),
    ("what is the price with tax", "what is the price without tax", False),
    # Unrelated — a hit would be absurd.
    ("what is the capital of France", "how do i reset my password?", False),
    ("write me a poem about rain", "what's your refund policy", False),
]


def evaluate_threshold(threshold: float) -> Dict[str, float]:
    """Precision/recall of a semantic cache at one threshold."""
    true_hit = false_hit = true_miss = false_miss = 0
    for query, cached, should_hit in EVAL_PAIRS:
        cache = SemanticCache(threshold=threshold)
        cache.put(cached, f"[answer to: {cached}]")
        response, _, _ = cache.get(query)
        hit = response is not None
        if hit and should_hit:
            true_hit += 1
        elif hit and not should_hit:
            false_hit += 1
        elif not hit and should_hit:
            false_miss += 1
        else:
            true_miss += 1
    total_hits = true_hit + false_hit
    return {
        "threshold": threshold,
        "hits": total_hits,
        "correct_hits": true_hit,
        "wrong_answers": false_hit,
        "missed_opportunities": false_miss,
        "precision": true_hit / total_hits if total_hits else 1.0,
        "recall": true_hit / (true_hit + false_miss) if (true_hit + false_miss) else 0.0,
    }


def _demo() -> None:
    print("=== Exact caching first — measure before you get clever ===")
    traffic = (["what is your refund policy"] * 40 +
               ["how do I reset my password"] * 30 +
               [f"summarise document {i}" for i in range(30)])
    cache = ExactCache(capacity=100)
    now = 1000.0
    for prompt in traffic:
        if cache.get(prompt, now=now) is None:
            cache.put(prompt, f"[answer to {prompt}]", now=now)
        now += 1
    print(f"{len(traffic)} requests, {len(set(traffic))} distinct")
    print(f"exact-cache hit rate: {cache.hit_rate:.1%}, "
          f"model calls avoided: {cache.stats['hits']}")
    print("No embeddings, no threshold, no possibility of a wrong answer.")

    print("\n=== What the similarity scores actually look like ===")
    print(f"{'similarity':>11}  {'should hit':>10}  pair")
    for query, cached, should_hit in EVAL_PAIRS:
        similarity = cosine(embed(query), embed(cached))
        flag = "yes" if should_hit else "NO"
        print(f"{similarity:>11.3f}  {flag:>10}  {query[:34]:<34} | {cached[:30]}")

    print("\n=== Threshold sweep: hit rate versus wrong answers ===")
    print(f"{'threshold':>10}{'hits':>7}{'correct':>9}{'WRONG':>7}"
          f"{'missed':>8}{'precision':>11}{'recall':>9}")
    for threshold in (0.80, 0.85, 0.90, 0.93, 0.95, 0.97, 0.99):
        result = evaluate_threshold(threshold)
        print(f"{threshold:>10.2f}{result['hits']:>7}{result['correct_hits']:>9}"
              f"{result['wrong_answers']:>7}{result['missed_opportunities']:>8}"
              f"{result['precision']:>10.0%}{result['recall']:>9.0%}")

    print("\nThe pairs that break it are the ones where a single token flips the")
    print("meaning: enable/disable, from/to, with/without, covered/not covered.")
    print("Lexical similarity is near 1.0 and the correct answers are opposite.")
    print("A better encoder moves these numbers; it does not remove the failure")
    print("mode, because the failure is in the premise — 'similar text implies")
    print("interchangeable answer' is simply not true.")

    print("\n=== Where semantic caching is defensible ===")
    print("  - FAQ deflection, where a near-miss costs a mildly unhelpful reply")
    print("  - As a RETRIEVAL hint: use the hit to prefetch context, not to")
    print("    skip the model")
    print("  - Behind a cheap verifier: a small model checks whether the cached")
    print("    answer actually answers the new question")
    print("\nWhere it is not:")
    print("  - Anything with a negation, a direction, a unit, or a number")
    print("  - Personalised answers (the prompt hides the user's identity)")
    print("  - Anything the user could act on and be harmed by being wrong")

    print("\n=== TTL: cached answers go stale ===")
    cache = ExactCache(capacity=10, ttl_seconds=60)
    cache.put("what is the current price", "$42", now=1000.0)
    print(f"t=1000 -> {cache.get('what is the current price', now=1000.0)}")
    print(f"t=1030 -> {cache.get('what is the current price', now=1030.0)}")
    print(f"t=1100 -> {cache.get('what is the current price', now=1100.0)}")
    print("The TTL is your honest statement about how long an answer stays")
    print("true. Anything backed by changing data needs a short one — or")
    print("explicit invalidation when the underlying data changes.")


if __name__ == "__main__":
    _demo()
