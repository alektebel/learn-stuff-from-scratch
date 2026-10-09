# RESOURCES — stats_engine (agent-evals #7)

How to read this list: each entry says why it matters for THIS module and is
restated in our own words (cite and restate, never copy). `[v]` = confident
it exists as cited; `[verify]` = written from memory, confirm the details
later.

## The bootstrap itself

1. Efron & Tibshirani, *An Introduction to the Bootstrap*, Chapman & Hall,
   1993 — chapters 2–5 and 13. `[v]`
   Why: the percentile interval this module implements, and how to think
   about the number of resamples (10,000 is generous for a 95% band).
   Restated: treat your sample as if it were the population, redraw the
   units with replacement, recompute the statistic on each redraw, and read
   the interval off the percentiles of that distribution.

2. Efron, "Bootstrap Methods: Another Look at the Jackknife", *Annals of
   Statistics* 7(1), 1979. `[v]`
   Why: the origin; shows the bootstrap as a plug-in estimate of the unknown
   sampling distribution.
   Restated: you cannot rerun the world, so approximate the world by your
   own data and perturb it the way sampling would.

3. Davison & Hinkley, *Bootstrap Methods and Their Application*, Cambridge
   University Press, 1997. `[v]`
   Why: the pairs/cluster resampling discussion — our "resample tasks" is
   their clustered-data case.
   Restated: when observations come in clusters, resample whole clusters and
   never split the rows inside one; otherwise you invent information the
   clusters do not contain.

## Resampling units (the point of the project)

4. Field & Welsh, "Bootstrapping Clustered Data", *Journal of the Royal
   Statistical Society, Series B* 69(3), 2007. `[verify]`
   Why: the formal statement behind limit case L1 — the cluster (here the
   task) is the unit, and ignoring clustering underestimates variance.
   Restated: correlated copies of a task are one piece of evidence, not
   many; the run-level bootstrap counts them many times.

5. In-repo: `harness-lab/eval/stats.py` (Wilson intervals, McNemar, MDE). `[v]`
   Why: the sibling implementation to cross-check against (Acceptance 10) —
   read it, do not copy it; note that it reasons per-run while this module
   deliberately reasons per-task.
   Restated: its Wilson interval and McNemar are exact small-sample tools
   for binary data; the bootstrap here trades exactness for flexibility
   about the statistic being compared.

## Paired binary tests

6. McNemar, "Note on the sampling error of the difference between correlated
   proportions or percentages", *Psychometrika* 12(2), 1947. `[v]`
   Why: the exact test our bootstrap p approximates when per-task outcomes
   are binary (Acceptance 10).
   Restated: throw away the tasks both variants agree on; under the null the
   two discordant counts split like fair coin flips, and the exact p comes
   from that binomial.

7. Wikipedia: "McNemar's test" and "Bootstrapping (statistics)". `[v]`
   Why: quick refreshers on the concordant/discordant bookkeeping and the
   percentile-vs-basic-vs-BCa interval zoo.
   Restated: for paired binary data only the disagreements carry signal; the
   percentile interval is the simplest of the bootstrap intervals and the
   one worth implementing first.

8. Ernst, "Permutation Methods: A Basis for Exact Inference", *Statistical
   Science* 19(4), 2004. `[verify]`
   Why: the contrast class for our p-value — resampling to *test* vs
   resampling to *estimate an interval*.
   Restated: shuffling labels under the null answers a different question
   than redrawing units under the data; our bootstrap p leans on the second
   and is approximate, which is why the exact cross-check exists.

## Where the requirement comes from

9. `agent-evals/README.md`, project row #7. `[v]`
   Why: names the paired-design correction this module teaches — same task
   set ⇒ paired data ⇒ task-level resampling; run-level resampling is
   anti-conservative (too-narrow CIs, too-small p-values).
   Restated in one line: the unit of evidence is the task, and every
   statistic in this module must say `unit == "task"`.
