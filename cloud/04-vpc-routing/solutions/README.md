# VPC Routing From Scratch — Solutions

A complete version of the templates in the parent directory. Pure Python 3, no
dependencies. Run each file from this directory (they import each other by name):

```bash
python3 solutions/routes.py
python3 solutions/security.py
python3 solutions/simulator.py
```

## Expected output

`routes.py` — longest-prefix match over a table with a default route, a peering
route, a local route, a NAT route and a /32 host route:

```
Route table -- longest prefix wins
  10.0.1.7         -> 10.0.1.7/32     target appliance-1
  10.0.1.8         -> 10.0.1.0/24     target nat-1
  10.0.99.1        -> 10.0.0.0/16     target local
  10.1.0.1         -> 10.0.0.0/8      target pcx-peering
  192.168.1.1      -> 0.0.0.0/0       target igw-1
A deleted target becomes a blackhole: the route still matches but drops the packet
  203.0.113.9      -> blackhole, resolve = None
```

`security.py` — the same request judged by a stateful group and by a stateless NACL:

```
Security groups are stateful -- no rule is needed for the response
  request  server inbound : True
  request  client outbound: True
  response server outbound: True   (the server group has no outbound rule at all)
  response client inbound : True   (the client group has no inbound rule at all)
A NACL is stateless -- the request is allowed, the return is not
  request  inbound  443  : True
  response outbound dst 40000 (client ephemeral): False  (no ephemeral rule)
  after adding an outbound rule for 32768-60999: True
```

`simulator.py` — a full HTTPS connection, once healthy and once with the return port
blocked:

```
Packet simulator -- a whole HTTPS connection, decision by decision

Fully allowed: the SGs are stateful, the NACLs allow both directions
  allow client-sg-outbound     client egress security group
  allow client-nacl-outbound   subnet-a NACL outbound (request)
  allow route                  route for 10.0.2.20 -> 'local'
  allow server-nacl-inbound    subnet-b NACL inbound (request)
  allow server-sg-inbound      server ingress security group
  allow server-sg-outbound     server egress security group (response, stateful)
  allow server-nacl-outbound   subnet-b NACL outbound (response)
  allow route-return           route for 10.0.1.10 -> 'local'
  allow client-nacl-inbound    subnet-a NACL inbound (response)
  allow client-sg-inbound      client ingress security group (response, stateful)
  => Decision(ACCEPTED, 10 steps)

NACL outbound only allows 443: the ephemeral return is dropped
  allow client-sg-outbound     client egress security group
  allow client-nacl-outbound   subnet-a NACL outbound (request)
  allow route                  route for 10.0.2.20 -> 'local'
  allow server-nacl-inbound    subnet-b NACL inbound (request)
  allow server-sg-inbound      server ingress security group
  allow server-sg-outbound     server egress security group (response, stateful)
  DROP  server-nacl-outbound   subnet-b NACL outbound (response)
  => Decision(DROPPED at server-nacl-outbound, 7 steps)
```

Both numbers are deterministic — no seeds, no randomness — so they never change.

Three lines carry the module:

- **`10.0.99.1 -> 10.0.0.0/16 target local`**, not the default route. The default
  `0.0.0.0/0` is present and matches every address; it loses because prefix length 0 is
  the shortest possible. A first-match scan gets this right only by accident of ordering.
- **`response server outbound: True`** although the server group has no outbound rule.
  That is the stateful half: the group remembered the inbound request and allows its
  reverse. Remove that memory and a stateless implementation drops the response — the
  bug step 4 plants.
- **`DROP server-nacl-outbound`** in the second trace, after six `allow` steps. The
  request and the SG-leg of the response both passed; the stateless NACL then judged the
  response on its own and found only a rule for 443, while the client's return port is an
  ephemeral 40000.

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd cloud/04-vpc-routing
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 7/7 passing
```
