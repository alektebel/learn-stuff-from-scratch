"""
Step 2 — The quantity ContextCite regresses on
===============================================
Paper: ContextCite, section 3. Reference implementation: _compute_logit_probs
and aggregate_logit_probs in context_cite/utils.py

Effort: small in code, careful in thought. Four short functions, but the
numerical details are the point — a naive version silently produces infinities.

What you build:
  token_logit_prob      -> log(p / (1-p)) for one token, straight from logits
  sequence_logit_probs  -> one per response token
  aggregate             -> collapse them into a single number per ablation
  response_score        -> the end-to-end scalar for one ablated context

Background:
  ContextCite regresses the *logit-scaled probability* of the response on which
  sources were kept. Why the logit rather than the log-probability:

    A log-probability is bounded above by 0 and saturates. If a source pushes
    an already-confident token from p=0.98 to p=0.999, log p barely moves. The
    logit is unbounded in both directions and behaves roughly additively in
    "evidence" — which is what makes fitting a LINEAR surrogate defensible.

  For one token with logits z and true token y:

      logit_prob = z[y] - logsumexp(z[j] for j != y)

  and for a whole response, using log_sigmoid(logit(p)) == log(p) exactly:

      log P(response) = sum_t log_sigmoid(logit_prob_t)
      output          = log P - log(1 - P)
"""

import math
from typing import Dict, List, Sequence


def logsumexp(values: Sequence[float]) -> float:
    """Stable log(sum(exp(v))).

    TODO: subtract the max before exponentiating; return -inf for an empty
    input. Doing this naively overflows on logits of ~700 and up.
    """
    raise NotImplementedError


def token_logit_prob(logits: Sequence[float], token_id: int) -> float:
    """log(p / (1 - p)) for one token.

    TODO: logits[token_id] - logsumexp(every OTHER logit).

    Do NOT compute this as log(p) - log(1-p) after a softmax. When p rounds to
    1.0 in floating point, 1-p is exactly 0 and you get infinity — for a token
    the model was merely very confident about, not certain of. Working from the
    logits keeps it finite and accurate.

    Test: for logits [2, 1, 0.5, -1] and token 0, this must equal
    log(p/(1-p)) computed the slow way to ~1e-12.
    """
    raise NotImplementedError


def sequence_logit_probs(logits_per_position: Sequence[Sequence[float]],
                         token_ids: Sequence[int]) -> List[float]:
    """Per-token logit-probs for a response, teacher-forced.

    TODO: zip the rows with the token ids and call token_logit_prob. Raise if
    the lengths disagree — that mismatch means you are scoring one response
    against another's logits.
    """
    raise NotImplementedError


def log_sigmoid(x: float) -> float:
    """log(1 / (1 + e^-x)).

    TODO: branch on the sign to stay stable:
        x >= 0 ->  -log1p(exp(-x))
        x <  0 ->  x - log1p(exp(x))
    A single-branch version overflows for large negative x.
    """
    raise NotImplementedError


def aggregate(token_logit_probs: Sequence[float]) -> float:
    """Collapse per-token logit-probs into one score for the response.

    TODO:
    1. log_p = sum of log_sigmoid over the tokens. (This is exactly
       log P(response) — verify that claim on one token before trusting it.)
    2. If log_p is ~0, P is indistinguishable from 1; return inf rather than
       dividing by zero.
    3. Otherwise return log_p - log1p(-exp(log_p)).

    Step 3 uses log1p rather than log(1 - exp(log_p)) because the argument is
    tiny whenever the model is confident, and log1p is accurate there.
    """
    raise NotImplementedError


def response_score(model, context: str, response: Sequence[str]) -> float:
    """The scalar for one ablated context.

    TODO: model.sequence_logits(context, response) -> per-position logits,
    map response tokens to ids with model.index, then aggregate.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify:

    1. token_logit_prob agrees with log(p/(1-p)) to ~1e-12 on ordinary logits.
    2. log_sigmoid(token_logit_prob(...)) == log(p). This identity is what
       makes aggregate() correct; check it before moving on.
    3. Logits like [40, 0, 0] give a finite answer (~39.3) where the softmax
       route gives p == 1.0 and a division by zero.
    4. The real signal: score the response under the full context, then under
       each leave-one-out ablation. Dropping source 4 should cost ~37 while
       every other source costs about 1 — and several are NEGATIVE, meaning the
       response gets likelier without them. Those are distractors.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
