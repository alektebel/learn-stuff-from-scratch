# reference/ — read these, do not build them

Five directories that are **not on the schedule**. They are here to be read and
compared against what you built, not implemented.

| Directory | Was budgeted | Why it is here instead |
|---|---|---|
| [`ml-inference/`](ml-inference/) | 137 h | 137 hours resting on **6 stubs and no checker**. [`week-04/inference-from-scratch/`](../week-04/inference-from-scratch/) covers the same ground in 60 h with 12 files, 41 stubs and 12 graded checks. |
| [`vllm-engine/`](vllm-engine/) | 156 h | A design brief with **no templates and no checker**. The largest single allocation in the old plan, and nothing in it could be graded. |
| [`tensorrt-inference/`](tensorrt-inference/) | 109 h | Same — a design brief, and vendor-specific. |
| [`world-models/`](world-models/) | 106 h | A genuine cut. Five papers deep, no checker, and one of the two remaining things needing a GPU you would have to pay for. |
| [`diffusion-models/`](diffusion-models/) | 91 h | The same cut, for the same reasons. |
| [`system-design/`](system-design/) | 48 h | Displaced by `week-17/database-internals/`. Its own README's patterns are mostly covered from the mechanisms up by `aws-from-scratch` (caching, queues, rate limiting, consistent hashing) and by `deploy-and-debug` (circuit breakers, backpressure). Kleppmann's *Designing Data-Intensive Applications* covers the rest better than 159 stubs will. |

**647 hours.** Removing them is what takes the plan from 100 h/week to 73.

## The argument for the first three

It is not mine — it is step 11 of the inference curriculum this repo now
follows:

> *Only then go read vLLM, SGLang, TensorRT-LLM and other serving engines.
> Compare their design decisions with yours.*

**Read** and **compare**, after you have built your own. That is a weekend with
the source open, not 402 hours of building. And you will get far more out of it
having done `week-04/inference-from-scratch/` first — the whole point of the
comparison is that you have something to compare *against*.

So when week 4 is green, come back here. Open `vllm-engine/README.md` beside
your own scheduler and paged allocator and read for what they did differently
and why. Write that up. It is one of the more valuable things in the plan and
it costs almost nothing.

## The argument for the last two

Less comfortable: they are simply the lowest-value hours left once the plan had
to fit in eighteen weeks, and they are GPU-bound. If you want either back, the
honest trade is naming what comes out — `haskell-projects` (61 h) and
`system-design` (48 h) are the next candidates, the latter because
`aws-from-scratch` covers much of the same ground from the mechanisms up.

## If you change your mind

Nothing is deleted. Move a directory back into a `week-NN/` folder, add its row
to `PLAN` in [`../progress.py`](../progress.py), and re-run
`python3 progress.py --rebaseline`.

---

[Roadmap](../ROADMAP.md) · [What remains](../REMAINING.md) · [TODO](../TODO.md)
