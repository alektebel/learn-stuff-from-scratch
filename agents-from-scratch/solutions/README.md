# Solutions

Finished, runnable versions of each stage. Read them *after* attempting — a
solution read cold is just more prose, and these are short enough to fool you
into thinking the stage was easy.

| File | Stage |
|---|---|
| `stage_01.py` | The loop, and the transcript that is the state |
| `stage_02.py` | The tools the model can see |
| `stage_03.py` | The toolbox: a failure is an observation |
| `stage_04.py` | What the model actually said |
| `stage_05.py` | Retries, and the effect that must not happen twice |
| `stage_06.py` | Memory: the window is measured in turns |
| `stage_07.py` | The sandbox: a root the tools cannot leave |
| `stage_08.py` | The gate, and the content that is not a command |
| `stage_09.py` | Budgets, and why the run stopped |
| `stage_10.py` | The trace, and the audit that reads the world |

Stages 3, 4, 6 and 9 build on the earlier ones (`stage_03` validates through
`stage_02`, `stage_04` and `stage_06` drive `stage_01`'s loop), so copying one
over its template needs the earlier ones in place too.

To compare a stage, copy it over the template and re-run the checker, then
restore the template if you want to try again:

```bash
cp solutions/stage_10.py stage_10.py
python3 codecraft/cli.py run agents-from-scratch
```

All ten pass their checks with the standard library alone. Three are worth
reading even if you solved them: `stage_01.run_agent` is the eleven lines
everything else is built around, `stage_05.Effect.once` is the three lines that
stop a retry from charging twice, and `stage_10.audit` is the only function
here whose output a person is expected to act on.
