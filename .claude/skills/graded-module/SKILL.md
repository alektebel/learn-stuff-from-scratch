---
name: graded-module
description: Build or modify a graded learning module in this repository (templates + check.py + solutions/ + _build/). Use when creating a new from-scratch module, adding steps or checks to an existing one, regenerating templates, or mutation-testing a checker.
---

# Graded module

The format every from-scratch module in this repo follows. Canonical examples to copy from:
`database-from-scratch/` (stdlib only) and `ml-systems/framework/` (numpy). Read
`PHILOSOPHY.md` at the repo root first: design decisions named, MVP then limit cases,
verification you can run.

## Layout

```
<module>/
  README.md        table of steps, how to run, design decisions, questions WITHOUT answers, limits
  check.py         graded checks; never imports solutions/
  <file>.py ...    templates (generated, never hand-edited)
  solutions/       complete implementations + README.md with expected demo output
  _build/
    hints.py       HINTS = {"file.py": {"func_or_Class.method": "graded hint"}}
    mutations.py   MUTATIONS = [(description, file, old_text, new_text, check_step)]
```

## Procedure

1. **Solutions first.** Write `solutions/*.py` completely. Each file opens with a docstring:
   what it implements (cite the source: paper section, book chapter), and every
   `DESIGN DECISION - <question>` with the alternatives and the cost of the choice made.
   Give each file a `__main__` demo that prints a measurement.
2. **check.py.** Copy the runner from `database-from-scratch/check.py` (CHECKS list,
   `run_one`, `main`, TODO/FAIL/ERROR handling, stop at first gap, `--all`, step ranges,
   `sys.dont_write_bytecode` + clearing `__pycache__`). One function per step. Assertion
   messages name the likely CAUSE, not just the symptom.
3. **Run check.py against the solutions** in a temporary copy (copy `solutions/*.py` and
   `check.py` together). Every step must pass.
4. **Templates.** Write `_build/hints.py`, then
   `python3 .claude/skills/graded-module/scripts/make_templates.py <module> <module>/_build/hints.py`.
   Verify: `python3 check.py --all` on the templates reports every step as TODO, none as
   FAIL or ERROR; and with only the first file's solution copied in, the first steps pass
   and the checker points at the next one.
5. **Mutation test.** Write `_build/mutations.py`: at least one planted bug per file, each a
   classic mistake for that mechanism. Run
   `python3 .claude/skills/graded-module/scripts/mutate.py <module> <module>/_build/mutations.py`.
   Every mutation must be CAUGHT. If one is MISSED, strengthen the check; never weaken
   or drop the mutation.
6. **Docs.** Module README (state the mutation table), `solutions/README.md` with the
   expected output, one line in the root `README.md` under the right section.
7. Delete every `__pycache__`, commit.

## Mistakes already made in this repo (do not repeat them)

- **Random data does not hit limit cases.** A randomised B-tree test never clustered large
  entries in one half, so a count-based split passed. Construct the limit case
  deterministically.
- **One defence masking another.** A corrupted byte broke the JSON before the missing CRC
  check mattered. Corrupt in a way that only the defence under test can catch.
- **Module names shadowing the stdlib.** `profile.py` shadows `profile`, which `cProfile`
  imports. Check new file names against the standard library.
- **Constants inside a graph.** Autograd ran `_backward` on constant nodes that never
  received a gradient. Every check suite needs a case mixing constants with tracked values.
- **A schedule hiding the phenomenon.** A dirty read let the second transaction see the
  first one's write, which hid a write skew. When demonstrating an anomaly, do all reads
  before any write.
- **A checker that only proves the solution passes proves nothing.** Step 5 is not optional.
