# Learning journal

A local site that starts **today, 23 August 2026**, and runs through 27 December.
The daily plan follows the current priority: AWS, then LLM work, then
provenance-reasoning (ℕ[X], s(CASP), LINC, then citation), then distributed
training, then the database, then the rest.

Each day has two things:

1. **What to implement** — the next unfinished stub, named
2. **What to publish** — the blog title you write before you close the laptop

The publishable is the same ten-minute log [`ROADMAP.md`](../ROADMAP.md) asked
for, except it has a URL and a calendar.

```bash
python3 journal/serve.py          # http://127.0.0.1:8765
```

Posts are markdown in `journal/posts/YYYY-MM-DD.md`. Today's file is already
there. `Ctrl-S` / `Cmd-S` saves. The green underline on a calendar day means
a post exists on disk.

The sidebar runs `python3 progress.py --track core` so the bars and the
journal stay in the same place.

Sunday is still regression day. The expected publish that day is always a
look-back, not a new feature.
