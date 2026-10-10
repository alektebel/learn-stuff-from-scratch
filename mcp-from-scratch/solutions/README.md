# Solutions

Finished, runnable versions of each stage. Read them *after* attempting — a
solution read cold is just more prose, and these are short enough to fool you
into thinking the stage was easy.

| File | Stage |
|---|---|
| `stage_01.py` | The envelope, and the four ways to answer it |
| `stage_02.py` | The transports: one line, one event, one POST |
| `stage_03.py` | The handshake, and the session it creates |
| `stage_04.py` | The tools the model can see |
| `stage_05.py` | Resources and prompts, and the not-found splits |
| `stage_06.py` | Out of band: subscriptions, progress, cancellation |
| `stage_07.py` | Read-only first, and the report in the middle |
| `stage_08.py` | Idempotency, because the caller will retry |
| `stage_09.py` | The confirmation shows the diff |
| `stage_10.py` | The trajectory, and the audit line |

Stages 5, 7, 8 and 9 register into stage 4's table (`server.add_tool`, and a tool's
`fn` is called with `(arguments, session)`), stage 6 is consulted by stage 3's
dispatcher (`Cancellations.answer_for`), and stage 10 wraps stage 3's
`dispatch` — so copying one over its template needs the neighbours in place too.
`erp.py` is not a stage: it is the domain, provided complete.

To compare a stage, copy it over the template and re-run the checker, then
restore the template if you want to try again:

```bash
cp solutions/stage_10.py stage_10.py
python3 codecraft/cli.py run mcp-from-scratch
```

All ten pass their checks with the standard library alone. Four are worth reading
even if you solved them: `stage_01.Dispatcher.dispatch` is the twenty lines every
later stage adds one clause to, `stage_04.ToolRegistry.call_tool` is where the
protocol/execution split actually happens, `stage_06.Cancellations.answer_for` is
the two lines that implement "send no response for the cancelled request", and
`stage_09.Confirmation.require` is the only function here whose correctness a
person's attention depends on.
