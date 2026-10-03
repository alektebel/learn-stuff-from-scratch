# s(CASP) From Scratch

A goal-directed ASP engine. The result of a query is not a boolean.
It is a **justification tree** you can replay.

> **Arias, Carro, Salazar, Marple, Gupta. "Constraint Answer Set
> Programming without Grounding." TPLP 2018.**
> [paper](https://arxiv.org/abs/1804.11162)

clingo grounds the whole program, then solves. s(CASP) never grounds:
it runs the query, generates *dual rules* so negation is a call, and
closes *even loops* coinductively. That is why it can say *why*
tweety does not fly, and why `not p(X)` can return a binding.

This directory is the engine. [`../provenance-semirings/`](../../week-06/provenance-semirings/)
is the algebra you will eventually hang off the tree. [`../linc/`](../../week-08/linc/)
is the front end that is only allowed to parse.

## The ladder

| MVP | Limit case that forces the next file |
|---|---|
| Unification | `X = f(X)` — occurs check, or you build an infinite term |
| SLD (Prolog) | `p :- q. q :- p.` — SLD diverges |
| Dual rules | `not p(X)` must *bind* X, not just fail |
| CoSLD | the even loop is a *success*, the odd loop is not |
| Justification | a substitution cannot answer "why" |

## Files

| File | What it is |
|---|---|
| `program.py` | **Provided** — EVEN_LOOP, ODD_LOOP, MEMBER, FLIES, UNIT |
| `term.py` | Apply, collect, rename |
| `unify.py` | MGU with occurs |
| `sld.py` | Positive Prolog; even loop returns None |
| `dual.py` | Clark duals, `neq`, De Morgan on conjuncts |
| `coinductive.py` | Even-ancestor success, odd-ancestor fail |
| `justify.py` | The tree; `atoms_used` is the lineage |

```bash
python3 check.py          # 8 graded checks against YOUR code
```

Checks only. Templates raise `NotImplementedError`. No `solutions/`.
Do [`../provenance-semirings/`](../../week-06/provenance-semirings/) first if you
want the algebra in your head; this engine does not import it.

## Done means

- 8/8.
- SLD on the even loop is None; coSLD is a tree marked `coinductive`.
- `flies(opus)` cites `sparrow(opus)` and does not cite `penguin(tweety)`.
