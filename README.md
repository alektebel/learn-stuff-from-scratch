# learn-stuff-from-scratch

A collection of from-scratch implementations of various systems and projects for learning purposes.

**Open work: [TODO.md](TODO.md).** **New here? Read [PHILOSOPHY.md](PHILOSOPHY.md)** — what this repo is for, and the three
principles every directory follows: design choices named as problem-solving decisions,
MVP-then-complicate driven by limit cases, and verification you can run.

**Reading list:** [RESOURCES.md](RESOURCES.md) indexes external links; directories with
relevant reading carry their own `RESOURCES.md`.

## codecraft — the adaptive course runner

**[codecraft/](codecraft/)** turns this repo into your own CodeCrafters. It runs any
course's `check.py`, remembers every attempt, classifies how you got stuck (the same
failure three times vs. three different failures get different advice), and tunes the
nudge, hint depth and pacing to you. It also scaffolds **new** from-scratch courses you
author yourself:

```bash
cz run llm-from-scratch       # run a course, get coached (cz = the CLI shim)
cz path                       # the ordered plan, with progress
cz progress                   # repo completion + checker completion, live
cz web                        # the skill tree and the next action, in a browser
python3 codecraft/cli.py new my-course --title "Build X" --stages 3
```

`cz progress` reads progress from two places — the stub markers still standing in the
templates, and each course's own checker — so neither number can be faked. `cz web`
serves that same state, read-only, at `http://127.0.0.1:8766`; the CLI stays the engine.

`cz` is a one-line forwarder to `python3 codecraft/cli.py`; both work. See
[codecraft/README.md](codecraft/README.md).

## Directory Structure

### Low-Level Systems (C/C++)
- **[c-compiler/](c-compiler/)** - C compiler implementation in C
- **[quantum-computing-lang/](quantum-computing-lang/)** - Quantum computing language and simulator (like Qiskit) in C
- **[cryptographic-library/](cryptographic-library/)** - Cryptographic primitives (SHA-256, ECDSA, etc.) in C
- **[bash-from-scratch/](bash-from-scratch/)** - Unix shell/terminal implementation
- **[http-server/](http-server/)** - HTTP server implementation
- **[dns-server/](dns-server/)** - DNS server implementation with UDP networking and protocol parsing
- **[firewall-from-scratch/](firewall-from-scratch/)** - Packet filtering firewall with raw sockets, protocol parsing, and rule-based filtering
- **[communication-protocols/](communication-protocols/)** - Serial & parallel communication protocol implementations: UART/USART, SPI, I2C, CAN bus, RS-232/RS-485 (with Linux spidev/i2c-dev/SocketCAN hardware support)

### From-scratch systems, distributed & cloud (skill-tree modules)
Python, standard library only, each a graded module (`check.py` + `solutions/` + planted bugs caught by the checker), from the skill-tree tracks:
- **Low level** - [`01-bit-representation`](lowlevel/01-bit-representation/) bits, two's complement, IEEE-754, endianness · [`02-memory-layout`](lowlevel/02-memory-layout/) struct layout, alignment, padding (checked against the C ABI) · [`03-allocator`](lowlevel/03-allocator/) a malloc: free list, split, coalesce · [`04-syscalls-io`](lowlevel/04-syscalls-io/) file descriptors, short reads, buffering · [`05-concurrency`](lowlevel/05-concurrency/) locks, a bounded queue, a lost wake-up and a deadlock on a deterministic scheduler
- **Distributed** - [`01-clocks`](distributed/01-clocks/) Lamport and vector clocks · [`02-replication-quorums`](distributed/02-replication-quorums/) leader/follower log with R+W>N · [`03-consensus`](distributed/03-consensus/) Raft election, replication, commit (capstone) · [`04-crdts`](distributed/04-crdts/) G-counter, LWW register, OR-set · [`05-partitioning`](distributed/05-partitioning/) consistent hashing and rebalancing
- **Cloud / AWS** - [`01-object-store`](cloud/01-object-store/) an S3-shaped store with versioning and ETags · [`02-iam-policy`](cloud/02-iam-policy/) IAM policy evaluation (explicit deny wins) · [`03-queue-fanout`](cloud/03-queue-fanout/) SQS visibility timeouts + SNS fanout · [`04-vpc-routing`](cloud/04-vpc-routing/) route tables, security groups, NACLs · [`05-iac-drift`](cloud/05-iac-drift/) an infra-as-code drift plan (capstone)

### GPU Programming & Parallel Computing
- **[cuda-from-scratch/](cuda-from-scratch/)** - CUDA parallel programming from basics to neural networks on GPU
- **[compiler-and-vgpu/](compiler-and-vgpu/)** - A compiler and a virtual GPU sharing one instruction set: 32-bit ISA, two-pass assembler, scalar CPU, recursive-descent front end, code generation with linear-scan register allocation and spilling, and a SIMT warp with divergence, mask stacks and barrier deadlock detection (12 graded checks via `python3 check.py`)

### Functional Programming & Formal Verification
- **[haskell-projects/](haskell-projects/)** - Various projects to learn Haskell
- **[skill-tree/](skill-tree/)** - Dependency graph of what the repo builds from scratch: 97 nodes across 20 tracks in five domains (mathematics, systems/low-level, distributed, cloud/AWS, ML systems, agents…), each with prerequisites, acceptance criteria and limit cases, validated by `tree.py`; lightly gamified (XP, levels, per-track badges) and drawn as an interactive map in `tree.html`. Modules are built into their track's root following `.claude/skills/skill-tree-worker`
- **[math/](math/)** - Graded modules for the skill-tree nodes. Done: `foundations/01-linear-algebra/` (Gaussian elimination with partial pivoting, rank, null space, inverse and determinant) and `foundations/02-analytic-geometry/` (inner products from an SPD matrix, orthogonal and affine projections, classical vs modified Gram-Schmidt, 2-D/3-D rotations) — 10 graded checks each, mutation-tested by planted bugs
- **[lean-proofs/](lean-proofs/)** - Mathematical proofs in Lean, progressing toward Galois theorem

### Machine Learning & MLOps
- **[distributed-training/](distributed-training/)** - Distributed training systems (data parallelism, model parallelism, multi-node training)
- **[ml-in-production/](ml-in-production/)** - Production ML systems (model serving, monitoring, A/B testing)
- **[mlops/](mlops/)** - MLOps pipelines (experiment tracking, CI/CD, feature stores)
- **[ml-systems/](ml-systems/)** - Harvard CS249r *Machine Learning Systems* implemented: a chapter-by-chapter map of Vols I-III onto this repo, and a framework track (TinyTorch's arc) - tensors with autograd, layers, stable losses, SGD/Adam, data loading, the 1958/1969/1986 milestones and a cost model checked against real allocations (16 graded checks, mutation-tested)
- **[ml-inference/](ml-inference/)** - High-performance inference (optimization, quantization, edge deployment)

### Reinforcement Learning & LLM Post-Training
- **[rl-posttraining-llm/](rl-posttraining-llm/)** - RL post-training of LLMs for applications (GRPO from scratch, phased/process/execution-free rewards, multi-turn schema-discovery agents) using text-to-SQL & agentic data analysis as the running app. Zero-dependency CPU core + optional TRL real-model track.

### Generative AI & Deep Learning
- **[diffusion-models/](diffusion-models/)** - Diffusion models from scratch (DDPM, DDIM, U-Net, image generation like Stable Diffusion)
- **[deepfake-creation/](deepfake-creation/)** - Deepfake generation techniques (face swapping, reenactment, First Order Motion Model, Wav2Lip)
- **[deepfake-detection/](deepfake-detection/)** - Deepfake detection methods (CNN-based, temporal analysis, frequency domain, biological signals)

### ML Infrastructure & Serving
- **[sgl-lang/](sgl-lang/)** - Structured Generation Language (SGL) for LLMs - constrained generation, grammar enforcement, compilation
- **[tensorrt-inference/](tensorrt-inference/)** - TensorRT-style inference engine - graph optimization, quantization, kernel auto-tuning
- **[vllm-engine/](vllm-engine/)** - vLLM serving engine - PagedAttention, continuous batching, high-throughput LLM serving
- **[context-caching/](context-caching/)** - LLM context caching from scratch on a tiny pure-Python transformer: KV cache, block-hash and radix-tree prefix caching, paged KV blocks with copy-on-write, semantic response caching, and cache-aware request routing (16 graded checks via `python3 check.py`)
- **[contextcite/](contextcite/)** - ContextCite (NeurIPS 2024) replicated from scratch: context attribution by ablating sources and fitting a sparse LASSO surrogate - source partitioning, logit-probability scoring, coordinate-descent LASSO, held-out LDS evaluation, and the paper's three applications (14 graded checks via `python3 check.py`)

### System Design & Distributed Systems
- **[system-design/](system-design/)** - Core distributed systems patterns: caching (LRU, cache-aside, stampede), async queues (retries, backoff, DLQ, idempotency), reliability (circuit breaker, bulkhead, backpressure), consistent hashing, leaderboards, URL shortener, rate limiter, and capacity math
- **[system-design/auth/](system-design/auth/)** - Authentication protocols from scratch, stdlib only: server-side sessions, HS256 JWTs (`alg=none` and RS256/HS256 confusion rejected, constant-time compare), and the OAuth 2.0 authorization code flow with PKCE (exact `redirect_uri`, single-use codes) - 14 graded checks via `python3 check.py`
- **[system-design/replication/](system-design/replication/)** - Leader-follower replication with failover from scratch: the Raft up-to-date rule (term before length), quorum commit, synchronous vs asynchronous replication (measured data loss on failover), most-up-to-date election, and epoch fencing against a partitioned old leader - 10 graded checks via `python3 check.py`
- **[system-design/microservices/](system-design/microservices/)** - The operational core of microservices from scratch: service discovery with TTL heartbeats and graceful draining, an API gateway (longest-prefix routing, client-side round-robin, retries only for idempotent methods on transient failures), and versioned-contract compatibility checking - 13 graded checks via `python3 check.py`
- **[dynamo-paper/](dynamo-paper/)** - Amazon's Dynamo paper (SOSP 2007) implemented directly: consistent hashing with preference lists, vector clocks, N/R/W quorums, sloppy quorum with hinted handoff, Merkle-tree anti-entropy, and gossip membership (17 graded checks via `python3 check.py`)
- **[aws-from-scratch/](aws-from-scratch/)** - Learn AWS by implementing toy versions of its core services: IAM policy evaluation, S3 with versioning and delete markers, SQS visibility timeouts, DynamoDB hot partitions, Lambda concurrency and cold starts, SNS filter policies and EventBridge patterns, KMS envelope encryption, VPC stateful-vs-stateless networking, plus a capstone pipeline wiring them together - and a map of which remaining AWS services are variations of which mechanism (18 graded checks via `python3 check.py`)
- **[database-from-scratch/](database-from-scratch/)** - A crash-safe transactional database in pure Python: pager with LRU buffer pool, B+tree (byte-based splits), write-ahead log with CRC framing and redo recovery tested by truncating the log at every byte, MVCC with four isolation levels, the anomaly x isolation-level matrix produced by your own engine, and atomic vs async secondary indexes (SQL vs NoSQL, measured). 18 graded checks, themselves mutation-tested

### AI Agents
- **[harness-lab/](harness-lab/)** - Coding-agent harness from scratch: seven subsystems, the distinctive mechanism of each major harness (OpenHands, Aider, Codex, opencode, ...) as a swappable variant, and a controlled experiment comparing them. Phase 0: a Docker-sandboxed evaluation bench of 20 tasks with hardened hidden-test verifiers, null/oracle control agents and paired-comparison power analysis. Phase 1 now ships a LEARN contract ([spec](harness-lab/docs/phase1.md)): message and model interfaces, a deterministic scripted backend, the linear-loop stub the learner implements, and its tests; the model-backed baseline awaits the model API
- **[agent-evals/](agent-evals/)** - Evaluation, safety and operations tooling layered on harness-lab: 15 projects mapped (trajectory grading, judge calibration, CI gates, red-teaming, drift, contamination...). Done: red-team fuzzer v1 - six adversarial scenarios (file, tool-output and statement injection, scope overreach) with state-based detectors proved by null/oracle/complicit controls. Three more projects ([#7](agent-evals/stats_engine/), [#13](agent-evals/eviction/), [#14](agent-evals/contamination/)) now ship a LEARN contract: guidelines, a cited reading list, and a runnable test suite that is green with the core stubbed
- **[inference-lab/](inference-lab/)** - Plan for 15 inference-infrastructure projects (serving, TTFT/ITL load curves, KV cache, prefix-cache routing, quantization, speculative decoding, Triton, chunked prefill, PagedAttention, disaggregation, autoscaling, gateways, chaos), mapped onto existing directories and split by whether they need a GPU. Built: the KV-cache monitor (#3, a simulated block pool with preemption and a capacity recommendation), the prefix-caching proxy (#4) and the AI gateway (#13)
- **[enterprise-ai-projects/](enterprise-ai-projects/)** - Implementation guides (not solutions, no code) for twelve enterprise AI projects: bi-directional legacy sync with conflict resolution, zero-trust multi-tenant RAG, PII redaction proxy, air-gapped deployment, ROI telemetry, idempotent webhook reconciliation, SSO/SCIM bridge, model fallback gateway, compliance-as-code auditing, an MCP server for legacy ERPs, shadow traffic evaluation, and a tested incident runbook. Each guide names a real system to build against (Oracle Free, Keycloak, Presidio, Zarf, the SAP ABAP trial image, Envoy), the design decisions with their costs, the limit case that breaks it, and verified references - plus where three of the twelve are already built elsewhere in this repo. The MCP server is no longer only a guide: [mcp-from-scratch/](mcp-from-scratch/) has a spec, resources, a runnable test contract (JSON-RPC over streamable HTTP against a fake ERP) and a reference implementation behind a twelve-bug mutation test
- **[rag-from-scratch/](rag-from-scratch/)** - Plan for ten RAG projects (hybrid search, metadata filtering, reranking, contextual chunking, SQL+vector, graph+vector, corrective, Self-RAG, multimodal, agentic) as one pipeline on a shared evaluation set with no-answer queries; frameworks replaced by BM25, HNSW, SQLite and a triple store built here; corrections to the claims of the source list. Step 0 (the shared eval set) and projects 1-8 (hybrid, metadata filters, reranking, chunking, SQL+vector, graph+vector, corrective, Self-RAG) are built; multimodal and agentic RAG are planned
- **[interview-prep/](interview-prep/)** - 20 AI-engineering interview questions (RAG, hallucinations, evals, cost, multi-agent loops, prompt injection, memory, tool-call grading...), each mapped to what this repo builds, with the follow-up an interviewer uses to tell recitation from experience. No answers by design

### Operations & Reliability
- **[deploy-and-debug/](deploy-and-debug/)** - Running the systems in this repo and debugging them when they break: capacity math (KV cache sizing, N/R/W failure tolerance), percentiles/queueing/error budgets, root-cause diagnosis of 11 injected faults from metrics alone, and safe rollout (liveness vs readiness, canary analysis, budget-based auto-rollback) - plus a runbook of the real vllm/nodetool/nvidia-smi/k8s commands (12 graded checks via `python3 check.py`)

### Web
- **[web-launch-checklist/](web-launch-checklist/)** - Sixteen pre-launch items (404, titles, descriptions, favicon, robots.txt, sitemap, Open Graph, alt text, mobile, loading and error states, legal pages, cookies, analytics, contact, WebP) learned from the failure side: an observer (crawler, link unfurler, screen reader, phone, impatient user) measures the damage before and after each fix. Exercises 1-13 are built (crawler, unfurl, visit, reader and impatient observers, `check.py`, a reference and a broken variant, 65 mutation-tested planted bugs); the mobile and WebP exercises need a browser and Pillow; no answers by design

### Data Engineering & Analytics
- **[sas-lineage-tool/](sas-lineage-tool/)** - SAS field lineage parser for tracking data transformations and dependencies
- **[web-scraping/](web-scraping/)** - Industrial web scraping/crawler library (Python/C, CUDA acceleration, CAPTCHA bypass, distributed architecture)

### Quantitative Finance & Trading
- **[quantitative-trading/](quantitative-trading/)** - Algorithmic trading systems (statistical arbitrage, ML strategies, RL agents, market microstructure)

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
*Relevant for: bash-from-scratch, http-server, dns-server, c-compiler*
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
*Relevant for: distributed-training, ml-in-production, mlops, ml-inference, diffusion-models, deepfake-creation, deepfake-detection, world-models*
- [CS229 - Machine Learning - Stanford](http://cs229.stanford.edu/)
- [6.S191 - Introduction to Deep Learning - MIT](http://introtodeeplearning.com/)
- [Deep Learning Specialization - Various Universities](https://github.com/Developer-Y/cs-video-courses#deep-learning)
- [Computer Vision Courses](https://github.com/Developer-Y/cs-video-courses#computer-vision)
- [Generative AI and LLMs](https://github.com/Developer-Y/cs-video-courses#generative-ai-and-llms)

### MLOps & Production ML
*Relevant for: sgl-lang, tensorrt-inference, vllm-engine*
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

### Computational Finance
*Relevant for: quantitative-trading*
- [Computational Finance Courses](https://github.com/Developer-Y/cs-video-courses#computational-finance)

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