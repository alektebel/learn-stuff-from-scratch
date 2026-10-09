# Solutions

Complete implementations of the registry, the gateway and the contract checker. Copy any
file over the template of the same name to see its steps pass. `gateway.py` imports
`registry.py`, so run it from this directory (or copy both together).

```bash
python3 registry.py   # TTL heartbeats, expiry, graceful draining
python3 gateway.py    # routing, round-robin, retrying a GET but never a POST
python3 contract.py   # classify schema changes as compatible vs breaking
```

## Expected demo output

```
$ python3 registry.py
resolved at t=0: ['10.0.0.0:8080', '10.0.0.1:8080', '10.0.0.2:8080']
after pod-1 heartbeat + pod-0 draining at t=31: ['10.0.0.1:8080']  (pod-2's TTL lapsed, pod-0 drains)
sweep removed 2 expired instance(s)
remaining keys: [('checkout', 'pod-1')]

$ python3 gateway.py
GET /orders -> 200 after trying ['10.0.0.1:80', '10.0.0.2:80'] (retried on a fresh instance)
POST /orders -> 500 after trying ['10.0.0.1:80'] (a POST is never retried: side effects)

$ python3 contract.py
compatible  add optional 'coupon'
breaking    add required 'region'        ["new required field 'region'"]
breaking    rename 'total' to 'amount'   ["field 'total' was removed"]
```

## Verification

```bash
# against the solutions, in a temp copy:
cp check.py solutions/*.py /tmp/micro && cd /tmp/micro && python3 check.py --all   # 13/13

# the checker's own bugs: plant each mutation and confirm the step catches it
python3 ../../../.claude/skills/graded-module/scripts/mutate.py .. ../_build/mutations.py
```

Mutation result: `9/9 CAUGHT, 0 MISSED`.
