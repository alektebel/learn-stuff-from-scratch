"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    # layout.py
    ("forget the struct's trailing padding", "layout.py",
     "    return Layout(offsets, align_up(offset, alignment), alignment)\n",
     "    return Layout(offsets, offset, alignment)\n", "1"),
    ("ignore a nested struct's alignment", "layout.py",
     "        return spec.size, spec.alignment, None\n",
     "        return spec.size, 1, None\n", "2"),
    ("natural format string drops trailing padding", "layout.py",
     "    if cursor < layout.size:\n",
     "    if False:\n", "3"),
    ("packing is treated as always aligned", "layout.py",
     "        if layout.offsets[name] % member_align != 0:\n",
     "        if False:\n", "7"),
    # reorder.py
    ("the bytes-saved metric always reports zero", "reorder.py",
     "    return Struct(fields).size - Struct(minimal_order(fields)).size\n",
     "    return 0\n", "5"),
    ("reordering is a no-op", "reorder.py",
     "    return sorted(fields, key=lambda f: (-_describe(f[1])[1], -_describe(f[1])[0]))\n",
     "    return list(fields)\n", "6"),
    ("padding_bytes ignores the real padding", "reorder.py",
     "    return s.size - payload\n",
     "    return 0\n", "5"),
]
