"""
Struct layout, alignment and padding under the x86-64 / LP64 ABI.

Source: Bryant & O'Hallaron, *Computer Systems: A Programmer's Perspective*
(CS:APP), Chapter 3 "Machine-Level Representation of Programs", section 3.9
"Heterogeneous Data Structures" -- Structures (3.9.1) and, in particular,
"Data Alignment" (3.9.3). Restated in my own words:

  - Every scalar type has a *size* and an *alignment*. On x86-64 an `int` is 4
    bytes and wants a 4-byte boundary; a `double` is 8 and wants 8; a `char` is
    1 and is happy anywhere.
  - A member is placed at the next offset that is a multiple of its own
    alignment. The bytes skipped to get there are *internal padding*.
  - The whole struct's alignment is the maximum of its members' alignments, and
    the struct's size is rounded up to a multiple of that. The bytes added at
    the end are *trailing padding*, and they are what makes ``sizeof`` larger
    than the sum of the field sizes.
  - Padding is invisible to the program but real in memory: it is what a
    struct-by-struct ``memcmp`` or a ``write()`` of a struct sends to the wire.

The module builds the layout rule from scratch, then uses it to (a) report
``sizeof``/offsets, (b) pack a struct into its exact in-memory byte string, and
(c) flag the fields that become unaligned when padding is removed.

DESIGN DECISION -- query the compiler or model the ABI?
    `ctypes` can tell us the real size and offsets, but that hides the rule we
    are trying to learn and is not available in a freestanding piece of code.
    **Chosen:** an explicit type table (``NATIVE_TYPES``); the checks cross-check
    it against ``ctypes``/``struct`` so the model cannot drift quietly.

DESIGN DECISION -- byte order of the packed bytes?
    **Chosen:** little-endian (``"<"`` in the ``struct`` format). It is the
    native order on x86-64 and it is deterministic, so the byte string is
    reproducible on any machine running these checks.

DESIGN DECISION -- how does a nested struct behave?
    A nested struct is laid out once by its own rules and then treated as a
    single member with that struct's size and alignment (exactly C's rule).
    **Chosen:** the nested struct keeps its own ``packed`` setting; the outer
    struct only copies its bytes.
"""

import struct
from collections import namedtuple

# (size in bytes, alignment in bytes, python struct format code or None)
TypeInfo = namedtuple("TypeInfo", "size align code")

# The LP64 data model used by x86-64 Linux (the model the checks verify against
# ctypes). `longdouble` is x86-64's 80-bit extended float, stored in 16 bytes
# and *over-aligned* to 16 -- the type the over-alignment limit case is built on.
NATIVE_TYPES = {
    "char": TypeInfo(1, 1, "b"),
    "uchar": TypeInfo(1, 1, "B"),
    "short": TypeInfo(2, 2, "h"),
    "ushort": TypeInfo(2, 2, "H"),
    "int": TypeInfo(4, 4, "i"),
    "uint": TypeInfo(4, 4, "I"),
    "long": TypeInfo(8, 8, "q"),
    "ulong": TypeInfo(8, 8, "Q"),
    "longlong": TypeInfo(8, 8, "q"),
    "ulonglong": TypeInfo(8, 8, "Q"),
    "float": TypeInfo(4, 4, "f"),
    "double": TypeInfo(8, 8, "d"),
    "pointer": TypeInfo(8, 8, "Q"),
    "longdouble": TypeInfo(16, 16, None),  # layout only; no struct format code
}

# offsets, total size, and the struct's own alignment
Layout = namedtuple("Layout", "offsets size alignment")


def align_up(n: int, a: int) -> int:
    """Round n up to the next multiple of a (a need not be a power of two)."""
    return (n + a - 1) // a * a


def _describe(spec):
    """(size, alignment, format_code) for a type spec, scalar or nested Struct."""
    if isinstance(spec, Struct):
        return spec.size, spec.alignment, None
    t = NATIVE_TYPES[spec]
    return t.size, t.align, t.code


def _type_name(spec) -> str:
    return "struct" if isinstance(spec, Struct) else spec


def compute_layout(fields, packed: bool = False) -> Layout:
    """
    Lay `fields` out in memory and return (offsets, size, alignment).

    `fields` is a sequence of (name, spec) pairs, in declaration order; `spec`
    is a key of NATIVE_TYPES or a nested Struct. In natural mode a member is
    aligned to its own alignment and the struct is padded to its own alignment;
    in packed mode no padding at all is inserted.
    """
    # TODO: Walk the fields in declaration order. In natural mode round the running offset up to the member's alignment before placing it, then add its size; the struct's alignment is the max member alignment and its size is rounded up to that. In packed mode add no padding: size is just the sum.
    raise NotImplementedError("compute_layout")


def _pack_one(spec, value) -> bytes:
    if isinstance(spec, Struct):
        return spec.pack(value)
    t = NATIVE_TYPES[spec]
    if t.code is None:  # longdouble and friends: raw bytes
        raw = bytes(value)
        if len(raw) != t.size:
            raise ValueError(f"{_type_name(spec)} needs {t.size} raw bytes, got {len(raw)}")
        return raw
    return struct.pack("<" + t.code, value)


def _unpack_one(spec, raw: bytes):
    if isinstance(spec, Struct):
        return spec.unpack(raw)
    t = NATIVE_TYPES[spec]
    if t.code is None:
        return raw
    return struct.unpack("<" + t.code, raw)[0]


class Struct:
    """A fixed set of (name, type) fields with a computed memory layout."""

    def __init__(self, fields, packed: bool = False):
        self.fields = [(name, spec) for name, spec in fields]
        self.packed = packed
        self.layout = compute_layout(self.fields, packed)
        self.size = self.layout.size
        self.alignment = self.layout.alignment

    def offset(self, name: str) -> int:
        return self.layout.offsets[name]

    def unaligned(self):
        """Names whose offset is not a multiple of their own alignment."""
        return unaligned_fields(self.fields, self.packed)

    def pack(self, values) -> bytes:
        return pack_struct(self.fields, values, self.packed)

    def unpack(self, data: bytes) -> dict:
        return unpack_struct(self.fields, data, self.packed)

    def format_string(self) -> str:
        return format_string(self.fields, self.packed)

    def __repr__(self) -> str:
        body = ", ".join(f"{n}: {_type_name(s)}" for n, s in self.fields)
        return f"Struct({body}, size={self.size}, align={self.alignment})"


def sizeof(fields, packed: bool = False) -> int:
    """Total size in bytes, trailing padding included (natural mode)."""
    # TODO: Return the size from compute_layout (trailing padding included).
    raise NotImplementedError("sizeof")


def offset_of(fields, name: str, packed: bool = False) -> int:
    """Byte offset of member `name` from the start of the struct."""
    # TODO: Return compute_layout(...).offsets[name]; raise KeyError for an unknown field.
    raise NotImplementedError("offset_of")


def format_string(fields, packed: bool = False) -> str:
    """
    A python `struct` format string that reproduces this layout.

    Padding is written out explicitly as `x` bytes, so
    ``struct.calcsize(format_string(fields)) == sizeof(fields)`` and
    ``struct.calcsize(format_string(fields, packed=True))`` is the packed size.
    Nested structs have no single format code, so they are rejected here.
    """
    # TODO: Concatenate each member's struct code, inserting 'x'*gap for every padding byte (internal and trailing) in natural mode; tile the codes with no gaps in packed mode; prefix with '<'.
    raise NotImplementedError("format_string")


def pack_struct(fields, values, packed: bool = False) -> bytes:
    """Lay a struct out as a byte string, padding bytes zeroed."""
    # TODO: Allocate a zeroed bytearray of the layout size, encode each value (struct.pack('<'+code), raw bytes for code None, or a nested Struct.pack), and copy it in at that member's offset.
    raise NotImplementedError("pack_struct")


def unpack_struct(fields, data: bytes, packed: bool = False) -> dict:
    """Inverse of pack_struct; returns {field name: value}."""
    # TODO: Reject data whose length is not the layout size, then slice each member's bytes at its offset and decode (struct.unpack, raw bytes, or a nested Struct.unpack).
    raise NotImplementedError("unpack_struct")


def unaligned_fields(fields, packed: bool = False) -> list:
    """
    Names whose offset is not a multiple of their own alignment *in this layout*.

    A naturally aligned struct reports nothing: alignment is guaranteed by
    construction. A packed struct (no padding) can place a 4-byte `int` at
    offset 1; that is the access a CPU either faults on or silently pays a
    fix-up for, so packing is a space/CPU trade, not a free win.
    """
    # TODO: Lay the fields out in the given mode and return the names whose offset % their own alignment != 0. Natural mode is always empty; packed mode is where the hazard shows up.
    raise NotImplementedError("unaligned_fields")


if __name__ == "__main__":
    table = [
        [("c", "char"), ("i", "int"), ("d", "char")],
        [("i", "int"), ("c", "char")],
        [("a", "short"), ("in", Struct([("x", "char"), ("y", "int")])), ("b", "char")],
        [("c", "char"), ("w", "longdouble"), ("d", "char")],
    ]
    print(f"{'fields':<44} {'sizeof':>6} {'align':>5} {'pad':>4} {'packed':>6} {'unaligned (packed)'}")
    for fields in table:
        s = Struct(fields)
        payload = sum(_describe(spec)[0] for _, spec in fields)
        p = Struct(fields, packed=True)
        label = ", ".join(f"{n}:{_type_name(spec)}" for n, spec in fields)
        flag = ",".join(p.unaligned()) or "-"
        print(f"{label:<44} {s.size:>6} {s.alignment:>5} {s.size - payload:>4} {p.size:>6} {flag}")
    fields = [("c", "char"), ("i", "int"), ("d", "double")]
    print()
    print("format string packed :", format_string(fields, packed=True),
          "calcsize", struct.calcsize(format_string(fields, packed=True)))
    print("format string natural:", format_string(fields, packed=False),
          "calcsize", struct.calcsize(format_string(fields, packed=False)))
    print("packed bytes         :", pack_struct(fields, {"c": 65, "i": 7, "d": 2.5}, packed=True).hex())
