"""Hybrid (fusion) retrieval — the FUSION stage of RAG project 1.

This stage sits on top of the two retrievers already built: BM25 (lexical, `../bm25`)
and LSA (dense, `../lsa`). It does not look at documents directly for the ranking
logic; it asks each stage for its ranking of the *same* corpus for the *same* query
and combines those rankings. The shared step-0 evaluation set (`../eval-set`) is what
makes the comparison meaningful: every stage and every fusion method is measured on
exactly the same queries and qrels.

Two combination strategies are implemented, because they fail in different ways:

  * Reciprocal Rank Fusion (RRF, Cormack et al., 2009). Only the *order* a stage puts
    documents in matters, never the magnitude of its scores. Robust to the fact that a
    BM25 score and a cosine similarity are not comparable as numbers.
  * Weighted score fusion. Each stage's per-query scores are normalised (min-max or
    z-score) so they become comparable, then combined with weights. Uses magnitude
    information, so it can be better when both stages are well calibrated and worse
    when one stage's scores are dominated by a few outliers.

DESIGN DECISION - the fusion input is a *ranking*, not a document. A stage is adapted
    only through its ``scored`` method (key, score pairs, best first). BM25 and LSA are
    therefore free to change their internals without touching this module, and the
    fusion logic is testable on hand-built rankings. Cost: a stage that returns only
    doc_ids is re-scored to recover magnitudes; here the LSA scores are recomputed
    exactly from its fitted model and BM25 is re-derived from the corpus with the
    standard Okapi formula and the same tokeniser.

DESIGN DECISION - RRF uses ``score(d) = sum_r w_r / (k + rank_r(d))`` with 1-based
    ranks and ``k = 60`` (the value from the original paper). Ties break by doc_id
    ascending so runs are reproducible.
    Cost: RRF throws away score magnitude entirely, so a document that one stage ranks
    first with a tiny score and another ranks first with a huge score gets the same
    fused score as a unanimous #1.

DESIGN DECISION - ``weighted_fusion`` min-max normalises each stage's score list to
    [0, 1] per query before weighting, and a document a stage did not return
    contributes 0.0 from that stage (not the stage's minimum). z-score is offered as
    the alternative. Ties break by doc_id ascending.
    Cost: min-max is sensitive to a single high outlier (it compresses everything
    else); z-score keeps more spread but can go negative, which is only meaningful if
    a missing document is treated as exactly 0.0, as it is here.

DESIGN DECISION - abstention is inherited: a query for which *both* stages return
    nothing makes the hybrid return ``[]`` (abstain). A query for which only one stage
    has any candidate still returns the other stage's hits — that asymmetry is the
    whole point of hybrid search.

DESIGN DECISION - the paired comparison is a per-query sign test (wins/losses/ties and
    an exact two-sided binomial p-value). It compares fusion with each single stage on
    the same queries, so it is paired and does not assume any distribution of the
    metric across queries. Cost: with few queries the test has little power; that is
    reported rather than hidden.

No third-party imports: the eval harness forbids them. Run the demo with
``python3 solutions/fusion.py``.
"""
from __future__ import annotations

import math
import pathlib
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# small helpers shared with the sibling stages
# ---------------------------------------------------------------------------

_FILTER_KEYS = ("region", "year", "department", "access_level")

STAGE_ORDER = ("bm25", "lsa")  # index 0 is lexical, 1 is dense; weights follow this order
RRF_K = 60
BM25_K1 = 1.5
BM25_B = 0.75
CANDIDATE_DEPTH = 100


def _as_keys(ranking):
    """Normalise a ranking to a plain list of keys.

    Accepts either a list of keys or a list of ``(key, score)`` pairs (each pair a
    list or tuple), so a stage may expose either form.
    """
    keys = []
    for item in ranking:
        if isinstance(item, (tuple, list)):
            keys.append(item[0])
        else:
            keys.append(item)
    return keys


def _passes_filters(doc, filters):
    """Same metadata-filter convention as BM25 and LSA."""
    if not filters:
        return True
    for key in _FILTER_KEYS:
        if key not in filters:
            continue
        value = filters[key]
        if key == "year":
            if doc.get("date", "")[:4] != str(value):
                return False
        elif doc.get(key) != value:
            return False
    return True


def _sort_ranked(scored):
    """Sort (key, score) pairs by score descending, then key ascending; drop <= 0."""
    pairs = [(key, score) for key, score in scored if score > 0.0]
    pairs.sort(key=lambda pair: (-pair[1], pair[0]))
    return pairs


# ---------------------------------------------------------------------------
# the two fusion functions
# ---------------------------------------------------------------------------

def rrf(rankings, k=RRF_K, weights=None):
    """Reciprocal Rank Fusion of several rankings.

    ``rankings`` is a list of ranked lists; each list may be keys or ``(key, score)``
    pairs. ``weights[r]`` multiplies the contribution of ranking ``r`` (default all
    1.0). Returns a fused list of ``(key, score)`` sorted best first, where

        score(d) = sum over rankings r that contain d of  w_r / (k + rank_r(d))

    ``rank_r(d)`` is 1-based (the first item of a ranking has rank 1). Ties are broken
    by ``key`` ascending. Keys absent from a ranking simply do not receive that
    ranking's term.
    """
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights must have one entry per ranking")

    scores = {}
    for ranking, weight in zip(rankings, weights):
        for position, key in enumerate(_as_keys(ranking), start=1):
            scores[key] = scores.get(key, 0.0) + weight / (k + position)
    return _sort_ranked(scores.items())


def normalize_scores(scores, method="minmax"):
    """Normalise a score collection. Documented behaviour:

    * ``method="minmax"``: ``(s - min) / (max - min)``, so the lowest becomes 0.0 and
      the highest 1.0. A constant collection (max == min) maps every value to 0.0
      instead of dividing by zero.
    * ``method="zscore"``: ``(s - mean) / std`` (population standard deviation). A
      zero-variance collection maps every value to 0.0.

    ``scores`` may be a mapping ``key -> score`` (returns a new mapping), a sequence
    of ``(key, score)`` pairs (returns a mapping), or a sequence of plain numbers
    (returns a list of numbers). Keys are preserved exactly.
    """
    mapping = None
    if isinstance(scores, dict):
        mapping = list(scores.items())
    elif scores and all(isinstance(item, (tuple, list)) and len(item) == 2 for item in scores):
        mapping = [(item[0], item[1]) for item in scores]
    else:
        values = [float(v) for v in scores]

    if mapping is not None:
        keys = [key for key, _ in mapping]
        values = [float(value) for _, value in mapping]
    else:
        keys = None

    if not values:
        return {} if keys is not None else []

    if method == "minmax":
        low = min(values)
        high = max(values)
        span = high - low
        out = [0.0] * len(values) if span == 0.0 else [(v - low) / span for v in values]
    elif method == "zscore":
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)
        out = [0.0] * len(values) if std == 0.0 else [(v - mean) / std for v in values]
    else:
        raise ValueError(f"unknown normalisation method: {method!r} (use 'minmax' or 'zscore')")

    if keys is None:
        return out
    return dict(zip(keys, out))


def weighted_fusion(score_lists, weights, norm="minmax"):
    """Normalise each retriever's per-query scores, then weight and sum them.

    ``score_lists`` is a list (one per retriever) of mappings ``key -> raw score`` or
    of ``(key, score)`` pairs. Each list is normalised on its own by
    :func:`normalize_scores` with ``norm``, multiplied by the matching entry in
    ``weights``, and summed. A key a retriever did not score contributes 0.0 from that
    retriever. Returns ``(key, score)`` pairs sorted best first, ties by key ascending.
    """
    if len(weights) != len(score_lists):
        raise ValueError("weights must have one entry per retriever")

    combined = {}
    for scores, weight in zip(score_lists, weights):
        normalised = normalize_scores(scores, method=norm)
        for key, value in normalised.items():
            combined[key] = combined.get(key, 0.0) + weight * value
    return sorted(combined.items(), key=lambda pair: (-pair[1], pair[0]))


# ---------------------------------------------------------------------------
# stage adapters: recover comparable scores from the sibling retrievers
# ---------------------------------------------------------------------------

class _Bm25Stage:
    """Okapi BM25 scoring re-derived from the corpus, matching the sibling BM25.

    The sibling ``bm25`` module exposes rankings, not a stable ``score`` hook, so the
    same smoothed idf and the standard saturation/normalisation formula are re-applied
    here with the shared tokeniser. ``bm25.py`` is imported for its ``tokenize`` so the
    two cannot drift apart.
    """

    def __init__(self, documents, tokenize, k1=BM25_K1, b=BM25_B):
        self.documents = list(documents)
        self.tokenize = tokenize
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(str(doc.get("title", "")) + " " + str(doc.get("body", "")))
                       for doc in self.documents]
        self.lengths = [len(toks) for toks in self.tokens]
        self.avgdl = (sum(self.lengths) / len(self.lengths)) if self.lengths else 1.0
        if self.avgdl == 0.0:
            self.avgdl = 1.0
        n_docs = len(self.documents)
        document_freq = Counter()
        for toks in self.tokens:
            for term in set(toks):
                document_freq[term] += 1
        self.idf = {term: math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                    for term, df in document_freq.items()}
        self.term_freq = [Counter(toks) for toks in self.tokens]

    def scored(self, query, depth=CANDIDATE_DEPTH, filters=None):
        text = query.get("text", "") if isinstance(query, dict) else query
        if filters is None and isinstance(query, dict):
            filters = query.get("filters", {})
        query_terms = self.tokenize(text)
        scored = []
        for index, doc in enumerate(self.documents):
            if not _passes_filters(doc, filters):
                continue
            length = self.lengths[index] or 1
            score = 0.0
            for term in query_terms:
                idf = self.idf.get(term)
                if idf is None:
                    continue
                freq = self.term_freq[index].get(term, 0)
                if not freq:
                    continue
                score += idf * (freq * (self.k1 + 1)) / (
                    freq + self.k1 * (1 - self.b + self.b * length / self.avgdl))
            if score > 0.0:
                scored.append((doc["doc_id"], score))
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[:depth]


class _LsaStage:
    """Thin adapter over the sibling ``LsaRetriever`` that exposes exact scores."""

    def __init__(self, documents, module, n_components=None):
        self.module = module
        if n_components is None:
            self.retriever = module.LsaRetriever(documents)
        else:
            self.retriever = module.LsaRetriever(documents, n_components)
        self.documents = self.retriever.documents

    def scored(self, query, depth=CANDIDATE_DEPTH, filters=None):
        text = query.get("text", "") if isinstance(query, dict) else query
        if filters is None and isinstance(query, dict):
            filters = query.get("filters", {})
        embedding = self.module.embed_query(text, self.retriever.model)
        scored = []
        for doc in self.documents:
            if not _passes_filters(doc, filters):
                continue
            doc_embedding = self.retriever._embeddings.get(doc["doc_id"], [])
            score = sum(a * b for a, b in zip(embedding, doc_embedding))
            if score > 0.0:
                scored.append((doc["doc_id"], score))
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[:depth]


def _sibling_solutions(name):
    """Locate ``../<name>/solutions`` relative to this file or its parent module."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / name / "solutions",
        here.parent / name / "solutions",
    ]
    for candidate in candidates:
        if (candidate / f"{name}.py").is_file():
            return candidate
    raise FileNotFoundError(
        f"cannot find the sibling {name!r} stage. Expected ../{name}/solutions "
        f"relative to {here}.")


def _import_sibling(name):
    path = str(_sibling_solutions(name))
    if path not in sys.path:
        sys.path.insert(0, path)
    import importlib

    return importlib.import_module(name)


def load_stages(docs, n_components=None):
    """Build the two sibling retrievers on ``docs`` and return the stage adapters.

    Returns a dict ``{"bm25": ..., "lsa": ..., "modules": {"bm25": ..., "lsa": ...}}``
    where each stage exposes ``scored(query, depth, filters) -> [(doc_id, score)]``.
    """
    documents = docs["documents"] if isinstance(docs, dict) else docs
    documents = list(documents)
    bm25_module = _import_sibling("bm25")
    lsa_module = _import_sibling("lsa")

    bm25_stage = _Bm25Stage(documents, bm25_module.tokenize)
    lsa_stage = _LsaStage(documents, lsa_module, n_components)
    return {
        "bm25": bm25_stage,
        "lsa": lsa_stage,
        "modules": {"bm25": bm25_module, "lsa": lsa_module},
    }


class HybridRetriever:
    """Fuse the BM25 and LSA rankings, with the same filtering/abstention conventions.

    ``__init__`` accepts a corpus (the dict from ``corpus.generate_corpus`` or a list of
    documents) and builds both sibling stages on it. ``retrieve`` asks each stage for a
    deep candidate list, fuses it with ``method`` ("rrf" or "weighted"), and returns up
    to ``k`` doc_ids best first. ``[]`` means "abstain": both stages found nothing.
    """

    def __init__(self, docs, n_components=None, stages=None):
        documents = docs["documents"] if isinstance(docs, dict) else docs
        self.documents = list(documents)
        if stages is None:
            stages = load_stages(self.documents, n_components=n_components)
        self.stages = stages
        self._by_id = {doc["doc_id"]: doc for doc in self.documents}

    def _score_lists(self, query, depth, filters):
        score_lists = []
        for name in STAGE_ORDER:
            score_lists.append(dict(self.stages[name].scored(query, depth=depth, filters=filters)))
        return score_lists

    def retrieve(self, query, k=10, method="rrf", weights=None, filters=None,
                 depth=CANDIDATE_DEPTH):
        """Return up to ``k`` doc_ids for ``query``; ``[]`` means abstain.

        ``query`` is the eval set's query dict (``text`` + ``filters``) or a raw string;
        an explicit ``filters`` argument overrides the query's own filters.
        ``method`` is ``"rrf"`` or ``"weighted"``; ``weights`` follows
        :data:`STAGE_ORDER` (BM25 first), defaulting to equal weights.
        """
        if weights is None:
            weights = [1.0] * len(STAGE_ORDER)
        score_lists = self._score_lists(query, depth, filters)
        if method == "rrf":
            rankings = [list(scores) for scores in score_lists]
            fused = rrf(rankings, weights=weights)
        elif method == "weighted":
            fused = weighted_fusion(score_lists, weights, norm="minmax")
        else:
            raise ValueError(f"unknown fusion method: {method!r} (use 'rrf' or 'weighted')")
        return [key for key, _score in fused[:k]]


# ---------------------------------------------------------------------------
# evaluation: same metric shape as the sibling stages, plus paired comparisons
# ---------------------------------------------------------------------------

def _eval_set_solutions():
    """Locate ``../eval-set/solutions`` from either this file or its parent."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / "eval-set" / "solutions",
        here.parent / "eval-set" / "solutions",
    ]
    for candidate in candidates:
        if (candidate / "metrics.py").is_file():
            return candidate
    raise FileNotFoundError(
        f"cannot find the shared eval set at ../eval-set/solutions relative to {here}.")


def _import_metrics():
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import importlib

    return importlib.import_module("metrics")


def _flatten_queries(queries):
    if isinstance(queries, dict):
        order = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
        return [q for family in order for q in queries.get(family, [])]
    return list(queries)


def _binom_two_sided(wins, losses):
    """Exact two-sided sign-test p-value under p = 0.5."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = min(wins, losses)
    cumulative = sum(math.comb(n, i) for i in range(tail + 1)) / (2 ** n)
    return min(1.0, 2.0 * cumulative)


def paired_comparison(fusion_per_query, single_per_query, qids, metric="recall@k"):
    """Paired per-query comparison of two predictions over the same ``qids``.

    Returns wins (fusion > single), losses, ties, the win rate over decided pairs, the
    mean per-query difference, and the exact two-sided sign-test p-value.
    """
    wins = losses = ties = 0
    differences = []
    for qid in qids:
        a = fusion_per_query.get(qid, {}).get(metric, 0.0)
        b = single_per_query.get(qid, {}).get(metric, 0.0)
        differences.append(a - b)
        if a > b:
            wins += 1
        elif a < b:
            losses += 1
        else:
            ties += 1
    decided = wins + losses
    return {
        "metric": metric,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "n": len(qids),
        "win_rate": (wins / decided) if decided else 0.0,
        "mean_diff": (sum(differences) / len(differences)) if differences else 0.0,
        "p_value": _binom_two_sided(wins, losses),
    }


def evaluate(corpus, queries, k=10, weights=None, n_components=None, norm="minmax"):
    """Score the shared eval set with RRF, weighted fusion, BM25 alone and LSA alone.

    Returns the dict ``metrics.evaluate`` produces for reciprocal rank fusion (so the
    shape matches the sibling stages: ``overall``, ``by_type``, ``per_query``,
    ``abstention``), with two extra keys:
      * ``"methods"``: the full metrics dict for ``rrf``, ``weighted``, ``bm25`` and
        ``lsa``.
      * ``"paired"``: ``{"rrf"|"weighted": {"bm25"|"lsa": <paired_comparison>}}`` plus
        ``"by_type"`` with the same nested shape per query family.
    """
    metrics = _import_metrics()
    flat = _flatten_queries(queries)
    if weights is None:
        weights = [1.0] * len(STAGE_ORDER)

    stages = load_stages(corpus, n_components=n_components)
    hybrid = HybridRetriever(corpus, stages=stages)

    rrf_preds = {q["qid"]: hybrid.retrieve(q, k=k, method="rrf", weights=weights) for q in flat}
    weighted_preds = {q["qid"]: hybrid.retrieve(q, k=k, method="weighted", weights=weights)
                      for q in flat}
    bm25_preds = {q["qid"]: [key for key, _ in stages["bm25"].scored(q, depth=k)]
                  for q in flat}
    lsa_preds = {q["qid"]: [key for key, _ in stages["lsa"].scored(q, depth=k)] for q in flat}

    methods = {
        "rrf": metrics.evaluate(rrf_preds, flat, k=k),
        "weighted": metrics.evaluate(weighted_preds, flat, k=k),
        "bm25": metrics.evaluate(bm25_preds, flat, k=k),
        "lsa": metrics.evaluate(lsa_preds, flat, k=k),
    }

    result = dict(methods["rrf"])
    result["methods"] = methods
    result["paired"] = _paired_overall(methods, flat)
    result["paired_by_type"] = _paired_by_type(methods, flat)
    return result


def _paired_overall(methods, flat):
    qids = [q["qid"] for q in flat]
    paired = {}
    for method in ("rrf", "weighted"):
        paired[method] = {}
        for stage in ("bm25", "lsa"):
            paired[method][stage] = paired_comparison(
                methods[method]["per_query"], methods[stage]["per_query"], qids)
    return paired


def _paired_by_type(methods, flat):
    by_type = {}
    for method in ("rrf", "weighted"):
        by_type[method] = {}
        for stage in ("bm25", "lsa"):
            by_type[method][stage] = {}
            for family in ("lexical", "semantic", "filtered", "multi_hop", "no_answer"):
                qids = [q["qid"] for q in flat if q.get("type") == family]
                if qids:
                    by_type[method][stage][family] = paired_comparison(
                        methods[method]["per_query"], methods[stage]["per_query"], qids)
    return by_type


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

def _row(result, family):
    if family == "overall":
        return result["overall"]
    return result["by_type"].get(family, {})


def demo():
    """Print the honest fusion-vs-single-stage table with paired win/loss counts."""
    sys.dont_write_bytecode = True
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)

    from corpus import generate_corpus
    from queries import all_queries, build_query_sets

    corpus = generate_corpus(0)
    query_sets = build_query_sets(corpus)
    queries = all_queries(query_sets)
    result = evaluate(corpus, query_sets, k=10)
    methods = result["methods"]

    families = ("lexical", "semantic", "filtered", "multi_hop", "no_answer", "overall")
    print(f"seed 0, {len(corpus['documents'])} documents, {len(queries)} queries")
    header = (f"{'family':<12}{'BM25 r@10':>11}{'LSA r@10':>10}{'RRF r@10':>10}"
              f"{'WT r@10':>9}")
    print(header)
    for family in families:
        b = _row(methods["bm25"], family).get("recall@k", 0.0)
        l = _row(methods["lsa"], family).get("recall@k", 0.0)
        r = _row(methods["rrf"], family).get("recall@k", 0.0)
        w = _row(methods["weighted"], family).get("recall@k", 0.0)
        print(f"{family:<12}{b:>11.3f}{l:>10.3f}{r:>10.3f}{w:>9.3f}")

    print("\npaired per-query, RRF vs each single stage (metric recall@10):")
    print(f"  {'family':<12}{'vs BM25 W/L/T':>18}{'vs LSA W/L/T':>16}")
    for family in families:
        row = {}
        for stage in ("bm25", "lsa"):
            if family == "overall":
                stats = result["paired"]["rrf"][stage]
            else:
                stats = result["paired_by_type"]["rrf"][stage].get(family)
            if stats is not None:
                row[stage] = f"{stats['wins']}/{stats['losses']}/{stats['ties']}"
        print(f"  {family:<12}{row.get('bm25', '-'):>18}{row.get('lsa', '-'):>16}")
    print("  W/L/T = fusion better / worse / equal on that query; ties are queries where "
          "both retrieve the same documents.")
    print("  the numbers are reported as measured: fusion is not assumed to win.")


if __name__ == "__main__":
    demo()
