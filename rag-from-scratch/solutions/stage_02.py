"""RAG From Scratch — stage 2 solution: TF-IDF on sparse dicts."""

import math
import re

_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return _WORD.findall(text.lower())


class Tfidf:
    def fit(self, docs):
        tokenized = [tokenize(d) for d in docs]
        df = {}
        for toks in tokenized:
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        self.vocab = {t: i for i, t in enumerate(sorted(df))}
        n = len(docs)
        self.idf = {t: math.log((n + 1) / (df[t] + 1)) + 1 for t in df}
        return self

    def transform(self, text):
        tf = {}
        for t in tokenize(text):
            if t in self.vocab:
                tf[t] = tf.get(t, 0) + 1
        vec = {t: (1 + math.log(c)) * self.idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm:
            vec = {t: v / norm for t, v in vec.items()}
        return vec


def cosine(a, b):
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(t, 0.0) for t, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
