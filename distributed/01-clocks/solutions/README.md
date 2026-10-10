# Time, Lamport and Vector Clocks — Solutions

Complete versions of every template in the parent directory. Pure Python 3, no
dependencies. Run them from inside this directory (they do not import each other):

```bash
python3 lamport.py   # a send/receive chain; every send precedes its receive
python3 vector.py    # classifications over a stream with a concurrent pair
python3 wall.py      # two unsynchronised clocks invert a causal pair
```

## Expected output

`lamport.py` — the chain A -> B -> C, then back to C via B:

```
event stream (process, kind, Lamport timestamp):
  A local   ts=1
  A send    ts=2
  B local   ts=1
  B receive ts=3
  B send    ts=4
  C receive ts=5
send precedes receive on 2/2 messages; max timestamp = 5
```

`vector.py` — A and B each send to C without talking to each other:

```
classifications in the stream:
  last A event vs last B event : concurrent
  C receive #1 vs C receive #2 : before
  vector clocks: A={'A': 3} B={'B': 2} C={'A': 3, 'C': 2, 'B': 2}
```

`wall.py` — B's clock runs 5 seconds slow:

```
one message between two unsynchronised clocks:
  send    true= 10.0  wall= 10.0
  receive true= 11.0  wall=  6.0
  wall-time order says: receive then send  (true-time order says send then receive)
  causally ordered pair with inverted wall stamps: True
```

That last line is the whole point of the module: the receive happened a second *after*
the send in real time, yet its wall timestamp (6) is earlier than the send's (10), so
ordering by wall time puts the effect before its cause. Logical clocks exist precisely
because a timestamp on a message is not a global order.

## Notes

- `check.py` in the parent directory never imports these files; it tests the templates.
- Every check in the suite passed against these solutions (`python3 check.py --all` from
  a directory holding `check.py` and these files: 8/8).
