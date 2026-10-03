# 93 characteristic bugs

Six catalogues, one per directory that has reference implementations. Each entry
is `(check_step, filename, description, correct_code, broken_code)`.

These are **not random mutations.** Every one was written deliberately, injected
into a working implementation, and confirmed to make a specific check fail. They
are the mistakes that actually get made:

| Directory | Bugs | Example |
|---|---|---|
| `autograd` | 18 | `train_mode` misses a Dropout inside a Sequential |
| `aws-from-scratch` | 13 | policy evaluation lets order change the answer |
| `database-engine` | 20 | recovery redoes but never undoes |
| `llm-from-scratch` | 14 | the causal mask is applied after the softmax |
| `raft` | 12 | commit on a majority alone, without the current-term clause |
| `ray-tracer` | 16 | matte sampling is uniform over the hemisphere, not cosine-weighted |
| | **93** | |

## Two uses

**1. Verifying a checker** (TODO §1). A checker has to be shown to *catch*
things, not merely to pass. Injecting a known bug and requiring the
corresponding check to fail is the half of verification that finds real
problems — it caught four bugs in reference code here that a passing checker had
missed.

**2. Debugging practice** (TODO §13). Inject one at random, hand over the broken
tree and the symptom, and find it. Score by **how many observations you needed**,
not by whether you eventually got there.

## Why these are good exercises

The best ones do not crash. They produce a **plausible** result:

- Sampling the hemisphere uniformly instead of cosine-weighted still renders an
  image. It just looks flatter.
- Semi-naive evaluation over a non-idempotent semiring still terminates with an
  answer. It undercounts.
- A missing `/2` in a VAE's reparameterisation still trains. The samples are
  slightly worse, forever.

A bug that produces a plausible picture is the hardest kind to find, and the
only kind worth practising on.

## Do not read these while learning

They are the answer key. Run the harness; do not open the catalogue.

---

[Verification harness](../verify_checks.py) · [TODO](../../TODO.md)
