# Compiler + Virtual GPU — Solutions

Complete implementations of every template in the parent directory. Pure Python 3
standard library; the whole directory runs in about a second.

```bash
python3 isa.py            # encoding round-trips
python3 assembler.py      # two-pass assembly with labels
python3 cpu.py            # the scalar machine
python3 frontend.py       # lexer + parser
python3 codegen.py        # v1 -> v3, spilling appearing
python3 vgpu.py           # SIMT divergence, traced and measured
python3 capstone.py       # one program, two machines
```

## What each file shows

### `isa.py`
16 registers, 32-bit fixed-width: `[opcode:6][rd:4][rs1:4][rs2:4][imm:14]`.

```
ADD r3, r1, r2      0x10c48000  round-trip: OK
LI r5, -1234        0x09403b2e  round-trip: OK
immediate too large: rejected — LI: immediate 99999 does not fit in 14 bits
```

The negative immediate is the one that matters: it needs masking on the way in and
sign-extension on the way out. Miss either and every backward jump is wrong.

### `assembler.py`
Two passes, because `JNZ r4, done` refers to a label that has not been seen yet. Labels
resolve to instruction indices, not byte offsets. Every error names its line.

### `cpu.py`
Fetch–decode–execute, decoding from the **word** each cycle rather than caching decoded
objects — the machine's input is memory. `sum(1..100) = 5050` in 505 cycles, five per
iteration. Out-of-range addresses, division by zero, runaway loops and GPU instructions
each get their own message.

### `frontend.py`
Recursive descent with precedence climbing. `1 + 2 * 3` puts `*` deeper; `10 - 3 - 2`
nests left. One `PRECEDENCE` table, so adding an operator is one entry.

**Note the `TOKEN_SPEC` ordering.** `COMMENT` must precede `OP`: alternation takes the
first branch that matches, so with `OP` first, `//` lexes as two `/` operators and the
comment body becomes identifiers. This was a real bug in this file, caught by the checker.

### `codegen.py`
Four stages. v1 emits to unlimited virtual registers; v3 allocates them by linear scan
over live intervals, spilling to memory at `SPILL_BASE`.

```
  depth  virtual regs   spills   result   ok
     10            21        0       55   OK
     14            29        1      105   OK
     24            49       11      300   OK
```

Right-nested expressions are what force this — left-nested temporaries die immediately
and linear scan reuses one register forever. What is live at once is a property of the
expression's **shape**, not its size.

### `vgpu.py`
One warp, eight lanes, one PC, a mask stack.

```
condition               issues  efficiency
all lanes same              12        92%
half and half               14        75%
alternating                 16        78%
```

`all lanes same` is 92%, not 100%: it still issues the `DIVERGE` and an empty `ELSE`, but
skips the dead arm's body — which is the part that would actually cost you.

A `BAR` inside divergence is detected and explained rather than hanging.

### `capstone.py`
```
uniform     8.00x speedup, 100% efficiency
divergent   6.86x,          75%
ragged      1.37x,          57%
```

The serial baseline runs the **same compiled words** on a one-lane warp, so the difference
is the execution model and not the compiler.

## Implementation notes

- **`encode` masks the immediate** with `((1 << IMM_BITS) - 1)`; **`decode` sign-extends**.
  Both are required, and the checker tests a negative immediate specifically.
- **Labels do not advance the address.** A label is a position, not an instruction.
- **`second_pass` checks the operand count.** `ADD r1, r2` would otherwise assemble with
  `rs2 = 0` and compute the wrong thing at runtime.
- **`COMMENT` precedes `OP` in `TOKEN_SPEC`** — see above.
- **`parse_expr` recurses with `power + 1`.** That is what makes operators left-associative.
- **Codegen emits virtual registers; allocation is a separate pass.** Mixing them makes
  both problems much harder, which is why every real compiler separates them too.
- **Spill rewriting must know which operand is a destination.** `ST`, `STS`, `JZ`, `JNZ`,
  `DIVERGE` and `LOOPTEST` all *read* their first operand rather than writing it.
- **`CONVERGE` restores the saved outer mask**, never "all lanes". Restoring all lanes
  passes a simple nested test and fails the moment a statement follows the inner `if` —
  which the checker now covers.
- **`<=`, `>=` and `!=` have no opcodes.** They are derived by comparing the base
  comparison against 0. Fewer opcodes means less to decode, in the assembler and the
  hardware.
