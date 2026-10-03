"""
Knowledge distillation — after the model exists, teach a smaller one.

You already have a transformer that predicts the next token. Distillation is
the question of *whose* next-token distribution you train against, and *on
which prefixes*. Those two choices are the whole field.

DESIGN DECISION — train on whose states?
  SFT and classical KD train on prefixes from a fixed dataset (or from a
  teacher). At inference the student generates its OWN prefixes. The two
  distributions diverge; that gap is exposure bias.
  CHOSEN for OPD: the student samples the prefixes, the teacher only scores
  them. Training states match inference states. That is the entire move.

DESIGN DECISION — which divergence?
  Forward KL (teacher || student) is mode-covering: the student must put mass
  everywhere the teacher does, including the teacher's bad modes.
  Reverse KL (student || teacher) is mode-seeking: the student is allowed to
  lock onto one of the teacher's modes and ignore the rest.
  JSD is the symmetric middle.
  MiniLLM (2023) picks reverse KL. GKD (Agarwal et al., 2024) lets you pick.
  There is no free lunch — only a named trade.

DESIGN DECISION — who is the teacher?
  Classical KD needs a larger frozen model. OPSD (on-policy self-distillation)
  uses the SAME weights twice: the teacher role sees privileged context
  (the answer, a verified trace), the student role sees only the question.
  The privilege is the point, and also the failure mode: Privilege Illusion
  is the student learning to *imitate the look of privileged reasoning*
  rather than acquiring the capability the privilege was supposed to transfer.

Papers this file is built against:
  MiniLM / MiniLLM  — Wang et al.; reverse KL, mixture for stability
  GKD               — Agarwal et al., 2024; generalised on-policy KD
  SDPO              — self-distilled preference optimisation
  OPSD              — one model, two contexts
  Privilege Illusion — DOPD and follow-ups; information asymmetry ≠ skill gap

Learning Path:
1. kl_forward / kl_reverse / jsd          — three divergences, same pair
2. sample_on_policy / sample_off_policy   — whose prefixes
3. opd_loss                               — teacher scores student states
4. compare_supervision                    — RL vs OPD vs SFT, density
5. opsd_pair                              — same weights, privileged teacher
6. paper_choices                          — named decisions, not summaries
7. privilege_illusion                     — the case that looks like learning
"""

from typing import Dict, List, Sequence, Tuple


# ---------------------------------------------------------------------------
# 1. Divergences
# ---------------------------------------------------------------------------

def _check_distribution(p: Sequence[float], name: str = "p") -> None:
    if abs(sum(p) - 1.0) > 1e-8:
        raise ValueError(f"{name} must sum to 1, got {sum(p)}")
    if any(x < 0 for x in p):
        raise ValueError(f"{name} has a negative entry")


def kl_forward(teacher: Sequence[float], student: Sequence[float]) -> float:
    """KL(teacher || student) = Σ t_i log(t_i / s_i).

    Mode-COVERING. The student is punished for missing any teacher mass.
    Zero student mass where the teacher has mass is +inf.

    TODO:
    1. Validate both are distributions.
    2. Skip terms where teacher[i] == 0 (0 log 0 is 0 by continuity).
    3. If teacher[i] > 0 and student[i] == 0, return +inf.
    4. Otherwise accumulate teacher[i] * log(teacher[i] / student[i]).
    Use math.log. Natural log — nats, same units as the training loss.
    """
    raise NotImplementedError


def kl_reverse(teacher: Sequence[float], student: Sequence[float]) -> float:
    """KL(student || teacher) = Σ s_i log(s_i / t_i).

    Mode-SEEKING. The student is punished for putting mass where the teacher
    has none. It can ignore a teacher mode entirely and still score well.

    TODO: same numerical rules as kl_forward, roles swapped.
    MiniLLM's objective is this one. GKD can pick either.
    """
    raise NotImplementedError


def jsd(teacher: Sequence[float], student: Sequence[float]) -> float:
    """Jensen-Shannon: ½ KL(t || m) + ½ KL(s || m), m = (t+s)/2.

    Symmetric, finite whenever both inputs are distributions (the mixture
    is never zero where either is positive). Bounded by log 2.

    TODO:
    1. Build m_i = 0.5 * (teacher[i] + student[i]).
    2. Return 0.5 * kl_forward(teacher, m) + 0.5 * kl_forward(student, m).
    Yes — both terms are forward KL against the mixture. Do not invent a
    third formula.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 2. On-policy vs off-policy
# ---------------------------------------------------------------------------

def sample_off_policy(teacher_logits_by_prefix: Dict[Tuple[int, ...], List[float]],
                      prefixes: Sequence[Tuple[int, ...]]
                      ) -> List[Tuple[Tuple[int, ...], List[float]]]:
    """Off-policy: the DATASET (or the teacher) chooses the prefixes.

    Returns [(prefix, teacher_distribution_at_prefix), ...] for every
    prefix in `prefixes`, in that order. The student never gets a say.

    TODO: look up each prefix in the table. Raise KeyError if a prefix is
    missing — silent fallback to a uniform is how exposure bias hides.
    Softmax the logits yourself; do not assume they are already a
    distribution. Temperature is 1.
    """
    raise NotImplementedError


def sample_on_policy(student_logits_by_prefix: Dict[Tuple[int, ...], List[float]],
                     start: Tuple[int, ...],
                     length: int,
                     rng_draws: Sequence[float]
                     ) -> List[Tuple[int, ...]]:
    """On-policy: the STUDENT walks, one token at a time.

    `rng_draws[t]` is a uniform [0, 1) used to pick token t from the
    student's softmax at the current prefix. Deterministic given the draws
    — the checker supplies them so this is testable.

    Returns the list of prefixes visited, INCLUDING `start` and each
    extension, length+1 long (start plus `length` new tokens).

    TODO:
    1. softmax the student's logits at the current prefix.
    2. Walk the cdf until it exceeds rng_draws[t]; that index is the token.
    3. Append the token, record the new prefix, repeat.
    A prefix the student can reach that is NOT in an off-policy dataset is
    exactly the exposure-bias gap OPD exists to close.
    """
    raise NotImplementedError


def exposure_gap(on_policy_prefixes: Sequence[Tuple[int, ...]],
                 off_policy_prefixes: Sequence[Tuple[int, ...]]) -> float:
    """Fraction of on-policy prefixes that never appear off-policy.

    0 means the dataset already covers every state the student visits.
    1 means training and inference share no prefixes at all.

    TODO: treat prefixes as tuples. Return
    |on \\ off| / |on|, or 0.0 if on is empty.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 3. OPD loss
# ---------------------------------------------------------------------------

def softmax(logits: Sequence[float], temperature: float = 1.0) -> List[float]:
    """TODO: numerically stable softmax. temperature divides the logits.
    T=0 is a one-hot on the argmax (same convention as sample.py).
    """
    raise NotImplementedError


def opd_loss(teacher_logits: Sequence[float],
             student_logits: Sequence[float],
             divergence: str = "reverse") -> float:
    """On-policy distillation at ONE position.

    The prefix was sampled from the student. Both models now emit a
    distribution over the next token. Minimise the named divergence.

    `divergence` is one of: "forward", "reverse", "jsd".

    DESIGN DECISION — why token-level, not sequence-level?
      RL (GRPO, PPO) gives one scalar at the end of the rollout. OPD gives
      a gradient at every token. That is why people say OPD is "dense" and
      RL is "sparse": same trajectory, |T| times more supervised positions.

    TODO:
    1. Softmax both logit vectors (T=1).
    2. Dispatch to kl_forward / kl_reverse / jsd.
    3. Raise ValueError on an unknown name — a typo here silently trains
       the wrong objective, which is the most expensive typo in the file.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 4. RL vs OPD vs SFT
# ---------------------------------------------------------------------------

def supervision_density(method: str, sequence_length: int) -> Dict[str, float]:
    """How much signal do you get per generated sequence?

    Returns a dict with:
      tokens_supervised  — how many positions receive a gradient
      signal             — "one-hot" | "distribution" | "scalar"
      states             — "off-policy" | "on-policy"
      density            — tokens_supervised / sequence_length

    Contract the checker enforces (this is the comparison, not a vibe):

      SFT  —  sequence_length tokens, one-hot, off-policy, density 1.0
              (teacher-forced; every position is supervised, on DATA prefixes)
      OPD  —  sequence_length tokens, distribution, on-policy, density 1.0
              (every position, full teacher distribution, STUDENT prefixes)
      RL   —  1 token-equivalent, scalar, on-policy, density 1/sequence_length
              (one reward at the end; the whole sequence shares it)

    TODO: implement the table. Raise ValueError on an unknown method.
    The point is that SFT and OPD look equally "dense" until you notice
    the states column, and RL and OPD look equally "on-policy" until you
    notice the signal column. All three pairwise confusions are common.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 5. OPSD — self distillation
# ---------------------------------------------------------------------------

def opsd_pair(question: Sequence[int],
              privileged: Sequence[int],
              student_logits_fn,
              teacher_logits_fn
              ) -> Tuple[List[float], List[float]]:
    """One model, two contexts.

    `student_logits_fn(tokens)` and `teacher_logits_fn(tokens)` are the
    SAME network called on different prefixes:
      student context = question
      teacher context = question + privileged   (answer, or a verified trace)

    Returns (teacher_distribution, student_distribution) at the NEXT token
    after each context — i.e. softmax of the last-position logits.

    TODO:
    1. Call teacher on list(question) + list(privileged).
    2. Call student on list(question) only.
    3. Softmax the last row of each (the functions return a list of logit
       rows, one per position, matching transformer.GPT).
    The weights are shared. If you instantiate two models you have rebuilt
    classical KD and missed the point of OPSD — and the memory saving
    (papers report ~40–60%) disappears with them.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 6. Named paper decisions
# ---------------------------------------------------------------------------

def paper_choices() -> Dict[str, Dict[str, str]]:
    """The decisions, not the abstracts.

    Return a dict keyed by "minilm", "gkd", "sdpo", "opsd" (lowercase).
    Each value is a dict that MUST contain exactly these keys:

      teacher       — "external" | "self"
      states        — "on-policy" | "off-policy" | "mixed"
      divergence    — "forward" | "reverse" | "jsd" | "preference" | "configurable"
      privilege     — "none" | "answer" | "trace" | "feedback"

    The checker compares against the papers, not against your notes.
    Fill it from the papers (or the docstring at the top of this file),
    not from memory of a blog post.

    MiniLM/MiniLLM: external teacher, on-policy (with a mix for stability),
      reverse KL, no privilege.
    GKD: external teacher, on-policy, configurable divergence, no privilege.
    SDPO: self, on-policy, preference-style objective, textual feedback.
    OPSD: self, on-policy, typically reverse/configurable, answer or trace.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 7. Privilege Illusion
# ---------------------------------------------------------------------------

def privilege_tokens(teacher_distribution: Sequence[float],
                     student_distribution: Sequence[float],
                     privileged_token_ids: Sequence[int],
                     capability_token_ids: Sequence[int]
                     ) -> Dict[str, float]:
    """Separate 'looks like the teacher' from 'can do the work'.

    Privilege Illusion: the student matches the teacher on tokens that are
    only identifiable from the privileged context (ids in
    `privileged_token_ids`) and fails to match on tokens that are the
    actual skill (`capability_token_ids`).

    Returns:
      privilege_mass_gap  — |t − s| summed over privileged ids
      capability_mass_gap — |t − s| summed over capability ids
      illusion            — True when privilege_mass_gap < capability_mass_gap
                            AND privilege_mass_gap is small (< 0.1)
                            i.e. the student copied the privilege tell and
                            missed the capability.

    TODO: implement the three fields. An empty id list contributes 0.
    The illusion flag is the lesson: a falling OPD loss can be the student
    learning to say "therefore" in the same places the teacher says
    "therefore", while still being unable to compute the answer. Loss is
    not capability. This function is how you notice.
    """
    raise NotImplementedError


if __name__ == "__main__":
    print("distill.py — implement the functions, then run:")
    print("  python3 check.py 9 15")
    print("Nothing here is runnable until the stubs are filled in.")
