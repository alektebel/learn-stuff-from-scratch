"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    ("sign bit off by one in decode", "twos_complement.py",
     "    sign_bit = 1 << (width - 1)\n",
     "    sign_bit = 1 << width\n",
     "1"),
    ("guarded add wraps silently", "twos_complement.py",
     "    if not lo <= total <= hi:\n",
     "    if False:  # overflow check disabled\n",
     "3"),
    ("float bits read in the wrong byte order", "float754.py",
     '    return int.from_bytes(packed, "little")\n',
     '    return int.from_bytes(packed, "big")\n',
     "4"),
    ("denormal flushed to zero", "float754.py",
     '    packed = struct.pack("<" + fmt, value)\n',
     '    packed = (b"\\x00" * _size(fmt)\n'
     '              if (value != 0.0 and abs(value) < 2.2250738585072014e-308)\n'
     '              else struct.pack("<" + fmt, value))\n',
     "6"),
    ("little-endian bytes read as big-endian", "endianness.py",
     '    return int.from_bytes(data, "little")\n',
     '    return int.from_bytes(data, "big")\n',
     "7"),
]
