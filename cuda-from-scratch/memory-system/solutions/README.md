# Solutions — GPU memory system

Working implementations of the four templates. Read them *after* attempting: a solution
read cold is just more prose. Each file opens with its design decisions and has a
`__main__` demo that prints a measurement.

```bash
cd cuda-from-scratch/memory-system
python3 check.py --all                       # against the templates: every step TODO
cp solutions/*.py . && python3 check.py --all  # 16/16 pass
python3 solutions/coalescing.py              # the demos below
```

To check in a temporary copy without touching the templates, copy `solutions/*.py` and
`check.py` into an empty directory and run `python3 check.py --all` there.

## Expected demo output

`python3 solutions/coalescing.py`:

```
pattern                      sectors  efficiency
contiguous f32 (stride 4)          4       1.000
stride 8 bytes                     8       0.500
stride 32 bytes                   32       0.125
contiguous, offset 7               5       0.800
```

`python3 solutions/banks.py`:

```
access                         degree
row of 32x32                        1
column of 32x32                    32
column, padded to 33                1
broadcast (same word x32)           1
two words in bank 5                 2
padding a 32x32 tile costs 32 words (128 bytes, 3.12% more)
```

`python3 solutions/occupancy.py`:

```
 regs    smem   thr  blocks  warps    occ  limiting
   32       0   256       6     48   1.00  threads
   64       0   256       4     32   0.67  registers
  128       0   256       2     16   0.33  registers
   32   16384   256       3     24   0.50  shared_memory
   32       0  1024       1     32   0.67  threads
```

`python3 solutions/roofline.py`:

```
peak 1.0e+13 flop/s, bandwidth 1.0e+12 B/s -> ridge 10.0 flop/byte
kernel                    AI     bound  fraction of peak
vector add              0.17    memory             0.017
matmul N=1024         170.67   compute             1.000
AI=2                    2.00    memory             0.200
```

## Predicting before looking

The point of the demos is not the output but whether you predicted it. Before you run
`occupancy.py`, work out which resource limits the 64-register case and the 128-register
case. Before you run `banks.py`, write down the bank index of thread 17 in the padded
tile. Before you run `roofline.py`, decide which side of the ridge vector add and matmul
fall on. A surprise is a gap in your model that passing the checks did not reveal.
