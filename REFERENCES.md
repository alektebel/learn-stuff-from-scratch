# References

One canonical source per mechanism, by week. Where a directory already carries
its own reading list, this points at it rather than repeating it.

**Two rules.** Read the primary source, not a summary of it — most of these are
short, and the summaries drop exactly the caveat that matters. And when a demo
here disagrees with a paper, the paper is probably right and the disagreement is
the interesting part: write it down.

---

## Week 1 · [`aws-from-scratch/`](week-01/aws-from-scratch/)

- **IAM policy evaluation logic** — AWS docs, *Policy evaluation logic*. The
  three-line rule the whole directory is gated on.
- DeCandia et al., **"Dynamo: Amazon's Highly Available Key-value Store"**, SOSP
  2007 — what DynamoDB's partition key inherits. Built in full in week 10.
- **AWS Well-Architected Framework** — the six pillars, revisited in week 12.
- The current **AWS price list**, for anything `pricing.py` asserts. The ratios
  in the demo are right; the absolute numbers are dated by design.

## Week 2 · [`autograd/`](week-02/autograd/)

- Baydin, Pearlmutter, Radul & Siskind, **"Automatic Differentiation in Machine
  Learning: a Survey"**, JMLR 2018 — why reverse mode, and the forward/reverse
  cost asymmetry the demo measures.
- Griewank & Walther, **"Evaluating Derivatives"**, 2008 — the book, if the
  survey leaves you wanting the proofs.
- Glorot & Bengio, AISTATS 2010; He et al., **"Delving Deep into Rectifiers"**,
  ICCV 2015 — the two initialisation scales, and why ReLU needs the second.
- Kingma & Ba, **"Adam"**, ICLR 2015 — read §2 for bias correction, then check
  which direction it cuts before writing anything about it.
- Loshchilov & Hutter, **"Decoupled Weight Decay Regularization"**, ICLR 2019 —
  AdamW, and why L2 and weight decay are not the same under Adam.
- Srivastava et al., **"Dropout"**, JMLR 2014 — including the inverted scaling.
- Kingma & Welling, **"Auto-Encoding Variational Bayes"**, ICLR 2014 — the
  reparameterisation trick in `generative.py`.

## Week 2 · [`llm-from-scratch/`](week-02/llm-from-scratch/)

- Vaswani et al., **"Attention Is All You Need"**, NeurIPS 2017 — §3.2.1 is the
  scaled dot product and the √d_k you must not omit.
- Sennrich, Haddow & Birch, **"Neural Machine Translation of Rare Words with
  Subword Units"**, ACL 2016 — BPE, and why merges apply in rank order.
- Ba, Kiros & Hinton, **"Layer Normalization"**, 2016.
- Xiong et al., **"On Layer Normalization in the Transformer Architecture"**,
  ICML 2020 — why pre-norm trains without a warmup and post-norm does not.
- Press & Wolf, **"Using the Output Embedding to Improve Language Models"**,
  EACL 2017 — weight tying.
- Holtzman et al., **"The Curious Case of Neural Text Degeneration"**, ICLR 2020
  — top-p, and why greedy decoding produces text nobody would write.
- Raschka, **Build a Large Language Model (From Scratch)**; Karpathy, **nanoGPT**
  — the two best walk-throughs if you get stuck on shapes.

### `distill.py` specifically

- Hinton, Vinyals & Dean, **"Distilling the Knowledge in a Neural Network"**,
  2015 — the T² correction is §2.
- Wang et al., **"MiniLM"**, NeurIPS 2020 — attention and value-relation
  transfer, and why it needs no layer mapping.
- Agarwal et al., **"GKD: Generalized Knowledge Distillation"**, 2023 — the β
  family, and on-policy sampling.
- Rafailov et al., **"Direct Preference Optimization"**, NeurIPS 2023 — the
  identity in §4 is the one `methods.py` round-trips.

## Week 3 · [`rl-posttraining/`](week-03/rl-posttraining/)

Full list in that directory's README — Sutton & Barto ch. 13, Spinning Up, the
RLHF Book, Schulman's KL note, Weng, YugeTen, Dr. GRPO, async GRPO, TRL.

The two to start with: **Schulman, "Approximating KL Divergence"**
(joschu.net) for k1/k2/k3, and **Schulman et al., "Proximal Policy Optimization
Algorithms"**, 2017 for the clip.

## Week 3 · [`context-caching/`](week-03/context-caching/)

- Kwon et al., **"Efficient Memory Management for Large Language Model Serving
  with PagedAttention"**, SOSP 2023 — the paged KV cache and copy-on-write.
- Zheng et al., **"SGLang: Efficient Execution of Structured Language Model
  Programs"**, 2023 — RadixAttention, i.e. `radix_cache.py`.
- Pope et al., **"Efficiently Scaling Transformer Inference"**, 2022 — the
  arithmetic behind why decode is memory-bound.

## Week 4 · [`inference-from-scratch/`](week-04/inference-from-scratch/)

- Yu et al., **"Orca: A Distributed Serving System for Transformer-Based
  Generative Models"**, OSDI 2022 — continuous batching, before vLLM.
- Kwon et al., SOSP 2023 (above) — paged KV, block allocation, fragmentation.
- Leviathan, Kalman & Matias, **"Fast Inference from Transformers via
  Speculative Decoding"**, ICML 2023; and Chen et al., **"Accelerating LLM
  Decoding with Speculative Sampling"**, 2023 — read both, they differ.
- Dao et al., **"FlashAttention"**, NeurIPS 2022 — the IO-aware argument.
- **NVIDIA CUDA C++ Programming Guide**, §CUDA Graphs — for step 7.

## Week 4 · [`deploy-and-debug/`](week-04/deploy-and-debug/)

- Beyer et al., **Site Reliability Engineering** (Google) — error budgets ch. 3,
  and the chapter on alerting on symptoms rather than causes.
- Dean & Barroso, **"The Tail at Scale"**, CACM 2013 — why p99 is the number.

## Week 5 · attribution

- Cohen-Wang et al., **"ContextCite: Attributing Model Generation to Context"**,
  NeurIPS 2024 — [`contextcite/`](week-05/contextcite/).
- [`spade/`](week-05/spade/) and [`mars-sql/`](week-05/mars-sql/) carry their own
  reading lists.
- Tibshirani, **"Regression Shrinkage and Selection via the Lasso"**, JRSS-B
  1996 — the surrogate ContextCite fits.

## Week 6 · [`provenance-semirings/`](week-06/provenance-semirings/)

- Green, Karvounarakis & Tannen, **"Provenance Semirings"**, PODS 2007 — the
  whole directory. Prop. 3.4 is the universality theorem `check.py` tests.
- Cheney, Chiticariu & Tan, **"Provenance in Databases: Why, How, and Where"**,
  FnTDB 2009 — the taxonomy, and where lineage loses information.
- Green & Tannen, **"The Semiring Framework for Database Provenance"**, PODS
  2017 — the retrospective, including absorption and recursion.

## Week 7 · [`scasp/`](week-07/scasp/)

- Arias, Carro, Salazar, Marple & Gupta, **"Constraint Answer Set Programming
  without Grounding"**, TPLP 2018 — s(CASP), including dual rules.
- Gelfond & Lifschitz, **"The Stable Model Semantics for Logic Programming"**,
  1988 — what an answer set *is*.

## Week 8 · [`linc/`](week-08/linc/)

- Olausson et al., **"LINC: A Neurosymbolic Approach for Logical Reasoning by
  Combining Language Models with First-Order Logic Provers"**, EMNLP 2023 —
  read the **error analysis**; `faults.py` is built from it.
- Pan et al., **"Logic-LM"**, EMNLP 2023 Findings — and note the fallback, which
  is what destroys its ability to say *unknown*.
- Lyu et al., **"Faithful Chain-of-Thought Reasoning"**, 2023.
- Robinson, **"A Machine-Oriented Logic Based on the Resolution Principle"**,
  JACM 1965 — resolution and unification.

## Week 8 · [`distributed-training/`](week-08/distributed-training/)

- Goyal et al., **"Accurate, Large Minibatch SGD"**, 2017 — the linear scaling
  rule and warmup.
- Li et al., **"PyTorch Distributed: Experiences on Accelerating Data Parallel
  Training"**, VLDB 2020.
- Rajbhandari et al., **"ZeRO"**, SC 2020 — where the memory actually goes.

## Week 9 · [`database-engine/`](week-09/database-engine/)

- Hellerstein, Stonebraker & Hamilton, **"Architecture of a Database System"**,
  FnTDB 2007 — read this first; it is the map for the whole directory.
- Comer, **"The Ubiquitous B-Tree"**, ACM Computing Surveys 1979.
- Mohan et al., **"ARIES"**, TODS 1992 — redo-then-undo, and why in that order.
- Berenson et al., **"A Critique of ANSI SQL Isolation Levels"**, SIGMOD 1995 —
  where write skew comes from.
- Fekete et al., **"Making Snapshot Isolation Serializable"**, TODS 2005 — and
  what it costs to close the gap.
- Graefe, **"Volcano — An Extensible and Parallel Query Evaluation System"**,
  TKDE 1994 — the iterator model in `executor.py`.
- Selinger et al., **"Access Path Selection in a Relational Database Management
  System"**, SIGMOD 1979 — cost-based planning, and the crossover.
- **CMU 15-445** lectures, if you want the whole thing narrated.

### `lsm.py` and `datastep.py`

- O'Neil, Cheng, Gawlick & O'Neil, **"The Log-Structured Merge-Tree (LSM-Tree)"**,
  Acta Informatica 1996 — the original.
- Athanassoulis et al., **"Designing Access Methods: The RUM Conjecture"**,
  EDBT 2016 — read, write and space amplification, and why you get two of three.
  This is what `lsm.py`'s demo measures.
- Dayan, Athanassoulis & Idreos, **"Monkey: Optimal Navigable Key-Value Store"**,
  SIGMOD 2017 — how to size bloom filters ACROSS levels rather than uniformly,
  which is the non-obvious part.
- Bloom, **"Space/Time Trade-offs in Hash Coding with Allowable Errors"**,
  CACM 1970.
- The **RocksDB wiki** on leveled vs universal compaction — the clearest
  practitioner account of the same trade.
- **SAS Language Reference**, the DATA step chapter — the PDV, the implicit
  loop, `RETAIN`, BY-groups and `MERGE`. There is no paper; the manual is the
  specification, and the `MERGE` many-to-many behaviour is documented rather
  than derivable.
- Wickham, **"The Split-Apply-Combine Strategy for Data Analysis"**, JSS 2011 —
  the same problems, solved declaratively, for the comparison.

## Week 10 · consensus, and its refusal

- DeCandia et al., **"Dynamo"**, SOSP 2007 — [`dynamo-paper/`](week-10/dynamo-paper/).
- Ongaro & Ousterhout, **"In Search of an Understandable Consensus Algorithm"**,
  USENIX ATC 2014 — [`raft/`](week-10/raft/). **Figure 8 before you write
  `replication.py`.**
- Lamport, **"Paxos Made Simple"**, 2001 — the thing Raft was written to replace.
- Gilbert & Lynch, **"Brewer's Conjecture and the Feasibility of Consistent,
  Available, Partition-Tolerant Web Services"**, SIGACT News 2002 — CAP, proved.

## Week 11 · [`blockchain-from-scratch/`](week-11/blockchain-from-scratch/)

- Nakamoto, **"Bitcoin: A Peer-to-Peer Electronic Cash System"**, 2008 — §11 is
  the `(q/p)^k` catch-up probability `fork.py` simulates.
- Eyal & Sirer, **"Majority Is Not Enough: Bitcoin Mining Is Vulnerable"**, FC
  2014 — selfish mining, and the γ dependence.
- Lamport, Shostak & Pease, **"The Byzantine Generals Problem"**, TOPLAS 1982 —
  the fault model that separates this week from week 10.
- Castro & Liskov, **"Practical Byzantine Fault Tolerance"**, OSDI 1999 — BFT
  with known membership, i.e. the case Bitcoin does *not* solve.
- Merkle, **"A Digital Signature Based on a Conventional Encryption Function"**,
  CRYPTO 1987 — the tree.
- Wood, **Ethereum Yellow Paper** — the EVM, gas, and the Merkle-Patricia trie.
- Buterin & Griffith, **"Casper the Friendly Finality Gadget"**, 2017 —
  accountable safety, and the ⅓ slashing bound `pos.py` checks.

## Week 12 · AWS certification and deployment

- The **current official exam guides** — TODO §10.10 says to diff them against
  the check list before anything else. They are the authority; this repo is not.
- **AWS Well-Architected Framework** and its lenses — [`aws-certification/wellarchitected.py`](week-12/aws-certification/).
- **AWS Security Best Practices** / IAM docs — least privilege, permission
  boundaries, and the credential resolution chain.
- **AWS Service Quotas** and the **price list API** — the two sources that
  answer "is this a limit or a bug" and "what will this cost", better than any
  documentation page.

## Week 13–14 · sockets and protocols

- Stevens, Fenner & Rudoff, **UNIX Network Programming, Vol. 1** — the reference
  for [`http-server/`](week-13/http-server/) and [`toralizer/`](week-14/toralizer/).
- Kerrisk, **The Linux Programming Interface** — `fork`, `exec`, pipes, signals,
  for [`bash-from-scratch/`](week-13/bash-from-scratch/).
- **RFC 9110** (HTTP semantics) and **RFC 9112** (HTTP/1.1) — these supersede
  RFC 2616, which most tutorials still cite.
- **RFC 1034 / 1035** — DNS, for [`dns-server/`](week-14/dns-server/).
- **FIPS 180-4** — SHA-2, for [`cryptographic-library/`](week-14/cryptographic-library/).
- **RFC 1928** — SOCKS5, for `toralizer/`.
- **NXP UM10204** (I²C) and the **Bosch CAN 2.0 specification** — for
  [`communication-protocols/`](week-14/communication-protocols/).

## Week 15 · compilers

- Aho, Lam, Sethi & Ullman, **Compilers: Principles, Techniques, and Tools** —
  the Dragon Book. Chapters 3–6 cover this week.
- Sandler, **Writing a C Compiler**, 2024 — the closest thing to a walk-through
  of exactly this project.
- Poletto & Sarkar, **"Linear Scan Register Allocation"**, TOPLAS 1999 — the
  allocator and its spilling, which is what
  [`c-compiler/`](week-15/c-compiler/)'s `codegen.c` implements.
- Patterson & Hennessy, **Computer Organization and Design** — instruction
  encoding and the fetch/decode/execute loop, for
  [`compiler-and-vgpu/`](week-15/compiler-and-vgpu/)'s `isa.py` and `cpu.py`.
- Nickolls, Buck, Garland & Skadron, **"Scalable Parallel Programming with
  CUDA"**, ACM Queue 2008 — what SIMT *is*, and the one-PC-per-warp model
  `vgpu.py` implements.
- Fung, Sham, Yuan & Aamodt, **"Dynamic Warp Formation and Scheduling for
  Efficient GPU Control Flow"**, MICRO 2007 — branch divergence and the mask
  stack, and what hardware does about it.
- **RFC 791 / 793** — IP and TCP headers, for
  [`firewall-from-scratch/`](week-15/firewall-from-scratch/).
- Nielsen & Chuang, **Quantum Computation and Quantum Information** — ch. 4 for
  [`quantum-computing-lang/`](week-15/quantum-computing-lang/).

## Week 16 · [`cuda-from-scratch/`](week-16/cuda-from-scratch/)

- **NVIDIA CUDA C++ Programming Guide** and the **Best Practices Guide** — the
  primary sources, and genuinely good.
- Kirk & Hwu, **Programming Massively Parallel Processors** — the textbook.
- Harris, **"Optimizing Parallel Reduction in CUDA"** — seven versions of one
  kernel, each faster than the last, with the reason stated. The single best
  worked example of the profile-then-fix loop this week is about.
- Volkov & Demmel, **"Benchmarking GPUs to Tune Dense Linear Algebra"**, SC 2008
  — why occupancy is not the goal, and the case `occupancy.py` must reproduce.
- Williams, Waterman & Patterson, **"Roofline: An Insightful Visual Performance
  Model"**, CACM 2009 — `roofline.py`, and the one plot that says which
  optimisation can possibly help.
- Fregly, **AI Systems Performance Engineering** (O'Reilly) —
  [repo](https://github.com/cfregly/ai-performance-engineering). Chapters 6–12
  are `roofline.py`, `occupancy.py`, `coalescing.py` and `pipelining.py`.
  **Chapters 2–5 and 13–19 need a GPU in front of you** — Nsight counters,
  tensor cores, NVLink topology, power and thermal, PyTorch/Triton/XLA. None of
  that is fakeable in pure Python and this repo does not pretend otherwise.
- Zhong et al., **"DistServe"**, OSDI 2024; Patel et al., **"Splitwise"**, ISCA
  2024 — prefill/decode disaggregation, for
  `week-04/inference-from-scratch/disaggregate.py` (Fregly ch. 17–18).
- Thakur, Rabenseifner & Gropp, **"Optimization of Collective Communication
  Operations in MPICH"**, IJHPCA 2005; Patarasuk & Yuan on bandwidth-optimal
  all-reduce — `week-08/distributed-training/collectives.py` (Fregly ch. 4).

## Week 17 · patterns, light, Haskell

- Leis, Gubichev, Mirchev, Boncz, Kemper & Neumann, **"How Good Are Query
  Optimizers, Really?"**, VLDB 2015 — the single deepest result in query
  processing: estimation error compounds multiplicatively with join count, so
  the planner picks a bad plan **correctly**. `database-internals/estimation.py`.
- Flajolet, Fusy, Gandouet & Meunier, **"HyperLogLog"**, AofA 2007; Cormode &
  Muthukrishnan, **"Count-Min Sketch"**, J. Algorithms 2005 — what a planner's
  statistics actually are.
- Stonebraker et al., **"C-Store"**, VLDB 2005; Abadi, Madden & Ferreira,
  **"Integrating Compression and Execution in Column-Oriented Database
  Systems"**, SIGMOD 2006 — column layout and late materialization.
- Boncz, Zukowski & Nes, **"MonetDB/X100"**, CIDR 2005; Neumann, **"Efficiently
  Compiling Efficient Query Plans for Modern Hardware"**, VLDB 2011 — the two
  answers to the Volcano model's per-tuple overhead.
- Kung & Robinson, **"On Optimistic Methods for Concurrency Control"**, TODS
  1981; Cahill, Röhm & Fekete, **"Serializable Isolation for Snapshot
  Databases"**, SIGMOD 2008.
- Petrov, **Database Internals**, 2019 — most of the above in one narrative.
- Kleppmann, **Designing Data-Intensive Applications** — for
  [`reference/system-design/`](reference/system-design/), and honestly for the
  whole repo.
- Karger et al., **"Consistent Hashing and Random Trees"**, STOC 1997.
- Nygard, **Release It!** — circuit breakers, bulkheads, backpressure.
- Shirley, **Ray Tracing in One Weekend** — [`ray-tracer/`](week-17/ray-tracer/).
- Pharr, Jakob & Humphreys, **Physically Based Rendering** (free online) — the
  reference. Ch. 4 for BVH and the surface area heuristic.
- Kajiya, **"The Rendering Equation"**, SIGGRAPH 1986 — the integral the whole
  directory is estimating.
- Hutton, **Programming in Haskell**; Hutton & Meijer, **"Monadic Parser
  Combinators"** — [`haskell-projects/`](week-17/haskell-projects/).

## Week 18 · the tail

- von Luxburg, **"A Tutorial on Spectral Clustering"**, 2007; Shi & Malik,
  **"Normalized Cuts and Image Segmentation"**, PAMI 2000 — for
  [`spectral-graphs/`](week-18/spectral-graphs/).
- Sculley et al., **"Hidden Technical Debt in Machine Learning Systems"**,
  NeurIPS 2015 — the one paper to read before
  [`ml-in-production/`](week-18/ml-in-production/) or [`mlops/`](week-18/mlops/).
- Olston & Najork, **"Web Crawling"**, FnTIR 2010; and **RFC 9309** (Robots
  Exclusion Protocol) — for [`web-scraping/`](week-18/web-scraping/). The RFC is
  short and is the part with obligations attached.
- Cheney, Chiticariu & Tan (week 6, above) — data lineage is provenance with the
  algebra removed, which is the right way to read
  [`sas-lineage-tool/`](week-18/sas-lineage-tool/) after week 6.

## Daily · [`lean-proofs/`](lean-proofs/)

- Avigad, de Moura, Kong & Ullrich, **Theorem Proving in Lean 4** — the manual.
- **Mathematics in Lean** — the tutorial that matches this directory's ladder.
- Artin, **Algebra**, ch. 14–16 — the mathematics the Galois track is formalising.

## Not scheduled · [`reference/`](reference/)

Those five directories carry their own reading lists. `vllm-engine` and
`tensorrt-inference` are where you go **after** week 4, with your own scheduler
open beside them. The primary sources, so you can read without opening them:

- [`vllm-engine/`](reference/vllm-engine/) — Kwon et al., **PagedAttention**,
  SOSP 2023. The same paper as week 3 and week 4; read it a third time here,
  against your own block allocator.
- [`tensorrt-inference/`](reference/tensorrt-inference/) — the **NVIDIA TensorRT
  Developer Guide**, on layer fusion, precision calibration and kernel
  auto-tuning. Vendor documentation, and the honest place for it.
- [`ml-inference/`](reference/ml-inference/) — Jacob et al., **"Quantization and
  Training of Neural Networks for Efficient Integer-Arithmetic-Only
  Inference"**, CVPR 2018; and Dettmers et al., **"LLM.int8()"**, 2022, for what
  changes at transformer scale.
- [`world-models/`](reference/world-models/) — Ha & Schmidhuber, **"World
  Models"**, 2018; then Hafner et al., **Dreamer** v1 (ICLR 2020), v2 (ICLR
  2021) and v3 (2023); then Micheli et al., **IRIS**, ICLR 2023.
- [`diffusion-models/`](reference/diffusion-models/) — Ho, Jain & Abbeel,
  **"Denoising Diffusion Probabilistic Models"**, NeurIPS 2020; Song, Meng &
  Ermon, **"DDIM"**, ICLR 2021; Ho & Salimans, **"Classifier-Free Diffusion
  Guidance"**, 2022; Ronneberger, Fischer & Brox, **"U-Net"**, MICCAI 2015.

---

## Method, not content

- Ericsson, Krampe & Tesch-Römer, **"The Role of Deliberate Practice"**, 1993 —
  the predict-then-run loop is deliberate practice; the checkers are the
  immediate feedback it requires.
- Roediger & Karpicke, **"Test-Enhanced Learning"**, 2006 — why `drill.py` and
  `defend.py` are separate from `check.py`, and why retrieval beats review.

---

[Roadmap](ROADMAP.md) · [Implementation order](IMPLEMENTATION_ORDER.md) · [TODO](TODO.md)
