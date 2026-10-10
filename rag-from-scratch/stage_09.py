"""RAG From Scratch — stage 9: end-to-end retrieval and recall@k

The capstone wires stages 1-3 together and puts a number on it. Recall@k is
the retriever's honest metric: did the gold chunk make the cut at all? Ranking
quality is stage 6's business.

TODO: implement `build`, `retrieve`, `recall_at_k`.

    build(docs)                  fit a Tfidf model, add every doc to a
                                 VectorIndex keyed by its index; return
                                 (model, index)
    retrieve(question, model, index, k) -> [(doc_index, score)]
    recall_at_k(model, index, questions, gold, k)
                                 fraction of questions whose gold doc_index is
                                 in the top k; 1.0 for an empty question list
"""

from stage_02 import Tfidf
from stage_03 import VectorIndex


def build(docs):
    raise NotImplementedError("stage 9: implement build()")


def retrieve(question, model, index, k):
    raise NotImplementedError("stage 9: implement retrieve()")


def recall_at_k(model, index, questions, gold, k):
    raise NotImplementedError("stage 9: implement recall_at_k()")
