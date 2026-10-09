# Solutions

Complete implementations of the replicated log and the replica set. Copy any file over
the template of the same name to see its steps pass. `cluster.py` imports `log.py`, so
run it from this directory (or copy both together).

```bash
python3 log.py       # the log algebra: up-to-date rule, leader choice, quorum
python3 cluster.py   # sync replication, async lag, and losing an acked write on failover
```

## Expected demo output

```
$ python3 log.py
last_term(old)=1  last_term(new)=2
is_up_to_date(new, old)=True  is_up_to_date(old, new)=False
choose_leader(['old','new']) = 'new' (term beats length)
committed with majority=2: 1 of 2 entries (a single replica is not a quorum)

$ python3 cluster.py
elected A (term 1, epoch 1)
  A: ['balance=100']  log=['balance=100']
  B: ['balance=100']  log=['balance=100']
  C: ['balance=100']  log=['balance=100']

async: leader A reads ['pay=50'], follower B reads []
after A dies, B leads and reads []: the acked write is gone (async)
```

The elected leader is whichever name sorts first among equal logs, so the output is
deterministic.

## Verification

```bash
# against the solutions, in a temp copy:
cp check.py solutions/*.py /tmp/repl && cd /tmp/repl && python3 check.py --all   # 10/10

# the checker's own bugs: plant each mutation and confirm the step catches it
python3 ../../../.claude/skills/graded-module/scripts/mutate.py .. ../_build/mutations.py
```

Mutation result: `8/8 CAUGHT, 0 MISSED`.
