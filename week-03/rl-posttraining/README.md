# RL Post-Training for LLMs — from scratch

**SKELETON.** File structure, signatures and the checker contract are in place.
Nothing is implemented, and the checks are not written either. See
[`../../TODO.md`](../../TODO.md) for the steps.

Pure Python 3 standard library. No model, no GPU, no download — every mechanism
here is a property of an **estimator**, and a real policy would only add noise
to the measurement.

## Why this directory exists

The repo already has a teacher supervising every token
([`llm-from-scratch/distill.py`](../../week-02/llm-from-scratch/distill.py)).
This is the other end of the same axis: one scalar supervising a whole episode.
The `supervision_density` table in `distill.py` already names that comparison —
this makes it runnable.

| | signal | needs | fails when |
|---|---|---|---|
| SFT | one target sequence | a corpus | you deploy |
| distillation | full distribution per token | a teacher | the teacher is wrong |
| RL | one scalar per episode | a reward | the reward is gameable |

It also pairs with [`mars-sql/`](../../week-05/mars-sql/) — the same
application (text-to-SQL, multi-turn, schema discovery) from the training side
rather than the inference side.

## What you build

| File | Mechanism | Stubs |
|---|---|---|
| `env.py` | PROVIDED — a tiny categorical env | 3 |
| `policy_gradient.py` | `∇E[R] = E[R ∇log π]`, against finite differences | 4 |
| `baselines.py` | Variance down, mean unmoved — and the one that biases | 4 |
| `kl_estimators.py` | k1 / k2 / k3 | 4 |
| `ppo.py` | Trust region → the one-sided clip | 4 |
| `grpo.py` | Group baseline, and Dr. GRPO's two normalisations | 3 |
| `async_rl.py` | Staleness, importance ratios, effective sample size | 3 |
| `reward_hacking.py` | Proxy up, true down, KL as the knob | 3 |
| `dpo.py` | `π* ∝ π_ref·exp(r/β)`, and its inverse | 4 |

```bash
cd week-03/rl-posttraining
python3 check.py          # 9 graded checks — NOT YET WRITTEN
```

**There is no `solutions/` here, on purpose.** Reading an answer converts an
exercise into a transcription. That makes the checker the only feedback, which
raises the bar on the checker: it has to be verified two ways before it is
worth trusting. See [`../../tools/verify_checks.py`](../../tools/verify_checks.py).

## The nine measurements

1. **The identity.** `∇E[R] = E[R ∇log π]`, checked against central differences.
   Everything below is a variance argument about the right-hand side.
2. **Baselines.** Subtracting `b(s)` is unbiased because `E[∇log π] = 0`.
   Subtracting anything that depends on the **action** is not — and that bias
   is easy to introduce by accident, so it is measured here on purpose.
3. **k1 / k2 / k3.** `k1 = −log r` is unbiased, high variance, and goes
   negative. `k2 = ½(log r)²` is low variance and biased. `k3 = r − 1 − log r`
   is unbiased **and** non-negative, which is why it is the one in every modern
   implementation.
4. **The PPO clip is one-sided per sample.** It stops the ratio moving further
   in the direction that already helped and does nothing in the other. The clip
   fraction is the number to log in a real run.
5. **GRPO replaces the critic with a group mean.** No value network, no GAE, no
   second model to train.
6. **Dr. GRPO.** Dividing by the group std and by response length each
   introduce a bias. Measure the length bias, remove the terms, measure it gone.
7. **Async staleness.** The importance ratio drifts as generation lags the
   update. Effective sample size falls with lag, and where it crosses a
   threshold is the real constraint on async throughput — not the hardware.
8. **Reward hacking.** Proxy reward rising while true reward falls. The KL
   coefficient trades them, and it is the same axis as forward-vs-reverse KL in
   `distill.py`, reached from the other side.
9. **DPO's identity.** `r = β log(π*/π_ref) + β log Z`. The constant is
   per-prompt and cancels in a pairwise margin, which is exactly why DPO never
   has to fit `Z`.

## Sources

Built as a synthesis, not as a reimplementation of any one of these:

- **The RLHF Book** — [rlhfbook.com](https://rlhfbook.com), Nathan Lambert
- **Reinforcement Learning: An Introduction** — Sutton & Barto (ch. 13)
- **Spinning Up in Deep RL** — [OpenAI](https://spinningup.openai.com/en/latest/)
- **Build an LLM / Reasoning Model from Scratch** — Sebastian Raschka
- **Approximating KL Divergence** — [John Schulman](http://joschu.net/blog/kl-approx.html), plus TRPO and PPO
- **Policy Gradient Algorithms** — [Lilian Weng](https://lilianweng.github.io/posts/2018-04-08-policy-gradient/)
- **A Vision Researcher's Guide to RL** — [Yuge Ten](https://yugeten.github.io/posts/2025/01/ppogrpo/)
- **From REINFORCE to Dr. GRPO** — Qingfeng Lan
- **Async GRPO in the Wild** — Yumo Xu
- **TRL** and **OpenInstruct** — for what the production paths actually do

---

[← Week 5](../) · [Roadmap](../../ROADMAP.md) · [What remains](../../REMAINING.md)
