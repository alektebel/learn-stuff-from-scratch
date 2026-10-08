"""Reranking — RAG project 3 (retrieve 100, rerank to 5).

The first stage (`../bm25`, project 1's lexical retriever) proposes a deep candidate
list for a query; this module reorders *that list only* down to a short list with a
reranker trained here. Two facts drive every design decision:

  * The reranker can only reorder what the first stage returned. If the relevant
    document is not in the first stage's candidate list, no reranker can recover it:
    ``recall@100`` of the first stage is the **ceiling** of any reranked result. The
    demo and check.py print both numbers and make the ceiling concrete on a corpus
    large enough that the first stage actually truncates.
  * The reranker is trained on one set of queries and evaluated on a **disjoint** set,
    or the number it reports is training accuracy in disguise.

DESIGN DECISION - the reranker is a logistic-regression ranker trained by deterministic
    gradient descent over hand-built features, not a neural cross-encoder.
    The repository's intended trainer is ``ml-systems/framework`` (a numpy tensor
    library). This environment has no numpy and no pip (Python 3.14), so the framework
    cannot be imported. A logistic model over nine interpretable features trains in
    milliseconds, has no random state to seed, and its weights can be read off and
    explained. Cost: it cannot learn feature interactions the way an MLP or a
    cross-encoder would, so where two documents differ only by a conjunction of
    features the linear model cannot separate them. That is a deliberate, visible
    limitation; ``ml-systems/framework`` is the alternative path once numpy exists.

DESIGN DECISION - features are computed from the query and the document, never from
    the candidate's rank or position.
    A feature that encodes "is this the 3rd candidate" teaches the model the first
    stage's ordering rather than relevance, and would not transfer to a different
    first stage. Every feature here is a property of (query, document). Cost: the
    model cannot simply imitate a strong first-stage score; it has to combine the
    score with text evidence.

DESIGN DECISION - training examples are (feature vector, binary label) pairs, and only
    documents inside the first-stage candidate list are used.
    This is the standard pointwise learning-to-rank setup. Cost: many negatives share
    the list with few positives, so the positive class is rare; the fixed step-size
    gradient descent still converges because the features are already in [0, 1] and the
    loss is convex.

DESIGN DECISION - ``is_current`` is a feature (0.0 for a superseded document).
    The evaluation set's single most fragile invariant is that superseded documents are
    never relevant, even though their text still matches. Without this feature the
    reranker would happily promote a stale policy that the first stage ranked highly.
    Cost: it uses document metadata, so a collection without revision history loses a
    feature; the other eight still fire, and the checker's toy corpus exercises it.

DESIGN DECISION - the train/eval split is by whole queries, alternating within each
    family, and the two sets are asserted disjoint.
    Splitting by document would leak: the same query's other relevant documents would
    be in the training set, so the model would memorise the query. Splitting by query
    is the only split that measures generalisation. Alternating within a family keeps
    every family represented on both sides even when a family has few queries. Cost:
    with a handful of queries per family the held-out estimate has wide error bars; the
    numbers are reported as measured, not asserted to improve.

No third-party imports. Run the demo with ``python3 solutions/rerank.py``.
"""
from __future__ import annotations

import math
import os
import pathlib
import re
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# constants and the feature vector
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"[a-z0-9]+")
_FILTER_KEYS = ("region", "year", "department", "access_level")
_FAMILY_ORDER = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")

CANDIDATE_DEPTH = 100  # the first stage proposes this many; recall@100 is the ceiling
RERANK_DEPTH = 5       # the reranker returns this many
_EPS = 1e-12
_DEFAULT_AVG_LEN = 40.0

FEATURE_NAMES = (
    "stage_score",      # first-stage score, squashed to (-1, 1)
    "lexical_cosine",   # bag-of-words cosine between query and document
    "term_coverage",    # distinct query terms present in the document
    "idf_coverage",     # coverage weighted by the term's inverse document frequency
    "exact_phrase",     # 1.0 if the whole query appears contiguously in the text
    "title_match",      # fraction of query terms that appear in the title
    "length_ratio",     # document length / corpus average, capped to [0, 1]
    "dense_cosine",     # latent-semantic cosine (sibling LSA), squashed to (-1, 1)
    "is_current",       # 0.0 if the document is superseded, else 1.0
)


def tokenize(text):
    """Lower-cased alphanumeric tokens, the same tokeniser as BM25 and LSA."""
    return TOKEN_RE.findall(str(text).lower())


def _query_text(query):
    # TODO: Return query['text'] for a dict query, else str(query).
    raise NotImplementedError("_query_text")


def _squash(value):
    """Map any real number into (-1, 1); non-finite input becomes 0.0."""
    # TODO: Map a real number into (-1, 1) with x/(1+abs(x)); non-finite becomes 0.0.
    raise NotImplementedError("_squash")


def _cosine(left_tokens, right_tokens):
    """Cosine of the term-frequency vectors of two token lists."""
    # TODO: Cosine of the term-frequency vectors of two token lists; 0.0 if either is empty or has zero norm.
    raise NotImplementedError("_cosine")


def _phrase_hit(query_text, document_text):
    """1.0 if the tokenised query occurs contiguously in the tokenised document."""
    # TODO: Tokenise query and document, join with spaces, and return 1.0 if the query string occurs contiguously in the document string.
    raise NotImplementedError("_phrase_hit")


def features(query, doc, context=None):
    """Return the fixed-length feature vector for ``(query, doc)`` as a list of floats.

    The length is always ``len(FEATURE_NAMES)`` and every value is finite. ``context``
    is any object exposing ``stage_score(query_text, doc)``, ``dense_cosine(query_text,
    doc)``, ``idf(term)`` and ``avg_length`` (see :class:`FeatureContext`); when it is
    omitted the context-dependent features fall back to finite constants and the
    text-only features still vary with the document.
    """
    # TODO: Build the values dict keyed by FEATURE_NAMES: stage_score and dense_cosine squashed from the context (0.0 without one), lexical_cosine, term_coverage, idf_coverage via context.idf (1.0 without one), exact_phrase, title_match, length_ratio against context.avg_length (or the default), and is_current from the absence of superseded_by. Return a list in FEATURE_NAMES order.
    raise NotImplementedError("features")


class FeatureContext:
    """Everything ``features`` needs that is not inside a single document.

    ``stage_scorer`` and ``dense_scorer`` are callables ``(query_text, doc) -> float``.
    When they are omitted the first-stage feature is a local Okapi BM25 over the same
    corpus (so the module works with no sibling stage present) and the dense feature is
    0.0. ``idf`` is a mapping term -> idf computed from the corpus when not supplied.
    """

    def __init__(self, documents, stage_scorer=None, dense_scorer=None, idf=None,
                 avg_length=None):
        # TODO: Store the documents, tokens, term frequencies and lengths; set avg_length (from the argument, else the mean length); build or store idf; and keep the stage/dense scorers, defaulting to the local BM25 and a constant 0.0.
        raise NotImplementedError("FeatureContext.__init__")

    def _compute_idf(self):
        # TODO: Return term -> smoothed BM25 idf log(1+(N-df+0.5)/(df+0.5)) over the stored document tokens.
        raise NotImplementedError("FeatureContext._compute_idf")

    def idf(self, term):
        # TODO: Delegate to _idf_value(term).
        raise NotImplementedError("FeatureContext.idf")

    def _idf_value(self, term):
        # TODO: Return and validate the idf for a term, supporting both a callable and a mapping; non-finite becomes 0.0.
        raise NotImplementedError("FeatureContext._idf_value")

    def _local_bm25(self, query_text, doc):
        # TODO: Okapi BM25 over the stored term frequencies, lengths and idf, with k1=1.5 and b=0.75; used when no stage_scorer is injected.
        raise NotImplementedError("FeatureContext._local_bm25")

    def stage_score(self, query_text, doc):
        # TODO: Return float(self._stage(query_text, doc)).
        raise NotImplementedError("FeatureContext.stage_score")

    def dense_cosine(self, query_text, doc):
        # TODO: Return float(self._dense(query_text, doc)).
        raise NotImplementedError("FeatureContext.dense_cosine")


# ---------------------------------------------------------------------------
# the reranker
# ---------------------------------------------------------------------------

def _as_keys(candidates):
    """Accept doc_ids or ``(doc_id, score)`` pairs and return the doc_ids."""
    keys = []
    for item in candidates:
        if isinstance(item, (tuple, list)):
            keys.append(item[0])
        else:
            keys.append(item)
    return keys


class Reranker:
    """A pointwise logistic-regression ranker trained by deterministic gradient descent.

    ``fit`` takes ``(feature_vector, label)`` pairs with labels in ``{0.0, 1.0}`` and
    minimises the mean logistic loss plus a tiny L2 penalty by fixed-step gradient
    descent. There is no random state: the same examples always produce the same
    weights. ``score`` is the linear score of the feature vector; ``rerank`` sorts a
    candidate list by that score and keeps the top ``k``, never returning a document
    outside the candidates it was given.
    """

    def __init__(self, context=None, iterations=400, lr=0.5, l2=1e-4):
        # TODO: Store the context, iterations, lr and l2; start weights at zero, bias at 0.0, and loss_history empty.
        raise NotImplementedError("Reranker.__init__")

    @staticmethod
    def _sigmoid(z):
        # TODO: Numerically stable logistic function (branch on the sign of z).
        raise NotImplementedError("Reranker._sigmoid")

    def score_vector(self, vector):
        # TODO: Return bias plus the dot product of the weights and the vector.
        raise NotImplementedError("Reranker.score_vector")

    def fit(self, examples):
        """Train on ``(feature_vector, label)`` pairs; returns ``self``."""
        # TODO: For a fixed number of iterations accumulate the logistic-loss gradient (probability - label) over the (vector, label) examples, take the mean, add the L2 term, and step the weights and bias; record the mean loss each iteration. No randomness.
        raise NotImplementedError("Reranker.fit")

    def score(self, query, doc):
        # TODO: Return score_vector(features(query, doc, self.context)).
        raise NotImplementedError("Reranker.score")

    def rerank(self, query, candidates, k=RERANK_DEPTH):
        """Reorder ``candidates`` by score and return the top ``k`` doc_ids.

        ``candidates`` may be doc_ids or ``(doc_id, score)`` pairs. The result is always
        a subsequence of the given candidates: a document outside the list can never
        appear. An empty candidate list (the first stage abstained) returns ``[]``.
        """
        # TODO: Normalise candidates to doc_ids, look each document up in the context (an empty document if absent), score it, sort by (-score, doc_id), and return the first k. Only candidates may appear; [] for an empty list.
        raise NotImplementedError("Reranker.rerank")


# ---------------------------------------------------------------------------
# sibling stages and the shared evaluation set
# ---------------------------------------------------------------------------

def _repo_module_dir(name):
    """Locate ``rag-from-scratch/<name>/solutions`` from this file or its parent."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / name / "solutions",
        here.parent / name / "solutions",
    ]
    for candidate in candidates:
        if (candidate / f"{name}.py").is_file():
            return candidate
    raise FileNotFoundError(
        f"cannot find the sibling {name!r} stage at ../{name}/solutions relative to {here}.")


def _import_sibling(name):
    path = str(_repo_module_dir(name))
    if path not in sys.path:
        sys.path.insert(0, path)
    import importlib

    return importlib.import_module(name)


def _eval_set_solutions():
    """Locate ``rag-from-scratch/eval-set/solutions`` from this file or its parent."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / "eval-set" / "solutions",
        here.parent / "eval-set" / "solutions",
    ]
    env = os.environ.get("RAG_EVAL_SET")
    if env:
        candidates.insert(0, pathlib.Path(env))
    for candidate in candidates:
        if (candidate / "metrics.py").is_file() and (candidate / "corpus.py").is_file():
            return candidate
    raise FileNotFoundError(
        f"cannot find the shared eval set at ../eval-set/solutions relative to {here}.")


def _import_eval_metrics():
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import importlib

    return importlib.import_module("metrics")


def _flatten_queries(queries):
    if isinstance(queries, dict):
        return [q for family in _FAMILY_ORDER for q in queries.get(family, [])]
    return list(queries)


_EVAL_CACHE = [None]


def load_eval_set():
    """Return the shared evaluation set: ``{corpus, query_sets, queries, metrics}``.

    Imported from ``../eval-set/solutions`` exactly the way the sibling stages do. The
    dict is cached so repeated calls do not rebuild the corpus.
    """
    # TODO: Locate ../eval-set/solutions, import corpus/queries/metrics, generate seed 0, build the query sets, and return {corpus, query_sets, queries, metrics}; cache the result.
    raise NotImplementedError("load_eval_set")


def build_retriever(corpus):
    """Build the sibling BM25 retriever over ``corpus`` (a corpus dict or doc list)."""
    # TODO: Import the sibling bm25 and return BM25Retriever(corpus) — the first stage.
    raise NotImplementedError("build_retriever")


def build_context(corpus):
    """Build a :class:`FeatureContext` wired to the sibling BM25 and LSA stages."""
    # TODO: Import the sibling bm25 and (if present) lsa; build the BM25 index and the LSA embeddings once; return a FeatureContext whose stage scorer is bm25_score and whose dense scorer dot-products the query and document embeddings.
    raise NotImplementedError("build_context")


_DEFAULT_RETRIEVER = [None]


def first_stage(query, k=CANDIDATE_DEPTH, filters=None, retriever=None):
    """Return up to ``k`` doc_ids from the first-stage lexical retriever.

    By default this is the sibling ``../bm25`` retriever over the shared eval set. The
    returned list is the candidate list: recall@``CANDIDATE_DEPTH`` of this list is the
    ceiling for any reranker built on top of it.
    """
    # TODO: Use the given retriever, or lazily build the sibling-BM25 retriever over the shared eval set, and return retriever.retrieve(query, k=k, filters=filters).
    raise NotImplementedError("first_stage")


# ---------------------------------------------------------------------------
# training, the disjoint split, and evaluation
# ---------------------------------------------------------------------------

def choose_split(queries):
    """Return ``(train_qids, eval_qids)``: a deterministic, disjoint query split.

    Within each answerable family, the queries sorted by qid alternate between train
    and eval, so every family appears on both sides. No-answer queries go to eval only
    (they carry no positive example to train on) and are what the abstention metrics
    are measured over. Disjointness is the whole contract; check.py asserts it.
    """
    # TODO: For each family in order, sort its queries by qid and alternate them into train and eval; send no_answer queries to eval only. Return the two qid lists; they must be disjoint.
    raise NotImplementedError("choose_split")


def train_and_evaluate(corpus, query_sets, k=RERANK_DEPTH, depth=CANDIDATE_DEPTH,
                       retriever=None, context=None, iterations=400, lr=0.5, l2=1e-4):
    """Train on one query split and measure base vs reranked on the disjoint other.

    Returns a dict with the base (first-stage top-``k``) and reranked metrics, the
    split qids, the fitted model, and ``first_stage_recall@100`` — the ceiling the
    reranked ``recall@k`` can never exceed. The metrics are reported as measured; the
    reranker is not assumed to beat the base ranking.
    """
    # TODO: Choose the split; build examples from the train queries' candidate lists labelled by relevance; fit a Reranker; then for each eval query record the base top-k and the reranked top-k, accumulate first-stage recall@depth over answerable queries, and return base/reranked metrics, the model, the qids, and the ceiling.
    raise NotImplementedError("train_and_evaluate")


def find_ceiling_case(corpus, query_sets, depth=CANDIDATE_DEPTH, distractors=140):
    """Find a query whose relevant document the first stage leaves out of its top-``depth``.

    The shared corpus has fewer documents than the candidate depth, so depth-100 does not
    truncate it. To make the ceiling bind, 140 deterministic distractor documents are
    appended to the corpus: each repeats the query's own tokens, so BM25 ranks them above
    the real documents while ``is_current`` still marks them as superseded clones. The
    first query for which a relevant document is pushed out is returned as
    ``{query, doc_id, candidates, documents, retriever}``, or ``None``.
    """
    # TODO: For each answerable query, append deterministic clone documents that repeat the query's tokens (so BM25 ranks them first) and return the first query whose relevant document is outside retriever.retrieve(query, depth), with the candidates, augmented documents and retriever.
    raise NotImplementedError("find_ceiling_case")


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

_FAMILIES = ("lexical", "semantic", "filtered", "multi_hop", "no_answer", "overall")


def _row(result, family):
    if family == "overall":
        return result["overall"]
    return result["by_type"].get(family, {})


def demo():
    """Print base vs reranked metrics per family, the ceiling, and a ceiling query."""
    # TODO: Load the shared eval set, train and evaluate with k=5, print the per-family base-vs-reranked recall/MRR/nDCG table and the first-stage ceiling, then find and print a ceiling query with and without the excluded document injected as a candidate.
    raise NotImplementedError("demo")


if __name__ == "__main__":
    demo()
