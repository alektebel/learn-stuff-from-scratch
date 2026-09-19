"""
Byte-Pair Encoding — complete solution.

DESIGN DECISION — character vocabulary or byte vocabulary?
  CHOSEN: bytes (all 256 always present, no [UNK]).

DESIGN DECISION — merge order at encode time?
  CHOSEN: lowest-rank merge first, applied until no known pair remains.

DESIGN DECISION — tie-break in training?
  CHOSEN: highest count, then smallest pair tuple. Deterministic.
"""

from collections import Counter
from typing import Dict, List, Tuple


def bytes_to_symbols(data: bytes) -> List[int]:
    return list(data)


def get_pair_counts(symbols: List[int]) -> "Counter[Tuple[int, int]]":
    counts: "Counter[Tuple[int, int]]" = Counter()
    for a, b in zip(symbols, symbols[1:]):
        counts[(a, b)] += 1
    return counts


def merge_pair(symbols: List[int], pair: Tuple[int, int], new_id: int) -> List[int]:
    out: List[int] = []
    i = 0
    while i < len(symbols):
        if i < len(symbols) - 1 and (symbols[i], symbols[i + 1]) == pair:
            out.append(new_id)
            i += 2
        else:
            out.append(symbols[i])
            i += 1
    return out


def train_bpe(data: bytes, num_merges: int) -> Dict[Tuple[int, int], int]:
    symbols = bytes_to_symbols(data)
    merges: Dict[Tuple[int, int], int] = {}
    for rank in range(num_merges):
        counts = get_pair_counts(symbols)
        if not counts:
            break
        pair = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        new_id = 256 + rank
        symbols = merge_pair(symbols, pair, new_id)
        merges[pair] = new_id
    return merges


def encode(text: str, merges: Dict[Tuple[int, int], int]) -> List[int]:
    symbols = bytes_to_symbols(text.encode("utf-8"))
    while True:
        best_pair = None
        best_id = None
        for a, b in zip(symbols, symbols[1:]):
            pair = (a, b)
            new_id = merges.get(pair)
            if new_id is not None and (best_id is None or new_id < best_id):
                best_id = new_id
                best_pair = pair
        if best_pair is None:
            break
        symbols = merge_pair(symbols, best_pair, best_id)
    return symbols


def decode(ids: List[int], merges: Dict[Tuple[int, int], int]) -> bytes:
    reverse = {v: k for k, v in merges.items()}
    out = bytearray()
    for token in ids:
        stack = [token]
        while stack:
            current = stack.pop()
            if current < 256:
                out.append(current)
            else:
                left, right = reverse[current]
                stack.append(right)
                stack.append(left)
    return bytes(out)


if __name__ == "__main__":
    corpus = (b"the quick brown fox jumps over the lazy dog. "
              b"the quick brown fox is quick and the dog is lazy. ") * 20
    merges = train_bpe(corpus, num_merges=48)
    ids = encode(corpus.decode(), merges)
    ratio = len(ids) / len(corpus)
    print(f"merges learned:        {len(merges)}")
    print(f"tokens for {len(corpus)} bytes: {len(ids)}  ({ratio:.3f} tokens/byte)")
    print(f"round-trip exact:      {decode(ids, merges) == corpus}")
    print(f"first merge (most frequent byte pair): {next(iter(merges))}")
