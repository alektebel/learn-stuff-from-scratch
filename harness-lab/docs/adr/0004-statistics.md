# ADR 0004 — Paired comparisons and power, decided before any agent exists

Status: accepted (phase 0)

## Decision
- Variants are compared **paired by task**, with an exact McNemar test on discordant pairs.
- `n` counts **tasks**. Seeds of one task are correlated; treating 20 tasks × 3 seeds as n = 60
  overstates certainty. The report prints this caveat whenever several seeds are pooled.
- Success rates are reported with Wilson intervals (well-behaved at 0/n and n/n, which the
  control agents hit by design).
- Minimum detectable effect is computed with Connor's (1987) approximation, `eval/stats.py`.

## The number that matters
`python -m eval.stats power` (alpha 0.05, power 0.8):

| tasks | psi=0.1 | psi=0.2 | psi=0.3 | psi=0.4 |
|---|---|---|---|---|
| 20  | none | none | none | 37.3 pp |
| 50  | none | 17.3 pp | 21.2 pp | 24.5 pp |
| 70  | none | 14.7 pp | 18.0 pp | 20.8 pp |
| 150 | 7.2 pp | 10.1 pp | 12.4 pp | 14.4 pp |

psi = share of tasks on which two variants disagree.

**With the 20-task suite alone, no plausible difference in success rate between two variants is
detectable.** With the planned 50 SWE-bench tasks (70 in total), only differences of roughly
15–20 points are. Harness mechanisms with the same model usually differ by less. Consequences:
1. Success-rate claims in phase 6 will mostly be "not detectable at this n"; that is a valid,
   reportable result.
2. Cost metrics (tokens, turns, cache hits) are the primary comparison: continuous, far lower
   variance, and paired tests on them (Wilcoxon) need far fewer tasks.
3. The suite's job is mechanism coverage (amendment 2), not statistical power.

The normal approximation is crude at small n; for n = 20 it is indicative only.
