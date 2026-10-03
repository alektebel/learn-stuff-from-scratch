"""
digits — the dataset. PROVIDED; you do not implement this one.

MNIST is a 45 MB download and this repo runs offline with no numpy, so this
generates an MNIST-SHAPED dataset instead: 8x8 greyscale glyphs for the digits
0-9, with per-sample jitter, stroke-thickness variation and noise.

It is not MNIST. It is small enough to train in pure Python in seconds, hard
enough that a linear model does noticeably worse than an MLP, and structured
enough that a generative model's samples are recognisable as digits — which is
the property that makes generative.py worth running at all.

Everything a real loader does is here and worth reading:

    a fixed train/test SPLIT, because the number that matters is accuracy on
    data the model has never seen

    NORMALISATION to roughly zero mean and unit variance, because a network
    whose inputs are all in [0, 255] has a first layer that has to learn to
    undo the scale before it can learn anything else

    SHUFFLING per epoch, because a loader that always presents digits in the
    same order lets the model fit the order

    a `noise` knob, so you can watch every model in this directory degrade and
    find out which ones degrade gracefully
"""

import random
from typing import Iterator, List, Sequence, Tuple

# 8x8 templates. Deliberately hand-drawn rather than generated, so that the
# confusions a model makes are the ones a person would predict: 3 with 8, 4
# with 9, 5 with 6.
GLYPHS = {
    0: ["  ####  ", " ##  ## ", "##    ##", "##    ##", "##    ##", "##    ##",
        " ##  ## ", "  ####  "],
    1: ["   ##   ", "  ###   ", " ####   ", "   ##   ", "   ##   ", "   ##   ",
        "   ##   ", " ###### "],
    2: [" ###### ", "##    ##", "      ##", "     ## ", "   ##   ", "  ##    ",
        " ##     ", "########"],
    3: [" ###### ", "##    ##", "      ##", "   #### ", "      ##", "      ##",
        "##    ##", " ###### "],
    4: ["     ## ", "    ### ", "   #### ", "  ## ## ", " ##  ## ",
        "########", "     ## ", "     ## "],
    5: ["########", "##      ", "##      ", "####### ", "      ##", "      ##",
        "##    ##", " ###### "],
    6: ["  ##### ", " ##     ", "##      ", "####### ", "##    ##", "##    ##",
        "##    ##", " ###### "],
    7: ["########", "##    ##", "     ## ", "    ##  ", "   ##   ", "  ##    ",
        "  ##    ", "  ##    "],
    8: [" ###### ", "##    ##", "##    ##", " ###### ", "##    ##", "##    ##",
        "##    ##", " ###### "],
    9: [" ###### ", "##    ##", "##    ##", " #######", "      ##", "     ## ",
        "   ###  ", " ###    "],
}

WIDTH = HEIGHT = 8
PIXELS = WIDTH * HEIGHT


def _render(digit: int, rng: random.Random, noise: float) -> List[float]:
    glyph = GLYPHS[digit]
    shift_x = rng.choice([-1, 0, 0, 1])
    shift_y = rng.choice([-1, 0, 0, 1])
    ink = rng.uniform(0.75, 1.0)

    pixels = [0.0] * PIXELS
    for y, row in enumerate(glyph):
        for x, character in enumerate(row.ljust(WIDTH)[:WIDTH]):
            if character == " ":
                continue
            ty, tx = y + shift_y, x + shift_x
            if 0 <= ty < HEIGHT and 0 <= tx < WIDTH:
                pixels[ty * WIDTH + tx] = ink
    if noise:
        pixels = [min(1.0, max(0.0, p + rng.gauss(0.0, noise))) for p in pixels]
    return pixels


def make_dataset(n: int = 1200, noise: float = 0.12, seed: int = 0,
                 digits: Sequence[int] = tuple(range(10))
                 ) -> Tuple[List[List[float]], List[int]]:
    rng = random.Random(seed)
    xs, ys = [], []
    for i in range(n):
        digit = digits[i % len(digits)]
        xs.append(_render(digit, rng, noise))
        ys.append(digit)
    order = list(range(n))
    rng.shuffle(order)
    return [xs[i] for i in order], [ys[i] for i in order]


def split(xs: List[List[float]], ys: List[int], test_fraction: float = 0.25):
    """A FIXED split. Every number that matters is measured on data the model
    has never been trained on, and reshuffling the split between experiments is
    how people accidentally report their best random seed."""
    cut = int(len(xs) * (1 - test_fraction))
    return (xs[:cut], ys[:cut]), (xs[cut:], ys[cut:])


def normalize(xs: List[List[float]]) -> List[List[float]]:
    """Zero mean, unit variance, computed over the WHOLE dataset.

    Strictly this should use training-set statistics only and apply them to the
    test set — using test statistics is a mild form of leakage. It is called
    out here rather than silently done right, because the leakage version is
    the one people write, and knowing the distinction is the point.
    """
    total = sum(sum(row) for row in xs)
    count = len(xs) * len(xs[0])
    mean = total / count
    variance = sum((v - mean) ** 2 for row in xs for v in row) / count
    std = max(variance ** 0.5, 1e-6)
    return [[(v - mean) / std for v in row] for row in xs]


def batches(xs: List[List[float]], ys: List[int], size: int,
            rng: random.Random) -> Iterator[Tuple[List[List[float]], List[int]]]:
    """Shuffle, then yield batches. The shuffle is per epoch and it matters:
    present the classes in a fixed order and the model can fit the ORDER."""
    order = list(range(len(xs)))
    rng.shuffle(order)
    for start in range(0, len(order) - size + 1, size):
        chunk = order[start:start + size]
        yield [xs[i] for i in chunk], [ys[i] for i in chunk]


def render(pixels: Sequence[float], threshold: float = 0.35) -> str:
    """Print an 8x8 image as ASCII. Looking at your data is not optional, and
    it is how you find out that your labels are shifted by one."""
    shades = " .:-=+*#%@"
    lowest, highest = min(pixels), max(pixels)
    span = max(highest - lowest, 1e-9)
    lines = []
    for y in range(HEIGHT):
        row = ""
        for x in range(WIDTH):
            value = (pixels[y * WIDTH + x] - lowest) / span
            row += shades[min(len(shades) - 1, int(value * len(shades)))] * 2
        lines.append(row)
    return "\n".join(lines)


def side_by_side(images: Sequence[Sequence[float]], labels: Sequence[str] = ()
                 ) -> str:
    blocks = [render(image).splitlines() for image in images]
    out = []
    for row in range(HEIGHT):
        out.append("   ".join(block[row] for block in blocks))
    if labels:
        out.append("   ".join(str(label).center(WIDTH * 2) for label in labels))
    return "\n".join(out)


def _demo() -> None:
    print("=" * 70)
    print("digits — an MNIST-shaped dataset that fits in a Python file")
    print("=" * 70)

    xs, ys = make_dataset(20, noise=0.0, seed=1)
    print("\nClean glyphs:")
    print(side_by_side([_render(d, random.Random(0), 0.0) for d in range(5)],
                       list(range(5))))
    print(side_by_side([_render(d, random.Random(0), 0.0) for d in range(5, 10)],
                       list(range(5, 10))))

    print("\nWith the jitter and noise a model actually sees (noise=0.12):")
    rng = random.Random(3)
    print(side_by_side([_render(3, rng, 0.12) for _ in range(5)], ["3"] * 5))

    xs, ys = make_dataset(1200, noise=0.12, seed=0)
    (train_x, train_y), (test_x, test_y) = split(xs, ys)
    print(f"\n  {len(train_x)} train, {len(test_x)} test, "
          f"{PIXELS} features, {len(set(ys))} classes")
    print(f"  class balance in train: "
          f"{[train_y.count(d) for d in range(10)]}")

    raw_mean = sum(sum(r) for r in train_x) / (len(train_x) * PIXELS)
    normed = normalize(train_x)
    norm_mean = sum(sum(r) for r in normed) / (len(normed) * PIXELS)
    print(f"\n  mean pixel before normalisation {raw_mean:.4f}, "
          f"after {norm_mean:.2e}")
    print("  A first layer fed values all in [0, 1] with mean 0.3 has to learn")
    print("  to undo that offset before it can learn anything else. It can —")
    print("  through the bias — but it spends the early steps doing it.")

    print("\n  Noise levels, and what the digit still looks like:")
    for noise in (0.0, 0.15, 0.35, 0.6):
        print(f"\n  noise={noise}")
        print(side_by_side([_render(d, random.Random(5), noise)
                            for d in (0, 3, 8)], [0, 3, 8]))
    print("\n  At 0.6 a person can barely read them either. Any accuracy your")
    print("  model reports there is worth checking against that.")

    print("\n" + "=" * 70)
    print("Next: train.py fits a classifier to this.")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
