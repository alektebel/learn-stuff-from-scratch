"""
Byte-Pair Encoding — turn text into tokens by learning the merges that compress it.

The model never sees characters. It sees a sequence of integer ids from a vocabulary
this file builds. Get the vocabulary shape wrong and every downstream number is wrong,
so this is the first thing to implement and the first thing worth checking.

DESIGN DECISION — character vocabulary or byte vocabulary?
  A character vocabulary is smaller for English but explodes for Unicode, and needs an
  [UNK] token, which silently maps unseen characters into a placeholder the model can
  never recover.
  CHOSEN: bytes. All 256 are always in vocabulary, so every string is representable and
  there is no [UNK]. The cost is that non-English text starts longer, which is exactly
  the trade real tokenizers make.

DESIGN DECISION — what order do merges apply at encode time?
  A left-to-right sweep that merges whenever it sees a known pair is simple and wrong:
  which pair is present first depends on ordinary text order, so the tokenization stops
  matching the rank order training produced.
  CHOSEN: always apply the LOWEST-RANK applicable merge anywhere in the sequence, repeat
  until no known pair remains. The rank is the merge id; lower id wins. This is what makes
  training and encoding agree.

DESIGN DECISION — how to break ties in pair frequency?
  Ties are common on small corpora and a set/dict iteration order would make training
  irreproducible.
  CHOSEN: highest count first, then smallest pair tuple. Deterministic, documented, and
  the same corpus always yields the same tokenizer.
"""

from collections import Counter
from typing import Dict, List, Tuple


def bytes_to_symbols(data: bytes) -> List[int]:
    """Provided, not an exercise: bytes are already the initial symbols."""
    return list(data)


def get_pair_counts(symbols: List[int]) -> "Counter[Tuple[int, int]]":
    """Count every adjacent pair in the sequence."""
    raise NotImplementedError


def merge_pair(symbols: List[int], pair: Tuple[int, int], new_id: int) -> List[int]:
    """Replace every non-overlapping occurrence of `pair` with `new_id`.

    `aa` in `aaa` becomes `(new, a)`, never two overlapping merges — scan with an
    index, not a `zip`-and-rebuild.
    """
    raise NotImplementedError


def train_bpe(data: bytes, num_merges: int) -> Dict[Tuple[int, int], int]:
    """Learn `num_merges` merges; return {pair: new_id}.

    New ids start at 256 and increase. At each step merge the most frequent pair,
    break ties by the smallest pair tuple, and stop early if no pairs remain.
    """
    raise NotImplementedError


def encode(text: str, merges: Dict[Tuple[int, int], int]) -> List[int]:
    """Tokenize `text` with a trained merge table.

    Apply the lowest-id applicable merge anywhere in the sequence, repeatedly, until
    no known pair is left. A left-to-right sweep gives different tokens on the same
    text and is the bug this function exists to avoid.
    """
    raise NotImplementedError


def decode(ids: List[int], merges: Dict[Tuple[int, int], int]) -> bytes:
    """Invert `encode`: expand every id >= 256 back into its two children.

    Byte ids (< 256) are appended directly; a merge id is expanded recursively. The
    result must be the original bytes for any text whose bytes were in vocabulary.
    """
    raise NotImplementedError
