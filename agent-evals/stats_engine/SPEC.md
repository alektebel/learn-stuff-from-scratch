# stats_engine — paired bootstrap over tasks (agent-evals #7)

## What it is

A standard-library-only module that compares two agent variants run on the
SAME task set and answers one question honestly: is A better than B, by how
much, and how sure are we? It reports the mean difference in per-task
success, a percentile bootstrap confidence interval for that difference, and
a two-sided bootstrap p-value — all computed by resampling **tasks**, never
runs.

LEARN mode: `parse_jsonl` and `summarise_by_task` are shipped **implemented**
as test infrastructure (decided: implemented — they are the plumbing the
tests need to build paired inputs, not the point of the project). The four
statistical entry points (`paired_bootstrap_ci`, `paired_bootstrap_p`,
`compare`, `main`) are `NotImplementedError` stubs; the tests define what the
learner must make true.

## What it demonstrates

The paired-design correction recorded in `agent-evals/README.md` (row #7):
when both variants are evaluated on a common task set, their outcomes are
**paired by task**, and the task — not the run/episode — is the resampling
unit. A variant often gets several correlated attempts per task (seeds,
retries); those attempts are not independent evidence. Resampling runs
instead of tasks inflates the effective sample size (n_runs instead of
n_tasks), so confidence intervals come out too narrow and p-values too small
— exactly the self-flattering mistake an eval harness must not make. Limit
case L1 below makes the learner measure this effect on purpose.

## The interface

```python
REQUIRED_FIELDS = ("agent", "task_id", "success")

def parse_jsonl(lines: Iterable[str]) -> list[dict[str, Any]]: ...
    # infrastructure, implemented. JSONL run records of the harness-lab
    # eval/contract.py shape (agent, task_id, success). Blank lines skipped;
    # ValueError on invalid JSON, missing field, or success not bool/0-1.

def summarise_by_task(records: Iterable[Any]) -> dict[str, dict[str, bool]]: ...
    # infrastructure, implemented. task_id -> {agent_name: success}; accepts
    # dict records and attribute-style records. ValueError if the same agent
    # appears twice on a task, or if the per-task agent sets differ (not
    # paired).

def paired_bootstrap_ci(a_passes, b_passes, *, n_resamples=10000,
                        confidence=0.95, seed=0) -> tuple[float, float]
    # STUB. Percentile CI for mean(a) - mean(b); a_passes/b_passes are
    # per-task outcomes, equal length, index i = task i. Each resample draws
    # n task indices with replacement and uses the SAME indices for both
    # variants. ValueError on length mismatch or confidence outside (0, 1).

def paired_bootstrap_p(a_passes, b_passes, *, n_resamples=10000, seed=0) -> float
    # STUB. Two-sided p: min(1, 2 * min(#{d* <= 0}, #{d* >= 0}) / B) over the
    # B resampled mean differences d*. Ties (d* == 0) count on BOTH sides, so
    # identical variants give p = 1.0.

def compare(a_records, b_records, *, seed=0) -> dict
    # STUB. Reduces both record streams with summarise_by_task and returns a
    # dict with EXACTLY the keys: n_tasks (int), mean_diff (float),
    # ci (lo, hi), p (float), unit ("task").

def main(argv: Sequence[str] | None = None) -> int
    # STUB. CLI: python -m stats_engine --a a.jsonl --b b.jsonl
    # [--n-resamples N] [--confidence X] [--seed K]. Prints the compare()
    # report as JSON; returns 0.
```

## Acceptance

1. **Record parsing.** `parse_jsonl` turns JSONL lines (blank lines allowed)
   into record dicts; a line missing a required field raises `ValueError`; a
   `success` that is neither bool nor 0/1 raises `ValueError` (no string
   coercion). Tests: `test_parse_jsonl_reads_records`,
   `test_parse_jsonl_missing_field_raises`,
   `test_parse_jsonl_rejects_non_boolean_success`. (Passes today.)
2. **Grouping.** `summarise_by_task` maps task_id → {agent: success} and
   accepts dict and attribute-style records. Tests:
   `test_summarise_by_task_maps_task_to_agent_success`,
   `test_summarise_by_task_accepts_attribute_records`. (Passes today.)
3. **Pairing enforced.** Task sets must match across agents and each
   (task, agent) may appear once; violations raise `ValueError` instead of
   silently producing a "paired" report. Tests:
   `test_summarise_by_task_unequal_task_sets_raises`,
   `test_summarise_by_task_rejects_duplicate_run`. (Passes today.)
4. **CI.** `paired_bootstrap_ci` returns `(lo, hi)` floats, `lo <= hi`,
   resampling tasks with the pairing preserved: identical variants → the CI
   is the degenerate point `(0.0, 0.0)` (the per-task difference is 0 on every
   resample); strongly separated variants (18/20 vs 2/20) → the CI excludes 0.
   Tests: `test_ci_identical_variants_covers_zero`,
   `test_ci_identical_variants_is_exactly_zero`,
   `test_ci_separated_variants_excludes_zero`.
5. **Determinism.** Same seed ⇒ identical CI and identical p across calls.
   Test: `test_deterministic_under_fixed_seed`.
6. **Input validation.** Length-mismatched per-task lists raise `ValueError`
   (never a silent zip-truncate); bad `confidence` raises `ValueError`.
   Test: `test_ci_length_mismatch_raises_value_error`.
7. **p-value.** In [0, 1]; identical variants → ≥ 0.5 (exactly 1.0 with the
   tie rule above); 10-vs-0 discordant pairs → < 0.05. Test:
   `test_p_value_matches_sign_of_effect`.
8. **Report shape.** `compare` returns exactly the keys `n_tasks`,
   `mean_diff`, `ci`, `p`, `unit`; `unit == "task"`; `n_tasks` and
   `mean_diff` match the input pairs. Test: `test_compare_report_shape`.
9. **CLI.** `main(["--a", fa, "--b", fb, "--seed", "3"])` reads both JSONL
   files, forwards the seed to `compare`, prints the report as JSON, and
   returns 0. Test: `test_main_cli_smoke`.
10. **Cross-check (optional).** With harness-lab's `eval` package importable,
    the bootstrap p agrees with an exact McNemar test's verdict on the same
    paired binary data. Test: `test_mcnemar_cross_check_with_eval_stats`
    (skips when `eval.stats` is not importable).

## Limit cases

- **L1 — wrong unit, too-narrow CI.** On data with several perfectly
  correlated seeds per task (40 tasks × 5 seeds), a naive run-level
  bootstrap built *in the test* (resampling the 200 runs, ignoring task
  clustering) yields a NARROWER CI than the module's task-level CI; the
  module's CI must be the wider one (theory: ~√5 wider). The naive helper
  lives in the test on purpose — the core must not grow a wrong-unit mode.
  Test: `test_task_ci_is_wider_than_naive_run_resampling`.
- **L2 — n = 1 task.** Degenerate but no crash: `paired_bootstrap_ci([1],
  [0])` returns well-formed floats and `paired_bootstrap_p` a value in
  [0, 1]. Test: `test_single_task_degenerate_no_crash`.
- **L3 — length mismatch.** Never silently truncates; raises `ValueError`.
  Test: `test_ci_length_mismatch_raises_value_error`.
- **L4 — unpaired data.** Unequal task sets or a duplicated (task, agent)
  run raise `ValueError` at the grouping step, before any statistic runs.
  Tests: see Acceptance 3.
- **L5 — unpaired resampling.** With identical per-task outcomes, an
  implementation that draws a separate resample for each variant (ignoring
  the alignment) returns a non-degenerate interval where the paired one is
  exactly `(0.0, 0.0)`. Test: `test_ci_identical_variants_is_exactly_zero`.

## Out of scope / blocked

- **No numpy/scipy/pip.** Environment constraint: standard library only.
- **No BCa or bias-corrected intervals.** MVP is the percentile interval;
  better intervals are an extension, not a requirement.
- **No permutation/sign-flip test.** A natural variant of the p-value; left
  as an exercise. The bootstrap p defined here is not an exact test — that
  is why Acceptance 10 cross-checks against McNemar instead of claiming
  equivalence.
- **No Wilson/MDE/McNemar implementations here.** They live in
  `harness-lab/eval/stats.py` and work per-run; this module works per-task.
  The optional integration test only cross-checks, and skips when that
  package is not importable from this checkout.
- **No seed-level aggregation policy.** Multi-seed data must be reduced to
  per-task outcomes by the caller (any/all/majority is a semantic choice the
  module refuses to guess — hence the duplicate-run ValueError).
- **No plotting, no report tables, no unpaired (two-sample) bootstrap.**

## How to run

```sh
cd agent-evals
python3 -m pytest -q tests/test_stats_engine.py
# today: the infrastructure tests pass, the core tests xfail
# (raises=NotImplementedError), zero failures/errors expected.

# CLI (works once the core is implemented; raises NotImplementedError today):
python3 -m stats_engine --a runs-a.jsonl --b runs-b.jsonl --seed 0
```

The test file puts the project directory on `sys.path` itself, so it runs
with or without a conftest.

## Design decisions

- **Resampling unit = task** (the paired-design correction from
  `agent-evals/README.md` #7): paired data ⇒ resample the task pair, one
  draw feeding both variants. Cost: every entry point needs task-level
  inputs, so seed-level streams must be reduced first, and unequal task sets
  are fatal (`ValueError`) rather than papered over.
- **Percentile bootstrap CI**, not BCa or a normal approximation: a few
  dozen lines of stdlib. Cost: known bias at extreme quantiles and small n;
  acceptable for success-rate differences bounded in [−1, 1].
- **p-value from the same resamples as the CI**, two-sided, ties counted on
  both sides: one resampling loop serves both numbers. Cost: not exact for
  binary pairs — McNemar is, so we cross-check (Acceptance 10) instead of
  claiming equivalence.
- **`parse_jsonl` + `summarise_by_task` shipped as infrastructure**, core
  functions as stubs. Cost: the pass/xfail split of the suite states
  honestly what exists; the grouping strictness (ValueError on duplicates
  and mismatched agent sets) is part of the contract, not an accident.
- **Explicit `seed` per entry point, private `random.Random`**: no global
  RNG state, no `PYTHONHASHSEED` dependence. Cost: reproducibility is
  opt-in per call; two calls with different seeds legitimately differ.
- **CLI returns an int and prints JSON**: composable with other tooling.
  Cost: no human-friendly table output.
