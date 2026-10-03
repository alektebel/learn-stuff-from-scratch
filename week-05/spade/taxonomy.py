"""
Step 2 — Taxonomy of prompt deltas
==================================
Paper: SPADE Figure 2. Structural (~35%) vs content-based (~65%).

You do not call an LLM here. The categories are a small keyword/heuristic
classifier so the directory stays pure Python and the checker is deterministic.
The paper used GPT-4 and reported F1 0.81 against human labels; your job is
to get the FIXTURE versions right, which is the same decision procedure
with a known answer.

DESIGN DECISION — classify the delta, not the whole prompt.
  Prompting "write assertions for this prompt" misses pieces. Classifying
  each added sentence against the taxonomy is what made candidate generation
  cover the failure modes the authors actually saw.

Categories (must match fixtures.TAXONOMY):
  response_format, example_demonstration, prompt_clarification,
  workflow_description, data_integration, quantity_instruction,
  inclusion_instruction, exclusion_instruction, qualitative_criteria
"""

from typing import Dict, Sequence


def classify_sentence(sentence: str) -> str:
    """Return exactly one category name from fixtures.TAXONOMY.

    Heuristics that pass the fixture (and nothing more is required):
      - '{...}' placeholder  -> data_integration
      - 'do not' / 'don't' / 'avoid' / 'not mention' -> exclusion_instruction
      - a number plus 'word' / 'sentence' / 'character' -> quantity_instruction
      - 'for example' / 'e.g.' -> example_demonstration
      - 'first,' / 'then,' / 'step' -> workflow_description
      - 'json' / 'markdown' / 'start with' / 'format' -> response_format
      - 'concise' / 'tone' / 'friendly' / 'professional' -> qualitative_criteria
      - 'mention' / 'include' / 'ensure' (and not exclusion) -> inclusion_instruction
      - otherwise prompt_clarification

    Apply them in that order so a sentence that matches two things lands
    in the more specific bucket. The fixture's VERSION_CATEGORY is the spec.
    """
    raise NotImplementedError


def classify_delta(delta: Sequence[Dict[str, str]]) -> Dict[str, str]:
    """Map each ADDED sentence to a category.

    TODO: {sentence: classify_sentence(sentence)} for op == '+'.
    Deletions are not classified — they do not generate assertions.
    """
    raise NotImplementedError
