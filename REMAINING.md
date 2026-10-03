# What remains to do

State as of the pull on **23 Aug 2026** (`9d9fb8c`), written before the plan
starts tomorrow. Ordered by what blocks what, not by size.

---

## 0. The number to look at first

```
41 directories · 1,799 h · 100 h/week on the full track
```

That is up from 87 h/week two commits ago, and it is the third time the plan
has grown after a scoping conversation. The 12-week / ten-project cut discussed
on 23 Aug was not applied — everything cut is still in `PLAN`, in weeks 14–18,
which now hold **900 h between them** (half the plan in a third of the weeks).

Nothing below fixes this. It is a decision, not a task, and it is yours.
Recorded here so it is not quietly true.

---

## 1. BLOCKING — none of the new checkers has been verified

Seven directories were added as check-only. This is the right call and it
answers an objection I raised: shipping `solutions/` alongside a template turns
"from scratch" into transcription. But it leaves the repo's own verification
discipline unsatisfied, and that discipline is the thing that has caught every
real bug in this repo so far.

A checker has to be verified **two ways**:

1. it passes 100% against a working reference implementation, and
2. it is shown to **catch** deliberately injected characteristic bugs.

Neither has been done for any of the seven. Right now we do not know whether
these checks are passable at all.

| Directory | Files | Stubs | Checks | Verified |
|---|---|---|---|---|
| `week-02/llm-from-scratch/distill.py` | 1 | 12 | 7 | no |
| `week-06/provenance-semirings/` | 6 | 76 | 8 | no |
| `week-07/scasp/` | 6 | 22 | 8 | no |
| `week-08/linc/` | 7 | 22 | 8 | no |
| `week-05/spade/` | 5 | 19 | 8 | no |
| `week-05/mars-sql/` | 4 | 15 | 8 | no |
| `week-04/inference-from-scratch/` | 12 | 41 | 12 | no |
| | | **207** | **59** | |

**Why this is blocking and not pedantry.** An impossible check is worse than no
check. You will spend a day assuming you are wrong, because the whole method of
this repo is "trust the checker over your own reading". One bad assertion
converts that from an asset into a trap, and it will happen on the day you are
least able to tell.

**The fix that keeps the no-solutions rule.** Write references in a scratch
directory outside the repo, run the checker against them until 59/59, inject
one characteristic bug per check and confirm each is caught, then delete the
references. Verified checks, nothing shipped. Roughly a day's work for all
seven; it was the outstanding item when the Cursor pass landed.

Order to do it in: `provenance-semirings` (76 stubs, the most exposed), then
`inference-from-scratch` (12 checks), then the rest.

## 1b. One check grades recall rather than a mechanism

`week-02/llm-from-scratch/check.py` step 14 — *"MiniLM, GKD, SDPO, OPSD — the
decisions"* — grades `paper_choices()`, a dict of strings. It tests whether you
remember what a paper said. Every other check in this repo tests whether a
mechanism you built behaves correctly, and that difference is most of why the
checkers are worth anything.

Each of those four has a mechanism that is exactly checkable in pure Python:

- **MiniLM** — attention distributions and value-relation matrices are `L x L`,
  so a width-8 teacher and a width-4 student produce comparable targets with no
  layer mapping and no learned projection. Check it with mismatched widths;
  that property *is* the paper.
- **GKD** — the generalised JSD family with `m = β·teacher + (1−β)·student`.
  Check the two limits numerically: `D/β → KL(t‖s)` as `β→0`, and
  `D/(1−β) → KL(s‖t)` as `β→1`. One knob, both directions, finite in between.
- **OPSD** — with teacher identical to student the gradient is **exactly zero**,
  in both directions. A loss that drifts there still trains and still prints a
  falling curve. Also: EMA the *logits*, not the probabilities — averaging
  probabilities drifts the teacher toward uniform, silently.
- **SDPO** — several distinct methods use that name (stepwise, segment-level,
  self-play, score-based). Rather than assert one, check the identity all of
  them are built on: `π*(y|x) ∝ π_ref(y|x)·exp(r/β)`, invertible to
  `r = β·log(π*/π_ref) + β·log Z`, with the per-prompt constant cancelling in a
  pairwise margin. Round-trip it and the DPO derivation is verified.

## 1c. Gaps in `distill.py` worth closing while you are there

Present coverage hits all seven of your topics. Three mechanisms are named in
the docstrings but not reachable by any check:

- **the gradients themselves** — `∂KL(t‖s)/∂z = s − t` (forward) versus
  `s·(log(s/t) − KL(s‖t))` (reverse). The leading `s` in the reverse form is
  *why* mode collapse happens; it is one line and it is the explanation.
- **the mass-covering / mode-seeking picture, measured** — fit a deliberately
  unimodal student to a bimodal teacher by each divergence. Forward lands in
  the valley between the modes; reverse commits to one. They only differ when
  the student cannot match the teacher, which is always.
- **the privilege floor as a closed form** — the best blind student is the
  marginal `E_z[p(y|x,z)]` and its loss is exactly `I(y;z|x)`. Sweep student
  capacity and watch the loss stop at that wall. That number is the illusion
  quantified, and it is computable *before* training anything.

Draft templates for all three, plus MiniLM/GKD/OPSD/DPO, are in the scratchpad
at `.../scratchpad/superseded/llm/` — `distill.py`, `policy.py`,
`privilege.py`, `methods.py` (46 stubs, docstrings written, no solutions). Merge
or discard; they are not in the repo.

---

## 2. RL post-training is built but not connected

`origin/claude/rl-posttraining-llm-exercises-wzfe8w` contains
`rl-posttraining-llm/` — eight phases, shared `common/` machinery (GRPO,
rewards, a tiny SQL env), tests, and solutions. It is **not merged, not in a
week folder, not in `progress.py`'s `PLAN`, and not in `ROADMAP.md`.**

It is also the closest thing in the repo to the reading list you are publishing
against tomorrow, and it lands directly next to `mars-sql/` — which is the same
application (text-to-SQL, multi-turn, schema discovery) approached from the
inference side rather than the training side.

**Decide first:** merge it as-is, or rebuild it check-only to match the seven
new directories. Merging keeps 8 phases of work; rebuilding keeps the repo
consistent and keeps you from reading answers. I would merge `common/` and the
phase structure, and strip `solutions/`.

### What the reading list makes checkable

Your synthesis draws on Sutton & Barto, Spinning Up, the RLHF Book, Schulman's
notes, Weng's policy-gradient post, YugeTen, Dr. GRPO, async GRPO, and TRL /
OpenInstruct. Stripped of branding, that reduces to a handful of mechanisms,
every one of which is exactly measurable in pure Python — no model, no GPU:

- **The policy-gradient identity.** `∇E[R] = E[R·∇log π]`. Verify against a
  finite-difference gradient on a small categorical policy. This is the one
  everything else is a variance-reduction argument about.
- **Baselines reduce variance without introducing bias.** Measure both: mean
  of the estimator unchanged, variance down. Then show a *state-dependent*
  baseline is still unbiased and a *reward-dependent* one is not.
- **Schulman's three KL estimators.** `k1 = −log r`, `k2 = ½(log r)²`,
  `k3 = r − 1 − log r`. Measure: k1 is unbiased but high variance and goes
  negative; k2 is low variance and biased; **k3 is unbiased AND non-negative**,
  which is why it is the one in every modern implementation. A three-line
  measurement that settles an argument people have repeatedly.
- **TRPO → PPO.** The clip is one-sided per sample — it stops the ratio moving
  further in the direction that already helped, and does nothing in the other.
  Measure the fraction of samples clipped as the policy drifts.
- **GRPO.** Group-relative advantage replaces the value network. Check that the
  group baseline is the group mean and that no critic is needed. Then
  **Dr. GRPO**: dividing by the group's std and by response length introduces a
  length bias — measure the bias, remove the terms, measure it gone.
- **Async / off-policy staleness.** The importance ratio drifts as the
  generation lags the update. Sweep lag against ratio variance and find where
  the estimator stops being usable — that is the actual constraint on async
  GRPO throughput.
- **Reward hacking and the KL budget.** With a deliberately gameable reward,
  measure proxy reward rising while true reward falls, and how the KL
  coefficient trades them. This is the same axis as forward-vs-reverse KL in
  `distill.py`, reached from the other side.
- **DPO as the shortcut.** The identity in §1b, verified. Then: what DPO gives
  up relative to on-policy PPO, measured on a case where the preference data is
  off-policy.

That is ~8 checks and one directory. It also completes a line the repo already
half-draws: `autograd` → `llm-from-scratch` → `distill` (a teacher supervises
every token) → `rl` (a scalar supervises the episode) → `inference`. The
supervision-density table in `distill.py` already names the comparison; this
would make it runnable.

---

## 3. Smaller, still open

- **`provenance-reasoning/` (mine) is superseded but not merged.** Five
  templates *and* five working solutions with running demos, in
  `.../scratchpad/superseded/provenance-reasoning/`. It overlaps
  `week-06/provenance-semirings/` and `week-08/linc/`. Worth mining for two
  things the shipped version does not have: the **homomorphism/universality
  check** (evaluate a query once in `N[X]`, derive nine semantics by mapping the
  answer — the property that makes provenance one feature instead of nine), and
  the **absorption/termination result** (non-absorptive semirings have no
  fixpoint on cyclic data; measured, `Counting` and `N[X]` diverge where
  `PosBool` and `Tropical` converge). Then delete the directory.
- **`week-11` and `week-14` have no directory of their own** — expected under
  the layout, but confirm their READMEs point at where the work lives.
- **`IMPLEMENTATION_SUMMARY.md` and `LEAN_PROOFS_EXPANSION_SUMMARY.md`** are at
  the root and are pre-reorganisation artifacts. Same category as the deepfake
  summary that was deleted.
- **`__pycache__/` and `_codeql_detected_source_root` are untracked at the
  root.** Add to `.gitignore` or remove.
- **`LOG.md` still does not exist.** Every week README instructs you to write it
  daily; `ROADMAP.md` calls it the only artifact that will still be useful in a
  year. The journal at `journal/` may now be that thing — if so, say so in the
  week READMEs so the instruction points somewhere real.

---

## Suggested order

1. Verify the 59 checks against throwaway references. Nothing else is safe
   until this is done, and the plan starts tomorrow.
2. Fix `check_paper_choices` to grade mechanisms (§1b).
3. Decide on `rl-posttraining-llm`: merge, or rebuild check-only (§2).
4. Mine and delete `provenance-reasoning` (§3).
5. Housekeeping (§3), including whether `journal/` replaces `LOG.md`.
6. Re-read the 100 h/week number and decide whether the plan is the one you
   are going to follow.
