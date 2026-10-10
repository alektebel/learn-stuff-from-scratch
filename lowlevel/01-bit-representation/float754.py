"""IEEE-754 binary32 / binary64 as bit patterns, via `struct`.

The material is CS:APP (Bryant & O'Hallaron), chapter 2, section 2.4, "Floating Point".
The chapter's point is that a float is three fields packed into one word - sign,
exponent (biased) and fraction - and that special values are not exceptions but ordinary
field patterns: exponent all zero means a *subnormal* (no implicit leading 1), exponent
all ones means infinity (fraction zero) or a NaN (fraction nonzero).

DESIGN DECISION - reimplement the fields, or let `struct` do the conversion?
Re-deriving the value from sign/exponent/fraction is the chapter's exercise, but it is a
lossy re-encode once you are back in a Python float: the payload of a NaN and the sign of
a zero do not survive arithmetic. **Chosen: `struct` moves the bytes in both directions,
and the fields are decoded separately for inspection.** The cost is that the byte order
must be pinned explicitly; that is itself checkable, and a wrong endianness is a planted
bug in `_build/mutations.py`.

DESIGN DECISION - strict round-trip for every pattern, or just true values?
Comparing decoded floats with `==` is wrong for NaN (never equal) and hides -0.0 (+0.0 ==
-0.0). **Chosen: compare the *bit patterns* after a round-trip** - the only representation
that distinguishes -0.0 from +0.0 and a signaling NaN from a quiet one. Payload equality
is required for finite values, infinities and zeros; for NaNs the sign and the quiet /
signaling class are what must survive, because the C conversion behind `struct` is only
promised to preserve those.

    python3 float754.py      # prints the measurements this file promises
"""

import math
import struct

#: fmt -> (total bits, exponent bits, fraction bits, exponent bias)
_SHAPES = {
    "f": (32, 8, 23, 127),      # binary32, C `float`
    "d": (64, 11, 52, 1023),    # binary64, C `double` / Python `float`
}


def _shape(fmt: str) -> tuple[int, int, int, int]:
    """(total, exponent, fraction, bias) for 'f' or 'd', or raise ValueError."""
    try:
        return _SHAPES[fmt]
    except KeyError:
        raise ValueError(f"unknown float format {fmt!r}; use 'f' (binary32) or 'd' (binary64)")


def _size(fmt: str) -> int:
    """Width in bytes of format `fmt` ('f' -> 4, 'd' -> 8)."""
    return _shape(fmt)[0] // 8


def float_to_bits(value: float, fmt: str = "d") -> int:
    """Encode a Python float as the unsigned bit pattern of an IEEE-754 `fmt`.

    The value is packed little-endian (so the raw bytes do not depend on the host) and
    read back as an integer, the representation the other functions inspect.
    """
    # TODO: Pack `value` with struct in format '<f' or '<d', then read the bytes as a little-endian unsigned integer.
    raise NotImplementedError("float_to_bits")


def bits_to_float(bits: int, fmt: str = "d") -> float:
    """Decode an unsigned IEEE-754 `fmt` bit pattern into a Python float.

    `bits` must be a valid pattern in [0, 2**width). Decoding a *subnormal* returns the
    true tiny value, never 0.0: exponent zero with a nonzero fraction is a real number.
    """
    # TODO: Check `bits` is a valid pattern, turn it into bytes little-endian, and struct.unpack '<f' or '<d'. Subnormals stay nonzero.
    raise NotImplementedError("bits_to_float")


def sign_of_bits(bits: int, fmt: str = "d") -> int:
    """The sign bit (0 or 1) of a float pattern. 1 means negative, even for -0.0."""
    # TODO: The top bit of the pattern: `(bits >> (total_bits - 1)) & 1`.
    raise NotImplementedError("sign_of_bits")


def classify_bits(bits: int, fmt: str = "d") -> str:
    """Name the class of a float pattern from its fields alone.

    One of: "zero", "negative zero", "subnormal", "negative subnormal", "normal",
    "negative normal", "infinity", "negative infinity", "quiet nan", "signaling nan".
    The two NaN kinds differ in the *quiet bit*, the top bit of the fraction: a quiet
    NaN has it set, a signaling NaN has it clear and a nonzero payload.
    """
    # TODO: Split into sign, exponent (next `ebits`) and fraction (low `fbits`). exp all ones -> inf/NaN (quiet if the top fraction bit is set); exp zero -> zero or subnormal; else normal.
    raise NotImplementedError("classify_bits")


def nan_payload(bits: int, fmt: str = "d") -> int:
    """The fraction field of a NaN, or 0 if `bits` is not a NaN.

    The payload is what turns "some NaN" into a particular one; the quiet bit is part of
    the fraction, so a quiet NaN always has a payload >= 2**(fraction_bits - 1).
    """
    # TODO: The fraction field, but only when the exponent is all ones and the fraction is nonzero; otherwise 0.
    raise NotImplementedError("nan_payload")


if __name__ == "__main__":
    tiny32 = bits_to_float(1, "f")
    tiny64 = bits_to_float(1, "d")
    print(f"smallest binary32 subnormal: bits=0x1 -> {tiny32!r} "
          f"(re-encoded 0x{float_to_bits(tiny32, 'f'):X}); min normal {2.0 ** -126!r}")
    print(f"smallest binary64 subnormal: bits=0x1 -> {tiny64!r} "
          f"(re-encoded 0x{float_to_bits(tiny64, 'd'):X})")
    neg_zero = bits_to_float(1 << 63, "d")
    print(f"-0.0: value == 0.0 is {neg_zero == 0.0}, copysign is {math.copysign(1.0, neg_zero):+.0f}, "
          f"class {classify_bits(1 << 63, 'd')!r}")
    for name, bits in [("+inf", 0x7FF0000000000000), ("-inf", 0xFFF0000000000000),
                       ("qNaN", 0x7FF8000000000000), ("sNaN", 0x7FF0000000000001),
                       ("-qNaN payload 1", 0xFFF8000000000001)]:
        print(f"{name:>18}: class {classify_bits(bits, 'd'):>16}, "
              f"payload 0x{nan_payload(bits, 'd'):X}, "
              f"round-trips {float_to_bits(bits_to_float(bits, 'd'), 'd') == bits}")
