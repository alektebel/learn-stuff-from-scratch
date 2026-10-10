# CRDTs From Scratch — Solutions

Complete versions of every template in the parent directory. Pure Python 3, no dependencies.
Run them from inside this directory (each file is self-contained):

```bash
python3 gc_counter.py     # 40 increments / 60 mixed ops over 5 replicas -> one total
python3 lww_register.py   # 4 replicas writing at the same timestamp -> one winner
python3 or_set.py         # concurrent remove and re-add -> one surviving set
```

## Expected output

`python3 gc_counter.py` (seed 7, deterministic):

```
G-Counter: 40 increments over 5 replicas -> total 179
PN-Counter: 60 ops mixed +/- -> value -59 (can be negative)
G-Counter idempotent: True
```

`python3 lww_register.py` (seed 11, deterministic):

```
4 replicas, 7 writes each -> winner 'tie:gamma' (stamp (99, 'gamma'))
tie-break is order-independent: True
```

`python3 or_set.py` (seed 13, deterministic):

```
OR-set after concurrent remove/re-add -> ['only-n0', 'only-n1', 'only-n2', 'only-n3', 'shared']
'shared' survives a concurrent add: True
merge is idempotent: True
```

## Reading the numbers

- The G-counter total is a sum of per-node high-water marks, so it is independent of which
  replica happened to receive which increment; run it ten times and the total never moves.
- The PN-counter value is **negative** on purpose. If your implementation clamps at zero,
  you have collapsed the lattice and step 2 will say so.
- The LWW winner is `tie:gamma` because every replica writes at timestamp 99 and `gamma` is
  the greatest node id. The tie-break is the only reason the merge commutes.
- The OR-set keeps `shared` because two replicas `add`ed it after (or concurrently with) the
  removes, with fresh tags the removers never observed. The `only-*` elements show that
  partition-local adds survive independently.

`solutions/README.md`'s numbers are a claim you can reproduce; predict each one before you
run it, and if a number surprises you, that is the gap worth chasing.
