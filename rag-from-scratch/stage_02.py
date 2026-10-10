"""RAG From Scratch — stage 2: TF-IDF embeddings on sparse dicts

Why sparse dicts and not a vector library? Because "embedding" is not magic:
it is a term-weighting scheme, and you cannot reason about retrieval until you
have built the boring one. A dict is also the honest representation — most
dimensions are zero.

TODO: implement `tokenize`, `Tfidf.fit`, `Tfidf.transform`, `cosine`.

    tokenize(text) -> lowercase alphanumeric words
    Tfidf.fit(docs):
        self.vocab  term -> column index
        self.idf    term -> ln((N + 1) / (df + 1)) + 1     (smoothed, never 0)
    Tfidf.transform(text) -> {term: weight}, L2-normalised
        weight = (1 + ln(tf)) * idf
    cosine(a, b) -> true cosine similarity in [-1, 1], 0.0 if either is empty
"""


def tokenize(text):
    raise NotImplementedError("stage 2: implement tokenize()")


class Tfidf:
    def fit(self, docs):
        raise NotImplementedError("stage 2: implement Tfidf.fit()")

    def transform(self, text):
        raise NotImplementedError("stage 2: implement Tfidf.transform()")


def cosine(a, b):
    raise NotImplementedError("stage 2: implement cosine()")
