# Bits: integers, floats, endianness — Solutions

Complete versions of every template in the parent directory. Pure Python 3, no
dependencies. Run them from inside this directory (they do not import each other):

```bash
python3 twos_complement.py   # i32 two's complement, wrapping vs guarded add
python3 float754.py          # subnormals, -0.0, infinities and NaN classes
python3 endianness.py        # host byte order and a hex dump
```

## Expected output

`python3 twos_complement.py`:

```
i32 two's complement: -1 -> 0xFFFFFFFF, decoded back -> -1
i32 wrapping add: 0x7FFFFFFF + 1 -> -2147483648 (0x80000000)
guarded add raised: 2147483647 + 1 does not fit in signed 32-bit (range -2147483648..2147483647); use add_wrap for wrapping arithmetic
i8 decode: 0xFF -> -1, 0x80 -> -128
```

`python3 float754.py`:

```
smallest binary32 subnormal: bits=0x1 -> 1.401298464324817e-45 (re-encoded 0x1); min normal 1.1754943508222875e-38
smallest binary64 subnormal: bits=0x1 -> 5e-324 (re-encoded 0x1)
-0.0: value == 0.0 is True, copysign is -1, class 'negative zero'
              +inf: class         infinity, payload 0x0, round-trips True
              -inf: class negative infinity, payload 0x0, round-trips True
              qNaN: class        quiet nan, payload 0x8000000000000, round-trips True
              sNaN: class    signaling nan, payload 0x1, round-trips True
   -qNaN payload 1: class        quiet nan, payload 0x8000000000001, round-trips True
```

`python3 endianness.py` (the first line depends on the host; this machine is little-endian):

```
host byte order: little (interpreter says little)
0x01020304 little-endian -> 04 03 02 01
0x01020304 big-endian    -> 01 02 03 04
-1 as i32 big-endian bytes -> ff ff ff ff
swap 01 02 03 04 -> 04 03 02 01
```

The numbers to predict before running: the smallest binary32 subnormal is `2**-149`,
`-0.0 == 0.0` is `True` but its sign bit is set, and `0x7FF0000000000001` is a
*signaling* NaN because the top fraction bit (the quiet bit) is clear.
