"""Byte order: little/big endian, a host detector, and a hex dump.

The material is CS:APP (Bryant & O'Hallaron), chapter 2, section 2.1, "Information
Storage": a multi-byte object in memory is just bytes, and whether the least significant
byte comes first (little endian) or last (big endian) is a convention the hardware
chooses. It only becomes visible when the same bytes are written by one machine and read
by another, or when a debugger prints memory.

DESIGN DECISION - ask the interpreter, or measure the machine?
`sys.byteorder` reports the answer, but it is the interpreter's claim, not a measurement.
**Chosen: pack the integer 1 in *native* format and look at its first byte** - `01 00 00 00`
is little, `00 00 00 01` is big. The detector then has a falsifiable contract, and the
same trick is what the checker uses to sanity-check it.

DESIGN DECISION - `bytes.hex()` as the dump, or a hand-rolled one?
`bytes.hex(' ')` already emits lowercase, space-separated bytes. **Chosen: a small
`hex_dump` built from `f"{b:02x}"`**, not because `bytes.hex` is wrong but because the
grouping (and later, addresses and ASCII) is where debuggers differ, and writing the loop
is how you notice that a byte is two hex digits. The cost is one avoided built-in.

    python3 endianness.py      # prints the measurements this file promises
"""

import struct


def host_byteorder() -> str:
    """Return "little" or "big", measured from a native pack, not from `sys.byteorder`."""
    native = struct.pack("@I", 1)
    return "little" if native[0] == 1 else "big"


def to_little_endian(value: int, width: int) -> bytes:
    """Encode a non-negative integer as exactly `width` bytes, least significant first."""
    return value.to_bytes(width, "little")


def to_big_endian(value: int, width: int) -> bytes:
    """Encode a non-negative integer as exactly `width` bytes, most significant first."""
    return value.to_bytes(width, "big")


def from_little_endian(data: bytes) -> int:
    """Read bytes as an integer whose first byte is the least significant."""
    return int.from_bytes(data, "little")


def from_big_endian(data: bytes) -> int:
    """Read bytes as an integer whose first byte is the most significant."""
    return int.from_bytes(data, "big")


def swap_byteorder(data: bytes) -> bytes:
    """Reverse a byte string - the conversion between the two orders for one word."""
    return bytes(reversed(data))


def hex_dump(data: bytes) -> str:
    """A canonical hex dump: lowercase, exactly two hex digits per byte, space-separated.

    An empty input yields the empty string. Two-digit padding is the whole point: without
    it `01 2 03` would be unreadable and ambiguous.
    """
    return " ".join(f"{b:02x}" for b in data)


if __name__ == "__main__":
    word = 0x01020304
    print(f"host byte order: {host_byteorder()} (interpreter says {__import__('sys').byteorder})")
    print(f"0x{word:08X} little-endian -> {hex_dump(to_little_endian(word, 4))}")
    print(f"0x{word:08X} big-endian    -> {hex_dump(to_big_endian(word, 4))}")
    print(f"-1 as i32 big-endian bytes -> {hex_dump(to_big_endian(0xFFFFFFFF, 4))}")
    print(f"swap {hex_dump(to_big_endian(word, 4))} -> {hex_dump(swap_byteorder(to_big_endian(word, 4)))}")
