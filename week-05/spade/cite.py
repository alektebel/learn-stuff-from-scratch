"""
Step 5 — Cite each kept assertion back to its prompt delta
==========================================================
This is the join with ContextCite. SPADE chose the assertion; ContextCite
says which source sentence actually supports it.

You will partition the CONCATENATED added-sentences of the prompt history
as the "context", use the assertion's `sentence` as the "response", and
ask ContextCite which sources caused that response. The top source should
be the delta the assertion was generated from.

DESIGN DECISION — why cite at all?
  An assertion that cannot be traced to a developer edit is a check you
  invented. The paper's claim is that the edits already named the failure
  modes. Citation is how you verify that claim per assertion, instead of
  taking the ILP's word for it.

Do ../contextcite/ first. This file imports it.
"""

from typing import Dict, List, Sequence


def history_as_context(added_by_version: Sequence[Sequence[str]]) -> str:
    """Join every added sentence, in version order, with a single space.

    TODO: flatten, skip empty strings, join with ' '. This is the context
    ContextCite will ablate. Stable order is load-bearing: source indices
    are how we name a delta.
    """
    raise NotImplementedError


def cite_assertion(assertion_sentence: str,
                   context: str,
                   top_k: int = 1) -> List[Dict]:
    """Run ContextCite and return the top_k sources.

    TODO:
    1. Import ContextCiter from the neighbouring contextcite package
       (sys.path insert of ../contextcite is fine and expected).
    2. You need a model. Use contextcite.toy_lm.ToyLM with
       context=context and query=assertion_sentence, or pass a response=
       directly if your ContextCiter allows it.
    3. Return [{"index": int, "source": str, "score": float}, ...]
       sorted by score descending, length top_k.

    If ContextCite is not implemented yet this will raise
    NotImplementedError — that is the correct next step, not a skip.
    """
    raise NotImplementedError


def cite_selected(selected: Sequence[dict],
                  added_by_version: Sequence[Sequence[str]]
                  ) -> List[Dict]:
    """Cite every selected assertion.

    TODO: build the context once, then for each selected item call
    cite_assertion(item["sentence"], context, top_k=1) and attach
    item["cited_source"] = that top source string.
    Return the selected list (mutated or copied).
    """
    raise NotImplementedError
