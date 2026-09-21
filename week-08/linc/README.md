# LINC From Scratch

Make an LLM's answer **traceable** and **replicable** by refusing to
let it deduce.

> **Olausson, Gu, Lipkin, Zhang, Solar-Lezama, Tenenbaum, Levy.
> "LINC: A Neurosymbolic Approach for Logical Reasoning by Combining
> Language Models with First-Order Logic Provers." EMNLP 2023.**
> [paper](https://arxiv.org/abs/2310.15164)
>
> Also: **Logic-LM** (Pan et al., EMNLP 2023 Findings) and
> **Faithful CoT** (Lyu et al., AACL 2023). Same shape: translate,
> then *run* something.

LINC's premise is an LLM as the semantic parser. This repo has no
LLM — pure stdlib, no torch; the tiny transformer in
`llm-from-scratch` cannot parse FOL and never will. A faithful LINC
is not runnable here.

What is runnable, and the better directory:

1. Implement the **prover** and the **provenance layer** exactly.
2. Make the parse step a **pluggable interface**.
3. Drive it with a **fault-injected parser** whose taxonomy is
   LINC's own error analysis, made operational:
   quantifier-scope inversion, dropped negation, predicate arity
   drift (the paper's most common L3), hallucinated constant,
   implicit-premise drop (L1).
4. Sweep the parse error rate. Predict the table first.

```
English  →  (untrusted) parse  →  (deterministic) proof
         →  how-polynomial     →  any later question is specialize()
```

Traceable means a proof object whose leaves are axiom ids.
Replicable means: same parse, same proof. The LLM is not consulted
again. ContextCite (next week) attributes *tokens*; this attributes
*derivations*. They are different questions.

## Files

| File | What it is |
|---|---|
| `fixtures.py` | **Provided** — three stories, gold FOL, labels |
| `fol.py` | AST, finite-domain grounding, NNF |
| `parser.py` | `Parser` protocol + `GoldParser` |
| `faults.py` | Operational faults, L1/L2/L3, `FaultyParser` |
| `prover.py` | Saturate, `{True, False, Uncertain, Error}`, proof |
| `pipeline.py` | translate then prove; optional majority vote |
| `sweep.py` | accuracy vs parse-error rate |
| `trace.py` | how-polynomial of the proof (needs semirings) |

```bash
python3 check.py          # 8 graded checks against YOUR code
```

Do [`../provenance-semirings/`](../../week-06/provenance-semirings/) first — the
last check imports it. s(CASP) is the richer engine; this prover is
the one LINC actually calls (a FOL solver with a label). You will
recognise the justification tree when you meet it.

## Done means

- 8/8.
- Gold parse is 3/3. Rate 1.0 is worse. The table is monotone.
- `lineage_of(p1)` is `{p0,p1,p2}` via `specialize`, not via a list
  you appended by hand.
- You can say what "faithful" means when the label is right and
  the axiom set is not.
