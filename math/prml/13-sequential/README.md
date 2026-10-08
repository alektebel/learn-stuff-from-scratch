# Sequential models: HMMs, Kalman filtering and smoothing

Forward-backward and Viterbi for hidden Markov models, Baum-Welch EM, and the Kalman
filter with the Rauch-Tung-Striebel smoother for linear-Gaussian state-space models, from
scratch. Implements chapter 13 of Bishop, *Pattern Recognition and Machine Learning*
(`bishop:13`; the argument is restated here, never copied). Pure standard library, only
`math`; no numpy.

**Status: not built.** `sequential.py` holds the stubs; `check.py` grades them. This file
describes the work; `solutions/` is the reference.

## What you build

`sequential.py`, eight graded functions. The small dense linear-algebra helpers (`_matvec`,
`_matmul`, `_transpose`, `_add`, `_sub`, `_eye`, `_inv`) and the demo are given.

| Function | What it does |
|---|---|
| `forward(pi, A, B, obs)` | scaled forward recursion; returns normalised `alphas` and the per-step scaling factors `cs` |
| `backward(pi, A, B, obs)` | scaled backward recursion with the same scaling factors |
| `forward_backward(pi, A, B, obs)` | per-time posterior state marginals `gamma[t][i] = P(q_t=i \| obs)` |
| `viterbi(pi, A, B, obs)` | most likely state sequence (MAP path), max-product with backpointers |
| `baum_welch(pi, A, B, obs, maxit)` | EM for `pi, A, B`; returns the parameters and the log-likelihood trajectory |
| `kalman_filter(mu0, P0, F, H, Q, R, obs)` | filtered means/covariances `p(x_t \| y_0..y_t)` |
| `rts_smoother(mu0, P0, F, H, Q, R, obs)` | smoothed means/covariances `p(x_t \| y_0..y_{T-1})` |
| `batch_gaussian_posterior(mu0, P0, F, H, Q, R, obs)` | exact joint posterior by assembling the whole linear-Gaussian system, for comparison |

The HMM is `pi` (length `N`), `A[i][j] = P(q_t=j | q_{t-1}=i)`, `B[i][k] = P(o_t=k |
q_t=i)`, and `obs` a list of emission indices. The state-space model is `x_0 ~ N(mu0, P0)`,
`x_t = F x_{t-1} + w` with `w ~ N(0, Q)`, `y_t = H x_t + v` with `v ~ N(0, R)`, and `obs`
a list of observation vectors.

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`sequential.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | forward-backward marginals equal the checker's brute-force sum over all state paths, to `1e-9`, on six random short HMMs |
| 2 | Viterbi returns the MAP path: its joint probability matches the checker's brute-force argmax |
| 3 | Baum-Welch increases the log-likelihood every iteration (within `1e-6`), improves it by more than `1.0` on a seeded synthetic HMM, and returns valid distributions |
| 4 | the accept criterion: the final Kalman filtered estimate equals the exact batch Gaussian posterior on the last state, and the RTS smoother equals the batch posterior on the middle state, to `1e-9` |
| 5 | the limit: on a 1200-step sequence the check's own unscaled forward variable underflows to zero, while your scaled forward stays finite and sums to one at every step |

## Design decisions

- **The forward variable is rescaled to sum to one at every step.** The raw `alpha_t` is a
  joint probability and shrinks by a factor below one per observation; over a thousand
  steps it flushes to zero. Dividing by `c_t = sum(a)` and keeping `c_t` preserves both the
  numerics and the likelihood, since `prod(cs) = P(obs)`. This is the whole point of step 5.
- **Backward shares the forward scaling factors.** `beta_t[i] = (sum_j A[i][j] B[j][o_{t+1}]
  beta_{t+1}[j]) / c_{t+1}` makes `alphas[t] * betas[t]` already proportional to
  `P(q_t | obs)`, so `gamma` is a normalised elementwise product.
- **Viterbi is max-product in log space with backpointers.** Products underflow and the
  argmax is what matters, so the scores add log probabilities and take the max, storing the
  predecessor that attained it. The decode walks the backpointers down from the best final
  state; a running max without backpointers is not a path.
- **Baum-Welch is the forward-backward E-step plus the closed-form M-step.** `xi` is the
  pairwise posterior from the same scaled messages; the M-step sets `pi`, `A`, `B` to
  expected transition and emission counts. The reported trajectory is the likelihood of the
  *returned* parameters under the same forward recursion, so a mismatch is visible.
- **The Kalman filter is the Gaussian update written in moments.** Predict with `F, Q`,
  correct with the innovation covariance `S = H P H^T + R` and gain `K = P H^T S^{-1}`.
  Dropping `R` from `S` inflates the gain — the planted bug.
- **The smoother is a backward recursion with its own gain.** The RTS gain is
  `G = P_t F^T (F P_t F^T + Q)^{-1}`, which uses the process model; the filter gain uses the
  observation model. Substituting one for the other is the planted bug.
- **`batch_gaussian_posterior` is an independent reference, not a shipping method.** It
  builds the joint precision of `(x_0..x_{T-1})` in information form and inverts it. It is
  `O((NT)^3)`, but for a short sequence it gives the exact marginals the recursions must
  match without sharing any code with them.

## Limit cases

- **Long sequences underflow.** With near-uniform emissions the forward variable halves
  every step; after about 1075 steps it is subnormal and then exactly zero. Scaling (or log
  space) keeps every intermediate finite and normalised. Step 5 asserts the difference.
- **Filtering is not smoothing.** The filtered estimate at time `t` conditions only on
  `y_0..y_t`, so it equals the batch posterior only at the final step; the smoother
  conditions on the whole sequence and matches the batch posterior at every step.
- **EM only guarantees a local maximum.** Baum-Welch never decreases the likelihood, but it
  can converge to a local optimum; the check asserts monotonicity and improvement on
  synthetic data from a seeded model, not global optimality.
- **Ties in MAP decoding.** With random continuous parameters a tie is measure zero; the
  check compares joint probabilities so the decode is graded on the value it finds, not on
  an arbitrary representative of a tie.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/13-sequential math/prml/13-sequential/_build/mutations.py`).

| Bug | Step |
|---|---|
| the forward recursion never rescales (underflow on the long sequence) | 5 |
| the backward recursion uses the transposed transition matrix | 1 |
| Viterbi drops the backpointers | 2 |
| the Kalman update drops `R` from the innovation covariance | 4 |
| the RTS smoother uses the filter gain instead of the smoother gain | 4 |
| `batch_gaussian_posterior` drops the initial-state prior precision | 4 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why does `prod(cs)` equal `P(obs)`, and why is dividing by `c_t` the same computation as
   the unscaled recursion followed by one normalisation at the end?
2. In the backward recursion, why does dividing by `c_{t+1}` (forward's factor) and not the
   backward step's own sum make `alphas[t] * betas[t]` the posterior?
3. Viterbi and forward-backward differ only in `sum` versus `max`. Where exactly does the
   backpointer become necessary, and what does the algorithm return without it?
4. Derive the RTS gain `P_t F^T (F P_t F^T + Q)^{-1}` from the joint Gaussian of
   `(x_t, x_{t+1})`. Why can the filter gain not appear there?
5. `batch_gaussian_posterior` inverts an `NT x NT` matrix. How does the Kalman filter get
   the same last-state marginal in `O(T)` without ever forming it?

## Limits

- Dense `O(N^2)`-per-step HMM recursions and dense matrix inverses; small `N`, `M` and
  state dimension only.
- `baum_welch` can hit zero expected counts; it falls back to the previous parameter row
  there rather than smoothing, so a degenerate model can stall.
- `batch_gaussian_posterior` is exponential in the sequence length; the checker uses four
  steps and a two-dimensional state.
- Non-linear state-space models, particle filters and continuous-state HMMs are out of
  scope.
