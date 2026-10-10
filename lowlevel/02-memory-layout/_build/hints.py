"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "layout.py": {
  "compute_layout": "Walk the fields in declaration order. In natural mode round the running offset up to the member's alignment before placing it, then add its size; the struct's alignment is the max member alignment and its size is rounded up to that. In packed mode add no padding: size is just the sum.",
  "sizeof": "Return the size from compute_layout (trailing padding included).",
  "offset_of": "Return compute_layout(...).offsets[name]; raise KeyError for an unknown field.",
  "format_string": "Concatenate each member's struct code, inserting 'x'*gap for every padding byte (internal and trailing) in natural mode; tile the codes with no gaps in packed mode; prefix with '<'.",
  "pack_struct": "Allocate a zeroed bytearray of the layout size, encode each value (struct.pack('<'+code), raw bytes for code None, or a nested Struct.pack), and copy it in at that member's offset.",
  "unpack_struct": "Reject data whose length is not the layout size, then slice each member's bytes at its offset and decode (struct.unpack, raw bytes, or a nested Struct.unpack).",
  "unaligned_fields": "Lay the fields out in the given mode and return the names whose offset % their own alignment != 0. Natural mode is always empty; packed mode is where the hazard shows up.",
 },
 "reorder.py": {
  "padding_bytes": "sizeof minus the sum of the member sizes: the bytes belonging to no member. A 6-byte payload in a size-8 struct has 2.",
  "minimal_order": "Return the fields sorted by DECREASING alignment (ties by decreasing size), stable so equal members keep their order. That makes each member already aligned, so only the final round-up remains.",
  "shrink_struct": "In packed mode return the fields unchanged; otherwise build a Struct over minimal_order(fields).",
  "bytes_saved": "Size of the declaration as written minus the size after minimal_order.",
 },
}
