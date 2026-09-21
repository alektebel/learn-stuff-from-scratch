# TODO — the work, in steps

Skeletons are in place. Nothing below is implemented. Each step says what to
build and how you will know it is right; the *why* for each is in
[`REMAINING.md`](REMAINING.md).

Steps 1–2 block everything else. Do them before the plan starts.

> **This file is a menu, not a plan.** A hundred and forty-nine boxes across sixteen
> sections, roughly 438 hours, against a schedule already reading 73 h/week.
> Only §12 removes anything. Nothing here is committed to until you write it
> into `ROADMAP.md` and take the hours out of somewhere — so pick a subset, put
> it on the line below, and treat the rest as a backlog.
>
> **Doing now:** `________________`

> **Every step below names its source.** Where it does not, the mechanism is
> either the repo's own or documented in [`REFERENCES.md`](REFERENCES.md) under
> the relevant week. If you are about to implement something and cannot say
> which paper or spec it comes from, that is the gap to close first — it is
> usually the sign that the check is going to be weak.

---

## 1. Verify the 59 existing checks · ~1 day · BLOCKING

Seven directories are check-only. None of their checkers has been run against a
working implementation, so it is not known whether they are passable. An
impossible check is worse than no check: the method here is to trust the
checker over your own reading, and one bad assertion turns that into a trap.

Skeleton: [`tools/verify_checks.py`](tools/verify_checks.py).

- [ ] **1.1** Implement `stage()` — copy templates + `check.py` to a temp dir,
      overlay references from a path **outside the repo**. The checker must
      never run from the repo, so an interrupt cannot leave a reference behind.
- [ ] **1.2** Implement `run_checker()` — parse `"N/M passing"`. A missing line
      is a failure, not a zero; a crashed checker must not look like a clean run.
- [ ] **1.3** Implement `apply_injection()` — assert the target string appears
      **exactly once** before replacing. A silent no-op injection reports as
      "caught" and is the main way a harness like this lies to you.
- [ ] **1.4** Implement `verify()` — pass N/N, then one injection per check,
      each required to make its own check FAIL. Exit non-zero on any MISS.
- [ ] **1.5** Write references (outside the repo) and run it, in this order.
      Delete each reference set as soon as its directory is green.

      | Directory | Stubs | Checks | Pass N/N | Injections caught |
      |---|---|---|---|---|
      | `week-06/provenance-semirings/` | 76 | 8 | ☐ | ☐ |
      | `week-04/inference-from-scratch/` | 41 | 12 | ☐ | ☐ |
      | `week-08/linc/` | 22 | 8 | ☐ | ☐ |
      | `week-07/scasp/` | 22 | 8 | ☐ | ☐ |
      | `week-05/spade/` | 19 | 8 | ☐ | ☐ |
      | `week-05/mars-sql/` | 15 | 8 | ☐ | ☐ |
      | `week-02/llm-from-scratch/distill.py` | 12 | 7 | ☐ | ☐ |

- [ ] **1.6** Add a line to each directory's README recording the date it was
      verified and at what counts. An unverified checker should be visibly
      unverified.

**Done means:** `verify_checks.py` exits 0 for all seven, and no reference
implementation exists anywhere under the repo.

---

## 2. Replace the one check that grades recall · ~2 h

`week-02/llm-from-scratch/check.py` step 14 grades `paper_choices()`, a dict of
strings — it tests whether you remember what a paper said. Every other check in
this repo tests a mechanism.

- [ ] **2.1 MiniLM** *(Wang et al., NeurIPS 2020)* — attention distributions and value-relation matrices are
      `L × L`. Check with a **width-8 teacher and a width-4 student**: the
      targets stay comparable with no layer mapping and no learned projection.
      That property *is* the paper.
- [ ] **2.2 GKD** *(Agarwal et al., 2023)* — generalised JSD with `m = β·teacher + (1−β)·student`. Check
      both limits numerically: `D/β → KL(t‖s)` as `β→0`, `D/(1−β) → KL(s‖t)` as
      `β→1`. A version matching only one limit has the mixture coefficient wrong.
- [ ] **2.3 OPSD** — teacher identical to student ⇒ gradient **exactly zero**,
      both directions. Also: EMA the *logits*, not the probabilities — check
      that the probability-space average drifts toward uniform and the
      logit-space one does not.
- [ ] **2.4 SDPO** *(the identity: Rafailov et al., DPO, NeurIPS 2023 §4)* — several distinct methods use that name. Do not assert one.
      Check the identity they share: `π* ∝ π_ref·exp(r/β)`, inverted to
      `r = β·log(π*/π_ref) + β·log Z`, with the constant cancelling in a
      pairwise margin. Then read the specific paper you meant and add a check
      for whatever it changes.
- [ ] **2.5** Delete `paper_choices()` and its check.

---

## 3. Close the three unreachable claims in `distill.py` · ~4 h

Named in docstrings, not reachable by any check.

- [ ] **3.1** The gradients: `∂KL(t‖s)/∂z = s − t` forward, and
      `s·(log(s/t) − KL(s‖t))` reverse. The leading `s` is *why* mode collapse
      happens — check it against finite differences.
- [ ] **3.2** Mass-covering vs mode-seeking, measured: fit a deliberately
      **unimodal** student to a bimodal teacher under each divergence. Forward
      lands in the valley; reverse commits to one mode. Assert the valley mass
      differs by a wide margin. They only diverge when the student cannot match
      the teacher — which is always, so the student family must be underpowered
      or the check is vacuous.
- [ ] **3.3** The privilege floor in closed form *(the quantity is I(y;z|x); Cover & Thomas ch. 2 for the identity)*: best blind student is the
      marginal `E_z[p(y|x,z)]`, its loss is exactly `I(y;z|x)`. Assert the two
      agree to floating point, then sweep student capacity and assert the loss
      stops at that wall rather than approaching zero.

Draft templates for all three, plus MiniLM/GKD/OPSD/DPO, are in the scratchpad
at `.../scratchpad/superseded/llm/`. Merge or discard.

---

## 4. RL post-training · ~30 h · SKELETON IN PLACE

[`week-03/rl-posttraining/`](week-03/rl-posttraining/) — 9 files, 32 stubs,
9 checks named and unwritten. No `solutions/`.

- [ ] **4.0** Decide what happens to
      `origin/claude/rl-posttraining-llm-exercises-wzfe8w`, which has 8 phases,
      GRPO machinery, a tiny SQL env, tests **and solutions**. Merge `common/`
      and the phase structure into this directory and strip the solutions, or
      keep it separate and accept the overlap. **Nothing below should start
      until this is decided**, or you will build the same thing twice.
- [ ] **4.1** Write the nine checks in `check.py` first, each so it fails
      against a deliberately wrong implementation. The TODO in each check's
      docstring says what to assert.
- [ ] **4.2** `env.py`, then `policy_gradient.py` — the identity against
      central differences. Nothing later is meaningful until this passes.
- [ ] **4.3** `baselines.py` — include the **action-dependent** baseline and
      show it biased. That is the one people ship by accident.
- [ ] **4.4** `kl_estimators.py` — k1/k2/k3, with the negative-sample fraction. *(Schulman, "Approximating KL Divergence", joschu.net)*
- [ ] **4.5** `ppo.py` — clip fraction rising monotonically with drift. *(Schulman et al., PPO 2017; TRPO 2015 for what it replaced)*
- [ ] **4.6** `grpo.py` *(DeepSeekMath for GRPO; Lan, "From REINFORCE to Dr. GRPO" for the correction)* — group baseline, then the length bias measured
      and removed. The bias must be clearly non-zero before removal, or the
      check is testing nothing.
- [ ] **4.7** `async_rl.py` — ESS against lag, and the threshold crossing. *(Xu, "Async GRPO in the Wild"; Kong & Liu on ESS)*
- [ ] **4.8** `reward_hacking.py` — the true reward must **turn over**. *(Gao et al., scaling laws for reward-model over-optimisation; the RLHF Book)*
      Asserting only that the proxy rises tests nothing; that is what
      optimisers do.
- [ ] **4.9** `dpo.py` — round-trip the identity; the recovered reward differs
      by a **constant**, not by zero.
- [ ] **4.10** Add to `progress.py`'s `PLAN` and to the week-05 README, and
      wire the cross-links to `distill.py` and `mars-sql/`.
- [ ] **4.11** Verify with `tools/verify_checks.py`, then delete the references.

---

## 5. Mine and delete `provenance-reasoning` · ~2 h

In the scratchpad at `.../scratchpad/superseded/provenance-reasoning/` — five
templates **and** five working solutions with running demos. Overlaps
`week-06/provenance-semirings/` and `week-08/linc/`. Two results in it are not
in the shipped version:

- [ ] **5.1** The **universality check** *(Green, Karvounarakis & Tannen, PODS 2007, Prop. 3.4)* — evaluate a query once in `N[X]`, then
      derive nine semantics by mapping the answer through a homomorphism, and
      assert it agrees with having evaluated natively in each. That property is
      what makes provenance one feature instead of nine, and an operator that
      does not use `+` and `×` where the definition says passes every row-count
      test and fails exactly this one.
- [ ] **5.2** The **absorption/termination result** *(Green & Tannen, PODS 2017, on ω-continuous and absorptive semirings)* — `a + a×b == a` predicts
      whether a recursive program reaches a fixpoint. Measured: `Boolean`,
      `Tropical` and `PosBool` converge on cyclic data; `Counting` and `N[X]`
      never do, because the answer really is infinite.
- [ ] **5.3** Delete the directory.

---

## 6. Housekeeping · ~1 h

- [ ] **6.1** `IMPLEMENTATION_SUMMARY.md` and
      `LEAN_PROOFS_EXPANSION_SUMMARY.md` are pre-reorganisation artifacts at the
      root — same category as the deepfake summary already deleted.
- [ ] **6.2** `_codeql_detected_source_root` at the root: gitignore or remove.
- [ ] **6.3** **Week folders no longer match `PLAN`'s due weeks.** `raft` and
      `dynamo-paper` live in `week-05/` and are due week 13; `ray-tracer` is in
      `week-08/` and due 17. Either re-home the directories or state in the
      READMEs that the folder is a name, not a date. Right now both readings
      look supported and one of them is wrong.
- [ ] **6.4** `LOG.md` still does not exist, and every week README instructs
      that it be written daily. If `journal/` is now that thing, say so in the
      week READMEs so the instruction points somewhere real.
- [ ] **6.5** Confirm `week-11` and `week-14` READMEs point at where their work
      actually lives — neither has a directory of its own.

---

## 8. Bitcoin / Ethereum · ~55 h · SKELETON IN PLACE

[`week-11/blockchain-from-scratch/`](week-11/blockchain-from-scratch/) — 9 files,
46 stubs, 11 checks named and unwritten. No `solutions/`.

It sits beside `raft/` and `dynamo-paper/` on purpose. Those two cover
**crash faults with known membership**; this is the third corner —
**Byzantine faults with open membership**, where a participant profits by
lying and you do not know who they are. Sybil resistance is the only genuinely
new idea in the subject, and it is worth having next to the other two.

- [ ] **8.1** Write the eleven checks first. Each docstring in `check.py` says
      what to assert and names the weak version to avoid.
- [ ] **8.2** `chain.py` — Merkle root and SPV proof. Assert proof length grows
      as `log2(n)`, and that changing **any** transaction moves the root — per
      transaction, not just the first.
- [ ] **8.3** `pow.py` *(Nakamoto 2008)* — assert hashes-to-block is **geometric**, not merely
      that the mean is `2^d`. A constant would pass a mean-only check.
- [ ] **8.4** `utxo.py` — the second spend must be refused **by the set**, not
      by a history scan. That is the whole double-spend defence.
- [ ] **8.5** `script.py` — P2PKH runs, and assert there is no jump opcode, so
      validation cost is bounded by script length.
- [ ] **8.6** `fork.py` — heaviest **work**, not most blocks. Build a case where
      the longer chain has less work; equal difficulty tests nothing.
- [ ] **8.7** `fork.py` *(Nakamoto 2008 §11)* — `(q/p)^k`, simulated against the closed
      form. Include `q > 0.5`, where the probability is 1 and the formula stops
      applying.
- [ ] **8.8** `fork.py` *(Eyal & Sirer, FC 2014)* — selfish mining, sweeping **gamma** (the share of
      honest miners that build on the attacker's released block). Assert the
      profitability threshold moves with it; a single-gamma check hides the
      result.
- [ ] **8.9** `accounts.py` — replay the same signed transaction twice with
      nonce checking off, then on. That is the exact price of dropping the UTXO
      set.
- [ ] **8.10** `evm.py` — an infinite loop must **terminate** out of gas, the
      sender must still be charged, and state must revert.
- [ ] **8.11** `trie.py` *(Wood, Ethereum Yellow Paper, App. D)* — inclusion proofs, and an **exclusion** proof for a
      key that is absent. The exclusion proof is what a plain Merkle tree
      cannot do and why the trie is a trie.
- [ ] **8.12** `pos.py` *(Buterin & Griffith, Casper FFG, 2017)* — hand-build conflicting finality and assert `slashable`
      names at least a third of the stake. Same shape as Raft's Figure 8: a
      safety checker that has never caught anything is not evidence.
- [ ] **8.13** Add to `progress.py`'s `PLAN`, cross-link from `raft/` and
      `dynamo-paper/`, and verify with `tools/verify_checks.py`.

---

## 9. AWS: three services, not thirty · ~22 h

**Mostly no — and the directory already argues why.** Its own "The rest of AWS"
table maps roughly twenty services onto the eight mechanisms already built:
Kinesis is `sqs.py` plus partitioning, Fargate is `lambda_svc.py` with a longer
container, Cognito is `iam.py` with a user directory, Secrets Manager is
`kms.py` with rotation. Adding a seventh variant of S3 would teach nothing and
would dilute a directory that currently sits at a verified 24/24.

Three mechanisms are genuinely absent. The README names the first two itself.

- [ ] **9.1 `cloudformation.py` — declarative desired state · ~8 h.** *(AWS CloudFormation docs on rollback and drift; the same mechanism as Terraform's plan/apply and Kubernetes' reconciliation loop)*
      A dependency graph with **rollback**, which nothing in the eight has.
      Topological ordering, partial failure, rollback to last-known-good, drift
      detection, and cycle detection. This is the mechanism under Terraform and
      Kubernetes too, so it pays out well beyond AWS.
      *Checks:* a cycle is refused rather than deadlocking; a mid-way failure
      leaves **no** partially-applied resources; drift is detected on a
      resource changed out of band; and a rollback that itself fails is
      reported rather than swallowed — that last one is where real deployments
      get stuck.
- [ ] **9.2 `kinesis.py` — an ordered log with replay · ~8 h.** *(Kreps, Narkhede & Rao, "Kafka: a Distributed Messaging System for Log Processing", NetDB 2011 — the same mechanism)*
      `sqs.py` deliberately has neither ordering nor replay, so this is a real
      contrast rather than a variant: per-shard ordering, a retention window,
      consumer checkpointing and iterators, and resharding. It is also Kafka.
      *Checks:* order holds **within** a shard and explicitly does not across
      shards; a consumer resuming from a checkpoint replays exactly the
      un-processed suffix; records expire out of the retention window even
      unread; and a reshard preserves per-key ordering across the split — the
      one everybody gets wrong.
- [ ] **9.3 `autoscaling.py` — a control loop · ~6 h.**
      The one the README's table misses. None of the eight has feedback
      control, and the failure modes are measurable and instructive:
      oscillation, and scaling on a **lagging** metric.
      *Checks:* the loop converges to the target under steady load; with too
      short a cooldown it **oscillates** (assert the amplitude, do not just
      assert it settles); scaling on queue depth beats scaling on CPU for a
      queue-driven workload; and scale-in on a lagging metric overshoots. Pair
      it with `optimize.py` so the cost of the overshoot is in dollars.

Then update `billing.py` to meter all three, and the README's "rest of AWS"
table to point the relevant rows at the new files.

**Explicitly not worth adding:** RDS/Aurora failover (it is `raft/` plus
replication lag), ElastiCache (`system-design/`), Route 53 (`dns-server/`),
CloudTrail (already written by `capstone.py`), Step Functions (a state machine
over `lambda_svc.py`), Organizations/SCPs (another deny layer in `iam.py`),
Glue/Athena (`database-engine/`'s planner over `s3.py`). Each is a packaging
difference, and the map in the README is the right place to say so.

---

## 10. AWS certification · ~35 h + daily drill · SKELETON IN PLACE

[`week-12/aws-certification/`](week-12/aws-certification/) — 7 files, 40 stubs,
10 checks named and unwritten.

**Do not plan on `aws-from-scratch/` clearing an exam by itself.** This repo is
deliberately anti-recall — its standard is re-deriving a decision and naming the
rejected alternative — and the exams are substantially recall: service names,
quotas, defaults, retrieval times. An arbitrary quota is not derivable.

Having done `aws-from-scratch/` you hold the harder half, and it is the half
that separates reasoning from cramming. It is not sufficient. The split is kept
visible on purpose: `check.py` grades the derivable half, `drill.py` carries the
arbitrary half and is **not** graded.

- [ ] **10.1** Write the ten checks. Two matter most: `check_elimination`
      (every distractor rejected by a **named** constraint) and
      `check_decision_is_not_a_lookup` (change one requirement, the answer
      changes at a boundary you can compute). A decision table that survives
      the second has memorised scenarios rather than rules.
- [ ] **10.2** `decide.py` — the elimination procedure. This is the shape of
      nearly every scenario question, and it is derivable given the eight
      mechanisms you already built.
- [ ] **10.3** `storage.py` — reuse the minimum-object-size and
      minimum-duration rules already checked in `pricing.py`. Include a
      lifecycle transition that **loses** money for small objects and one that
      loses it for short-lived ones — both are standard traps and both are
      arithmetic.
- [ ] **10.4** `storage.py` — EBS: assert IOPS binds for small blocks and
      throughput for large ones. A check that only tests IOPS passes a wrong
      answer on every sequential workload.
- [ ] **10.5** `network.py` — reachability over real route tables, including
      the **asymmetric-routing** case people answer from intuition. Then the
      six connectivity options, with the N where Transit Gateway overtakes a
      peering mesh computed rather than asserted.
- [ ] **10.6** `resilience.py` — RTO and standing cost order **opposite** ways
      across backup-restore / pilot light / warm standby / multi-site, and
      `pattern_for` returns the **cheapest that clears** the stated RPO/RTO.
      Returning the best pattern is the most common wrong answer.
- [ ] **10.7** `mlstack.py` — real-time, serverless, async and batch inference
      as four points on one curve, with the serverless-vs-provisioned crossover
      derived the same way as DynamoDB's in `optimize.py`. Map Feature Store
      onto `dynamodb.py`'s partition key and Pipelines onto the dependency
      graph from §9.1 — build that first if you want this to land.
- [ ] **10.8** `wellarchitected.py` — a review returning six green ticks is a
      review that was not done. Grade on reporting a **trade-off** and naming
      the pillar that fails first. This is the professional-level skill and the
      one your preparation is unusually good for.
- [ ] **10.9** `drill.py` — spaced repetition over quotas, defaults, names and
      limits. Keep it out of `check.py`; `check_drill_is_separate` enforces
      that as the directory grows. Run it **daily**, starting well before the
      exam date — this is the part that cannot be crammed in the last week and
      the part this repo's method does not help with.
- [ ] **10.10** Before any of the above, pull the **current official exam
      guides** and diff them against the check list here. Exam codes, blueprints
      and service names change, and everything above was written against a
      knowledge cutoff. Treat any conflict as the guide being right.
- [ ] **10.11** Order to sit them in: Solutions Architect Associate first (it
      shares the most with what you have built), then ML Engineer Associate,
      then Solutions Architect Professional. AI Practitioner is cheapest to
      clear and worth least — sit it only if someone is asking you for it.

---

## 11. Deploy it for real · ~20 h + a real account · SKELETON IN PLACE

[`week-12/aws-deploy/`](week-12/aws-deploy/) — 5 files, 42 stubs, 10 checks
named and unwritten, plus [`RUNBOOK.md`](week-12/aws-deploy/RUNBOOK.md) which is
deliberately **not** graded.

`aws-from-scratch` says of itself: *"Not API-compatible. No boto3 surface, no
XML, no signatures, no regions."* So after week 1 you can derive why a hot
partition key throttles an idle-looking table, and you cannot run
`aws dynamodb put-item`. The "200 services reduce to 8 mechanisms" argument
holds for understanding and for the exams, and does **not** hold for shipping.

### 11a — the offline half, graded

- [ ] **11.1** Write the ten checks first. `check_no_long_lived_keys` is worth
      more than the other nine together — it is the mistake that is both
      expensive and public.
- [ ] **11.2** `credentials.py` — resolution order (flags → env → profile →
      container role → instance role), role assumption, session expiry.
      `redact` must never return a full secret, including in an exception.
- [ ] **11.3** `policy.py` — granted-minus-needed. Include a policy that is
      **tight on actions and wide on `Resource`**; a check comparing only
      action lists passes that one, and that one is the real-world case.
- [ ] **11.4** `policy.py` — wildcards on writes, tolerated on explicit reads.
      Reuse week 1's evaluation rule: an explicit Deny still wins, so a wildcard
      Allow under a Deny boundary is not a finding.
- [ ] **11.5** `template.py` — dependency order including **implicit**
      references inside properties, not just `DependsOn`. Explicit-only is the
      version that passes tests and fails in production. Cycles must be
      reported, not silently edge-dropped.
- [ ] **11.6** `template.py` — inject a failure at each position in the apply
      order; the rollback must remove exactly what was created, no more and no
      less. Then assert no teardown orphans, **including retain-policy
      resources** — those are the ones that quietly keep billing.
- [ ] **11.7** `guard.py` — `bills_while_idle` names the per-hour resources
      (NAT gateway, unattached elastic IP, load balancer, provisioned IOPS, idle
      database) and not the per-request ones. Verify rates against the current
      price sheet; the numbers move, the categories do not.
- [ ] **11.8** `guard.py` — an alarm that fires monthly cannot catch a resource
      that bills hourly. Assert `alarm_before_spend` is False when the forecast
      crosses the limit faster than the alarm period can detect it.
- [ ] **11.9** `deploy.py` — fail at every transition and assert a safe terminal
      state each time, including the nasty one: health check passes, then fails
      after promotion. A pipeline never failed on purpose has not been tested.
- [ ] **11.10** `deploy.py` — the gate rejects a 200 serving the **wrong
      content**, and waits out a cold start rather than failing it.

### 11b — the real-account half, not graded

Follow [`RUNBOOK.md`](week-12/aws-deploy/RUNBOOK.md) in order. Phase 0 is marked
DO NOT SKIP because the two ways this goes badly — a leaked credential and a
forgotten hourly resource — are both cheap to prevent now.

- [ ] **11.11 Phase 0, before any other AWS work in this repo.** Root MFA then
      never touch root; a budget alarm on **forecast** as well as actual, tested
      by setting it to $0.01 and receiving the mail; IAM Identity Center rather
      than IAM users, so credentials are short-lived by default; `~/.aws/` in
      your global gitignore; a pre-commit secret scanner. **No long-lived access
      keys, ever.**
- [ ] **11.12 Phase 1** — CLI and boto3. `aws sts get-caller-identity` is the
      first thing to run whenever something is mysteriously denied. Read errors
      by `Error.Code`; the code is stable, the message is not.
- [ ] **11.13 Phase 1** — the read-only tour across the eight services from week
      1, comparing each real response shape to your toy version. This is the
      hour where week 1 pays off.
- [ ] **11.14 Phase 2** — S3 + CloudFront by CLI, broken on purpose (wrong
      content type, missing index document, a cache serving the old file), then
      deleted and rebuilt identically from IaC. Time both.
- [ ] **11.15 Phase 3** — Amplify: a build spec, a push-to-deploy branch, a
      **deliberately broken build** read from the log, a custom domain with an
      hour budgeted for DNS. Then enumerate what Amplify provisioned on your
      behalf and run its service role through 11.3.
- [ ] **11.16 Phase 4** — API Gateway → Lambda → DynamoDB and a Cognito
      authorizer, all from IaC, none from the console. **Do not add a NAT
      gateway** unless you have proved you need one; use a VPC endpoint, which
      is the crossover you already derived in `optimize.py`.
- [ ] **11.17 Phase 5** — deploy a bad version and roll back, for real, timed.
      Cause a DynamoDB throttle with a hot partition key and watch the alarm you
      set. Read the bill line by line; every line should be a resource you can
      name.
- [ ] **11.18 Phase 6 — the test.** Destroy everything, confirm zero new spend
      after 24 h, then **rebuild the whole stack from code in under an hour with
      no console clicks**, and tear it down again. Twice. That is the only
      claim here that cannot be faked, and it is what "I control this" means.
- [ ] **11.19** Standing rules afterwards: nothing exists that is not in code;
      check the bill weekly, not monthly; a credential on disk is an incident;
      tear down what you are not using, because the free tier expires twelve
      months in on a date you will not be watching for.

---

## 12. Defend it · ~6 h · PAID FOR BY A CUT

The goal this serves is **"defend myself solidly, and know exactly what to look
for"** — which is a better goal than expertise because it is achievable in
eighteen weeks, and it needs **less** new content rather than more. Everything
below is a rehearsal loop over knowledge the repo already produces.

**This one comes with an offsetting cut**, unlike sections 1–11. Take the six
hours out of `system-design` (48 h, week 17): `aws-from-scratch` covers much of
the same ground from the mechanisms up, and week 17 is already the heaviest and
most arbitrary week in the plan. Net change to the schedule: **−42 h.**

### 12a — the defence drill · ~3 h

**A worked instance already exists:**
[`week-09/database-engine/DRILL.md`](week-09/database-engine/DRILL.md), with
`drill_fixtures.py` generating a real SQLite file so the byte-level questions
have ground truth. Read it before writing `defend.py` — it is a better
specification of the format than the description below, and it adds two things
worth stealing: a **confidence level per answer** so the examiner can calibrate
you, and a fixed difficulty mix (60% mechanics, 30% failure modes, 10% "why did
the real engine do it this way and what did it cost them").

`week-12/aws-certification/defend.py`, beside `drill.py` and **also not graded
by `check.py`**. It is a third kind of practice, distinct from both:

| | grades | format |
|---|---|---|
| `check.py` | mechanisms you implemented | assertions |
| `drill.py` | arbitrary facts | spaced repetition |
| `defend.py` | **whether you can hold a claim under challenge** | answer in four beats, self-marked |

- [ ] **12.1** *(Roediger & Karpicke, "Test-Enhanced Learning", 2006 — retrieval beats review, which is why this is separate from `check.py`)* The card format is a claim plus a hostile challenge, answered in
      **four beats**: mechanism → the alternative you rejected → the limit case
      that complicates it → **the number that would change your mind**. The
      fourth beat is the one that makes a defence solid rather than confident,
      and it is the one nobody practises. A card answered in three beats counts
      as dodged.
- [ ] **12.2** Track dodges, not scores. The output is a list of claims you
      could not defend, which is the only useful signal — a percentage is not.
- [ ] **12.3** Seed it from the repo rather than inventing content: every
      `DESIGN DECISION` block already has the shape (decision + rejected
      alternative), so the work is writing the *challenge*, not the answer.
      Start with `iam.py`, `dynamodb.py`, `optimize.py`, `raft/replication.py`
      and `context-caching/kv_cache.py`.
- [ ] **12.4** Worked example to build the format against:
      *Claim:* put the tenant ID in the partition key.
      *Challenge:* forty tenants and one is 60% of traffic.
      *Four beats:* partition throughput is per-partition not per-table → a
      random suffix would kill the query pattern → write-sharding on a composite
      key, paid for with a scatter-gather read → **it changes when that tenant
      exceeds a single partition's write capacity.**
- [ ] **12.5** Run it weekly, on the directories finished so far. It belongs on
      Sunday's regression day, which currently has no verbal component at all.

### 12b — the discriminating command · ~2 h

One `LOOKUP.md` per major directory, ~20 lines each. Not prose — a table of
**symptom → the single command or page that tells you which branch you are in.**
This is literally what "know what to look for" means.

- [ ] **12.6** Write the AWS one first. Starting rows, each of which has cost
      somebody a day:

      | Symptom | The one thing to check |
      |---|---|
      | Access denied, cause unknown | `aws sts get-caller-identity` — half of all AWS mysteries are *you are not who you think you are* |
      | Denied, and you **are** the right principal | policy simulator, then the SCP — an explicit Deny anywhere wins |
      | Table throttling while metrics look idle | Contributor Insights on the partition key; table-level metrics average the hot partition away |
      | Deploy green, site 403 | origin or distribution? `curl` the S3 object directly |
      | Bill jumped, nothing changed | Cost Explorer grouped by **usage type**, not by service |
      | Lambda slow only sometimes | cold starts vs downstream — check init duration separately from duration |
      | It worked yesterday | CloudTrail, filtered to write events by a principal that is not you |

- [ ] **12.7** Then one each for `inference-from-scratch`, `database-engine`,
      `raft` and `context-caching`. Same format: symptom, the discriminating
      check, and what each branch means.
- [ ] **12.8** Rank the SOURCES too, because "read the docs" is not an answer
      and the ranking is the skill: the service **FAQ** answers *"what happens
      when…"* better than the user guide; the **API reference** carries the
      error codes, which are stable when messages are not; **`describe-*`
      against your own account** beats any documentation for ground truth;
      **Service Quotas** answers *"is this a limit or a bug"*; the **price list
      API** beats the pricing page.

### 12c — the cut that pays for it · ~1 h

- [ ] **12.9** Remove `system-design` from the schedule and move it to
      [`reference/`](reference/) with a row in that README explaining the
      overlap with `aws-from-scratch`. Update `PLAN`, week 17's README, the
      ROADMAP table and the root index. Week 17 drops from 144 h to 96 h and
      stops being the outlier.
- [ ] **12.10** Re-run `python3 progress.py --rebaseline` and confirm the full
      track lands near 70 h/week.

---

## 13. Debug it · one catalogue per project

Every exercise in this repo is *"build this correctly"*. The actual job is
*"someone built it wrong and you do not know where"*, and only
[`week-04/deploy-and-debug/`](week-04/deploy-and-debug/) practises it.
[`tools/bugs/`](tools/bugs/) generalises that, and doubles as the half of
checker verification (§1) that actually finds problems.

**The rule: every check gets at least one bug proving it bites.** A check with
no bug against it has never been shown to detect anything.

### The harness · ~4 h

- [ ] **13.1** `tools/breakit.py`, sharing `stage()` and `apply_injection()`
      with [`tools/verify_checks.py`](tools/verify_checks.py) — §1 builds those
      anyway, so this is mostly wiring.

      ```
      python3 tools/breakit.py week-01/aws-from-scratch
        -> a broken tree and ONE symptom. Which bug is not disclosed.
      python3 tools/breakit.py --reveal    # only after you commit to an answer
      ```
- [ ] **13.2** **Score by observations**, not time or success. Someone who
      binary-searches beats someone who reads every file, and time measures
      neither.
- [ ] **13.3** **Symptom only** — never the traceback, never the failing check
      name. The name gives away the file and collapses the exercise.
- [ ] **13.4** Weight selection toward bugs that **do not crash**. *(the same argument as mutation testing: DeMillo, Lipton & Sayward, IEEE Computer 1978)* Uniform
      hemisphere sampling still renders; semi-naive over a non-idempotent
      semiring still terminates and undercounts; a missing `/2` in a VAE still
      trains. Plausible results are the hardest to find and the only kind worth
      drilling.
- [ ] **13.5** Put it on **Sunday's regression day**, which currently says
      "re-run every checker" and nothing else. One bug a week, in a directory
      finished at least a fortnight ago, is also a memory test.
- [ ] **13.6** Log the ones you failed to find. Same principle as §12.2 — the
      list of what you could not diagnose is the signal, a success rate is not.

### Per project

`existing` counts what is already in `tools/bugs/`. Directories with
`solutions/` can be written today; check-only ones need a reference from §1
first; skeletons need their checks written before there is anything to prove.

**AWS is done.** It was the biggest gap: 24 checks with bugs against only 6 of
them. Writing the other 18 found **four checks that could not detect the very
thing they existed to test** — see the note under the table.

| | Directory | Checks | Existing | Write | Blocked on |
|---|---|---|---|---|---|
| ~~13.7~~ | `week-01/aws-from-scratch` | 24 | **54** | 0 | **DONE** — 54/54 caught, all 24 checks proven |
| 13.8 | `week-02/llm-from-scratch` | 15 | 14 | 1 | nothing |
| 13.9 | `week-03/context-caching` | 16 | 0 | 16 | nothing |
| 13.10 | `week-04/deploy-and-debug` | 12 | 0 | 12 | nothing |
| 13.11 | `week-05/contextcite` | 14 | 0 | 14 | nothing |
| 13.12 | `week-10/dynamo-paper` | 17 | 0 | 17 | nothing |
| 13.13 | `week-15/compiler-and-vgpu` | 12 | 0 | 12 | nothing |
| 13.14 | `week-04/inference-from-scratch` | 12 | 0 | 12 | §1.5 reference |
| 13.15 | `week-06/provenance-semirings` | 8 | 0 | 8 | §1.5 reference |
| 13.16 | `week-07/scasp` | 8 | 0 | 8 | §1.5 reference |
| 13.17 | `week-08/linc` | 8 | 0 | 8 | §1.5 reference |
| 13.18 | `week-05/spade` | 8 | 0 | 8 | §1.5 reference |
| 13.19 | `week-05/mars-sql` | 8 | 0 | 8 | §1.5 reference |
| 13.20 | `week-03/rl-posttraining` | 9 | 0 | 9 | §4.1 checks |
| 13.21 | `week-11/blockchain-from-scratch` | 11 | 0 | 11 | §8.1 checks |
| 13.22 | `week-12/aws-certification` | 10 | 0 | 10 | §10.1 checks |
| 13.23 | `week-12/aws-deploy` | 10 | 0 | 10 | §11.1 checks |
| — | `week-02/autograd` | 10 | 18 | 0 | **covered** |
| — | `week-09/database-engine` | 18 | 20 | 0 | **covered** |
| — | `week-10/raft` | 7 | 12 | 0 | **covered** |
| — | `week-17/ray-tracer` | 6 | 16 | 0 | **covered** |

**What writing the AWS catalogue actually found.** Four checks passed against a
deliberately broken implementation and had to be strengthened:

- **check 4** verified a multipart ETag ended in `-N` but never that the digest
  half was the MD5 of the *concatenated part digests*. Hashing the whole body
  and appending the suffix passed.
- **check 11** proved a reservation was a *floor* (others lost capacity) but
  never a *ceiling* — a function that ignored its own reservation passed. It
  also never tested that a timed-out invocation is billed for the full timeout.
- **check 12** asserted `matches_filter` worked in isolation but every
  subscriber in the delivery test had no filter policy, so a topic that ignored
  filter policies entirely passed.
- **check 2** exercised conditions and boundaries without ever testing that
  resource matching is case-SENSITIVE, or that a `Bool` condition parses the
  policy string rather than coercing it. Both bugs fail **open**, and both were
  found by a real attempt at the exercise rather than by the checker.
- **check 18** ran the capstone end to end without ever checking that the stored
  object was *encrypted*, or that a failed message *survived* to be redelivered.

That is the argument for this whole section in one paragraph: a checker nobody
has tried to fool is a checker nobody has tested.

- [ ] **13.24** The remaining directories have **no `check.py` at all** —
      `bash-from-scratch`, `http-server`, `dns-server`, `cryptographic-library`,
      `communication-protocols`, `toralizer`, `firewall-from-scratch`,
      `c-compiler`, `quantum-computing-lang`, `cuda-from-scratch`,
      `haskell-projects`, `distributed-training`, and the week-18 tail. Writing a
      checker for those is a larger job than this section and is not scheduled.
      When you do write one, **write the bug at the same time** — that is the
      moment you know what the check is defending against, and it never comes
      back.

**Do not read `tools/bugs/` while learning.** It is the answer key.

---

## 14. Databases, deeper · ~72 h · PARTLY PAID FOR BY A CUT

Two additions to [`week-09/database-engine/`](week-09/database-engine/) (50 h →
77 h) and one new directory,
[`week-17/database-internals/`](week-17/database-internals/) (45 h), which
displaces `system-design` into `reference/`. Net **+24 h**; the full track moves
73 → 75 h/week and `core` 44 → 48.

### 14a — LSM trees · ~15 h · `week-09/database-engine/lsm.py`

*(O'Neil et al., Acta Informatica 1996; Athanassoulis et al., RUM conjecture,
EDBT 2016; Dayan et al., Monkey, SIGMOD 2017)*

- [ ] **14.1** Memtable, immutable SSTables with a sparse index, tombstones,
      and the read path memtable → L0 → Ln in age order.
- [ ] **14.2** Bloom filters. Measure what they save by counting **file opens
      on ABSENT keys** — that is where the saving is, and a check that only
      looks up present keys will show nothing.
- [ ] **14.3** Both compaction policies: **leveled** (one run per level, high
      write amplification, low read) and **tiered** (several runs, the reverse).
      RocksDB is the first, Cassandra the second, and neither is a bug.
- [ ] **14.4** Measure **all three amplifications** — read, write, space. The
      RUM conjecture says you get two; the deliverable is seeing which corner
      each policy stands in, not being told.
- [ ] **14.5** Head-to-head against `btree.py` on a write-heavy and a read-heavy
      workload. **If one structure wins both, the workload is not exercising
      the difference** — that is the check to write first.

### 14b — a DATA step engine · ~12 h · `week-09/database-engine/datastep.py`

*(SAS Language Reference — no paper; the manual is the specification. Wickham,
"Split-Apply-Combine", JSS 2011, for the declarative comparison.)*

- [ ] **14.6** The PDV, and the implicit loop that runs the whole step once per
      input row and writes out at the bottom unless told otherwise.
- [ ] **14.7** `RETAIN` — a variable that survives the iteration. This is how a
      running total exists without a window function.
- [ ] **14.8** BY-groups with `first.`/`last.` flags. **Requires sorted input,
      and unsorted input silently produces wrong groups rather than an error** —
      the most common DATA step bug, and the check must assert it is detected.
- [ ] **14.9** `MERGE`, and then say which SQL join it actually equals. On a
      many-to-many match its behaviour is a documented surprise; reproduce it.
- [ ] **14.10** `OUTPUT`/`DELETE`, so one input row can produce zero rows or
      ten. This is the real answer to why the model survived.
- [ ] **14.11** The comparison table: five transformations, both ways, with
      which is shorter and which is clearer as separate columns. The interesting
      rows are the two SQL cannot express cleanly — a running total that resets
      on a condition, and a variable number of output rows per input row.
- [ ] **14.12** Cross-link to [`week-18/sas-lineage-tool/`](week-18/sas-lineage-tool/), which
      *parses* these rather than running them, and reads much better once you
      have built one.

### 14c — `week-17/database-internals/` · ~45 h · SKELETON IN PLACE

6 files, 36 stubs, 11 checks named and unwritten. Needs week 9 finished — every
measurement here is *against* its Volcano executor and cost planner.

- [ ] **14.13** `estimation.py` **first, and before anything else in the
      directory.** *(Leis et al., VLDB 2015.)* Reproduce the result: estimation
      error compounds multiplicatively with join count, so a 4-way join is off
      by orders of magnitude and the planner then picks a bad plan **correctly**.
      Assert the error factor **grows** with join count rather than staying flat,
      on **correlated** data — independent columns prove nothing.
- [ ] **14.14** `estimation.py` — feed the planner true cardinalities, then
      estimated ones, and assert the chosen plan **differs** and is measurably
      slower. Attribute the loss to the estimate, not the model. That
      attribution is the whole point.
- [ ] **14.15** `sketches.py` *(Flajolet et al. 2007; Cormode & Muthukrishnan
      2005)* — HyperLogLog within its theoretical bound including the small
      range where the naive formula is worst; and Count-Min's **one-sided**
      guarantee: every estimate ≥ true frequency, never below.
- [ ] **14.16** `columnar.py` *(Stonebraker et al. 2005; Abadi et al. 2006)* —
      RLE, dictionary and frame-of-reference each winning on the shape they are
      for, and the same data by row compressing measurably worse. Then late
      materialization, and **find the selectivity where its advantage reverses**.
- [ ] **14.17** `vectorized.py` *(Boncz et al., CIDR 2005)* — sweep batch size
      1/8/64/1024/8192 against your own Volcano executor. Overhead per tuple must
      fall sharply and then **flatten**; a monotonic curve means you are not
      measuring what made X100 fast. Then read Neumann (VLDB 2011) for the other
      answer — compile rather than interpret.
- [ ] **14.18** `joins.py` — Grace hash join when the build side does not fit,
      with I/O matching 3(|R|+|S|). Then **skew**, which breaks it, because one
      partition is still too big.
- [ ] **14.19** `concurrency.py` *(Kung & Robinson, TODS 1981; Cahill et al.,
      SIGMOD 2008)* — sweep the conflict rate across 2PL, OCC and MVCC. Assert
      OCC beats 2PL at low contention and **loses** at high, and name the
      crossover. A check at one contention level proves nothing.
- [ ] **14.20** `concurrency.py` — a genuine wait-for cycle detected, exactly
      one victim aborted, and a non-cyclic wait chain **not** reported. A
      detector that aborts on any wait has removed 2PL's only advantage.

### 14d — the cut

- [ ] **14.21** `system-design` (48 h) is already moved to
      [`reference/`](reference/). Its patterns are covered from the mechanisms up
      by `aws-from-scratch` (caching, queues, rate limiting, consistent hashing)
      and `deploy-and-debug` (circuit breakers, bulkheads, backpressure), and
      Kleppmann covers the rest better than 159 stubs will. Confirm you agree,
      or move it back and take the 45 h out of week 17 some other way.

**Every check in 14c is a crossover or a curve, not a single measurement.** At
one contention level, one selectivity or one batch size, each of these looks
either obviously right or obviously pointless. The content is entirely in where
they change places.

---

## 15. Performance engineering, the analytical half · ~38 h

From Chris Fregly's [AI Systems Performance Engineering](https://github.com/cfregly/ai-performance-engineering)
(O'Reilly, 20 chapters). Six new files across three existing directories.

**What was taken and what was not.** The book is GPU-hardware-specific: Nsight
counters, tensor cores, NVLink topology, power and thermal, PyTorch/Triton/XLA
backends. None of that can be faked in pure Python, and a simulated profiler
counter teaches a number rather than a skill. What lifts cleanly is the
**arithmetic** — the models you compute *before* writing a kernel and check the
profiler against *afterwards*. That is six files; the other fourteen chapters
want a GPU in front of you and `REFERENCES.md` says so.

### 15a — `week-16/cuda-from-scratch/`, 4 files + `check_perf.py` · ~20 h

- [ ] **15.1** Write the eight checks in `check_perf.py`. Four of them
      deliberately test the **reversal**, not the rule — see below.
- [ ] **15.2** `roofline.py` *(ch. 9; Williams, Waterman & Patterson, CACM
      2009)* — FLOPs, bytes moved, intensity, ridge point. Assert SAXPY is
      memory-bound and a large matmul compute-bound on the **same** hardware
      parameters, and that intensity **grows with tile size** — that growth is
      the whole reason tiling works and a single-size check cannot see it.
- [ ] **15.3** `roofline.py` — `speedup_ceiling` must return 1.0 for a kernel
      already at the roof. Optimising one that is already there is the week of
      work that produces nothing, and this is the check that prevents it.
- [ ] **15.4** `occupancy.py` *(ch. 6, 8)* — registers, shared memory and block
      size each capping warps per SM. Build three cases each limited by a
      **different** resource; a calculator that only checks registers is right
      two thirds of the time and useless.
- [ ] **15.5** `occupancy.py` — **the reversal.** Construct a case where using
      MORE registers per thread lowers occupancy and raises throughput, because
      ILP hides the latency with fewer warps *(Volkov & Demmel, SC 2008)*. A
      check that only rewards occupancy has taught the wrong lesson.
- [ ] **15.6** `coalescing.py` *(ch. 7)* — transactions per warp instruction.
      Contiguous aligned = minimum; stride 32 = one per lane; **misaligned but
      contiguous costs one extra, not double** — the case people over-estimate.
- [ ] **15.7** `coalescing.py` — AoS vs SoA, and assert the advantage
      **reverses** when the kernel reads every field rather than one. Both
      directions, or the check is an opinion.
- [ ] **15.8** `coalescing.py` — 32 banks: stride 1 conflict-free, stride 32 a
      32-way conflict, padding by one element fixes it, and **broadcast (every
      lane, same address) is NOT a conflict** — the exception people get wrong.
- [ ] **15.9** `pipelining.py` *(ch. 10, 11)* — overlap turns a sum into a max,
      then stops. `optimal_chunks` must return the point past which nothing
      improves, not "more is better".
- [ ] **15.10** **Then use them.** For every kernel you write in week 16,
      compute intensity, occupancy and transaction count first, write the
      prediction down, then profile. Where they disagree, one of the two is
      wrong and finding out which is the exercise.

### 15b — `week-04/inference-from-scratch/disaggregate.py` · ~10 h

*(ch. 17–18; Zhong et al., DistServe, OSDI 2024; Patel et al., Splitwise, ISCA 2024)*

- [ ] **15.11** Prefill is compute-bound and decode is memory-bandwidth-bound.
      Model both, and the interference when they share a replica — a long
      prefill stalls every streaming user, which is why TTFT and inter-token
      latency move in opposite directions under batch tuning.
- [ ] **15.12** `kv_transfer_cost` — compute the bytes **exactly**:
      `2 x layers x heads x head_dim x tokens x dtype_size`. Guessing this is
      how people conclude disaggregation is free.
- [ ] **15.13** The check is a **crossover**: at what prompt length, batch size
      and interconnect bandwidth does the KV hop cost less than the
      interference it removes? Compare against a colocated baseline that is
      genuinely **under mixed load** — comparing against an idle one is the
      standard way this result gets overstated.
- [ ] **15.14** `pool_ratio` — prefill replicas per decode replica. That these
      two numbers should differ, and cannot be tuned separately while the phases
      share a machine, is the actual argument for disaggregating.

### 15c — `week-08/distributed-training/collectives.py` · ~8 h

*(ch. 4; Thakur, Rabenseifner & Gropp, IJHPCA 2005; Patarasuk & Yuan)*

- [ ] **15.15** `alpha x hops + beta x bytes` for ring and tree all-reduce.
      Ring is bandwidth-optimal with latency linear in `p`; tree is
      latency-optimal and moves more bytes.
- [ ] **15.16** Compute `crossover_message_size`, then compare against what
      NCCL actually picks. The gap is either hardware you have not modelled or
      a bug in your model — both worth finding.
- [ ] **15.17** `overlap_with_backward` — bucketing gradients so layer *n*
      all-reduces while layer *n−1* still computes. The **largest single win in
      data-parallel training, and it is a scheduling change: the bytes are
      identical.** Find the bucket size where the overlap saturates.

---

## 16. Ready for an AI-ops role · the `ops` track + ~150 h of evidence

**The uncomfortable premise: you cannot get there by building more
from-scratch directories.** Past a point, more mechanism has diminishing
returns and the binding constraint becomes **evidence** — something a hiring
manager can look at, and something you have actually operated.

This repo is the *understanding* half, and it is the half most candidates lack.
The other half is integration work: tools, a running system, and artifacts. It
is smaller than it looks (~150 h) and it is a different kind of work — nothing
in it can be graded by a `check.py`, which is exactly why it gets skipped.

### 16a — the track · 694 h · ALREADY IN `progress.py`

`python3 progress.py --track ops` — 15 directories, **39 h/week over 18, 27
over 26.** It is `full` minus everything that does not serve the goal.

| Kept | Why |
|---|---|
| `aws-from-scratch`, `aws-certification`, `aws-deploy` | the platform, the exam, and the real account |
| `autograd`, `llm-from-scratch`, `rl-posttraining` | you cannot operate a model you cannot describe |
| `context-caching`, `inference-from-scratch`, `deploy-and-debug` | **the centre of the job** |
| `cuda-from-scratch` | the only way to read a profiler and mean it |
| `database-engine`, `dynamo-paper`, `raft` | every platform is a distributed system with state |
| `http-server`, `distributed-training` | the substrate, and multi-node |

**Dropped for this goal:** `blockchain-from-scratch`, `provenance-semirings`,
`scasp`, `linc`, `spade`, `mars-sql`, `contextcite`, `database-internals`,
`ray-tracer`, `haskell-projects`, `c-compiler`, `compiler-and-vgpu`,
`lean-proofs` and the week-14/18 tails. **708 hours.** Several are excellent and
none of them will come up in the interview.

### 16b — tool fluency · ~40 h · phases 6–8 of the runbook

Already added to [`RUNBOOK.md`](week-12/aws-deploy/RUNBOOK.md). Not new
mechanisms — packaging things you already understand, which is the right order.

- [ ] **16.1** Phase 6 — containerise `inference-from-scratch`. Multi-stage,
      non-root, pinned digest, and **measure the cost of the container** by
      running your own week-4 benchmark inside and outside it.
- [ ] **16.2** Phase 7 — local Kubernetes. Get **liveness vs readiness** wrong
      on purpose and watch a healthy app crash-loop; OOMKill a pod by setting a
      limit too low; kill a pod under load and measure what the client lost.
- [ ] **16.3** Phase 8 — deploy **vLLM** for real. Predict what
      `gpu_memory_utilization`, `max_num_seqs` and `max_model_len` do before
      changing them; you have the model for all three.
- [ ] **16.4** Terraform, not just CDK. It is what the job postings say, and
      `template.py`'s dependency-graph checks apply to it unchanged.
- [ ] **16.5** GitHub Actions: test → build image → push → deploy → smoke test,
      with the health gate from `deploy.py` as the promotion condition.
- [ ] **16.6** Prometheus + Grafana, scraping **your** `observe.py` metrics and
      vLLM's. Build the dashboard rather than importing one.

### 16c — the evidence · ~110 h · **STARTS WEEK 1**, see [`LIVE.md`](LIVE.md)

None of this is gradeable. All of it is what gets read.

**This was originally scheduled at week 12 and that was wrong.** Starting the
live system at week 12 puts ninety days of uptime at 7 Feb 2027 — after the
18-week plan ends and at the wire for 26. Starting week 1 puts it at 22 Nov,
with a month spare and room for a second incident. Nothing else in this file
has a deadline set by the calendar rather than by effort.

- [ ] **16.7 One system that stays up — deploy it in WEEK 1.** A public URL and
      a health endpoint before you have a model at all; your own week-2
      transformer replaces the placeholder in week 3. For **at least 90 days**. Not a demo — a thing with uptime. Cheapest
      honest version: a small model on one always-on instance, or serverless
      with a cold-start budget you have measured and stated.
- [ ] **16.8 A load test with a number attached.** Requests/sec at a stated p99,
      the knee, and *what saturated first*. From `traffic.py`, against your own
      stack and against vLLM. **The comparison is the artifact.**
- [ ] **16.9 A real incident, and a written postmortem.** Something broke, you
      found it, here is the timeline and the fix and what you changed so it
      cannot recur. If nothing breaks in 90 days, **break it deliberately** —
      OOM it, exhaust the KV cache, saturate the queue — and write that up.
- [ ] **16.10 A cost record.** What it costs per month, per request, and the one
      change that halved it. You will have the only rigorous cost model of any
      candidate; `optimize.py`'s crossovers are the thing to point at.
- [ ] **16.11 The scheduler comparison**, owed since week 4: your design
      decisions against vLLM's, with numbers and with the places you were wrong.
      Being able to say "I chose X, they chose Y, and here is why theirs is
      better" is worth more than either implementation.
- [ ] **16.12 The journal, edited.** 26 weeks of daily entries is not an
      artifact; **ten posts pulled out of it are.** Pick the ten where you were
      surprised — the fail-open IAM bugs, the estimation-error compounding, the
      1/√N bill, the checks that could not catch what they existed to catch.
- [ ] **16.13 `defend.py`, run against yourself weekly** (§12). The interview is
      a hostile-challenge format and you will have practised it. Most candidates
      have not.

### 16d — the honest scoreboard

- [ ] **16.14** Take three real AI-ops job postings and mark every requirement
      **have / partial / none** against what you actually hold. Redo it monthly.
      Where "none" appears twice in a row, that is the next 20 hours — not the
      next directory.

**What you will be unusually good at:** cost, capacity arithmetic, reasoning
about a serving stack you built, and defending a decision under challenge.
**What you will still be behind on:** years of on-call, other people's
codebases, and the ten tools nobody puts in a curriculum. The first set is
harder to acquire and rarer. Lead with it.

---

## Last: the decision that is not a task

The full track reads **41 directories, 1,799 h, 100 h/week**, up from 87 two
commits ago, with weeks 14–18 holding 900 h between them. The twelve-week,
ten-project cut discussed on 23 Aug was never applied.

Every step above adds roughly **182 hours** (≈40 for 1–6, 55 for the blockchain,
22 for the three AWS services, 35 for the certification layer, 20 for the deploy
layer, 6 for the defence loop) plus a daily drill and a real AWS bill.

**Section 12 is the only one that removes anything** (§13 adds 4 h but needs no new content — the 93 bugs are already written)**,** and — it cuts `system-design`,
48 h, for a net −42. Every other section adds and removes nothing. That
asymmetry is the whole problem with this file.

The schedule itself now reads 39 directories, 1,320 h, 73 h/week after moving
599 h to `reference/`. These steps put roughly a quarter of that back. Nothing in this file fixes the number,
and nothing should until you decide what the plan actually is.
