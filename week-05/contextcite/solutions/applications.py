"""
Step 7 — What attribution is FOR. Complete Solution.

Paper: ContextCite, section 5 — three applications:
  1. Verifying generated statements
  2. Pruning the context to improve response quality
  3. Detecting poisoning attacks

Plus the experiment that justifies random-subset ablation over leave-one-out.
"""

from typing import List, Optional, Sequence, Tuple

from contextcite import ContextCiter
from logit_probs import response_score
from partition import ContextPartitioner


# ---------------------------------------------------------------------------
# 1. Verification
# ---------------------------------------------------------------------------

def verify_tokens(citer, threshold: float = 1.0
                  ) -> List[Tuple[str, int, float, bool]]:
    """For each response token: its best source, that score, and whether it
    clears `threshold`.

    A token no source can explain is exactly what a hallucination looks like
    from the outside: the model produced it, but ablating the context does not
    move its probability, so nothing in the context caused it.

    The threshold is a judgement call, not a discovered constant. Calibrate it
    on responses you know to be grounded before trusting it.
    """
    results = []
    for index, token in enumerate(citer.response):
        best = citer.attribute_token(index, top_k=1)[0]
        results.append((token, best.index, best.score, best.score >= threshold))
    return results


# ---------------------------------------------------------------------------
# 2. Context pruning
# ---------------------------------------------------------------------------

def prune_context(citer, keep_top_k: int = 2) -> Tuple[str, List[int]]:
    """Keep only the top-k attributed sources. Returns (context, kept indices).

    Sources are re-sorted into their original order so the pruned context still
    reads in sequence.
    """
    kept = sorted(a.index for a in citer.attribute(top_k=keep_top_k))
    mask = [i in set(kept) for i in range(citer.num_sources)]
    return citer.partitioner.build(mask), kept


# ---------------------------------------------------------------------------
# 3. Poisoning detection
# ---------------------------------------------------------------------------

# An effective poison has to WIN the model's attention, not just sit in the
# context. This one repeats the query's own terms ("GPUs", "training") so the
# model rates it highly relevant, and repeats its payload so the payload words
# dominate. A first attempt that merely said "ignore all other sources..."
# changed nothing at all — the attack has to succeed before detection is even
# a meaningful question.
POISON = ("Training used H200 GPUs; the H200 GPUs were the only GPUs used "
          "for training.")


def poison_context(context: str, poison: str = POISON,
                   position: int = 2) -> str:
    """Splice a malicious sentence into the context at a given source index."""
    partitioner = ContextPartitioner(context)
    parts = partitioner.sources
    parts.insert(position, poison)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# The case against leave-one-out
# ---------------------------------------------------------------------------

def leave_one_out_scores(citer) -> List[float]:
    """Drop in response score when each source is removed alone."""
    full = response_score(citer.model, citer.context, citer.response)
    scores = []
    for index in range(citer.num_sources):
        mask = [i != index for i in range(citer.num_sources)]
        ablated = response_score(citer.model, citer.partitioner.build(mask),
                                 citer.response)
        scores.append(full - ablated)
    return scores


def _demo() -> None:
    from toy_lm import CONTEXT, GROUND_TRUTH_SOURCE, QUERY, ToyLM

    model = ToyLM(CONTEXT, QUERY)
    citer = ContextCiter(model, CONTEXT, QUERY)

    print("=" * 68)
    print("1. VERIFICATION — which tokens does the context actually support?")
    print("=" * 68)
    print(f"response: {' '.join(citer.response)}\n")
    print(f"{'token':<16}{'source':>8}{'score':>9}  supported")
    for token, source, score, supported in verify_tokens(citer, threshold=1.0):
        print(f"{token:<16}{source:>8}{score:>9.2f}  {'yes' if supported else 'NO'}")
    print("\nEvery token here is grounded. The interesting case is the one that")
    print("is not — see the poisoning section, where the model states something")
    print("that IS in the context but should not be trusted. Attribution finds")
    print("provenance, not truth.")

    print("\n" + "=" * 68)
    print("2. PRUNING — how much context can we throw away?")
    print("=" * 68)
    full_score = response_score(model, CONTEXT, citer.response)
    print(f"{'kept sources':>13}{'chars':>8}{'score':>10}   response")
    print(f"{'all 8':>13}{len(CONTEXT):>8}{full_score:>10.2f}   "
          f"{' '.join(model.generate(CONTEXT)[:6])}...")
    for k in (1, 2, 3):
        pruned, kept = prune_context(citer, keep_top_k=k)
        score = response_score(model, pruned, citer.response)
        preview = " ".join(model.generate(pruned)[:6])
        print(f"{str(kept):>13}{len(pruned):>8}{score:>10.2f}   {preview}...")
    print("\nOne source out of eight — 16% of the characters — preserves the")
    print("answer and RAISES its probability, because the other seven sentences")
    print("were competing for probability mass. That is the pruning win: less")
    print("context, less cost, and a more confident answer.")

    print("\n" + "=" * 68)
    print("3. POISONING — can we find the sentence that hijacked the answer?")
    print("=" * 68)
    poisoned = poison_context(CONTEXT, position=2)
    poisoned_model = ToyLM(poisoned, QUERY)
    poisoned_citer = ContextCiter(poisoned_model, poisoned, QUERY)

    print(f"injected at source 2: {POISON!r}\n")
    print(f"clean response:    {' '.join(citer.response)}")
    print(f"poisoned response: {' '.join(poisoned_citer.response)}")
    print("\nThe attack worked: the answer now leads with the injected claim.\n")

    print("attributing the WHOLE response:")
    for attribution in poisoned_citer.attribute(top_k=2):
        flag = "  <- THE POISON" if attribution.index == 2 else ""
        print(f"  {attribution}{flag}")
    whole = poisoned_citer.attribute(top_k=1)[0]
    print(f"top source: {whole.index} -> "
          f"{'detected' if whole.index == 2 else 'MISSED'}")
    print("Diluted: only the first few tokens came from the poison, and the")
    print("other eight outvote them in the aggregate.\n")

    print("attributing per token:")
    print(f"{'':>3} {'token':<14}{'source':>8}{'score':>9}")
    for index, token in enumerate(poisoned_citer.response):
        best = poisoned_citer.attribute_token(index, top_k=1)[0]
        flag = "  <- POISON" if best.index == 2 else ""
        print(f"{index:>3} {token:<14}{best.index:>8}{best.score:>9.2f}{flag}")

    print("\nattributing the span that makes the claim, tokens [0, 4):")
    for attribution in poisoned_citer.attribute(0, 4, top_k=3):
        flag = "  <- THE POISON" if attribution.index == 2 else ""
        print(f"  {attribution}{flag}")
    span_top = poisoned_citer.attribute(0, 4, top_k=1)[0]
    print(f"\ntop source for the span: {span_top.index}; the poison sits at 2 -> "
          f"{'DETECTED' if span_top.index == 2 else 'missed'}")
    print("\nThis is the lesson of the section, and the reason the paper supports")
    print("attributing arbitrary SPANS: attribute the clause that makes the")
    print("claim, not the whole answer. Averaging over a long response buries")
    print("the one sentence you needed to find. And note these span refits cost")
    print("no extra model calls — the logit-probabilities were cached.")

    print("\n" + "=" * 68)
    print("4. WHY RANDOM SUBSETS, NOT LEAVE-ONE-OUT")
    print("=" * 68)
    sentences = ContextPartitioner(CONTEXT).sources
    duplicated = " ".join(sentences + [sentences[GROUND_TRUTH_SOURCE]])
    dup_model = ToyLM(duplicated, QUERY)
    dup_citer = ContextCiter(dup_model, duplicated, QUERY)
    copies = (GROUND_TRUTH_SOURCE, len(sentences))
    print(f"the answer sentence now appears TWICE, at sources {copies[0]} and "
          f"{copies[1]}\n")

    loo = leave_one_out_scores(dup_citer)
    attributions = {a.index: a.score for a in dup_citer.attribute()}
    print(f"{'source':>8}{'leave-one-out':>16}{'ContextCite':>14}")
    for index in range(dup_citer.num_sources):
        flag = "  <- a copy" if index in copies else ""
        print(f"{index:>8}{loo[index]:>16.2f}{attributions[index]:>14.2f}{flag}")

    loo_max = max(loo[i] for i in copies)
    cc_max = max(attributions[i] for i in copies)
    print(f"\nbest leave-one-out score among the copies: {loo_max:.2f}")
    print(f"best ContextCite score among the copies:   {cc_max:.2f}")
    print("\nLeave-one-out removes one copy, the other still answers the query,")
    print("and it concludes NEITHER matters. Random subsets ablate both together")
    print("in roughly a quarter of draws, so the regression sees what happens")
    print("when the answer is genuinely absent. This is the whole argument for")
    print("the sampling design in ablation.py.")


if __name__ == "__main__":
    _demo()
