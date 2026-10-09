# Microservices From Scratch

The operational core of a microservices system, from scratch and stdlib only: **service
discovery** (registration, TTL heartbeats, graceful draining), an **API gateway**
(longest-prefix routing, client-side round-robin, safe retries), and **versioned
contracts** (which schema changes break a consumer).

Everything is deterministic: callers pass `now`, and the gateway takes the network call as
an `invoke` callback, so retry behaviour is tested without sockets or sleeps.

## Run it

```bash
cd system-design/microservices
python3 check.py          # stop at the first unimplemented step
python3 check.py --all    # run every check
python3 check.py 8        # just step 8
```

A step that raises `NotImplementedError` is TODO, not a failure. Read the docstring in
its file, implement it, re-run. Compare with `solutions/` only after trying.

## The steps

| Step | File | What you implement |
|---|---|---|
| 1 | `registry.py` | `register` / `resolve`: instances and endpoints, per service |
| 2 | `registry.py` | TTL expiry (`now >= expires_at`), `heartbeat`, `sweep` |
| 3 | `registry.py` | `start_draining` (kept, but no new traffic) and `deregister` |
| 4 | `registry.py` | re-register updates the endpoint and deadline; services are isolated |
| 5 | `gateway.py` | `match`: longest prefix on a path boundary, `404` when nothing matches |
| 6 | `gateway.py` | `pick`: round-robin over healthy instances, skip draining, `503` when none |
| 7 | `gateway.py` | `call`: retry an idempotent request on 5xx, re-picking a fresh instance |
| 8 | `gateway.py` | never retry a POST (it may already have applied a side effect) |
| 9 | `gateway.py` | never retry a 4xx; a connection error looks like a 5xx |
| 10 | `contract.py` | additive changes are compatible |
| 11 | `contract.py` | required fields (new, or promoted from optional) are breaking |
| 12 | `contract.py` | removal and type changes are breaking |
| 13 | `contract.py` | relaxations are compatible; reasons are complete and sorted |

Provided infrastructure (not graded): `ServiceRegistry.__init__`, `Gateway.__init__`,
`contract._fields`, and the check-side `invoke` callbacks.

## The idea in one page

- **Discovery.** A process cannot be configured with the addresses of its peers: they
  change on every deploy. It registers an endpoint with a TTL and refreshes it with
  heartbeats. A missed TTL means "presumed dead". A **draining** instance stays
  registered so its in-flight requests finish, but `resolve` stops returning it, so it
  gets no new work before it exits.
- **Gateway.** One front door maps a path to a service (longest matching prefix), picks a
  healthy instance (client-side round-robin), and calls it. Retries are only safe when the
  method is **idempotent** and the failure is **transient**: a 5xx or a dropped
  connection. A 4xx is the client's fault, and a POST may already have created something,
  so neither is retried.
- **Contracts.** Two services deploy independently, so a producer may only make changes an
  old consumer survives. New **required** fields and removals are breaking; new optional
  fields and relaxations are not. The check is the cheapest possible version of a
  consumer-driven contract test.

## Design decisions

The file docstrings carry the full arguments; the short version:

- **Registry over DNS/static list.** Fresh health, but one more service and a resolver
  hop. TTL heartbeats are cheap but detect death up to one TTL late.
- **Draining before deregistering.** Removes an instance from `resolve` first, then
  deregisters, so no request is dropped on the wire.
- **Client-side round-robin.** No second hop, stateless gateway replicas, but it ignores
  instance capacity (least-connections would adapt).
- **Retry policy.** Idempotent methods only, 5xx/connection errors only, bounded, and
  re-pick on each retry. Non-idempotent work must carry an idempotency key first.
- **Compatibility as a pure function.** Conservative: any type change and any removal is
  breaking; only additive-optional and relaxations pass.

## Mutation table

`_build/mutations.py` plants 9 mistakes; `mutate.py` confirms each is caught by the step
that should catch it. All CAUGHT:

| Mistake | Caught by |
|---|---|
| `resolve` ignores TTL expiry | 2 |
| `sweep` removes live instances too | 2 |
| `start_draining` does nothing | 3 |
| prefix matches without a path boundary | 5 |
| load balancer always picks the first instance | 6 |
| gateway retries a POST | 8 |
| gateway retries a 4xx | 9 |
| new required field treated as compatible | 11 |
| type change ignored | 12 |

## Questions to answer yourself (there is no check for these)

- TTL heartbeats detect a dead instance up to one TTL late, and a lazy node that misses
  one heartbeat is dropped. Compare with active health checks and with gossip membership
  (SWIM). Which failure does each detect first?
- The gateway retries a GET, and the retry is served by a replica that has not seen the
  client's earlier write. What guarantee did the client assume, and how do you provide it?
- A POST is not retried. How does an **idempotency key** let it be retried safely, and
  what does the server store? (See `../idempotency_keys.py`.)
- Round-robin ignores instance size and in-flight load. When does least-connections beat
  it, and what state does the gateway need to keep?
- A consumer upgrades before the producer. Which of the step-11 changes become compatible
  under that direction, and why is "backward" not the same as "forward" compatible?

## Limits (not implemented / deliberately simplified)

- No actual network: the gateway is handed an `invoke` callback; there are no timeouts,
  connection pools, or per-attempt deadlines (a retry budget would need them).
- No circuit breaker, bulkhead, rate limiting, or backpressure; those patterns live
  elsewhere in `system-design/`. Retries here do not consult any budget.
- The contract checker compares flat field schemas only: no nested objects, enums,
  defaults, or numeric ranges.
- No service-mesh data plane, mTLS, or distributed tracing (correlation IDs), which the
  observability and security tracks cover as design docs.
- The registry is in-process and single-node; a real one is replicated (see
  `../replication/`) and gossip-based.
