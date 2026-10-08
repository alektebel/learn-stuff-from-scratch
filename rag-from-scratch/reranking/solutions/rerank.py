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
    if isinstance(query, dict):
        return query.get("text", "")
    return str(query)


def _squash(value):
    """Map any real number into (-1, 1); non-finite input becomes 0.0."""
    value = float(value)
    if not math.isfinite(value):
        return 0.0
    return value / (1.0 + abs(value))


def _cosine(left_tokens, right_tokens):
    """Cosine of the term-frequency vectors of two token lists."""
    if not left_tokens or not right_tokens:
        return 0.0
    left = Counter(left_tokens)
    right = Counter(right_tokens)
    dot = sum(count * right.get(term, 0) for term, count in left.items())
    left_norm = math.sqrt(sum(count * count for count in left.values()))
    right_norm = math.sqrt(sum(count * count for count in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _phrase_hit(query_text, document_text):
    """1.0 if the tokenised query occurs contiguously in the tokenised document."""
    query = " ".join(tokenize(query_text))
    if not query:
        return 0.0
    return 1.0 if query in " ".join(tokenize(document_text)) else 0.0


def features(query, doc, context=None):
    """Return the fixed-length feature vector for ``(query, doc)`` as a list of floats.

    The length is always ``len(FEATURE_NAMES)`` and every value is finite. ``context``
    is any object exposing ``stage_score(query_text, doc)``, ``dense_cosine(query_text,
    doc)``, ``idf(term)`` and ``avg_length`` (see :class:`FeatureContext`); when it is
    omitted the context-dependent features fall back to finite constants and the
    text-only features still vary with the document.
    """
    query_text = _query_text(query)
    title = str(doc.get("title", ""))
    body = str(doc.get("body", ""))
    document_text = title + " " + body

    query_tokens = tokenize(query_text)
    title_tokens = tokenize(title)
    document_tokens = tokenize(document_text)
    query_set = set(query_tokens)
    document_set = set(document_tokens)
    matched = query_set & document_set

    coverage = (len(matched) / len(query_set)) if query_set else 0.0
    title_match = (len(query_set & set(title_tokens)) / len(query_set)) if query_set else 0.0

    if context is not None:
        stage_raw = context.stage_score(query_text, doc)
        dense_raw = context.dense_cosine(query_text, doc)
        average_length = float(getattr(context, "avg_length", _DEFAULT_AVG_LEN) or _DEFAULT_AVG_LEN)
        idf_lookup = getattr(context, "idf", None)
    else:
        stage_raw = 0.0
        dense_raw = 0.0
        average_length = _DEFAULT_AVG_LEN
        idf_lookup = None

    def term_idf(term):
        if idf_lookup is None:
            return 1.0
        value = float(idf_lookup(term))
        return value if math.isfinite(value) else 1.0

    total_idf = sum(term_idf(term) for term in query_set)
    matched_idf = sum(term_idf(term) for term in matched)
    idf_coverage = (matched_idf / total_idf) if total_idf > 0.0 else 0.0

    if average_length <= 0.0:
        average_length = 1.0
    length_ratio = min(2.0, len(document_tokens) / average_length) / 2.0
    is_current = 0.0 if doc.get("superseded_by") else 1.0

    values = {
        "stage_score": _squash(stage_raw),
        "lexical_cosine": _cosine(query_tokens, document_tokens),
        "term_coverage": coverage,
        "idf_coverage": idf_coverage,
        "exact_phrase": _phrase_hit(query_text, document_text),
        "title_match": title_match,
        "length_ratio": length_ratio,
        "dense_cosine": _squash(dense_raw),
        "is_current": is_current,
    }
    return [float(values[name]) for name in FEATURE_NAMES]


class FeatureContext:
    """Everything ``features`` needs that is not inside a single document.

    ``stage_scorer`` and ``dense_scorer`` are callables ``(query_text, doc) -> float``.
    When they are omitted the first-stage feature is a local Okapi BM25 over the same
    corpus (so the module works with no sibling stage present) and the dense feature is
    0.0. ``idf`` is a mapping term -> idf computed from the corpus when not supplied.
    """

    def __init__(self, documents, stage_scorer=None, dense_scorer=None, idf=None,
                 avg_length=None):
        self.documents = list(documents)
        self._by_id = {doc["doc_id"]: doc for doc in self.documents}
        self._tokens = {
            doc["doc_id"]: tokenize(str(doc.get("title", "")) + " " + str(doc.get("body", "")))
            for doc in self.documents
        }
        self._term_freq = {doc_id: Counter(tokens) for doc_id, tokens in self._tokens.items()}
        self._lengths = {doc_id: len(tokens) for doc_id, tokens in self._tokens.items()}
        if avg_length is None:
            if self._lengths:
                self.avg_length = sum(self._lengths.values()) / len(self._lengths)
            else:
                self.avg_length = 1.0
        else:
            self.avg_length = float(avg_length)
        if self.avg_length <= 0.0:
            self.avg_length = 1.0
        self._idf = idf if idf is not None else self._compute_idf()
        self._stage = stage_scorer if stage_scorer is not None else self._local_bm25
        self._dense = dense_scorer if dense_scorer is not None else (lambda _q, _d: 0.0)

    def _compute_idf(self):
        n_docs = len(self._lengths)
        document_freq = Counter()
        for tokens in self._tokens.values():
            for term in set(tokens):
                document_freq[term] += 1
        return {
            term: math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            for term, df in document_freq.items()
        }

    def idf(self, term):
        return self._idf_value(term)

    def _idf_value(self, term):
        if callable(self._idf):
            value = float(self._idf(term))
            return value if math.isfinite(value) else 0.0
        return self._idf.get(term, 0.0)

    def _local_bm25(self, query_text, doc):
        k1, b = 1.5, 0.75
        doc_id = doc["doc_id"]
        term_freq = self._term_freq.get(doc_id, Counter())
        length = self._lengths.get(doc_id, 0) or 1
        score = 0.0
        for term in tokenize(query_text):
            freq = term_freq.get(term, 0)
            if not freq:
                continue
            term_idf = self._idf_value(term)
            denominator = freq + k1 * (1 - b + b * length / self.avg_length)
            score += term_idf * (freq * (k1 + 1)) / denominator
        return score

    def stage_score(self, query_text, doc):
        return float(self._stage(query_text, doc))

    def dense_cosine(self, query_text, doc):
        return float(self._dense(query_text, doc))


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
        self.context = context
        self.iterations = int(iterations)
        self.lr = float(lr)
        self.l2 = float(l2)
        self.weights = [0.0] * len(FEATURE_NAMES)
        self.bias = 0.0
        self.loss_history = []

    @staticmethod
    def _sigmoid(z):
        if z >= 0.0:
            return 1.0 / (1.0 + math.exp(-z))
        exp_z = math.exp(z)
        return exp_z / (1.0 + exp_z)

    def score_vector(self, vector):
        return self.bias + sum(weight * value for weight, value in zip(self.weights, vector))

    def fit(self, examples):
        """Train on ``(feature_vector, label)`` pairs; returns ``self``."""
        data = [([float(value) for value in vector], float(label)) for vector, label in examples]
        if not data:
            raise ValueError("Reranker.fit needs at least one (features, label) example")
        n_features = len(self.weights)
        for _ in range(self.iterations):
            gradients = [0.0] * n_features
            bias_gradient = 0.0
            total_loss = 0.0
            for vector, label in data:
                probability = self._sigmoid(self.score_vector(vector))
                total_loss += -(label * math.log(probability + _EPS)
                                + (1.0 - label) * math.log(1.0 - probability + _EPS))
                error = probability - label
                for index, value in enumerate(vector):
                    gradients[index] += error * value
                bias_gradient += error
            scale = 1.0 / len(data)
            for index in range(n_features):
                self.weights[index] -= self.lr * (gradients[index] * scale
                                                  + self.l2 * self.weights[index])
            self.bias -= self.lr * bias_gradient * scale
            self.loss_history.append(total_loss * scale)
        return self

    def score(self, query, doc):
        return self.score_vector(features(query, doc, self.context))

    def rerank(self, query, candidates, k=RERANK_DEPTH):
        """Reorder ``candidates`` by score and return the top ``k`` doc_ids.

        ``candidates`` may be doc_ids or ``(doc_id, score)`` pairs. The result is always
        a subsequence of the given candidates: a document outside the list can never
        appear. An empty candidate list (the first stage abstained) returns ``[]``.
        """
        scored = []
        for doc_id in _as_keys(candidates):
            doc = None
            if self.context is not None:
                doc = self.context._by_id.get(doc_id)
            if doc is None:
                doc = {"doc_id": doc_id, "title": "", "body": ""}
            scored.append((self.score(query, doc), doc_id))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [doc_id for _score, doc_id in scored[:max(0, k)]]


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
    if _EVAL_CACHE[0] is not None:
        return _EVAL_CACHE[0]
    path = str(_eval_set_solutions())
    if path not in sys.path:
        sys.path.insert(0, path)
    import importlib

    corpus_mod = importlib.import_module("corpus")
    queries_mod = importlib.import_module("queries")
    metrics_mod = importlib.import_module("metrics")
    corpus = corpus_mod.generate_corpus(0)
    query_sets = queries_mod.build_query_sets(corpus)
    result = {
        "corpus": corpus,
        "query_sets": query_sets,
        "queries": queries_mod.all_queries(query_sets),
        "metrics": metrics_mod,
    }
    _EVAL_CACHE[0] = result
    return result


def build_retriever(corpus):
    """Build the sibling BM25 retriever over ``corpus`` (a corpus dict or doc list)."""
    bm25 = _import_sibling("bm25")
    return bm25.BM25Retriever(corpus)


def build_context(corpus):
    """Build a :class:`FeatureContext` wired to the sibling BM25 and LSA stages."""
    documents = corpus["documents"] if isinstance(corpus, dict) else list(corpus)
    bm25 = _import_sibling("bm25")
    index = bm25.build_inverted_index(documents)

    try:
        lsa = _import_sibling("lsa")
    except FileNotFoundError:
        lsa = None

    embeddings = None
    model = None
    if lsa is not None and documents:
        retriever = lsa.LsaRetriever(documents)
        embeddings = retriever._embeddings
        model = retriever.model

    def stage_scorer(query_text, doc):
        return bm25.bm25_score(index, query_text, doc["doc_id"])

    def dense_scorer(query_text, doc):
        if embeddings is None:
            return 0.0
        embedding = lsa.embed_query(query_text, model)
        document_embedding = embeddings.get(doc["doc_id"], [])
        if not embedding or not document_embedding:
            return 0.0
        return sum(a * b for a, b in zip(embedding, document_embedding))

    return FeatureContext(documents, stage_scorer=stage_scorer, dense_scorer=dense_scorer)


_DEFAULT_RETRIEVER = [None]


def first_stage(query, k=CANDIDATE_DEPTH, filters=None, retriever=None):
    """Return up to ``k`` doc_ids from the first-stage lexical retriever.

    By default this is the sibling ``../bm25`` retriever over the shared eval set. The
    returned list is the candidate list: recall@``CANDIDATE_DEPTH`` of this list is the
    ceiling for any reranker built on top of it.
    """
    if retriever is None:
        if _DEFAULT_RETRIEVER[0] is None:
            _DEFAULT_RETRIEVER[0] = build_retriever(load_eval_set()["corpus"])
        retriever = _DEFAULT_RETRIEVER[0]
    return retriever.retrieve(query, k=k, filters=filters)


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
    queries = list(queries)
    train, evaluation = [], []
    for family in _FAMILY_ORDER:
        family_queries = sorted((q for q in queries if q.get("type") == family),
                                key=lambda q: q["qid"])
        if family == "no_answer":
            evaluation.extend(q["qid"] for q in family_queries)
            continue
        for index, query in enumerate(family_queries):
            (train if index % 2 == 0 else evaluation).append(query["qid"])
    return train, evaluation


def train_and_evaluate(corpus, query_sets, k=RERANK_DEPTH, depth=CANDIDATE_DEPTH,
                       retriever=None, context=None, iterations=400, lr=0.5, l2=1e-4):
    """Train on one query split and measure base vs reranked on the disjoint other.

    Returns a dict with the base (first-stage top-``k``) and reranked metrics, the
    split qids, the fitted model, and ``first_stage_recall@100`` — the ceiling the
    reranked ``recall@k`` can never exceed. The metrics are reported as measured; the
    reranker is not assumed to beat the base ranking.
    """
    metrics = _import_eval_metrics()
    queries = _flatten_queries(query_sets)
    train_qids, eval_qids = choose_split(queries)
    train_set, eval_set = set(train_qids), set(eval_qids)
    train_queries = [q for q in queries if q["qid"] in train_set]
    eval_queries = [q for q in queries if q["qid"] in eval_set]

    if retriever is None:
        retriever = build_retriever(corpus)
    if context is None:
        context = build_context(corpus)

    examples = []
    for query in train_queries:
        candidates = first_stage(query, depth, retriever=retriever)
        for doc_id in candidates:
            doc = context._by_id.get(doc_id)
            if doc is None:
                continue
            label = 1.0 if query["relevance"].get(doc_id, 0.0) > 0.0 else 0.0
            examples.append((features(query, doc, context), label))

    model = Reranker(context=context, iterations=iterations, lr=lr, l2=l2)
    model.fit(examples)

    base_predictions = {}
    reranked_predictions = {}
    ceiling_total = 0.0
    answerable = 0
    for query in eval_queries:
        full = first_stage(query, depth, retriever=retriever)
        base_predictions[query["qid"]] = first_stage(query, k, retriever=retriever)
        reranked_predictions[query["qid"]] = model.rerank(query, full, k=k)
        if query["relevance"]:
            ceiling_total += metrics.recall_at_k(full, query["relevance"], depth)
            answerable += 1
    ceiling = (ceiling_total / answerable) if answerable else 0.0

    return {
        "base": metrics.evaluate(base_predictions, eval_queries, k=k),
        "reranked": metrics.evaluate(reranked_predictions, eval_queries, k=k),
        "model": model,
        "context": context,
        "retriever": retriever,
        "train_qids": train_qids,
        "eval_qids": eval_qids,
        "first_stage_recall@100": ceiling,
        "depth": depth,
        "k": k,
    }


def find_ceiling_case(corpus, query_sets, depth=CANDIDATE_DEPTH, distractors=140):
    """Find a query whose relevant document the first stage leaves out of its top-``depth``.

    The shared corpus has fewer documents than the candidate depth, so depth-100 does not
    truncate it. To make the ceiling bind, 140 deterministic distractor documents are
    appended to the corpus: each repeats the query's own tokens, so BM25 ranks them above
    the real documents while ``is_current`` still marks them as superseded clones. The
    first query for which a relevant document is pushed out is returned as
    ``{query, doc_id, candidates, documents, retriever}``, or ``None``.
    """
    documents = corpus["documents"] if isinstance(corpus, dict) else list(corpus)
    for query in (_flatten_queries(query_sets)):
        if not query["relevance"]:
            continue
        repeated = " ".join(tokenize(_query_text(query)) * 8)
        clones = [{
            "doc_id": f"CLONE-{query['qid']}-{index:04d}",
            "title": "",
            "body": repeated,
            "department": "Clone",
            "region": "GLOBAL",
            "author": "clone",
            "date": "2026-01-01",
            "access_level": "internal",
            "version": 1,
            "supersedes": None,
            "superseded_by": "CLONE",
            "topics": [],
            "code": "CLONE",
        } for index in range(distractors)]
        augmented = documents + clones
        retriever = build_retriever(augmented)
        candidates = retriever.retrieve(query, k=depth)
        candidate_set = set(candidates)
        missing = [doc_id for doc_id in sorted(query["relevance"])
                   if doc_id not in candidate_set]
        if missing:
            return {
                "query": query,
                "doc_id": missing[0],
                "candidates": candidates,
                "documents": augmented,
                "retriever": retriever,
            }
    return None


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
    sys.dont_write_bytecode = True
    eval_set = load_eval_set()
    corpus = eval_set["corpus"]
    query_sets = eval_set["query_sets"]

    print(f"seed 0, {len(corpus['documents'])} documents, "
          f"{len(eval_set['queries'])} queries")
    print(f"first stage: bm25, candidate depth {CANDIDATE_DEPTH}; "
          f"reranker: logistic regression trained here")

    result = train_and_evaluate(corpus, query_sets, k=RERANK_DEPTH)
    base = result["base"]
    reranked = result["reranked"]
    print(f"train queries {len(result['train_qids'])}, "
          f"eval queries {len(result['eval_qids'])} "
          f"(disjoint: {set(result['train_qids']).isdisjoint(result['eval_qids'])})")
    print(f"first-stage recall@{result['depth']} (the ceiling) = "
          f"{result['first_stage_recall@100']:.3f}")

    print(f"\n{'family':<12}{'base r@5':>10}{'rerank r@5':>12}"
          f"{'base MRR':>10}{'rerank MRR':>12}{'base nDCG@5':>13}{'rerank nDCG@5':>14}")
    for family in _FAMILIES:
        b = _row(base, family)
        r = _row(reranked, family)
        print(f"{family:<12}{b.get('recall@k', 0.0):>10.3f}{r.get('recall@k', 0.0):>12.3f}"
              f"{b.get('mrr', 0.0):>10.3f}{r.get('mrr', 0.0):>12.3f}"
              f"{b.get('ndcg@k', 0.0):>13.3f}{r.get('ndcg@k', 0.0):>14.3f}")

    print("\nreported as measured: the reranker is not assumed to beat the base ranking,")
    print("and its recall@5 can never exceed the first-stage ceiling above.")

    case = find_ceiling_case(corpus, query_sets)
    if case is None:
        print("\nceiling: no query had a relevant document outside the first-stage top-100")
        return
    query = case["query"]
    doc_id = case["doc_id"]
    augmented = {"documents": case["documents"]}
    ceiling_model = train_and_evaluate(augmented, query_sets, k=RERANK_DEPTH)["model"]
    from_candidates = ceiling_model.rerank(query, case["candidates"], k=RERANK_DEPTH)
    injected = ceiling_model.rerank(query, case["candidates"] + [doc_id], k=1)
    print(f"\nceiling query: {query['qid']} — a relevant document ({doc_id}) is not in "
          f"the first-stage top-{CANDIDATE_DEPTH} once the index holds more documents")
    print(f"  the reranker returns only candidates, so it cannot return it: {from_candidates}")
    print(f"  injected as a candidate it is ranked first: {injected}")


if __name__ == "__main__":
    demo()
