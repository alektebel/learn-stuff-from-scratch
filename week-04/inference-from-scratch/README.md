# Inference From Scratch

Build a serving stack on a *simulated* GPU, in the order a production engine
is actually assembled — and only then open vLLM, SGLang and TensorRT-LLM.

Do **not** start in [`../../reference/vllm-engine/`](../../reference/vllm-engine/).
That directory is step 11. Opening it earlier converts this into a
transcription.

`toy_gpu.py` is provided. It is not CUDA. It is a ledger: every kernel you
"launch" records bytes moved, FLOPs, and whether you synchronised. The
numbers are fake; the *ratios* are the ones real hardware shows you.

```bash
cd week-04/inference-from-scratch
python3 check.py          # 12 graded checks against YOUR code
```

Checks only. Templates raise `NotImplementedError`. No `solutions/` yet.

## The twelve steps

| # | File | What has to be true when it is done |
|---|---|---|
| 1 | `inference_path.py` | You can name every GPU event for one prefill token and one decode token |
| 2 | `naive_server.py` | One request at a time works; two concurrent requests fall apart in a named way |
| 3 | `batching.py` | Continuous batching, and you can measure TTFT, TPOT, throughput |
| 4 | `kv_runtime.py` | Decode bytes/FLOP crosses the ridge point. Decode is memory-bandwidth bound |
| 5 | `scheduler.py` | Queues, priorities, backpressure, cancellation, timeouts |
| 6 | `paged_kv.py` | Block allocation, fragmentation, prefix sharing, copy-on-write fork |
| 7 | `gpu_opt.py` | CUDA-graph-shaped replay, fusion, quant, attention kernel, host sync |
| 8 | `speculate.py` | Speculative decoding helps only when the draft is cheap *and* accurate |
| 9 | `observe.py` | TTFT, ITL, throughput, GPU util, KV used, queue time — all from one request |
| 10 | `traffic.py` | A concurrency where throughput stops scaling, and a *reason* |
| 11 | `compare.py` | vLLM / SGLang / TensorRT-LLM / yours — named decisions, not vibes |
| 12 | `deeper.py` | Multi-GPU, prefill/decode disaggregation, KV offload, routing |

Related: [`../../week-03/context-caching/`](../../week-03/context-caching/) is
the cache data structures. This directory is the *server* those structures
sit inside.

## The method

Make it work. Watch it fall apart. Only then add the machinery that handles
the case that broke it. That is [`PHILOSOPHY.md`](../../PHILOSOPHY.md) and it
is why step 2 exists: a naive server that you never watched fail teaches
you nothing about why vLLM is complicated.

## Sources

Full list in [`../../REFERENCES.md`](../../REFERENCES.md#week-4--inference-from-scratch).
Read in this order, and read them **after** the step they belong to:

- Yu et al., **"Orca"**, OSDI 2022 — continuous batching, and it predates vLLM.
  For step 3.
- Kwon et al., **"PagedAttention"**, SOSP 2023 — block allocation and
  fragmentation. For step 6.
- Pope et al., **"Efficiently Scaling Transformer Inference"**, 2022 — the
  arithmetic behind why decode is memory-bandwidth bound. For step 4.
- Leviathan et al., ICML 2023 **and** Chen et al., 2023 — two speculative
  decoding papers that differ. Read both, for step 8.
- Dao et al., **"FlashAttention"**, NeurIPS 2022 — for step 7.

Step 11 of this curriculum is *go read vLLM, SGLang and TensorRT-LLM and compare
their design decisions with yours* — that is [`../../reference/`](../../reference/),
and it only works once your own version runs.
