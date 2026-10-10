# solutions/ — Self-RAG reference

`self_rag.py` is the complete module: the injected reflection interface, the deterministic
`OverlapReflectionModel`, the five loop functions, the shared-eval-set loader and `demo`.
Copy it over the template to see the checker go 5/5.

```bash
cd rag-from-scratch/self-rag
cp solutions/self_rag.py self_rag.py
python3 check.py --all        # 5/5 passing
python3 self_rag.py           # the demo below
```

## Expected demo output

```
Self-RAG (offline, overlap reflection model), seed 0
  answer accuracy (answerable): 0.833
  abstention precision/recall:  0.833 / 1.000
  paths: {'answered': 19, 'abstain': 5} (n=24)
    lexical   correct 0.833
    semantic  correct 0.800
    filtered  correct 1.000
    multi_hop correct 0.667
    no_answer correct 0.833
  sample LEX-01: path=answered evidence=['DOC-0000'] answer='...'
```

The numbers are the loop's, under the offline overlap reflection model; the checker does not
assert them. The mutation table in `../README.md` is replayed by
`.claude/skills/graded-module/scripts/mutate.py` (every row CAUGHT).
