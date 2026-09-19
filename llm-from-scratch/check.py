"""
Progress checker for the LLM-from-scratch templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

Nothing here imports solutions/. It tests YOUR code.
"""

import math
import pathlib
import shutil
import sys
import traceback
from typing import Callable, List, Tuple

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def check_bpe_pairs() -> None:
    from tokenizer import get_pair_counts, merge_pair

    counts = get_pair_counts([1, 1, 1, 2])
    assert counts[(1, 1)] == 2, f"expected two adjacent (1,1) pairs, got {counts}"
    assert counts[(1, 2)] == 1

    merged = merge_pair([1, 1, 1, 2], (1, 1), 9)
    assert merged == [9, 1, 2], (
        "'aaa' must merge to (new, a), not to two overlapping merges. Scan with an "
        f"index and skip past a merge; got {merged}")


def check_bpe_training() -> None:
    from tokenizer import encode, train_bpe

    corpus = b"abababab" * 4
    first = train_bpe(corpus, 8)
    second = train_bpe(corpus, 8)
    assert first == second, (
        "training must be deterministic. Ties in pair frequency need an explicit "
        "rule (highest count, then smallest pair) or the same corpus makes a "
        "different tokenizer every run.")
    assert first.get((97, 98)) == 256, (
        "the most frequent pair is 'ab' (97, 98), so it must become merge id 256 "
        f"(the first new id). Got {first.get((97, 98))!r}")
    ids = encode(corpus.decode(), first)
    assert len(ids) < len(corpus), \
        f"merges must compress the corpus: {len(ids)} tokens for {len(corpus)} bytes"


def check_bpe_encode_order() -> None:
    from tokenizer import decode, encode, train_bpe

    # A hand-built table where a left-to-right sweep gives a different answer.
    merges = {(98, 97): 256, (97, 98): 257}
    ids = encode("aba", merges)
    assert ids == [97, 256], (
        "encode must apply the LOWEST-rank merge first, anywhere in the sequence. "
        "Here (98,97) is rank 256 and (97,98) is rank 257, so 'aba' -> a then "
        "merge 'ba' -> [97, 256]. A left-to-right sweep would merge (97,98) first "
        f"and return [257, 97]. Got {ids}")
    assert decode(ids, merges) == b"aba"

    corpus = b"the cat sat on the mat. the cat ate the rat. " * 10
    table = train_bpe(corpus, 32)
    assert decode(encode(corpus.decode(), table), table) == corpus, (
        "decode(encode(text)) must reproduce the original bytes exactly. If it "
        "does not, an id is being expanded into the wrong children.")


# ---------------------------------------------------------------------------
# Attention
# ---------------------------------------------------------------------------

def check_attention_softmax() -> None:
    from attention import softmax

    p = softmax([1000.0, 1001.0])
    assert all(math.isfinite(x) for x in p), (
        "softmax([1000, 1001]) must stay finite. exp(1000) is larger than a float "
        "can hold, so you must subtract the max first: exp(x - max). The result is "
        "mathematically identical and the overflow disappears.")
    assert abs(sum(p) - 1.0) < 1e-12, f"softmax must sum to 1, got {sum(p)}"
    assert p[1] > p[0], "the larger logit must get the larger probability"
    one = softmax([5.0])
    assert abs(one[0] - 1.0) < 1e-12, "a single score must become probability 1"


def check_attention_causal() -> None:
    from attention import scaled_dot_product_attention

    Q = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    K = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    V = [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]   # every value row sums to 1

    full = scaled_dot_product_attention(Q, K, V)
    for i, row in enumerate(full):
        assert abs(sum(row) - 1.0) < 1e-9, (
            f"row {i} of attention must be a convex combination of the value rows, "
            f"so it sums to 1; got {sum(row)}. Are the weights actually normalised?")

    causal = scaled_dot_product_attention(Q, K, V, causal=True)
    for i, row in enumerate(causal):
        assert abs(sum(row) - 1.0) < 1e-9, (
            f"causal row {i} must still sum to 1. If you zero the future AFTER "
            "the softmax the mass no longer adds up; mask to -inf BEFORE it.")
    assert causal[1] != full[1], (
        "causal row 1 must differ from the full-attention row 1 — position 1 is "
        "not allowed to see position 2, and if the outputs match the future leaked")
    assert causal[0] == V[0], (
        "position 0 may attend only to itself, so its output must equal V[0]=[1,0]. "
        f"Got {causal[0]} — if it sees position 1, the mask is missing or applied "
        "after the softmax.")


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def check_sampling_temperature() -> None:
    from random import Random

    from sampling import apply_temperature, sample, softmax

    logits = [2.0, 1.0, 0.0]
    greedy = apply_temperature(logits, 0.0)
    assert greedy[0] == 0.0 and greedy[1] == float("-inf") and greedy[2] == float("-inf"), (
        "temperature 0 means hard greedy: one-hot at the argmax, -inf elsewhere. "
        "'Very small temperature' still samples the tail occasionally.")
    assert sample(logits, Random(0), temperature=0.0) == 0

    scaled = apply_temperature(logits, 0.5)
    assert scaled == [4.0, 2.0, 0.0], f"temperature divides the logits, got {scaled}"

    hot = max(softmax(apply_temperature(logits, 1.0)))
    sharp = max(softmax(apply_temperature(logits, 0.5)))
    assert sharp > hot, "lower temperature must sharpen the distribution"


def check_sampling_top_k() -> None:
    from sampling import softmax, top_k_filter

    logits = [1.0, 3.0, 3.0, 2.0]
    masked = top_k_filter(logits, 2)
    assert masked[0] == float("-inf") and masked[3] == float("-inf"), \
        f"top-2 of {logits} must drop indices 0 and 3, got {masked}"
    assert masked[1] != float("-inf") and masked[2] != float("-inf"), (
        "the two 3.0 values tie — break ties by smallest index and keep BOTH")
    assert abs(sum(softmax(masked)) - 1.0) < 1e-12, \
        "the surviving mass must renormalise to 1"


def check_sampling_top_p() -> None:
    from sampling import top_p_filter

    probabilities = [0.5, 0.3, 0.15, 0.05]
    logits = [math.log(x) for x in probabilities]
    masked = top_p_filter(logits, 0.9)
    assert masked[2] != float("-inf"), (
        "top-p must keep the token that CROSSES the threshold. 0.5 + 0.3 + 0.15 = "
        "0.95 >= 0.9, so index 2 is inside the nucleus. Using `>` instead of `>=` "
        "drops it, which is the classic off-by-one-token bug.")
    assert masked[3] == float("-inf"), "0.05 is outside the 0.9 nucleus"
    assert masked[0] != float("-inf") and masked[1] != float("-inf")


def check_sampling_determinism() -> None:
    from random import Random

    from sampling import sample

    logits = [1.0, 1.0, 1.0, 1.0]
    first = Random(123)
    second = Random(123)
    a = [sample(logits, first, temperature=0.9, k=2, p=0.95) for _ in range(50)]
    b = [sample(logits, second, temperature=0.9, k=2, p=0.95) for _ in range(50)]
    assert a == b, (
        "a seeded RNG must reproduce the same sample sequence. If it does not, "
        "your evals are measuring noise.")


# ---------------------------------------------------------------------------
# KV cache
# ---------------------------------------------------------------------------

def check_kv_cache_object() -> None:
    from kv_cache import KVCache

    cache = KVCache()
    assert len(cache) == 0
    cache.append([1.0, 2.0], [3.0, 4.0])
    cache.append([5.0, 6.0], [7.0, 8.0])
    assert len(cache) == 2, f"two appends must give length 2, got {len(cache)}"
    assert cache.keys() == [[1.0, 2.0], [5.0, 6.0]], f"keys: {cache.keys()}"
    assert cache.values() == [[3.0, 4.0], [7.0, 8.0]], f"values: {cache.values()}"


def check_kv_cache_exactness() -> None:
    from kv_cache import KVCache, cached_step, recompute_step

    d = 8
    K = [[math.sin(i + j) for j in range(d)] for i in range(12)]
    V = [[math.cos(i * j + 1) for j in range(d)] for i in range(12)]
    q = [math.sin(3 + j) for j in range(d)]

    cache = KVCache()
    for key, value in zip(K, V):
        cache.append(key, value)

    got = cached_step(q, cache)
    want = recompute_step(q, K, V)
    diff = max(abs(a - b) for a, b in zip(got, want))
    assert diff < 1e-9, (
        f"the cached step must be EXACT, not approximate; max difference {diff:.2e}. "
        "A cache that changes the output gives you a model you cannot reproduce.")

    shorter = recompute_step(q, K[:-1], V[:-1])
    assert max(abs(a - b) for a, b in zip(got, shorter)) > 1e-6, (
        "the last key must change the output. If dropping it changes nothing, the "
        "cache is not actually being read.")


def check_kv_cache_cost() -> None:
    from kv_cache import cached_work, recompute_work

    recompute = recompute_work(64, 64, 8)
    cached = cached_work(64, 64, 8)
    assert cached < recompute / 10, (
        f"the cache must dominate for long generations: {cached:,} vs "
        f"{recompute:,} interactions. Recompute is quadratic in the prefix per step; "
        "the cache is linear.")
    assert recompute_work(128, 1, 8) > 3.5 * recompute_work(64, 1, 8), (
        "prefill is quadratic in prompt length, so doubling the prompt should "
        "nearly quadruple the work")


# ---------------------------------------------------------------------------
# RoPE
# ---------------------------------------------------------------------------

def check_rope_invariants() -> None:
    from rope import apply_rope, rope_freqs

    dim, seq = 8, 48
    freqs = rope_freqs(dim, seq)
    q = [math.sin(j + 1) for j in range(dim)]
    k = [math.cos(2 * j + 1) for j in range(dim)]

    def norm(v: List[float]) -> float:
        return math.sqrt(sum(x * x for x in v))

    assert max(abs(a - b) for a, b in zip(apply_rope(q, 0, freqs), q)) < 1e-12, \
        "position 0 must be the identity rotation"

    for pos in (0, 1, 7, 40):
        assert abs(norm(apply_rope(q, pos, freqs)) - norm(q)) < 1e-9, (
            f"rotation must preserve the norm; position {pos} changed it")

    distance = 7
    dots = [
        sum(a * b for a, b in zip(apply_rope(q, p, freqs),
                                  apply_rope(k, p + distance, freqs)))
        for p in range(seq - distance)
    ]
    spread = max(dots) - min(dots)
    assert spread < 1e-9, (
        f"dot(q@p, k@(p+{distance})) must depend only on the distance, not on p, "
        f"but it varied by {spread:.2e}. Your frequencies are wrong, and long-context "
        "behaviour will degrade in a way short tests never reveal.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("tokenizer.py", "pair counts and non-overlapping merges", check_bpe_pairs),
    ("tokenizer.py", "deterministic training and compression", check_bpe_training),
    ("tokenizer.py", "rank-ordered encode and round-trip", check_bpe_encode_order),
    ("attention.py", "stable softmax", check_attention_softmax),
    ("attention.py", "attention weights and the causal mask", check_attention_causal),
    ("sampling.py", "temperature and hard greedy", check_sampling_temperature),
    ("sampling.py", "top-k", check_sampling_top_k),
    ("sampling.py", "top-p keeps the crossing token", check_sampling_top_p),
    ("sampling.py", "seeded sampling is reproducible", check_sampling_determinism),
    ("kv_cache.py", "cache append and shape", check_kv_cache_object),
    ("kv_cache.py", "cached output is bit-exact", check_kv_cache_exactness),
    ("kv_cache.py", "the cost model: linear vs quadratic", check_kv_cache_cost),
    ("rope.py", "norm and relative-position invariants", check_rope_invariants),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

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
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}LLM From Scratch — progress check{RESET}")
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
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you built the core of an LLM.{RESET}")
        print(f"  {GREY}Run each solution's demo to see the measurements, then{RESET}")
        print(f"  {GREY}move on to context-caching/ to wire them into a model.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
