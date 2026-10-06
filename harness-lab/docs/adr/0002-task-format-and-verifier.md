# ADR 0002 — Task format and verifier isolation

Status: accepted (phase 0)

## Decision
A task is a directory: `task.toml` (statement, earlier user turns, category, `targets`),
`repo/` (+ optional deterministic `generate.py`), `hidden/` tests and a `solution/` overlay.

The verifier runs in a **fresh** container that sees only the exported `/work`:
- hidden tests are copied in only after the agent's container is destroyed;
- `python -I` (no PYTHONPATH, no user site): a planted `sitecustomize.py` never runs;
- `--rootdir=/hidden` and `-p no:cacheprovider`: a `conftest.py` or `pytest.ini` in `/work`
  is never collected; `/work` reaches `sys.path` through our own injected conftest.

## Evidence
`tests/test_docker.py::test_planted_files_cannot_fake_a_pass` plants five cheats. Three of them
(sitecustomize, conftest, pytest.ini) were checked to **fool a naive verifier** (`cd /work &&
PYTHONPATH=/work pytest`, exit 0) and to fail against this one. A test that passes against both
would prove nothing; this one was checked to have teeth.

## Known holes (accepted, documented)
- An agent can still special-case the hidden inputs if it guesses them (e.g. hard-coding
  `export()` output for t13). Hidden tests use several inputs where cheap; no defence beyond that.
- Structural checks (AST, "no regex in handlers.py") are proxies for intent and can reject an
  unusual but correct solution. They are limited to refactor tasks, where behaviour tests alone
  cannot tell a refactor from no change.

## Generated repositories
Tasks whose repo is too large to commit (t15, t16, t17, t19) generate it with a seeded RNG.
Determinism is tested (`test_materialize_is_deterministic`), and t19's hard-coded answer is
recomputed from the generated log in `test_huge_log_expected_answer_matches_generated_log`.
