"""rag_attack -- agent-evals #5: a deterministic adversarial harness for retrieval.

Re-exports the public interface from rag_attack.rag_attack so that ``import rag_attack``
works and the tests can reach both the provided infrastructure and the learner's core.
"""

from .rag_attack import (
    LocalRetriever,
    content_terms,
    evaluate_attacks,
    load_eval_set,
    local_sut_factory,
    perturb_text,
    poison_document,
    probe,
    tokenize,
)

__all__ = [
    "LocalRetriever",
    "content_terms",
    "evaluate_attacks",
    "load_eval_set",
    "local_sut_factory",
    "perturb_text",
    "poison_document",
    "probe",
    "tokenize",
]
