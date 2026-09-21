"""
Step 3 — Candidate assertions
=============================
Paper: SPADE section 2.3. Two-step in the original (criteria, then Python).
Here you write the Python yourself from the category.

An assertion is a callable (response: str) -> bool.
True means "this output is OK". False means "flag it".

DESIGN DECISION — boolean, not a score.
  The selector is an ILP over coverage and false-failure rate. Those are
  defined on binary outcomes. A soft score would need a threshold, which
  is another assertion in disguise.

The fixture only needs a handful of real predicates. Do not call an LLM.
"""

from typing import Callable, Dict, List, Sequence

Assertion = Callable[[str], bool]


def word_count(text: str) -> int:
    """TODO: len(text.split()), treating runs of whitespace as one break."""
    raise NotImplementedError


def mentions_sensitive_attribute(text: str) -> bool:
    """TODO: True if text.lower() contains race, ethnicity, or 'white viewer'."""
    raise NotImplementedError


def mentions_genre(text: str) -> bool:
    """TODO: True if any of crime, thriller, drama, comedy, sci-fi appear."""
    raise NotImplementedError


def make_assertion(category: str, sentence: str) -> Assertion:
    """Build a predicate from a classified added sentence.

    Required behaviour on the fixture:
      quantity_instruction containing '100' -> word_count(response) <= 100
      exclusion_instruction about race/ethnicity -> not mentions_sensitive...
      inclusion_instruction mentioning 'genre' -> mentions_genre(response)
      qualitative_criteria about concise -> word_count(response) <= 40
      everything else -> a default that returns True (does not flag)

    Return a function, not a bool. The same assertion runs on every labelled
    response in selector.py.
    """
    raise NotImplementedError


def generate_candidates(classified_additions: Sequence[Dict[str, str]]
                        ) -> List[Dict]:
    """TODO: one dict per classified addition:

      {"sentence": ..., "category": ..., "assert": make_assertion(...)}

    `classified_additions` items are {"sentence", "category"}.
    Keep the incoming order — selector.py cites by index.
    """
    raise NotImplementedError
