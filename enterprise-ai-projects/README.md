# Enterprise AI projects — implementation guides

Twelve projects about the part of AI work that is not the model: legacy data, tenant
isolation, privacy, air-gapped delivery, proving value, reliability, identity,
degradation, compliance, agent-to-ERP plumbing, safe rollout, and recovery.

**These are guides, not solutions.** No code, no templates, no `check.py`. Each guide
says what to build, which decisions it actually contains, what real system to build it
against, where it breaks, and what to read. Writing the code is the exercise.

| # | Project | Guide |
|---|---|---|
| 1 | Bi-directional legacy sync engine | [01-legacy-sync.md](01-legacy-sync.md) |
| 2 | Zero-trust multi-tenant RAG | [02-multitenant-rag.md](02-multitenant-rag.md) |
| 3 | PII redaction & unmasking proxy | [03-pii-proxy.md](03-pii-proxy.md) |
| 4 | Air-gapped one-click deployer | [04-airgapped-deploy.md](04-airgapped-deploy.md) |
| 5 | ROI & usage telemetry dashboard | [05-roi-telemetry.md](05-roi-telemetry.md) |
| 6 | Idempotent webhook reconciler | [06-webhook-reconciler.md](06-webhook-reconciler.md) |
| 7 | Enterprise SSO & SCIM bridge | [07-sso-scim.md](07-sso-scim.md) |
| 8 | AI fallback & degradation gateway | [08-fallback-gateway.md](08-fallback-gateway.md) |
| 9 | Automated compliance auditor | [09-compliance-auditor.md](09-compliance-auditor.md) |
| 10 | Custom MCP server for legacy ERPs | [10-mcp-legacy-erp.md](10-mcp-legacy-erp.md) |
| 11 | Shadow traffic evaluator | [11-shadow-evaluator.md](11-shadow-evaluator.md) |
| 12 | 3 AM incident runbook repo | [12-incident-runbook.md](12-incident-runbook.md) |

---

## Read this before picking one

### Build against a real system, not a mock

The list these projects came from does not say where you get a 20-year-old Oracle
database, an Okta tenant, or an SAP instance. That omission is not a detail — it is the
difference between a project and a blog post. A mock you wrote yourself cannot surprise
you, and being surprised by someone else's system *is the skill being demonstrated*.

Every guide names a real stand-in you can run locally. Summary:

| Project | Stand-in | Why this one |
|---|---|---|
| 1, 10 | `gvenzl/oracle-free` (Oracle 23c Free) or `mcr.microsoft.com/mssql/server` | Real SQL dialect, real locking, real driver pain. **Not** `gvenzl/oracle-xe`, which its author deprecated in favour of `oracle-free` |
| 1 | Debezium + Kafka Connect | Real CDC, and it forces you to enable supplemental logging like everyone else does |
| 2 | Postgres + `pgvector`, or Qdrant | RLS is a real database feature; you can test it adversarially |
| 3 | Microsoft Presidio | Real detection with real false negatives, which a regex will hide from you |
| 4 | k3s or kind + Helm + Zarf | Zarf is what people actually use for this |
| 5 | OpenTelemetry + the GenAI semantic conventions | A real schema, so your metrics mean the same as everyone else's |
| 6 | Any broker with real redelivery: Redis Streams, NATS JetStream, RabbitMQ | Redelivery semantics you did not choose |
| 7 | Keycloak (SAML + OIDC natively; SCIM is a preview feature behind a flag as of 26.6, community extensions otherwise) | Free, and speaks the actual protocols |
| 8 | Anthropic/OpenAI API + Ollama for the local tier | Real timeouts, real rate limits, real 529s |
| 9 | kube-bench, Conftest/OPA, Prowler, Trivy | Real controls with real IDs, not invented ones |
| 10 | `sapse/abap-cloud-developer-trial` on Docker Hub, or ERPNext/Odoo | SAP's own trial image. Three-month licence, extendable via `SLICENSE` + minisap, system key `A4H` |
| 11 | Envoy `request_mirror_policies`, or Istio `mirrorPercentage` | Mirroring is a solved problem at the proxy; the hard part is elsewhere |
| 12 | Your own deployment of any project above, with faults injected | A runbook for a system you did not build is fiction |

### Three of these are largely already in this repo

Each of the three guides names what you already have and where. The guides are written
in full anyway, but do not rebuild what is sitting there:

- **Project 6** — `system-design/message_queue.py` (retries, backoff, DLQ),
  `system-design/idempotency_keys.py`, `aws-from-scratch/sqs.py` (visibility timeouts),
  `aws-from-scratch/dynamodb.py`. The reliability core is done; the reconciler is not.
- **Project 8** — `system-design/circuit_breaker.py`. The breaker is done; model-aware
  routing and the semantics of a degraded answer are not.
- **Project 12** — `deploy-and-debug/` has `RUNBOOK.md`, `rollout.py` (canary,
  budget-based auto-rollback) and `diagnose.py` (11 injected faults). The gap is
  coverage and the fact that an untested runbook is not a runbook.

### What these projects actually demonstrate

Three of the twelve claim more than they deliver, and the guides say so where it matters:

- **Project 3** does not show that you "understand HIPAA/SOC2". Neither framework has a
  control called "redaction proxy". What it shows is that you understand redaction is a
  *lossy* mitigation — it degrades the model precisely on the entities you masked — and
  that the unmask map is itself a PII store, so you moved the problem rather than solving
  it. That is a better thing to be able to say.
- **Project 5** is not primarily an engineering project. The dashboard is the easy half.
  The hard half is defining "hours saved" so that it survives a hostile CFO, and no
  amount of code rescues a metric that was invented.
- **Project 12** is a documentation and testing project wearing engineering clothes. That
  is not a criticism — untested runbooks are the normal case and fixing that is real
  work — but do not expect it to look like the others.

### How each guide is laid out

- **What it is** — one paragraph, precise about scope.
- **What it actually demonstrates** — the claim, corrected where the original overstates.
- **The substrate** — the real system to build against, with concrete images and versions.
- **The decisions** — the choices the project actually contains, each with its cost.
  A design decision listed without its cost has been described as marketing.
- **Where it breaks** — the limit case that motivates the next version. Find it before
  you build the machinery that handles it.
- **Resources** — links, marked `[v]` where verified while writing.

### Order

There is no required order, but 6 → 8 → 12 is the reliability spine and the cheapest
place to start; 2 → 3 is the privacy pair and they share a threat model; 1 → 10 is the
legacy-data pair and they share a substrate, so build the database once. 4, 7 and 9 are
the "will enterprise IT let this in" cluster.

Start with the cluster you are worst at, not the one that sounds best in a summary.
