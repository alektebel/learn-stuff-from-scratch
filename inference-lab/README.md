# inference-lab

Fifteen inference-infrastructure projects (serve, optimise, scale), mapped onto what this repo
already has. **Not started.** This file is the plan; a project gets code only when chosen.

## The hardware constraint decides the order

The development environment has **no GPU** (4 CPUs, 15 GB RAM) and cannot download model
weights (huggingface.co is blocked by its network policy). So every project falls in one of
three groups:

- **CPU-real:** the thing built is the real thing, and the numbers mean something on CPU
  (calculators, routers, gateways, schedulers, autoscalers, dashboards, chaos tooling).
- **Simulated:** the mechanism is real, the GPU is a model of one (a simulated server with a
  latency model calibrated from published numbers). Teaches the mechanism; the numbers are
  the simulator's, not hardware's.
- **GPU-required:** meaningless without a GPU and real weights. Needs a GPU machine you
  provide; the code can be written here, the measurements cannot be taken here.

| # | Project | Group | Already in the repo | What is new |
|---|---|---|---|---|
| 1 | Self-hosted inference server (vLLM/SGLang, continuous batching) | GPU-required | `vllm-engine/`, `sgl-lang/` are implementation guides, not deployments | an actual deployment + API |
| 2 | TTFT/ITL benchmark suite under rising concurrency | CPU-real (harness) / GPU-required (numbers) | percentiles in `deploy-and-debug/metrics.py` | open-loop load generator, streaming timers, load curves |
| 3 | KV cache memory calculator and monitor | CPU-real | **calculator exists**: `deploy-and-debug/capacity.py` (`kv_bytes_per_token`, `kv_cache_capacity`, `max_concurrent_sequences`) | live utilisation monitor (needs #1) |
| 4 | Prefix-caching proxy | CPU-real | **routing exists**: `context-caching/cache_router.py` (cache-aware policies vs round robin), `radix_cache.py` | a real HTTP proxy in front of replicas |
| 5 | Quantization comparison lab (FP16/FP8/INT8/AWQ) | GPU-required | `ml-inference/phase2_optimization`, `tensorrt-inference/` (guides) | measured quality × latency × VRAM table |
| 6 | Speculative decoding with acceptance-rate tracking | Simulated or GPU | nothing | draft/verify loop; acceptance math runs on the tiny CPU transformer in `context-caching/tiny_transformer.py` |
| 7 | Triton fused kernel (softmax/RMSNorm) vs PyTorch | GPU-required (perf); `TRITON_INTERPRET=1` checks correctness on CPU | `cuda-from-scratch/` (CUDA C, not Triton) | Triton kernel + benchmark |
| 8 | Chunked prefill scheduler experiment | Simulated | nothing | scheduler + mixed prefill/decode workload |
| 9 | PagedAttention under memory pressure | Simulated | `context-caching/paged_kv_cache.py` (paged blocks, copy-on-write) | eviction, preemption, fragmentation report |
| 10 | Disaggregated prefill/decode | Simulated | nothing | two pools, KV transfer cost model |
| 11 | Queue-based GPU autoscaler | CPU-real (logic) / Simulated (GPUs) | cold starts and concurrency in `aws-from-scratch/` (Lambda) | queue-depth scaling with cold-start mitigation |
| 12 | Cost-per-token dashboard (per tenant, $/M tokens, MFU) | CPU-real | run records already carry tokens and cost (`harness-lab/eval/contract.py`) | accounting + dashboard; shares #10 of agent-evals |
| 13 | AI gateway: fallbacks, rate limits, TTFT SLOs | CPU-real | rate limiter, circuit breaker in `system-design/` | multi-provider router with degradation chains |
| 14 | Chaos suite for inference | CPU-real + Simulated | fault injection and SLO burn in `deploy-and-debug/` (11 injected faults) | replica kills, throttling, spikes against #13 |
| 15 | Public benchmark teardown | needs #1, #2 on a GPU | — | writing |

### Corrections to the briefs
- **#4 "up to 80% TTFT cuts":** true only when shared prefixes are long relative to the request
  and the replica still holds them. The number depends on the workload's prefix distribution;
  measure it on your traffic shape, do not quote it.
- **#10 "behind every frontier serving stack":** disaggregation pays off when prefill and decode
  interfere enough to justify moving the KV cache between pools; at small scale the transfer
  cost can erase the gain. The experiment should be able to show a loss.
- **#7:** a kernel benchmark without a GPU is not a benchmark. Correctness can be developed in
  Triton's interpreter here; timing needs hardware.
