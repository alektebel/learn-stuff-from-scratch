# Provenance Semirings From Scratch

Evaluate a query once in ℕ[X] (the free commutative semiring). Lineage,
why-provenance, bag semantics, trust, security, and min-cost are then
homomorphisms of that one result. You never re-run the query.

> **Green, Karvounarakis, Tannen. "Provenance Semirings." PODS 2007.**
> [paper](https://dl.acm.org/doi/10.1145/1265530.1265535)

If the homomorphism property holds, you built the right thing. If it
does not, you built an annotation scheme — which is what most systems
ship, and why they cannot answer a question they were not designed for.

This directory is the algebra. [`../scasp/`](../../week-07/scasp/) is the engine
that emits a proof object. [`../linc/`](../../week-08/linc/) is the LLM-shaped
front end that is only allowed to *parse*. ContextCite, SPADE and
MARS-SQL (later this phase) attribute tokens and columns. They cannot
tell you *how* an answer was derived. This can.

## The payoff

```
h( Q_ℕ[X](I) )  =  Q_K( h(I) )
```

Same query, same instance, two ways: specialize the polynomial, or
evaluate directly in K. They must agree for every K in the table.
That is check 5. Check 6 is the objection: lineage of `(Ada, Bar)` is
four sources, bag is two derivations, min-cost is 7. A set of ids
cannot produce the 2 or the 7 without running Q again.

## The eight semirings

| K | ⊕ | ⊗ | 0 | 1 | Asks |
|---|---|---|---|---|---|
| **how** ℕ[X] | + | × | 0 | 1 | the derivations themselves |
| **why** | ∪ | pairwise ∪ | ∅ | {∅} | the witnesses |
| **lineage** | ∪ | ∪ | ∅ | ∅ | which tuples appear |
| **boolean** | ∨ | ∧ | ⊥ | ⊤ | exists? |
| **bag** | + | × | 0 | 1 | how many |
| **trust** | max | × | 0 | 1 | most-trusted path |
| **security** | min | max | ∞ | 0 | least clearance that works |
| **tropical** | min | + | ∞ | 0 | cheapest path |

## Recursion

Positive RA is a polynomial. Datalog is a least fixpoint. That
fixpoint is finite iff K is *absorptive*: `a ⊕ (a ⊗ b) = a`. ℕ[X]
is not. On a cycle, How must raise, not truncate. Tropical and
Boolean finish. That is the last check.

## Files

| File | What it is |
|---|---|
| `instance.py` | **Provided** — Likes/Serves, valuations, a tiny graph |
| `semiring.py` | The eight instances |
| `polynomial.py` | Sparse ℕ[X] |
| `homomorphism.py` | `specialize`, and a hom-checker |
| `relation.py` | Annotated relations, compact on ⊕ |
| `ra.py` | σ, π, ⋈, ∪ — and the running query |
| `datalog.py` | Fixpoint, absorption, refuse the cycle |

```bash
python3 check.py          # 8 graded checks against YOUR code
```

Checks only. Templates raise `NotImplementedError`. No `solutions/`.
Do this directory before s(CASP) and before LINC.

## Done means

- 8/8.
- You can say, without opening a file, why a set of source ids cannot
  answer "what did this cost" and "how many ways" at the same time.
- You refused to finish a cyclic path query in ℕ[X].

## Sources

- Green, Karvounarakis & Tannen, **"Provenance Semirings"**, PODS 2007 — the whole directory. **Prop. 3.4** is the universality theorem `check.py` tests.
- Cheney, Chiticariu & Tan, **"Provenance in Databases: Why, How, and Where"**, FnTDB 2009 — the taxonomy, and where lineage loses information.
- Green & Tannen, **"The Semiring Framework for Database Provenance"**, PODS 2017 — absorption, ω-continuity, and recursion.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-6--provenance-semirings)
