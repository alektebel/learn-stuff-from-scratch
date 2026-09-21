# learn-stuff-from-scratch

A collection of from-scratch implementations of various systems and projects for learning purposes.

**New here? Read [PHILOSOPHY.md](PHILOSOPHY.md)** — what this repo is for, and the three
principles every directory follows: design choices named as problem-solving decisions,
MVP-then-complicate driven by limit cases, and verification you can run.

**Want the file-by-file list? Read [IMPLEMENTATION_ORDER.md](IMPLEMENTATION_ORDER.md)** —
every file you will open, in the order you will open it, with its stub count.

**Want the papers? Read [REFERENCES.md](REFERENCES.md)** — one canonical source
per mechanism, by week, with what to read each for.

**Starting? Read [LIVE.md](LIVE.md) first** — a system you deploy in week 1 and keep
running, in parallel. Ninety days of uptime takes ninety days; it is the only thing
here that effort cannot compress.

**Working through it? Read [ROADMAP.md](ROADMAP.md)** — an 18-week schedule (24 Aug –
27 Dec 2026) at three intensities. The daily notebook — expected work, expected
publishable, one blog post per day — lives in [`journal/`](journal/):

```bash
python3 journal/serve.py        # http://127.0.0.1:8765  (starts today, 23 Aug 2026)
```

Track where you actually are with:

```bash
python3 progress.py                 # per-directory bars, and how far behind the plan you are
python3 progress.py --checks        # also runs every check.py — the number that cannot be gamed
python3 progress.py --track spine   # the 10-directory minimum, 28 h/week
```

## The repo, in weeks

Each week folder has a `README.md` for **the current priority order** (AWS first,
then LLM work, then provenance, then distributed training, then the database,
then the rest). The code still lives where it was added; the README links to it.
**Start at [`week-01/`](week-01/)** — that is AWS, not a shell.

`lean-proofs/` stays at the root because it is not a week: it is a ~1.2 h daily
slot across all eighteen.

| Week | Dates | Objective | Projects |
|---|---|---|---|
| [**1**](week-01/) | Aug 24–Aug 30 | AWS, from its mechanisms up | `aws-from-scratch` |
| [**2**](week-02/) | Aug 31–Sep 6 | LLMs | `autograd`, `llm-from-scratch` |
| [**3**](week-03/) | Sep 7–Sep 13 | Teaching a model: distil, then reward | `rl-posttraining`, `context-caching` |
| [**4**](week-04/) | Sep 14–Sep 20 | Serving it yourself | `inference-from-scratch`, `deploy-and-debug` |
| [**5**](week-05/) | Sep 21–Sep 27 | Attribution, on a real task | `contextcite`, `spade`, `mars-sql` |
| [**6**](week-06/) | Sep 28–Oct 4 | Provenance, algebraically | `provenance-semirings` |
| [**7**](week-07/) | Oct 5–Oct 11 | Goal-directed reasoning | `scasp` |
| [**8**](week-08/) | Oct 12–Oct 18 | Parser in front, prover behind | `linc`, `distributed-training` |
| [**9**](week-09/) | Oct 19–Oct 25 | A database from the disk up | `database-engine` |
| [**10**](week-10/) | Oct 26–Nov 1 | Consensus, and its refusal | `dynamo-paper`, `raft` |
| [**11**](week-11/) | Nov 2–Nov 8 | Byzantine, and open membership | `blockchain-from-scratch` |
| [**12**](week-12/) | Nov 9–Nov 15 | AWS certification block | `aws-certification`, `aws-deploy` |
| [**13**](week-13/) | Nov 16–Nov 22 | Sockets | `bash-from-scratch`, `http-server` |
| [**14**](week-14/) | Nov 23–Nov 29 | What a byte stream carries | `dns-server`, `cryptographic-library`, `communication-protocols`, `toralizer` |
| [**15**](week-15/) | Nov 30–Dec 6 | Compilers, and a machine for them | `firewall-from-scratch`, `c-compiler`, `compiler-and-vgpu`, `quantum-computing-lang` |
| [**16**](week-16/) | Dec 7–Dec 13 | CUDA | `cuda-from-scratch` |
| [**17**](week-17/) | Dec 14–Dec 20 | Databases deeper, light, and Haskell | `database-internals`, `ray-tracer`, `haskell-projects` |
| [**18**](week-18/) | Dec 21–Dec 27 | The long tail | `spectral-graphs`, `sas-lineage-tool`, `web-scraping`, `ml-in-production`, `mlops` |

---

## Directory Structure

The same directories, grouped by subject rather than by week.

### Low-Level Systems (C/C++)
- **[c-compiler/](week-15/c-compiler/)** - C compiler implementation in C
- **[quantum-computing-lang/](week-15/quantum-computing-lang/)** - Quantum computing language and simulator (like Qiskit) in C
- **[cryptographic-library/](week-14/cryptographic-library/)** - Cryptographic primitives (SHA-256, ECDSA, etc.) in C
- **[bash-from-scratch/](week-13/bash-from-scratch/)** - Unix shell/terminal implementation
- **[http-server/](week-13/http-server/)** - HTTP server implementation
- **[dns-server/](week-14/dns-server/)** - DNS server implementation with UDP networking and protocol parsing
- **[firewall-from-scratch/](week-15/firewall-from-scratch/)** - Packet filtering firewall with raw sockets, protocol parsing, and rule-based filtering
- **[communication-protocols/](week-14/communication-protocols/)** - Serial & parallel communication protocol implementations: UART/USART, SPI, I2C, CAN bus, RS-232/RS-485 (with Linux spidev/i2c-dev/SocketCAN hardware support)

### Databases & Consensus
- **[database-engine/](week-09/database-engine/)** - A relational database from the disk up: slotted pages and a buffer pool with LRU, a B+tree index, write-ahead logging with ARIES-style redo-then-undo recovery, MVCC snapshot isolation (and the write skew it lets through), a recursive-descent SQL parser with precedence climbing, a cost-based planner, and a Volcano iterator executor (18 graded checks via `python3 check.py`)
- **[raft/](week-10/raft/)** - Consensus one mechanism at a time, tested against a network that partitions, crashes and drops messages: the log matching property, terms and the election restriction, nextIndex/matchIndex repair, and the Figure 8 commit rule that makes "a majority has it" wrong - the deliberate opposite of `dynamo-paper` (7 graded checks via `python3 check.py`)

### GPU Programming & Parallel Computing
- **[cuda-from-scratch/](week-16/cuda-from-scratch/)** - CUDA parallel programming from basics to neural networks on GPU
- **[ray-tracer/](week-17/ray-tracer/)** - A path tracer in pure Python: reflection, refraction and Fresnel, the ray-sphere quadratic and AABB slabs, a BVH with both median and surface-area-heuristic splits, matte/metal/glass materials, and a Monte Carlo integrator with a lens camera - where the 1/sqrt(N) noise bill comes from, and why `t_min = 0.001` is a guess about scene scale (6 graded checks via `python3 check.py`)
- **[compiler-and-vgpu/](week-15/compiler-and-vgpu/)** - A compiler and a virtual GPU sharing one instruction set: 32-bit ISA, two-pass assembler, scalar CPU, recursive-descent front end, code generation with linear-scan register allocation and spilling, and a SIMT warp with divergence, mask stacks and barrier deadlock detection (12 graded checks via `python3 check.py`)

### Functional Programming & Formal Verification
- **[haskell-projects/](week-17/haskell-projects/)** - Various projects to learn Haskell
- **[lean-proofs/](lean-proofs/)** - Mathematical proofs in Lean, progressing toward Galois theorem

### Machine Learning & MLOps
- **[distributed-training/](week-08/distributed-training/)** - Distributed training systems (data parallelism, model parallelism, multi-node training)
- **[ml-in-production/](week-18/ml-in-production/)** - Production ML systems (model serving, monitoring, A/B testing)
- **[mlops/](week-18/mlops/)** - MLOps pipelines (experiment tracking, CI/CD, feature stores)
- **[ml-inference/](reference/ml-inference/)** - High-performance inference (optimization, quantization, edge deployment)

### Generative AI & Deep Learning
- **[autograd/](week-02/autograd/)** - A reverse-mode automatic differentiation engine over arrays, then a neural network library on top of it: topological sort and gradient accumulation, broadcast folding, fused softmax cross-entropy, He/Xavier initialisation, SGD/momentum/RMSProp/Adam/AdamW, dropout, gradient clipping, and a VAE with the reparameterisation trick - pure Python, no numpy (10 graded checks via `python3 check.py`)
- **[llm-from-scratch/](week-02/llm-from-scratch/)** - A transformer language model built on that engine: BPE tokenisation in merge-rank order, scaled dot-product attention with a causal mask, multi-head attention, pre-norm blocks with the residual gradient highway, weight tying, training with gradient accumulation, greedy/temperature/top-k/top-p sampling, then on-policy distillation (forward vs reverse KL vs JSD, OPD vs RL vs SFT, OPSD, Privilege Illusion) (15 graded checks via `python3 check.py`)
- **[diffusion-models/](reference/diffusion-models/)** - Diffusion models from scratch (DDPM, DDIM, U-Net, image generation like Stable Diffusion)

### ML Infrastructure & Serving
- **[tensorrt-inference/](reference/tensorrt-inference/)** - TensorRT-style inference engine - graph optimization, quantization, kernel auto-tuning
- **[vllm-engine/](reference/vllm-engine/)** - vLLM serving engine - PagedAttention, continuous batching, high-throughput LLM serving
- **[context-caching/](week-03/context-caching/)** - LLM context caching from scratch on a tiny pure-Python transformer: KV cache, block-hash and radix-tree prefix caching, paged KV blocks with copy-on-write, semantic response caching, and cache-aware request routing (16 graded checks via `python3 check.py`)
- **[provenance-semirings/](week-06/provenance-semirings/)** - Green et al. (PODS 2007): evaluate a query once in ℕ[X], then lineage, why-provenance, bag, trust, security and min-cost are homomorphisms. If `h(Q_How)=Q_K` fails, you built an annotation scheme (8 graded checks)
- **[scasp/](week-07/scasp/)** - Goal-directed ASP: unification with occurs, SLD, Clark duals for constructive negation, coinductive success through even loops, justification trees. The result is a tree you can replay (8 graded checks)
- **[linc/](week-08/linc/)** - LINC / Logic-LM / Faithful CoT without an LLM: a pluggable parser, a prover that emits a proof, a fault injector from LINC's error analysis, a sweep of the parse-error rate, and a how-polynomial on the proof (8 graded checks)
- **[contextcite/](week-05/contextcite/)** - ContextCite (NeurIPS 2024) replicated from scratch: context attribution by ablating sources and fitting a sparse LASSO surrogate - source partitioning, logit-probability scoring, coordinate-descent LASSO, held-out LDS evaluation, and the paper's three applications (14 graded checks via `python3 check.py`)
- **[spade/](week-05/spade/)** - SPADE (PVLDB 2024): synthesise data-quality assertions from prompt-version deltas, select a minimal cover under an FFR cap, then cite each kept assertion back to its delta with ContextCite (8 graded checks)
- **[mars-sql/](week-05/mars-sql/)** - MARS-SQL (2025): grounding, ReAct generation, generative validation on a tiny company database, then cite the SQL to the schema columns that justified it (8 graded checks)
- **[inference-from-scratch/](week-04/inference-from-scratch/)** - A serving stack on a simulated GPU, in the order you actually assemble one: the per-token path, a naive server that fails under overlap, continuous batching, KV bandwidth, a scheduler, paged KV, GPU-path opts, speculative decoding, observability, a load test, then — only then — a comparison with vLLM / SGLang / TensorRT-LLM (12 graded checks)

### System Design & Distributed Systems
- **[system-design/](reference/system-design/)** - Core distributed systems patterns: caching (LRU, cache-aside, stampede), async queues (retries, backoff, DLQ, idempotency), reliability (circuit breaker, bulkhead, backpressure), consistent hashing, leaderboards, URL shortener, rate limiter, and capacity math
- **[dynamo-paper/](week-10/dynamo-paper/)** - Amazon's Dynamo paper (SOSP 2007) implemented directly: consistent hashing with preference lists, vector clocks, N/R/W quorums, sloppy quorum with hinted handoff, Merkle-tree anti-entropy, and gossip membership (17 graded checks via `python3 check.py`)
- **[aws-from-scratch/](week-01/aws-from-scratch/)** - Learn AWS by implementing toy versions of its core services: IAM policy evaluation, S3 with versioning and delete markers, SQS visibility timeouts, DynamoDB hot partitions, Lambda concurrency and cold starts, SNS filter policies and EventBridge patterns, KMS envelope encryption, VPC stateful-vs-stateless networking, plus a capstone pipeline wiring them together - then a meter and a price sheet on top of all of it: the two rounding rules AWS bills by, graduated tiers, fixed vs variable lines, and the crossover behind every cost rule of thumb (provisioned DynamoDB pays above 14.44% utilisation; a CPU-bound Lambda costs the same at 128 MB and 10 GB; an S3 gateway endpoint has no crossover at all) - and a map of which remaining AWS services are variations of which mechanism (24 graded checks via `python3 check.py`)

### Operations & Reliability
- **[deploy-and-debug/](week-04/deploy-and-debug/)** - Running the systems in this repo and debugging them when they break: capacity math (KV cache sizing, N/R/W failure tolerance), percentiles/queueing/error budgets, root-cause diagnosis of 11 injected faults from metrics alone, and safe rollout (liveness vs readiness, canary analysis, budget-based auto-rollback) - plus a runbook of the real vllm/nodetool/nvidia-smi/k8s commands (12 graded checks via `python3 check.py`)

### Data Engineering & Analytics
- **[sas-lineage-tool/](week-18/sas-lineage-tool/)** - SAS field lineage parser for tracking data transformations and dependencies
- **[web-scraping/](week-18/web-scraping/)** - Industrial web scraping/crawler library (Python/C, CUDA acceleration, CAPTCHA bypass, distributed architecture)

## Philosophy

This repository is dedicated to learning by building things from scratch. Each directory contains:
- **Template files** with TODO comments and implementation guidelines
- **Step-by-step instructions** for gradual implementation
- **Complete solutions** in the `solutions/` folder for reference
- A clear learning path from basics to advanced topics

## Structure

Each project directory contains:

```
project-name/
├── README.md              # Project overview and learning path
├── template-files         # Empty templates with TODOs and guidelines
├── Makefile              # Build configuration (for C projects)
└── solutions/            # Complete working implementations
    ├── README.md         # Solution documentation
    └── solution-files    # Fully implemented code
```

## Getting Started

1. **Choose a project** that interests you
2. **Read the README** in that directory to understand the goals
3. **Start with the template files** - they have TODOs and guidelines
4. **Implement gradually** - follow the TODO comments step by step
5. **Test frequently** - build and test as you implement each section
6. **Check solutions** when stuck or to verify your approach
7. **Learn and iterate** - understand each step before moving forward

## Implementation Approach

The templates are designed to be:
- ✅ **Gradual**: Start simple, add complexity incrementally
- ✅ **Guided**: Clear TODO comments explain what to implement
- ✅ **Balanced**: Not too easy (no hand-holding), not too hard (reasonable steps)
- ✅ **Educational**: Focus on understanding concepts, not just copying code

## Building Projects

Most C projects include a Makefile:

```bash
cd project-name/
make          # Build the project
make run      # Run the program
make test     # Run tests (if available)
make clean    # Clean build artifacts
```

## Video Courses & Learning Resources

To complement the hands-on projects in this repository, we've curated relevant video courses from universities and online platforms. These courses provide theoretical foundations and different perspectives on the topics covered here.

**Note**: This curated list is based on the excellent [cs-video-courses](https://github.com/Developer-Y/cs-video-courses) repository by Developer-Y, which maintains a comprehensive collection of Computer Science courses with video lectures.

### General Computer Science
- [CS 50 - Introduction to Computer Science, Harvard University](https://online-learning.harvard.edu/course/cs50-introduction-computer-science)
- [6.0001 - Introduction to Computer Science and Programming in Python - MIT OCW](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/video_galleries/lecture-videos/)

### Systems Programming & Operating Systems
*Relevant for: bash-from-scratch, http-server, dns-server, c-compiler, database-engine*
- [15-213 Introduction to Computer Systems - CMU](https://scs.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx#folderID=%22b96d90ae-9871-4fae-91e2-b1627b43e25e%22&maxResults=150)
- [CS 162 Operating Systems - UC Berkeley](https://archive.org/details/ucberkeley-webcast-PL-XXv-cvA_iBDyz-ba4yDskqMDY6A1w_c?sort=titleSorter)
- [6.824 - Distributed Systems - MIT](https://pdos.csail.mit.edu/6.824/schedule.html)

### Compiler Design & Programming Languages
*Relevant for: c-compiler, quantum-computing-lang*
- [CS143 - Compilers - Stanford](https://web.stanford.edu/class/cs143/)
- [Theoretical CS and Programming Languages courses](https://github.com/Developer-Y/cs-video-courses#theoretical-cs-and-programming-languages)

### Cryptography & Security
*Relevant for: cryptographic-library*
- [Security Courses - Various Universities](https://github.com/Developer-Y/cs-video-courses#security)

### Parallel Computing & GPU Programming
*Relevant for: cuda-from-scratch*
- [Parallel Computing and GPU Programming courses](https://github.com/Developer-Y/cs-video-courses#computer-organization-and-architecture)

### Machine Learning & Deep Learning
*Relevant for: autograd, llm-from-scratch, distributed-training, ml-in-production, mlops, ml-inference, diffusion-models, world-models*
- [CS229 - Machine Learning - Stanford](http://cs229.stanford.edu/)
- [6.S191 - Introduction to Deep Learning - MIT](http://introtodeeplearning.com/)
- [Deep Learning Specialization - Various Universities](https://github.com/Developer-Y/cs-video-courses#deep-learning)
- [Computer Vision Courses](https://github.com/Developer-Y/cs-video-courses#computer-vision)
- [Generative AI and LLMs](https://github.com/Developer-Y/cs-video-courses#generative-ai-and-llms)

### MLOps & Production ML
*Relevant for: tensorrt-inference, vllm-engine, context-caching*
- [Full Stack Deep Learning](https://fullstackdeeplearning.com/)
- [Machine Learning Systems Design](https://github.com/Developer-Y/cs-video-courses#machine-learning)

### Functional Programming
*Relevant for: haskell-projects*
- [FP 101x - Introduction to Functional Programming - TU Delft](https://ocw.tudelft.nl/courses/introduction-to-functional-programming/)
- [Functional Programming courses](https://github.com/Developer-Y/cs-video-courses#theoretical-cs-and-programming-languages)

### Formal Verification
*Relevant for: lean-proofs*
- [Formal Methods and Verification courses](https://github.com/Developer-Y/cs-video-courses#theoretical-cs-and-programming-languages)

### Quantum Computing
*Relevant for: quantum-computing-lang*
- [Quantum Computing Courses](https://github.com/Developer-Y/cs-video-courses#quantum-computing)

### Databases
*Relevant for: database-engine, dynamo-paper, raft*
- [CMU 15-445 Database Systems](https://15445.courses.cs.cmu.edu/fall2022/)
- [CMU 15-721 Advanced Database Systems](https://15721.courses.cs.cmu.edu/spring2023/)

### Computer Graphics
*Relevant for: ray-tracer*
- [Ray Tracing in One Weekend](https://raytracing.github.io/)
- [Computer Graphics courses](https://github.com/Developer-Y/cs-video-courses#computer-graphics)

### System Design & Distributed Systems
*Relevant for: system-design*
- [CS 75 - Building Dynamic Websites - Harvard](https://cs75.tv/2012/summer/)
- [6.824 - Distributed Systems - MIT](https://pdos.csail.mit.edu/6.824/schedule.html)
- [CMU 15-445 Database Systems](https://15445.courses.cs.cmu.edu/fall2022/)
- [Database Systems Courses](https://github.com/Developer-Y/cs-video-courses#database-systems)
- [Distributed Systems Courses](https://github.com/Developer-Y/cs-video-courses#distributed-systems)

### Data Engineering
*Relevant for: sas-lineage-tool, web-scraping*
- [Database Systems Courses](https://github.com/Developer-Y/cs-video-courses#database-systems)

### Computer Networks
*Relevant for: http-server, dns-server, communication-protocols*
- [Computer Networks Courses](https://github.com/Developer-Y/cs-video-courses#computer-networks)

**For a complete list of courses across all CS topics**, visit the [Developer-Y/cs-video-courses](https://github.com/Developer-Y/cs-video-courses) repository.

## Note

These implementations are for educational purposes. They prioritize clarity and understanding over production-ready features or performance. Use the solutions as reference, but try to implement yourself first for maximum learning!