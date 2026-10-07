---
name: skill-tree-worker
description: Work on the math / pattern-recognition skill tree (skill-tree/tree.toml): pick a ready node, build its graded module under math/, verify it, mark it done. Use when asked to continue the skill tree, build a math or PRML/Bishop/MML/Boyd/Axler/Blitzstein exercise module, or add nodes or books to the tree.
---

# Skill tree worker

The tree is `skill-tree/tree.toml` (nodes) and `skill-tree/books.toml` (books). Each node
becomes one graded module at its `deliverable` path, in the format of the `graded-module`
skill. Read that skill before building anything.

## Pick a node

```bash
python3 skill-tree/tree.py check          # must be OK before you start
python3 skill-tree/tree.py next           # ready nodes: todo with every prerequisite done
python3 skill-tree/tree.py show <id>      # build / accept / limit_cases for one node
```

Take one ready node. Set its `status = "in-progress"` in `tree.toml` and commit that alone,
so parallel workers do not collide. One node per commit series; do not start a second
node before the first is done.

## Build it

- `build` lists what the learner implements: one template function group per item.
- **Every `accept` item and every `limit_cases` item becomes a check in `check.py`.** A
  limit case is a check that a naive implementation FAILS; write the naive version as a
  mutation in `_build/mutations.py` and confirm it is caught.
- **Derivations are verified numerically:** gradients by central finite differences
  (relative error < 1e-6 in float64); expectations by Monte Carlo with a fixed seed and a
  tolerance of 4 standard errors computed from the sample, not a guessed epsilon; closed
  forms against simulation. Until `foundations-04-vector-calculus` exists, put a small
  finite-difference helper inside `check.py` (as `ml-systems/framework/check.py` does).
- numpy is allowed (run with `python3`); no scipy or sklearn in templates or solutions.
  A check may compare against `numpy.linalg` as a reference.
- Cite sources in each solution's docstring as in `sources` (for example "Bishop 9.2").
  For book exercises: cite the number, restate the task in your own words, never copy the
  statement, a figure, or a published solution. If `books.toml` marks access as "verify",
  check it before citing it as fact.
- Keep the module small enough to finish: 6-15 checks. If a node is larger, split it
  into two nodes in `tree.toml` (with the dependency between them) before building.

## Finish it

1. Graded-module procedure steps 3-5 all green (solutions pass, templates all TODO,
   every mutation caught).
2. In `tree.toml`, set `status = "done"`.
3. `python3 skill-tree/tree.py check` (it refuses `done` without a `check.py`, or with an
   unfinished prerequisite), then `python3 skill-tree/tree.py render`.
4. `python3 -m unittest skill-tree/test_tree.py`.
5. Commit: the module, `tree.toml`, the regenerated `skill-tree/README.md`.

## Changing the tree itself

Adding a book: an entry in `books.toml` with an honest `access` note. Adding or splitting
nodes: keep ids `<track>-NN-slug`, keep `requires` minimal (only true prerequisites), and
give every node concrete `accept` and `limit_cases`. `tree.py check` must stay OK.
