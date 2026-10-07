# Category 8: Security & Byzantine Fault Tolerance

Tracks 27–28. Everything so far assumed nodes are honest and failures are
crashes. Now: authenticate every connection and request (security), then
survive nodes that actively lie (BFT).

---

## Track 27: Security — mTLS, JWT, RBAC, Encryption

### Problem
Secure a service mesh: every connection authenticated both ways, every
request authorized, data encrypted in transit and at rest, secrets rotated —
with zero trust placed in the network ("the perimeter is dead").

### Part 1 — mTLS Between Services

Plain TLS authenticates the server; **mutual** TLS authenticates both ends.
```
   internal CA (yours)
      │ signs
      ├── cert: spiffe://cluster/svc/orders     (SAN carries identity)
      └── cert: spiffe://cluster/svc/payments

orders ══ mTLS handshake: each side presents cert, verifies against CA,
payments   checks peer identity ∈ allowed callers ══► encrypted channel
```
Build:
- A tiny CA: generate a root keypair, issue leaf certs with the service
  identity in the SAN, **short-lived** (hours, not years) — rotation instead
  of revocation as the primary mechanism.
- Handshake config: require client certs, pin the CA (never system roots for
  internal traffic), verify the peer SAN against an allow-list.
- Rotation: services reload certs from disk without restart; overlap old/new
  CA during CA rotation (trust both, issue from new).
- Identity bootstrap (the hard part — how does a node get its *first* cert?):
  platform attestation (cloud instance identity doc, k8s service account
  token) exchanged for a cert. Never a shared secret baked into images.

### Part 2 — JWT for End-User Auth

```
header.payload.signature   (base64url, signed — NOT encrypted)
payload: {sub: user_id, iss, aud, exp, iat, scope: [...]}
```
- Flow: user authenticates at the auth service → gets a short-lived
  **access token** (5–15 min, JWT) + a long-lived **refresh token**
  (opaque, stored server-side, revocable). Services verify the JWT locally
  — no per-request auth-service call. That's the entire point: stateless
  verification, and its cost: **revocation lag ≤ access-token TTL**.
- Verify properly or not at all: check signature (fetch keys via JWKS,
  cache by `kid`), `exp`, `iss`, `aud` — every one of these has a
  real-world CVE attached to skipping it. Reject `alg: none`; allow-list
  the algorithms you issue (RS256/EdDSA), never trust the header's choice.
- Key rotation: publish old+new in JWKS, sign with new; tokens outlive
  neither the key overlap nor their `exp`.
- Propagation: gateway validates the user JWT once, then forwards identity
  internally (header inside mTLS, or re-minted internal token) — services
  trust the *channel* (mTLS) plus the asserted user claims.

### Part 3 — RBAC (Authorization)

Authentication says *who*; authorization says *may they*.
```
permission = (action, resource)        e.g. (read, orders/*)
role       = named set of permissions  e.g. support-readonly
binding    = (principal, role, scope)  e.g. (alice, support-readonly, tenant:42)

check(principal, action, resource, scope) → allow/deny
```
- Deny by default; deny overrides allow; every check emits an audit log
  event (who, what, decision, why — which binding matched).
- **Scope/tenancy** is where real systems break: every check carries the
  tenant; forgetting it = cross-tenant data leaks (the most common real
  vulnerability class in multi-tenant systems).
- Service-to-service authz: the mTLS identity is the principal
  (`payments` may call `orders.charge`, `analytics` may not).
- Cache decisions with short TTL; invalidate on binding change (Track 10
  discipline). Keep the policy store strongly consistent (Track 8).

### Part 4 — Encryption at Rest

**Envelope encryption** — the universal pattern:
```
KMS root key (HSM, never leaves)
   └─ encrypts → DEK (data encryption key, random per object/table)
                    └─ encrypts → your data (AES-256-GCM)
store: ciphertext + encrypted-DEK + nonce + key-version
```
- Rotating the root = re-encrypt the small DEKs, not the data.
- AEAD (GCM) only — you need integrity, not just secrecy; **never reuse a
  (key, nonce) pair** (random 96-bit nonces or counters).
- Field-level encryption for the crown jewels (SSNs) on top of disk-level;
  searchability requires blind indexes (HMAC of value) — equality only.
- Secrets management: no secrets in env vars/images/repos; a secrets service
  (itself a Track 8 KV + envelope encryption) with short leases and audit.

### Threats & Failure Modes
| Threat/Failure | Mitigation |
|---|---|
| Stolen service cert | short TTL; per-workload identity limits blast radius |
| Stolen JWT | short exp; refresh rotation with reuse detection (stolen refresh token used twice → kill session family) |
| CA compromise | offline root + online intermediate; rotate intermediate |
| Replay of a captured request | TLS prevents on-channel; idempotency keys + `iat`/`jti` for tokens |
| Confused deputy (svc A tricked into using its authority for caller B) | propagate end-user identity; authorize the *user*, not just the calling service |
| KMS outage | cached DEKs allow reads; writes may degrade — decide policy explicitly |
| Clock skew breaks `exp`/cert validity | small leeway (≤60s), NTP monitoring (Track 26) |

### Milestones
1. Mini CA + mTLS between two Track 4 RPC services; SAN allow-list; reject
   wrong/expired/self-signed certs in tests.
2. Live cert rotation, then live CA rotation, under load, zero dropped requests.
3. JWT issuer + JWKS + verifying middleware; full negative-test suite
   (`alg:none`, wrong `aud`, expired, unknown `kid`, tampered payload).
4. RBAC service with tenant scoping + audit log; property test: no check
   path bypasses tenancy.
5. Envelope encryption for the Track 14/15 storage engine's values; root-key
   rotation without rewriting data.

---

## Track 28: Byzantine Fault Tolerance

### Problem
Raft (Track 7) survives nodes that **crash**. Now survive nodes that
**lie** — send conflicting messages to different peers, vote twice, forge
state — due to compromise, bugs, or bit corruption. Required for
multi-organization systems (blockchains, cross-company replication) where
"trust the operator" doesn't hold.

### The Fundamental Bound
Crash tolerance: N = 2f+1 (majority quorums).
Byzantine tolerance: **N = 3f+1** — e.g. 4 nodes tolerate 1 traitor.
Why: quorums of size 2f+1 out of 3f+1 guarantee any two quorums intersect
in ≥ f+1 nodes, hence **at least one honest node** in every intersection —
that honest overlap is what makes lying detectable across phases.

All messages are **signed** (Track 27's machinery): a Byzantine node can
lie about its own state but cannot forge others' messages.

### PBFT (the design to build)
Roles: one **primary** (leader) per **view** v; replicas 0..N-1; primary =
v mod N.

```
client   primary    r1      r2      r3
  │──req──►│
  │        │─PRE-PREPARE(v, n, digest(m))──► all      primary assigns seq n
  │        │◄────── PREPARE(v,n,d) ────────► all-to-all
  │        │   [2f+1 matching PREPAREs incl. own = "prepared":
  │        │    no two honest nodes prepare different m at (v,n)]
  │        │◄────── COMMIT(v,n,d) ─────────► all-to-all
  │        │   [2f+1 matching COMMITs = "committed":
  │        │    survives view changes]
  │◄─reply─┤  each replica executes in seq order, replies directly
  client accepts when f+1 MATCHING replies arrive  (≥1 honest guaranteed)
```

Why **three** phases where Raft needs one round: prepare establishes
agreement on order *within* a view; commit ensures that agreement survives
*across* view changes even when the primary was lying. The all-to-all
O(N²) message pattern is the price of not trusting the primary's word.

### View Change (replacing a lying/silent primary)
- Replicas time out waiting for progress → broadcast
  `VIEW-CHANGE(v+1, P)` where P = signed proof of every prepared request.
- New primary (v+1 mod N) collects 2f+1 view-change messages, re-issues
  PRE-PREPAREs for every request proven prepared → nothing committed is
  ever lost, even if the old primary equivocated.
- Timeouts double each failed view (like Raft's randomized timeouts, but
  deterministic rotation — randomness can't be trusted to a traitor).

### What a Byzantine Node Can Try (and why it fails)
| Attack | Defense |
|---|---|
| Primary sends different requests to different replicas at same (v,n) | prepare quorums intersect in an honest node → at most one digest can prepare |
| Replica votes for two values | signed votes = evidence; quorum intersection makes double-votes ineffective |
| Primary censors a client | client broadcasts to all after timeout → replicas trigger view change |
| Old-view messages replayed | (v, n) in every message + sequence watermarks |
| Forged replies to the client | client waits for f+1 matching signed replies |
| Slowloris primary (barely-alive) | progress timeouts, view change on missed deadlines |

### Practical Notes
- Checkpointing: every k sequence numbers, replicas exchange signed state
  digests; 2f+1 matching = stable checkpoint → garbage-collect logs (the
  Track 7 snapshot idea, adversarial edition).
- State transfer for lagging replicas: fetch state matching a stable
  checkpoint digest — the digest makes a lying donor detectable.
- Cost consciousness: BFT ≈ 3× replication + O(N²) messages + signatures
  everywhere. Within one trust domain, Raft + Track 27 security is almost
  always the right call; BFT pays off only across trust domains. Say this
  out loud in any design review.
- Modern descendants: HotStuff linearizes the communication (O(N)) and
  pipelines phases — read after PBFT works.

### Milestones
1. Normal-case PBFT (no view changes) over signed Track 4 RPC, N=4:
   client → committed → f+1 replies.
2. Byzantine test harness: a configurable traitor replica (equivocate,
   stay silent, corrupt digests); safety must hold with f=1.
3. View change: kill or corrupt the primary mid-stream; prepared requests
   survive into the new view; liveness resumes.
4. Checkpoints + log GC + state transfer for a rebuilt replica.
5. The final boss: randomized adversary fuzzing (random traitor behavior,
   random partitions) for hours; a checker asserts all honest replicas'
   histories are identical and every client-acked op is in them.

---

## What Carries Forward
- Security is not a track, it's a retrofit: go back and put mTLS + authz on
  the KV store (8), the broker (12), the DFS (16), the scheduler (19).
- Quorum-intersection reasoning (2f+1 of 3f+1) is the same tool you used
  for Raft majorities — now you can derive quorum systems for any fault model.
- With all 28 tracks done, you've built the full stack: transport →
  consensus → storage → scaling → coordination → data systems →
  observability → security. Every real system you meet now decomposes into
  parts you have personally implemented.
