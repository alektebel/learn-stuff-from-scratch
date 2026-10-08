"""Latent Semantic Analysis retrieval — the dense stage of RAG project 1 (hybrid search).

LSA (Deerwester et al., *Indexing by Latent Semantic Analysis*, 1990) is the dense
retriever that sits beside Okapi BM25 on the same corpus. A term-document count matrix
is weighted with tf-idf and truncated by its singular value decomposition, so documents
and queries that share no literal token can still meet in the latent "concept" space.

This module is wired to the shared step-0 evaluation set (`../eval-set`): `evaluate` and
`demo` import its `corpus`, `queries`, `metrics` and `baseline` modules, so LSA is
measured on exactly the queries BM25 is measured on.

DESIGN DECISION - tokenisation is identical to BM25: `re.findall(r"[a-z0-9]+", text.lower())`.
    The two stages only differ in how they weigh a document, never in what a document is
    made of; keeping the tokeniser identical is what makes the comparison on the shared
    eval set meaningful. Cost: no stemming and no stopword list, so some no-answer
    queries are answered by a generic token, exactly as with BM25 (reported honestly in
    the metrics).

DESIGN DECISION - the term-document matrix is N documents x D terms, stored row-major,
    and `tf_idf` also L2-normalises every row.
    Returning both the sorted vocabulary and the raw-count matrix keeps `tf_idf` a pure
    matrix transform and lets the checks inspect the counts directly. Row-normalising
    inside `tf_idf` means a document's weighted vector already lies on the unit sphere,
    so cosine similarity is a plain dot product. Cost: `idf` has to be stored on the
    model separately (`tf_idf` cannot recover it from the normalised rows) so queries can
    reuse the corpus statistics.

DESIGN DECISION - tf-idf is followed by centring the term-document matrix, then a
    truncated SVD.
    Centring removes the "every document shares this" component so the leading singular
    directions describe contrast between documents rather than their common vocabulary.
    The SVD is computed from whichever Gram matrix is smaller (N x N when there are
    fewer documents than terms, D x D otherwise), which is the whole point of the D > N
    limit case: the D x D matrix is never built when D is huge. Cost: the centred matrix
    no longer has a sparse identity to exploit, which is fine at this scale.

DESIGN DECISION - a query is a pseudo-document: same tokeniser, same idf, same
    normalisation, same centring, then projected onto the retained right singular
    vectors and L2-normalised.
    This is the standard LSA folding-in approximation and it keeps the query and document
    embeddings in the same basis, so cosine similarity is valid. Cost: folding-in is not
    the same as recomputing the SVD with the query included, so a query that would shift
    the concept axes is approximated.

DESIGN DECISION - abstention is "the ranked list is empty": a query with no token in the
    vocabulary, or whose every candidate is filtered out, returns [].
    A no-match query embeds to the zero vector, whose cosine with everything is zero, so
    nothing is returned; an explicit filter that empties the candidate set likewise
    returns []. Cost: the threshold is exactly zero and is not calibrated, so some
    no-answer queries are still answered (a generic token has a small positive cosine);
    a learned threshold is project 7's subject.

DESIGN DECISION - ties break by doc_id ascending, and eigenvector signs are canonicalised.
    Deterministic output is required for reproducible eval runs, for check.py, and for
    the reconstruction identity (a singular vector and its negation are both valid). Cost:
    sign canonicalisation adds a pass over each component.

Run the demo, which prints the honest LSA vs BM25 vs lexical-baseline numbers:
`python3 solutions/lsa.py`.
"""
from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+")

_FILTER_KEYS = ("region", "year", "department", "access_level")


def tokenize(text):
    """Lower-cased alphanumeric tokens, in order, with punctuation dropped."""
    return TOKEN_RE.findall(text.lower())


def build_term_document(docs):
    """Return ``(terms, doc_vectors)`` for an iterable of documents.

    ``terms`` is the sorted vocabulary (length D). ``doc_vectors`` is the N x D
    term-document count matrix in row-major order: ``doc_vectors[i][j]`` is the number
    of times ``terms[j]`` occurs in ``documents[i]`` (title + body).
    """
    tokens_per_doc = [tokenize(doc["title"] + " " + doc["body"]) for doc in docs]
    vocab = sorted({term for tokens in tokens_per_doc for term in tokens})
    position = {term: j for j, term in enumerate(vocab)}
    doc_vectors = []
    for tokens in tokens_per_doc:
        row = [0] * len(vocab)
        for term, count in Counter(tokens).items():
            row[position[term]] = count
        doc_vectors.append(row)
    return vocab, doc_vectors


def _idf_vector(matrix):
    """Smoothed BM25 idf for every column of an N x D count matrix."""
    n_docs = len(matrix)
    n_terms = len(matrix[0]) if matrix else 0
    df = [0] * n_terms
    for row in matrix:
        for j, count in enumerate(row):
            if count:
                df[j] += 1
    return [math.log(1 + (n_docs - df[j] + 0.5) / (df[j] + 0.5)) for j in range(n_terms)]


def _l2(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return list(vector)
    return [value / norm for value in vector]


def tf_idf(matrix):
    """tf-idf-weight an N x D count matrix and L2-normalise each row.

    The idf is the same smoothed form BM25 uses, so the two stages agree on how much a
    rare term is worth; the row normalisation makes cosine similarity a dot product.
    """
    if not matrix:
        return []
    idf = _idf_vector(matrix)
    weighted = []
    for row in matrix:
        vec = [row[j] * idf[j] for j in range(len(row))]
        weighted.append(_l2(vec))
    return weighted


def jacobi(A, tol=1e-13, max_sweeps=100):
    """Cyclic Jacobi eigen-decomposition of a real symmetric matrix ``A``.

    Returns ``(eigenvalues, eigenvectors)`` where ``eigenvalues`` are the diagonal of the
    rotated matrix and ``eigenvectors`` is a list of columns: ``eigenvectors[row][col]``
    is the ``row``-th component of the ``col``-th eigenvector. The order is the order the
    rotations happened to leave behind — use :func:`eig_sorted` when you need them
    sorted. The algorithm is from Golub & Van Loan, *Matrix Computations*, section 8.4.
    """
    n = len(A)
    a = [list(row) for row in A]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(max_sweeps):
        off = 0.0
        for p in range(n):
            for q in range(p + 1, n):
                off += a[p][q] * a[p][q]
        if off < tol * tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if apq == 0.0:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * apq)
                t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p] = c * vkp - s * vkq
                    v[k][q] = s * vkp + c * vkq
    return [a[i][i] for i in range(n)], v


def eig_sorted(A):
    """Eigenvalues and eigenvectors of symmetric ``A``, largest eigenvalue first.

    Returns ``(values, vectors)`` where ``vectors[i]`` is the eigenvector for
    ``values[i]`` (a length-n list). Ties break by the original index for determinism.
    """
    values, columns = jacobi(A)
    n = len(values)
    order = sorted(range(n), key=lambda i: (-values[i], i))
    sorted_values = [values[i] for i in order]
    sorted_vectors = [[columns[row][i] for row in range(n)] for i in order]
    return sorted_values, sorted_vectors


def _canonical_signs(vectors):
    """Flip each vector so its largest-magnitude entry is positive (sign is arbitrary)."""
    canonical = []
    for vector in vectors:
        pivot = max(range(len(vector)), key=lambda j: abs(vector[j])) if vector else None
        if pivot is not None and vector[pivot] < 0:
            canonical.append([-value for value in vector])
        else:
            canonical.append(list(vector))
    return canonical


def _gram(matrix, left_vectors):
    """Return the Gram matrix ``matrix @ matrix^T`` or ``matrix^T @ matrix``.

    With ``left_vectors=True`` this is N x N (rows are documents); False gives D x D.
    """
    if left_vectors:
        n = len(matrix)
        return [[sum(matrix[i][j] * matrix[l][j] for j in range(len(matrix[i])))
                 for l in range(n)] for i in range(n)]
    t = len(matrix[0]) if matrix else 0
    return [[sum(matrix[d][i] * matrix[d][j] for d in range(len(matrix)))
             for j in range(t)] for i in range(t)]


def _default_components(n_docs):
    """Coarse default rank: a quarter of the corpus, capped at 100 (at least 1).

    Truncation is what makes LSA dense: at full rank the embedding is the tf-idf matrix
    again and nothing is smoothed. A quarter is a coarse heuristic for these small
    corpora; a scree plot / explained-variance threshold is left as an exercise.
    """
    return max(1, min(100, n_docs // 4))


def fit_lsa(docs, k):
    """Fit a rank-``k`` LSA model to ``docs``.

    Returns a dict with:
      * ``terms``           sorted vocabulary, length D
      * ``idf``             smoothed idf per term, length D
      * ``mean``            per-term mean of the normalised tf-idf matrix, length D
      * ``components``      retained right singular vectors V_k, k x D
      * ``singular_values`` the k largest singular values, descending
      * ``doc_embeddings``  N x k L2-normalised document coordinates X_centred V_k^T
      * ``doc_ids``         the document ids in embedding order
      * ``gram_size``       the dimension of the Gram matrix that was decomposed

    The truncated SVD is taken from the smaller Gram matrix: N x N when N <= D (fewer
    documents than terms), else D x D. This is what makes the D > N case cheap — the
    D x D term-space matrix is never built when there are more terms than documents.
    """
    terms, counts = build_term_document(docs)
    doc_ids = [doc["doc_id"] for doc in docs]
    n_docs = len(counts)
    n_terms = len(terms)
    weighted = tf_idf(counts)
    idf = _idf_vector(counts) if n_terms else []
    mean = [sum(row[j] for row in weighted) / n_docs for j in range(n_terms)] if n_docs else [0.0] * n_terms
    centred = [[row[j] - mean[j] for j in range(n_terms)] for row in weighted]

    rank = max(0, min(k, n_docs, n_terms))
    components = []
    singular_values = []
    if rank:
        if n_docs <= n_terms:
            # Fewer documents than terms: decompose the N x N document-space Gram matrix.
            gram_size = n_docs
            values, vectors = eig_sorted(_gram(centred, left_vectors=True))
            for i in range(rank):
                singular = math.sqrt(max(values[i], 0.0))
                singular_values.append(singular)
                if singular > 1e-12:
                    u = vectors[i]  # length N
                    components.append([sum(centred[d][j] * u[d] for d in range(n_docs)) / singular
                                       for j in range(n_terms)])
                else:
                    components.append([0.0] * n_terms)
        else:
            # Fewer terms than documents: decompose the D x D term-space Gram matrix.
            gram_size = n_terms
            values, vectors = eig_sorted(_gram(centred, left_vectors=False))
            for i in range(rank):
                singular_values.append(math.sqrt(max(values[i], 0.0)))
                components.append(list(vectors[i]))  # already a right singular vector, length D
    else:
        gram_size = n_docs if n_docs <= n_terms else n_terms

    components = _canonical_signs(components)
    doc_embeddings = []
    for row in centred:
        coords = [sum(row[j] * components[i][j] for j in range(n_terms)) for i in range(rank)]
        doc_embeddings.append(_l2(coords))

    return {
        "terms": terms,
        "idf": idf,
        "mean": mean,
        "components": components,
        "singular_values": singular_values,
        "doc_embeddings": doc_embeddings,
        "doc_ids": doc_ids,
        "gram_size": gram_size,
    }


def embed_query(query, model):
    """Project a query into the fitted LSA space; returns a length-k L2-normalised list.

    A query with no token in the vocabulary returns the zero vector, whose cosine with
    every document is zero — that is how a no-match query abstains.
    """
    text = query.get("text", "") if isinstance(query, dict) else query
    terms = model["terms"]
    position = {term: j for j, term in enumerate(terms)}
    n_terms = len(terms)

    raw = [0.0] * n_terms
    for term in tokenize(text):
        j = position.get(term)
        if j is not None:
            raw[j] += 1.0
    if not any(raw):
        return [0.0] * len(model["components"])

    weighted = [raw[j] * model["idf"][j] for j in range(n_terms)]
    weighted = _l2(weighted)
    centred = [weighted[j] - model["mean"][j] for j in range(n_terms)]
    coords = [sum(centred[j] * component[j] for j in range(n_terms))
              for component in model["components"]]
    return _l2(coords)


class LsaRetriever:
    """LSA retriever with pre-retrieval metadata filtering and empty-result abstention."""

    def __init__(self, docs, n_components=None):
        documents = docs["documents"] if isinstance(docs, dict) else docs
        self.documents = list(documents)
        if n_components is None:
            n_components = _default_components(len(self.documents))
        self.model = fit_lsa(self.documents, n_components)
        self._by_id = {doc["doc_id"]: doc for doc in self.documents}
        self._embeddings = dict(zip(self.model["doc_ids"], self.model["doc_embeddings"]))

    @staticmethod
    def _passes_filters(doc, filters):
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

    def retrieve(self, query, k=10, filters=None):
        """Return up to k doc_ids for ``query``, best first; ``[]`` means "abstain".

        ``query`` is either the eval set's query dict (``text`` and ``filters``) or a raw
        string. An explicit ``filters`` argument overrides the query's own filters.
        """
        if isinstance(query, dict):
            text = query.get("text", "")
            if filters is None:
                filters = query.get("filters", {})
        else:
            text = query

        query_embedding = embed_query(text, self.model)
        scored = []
        for doc in self.documents:
            if not self._passes_filters(doc, filters):
                continue
            embedding = self._embeddings.get(doc["doc_id"], [])
            score = sum(a * b for a, b in zip(query_embedding, embedding))
            if score > 0.0:
                scored.append((score, doc["doc_id"]))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [doc_id for _score, doc_id in scored[:k]]


def _flatten_queries(queries):
    """Accept the eval set's family dict or an already-flat query list."""
    if isinstance(queries, dict):
        order = ("lexical", "semantic", "filtered", "multi_hop", "no_answer")
        return [q for family in order for q in queries.get(family, [])]
    return list(queries)


def _eval_set_path():
    """Locate the shared eval set's solutions directory."""
    import pathlib

    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent / "eval-set" / "solutions",
        here.parent.parent / "eval-set" / "solutions",
    ]
    for path in candidates:
        if (path / "metrics.py").is_file():
            return path
    raise FileNotFoundError(
        "cannot find the shared eval set at ../eval-set/solutions relative to "
        f"{here}: run the module from inside rag-from-scratch/ or copy check.py next "
        "to the eval set.")


def _import_metrics():
    import sys

    path = str(_eval_set_path())
    if path not in sys.path:
        sys.path.insert(0, path)
    import metrics

    return metrics


def evaluate(corpus, queries, k=10, n_components=None):
    """Score every query with LSA and assemble the shared metrics dictionary.

    ``corpus`` is ``corpus.generate_corpus(seed)``; ``queries`` is either
    ``queries.build_query_sets(corpus)`` or ``queries.all_queries(...)``. Returns the
    dict assembled by ``metrics.evaluate`` — the same shape BM25's ``evaluate_bm25``
    returns, so the two stages are directly comparable.
    """
    metrics = _import_metrics()
    flat = _flatten_queries(queries)
    retriever = LsaRetriever(corpus, n_components=n_components)
    ranked = {q["qid"]: retriever.retrieve(q, k=k) for q in flat}
    return metrics.evaluate(ranked, flat, k=k)


# Symmetric alias, mirroring bm25.evaluate_bm25.
evaluate_lsa = evaluate


def _row(result, family):
    if family == "overall":
        return result["overall"]
    return result["by_type"].get(family, {})


def demo():
    """Print LSA next to BM25 and the eval set's lexical baseline on the shared set."""
    import sys

    sys.dont_write_bytecode = True
    eval_path = str(_eval_set_path())
    if eval_path not in sys.path:
        sys.path.insert(0, eval_path)

    from baseline import LexicalBaseline
    from corpus import generate_corpus
    from queries import all_queries, build_query_sets
    import metrics

    corpus = generate_corpus(0)
    query_sets = build_query_sets(corpus)
    queries = all_queries(query_sets)

    lsa_result = evaluate(corpus, query_sets, k=10)
    baseline = LexicalBaseline(corpus)
    base_ranked = {q["qid"]: baseline.retrieve(q, 10) for q in queries}
    base_result = metrics.evaluate(base_ranked, queries, k=10)

    bm25_result = None
    try:
        import pathlib

        bm25_path = pathlib.Path(__file__).resolve().parent.parent.parent / "bm25" / "solutions"
        if (bm25_path / "bm25.py").is_file():
            if str(bm25_path) not in sys.path:
                sys.path.insert(0, str(bm25_path))
            import bm25

            bm25_result = bm25.evaluate_bm25(corpus, query_sets, k=10)
    except Exception:  # noqa: BLE001 - the demo must run with or without the sibling stage
        bm25_result = None

    print(f"seed 0, {len(corpus['documents'])} documents, {len(queries)} queries")
    header = f"{'family':<12}{'LSA r@10':>10}{'LSA MRR':>9}{'base r@10':>11}{'base MRR':>10}"
    if bm25_result is not None:
        header += f"{'BM25 r@10':>11}{'BM25 MRR':>10}"
    print(header)
    for family in ("lexical", "semantic", "filtered", "multi_hop", "no_answer", "overall"):
        l = _row(lsa_result, family)
        b = _row(base_result, family)
        line = (f"{family:<12}{l.get('recall@k', 0.0):>10.3f}{l.get('mrr', 0.0):>9.3f}"
                f"{b.get('recall@k', 0.0):>11.3f}{b.get('mrr', 0.0):>10.3f}")
        if bm25_result is not None:
            m = _row(bm25_result, family)
            line += f"{m.get('recall@k', 0.0):>11.3f}{m.get('mrr', 0.0):>10.3f}"
        print(line)
    print("abstention (tp/fp/fn)  LSA: "
          f"{lsa_result['abstention']['tp']}/{lsa_result['abstention']['fp']}/"
          f"{lsa_result['abstention']['fn']}  baseline: "
          f"{base_result['abstention']['tp']}/{base_result['abstention']['fp']}/"
          f"{base_result['abstention']['fn']}")


if __name__ == "__main__":
    demo()
