# RESOURCES — rag_attack (agent-evals #5)

How to read this list: each entry says why it matters for THIS module and is restated in our
own words (cite and restate, never copy). `[v]` = confident it exists as cited; `[verify]` =
written from memory, confirm the details later.

## Attacks on retrieval and RAG

1. Zou, Geng, Wang & Jia, "PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented
   Generation of Large Language Models", USENIX Security 2025. `[verify]`
   Why: the exact mechanism this module's `poison_document` tests — an attacker cannot edit
   the model, only insert a handful of documents, and repeats the target query's terms so a
   lexical/embedding retriever ranks the fake highest.
   Restated: you rarely need to break the retriever; you only need to add one document that
   looks more relevant than the truth.

2. Chaudhari et al., "Phantom: General Trigger Attacks on Retrieval Augmented Language
   Generation", 2024. `[verify]`
   Why: generalizes the poison to a trigger the attacker controls. Our module stops at the
   single-document, single-query case on purpose — the MVP before the limit cases.

3. Whitehead et al., "Reliable LLM-based RAG: a survey of attack and defense", 2024. `[verify]`
   Why: a taxonomy of query- and corpus-side attacks to pick the two families worth a from-
   scratch build (perturbation, poisoning) and to justify deferring the rest.

## Why recall is not enough

4. Manning, Raghavan & Schütze, *Introduction to Information Retrieval*, CUP, 2008 —
   chapters 8 and 9. `[v]`
   Why: precision/recall and ranked evaluation; the book already warns that a single aggregate
   number hides which queries fail. Restated: report per-family so a masked failure shows.

5. Voorhees, "The TREC Robust Retrieval Track", *SIGIR Forum* 39, 2005. `[verify]`
   Why: the Robust track exists precisely because systems that score well on average fail on
   a minority of hard queries; the per-query (not per-collection) view is the one that catches
   this. Our `drops`/`poisons` counters are the per-query view at the level of a single answer.

## Abstention

6. The RAG repo's own `rag-from-scratch/eval-set/` and `self-rag/` — read them first. `[v]`
   Why: the shared corpus, query families and the no-answer/abstention conventions this
   harness reuses instead of reinventing; `self-rag` is where the reflection threshold lives.

## Typos and noisy queries

7. Jones, "N-gram models and lexicons", in *Speech and Language Processing* (Jurafsky &
   Martin). `[verify]`
   Why: character-level noise (transposition, deletion, doubling, adjacent-key substitution)
   is the standard first model of a typo; `perturb_text` implements exactly one edit per
   touched word so the perturbation is meaning-preserving by construction.

## HNSW / the target systems

8. `rag-from-scratch/README.md` projects 1-7 and their solutions. `[v]`
   Why: the concrete SUTs a real run would point the harness at; `local_sut_factory` is a
   stdlib stand-in so the tests need nothing external.
