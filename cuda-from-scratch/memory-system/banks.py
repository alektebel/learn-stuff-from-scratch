"""
Shared-memory bank conflicts — the serialisation degree
=======================================================

Source: NVIDIA's matrix-transpose post (shared-memory bank conflicts), restated.

Shared memory is fast because it is split into 32 banks, each 4 bytes wide and able to
serve one 4-byte word per cycle. Bank = word_index % 32. In one warp instruction, if two
threads hit the same bank but *different* words, those accesses serialise: the request
takes as many cycles as the worst bank has distinct words. If every thread in a bank asks
for the *same* word, the hardware broadcasts it in one cycle — that is not a conflict.

The classic case: a 32x32 float tile in row-major shared memory. A row read is
conflict-free (thread c hits bank c). A column read has each thread r read word
r*32 + col, and r*32 % 32 == 0, so all 32 threads land in bank `col` on 32 different
words: a 32-way conflict, 32 cycles for one instruction. Adding one padding word per row
makes the stride 33, so bank = (r*33 + col) % 32 = (r + col) % 32, all distinct.

DESIGN DECISION — degree as a maximum, not a count of duplicates?
You could sum the extra accesses across banks, but the cost of one warp instruction is set
by its *slowest* bank: the other banks idle. A pattern with 32 two-way banks costs 2
cycles, not 64. Chosen: serialisation degree = max over banks of the number of distinct
words requested from that bank. 0 for an empty access, 1 for conflict-free.

DESIGN DECISION — broadcast counts as conflict-free?
Hardware really does broadcast a repeated address within a bank; treating it as a conflict
would overstate the cost of reductions and shuffle-style reads. The distinction is same
word (broadcast, 1) versus same bank, different word (conflict). Chosen: distinct words
per bank.
"""

BANKS = 32
WARP = 32


def bank_of(word_index, num_banks=BANKS):
    """The shared-memory bank for a 4-byte word index."""
    # TODO: Shared memory has 32 banks, each 4 bytes: bank = word_index % 32.
    raise NotImplementedError("bank_of")


def serialisation_degree(word_indices, num_banks=BANKS):
    """Cycles one warp shared-memory instruction costs: max distinct words per bank."""
    # TODO: Group threads by bank, keep the set of DISTINCT word indices per bank, return the largest set. Same word twice is a broadcast, not a conflict.
    raise NotImplementedError("serialisation_degree")


def is_conflict_free(word_indices, num_banks=BANKS):
    """True when the access completes in a single cycle."""
    # TODO: Conflict-free means the degree is 1: every bank serves at most one word.
    raise NotImplementedError("is_conflict_free")


def tile_word_index(row, col, width, pad=0):
    """Word index of element (row, col) in a row-major tile with `pad` filler words per row."""
    # TODO: Row-major with padding: row * (width + pad) + col.
    raise NotImplementedError("tile_word_index")


def row_words(row, cols, pad=0):
    """The word indices one warp reads for a full row of a cols-wide tile."""
    # TODO: Walk c from 0 to cols-1 at a fixed row; width is cols so padding shifts the row start.
    raise NotImplementedError("row_words")


def column_words(col, rows, width, pad=0):
    """The word indices one warp reads for a full column of a rows x width tile."""
    # TODO: Walk r from 0 to rows-1 at a fixed column, with the tile's real width and pad.
    raise NotImplementedError("column_words")


def tile_words(rows, cols, pad=0):
    """Total words a rows x cols tile occupies with `pad` filler words per row."""
    # TODO: A padded rows x cols tile holds rows * (cols + pad) words.
    raise NotImplementedError("tile_words")


def _demo():
    cases = (
        ("row of 32x32", row_words(0, 32)),
        ("column of 32x32", column_words(0, 32, 32)),
        ("column, padded to 33", column_words(0, 32, 32, pad=1)),
        ("broadcast (same word x32)", [5] * 32),
        ("two words in bank 5", [5, 37] * 16),
    )
    print(f"{'access':<30}{'degree':>7}")
    for name, words in cases:
        print(f"{name:<30}{serialisation_degree(words):>7}")
    extra = tile_words(32, 32, 1) - tile_words(32, 32, 0)
    print(f"padding a 32x32 tile costs {extra} words "
          f"({extra * 4} bytes, {(tile_words(32, 32, 1) / tile_words(32, 32, 0) - 1) * 100:.2f}% more)")


if __name__ == "__main__":
    _demo()
