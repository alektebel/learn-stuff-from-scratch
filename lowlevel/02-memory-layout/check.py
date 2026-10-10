"""
Progress checker for the memory-layout templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 3 6       # run steps 3 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The oracle is the C compiler's own ABI, reached through ctypes (an independent stdlib
implementation of the LP64 data model), plus python's `struct` for byte strings.
"""

import ctypes
import itertools
import pathlib
import random
import shutil
import struct
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

# ---------------------------------------------------------------------------
# Independent oracle: the platform C ABI, via ctypes.
# ---------------------------------------------------------------------------

_CTYPES = {
    "char": ctypes.c_byte,
    "uchar": ctypes.c_ubyte,
    "short": ctypes.c_short,
    "ushort": ctypes.c_ushort,
    "int": ctypes.c_int,
    "uint": ctypes.c_uint,
    "long": ctypes.c_long,
    "ulong": ctypes.c_ulong,
    "longlong": ctypes.c_longlong,
    "ulonglong": ctypes.c_ulonglong,
    "float": ctypes.c_float,
    "double": ctypes.c_double,
    "pointer": ctypes.c_void_p,
    "longdouble": ctypes.c_longdouble,
}

_FMT = {
    "char": "b", "uchar": "B", "short": "h", "ushort": "H", "int": "i", "uint": "I",
    "long": "q", "ulong": "Q", "longlong": "q", "ulonglong": "Q",
    "float": "f", "double": "d", "pointer": "Q",
}

_SCALARS = ["char", "short", "int", "long", "float", "double", "pointer"]


def _align_up(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def _abi(fields):
    """(sizeof, {name: offset}, alignment) from the real compiler ABI."""
    cls = type("_S", (ctypes.Structure,), {"_fields_": [(n, _CTYPES[t]) for n, t in fields]})
    return ctypes.sizeof(cls), {n: getattr(cls, n).offset for n, _ in fields}, ctypes.alignment(cls)


# ---------------------------------------------------------------------------
# Steps 1-2: layout.py -- natural alignment
# ---------------------------------------------------------------------------

def check_natural_layout() -> None:
    from layout import offset_of, sizeof

    cases = [
        [("c", "char")],
        [("c", "char"), ("i", "int")],
        [("c", "char"), ("i", "int"), ("d", "char")],
        [("i", "int"), ("c", "char")],
        [("a", "char"), ("b", "short"), ("c", "int"), ("d", "long")],
        [("f", "float"), ("d", "double"), ("i", "int")],
        [("p", "pointer"), ("c", "char"), ("l", "long")],
    ]
    rng = random.Random(7)
    for _ in range(200):
        n = rng.randint(1, 6)
        cases.append([(f"f{i}", rng.choice(_SCALARS)) for i in range(n)])

    for fields in cases:
        got_size = sizeof(fields)
        size, offs, align = _abi(fields)
        assert got_size == size, (
            f"sizeof({fields}) = {got_size}, the ABI says {size}. Trailing padding must round the "
            f"struct up to its own alignment ({align}); the sum of the fields is not the size.")
        for name, _ in fields:
            got = offset_of(fields, name)
            assert got == offs[name], (
                f"offset_of({fields}, {name!r}) = {got}, the ABI says {offs[name]}. Align each member "
                f"up to its own alignment before placing it.")
        # struct.calcsize cross-check: native `struct` inserts inter-field padding but no
        # trailing padding, so adding the trailing padding must reach our size exactly.
        native = struct.calcsize("@" + "".join(_FMT[t] for _, t in fields))
        assert got_size == _align_up(native, align), (
            f"sizeof({fields}) = {got_size}, but struct.calcsize says {native} + trailing padding to "
            f"alignment {align} = {_align_up(native, align)}.")


def check_nested_layout() -> None:
    from layout import Struct, offset_of, sizeof

    inner = Struct([("x", "char"), ("y", "int")])
    assert inner.size == 8 and inner.alignment == 4, (
        f"nested inner struct: size {inner.size} align {inner.alignment}, expected 8/4")
    outer = Struct([("a", "short"), ("in", inner), ("b", "char")])
    assert outer.alignment == 4, (
        f"a nested struct contributes its own alignment (max of its members); got {outer.alignment}, "
        "expected 4 (from the inner int)")
    assert outer.size == 16, (
        f"sizeof outer = {outer.size}, expected 16: the nested struct occupies 8 bytes at offset 4 "
        "(rounded up to alignment 4), then the trailing char, then padding to alignment 4")
    assert outer.offset("a") == 0 and outer.offset("in") == 4 and outer.offset("b") == 12, (
        f"outer offsets are {[outer.offset(n) for n, _ in outer.fields]}, expected [0, 4, 12]")
    assert offset_of([("in", inner), ("c", "char")], "in") == 0

    deep = Struct([("head", "char"), ("mid", outer), ("tail", "double")])
    assert deep.offset("mid") == 4, (
        f"deep.mid at offset {deep.offset('mid')}, expected 4 (aligned to the nested struct's alignment 4)")
    assert deep.offset("tail") == 24, (
        f"deep.tail at offset {deep.offset('tail')}, expected 24 (aligned to double's 8): a nested "
        "struct is aligned as a unit to ITS alignment, not to 1")
    assert deep.size == 32, f"deep size {deep.size}, expected 32"
    assert sizeof([("head", "char"), ("mid", outer), ("tail", "double")]) == 32


# ---------------------------------------------------------------------------
# Step 3: layout.py -- format strings and the packed byte layout
# ---------------------------------------------------------------------------

def check_packed_format() -> None:
    from layout import format_string, pack_struct, sizeof

    fields = [("c", "char"), ("i", "int"), ("d", "double")]
    got = format_string(fields, packed=True)
    assert got == "<bid", (
        f"format_string(packed) returned {got!r}, expected '<bid': concatenate the format codes "
        "with no padding bytes at all")
    assert sizeof(fields, packed=True) == struct.calcsize("<bid") == 13, (
        f"packed sizeof = {sizeof(fields, packed=True)}, struct.calcsize('<bid') = {struct.calcsize('<bid')}")

    values = {"c": 65, "i": 7, "d": 2.5}
    got_bytes = pack_struct(fields, values, packed=True)
    want = struct.pack("<bid", 65, 7, 2.5)
    assert got_bytes == want, (
        f"packed bytes {got_bytes.hex()} do not match the hand-written format string '<bid' "
        f"({want.hex()}): check the byte order and the value encoding")

    # The natural format string must spell the padding out explicitly, so that
    # struct.calcsize agrees with our sizeof instead of dropping the trailing bytes.
    nat = format_string(fields, packed=False)
    assert struct.calcsize(nat) == sizeof(fields) == 16, (
        f"format_string(natural) = {nat!r} has calcsize {struct.calcsize(nat)}, but sizeof = "
        f"{sizeof(fields)}. Write the internal AND trailing padding as 'x' bytes.")

    # Here the last member does NOT end on the struct's alignment, so the trailing
    # padding is the only thing that can make calcsize reach sizeof.
    tail = [("i", "int"), ("c", "char")]
    nat_tail = format_string(tail, packed=False)
    assert nat_tail == "<ibxxx", (
        f"format_string({tail}, natural) = {nat_tail!r}, expected '<ibxxx': the trailing 3 bytes "
        "pad the struct up to its 4-byte alignment (char's code is 'b')")
    assert struct.calcsize(nat_tail) == sizeof(tail) == 8, (
        f"calcsize({nat_tail!r}) = {struct.calcsize(nat_tail)}, but sizeof = {sizeof(tail)}: "
        "the natural format must include the trailing padding, or struct.calcsize undercounts")


# ---------------------------------------------------------------------------
# Step 4: layout.py -- pack / unpack round-trip
# ---------------------------------------------------------------------------

def check_pack_roundtrip() -> None:
    from layout import Struct

    fields = [("c", "char"), ("i", "int"), ("d", "double")]
    s = Struct(fields)
    values = {"c": -5, "i": 123456, "d": -1.25}
    data = s.pack(values)
    assert len(data) == s.size == 16, f"packed {len(data)} bytes, struct size is {s.size}"
    assert data[1:4] == b"\x00\x00\x00", (
        f"internal padding bytes are {data[1:4].hex()}, expected zeros: memset the struct to zero "
        "before filling the fields")
    assert s.unpack(data) == values, f"round-trip changed the values: {s.unpack(data)} != {values}"

    p = Struct(fields, packed=True)
    pd = p.pack(values)
    assert len(pd) == 13 and p.unpack(pd) == values, (
        f"packed round-trip: {len(pd)} bytes, unpack -> {p.unpack(pd)}")

    inner = Struct([("x", "char"), ("y", "int")])
    outer = Struct([("a", "short"), ("in", inner), ("b", "char")])
    nested_values = {"a": 3, "in": {"x": 9, "y": -2}, "b": 7}
    nd = outer.pack(nested_values)
    assert len(nd) == outer.size == 16, f"nested struct packed {len(nd)} bytes, size is {outer.size}"
    assert nd[2:4] == b"\x00\x00", f"padding before the nested member is {nd[2:4].hex()}, expected zeros"
    assert outer.unpack(nd) == nested_values, (
        f"nested round-trip changed the values: {outer.unpack(nd)} != {nested_values}")


# ---------------------------------------------------------------------------
# Steps 5-6: reorder.py -- shrinking a struct
# ---------------------------------------------------------------------------

def check_reorder_reduces() -> None:
    from layout import Struct
    from reorder import bytes_saved, minimal_order, padding_bytes, shrink_struct

    fields = [("c", "char"), ("i", "int"), ("d", "char")]
    before = Struct(fields)
    assert padding_bytes(fields) > 0, (
        f"padding_bytes({fields}) = {padding_bytes(fields)}; this declaration does have padding")
    assert before.size == 12, f"before reordering the size is {before.size}, expected 12"
    after = shrink_struct(fields)
    assert after.size < before.size, (
        f"reordering gave size {after.size}, not smaller than {before.size}: put the largest "
        "alignments first so the small members fill the tail")
    assert after.size == 8, f"reordered size {after.size}, expected 8 (the sum of the fields)"
    assert padding_bytes(after.fields) < padding_bytes(fields), (
        f"reordering did not remove any padding: {padding_bytes(after.fields)} bytes remain, "
        f"started from {padding_bytes(fields)}; order: {[n for n, _ in after.fields]}")
    assert padding_bytes(fields) - padding_bytes(after.fields) == 4, (
        f"expected to reclaim 4 padding bytes, reclaimed "
        f"{padding_bytes(fields) - padding_bytes(after.fields)}")
    assert Struct(minimal_order(fields)).size == 8
    assert bytes_saved(fields) == 4

    tight = [("i", "int"), ("j", "int")]
    assert Struct(minimal_order(tight)).size == Struct(tight).size == 8, (
        "a struct with no padding must not change size when reordered")


def check_reorder_minimal() -> None:
    from layout import sizeof
    from reorder import minimal_order

    rng = random.Random(11)
    for _ in range(60):
        n = rng.randint(3, 6)
        fields = [(f"f{i}", rng.choice(_SCALARS)) for i in range(n)]
        best = min(sizeof(list(perm)) for perm in itertools.permutations(fields))
        got = sizeof(minimal_order(fields))
        assert got == best, (
            f"minimal_order({[t for _, t in fields]}) gives size {got}, but some permutation "
            f"reaches {best}. Largest alignment first is optimal here; a sort in the wrong "
            "direction leaves padding behind.")


# ---------------------------------------------------------------------------
# Step 7: layout.py -- limit case: packed is smaller, unaligned flagged
# ---------------------------------------------------------------------------

def check_limit_packed_unaligned() -> None:
    from layout import Struct, unaligned_fields

    fields = [("c", "char"), ("i", "int")]
    natural = Struct(fields)
    packed = Struct(fields, packed=True)
    assert natural.size == 8 and packed.size == 5, (
        f"natural size {natural.size} (expected 8), packed size {packed.size} (expected 5)")
    assert packed.size < natural.size, "removing padding must make the packed struct smaller"
    assert natural.unaligned() == [], (
        f"a naturally aligned struct reports unaligned fields {natural.unaligned()}")
    assert unaligned_fields(fields) == [], (
        f"unaligned_fields({fields}) in the natural layout = {unaligned_fields(fields)}, expected []: "
        "the natural layout aligns every member")
    assert unaligned_fields(fields, packed=True) == ["i"], (
        f"unaligned_fields({fields}, packed=True) = {unaligned_fields(fields, packed=True)}, "
        "expected ['i']: in the packed layout the int sits at offset 1, not a multiple of 4")
    assert "i" in packed.unaligned(), "the packed struct must flag the int as unaligned"

    f2 = [("a", "char"), ("b", "double"), ("c", "int")]
    s2 = Struct(f2, packed=True)
    assert set(s2.unaligned()) == {"b", "c"}, (
        f"packed {f2} flags {s2.unaligned()}, expected ['b', 'c']: offsets 1 (double) and 9 (int) "
        "are not aligned")


# ---------------------------------------------------------------------------
# Step 8: layout.py -- limit case: an over-aligned member pads the whole struct
# ---------------------------------------------------------------------------

def check_limit_overaligned() -> None:
    from layout import Struct, offset_of, sizeof

    fields = [("c", "char"), ("w", "longdouble"), ("d", "char")]
    s = Struct(fields)
    assert s.alignment == 16, (
        f"struct alignment {s.alignment}, expected 16: longdouble is aligned to 16")
    assert s.size == 48, (
        f"sizeof = {s.size}, expected 48. An over-aligned member pads the WHOLE struct: after "
        "the 1-byte char (at 16), 16 bytes of longdouble (to 32) and 1 byte of char, the size "
        "must still round up to a multiple of 16.")
    assert s.size % s.alignment == 0, f"{s.size} is not a multiple of alignment {s.alignment}"
    assert (s.offset("c"), s.offset("w"), s.offset("d")) == (0, 16, 32), (
        f"offsets are {(s.offset('c'), s.offset('w'), s.offset('d'))}, expected (0, 16, 32)")
    assert offset_of(fields, "w") == 16 and sizeof(fields) == 48

    size, offs, align = _abi(fields)
    assert (s.size, s.alignment) == (size, align), (
        f"our size/align {(s.size, s.alignment)} disagree with the ABI {(size, align)}")
    packed = Struct(fields, packed=True)
    assert packed.size == 18, f"packed size {packed.size}, expected 18"
    assert "w" in packed.unaligned(), "the packed longdouble at offset 1 must be flagged unaligned"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("layout.py", "natural sizeof and member offsets match the ABI", check_natural_layout),
    ("layout.py", "nested structs propagate size and alignment", check_nested_layout),
    ("layout.py", "packed and natural format strings vs struct", check_packed_format),
    ("layout.py", "pack/unpack round-trip, padding is zero", check_pack_roundtrip),
    ("reorder.py", "reordering strictly reduces a padded struct", check_reorder_reduces),
    ("reorder.py", "reordering is size-optimal (brute force)", check_reorder_minimal),
    ("layout.py", "limit: packed is smaller, unaligned access flagged", check_limit_packed_unaligned),
    ("layout.py", "limit: over-aligned member pads the whole struct", check_limit_overaligned),
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
    print(f"\n{BOLD}Memory Layout — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the memory-layout model.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
