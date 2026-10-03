# What you implement, week by week, file by file

Every file you will open, in the order you will open it, with its stub count
in brackets. This is the bullet-point version of [`ROADMAP.md`](ROADMAP.md);
that file has the arithmetic, this one has the list.

`C` marks a directory on `core`, `S` on `spine`. Five directories are not on
the schedule at all — see [`reference/`](reference/).

**Two things run daily and are not below:** `lean-proofs/` (~8.4 h/week) and
`week-12/aws-certification/drill.py`, from week 1. Neither can be crammed.

---

## Week 1 · Aug 24–Aug 30 — AWS, from its mechanisms up

`aws-from-scratch` 42 h **C** **S**

- **`week-01/aws-from-scratch/`**
  - `billing.py` **[13]**
  - `capstone.py` **[5]**
  - `dynamodb.py` **[13]**
  - `iam.py` **[10]**
  - `kms.py` **[12]**
  - `lambda_svc.py` **[8]**
  - `optimize.py` **[15]**
  - `pricing.py` **[17]**
  - `s3.py` **[16]**
  - `sns.py` **[9]**
  - `sqs.py` **[8]**
  - `vpc.py` **[14]**

## Week 2 · Aug 31–Sep 6 — LLMs

`autograd` 30 h **C** **S** · `llm-from-scratch` 55 h **C** **S**

- **`week-02/autograd/`**
  - `generative.py` **[13]**
  - `nn.py` **[13]**
  - `optim.py` **[7]**
  - `tensor.py` **[27]**
  - `train.py` **[7]**
- **`week-02/llm-from-scratch/`**
  - `attention.py` **[4]**
  - `distill.py` **[12]**
  - `engine.py` **[2]**
  - `sample.py` **[9]**
  - `tokenizer.py` **[10]**
  - `train.py` **[4]**
  - `transformer.py` **[8]**

## Week 3 · Sep 7–Sep 13 — Teaching a model: distil, then reward

`rl-posttraining` 30 h **C** · `context-caching` 28 h **C**

- **`week-03/rl-posttraining/`**
  - `async_rl.py` **[3]**
  - `baselines.py` **[4]**
  - `dpo.py` **[4]**
  - `env.py` **[3]**
  - `grpo.py` **[3]**
  - `kl_estimators.py` **[4]**
  - `policy_gradient.py` **[4]**
  - `ppo.py` **[4]**
  - `reward_hacking.py` **[3]**
- **`week-03/context-caching/`**
  - `cache_router.py` **[13]**
  - `kv_cache.py` **[17]**
  - `paged_kv_cache.py` **[13]**
  - `prefix_cache.py` **[11]**
  - `radix_cache.py` **[12]**
  - `semantic_cache.py` **[12]**
  - `serving_demo.py` **[6]**
  - `tiny_transformer.py` **[10]**

## Week 4 · Sep 14–Sep 20 — Serving it yourself

`inference-from-scratch` 60 h **C** **S** · `deploy-and-debug` 10 h **C**

- **`week-04/inference-from-scratch/`**
  - `batching.py` **[3]**
  - `compare.py` **[1]**
  - `deeper.py` **[5]**
  - `gpu_opt.py` **[4]**
  - `inference_path.py` **[2]**
  - `kv_runtime.py` **[3]**
  - `naive_server.py` **[2]**
  - `observe.py` **[2]**
  - `paged_kv.py` **[7]**
  - `scheduler.py` **[5]**
  - `speculate.py` **[4]**
  - `traffic.py` **[3]**
- **`week-04/deploy-and-debug/`**
  - `capacity.py` **[10]**
  - `diagnose.py` **[4]**
  - `metrics.py` **[11]**
  - `rollout.py` **[9]**

## Week 5 · Sep 21–Sep 27 — Attribution, on a real task

`contextcite` 13 h **C** · `spade` 16 h **C** · `mars-sql` 20 h **C**

- **`week-05/contextcite/`**
  - `ablation.py` **[5]**
  - `applications.py` **[5]**
  - `contextcite.py` **[8]**
  - `evaluate.py` **[5]**
  - `lasso.py` **[7]**
  - `logit_probs.py` **[7]**
  - `partition.py` **[5]**
- **`week-05/spade/`**
  - `candidates.py` **[5]**
  - `cite.py` **[3]**
  - `deltas.py` **[4]**
  - `selector.py` **[5]**
  - `taxonomy.py` **[2]**
- **`week-05/mars-sql/`**
  - `cite.py` **[4]**
  - `generation.py` **[5]**
  - `grounding.py` **[3]**
  - `validation.py` **[3]**

## Week 6 · Sep 28–Oct 4 — Provenance, algebraically

`provenance-semirings` 45 h **C**

- **`week-06/provenance-semirings/`**
  - `datalog.py` **[3]**
  - `homomorphism.py` **[2]**
  - `polynomial.py` **[10]**
  - `ra.py` **[5]**
  - `relation.py` **[7]**
  - `semiring.py` **[49]**

## Week 7 · Oct 5–Oct 11 — Goal-directed reasoning

`scasp` 45 h

- **`week-07/scasp/`**
  - `coinductive.py` **[2]**
  - `dual.py` **[3]**
  - `justify.py` **[3]**
  - `sld.py` **[3]**
  - `term.py` **[8]**
  - `unify.py` **[3]**

## Week 8 · Oct 12–Oct 18 — Parser in front, prover behind

`linc` 30 h · `distributed-training` 10 h

- **`week-08/linc/`**
  - `faults.py` **[3]**
  - `fol.py` **[6]**
  - `parser.py` **[2]**
  - `pipeline.py` **[2]**
  - `prover.py` **[3]**
  - `sweep.py` **[3]**
  - `trace.py` **[3]**
- **`week-08/distributed-training/`**
  - `phase1_data_parallel/template_data_loader.py` **[4]**
  - `phase1_data_parallel/template_trainer.py` **[6]**

## Week 9 · Oct 19–Oct 25 — A database from the disk up

`database-engine` 50 h **C** **S**

- **`week-09/database-engine/`**
  - `btree.py` **[12]**
  - `database.py` **[13]**
  - `executor.py` **[19]**
  - `mvcc.py` **[12]**
  - `pager.py` **[13]**
  - `planner.py` **[20]**
  - `sql.py` **[15]**
  - `wal.py` **[10]**

## Week 10 · Oct 26–Nov 1 — Consensus, and its refusal

`dynamo-paper` 21 h **C** **S** · `raft` 30 h **C**

- **`week-10/dynamo-paper/`**
  - `dynamo_cluster.py` **[13]**
  - `gossip.py` **[10]**
  - `hinted_handoff.py` **[7]**
  - `merkle_sync.py` **[8]**
  - `partitioning.py` **[13]**
  - `quorum.py` **[8]**
  - `vector_clock.py` **[11]**
- **`week-10/raft/`**
  - `cluster.py` **[6]**
  - `election.py` **[7]**
  - `log.py` **[9]**
  - `replication.py` **[8]**

## Week 11 · Nov 2–Nov 8 — Byzantine, and open membership

`blockchain-from-scratch` 55 h **C**

- **`week-11/blockchain-from-scratch/`**
  - `accounts.py` **[4]**
  - `chain.py` **[6]**
  - `evm.py` **[5]**
  - `fork.py` **[5]**
  - `pos.py` **[5]**
  - `pow.py` **[5]**
  - `script.py` **[4]**
  - `trie.py` **[6]**
  - `utxo.py` **[6]**

## Week 12 · Nov 9–Nov 15 — AWS certification block

`aws-certification` 35 h **C**

- **`week-12/aws-certification/`**
  - `decide.py` **[5]**
  - `drill.py` **[5]**
  - `mlstack.py` **[6]**
  - `network.py` **[6]**
  - `resilience.py` **[6]**
  - `storage.py` **[7]**
  - `wellarchitected.py` **[5]**

## Week 13 · Nov 16–Nov 22 — Sockets

`bash-from-scratch` 8 h **C** · `http-server` 86 h **C** **S**

- **`week-13/bash-from-scratch/`**
  - `shell.c` **[18]**
- **`week-13/http-server/`**
  - `http_server.c` **[16]**

## Week 14 · Nov 23–Nov 29 — What a byte stream carries

`dns-server` 9 h · `cryptographic-library` 5 h · `communication-protocols` 34 h · `toralizer` 21 h

- **`week-14/dns-server/`**
  - `dns_server.c` **[20]**
- **`week-14/cryptographic-library/`**
  - `sha256.c` **[12]**
- **`week-14/communication-protocols/`**
  - `can.c` **[23]**
  - `i2c.c` **[26]**
  - `rs232_485.c` **[29]**
  - `spi.c` **[15]**
  - `uart.c` **[22]**
- **`week-14/toralizer/`**
  - `network.c` **[10]**
  - `socks.c` **[19]**
  - `toralizer.c` **[17]**

## Week 15 · Nov 30–Dec 6 — Compilers, and a machine for them

`firewall-from-scratch` 25 h · `c-compiler` 27 h **C** **S** · `compiler-and-vgpu` 16 h **C** **S** · `quantum-computing-lang` 8 h

- **`week-15/firewall-from-scratch/`**
  - `firewall.c` **[68]**
- **`week-15/c-compiler/`**
  - `codegen.c` **[33]**
  - `lexer.c` **[9]**
  - `optimizer.c` **[24]**
  - `parser.c` **[41]**
  - `semantic.c` **[42]**
- **`week-15/compiler-and-vgpu/`**
  - `assembler.py` **[9]**
  - `capstone.py` **[3]**
  - `codegen.py` **[12]**
  - `cpu.py` **[6]**
  - `frontend.py` **[12]**
  - `isa.py` **[3]**
  - `vgpu.py` **[8]**
- **`week-15/quantum-computing-lang/`**
  - `quantum.c` **[17]**

## Week 16 · Dec 7–Dec 13 — CUDA

`cuda-from-scratch` 122 h **C** **S**

- **`week-16/cuda-from-scratch/`**
  - `01_vector_addition.cu` **[16]**
  - `02_matrix_addition.cu` **[15]**
  - `03_matrix_multiplication.cu` **[16]**
  - `04_reduction.cu` **[5]**
  - `05_convolution.cu` **[7]**
  - `06_neural_network_forward.cu` **[9]**
  - `07_neural_network_backward.cu` **[8]**
  - `08_complete_neural_network.cu` **[29]**

## Week 17 · Dec 14–Dec 20 — Patterns, light, and Haskell

`system-design` 48 h · `ray-tracer` 35 h · `haskell-projects` 61 h

- **`week-17/system-design/`**
  - `cache.py` **[12]**
  - `capacity_planner.py` **[5]**
  - `cdn_caching.py` **[7]**
  - `circuit_breaker.py` **[9]**
  - `connection_pooling.py` **[6]**
  - `consistent_hash.py` **[5]**
  - `data_locality.py` **[12]**
  - `edge_computing.py` **[10]**
  - `eventual_consistency.py` **[13]**
  - `hot_partition_mitigation.py` **[8]**
  - `idempotency_keys.py` **[7]**
  - `leaderboard.py` **[14]**
  - `message_queue.py` **[8]**
  - `rate_limiter.py` **[4]**
  - `request_batching.py` **[12]**
  - `session_stickiness.py` **[11]**
  - `throttling.py` **[7]**
  - `url_shortener.py` **[9]**
- **`week-17/ray-tracer/`**
  - `bvh.py` **[5]**
  - `material.py` **[7]**
  - `render.py` **[8]**
  - `shapes.py` **[8]**
  - `vec.py` **[13]**
- **`week-17/haskell-projects/`**
  - `BuildTool.hs` **[22]**
  - `Calculator.hs` **[14]**
  - `JSONParser.hs` **[15]**
  - `WebScraper.hs` **[16]**

## Week 18 · Dec 21–Dec 27 — The long tail

`spectral-graphs` 5 h · `sas-lineage-tool` 8 h · `web-scraping` 6 h · `ml-in-production` 8 h · `mlops` 12 h

- **`week-18/spectral-graphs/`**
  - `spectral_graphs.py` **[11]**
- **`week-18/sas-lineage-tool/`**
  - `template_lineage_parser.py` **[23]**
- **`week-18/web-scraping/`** — no counted templates (design brief or skeleton); see its README
- **`week-18/ml-in-production/`**
  - `phase1_basic_serving/template_model_server.py` **[7]**
- **`week-18/mlops/`**
  - `phase1_tracking/template_experiment_logger.py` **[13]**

---

## Not scheduled — [`reference/`](reference/)

`ml-inference` · `vllm-engine` · `tensorrt-inference` · `world-models` · `diffusion-models`

599 hours, removed. The first three are reading after week 4 is green; the
last two are a genuine cut. Nothing is deleted — see that directory's README
for how to put one back.

---

[Roadmap](ROADMAP.md) · [Philosophy](PHILOSOPHY.md) · [What remains](REMAINING.md) · [TODO](TODO.md)
