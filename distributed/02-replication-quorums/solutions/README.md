# Replication and Quorums — Solutions

Complete versions of every template in the parent directory. Pure Python 3,
standard library only. Run them from inside this directory (they import each
other by name):

```bash
python3 network.py   # arrival order with delays; a partition dropping traffic
python3 replica.py   # a refused gap and a truncate rollback
python3 quorum.py    # the R+W>N table and the stale-read window
```

## Expected output

`python3 network.py`:

```
arrival order with explicit delays: ['fast', 'slow']
partition dropped 1 message(s); b holds ['fast', 'slow']
after heal, b holds: ['fast', 'slow', 'after-heal']
```

`python3 replica.py`:

```
log length: 2  value(x): (1, 'two')
append at a gap accepted? False  log length: 2
after truncate(1): length 1  value(x): (0, 'one')
```

`python3 quorum.py`:

```
R+W>N ?  (read must see the last acknowledged write when True)
  R=2 W=2 N=3: True
  R=1 W=3 N=3: True
  R=1 W=1 N=3: False
  R=2 W=2 N=5: False
  R=1 W=4 N=5: False
R=2 W=2 N=3: write acked at version 0; read from [C,B] -> 'hello' (overlap saves us)
R=1 W=1 N=3: write acked at version 0; read from [C] -> None (no overlap, stale)
        after heal + catch_up, read from [C] -> 'hello'
```

The network is seeded with `20261010`, so every order above is fixed. The checker
uses the same seed.

## What the numbers mean

- **`['fast', 'slow']`** is the point of the network: `slow` was sent first with a
  delay of 7, `fast` second with a delay of 1, and delivery is ordered by when a
  message comes due, not by when it was sent. A naive queue that delivers in send
  order prints `['slow', 'fast']`.
- **`partition dropped 1`** is the cross-group message: `a` and `b` stayed
  connected, `a -> b` was delivered, and the one message crossing into the other
  group was counted as dropped, never delivered.
- **`append at a gap accepted? False`** is log safety: the replica holds two
  entries (indices 0 and 1), so an append at index 3 would leave a hole. Refusing
  it forces the leader to catch the replica up instead of letting it fork.
- **`truncate(1)` rolls `(1, 'two')` back to `(0, 'one')`** because dropping a log
  entry must also drop the value it contributed. An implementation that truncates
  the log but not `applied` keeps a value whose write no longer exists.
- **`R=2 W=2 N=3: read from [C,B] -> 'hello'`** — there is exactly one prior write
  on all replicas, then `hello` reaches only `{A, B}` behind the partition. `C` is
  one version behind, yet the read is fresh: `R + W = 4 > 3`, so `{C, B}` cannot
  avoid `B`. Reading the first response rather than the newest version returns the
  stale `old`.
- **`R=1 W=1 N=3: read from [C] -> None`** — with `R + W = 2 <= 3` the read set
  `{C}` is disjoint from the write set `{A}`, so the acknowledged write is
  invisible. `catch_up()` sends the missing suffix and closes the window; it does
  not change the rule, it repairs the replica.

## A note on determinism

Every number comes from `random.Random(seed)` owned by the `Network`; the global
`random` module is never used, so nothing depends on `PYTHONHASHSEED` or on import
order. Two runs of the same script print the same lines.
