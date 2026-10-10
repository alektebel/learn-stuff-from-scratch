"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "twos_complement.py": {
  "to_bits": "Return the signed value reduced to `width` bits: `value & (2**width - 1)`. Overflow wraps here; it does not raise.",
  "from_bits": "Validate the pattern is in [0, 2**width); if bit `width-1` is set, subtract 2**width, else return the pattern.",
  "add_wrap": "Encode both operands, add the patterns, reduce mod 2**width, then decode back to signed. Never raise for magnitude.",
  "add_checked": "Compute the mathematical sum and raise OverflowError unless it lies in [-2**(width-1), 2**(width-1)-1]. Do not wrap.",
 },
 "float754.py": {
  "float_to_bits": "Pack `value` with struct in format '<f' or '<d', then read the bytes as a little-endian unsigned integer.",
  "bits_to_float": "Check `bits` is a valid pattern, turn it into bytes little-endian, and struct.unpack '<f' or '<d'. Subnormals stay nonzero.",
  "sign_of_bits": "The top bit of the pattern: `(bits >> (total_bits - 1)) & 1`.",
  "classify_bits": "Split into sign, exponent (next `ebits`) and fraction (low `fbits`). exp all ones -> inf/NaN (quiet if the top fraction bit is set); exp zero -> zero or subnormal; else normal.",
  "nan_payload": "The fraction field, but only when the exponent is all ones and the fraction is nonzero; otherwise 0.",
 },
 "endianness.py": {
  "host_byteorder": "struct.pack('@I', 1) and return 'little' if the first byte is 1 else 'big'. Do not read sys.byteorder.",
  "to_little_endian": "`value.to_bytes(width, 'little')`.",
  "to_big_endian": "`value.to_bytes(width, 'big')`.",
  "from_little_endian": "`int.from_bytes(data, 'little')`.",
  "from_big_endian": "`int.from_bytes(data, 'big')`.",
  "swap_byteorder": "Reverse the byte string: `bytes(reversed(data))`.",
  "hex_dump": "Join two-digit lowercase hex per byte with spaces: `' '.join(f'{b:02x}' for b in data)`.",
 },
}
