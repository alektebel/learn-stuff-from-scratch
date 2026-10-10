# Infrastructure as Code and Drift From Scratch

Parse a declarative resource spec and a current-state document, diff them into
`create` / `update` / `delete` actions, and order those actions by dependency so
the plan is safe to apply. Pure Python 3, standard library only — the spec and
the state are ordinary dicts (JSON), so there is no AWS SDK, no credentials and
no network.

Source: AWS CloudFormation documentation (`awsdocs:cloudformation`) — template
anatomy (`Resources`, `Type`, `Properties`, `DependsOn`), stack updates and
change sets. Everything here is restated from scratch; nothing is copied.

This is the cloud track's capstone: it ties the primitives together the way a
deployment tool does — it consumes a desired shape (`cloud/04-vpc-routing`,
`cloud/02-iam-policy` shaped resources) and the deployed shape, and decides what
to change.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| The documents | parse spec + state, validate, canonical comparison | `spec.py` | 1-2 |
| The dependency graph | dependents map, cycle detection | `spec.py` | 3 |
| The diff | create / update / delete; empty when nothing changed | `planner.py` | 4-5 |
| Ordering | creates after their deps, deletes after their dependents | `planner.py` | 6 |
| Limit: rename | create-before-destroy for a stateful resource | `planner.py` | 7 |
| Limit: cycle | reported, never recursed into | `planner.py` | 8 |

## How to use this directory

The top-level files are **templates**: each function keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`.
`solutions/` holds complete versions for when you are stuck, or to compare
afterwards.

```bash
cd cloud/05-iac-drift
python3 check.py        # what to build next; stops at the first gap
python3 check.py 4      # one step
python3 check.py --all  # everything
```

`check.py` runs 8 checks against **your** code and never imports `solutions/`.
Every `accept` and every `limit_cases` item from the skill-tree node is one of
those steps.

## The measurements

Run the solutions and predict each line before you look:

```bash
python3 solutions/spec.py      # parsing, canonical equality, cycle detection
python3 solutions/planner.py   # a real plan: diff then order
```

`solutions/planner.py` prints:

```
plan for a spec with one create, one update and one delete:
  1. delete legacy
  2. update web (ami)
  3. create cache

idempotent when state == spec: True
stateful rename db -> db-prod: [('create', 'db-prod'), ('delete', 'db')]  create first: True
cycle: dependency cycle: a -> b -> a
```

The plan has **3 actions** (`delete legacy`, `update web (ami)`, `create cache`)
and the same documents compared to themselves give **0 actions** — that is the
whole point: applying an up-to-date state does nothing. The rename produces the
create **first**, and the cycle is a message, not a stack overflow.

## Design decisions, named

Each file opens with its decisions and their cost. In short:

- **One `Resource` shape for spec and state** (`spec.py`). The diff then compares
  like with like instead of translating between a template and the provider's
  response shape. Cost: physical ids are dropped, so resources can only be
  matched by logical name.
- **Equality is canonical, not textual** (`spec.py`). `type` plus JSON with
  sorted keys; `depends_on` and `lifecycle` are metadata. Cost: a rename that
  also changes a property is not recognised as a rename.
- **A cycle is a planning condition, not a parse error** (`spec.py`,
  `planner.py`). `parse_document` accepts a cyclic template; `plan` reports it
  with `DependencyCycle` and names the loop. Cost: a caller that parses but does
  not plan must ask for the cycle itself.
- **Diff and order are separate phases** (`planner.py`). The diff is a pure set
  comparison (empty iff nothing changed); ordering is a graph problem with its
  own limit case. Cost: ordering rebuilds the edges the diff did not need.
- **Destroy-first by default, overridden for a stateful rename** (`planner.py`).
  Unrelated actions run in a fixed priority (delete, update, create, then name)
  so the plan is deterministic; a stateful rename pins its create before its
  delete. Cost: a stateless rename is torn down before it is rebuilt.

## Questions to answer before reading the solutions

1. Why compare resources canonically instead of comparing their `dict`s
   directly? Construct a state that is genuinely equal to the spec but compares
   unequal without `sort_keys`.
2. CloudFormation says a dependency must be created first. What is the delete
   order, and why is it the reverse?
3. A rename produces a create *and* a delete. For a stateless web server, either
   order works. For a database, only one does. Say which, and what the other
   order costs.
4. A cycle produces no useful plan. Why must it be detected even when the two
   documents are otherwise identical and no action would be produced?
5. Two actions are unrelated. Does the plan's order matter at all? If not, why
   make it deterministic anyway?

## The checker was itself tested

Nine classic bugs were planted in copies of the solutions; each must be caught
by its check:

| Planted bug | Caught by |
|---|---|
| a resource type is not validated | step 1 |
| canonical comparison ignores property key order | step 2 |
| cycle detection never sees the back-edge | step 3 |
| a changed attribute is not an update | step 5 |
| a removed resource is not deleted | step 5 |
| dependencies do not order the creates | step 6 |
| dependents are not deleted before their dependencies | step 6 |
| a stateful rename is destroy-before-create | step 7 |
| the plan ignores a dependency cycle | step 8 |

Every one is caught; the mutations live in `_build/mutations.py` and are run with
`.claude/skills/graded-module/scripts/mutate.py`.

## Limits

- **No provider, no apply.** The plan is computed and printed; nothing is
  created or destroyed, and no resource provider is called.
- **Rename detection matches identical configuration.** A rename that also
  changes a property is reported as an unrelated create and delete. That is what
  the diff honestly says without a `moved`/`import` hint.
- **No replacement semantics beyond renames.** Changing an immutable property
  (which a real provider would implement as destroy-then-create) is modelled as
  an in-place `update`; the module has no per-property replacement table.
- **No imports, outputs, parameters or providers.** A template that references a
  resource outside the document is rejected; there are no data sources.
- **One dependency edge type.** `depends_on` is explicit; there is no implicit
  edge inference from a property that embeds another resource's id.
- **Cycles are reported, not resolved.** The module names a loop and stops; it
  does not suggest which edge to cut.
