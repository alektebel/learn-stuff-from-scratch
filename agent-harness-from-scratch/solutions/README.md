# Solutions

Finished, runnable versions of each stage. Read them *after* attempting — a
solution read cold is just more prose, and these are short enough to fool you
into thinking the stage was easy.

| File | Stage |
|---|---|
| `stage_01.py` | The model is a callable returning an event stream |
| `stage_02.py` | The context window is a budget, not a list |
| `stage_03.py` | The loop, and what a budget exhaustion returns |
| `stage_04.py` | Dispatch: an unknown tool is a message, a failing tool is an observation |
| `stage_05.py` | Streaming, and the timings of a turn |
| `stage_06.py` | Retries: the model call, never the tool call |
| `stage_07.py` | Compaction: summarize the middle |
| `stage_08.py` | The trace, the artifact you can replay |
| `stage_09.py` | Process reward: a step has to be grounded in what came back |
| `stage_10.py` | Verification and the self-generated data loop |

Stage 3's `run` calls stage 1's `collect` and `assistant_message`, stage 4's
`dispatch` argument and stage 8's `Trace.step`; stage 5's `stream` wraps the same
model call with a sink and a log; stage 7 imports stage 2's `estimate_tokens`
(and falls back to the same arithmetic if stage 2 is still a stub); stage 10's
round runs an agent whose answer is verified by the same rules stage 9 rewards. So
copying one solution over its template needs the neighbours in place too, and
`tiny_env.py` is not a stage: it is the domain and the scripted model, provided
complete.

To compare a stage, copy it over the template and re-run the checker, then
restore the template if you want to try again:

```bash
cp solutions/stage_10.py stage_10.py
python3 codecraft/cli.py run agent-harness-from-scratch
```

All ten pass their checks with the standard library alone. Four are worth reading
even if you solved them: `stage_01.collect` is the twenty lines every later stage
consumes; `stage_03.run` is the loop, and the three lines that make a budget an
outcome rather than an exception are the whole stage; `stage_06.Retrying` is where
"was anything forwarded?" decides whether a retry is a repair or a doubled prefix;
and `stage_08.Trace.step` is the only function here whose *shape* a security
review would read.
