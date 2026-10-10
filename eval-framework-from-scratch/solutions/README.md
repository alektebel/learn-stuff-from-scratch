# Solutions

Finished, runnable versions of each stage. Read them *after* attempting — a
solution read cold is just more prose.

| File | Stage |
|---|---|
| `stage_01.py` | The suite config: unknown keys refused, defaults materialised, identities unique |
| `stage_02.py` | Metric plugins: resolved before the run, errors filed by metric name |
| `stage_03.py` | One case, one record: an injected clock, a discarded late answer, the right blame |
| `stage_04.py` | The run: declared order, adjacent repeats, budgets checked before the call |
| `stage_05.py` | Aggregation whose unit is the case, and the verdict that says why it is unstable |
| `stage_06.py` | The judge session: cached, budgeted, and asked twice in both orders |
| `stage_07.py` | Canonical records: sorted keys, rounded values, a truncated last line |
| `stage_08.py` | The gate and the four exit codes, invalid before failed |
| `stage_09.py` | The baseline diff: a regression has to beat the noise of both runs |
| `stage_10.py` | The resume: a hash of the effective config, budgets that carry over, bytes that match |

The stages are cumulative in the way the course is: stage 3 imports stage 2's
`apply_metrics`, stage 4 runs stage 3's `run_case`, stage 5 reads the records
those produce, stage 8 imports stage 5's two thresholds, stage 9 imports stage
3's precision, and stage 10 resumes through stage 7's `RunLog` and stage 4's
order. So copying one solution over its template needs its neighbours in place
too, and `lab.py` is not a stage: it is the task set, the solvers, the judges and
the clock, provided complete.

To compare a stage, copy it over the template and re-run the checker, then
restore the template if you want to try again:

```bash
cp solutions/stage_08.py stage_08.py
python3 codecraft/cli.py run eval-framework-from-scratch
```

All ten pass their checks with the standard library alone. Four are worth reading
even if you solved them: `stage_04.run_suite` is where the whole framework's
honesty lives — a budget checked before the call, a log that holds only what
happened, counters that come from the records; `stage_05.aggregate` is the stage
where "the unit is the case" stops being a sentence and becomes a weighted mean
over cases whose repeats were already averaged; `stage_06.JudgeSession` is a
cache with a budget and a vocabulary, which is what a judge protocol actually is;
and `stage_10.resume_run` is the one function whose result is checked as bytes.
