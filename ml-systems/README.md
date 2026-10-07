# ML Systems (Harvard CS249r) — implemented

The companion directory for **Machine Learning Systems: Principles and Practices of
Engineering Artificially Intelligent Systems** (Vijay Janapa Reddi et al., Harvard
CS249r): <https://github.com/harvard-edge/cs249r_book>, read at commit `8a9df95e`
(2026-10-06), and the site <https://mlsysbook.ai>.

The book is the reading; this directory and the rest of the repo are where it gets built.
Nothing here copies the book's text (CC BY-NC-SA 4.0) or TinyTorch's code (MIT): the
exercises are original, follow this repo's format (templates + `check.py` + `solutions/`),
and cite the chapter they implement.

## What the book repository contains

| Part | What it is | How to use it here |
|---|---|---|
| Vol I *Foundations* (16 ch.) | single-machine ML systems | map below |
| Vol II *Scaling* (17 ch.) | fleets, distributed training, inference at scale | map below |
| Vol III *Agentic* (18 ch., in development) | agent systems engineering | almost chapter for chapter, [harness-lab](../harness-lab/) |
| Vol IV *Physical AI* (17 ch., in development) | robots and embodied systems | not covered yet |
| TinyTorch (20 modules) | build a PyTorch-like framework from scratch | track [framework/](framework/) follows its arc |
| Labs (per chapter) | interactive notebooks | read alongside each chapter |
| MLSys·im | analytical performance modelling | the "count it before you run it" habit; see `framework/costs.py` |
| MLPerf-edu, kits | benchmarking; Arduino/Raspberry Pi TinyML kits | kits need the hardware |

## Volume I — Foundations

| Ch. | Topic | Build it in | Status |
|---|---|---|---|
| 1-3 | Introduction, ML systems, workflow | (reading) | — |
| 4 | Data engineering | [framework/](framework/) `data.py`; [web-scraping/](../web-scraping/), [sas-lineage-tool/](../sas-lineage-tool/) | batching done; pipelines partial |
| 5 | NN computation | [framework/](framework/) `tensor.py`, `costs.py` | **done** |
| 6 | NN architectures | [framework/](framework/) `nn.py` (MLP); CNNs next; attention in [llm-from-scratch/](../llm-from-scratch/) | MLP done |
| 7 | Frameworks | [framework/](framework/) autograd | **done** |
| 8 | Training | [framework/](framework/) `losses.py`, `optim.py`, `train.py` | **done** |
| 9 | Data selection | — | gap |
| 10 | Model compression | [ml-inference/](../ml-inference/), [tensorrt-inference/](../tensorrt-inference/) (guides) | framework part 3 |
| 11 | HW acceleration | [cuda-from-scratch/](../cuda-from-scratch/), [compiler-and-vgpu/](../compiler-and-vgpu/) | covered |
| 12 | Benchmarking | [harness-lab/eval/stats.py](../harness-lab/eval/stats.py) (paired tests, power) | statistics covered |
| 13 | Model serving | [vllm-engine/](../vllm-engine/), [context-caching/](../context-caching/), [inference-lab/](../inference-lab/) | covered / planned |
| 14 | ML operations | [mlops/](../mlops/), [ml-in-production/](../ml-in-production/), [deploy-and-debug/](../deploy-and-debug/) | covered |
| 15 | Responsible engineering | — | gap |

## Volume II — Scaling

| Ch. | Topic | Build it in | Status |
|---|---|---|---|
| 2 | Compute infrastructure | [inference-lab/](../inference-lab/) (needs GPU) | planned |
| 3 | Network fabrics | — | gap |
| 4 | Data storage | [database-from-scratch/](../database-from-scratch/), [aws-from-scratch/](../aws-from-scratch/) (S3) | covered |
| 5-6 | Distributed training, collectives | [distributed-training/](../distributed-training/) | guide; all-reduce from scratch is a candidate |
| 7 | Fault tolerance | [dynamo-paper/](../dynamo-paper/), [system-design/](../system-design/), [deploy-and-debug/](../deploy-and-debug/) | covered |
| 8 | Fleet orchestration | [aws-from-scratch/](../aws-from-scratch/) (Lambda, SQS); autoscaler in [inference-lab/](../inference-lab/) | partial |
| 9 | Performance engineering | [cuda-from-scratch/](../cuda-from-scratch/) | covered |
| 10 | Inference | [vllm-engine/](../vllm-engine/), [inference-lab/](../inference-lab/) | covered / planned |
| 11 | Edge intelligence | [ml-inference/](../ml-inference/) (edge deployment guide) | partial |
| 12 | Ops at scale | [deploy-and-debug/](../deploy-and-debug/) (SLOs, canaries) | covered |
| 13 | Security and privacy | [agent-evals/redteam](../agent-evals/redteam/), [cryptographic-library/](../cryptographic-library/) | partial |
| 14 | Robust AI | [deepfake-detection/](../deepfake-detection/) (adversarial angle) | partial |
| 15-16 | Sustainable, responsible AI | — | gap |

## Volume III — Agentic (maps onto harness-lab)

context engineering, KV cache, long-term memory, tool calling, sandboxes, agent harness,
durable execution, failure recovery, evaluation, trajectory curation, fine-tuning, RLVR,
multi-agent, agent economics: harness-lab phases 0-7, [agent-evals/](../agent-evals/),
[context-caching/](../context-caching/), and the RL post-training course on branch
`claude/rl-posttraining-llm-exercises-wzfe8w`.

## TinyTorch's arc, and where each module lives here

| TinyTorch | Here |
|---|---|
| 01 tensor, 06 autograd | `framework/tensor.py` |
| 02 activations, 03 layers | `framework/nn.py` |
| 04 losses | `framework/losses.py` |
| 05 dataloader | `framework/data.py` |
| 07 optimizers | `framework/optim.py` |
| 08 training + milestones 1958/1969/1986 | `framework/train.py` |
| 14 profiling (part) | `framework/costs.py` |
| 09 convolutions, milestone 1998 CNN | **framework part 2 (next)** |
| 10 tokenization, 11 embeddings, 12 attention, 13 transformers | [llm-from-scratch/](../llm-from-scratch/) has BPE, attention, RoPE, sampling, KV cache; a training transformer on this framework is part 2 |
| 15 quantization, 16 compression, 17 acceleration | **framework part 3** |
| 18 memoization (KV cache) | [llm-from-scratch/](../llm-from-scratch/), [context-caching/](../context-caching/) |
| 19 benchmarking, milestone 2018 MLPerf | [harness-lab/eval/stats.py](../harness-lab/eval/stats.py) + part 3 |

### Should you just do TinyTorch instead?

TinyTorch is a well-built course with its own tests, and it is free. Doing it as-is is
a legitimate choice. What this directory adds is this repo's discipline: named design
decisions, limit-case checks, and a checker that is itself mutation-tested. It also adds
connections to the rest of the repo (costs measured against allocations, the same stats
used for agent evals). What it lacks, compared to TinyTorch, is breadth: 8 of 20 modules today.
