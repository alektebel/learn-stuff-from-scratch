# A VPC: Routes, Security Groups, NACLs — From Scratch

A packet-decision simulator for an AWS-shaped VPC, in pure Python 3 (standard library
only). It re-implements the three filters a packet crosses — the **route table**, the
**security groups** and the **network ACLs** — and walks a request and its response
through all of them, naming the layer that dropped.

Node `cloud-04-vpc-routing` of the [skill tree](../../skill-tree/README.md), in the
`cloud` track. Source: AWS documentation, *How Amazon VPC works*, *Route tables*,
*Security groups* and *Network ACLs* (`awsdocs:vpc`). The behaviour is restated here,
not copied.

The idea the node turns on: **routing is longest-prefix match, security groups are
stateful and NACLs are stateless.** Every planted bug below breaks one of those three,
and the checker catches it because it constructs the exact case each one gets wrong.

## What you build

| Step | File | Mechanism | Node criterion |
|---|---|---|---|
| 1 | `routes.py` | route table, longest-prefix lookup | accept: the most specific prefix wins |
| 2 | `routes.py` | overlapping prefixes with a default route | **limit:** the longest match beats `0.0.0.0/0` |
| 3 | `security.py` | security-group rule matching (protocol + port + CIDR) | accept 3, build |
| 4 | `security.py` | **stateful** groups: the response needs no rule | accept: an SG allows the response without an inbound rule |
| 5 | `security.py` | **stateless** NACL: both directions + ephemeral ports | accept: a NACL must allow both directions and ephemeral ports |
| 6 | `simulator.py` | the walk: request and response across all ten layers | build: a packet simulator that walks the decision |
| 7 | `simulator.py` | a NACL that drops the ephemeral return port | **limit:** it kills an otherwise-allowed connection |

## How to use this directory

`routes.py`, `security.py` and `simulator.py` are **templates**: each function you write
keeps its signature and docstring, has a `TODO` with a hint, and raises
`NotImplementedError`. The dataclasses, rule matching and trace plumbing are provided —
they are not the lesson. `solutions/` holds a working version for when you are stuck.

```bash
cd cloud/04-vpc-routing
python3 check.py        # what to build next; stops at the first gap
python3 check.py 4      # one step
python3 check.py 4 6    # a range
python3 check.py --all  # everything
```

`check.py` runs 7 checks against **your** code and never imports `solutions/`. The
reference traces and rule decisions are constructed in `check.py` itself, so the checker
never asks your code what the right answer is.

## The limit cases, made to bite

- **Overlapping prefixes.** Step 2 builds the same five routes in both insertion orders
  and requires the same answer for every probe. A first-match implementation passes the
  "obvious" probe and fails the moment a more specific route is added second — which is
  exactly how a route table accumulates routes in practice.
- **The ephemeral return port.** Step 7 gives the server subnet a NACL that allows
  inbound 443 and outbound 443, and nothing else. The request is allowed all the way in;
  the response dies at `server-nacl-outbound` because the client's return port is an
  ephemeral port (32768–60999), not 443. A simulator that treats the NACL as stateful,
  or that judges the return against the service port, reports success and fails the
  check. The step then adds the ephemeral rule and requires the same connection to
  succeed.

## Mutation table

The checker was itself tested: eight classic bugs were planted in copies of the
solution and each must be caught by the step named. Run
`python3 ../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`.

| Planted bug | Caught by |
|---|---|
| route lookup keeps the first match, not the longest | step 1 |
| route lookup picks the shortest prefix, so the default wins | step 2 |
| security group ignores the rule's protocol, port and CIDR | step 3 |
| security group is stateless, so the response needs a rule | step 4 |
| NACL first-match uses insertion order, not rule number | step 5 |
| NACL has an implicit allow instead of an implicit deny | step 5 |
| simulator ignores the route lookup | step 6 |
| simulator reuses the service port for the return NACL check | step 7 |

The last two are deliberately different views of the same mistake — the return path is
not really walked. One skips the route, the other skips the ephemeral port; a check
that only counted "accepted or not" on one case would miss one of them.

## Design decisions, named

Each file's docstring names the alternatives and the cost. In short:

- **`ipaddress`, not a hand-rolled int mask.** CIDR arithmetic, containment and
  normalisation already exist in the standard library; re-deriving them teaches nothing
  about routing. Cost: slower parsing, irrelevant for a route table.
- **A linear scan for the longest prefix, not a trie.** The rule "greatest `prefixlen`
  among the matching routes" stays visible on one line. Cost: it does not scale to a full
  BGP table, which is a different exercise.
- **Connection state lives beside the group, not in it.** A security group is shared by
  every instance that uses it, so the tracked connections must be per-endpoint. Cost: the
  caller keeps one `SecurityGroupSet` per instance.
- **Security groups default-deny both directions.** AWS ships a new group with an
  all-traffic egress rule, which would mask the stateful return path. Cost: the model is
  slightly stricter than a fresh AWS group, and says so — add the default egress rule
  explicitly with `add_rule("outbound", protocol="all")`.
- **The simulator returns a trace, not a bool.** `Decision` carries `accepted`,
  `dropped_at` and the ordered steps, so a failure says *which* filter decided. Cost:
  `decision.accepted` instead of a bare truth value (`__bool__` keeps `if decision:`
  working).
- **A route only delivers when its target is `local`.** Checking membership in the VPC
  CIDR would pass even when a more specific route overrides it, hiding the routing bug.
  Cost: the caller must build the local route, as AWS does automatically.

## Questions to answer before reading the solutions

1. A route table has `10.0.0.0/16 -> local` and `0.0.0.0/0 -> igw`. To the address
   `10.0.1.5`, which route wins, and by how much? Why does a first-match scan over the
   list *sometimes* give the right answer and sometimes not — what property of the
   input decides?
2. The server's security group has only an inbound rule for 443. Why is the response
   allowed outbound when there is no outbound rule at all, while an unsolicited packet
   from the server to the client is denied? What exactly is remembered, and what would
   break if the memory lived on the group instead of the endpoint?
3. A NACL allows inbound 443 and outbound 443. Walk the connection's five-tuple in and
   back. Which packet does the outbound 443 rule match, and which packet does it *not*
   match? What is the smallest rule addition that fixes it?
4. Ephemeral ports are 32768–60999 for Linux and 1024–65535 for NAT gateways. If a NACL
   allows only the Linux range, which client-side connections to a NAT gateway break,
   and on which subnet's NACL?
5. Security groups have no deny rules but NACLs do. Given that, why can you only ever
   *widen* access with a security group, and what does that let you reason about when
   two groups are attached to one instance?

## Limits

- **IPv4 only.** `ipaddress` handles IPv6, but the module fixes the default route at
  `0.0.0.0/0`. Dual-stack is left out.
- **No connection timeouts.** The stateful table is a `set` that lives for one
  `simulate_connection` call; real groups expire idle flows, and no state is shared
  between calls.
- **Rules match `(protocol, destination port, remote CIDR)`.** ICMP type/code, prefix
  lists, referenced security groups and longest-prefix-first NACL semantics are not
  modelled; a NACL rule number is a plain integer, as in AWS.
- **No NAT, peering or transit gateways as behaviour** — they appear only as route
  targets. A packet whose target is not `local` is reported as leaving the VPC, not
  translated and forwarded.
- **No packet fragmentation, MTU or path MTU discovery.** The simulator reasons about
  headers, not bytes.
