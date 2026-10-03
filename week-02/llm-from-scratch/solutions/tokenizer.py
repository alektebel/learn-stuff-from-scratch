"""
Tokenizer — byte-pair encoding. Complete Solution.

Before a model sees text it sees integers, and the choice of how to turn one
into the other decides your sequence lengths, your vocabulary size, how the
model handles a word it has never seen, and — as section 5 measures — how much
it costs to serve a language you did not think about.

DESIGN DECISION — characters, words, or something between?
  CHARACTERS: a tiny vocabulary, nothing is ever out-of-vocabulary, and
  sequences are enormous. Attention is quadratic in sequence length, so a 4x
  longer sequence is 16x the attention cost.
  WORDS: short sequences and a vocabulary in the hundreds of thousands, most of
  which appear a handful of times. Worse, any word not in the list is
  unrepresentable — `<unk>` — and a model cannot generate what it cannot
  represent.
  CHOSEN: BYTE-PAIR ENCODING. Start from bytes (so nothing is ever
  out-of-vocabulary, in any language, including emoji) and repeatedly merge the
  most frequent adjacent pair. Frequent words end up as single tokens; rare
  ones decompose into pieces; a string never seen in training still encodes.
  It is a compression algorithm from 1994 doing a job nobody designed it for,
  and that is genuinely most of why it works.

DESIGN DECISION — what does the merge order mean?
  The merges are LEARNED, in order, and they must be REPLAYED in that same
  order at encode time. Merge 1 might be "t"+"h" and merge 40 "the"+" ". Apply
  40 before 1 and you get a different tokenisation of the same string — which
  means a model trained with one merge order cannot read text tokenised with
  another. The merge list is part of the model, not a preprocessing detail.

DESIGN DECISION — pre-tokenise on whitespace first, or merge across it?
  CHOSEN: split on word boundaries before merging, keeping the leading space
  attached to the word (` the`, not `the`). Two consequences:
    * merges never span a space, so "the cat" cannot become one token
    * ` the` and `the` are different tokens, which is why almost every
      generation bug involving a missing or doubled space is a tokenisation
      bug, not a model bug
"""

import collections
import json
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# Split into words, keeping the leading space attached. GPT-2's real pattern is
# a great deal more careful about contractions and unicode categories; this is
# the shape of it.
WORD = re.compile(r"\s?[A-Za-z]+|\s?\d+|\s?[^\sA-Za-z\d]+|\s+")


class BPETokenizer:
    """Learn merges from a corpus, then replay them to encode."""

    def __init__(self) -> None:
        self.merges: List[Tuple[str, str]] = []
        self.ranks: Dict[Tuple[str, str], int] = {}
        self.vocab: Dict[str, int] = {}
        self.inverse: Dict[int, str] = {}
        self.stats = {"merges_learned": 0, "corpus_symbols": 0}

    # -- training -----------------------------------------------------------

    def train(self, text: str, vocabulary_size: int = 256,
              verbose: bool = False) -> None:
        """Learn merges until the vocabulary reaches `vocabulary_size`.

        The loop is the whole algorithm: count adjacent pairs across the
        corpus, merge the most frequent one everywhere, repeat. Each merge adds
        exactly one token to the vocabulary, so the number of merges is
        `vocabulary_size - len(alphabet)`.
        """
        words = collections.Counter(WORD.findall(text))
        # Each word is a tuple of symbols. Counting UNIQUE words with their
        # frequencies rather than walking the raw text is the whole reason this
        # is tractable: a corpus of a million words has maybe 30,000 distinct
        # ones, so every merge pass is 30x cheaper.
        splits = {word: tuple(word) for word in words}
        alphabet = sorted({character for word in words for character in word})
        self.vocab = {symbol: index for index, symbol in enumerate(alphabet)}
        self.merges = []
        self.stats["corpus_symbols"] = sum(len(w) * n for w, n in words.items())

        while len(self.vocab) < vocabulary_size:
            pairs = collections.Counter()
            for word, count in words.items():
                symbols = splits[word]
                for i in range(len(symbols) - 1):
                    pairs[(symbols[i], symbols[i + 1])] += count
            if not pairs:
                break
            best, frequency = pairs.most_common(1)[0]
            if frequency < 2:
                break                       # merging a hapax helps nothing
            splits = {word: _merge_word(symbols, best)
                      for word, symbols in splits.items()}
            merged = best[0] + best[1]
            self.merges.append(best)
            self.vocab[merged] = len(self.vocab)
            if verbose and len(self.merges) <= 10:
                print(f"    merge {len(self.merges):>3}: "
                      f"{best[0]!r} + {best[1]!r} -> {merged!r}  "
                      f"({frequency} occurrences)")

        self.ranks = {pair: index for index, pair in enumerate(self.merges)}
        self.inverse = {index: symbol for symbol, index in self.vocab.items()}
        self.stats["merges_learned"] = len(self.merges)

    # -- encoding -----------------------------------------------------------

    def encode_word(self, word: str) -> List[str]:
        """Apply the learned merges to one word, IN RANK ORDER.

        Rank order, not left to right. At each step find the pair present in
        this word with the LOWEST rank — the earliest one learned — and apply
        it. Apply merges in the order they happen to appear in the word and you
        get a different tokenisation than training produced, and the model
        receives token sequences it has never seen.
        """
        symbols = list(word)
        while len(symbols) > 1:
            candidates = [(self.ranks[(symbols[i], symbols[i + 1])], i)
                          for i in range(len(symbols) - 1)
                          if (symbols[i], symbols[i + 1]) in self.ranks]
            if not candidates:
                break
            _, position = min(candidates)
            symbols[position:position + 2] = [symbols[position]
                                              + symbols[position + 1]]
        return symbols

    def encode(self, text: str) -> List[int]:
        out: List[int] = []
        for word in WORD.findall(text):
            for symbol in self.encode_word(word):
                if symbol in self.vocab:
                    out.append(self.vocab[symbol])
                else:
                    # A character not in the training alphabet. Real BPE works
                    # on BYTES so this cannot happen; here it is dropped, and
                    # that difference is exactly why byte-level tokenisers won.
                    for character in symbol:
                        if character in self.vocab:
                            out.append(self.vocab[character])
        return out

    def decode(self, ids: Sequence[int]) -> str:
        return "".join(self.inverse.get(index, "") for index in ids)

    @property
    def size(self) -> int:
        return len(self.vocab)

    def compression(self, text: str) -> float:
        """Characters per token. Higher is better, and it is the number that
        decides both your context window and your bill."""
        tokens = self.encode(text)
        return len(text) / max(1, len(tokens))

    def save(self) -> str:
        return json.dumps({"merges": self.merges,
                           "vocab": self.vocab}, ensure_ascii=False)

    @classmethod
    def load(cls, blob: str) -> "BPETokenizer":
        data = json.loads(blob)
        tokenizer = cls()
        tokenizer.merges = [tuple(pair) for pair in data["merges"]]
        tokenizer.ranks = {pair: index
                           for index, pair in enumerate(tokenizer.merges)}
        tokenizer.vocab = data["vocab"]
        tokenizer.inverse = {index: symbol
                             for symbol, index in tokenizer.vocab.items()}
        return tokenizer


def _merge_word(symbols: Tuple[str, ...],
                pair: Tuple[str, str]) -> Tuple[str, ...]:
    out: List[str] = []
    i = 0
    while i < len(symbols):
        if (i < len(symbols) - 1 and symbols[i] == pair[0]
                and symbols[i + 1] == pair[1]):
            out.append(pair[0] + pair[1])
            i += 2
        else:
            out.append(symbols[i])
            i += 1
    return tuple(out)


class CharTokenizer:
    """One token per character. Here as the baseline BPE is measured against."""

    def __init__(self, text: str):
        self.vocab = {c: i for i, c in enumerate(sorted(set(text)))}
        self.inverse = {i: c for c, i in self.vocab.items()}

    @property
    def size(self) -> int:
        return len(self.vocab)

    def encode(self, text: str) -> List[int]:
        return [self.vocab[c] for c in text if c in self.vocab]

    def decode(self, ids: Sequence[int]) -> str:
        return "".join(self.inverse.get(i, "") for i in ids)

    def compression(self, text: str) -> float:
        return 1.0


CORPUS = """
the cat sat on the mat and the cat ate the rat that ran across the floor.
a dog sat on a log while the dog watched the cat and the cat watched the dog.
the rat ran to the mat and the cat ran after the rat through the open door.
a bird sat on the log singing and the bird saw the dog sleeping in the sun.
the mat was flat and the log was round and the rat was fast but the cat was faster.
the dog ate the bone and the cat ate the fish and the bird ate the yellow seed.
morning came and the farmer opened the gate and counted 12 sheep and 3 goats.
the children walked to school along the river carrying books and lunch boxes.
rain fell on the roof all night and the river rose above the old stone bridge.
the baker made bread at 5 in the morning and the smell filled the whole street.
a letter arrived from the city asking about the price of wheat and of barley.
the horses stood quietly in the field while the wind moved through the grass.
she read the book twice and wrote her name inside the cover with a blue pen.
they built a small house near the water with a red door and a wooden floor.
the fire burned low and the room grew cold and somebody closed the window.
he counted the coins on the table: 7 silver, 21 copper, and 1 gold piece.
""" * 8


def _demo() -> None:
    print("=" * 74)
    print("TOKENIZER — the integers a model actually sees")
    print("=" * 74)

    print("\n1. Merges, learned in order")
    print("-" * 74)
    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, vocabulary_size=300, verbose=True)
    print(f"    ... {tokenizer.stats['merges_learned']} merges, "
          f"vocabulary {tokenizer.size}")
    print("  Frequent pairs merge first. `the` becomes one token because it")
    print("  appears constantly; a word seen twice stays as separate letters.")

    print("\n2. What a sentence becomes")
    print("-" * 74)
    for sentence in ("the cat sat on the mat",
                     "the dog saw the bird",
                     "an unfamiliar zebra"):
        pieces = [p for word in WORD.findall(sentence)
                  for p in tokenizer.encode_word(word)]
        ids = tokenizer.encode(sentence)
        print(f"  {sentence!r}")
        print(f"    -> {pieces}")
        print(f"    -> {len(ids)} ids, decoded back: "
              f"{tokenizer.decode(ids)!r}")
    print("  The last one has no merged tokens: nothing in it was frequent")
    print("  enough to learn. It still encodes, one character at a time, which")
    print("  is what 'no out-of-vocabulary' means in practice — unfamiliar text")
    print("  is not rejected, it is just EXPENSIVE.")

    print("\n3. Round-trip, exactly")
    print("-" * 74)
    sample = "the cat and the dog sat on the mat."
    assert tokenizer.decode(tokenizer.encode(sample)) == sample
    print(f"  decode(encode(x)) == x for {sample!r}")
    print("  Not a formality. A tokeniser that loses whitespace or drops a")
    print("  character produces a model that generates text it cannot read")
    print("  back, and the symptom appears hundreds of steps into training.")

    print("\n4. Vocabulary size against sequence length")
    print("-" * 74)
    print(f"    {'vocabulary':>11}{'merges':>9}{'tokens':>9}"
          f"{'chars/token':>13}{'attention cost':>16}")
    baseline = None
    text = "the cat sat on the mat and the dog saw the bird on the log."
    characters = CharTokenizer(CORPUS)
    print(f"    {characters.size:>11}{0:>9}"
          f"{len(characters.encode(text)):>9}{1.0:>13.2f}"
          f"{'1.00x':>16}")
    baseline = len(characters.encode(text))
    for size in (80, 150, 300, 600):
        t = BPETokenizer()
        t.train(CORPUS, vocabulary_size=size)
        n = len(t.encode(text))
        print(f"    {t.size:>11}{len(t.merges):>9}{n:>9}"
              f"{t.compression(text):>13.2f}"
              f"{f'{(n / baseline) ** 2:.2f}x':>16}")
    print("  The last column is the one to care about: attention is QUADRATIC")
    print("  in sequence length, so halving the tokens quarters the attention")
    print("  cost. That is why nobody trains a character-level model at scale —")
    print("  not because characters are a worse representation, but because")
    print("  they are four to five times as many of them.")

    print("\n5. Two ways text can be expensive, and one way it can be lost")
    print("-" * 74)
    print(f"    {'text':<32}{'tokens':>8}{'chars/token':>13}{'round-trips?':>14}")
    for label, sample in (
            ("in-distribution English", "the cat sat on the mat"),
            ("English, unfamiliar words", "the quantum flux capacitor"),
            ("digits", "1234567890"),
            ("punctuation", "!!! ??? ... --- ,,,"),
            ("outside the alphabet", "cafe\u0301 na\u00efve \u4f60\u597d")):
        ids = tokenizer.encode(sample)
        exact = tokenizer.decode(ids) == sample
        print(f"    {label:<32}{len(ids):>8}"
              f"{len(sample) / max(1, len(ids)):>13.2f}"
              f"{('yes' if exact else 'NO — lost'):>14}")
    print("  Two different problems in that table. Unfamiliar English is")
    print("  EXPENSIVE — no merges apply, so it costs one token per character,")
    print("  which is why the same sentence can cost several times more in a")
    print("  language the merge table was not trained on.")
    print("  The last three rows are worse: those characters were never in")
    print("  the training alphabet — this corpus contains the digits 1, 2, 3,")
    print("  5 and 7 but not 4, 6, 8, 9 or 0 — so they are DROPPED and the")
    print("  round trip silently fails.")
    print("  That is the exact failure real tokenisers avoid by working on")
    print("  BYTES rather than characters — there are only 256 of them, every")
    print("  one is in the alphabet, and nothing can ever be unrepresentable.")
    print("  It is the single most important detail this implementation skips.")

    print("\n6. The merge ORDER is part of the model")
    print("-" * 74)
    word = " the"
    correct = tokenizer.encode_word(word)
    scrambled = BPETokenizer()
    scrambled.vocab = dict(tokenizer.vocab)
    scrambled.merges = list(reversed(tokenizer.merges))
    scrambled.ranks = {p: i for i, p in enumerate(scrambled.merges)}
    scrambled.inverse = dict(tokenizer.inverse)
    print(f"  {word!r} with the learned merge order:  {correct}")
    print(f"  {word!r} with the order reversed:       "
          f"{scrambled.encode_word(word)}")
    print("  Same vocabulary, same merges, different ORDER, different tokens.")
    print("  A model trained against one ordering cannot read the other, which")
    print("  is why the merge list ships with the weights rather than being")
    print("  regenerated — and why `encode_word` picks the lowest-RANK pair")
    print("  present rather than the leftmost one.")

    print("\n" + "=" * 74)
    print("Next: attention.py, which is what reads these ids.")
    print("=" * 74)


if __name__ == "__main__":
    _demo()
