"""RAG From Scratch — stage 9 solution: end-to-end retrieval and recall@k."""

from stage_02 import Tfidf
from stage_03 import VectorIndex


def build(docs):
    model = Tfidf().fit(docs)
    index = VectorIndex()
    for i, doc in enumerate(docs):
        index.add(i, model.transform(doc))
    return model, index


def retrieve(question, model, index, k):
    return index.search(model.transform(question), k)


def recall_at_k(model, index, questions, gold, k):
    if not questions:
        return 1.0
    hits = 0
    for question, want in zip(questions, gold):
        found = [cid for cid, _ in retrieve(question, model, index, k)]
        if want in found:
            hits += 1
    return hits / len(questions)
