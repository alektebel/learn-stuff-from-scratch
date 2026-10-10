# Partitioning and Rebalancing — Solutions

Complete versions of every template in the parent directory. Pure Python 3,
standard library only. Run them from inside this directory (they import each
other by name):

```bash
python3 hashring.py      # peak/mean share against the virtual-node count
python3 partitioner.py   # evenness, key movement on join/leave, a hot key's load
```

## Expected output

`python3 hashring.py`:

```
consistent hashing: peak/mean share of 20000 keys over 8 nodes
  vnodes=  1  peak/mean=2.488  low/mean=0.139
  vnodes=  4  peak/mean=1.854  low/mean=0.438
  vnodes= 64  peak/mean=1.347  low/mean=0.846
  vnodes=256  peak/mean=1.134  low/mean=0.950
joining one node moved 11.2% of keys (ideal 1/9 = 11.1%); modulo hashing would move almost all
```

`python3 partitioner.py`:

```
key distribution over 8 nodes x 256 vnodes
  evenness (peak/mean) = 1.134  (bound 1.25)
  per-node keys        = [2374, 2414, 2431, 2461, 2468, 2484, 2534, 2834]
join node-8: 2234/20000 keys moved (11.2%), all to the new node: True
leave node-3: moved 2484 keys, exactly its 2484 keys: True
hot key 3bb03db8... on node-3: 98.2% of all accesses despite an even ring
  that is the limit of consistent hashing: it balances keys, not load
```

The exact per-node counts depend on the seeded key set (seed `20261010`), so
they are fixed; the hot key's prefix will change only if you change the seed.

## What the numbers mean

- **peak/mean** is the busiest node's share divided by the average share. 1.0 is
  perfect. One position per node gives 2.488 — one node owns two and a half times
  its fair share. 256 positions brings it to 1.134.
- **11.2% on join** is one ninth (11.1%) plus ring noise: joining a ninth node
  takes only the arcs the new node now owns. The check also verifies every moved
  key landed on the new node. `hash(key) % num_nodes` would move ~89% instead.
- **98.2% of accesses** for one hot key is the limit case: the ring is even in
  *keys*, but load is weighted by access count, and one key read a million times
  dominates. Consistent hashing balances data, not work.
