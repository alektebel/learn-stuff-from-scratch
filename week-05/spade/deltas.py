"""
Step 1 — Prompt deltas
======================
Paper: SPADE (Shankar et al., PVLDB 2024), section 2.1.

A prompt delta ΔP_i is the diff between version i-1 and version i.
Each sentence is tagged + (added) or - (removed). A modification is a
deletion plus an addition. Only additions become assertion candidates —
a deleted instruction is a thing the developer no longer wants checked,
or a thing they now expect the model to do without being told.

DESIGN DECISION — why every version, not just the last prompt?
  Developers delete instructions to save tokens and still expect the
  behaviour. Looking only at P_final misses those. The paper analyses
  every ΔP for that reason. CHOSEN: emit a delta per consecutive pair,
  including deletions, and let the selector drop what labels do not support.

TODO:
  prompt_delta(prev, curr) -> list of {op, sentence}
  history_deltas(versions) -> list of those lists, length len(versions)-1
  added_sentences(delta)   -> the + sentences, in order
"""

from typing import Dict, List, Sequence


def split_sentences(text: str) -> List[str]:
    """Split on '. ' / '? ' / '! ' boundaries, keeping the punctuation.

    Empty input is []. Strip each sentence. Do not invent sentences that
    were not in the text — the movie prompt is the checker's fixture.
    """
    raise NotImplementedError


def prompt_delta(previous: str, current: str) -> List[Dict[str, str]]:
    """Diff two consecutive versions.

    Each item is {"op": "+"|"-", "sentence": str}.
    Sentences in `previous` but not `current` are deletions.
    Sentences in `current` but not `previous` are additions.
    Shared sentences (exact string match after strip) are omitted —
    a delta is a change, not a restatement.

    Preserve the order: all deletions in previous-order, then all
    additions in current-order. The checker uses that to cite sources.
    """
    raise NotImplementedError


def history_deltas(versions: Sequence[str]) -> List[List[Dict[str, str]]]:
    """TODO: prompt_delta(versions[i], versions[i+1]) for each i.
    versions[0] is allowed to be the empty string (paper: P_0 = "").
    """
    raise NotImplementedError


def added_sentences(delta: Sequence[Dict[str, str]]) -> List[str]:
    """TODO: the sentence field of every item whose op is '+'."""
    raise NotImplementedError
