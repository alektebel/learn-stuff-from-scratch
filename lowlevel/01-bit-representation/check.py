"""
Progress checker for the bit-representation templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The references are the standard library itself - `int.to_bytes(signed=True)` for two's
complement and `struct.pack/unpack` for floats - plus hand-computed bit patterns for the
cases where the reference and the learner would share a mistake.
"""

import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Steps 1-3: twos_complement.py
# ---------------------------------------------------------------------------

def check_twos_complement_roundtrip() -> None:
    from twos_complement import from_bits, to_bits

    rng = random.Random(0xB157)
    # Any width, against a reference computed arithmetically here: the sign bit is the
    # top bit, so a pattern >= 2**(width-1) stands for a negative value.
    for width in (1, 3, 7, 8, 12, 16, 31, 32, 33, 64, 65):
        mod = 1 << width
        for _ in range(150):
            bits = rng.randrange(mod)
            want = bits - mod if bits >= (1 << (width - 1)) else bits
            got = from_bits(bits, width)
            assert got == want, (
                f"from_bits({bits:#x}, {width}) = {got}, expected {want}: the sign bit is "
                f"bit {width - 1}, and a set sign bit means subtract 2**{width}")
            assert to_bits(got, width) == bits, (
                f"to_bits({got}, {width}) = {to_bits(got, width):#x}, expected {bits:#x}: "
                f"encoding must reduce modulo 2**{width}")
    # Byte-aligned widths must agree with int.to_bytes, the stdlib's two's complement.
    for width in (8, 16, 32, 64):
        nbytes = width // 8
        for _ in range(150):
            value = rng.randrange(-(1 << (width - 1)), 1 << (width - 1))
            assert to_bits(value, width).to_bytes(nbytes, "big") == \
                value.to_bytes(nbytes, "big", signed=True), (
                    f"to_bits({value}, {width}) disagrees with int.to_bytes(..., signed=True)")
            bits = rng.randrange(1 << width)
            assert from_bits(bits, width) == \
                int.from_bytes(bits.to_bytes(nbytes, "big"), "big", signed=True), (
                    f"from_bits({bits:#x}, {width}) disagrees with int.from_bytes(..., signed=True)")


def check_twos_complement_known_values() -> None:
    from twos_complement import from_bits, to_bits

    known = [
        (-1, 32, 0xFFFFFFFF),
        (0, 32, 0x00000000),
        (1, 32, 0x00000001),
        (0x7FFFFFFF, 32, 0x7FFFFFFF),
        (-0x80000000, 32, 0x80000000),
        (-1, 8, 0xFF),
        (-128, 8, 0x80),
        (127, 8, 0x7F),
        (-1, 64, 0xFFFFFFFFFFFFFFFF),
        (-1, 1, 1),
        (0, 1, 0),
    ]
    for value, width, pattern in known:
        got = to_bits(value, width)
        assert got == pattern, (
            f"to_bits({value}, {width}) = {got:#x}, expected {pattern:#x}: the pattern is the "
            f"low {width} bits of the value")
        assert from_bits(pattern, width) == value, (
            f"from_bits({pattern:#x}, {width}) = {from_bits(pattern, width)}, expected {value}")
    assert from_bits(0xFFFFFFFF, 32) == -1, (
        "0xFFFFFFFF decoded to something other than -1 in i32: the top bit is the sign, "
        "so the value is 0xFFFFFFFF - 2**32")
    assert to_bits(from_bits(0x80000000, 32), 32) == 0x80000000, (
        "the i32 minimum 0x80000000 did not round-trip: it is INT_MIN (-2**31), not +2**31")


def check_overflow_wraps_and_guarded_add() -> None:
    from twos_complement import add_checked, add_wrap

    assert add_wrap(0x7F, 1, 8) == -128, (
        f"signed 8-bit 127 + 1 = {add_wrap(0x7F, 1, 8)}, expected -128: overflow WRAPS, "
        "the carry out of the top bit is discarded")
    assert add_wrap(-128, -1, 8) == 127, (
        f"8-bit -128 + -1 = {add_wrap(-128, -1, 8)}, expected 127 (wrap on underflow)")
    assert add_wrap(0x7FFFFFFF, 1, 32) == -0x80000000, "32-bit 0x7FFFFFFF + 1 must wrap to -0x80000000"
    assert add_wrap(7, 1, 4) == -8, "4-bit 7 + 1 must wrap to -8"
    assert add_wrap(-8, -1, 4) == 7
    # The guarded add is a *different* contract: it must raise where add_wrap wraps.
    overflowing = [(127, 1, 8), (-128, -1, 8), (0x7FFFFFFF, 1, 32),
                   (-0x80000000, -1, 32), (100, 100, 8)]
    for a, b, width in overflowing:
        try:
            result = add_checked(a, b, width)
        except OverflowError:
            continue
        raise AssertionError(
            f"add_checked({a}, {b}, {width}) returned {result} instead of raising: the "
            "guarded add must flag overflow, only add_wrap may wrap silently")
    assert add_checked(3, 4, 8) == 7
    assert add_checked(-128, 127, 8) == -1
    assert add_checked(0x7FFFFFFF, -1, 32) == 0x7FFFFFFE
    assert add_checked(-0x80000000, 0x7FFFFFFF, 32) == -1


# ---------------------------------------------------------------------------
# Steps 4-6: float754.py
# ---------------------------------------------------------------------------

def check_float_roundtrip_vs_struct() -> None:
    import struct

    from float754 import bits_to_float, classify_bits, float_to_bits, sign_of_bits

    rng = random.Random(0xF10A7)
    for fmt, size, nbits in (("f", 4, 32), ("d", 8, 64)):
        for _ in range(600):
            bits = rng.randrange(1 << nbits)
            got = bits_to_float(bits, fmt)
            ref = struct.unpack("<" + fmt, bits.to_bytes(size, "little"))[0]
            if ref != ref:  # NaN: == is always False, compare the class instead
                assert got != got, f"{fmt}: NaN pattern {bits:#x} decoded to the non-NaN {got!r}"
                back = float_to_bits(got, fmt)
                assert classify_bits(back, fmt) == classify_bits(bits, fmt) \
                    and sign_of_bits(back, fmt) == sign_of_bits(bits, fmt), (
                        f"{fmt}: NaN {bits:#x} came back as {back:#x}: the sign or the "
                        "quiet/signaling class changed (check the byte order)")
            else:
                assert got == ref, f"{fmt}: pattern {bits:#x} decoded to {got!r}, struct says {ref!r}"
                back = float_to_bits(got, fmt)
                assert back == bits, (
                    f"{fmt}: {bits:#x} -> {got!r} -> {back:#x}: the round-trip changed the bits "
                    "(check the byte order and that you are not recomputing the value)")
        # Hand-computed patterns, so a shared bug in the code cannot hide behind struct.
        table = ([(1.0, 0x3F800000), (-1.0, 0xBF800000), (2.0, 0x40000000)]
                 if fmt == "f" else
                 [(1.0, 0x3FF0000000000000), (-1.0, 0xBFF0000000000000), (2.0, 0x4000000000000000)])
        for value, expect in table:
            got = float_to_bits(value, fmt)
            assert got == expect, (
                f"{fmt}: float_to_bits({value!r}) = {got:#x}, expected {expect:#x}: the "
                "layout is [-1 sign][8 or 11 exponent, biased][rest fraction]")


def check_special_values() -> None:
    import math

    from float754 import bits_to_float, classify_bits, float_to_bits, nan_payload, sign_of_bits

    neg_zero = bits_to_float(1 << 63, "d")
    assert neg_zero == 0.0 and math.copysign(1.0, neg_zero) == -1.0, (
        "-0.0 lost its sign: == cannot see it, so inspect the sign bit or use math.copysign")
    assert float_to_bits(neg_zero, "d") == (1 << 63), (
        "-0.0 did not re-encode to 0x8000000000000000: the sign bit was dropped")
    assert sign_of_bits(1 << 63, "d") == 1 and sign_of_bits(0, "d") == 0

    for fmt, pos_inf, neg_inf, qnan, snan, frac_bits in (
        ("f", 0x7F800000, 0xFF800000, 0x7FC00000, 0x7F800001, 23),
        ("d", 0x7FF0000000000000, 0xFFF0000000000000,
         0x7FF8000000000000, 0x7FF0000000000001, 52),
    ):
        pinf, ninf = bits_to_float(pos_inf, fmt), bits_to_float(neg_inf, fmt)
        assert math.isinf(pinf) and pinf > 0 and math.isinf(ninf) and ninf < 0, (
            f"{fmt}: infinity did not survive (got {pinf!r} and {ninf!r})")
        assert float_to_bits(pinf, fmt) == pos_inf and float_to_bits(ninf, fmt) == neg_inf

        q = bits_to_float(qnan, fmt)
        assert math.isnan(q) and classify_bits(qnan, fmt) == "quiet nan", (
            f"{fmt}: 0x{qnan:x} must classify as a quiet NaN (exponent all ones, fraction nonzero)")
        assert float_to_bits(q, fmt) == qnan, f"{fmt}: quiet NaN did not round-trip"
        assert classify_bits(snan, fmt) == "signaling nan", (
            f"{fmt}: the quiet bit is the TOP bit of the fraction (0x{qnan:x} has it set); "
            "clearing it gives a signaling NaN, not the other way round")
        assert nan_payload(qnan, fmt) == (1 << (frac_bits - 1)), (
            f"{fmt}: the payload of 0x{qnan:x} is its fraction field")
        assert nan_payload(snan, fmt) == 1
        assert float_to_bits(bits_to_float(snan, fmt), fmt) == snan, (
            f"{fmt}: signaling NaN bits did not survive the round-trip")

    neg_nan = 0xFFF8000000000001
    v = bits_to_float(neg_nan, "d")
    assert math.isnan(v) and sign_of_bits(neg_nan, "d") == 1 and nan_payload(neg_nan, "d") == 0x8000000000001
    assert float_to_bits(v, "d") == neg_nan, "a negative quiet NaN lost its sign or payload"
    assert classify_bits(0, "d") == "zero" and classify_bits(1 << 63, "d") == "negative zero"
    assert classify_bits(0x3FF0000000000000, "d") == "normal"
    assert classify_bits(0xBFF0000000000000, "d") == "negative normal"


def check_denormal_not_flushed() -> None:
    from float754 import bits_to_float, classify_bits, float_to_bits

    min_normal_f = 2.0 ** -126
    tiny_f = bits_to_float(1, "f")
    assert tiny_f != 0.0, (
        "the smallest binary32 subnormal decoded to 0.0: a subnormal is a real number, "
        "not zero - flushing it to zero is the bug this step exists for")
    assert 0.0 < tiny_f < min_normal_f
    assert float_to_bits(tiny_f, "f") == 1, (
        "the smallest binary32 subnormal did not re-encode to 0x00000001: it was flushed or rounded")
    assert classify_bits(1, "f") == "subnormal", (
        "a pattern with exponent 0 and a nonzero fraction is a subnormal, not zero")
    largest_f = bits_to_float(0x007FFFFF, "f")
    assert 0.0 < largest_f < min_normal_f and float_to_bits(largest_f, "f") == 0x007FFFFF, (
        "the largest binary32 subnormal did not survive: the boundary with the smallest "
        "normal is the easy place to be off by a factor of 2")
    assert classify_bits(0x00800000, "f") == "normal", "2**-126 is the smallest NORMAL, not subnormal"

    tiny_d = bits_to_float(1, "d")
    assert tiny_d != 0.0 and float_to_bits(tiny_d, "d") == 1, (
        "the smallest binary64 subnormal (0x0000000000000001) did not survive a round-trip")
    assert classify_bits(1, "d") == "subnormal"
    assert classify_bits(0x000FFFFFFFFFFFFF, "d") == "subnormal"
    assert classify_bits(0x0010000000000000, "d") == "normal"
    assert float_to_bits(bits_to_float(0x000FFFFFFFFFFFFF, "d"), "d") == 0x000FFFFFFFFFFFFF


# ---------------------------------------------------------------------------
# Steps 7-8: endianness.py
# ---------------------------------------------------------------------------

def check_endianness_and_host_order() -> None:
    import struct

    from endianness import (from_big_endian, from_little_endian, host_byteorder,
                            swap_byteorder, to_big_endian, to_little_endian)

    assert host_byteorder() in ("little", "big")
    assert host_byteorder() == sys.byteorder, (
        f"host_byteorder() says {host_byteorder()!r} but the interpreter reports "
        f"{sys.byteorder!r}: pack the integer 1 in native '@I' order and read its first byte")
    native = struct.pack("@I", 1)
    assert (native[0] == 1) == (host_byteorder() == "little"), (
        "the detector does not agree with the bytes it is supposed to measure")

    rng = random.Random(0xE4D1A)
    for width in (1, 2, 4, 8):
        for _ in range(120):
            value = rng.randrange(1 << (8 * width))
            les = to_little_endian(value, width)
            bes = to_big_endian(value, width)
            assert len(les) == width and len(bes) == width, "the byte count must be exactly width"
            assert from_little_endian(les) == value, "little-endian round-trip failed"
            assert from_big_endian(bes) == value, "big-endian round-trip failed"
            assert les == bes[::-1], (
                "the two orders of the same word are byte reversals of each other")
            assert swap_byteorder(bes) == les and swap_byteorder(les) == bes
    assert to_little_endian(0x01020304, 4) == b"\x04\x03\x02\x01", (
        "little-endian puts the LEAST significant byte first")
    assert to_big_endian(0x01020304, 4) == b"\x01\x02\x03\x04", (
        "big-endian puts the MOST significant byte first")
    assert from_little_endian(b"\x04\x03\x02\x01") == 0x01020304
    assert from_big_endian(b"\x01\x02\x03\x04") == 0x01020304
    assert from_little_endian(b"\x01") == from_big_endian(b"\x01") == 1, (
        "a single byte has no byte order")


def check_hex_dump_known_values() -> None:
    from endianness import from_big_endian, hex_dump, to_big_endian, to_little_endian
    from twos_complement import from_bits, to_bits

    assert hex_dump(b"") == ""
    assert hex_dump(b"\x00") == "00"
    assert hex_dump(b"\x0f") == "0f", "a byte below 0x10 needs a leading zero: 'f' is ambiguous"
    assert hex_dump(b"\xff\xff\xff\xff") == "ff ff ff ff", (
        f"got {hex_dump(b'\\xff\\xff\\xff\\xff')!r}: lowercase, two digits per byte, single spaces")
    assert hex_dump(b"\xde\xad\xbe\xef") == b"\xde\xad\xbe\xef".hex(" "), (
        "the dump should match the standard library's spaced hex")
    assert to_bits(-1, 32) == 0xFFFFFFFF, "to_bits(-1, 32) must be 0xFFFFFFFF"
    assert hex_dump(to_big_endian(0xFFFFFFFF, 4)) == "ff ff ff ff", (
        "-1 as i32 is all ones in every byte order")
    assert hex_dump(to_little_endian(0x01020304, 4)) == "04 03 02 01"
    assert hex_dump(to_big_endian(0x01020304, 4)) == "01 02 03 04"
    assert from_bits(from_big_endian(bytes.fromhex("ffffffff")), 32) == -1, (
        "0xFFFFFFFF read from a big-endian file is -1 in i32")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("twos_complement.py", "two's-complement round-trip, any width", check_twos_complement_roundtrip),
    ("twos_complement.py", "known values: 0xFFFFFFFF is -1 in i32", check_twos_complement_known_values),
    ("twos_complement.py", "overflow wraps; guarded add flags it", check_overflow_wraps_and_guarded_add),
    ("float754.py", "binary32/binary64 round-trip vs struct", check_float_roundtrip_vs_struct),
    ("float754.py", "-0.0, infinities and NaN sign/payload class", check_special_values),
    ("float754.py", "a denormal is not flushed to zero", check_denormal_not_flushed),
    ("endianness.py", "little/big endian and host-order detector", check_endianness_and_host_order),
    ("endianness.py", "hex dump of known values", check_hex_dump_known_values),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}Bits: integers, floats, endianness — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<18} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<18} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<18} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you can read bytes on any machine.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
