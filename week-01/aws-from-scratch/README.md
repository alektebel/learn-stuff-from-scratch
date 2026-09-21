# AWS From Scratch

Learn AWS by implementing toy versions of its services in pure Python — and, more
usefully, by reproducing the failures that make them confusing in practice.

## Scope, honestly

AWS has **200+ services**. Implementing all of them would be neither feasible nor
useful: most are variations on a mechanism another service already has, or thin
management layers with nothing to learn from.

So this directory implements the **eight distinct mechanism families** that everything
else is built from, then [maps the rest onto them](#the-rest-of-aws-and-what-it-is-made-of),
and finally [puts a meter and a price on all of it](#the-bill). One mechanism deeply
beats nine gestured at.

| Service | The mechanism | The thing people get wrong |
|---|---|---|
| `iam.py` | Policy evaluation | Explicit Deny beats everything, in any order |
| `s3.py` | Object storage | `DELETE` does not delete in a versioned bucket |
| `sqs.py` | Leased queues | Redelivery is the design, not a bug |
| `dynamodb.py` | Partitioned KV + capacity | A hot key throttles an idle table |
| `lambda_svc.py` | Ephemeral compute | Warm state survives; concurrency is a quota |
| `sns.py` | Fanout + filtering | A missing attribute never matches |
| `kms.py` | Envelope encryption | Rotation re-encrypts keys, never data |
| `vpc.py` | Networking | Security groups are stateful; NACLs are not |
| `capstone.py` | All of it, wired together | Failures surface a layer from their cause |

Then three more files put a **meter and a price** on all of it, because a cloud service
you cannot cost is one you cannot make decisions about:

| File | The mechanism | The thing people get wrong |
|---|---|---|
| `pricing.py` | Price sheet + bill arithmetic | Two rounding rules that look like one |
| `billing.py` | Metering the services above | Request count is not message count |
| `optimize.py` | Crossovers, not rules of thumb | Every cost rule has a regime where it is wrong |

---

## How to use this directory

```bash
cd aws-from-scratch
python3 check.py            # what to build next
python3 check.py            # re-run after each function
```

**24 graded checks** against your code. Red `✗` names the likely cause:

```
  ✗  1. iam.py               explicit deny > allow > implicit deny
      an explicit Deny must beat any Allow, in EITHER order. Policies are
      evaluated as a set — collect all denies first, then allows. If order
      changed your answer, you are iterating and letting the last match win,
      like a firewall.
```

---

## The eight mechanisms

### `iam.py` — the one to do first

Everything else gates on it, and the rule is three lines:

```
1. An explicit DENY anywhere always wins.
2. Otherwise, an explicit ALLOW grants access.
3. Otherwise, DENY (implicit).
```

**Design decision:** partition statements by effect rather than evaluating in order.
That is what makes policy order irrelevant — a property worth proving to yourself, since
it is what makes a large policy set tractable at all.

Also here: conditions (which **AND across keys, OR within one**, and fail closed on a
missing key), `NotAction` (wider than it looks), permissions boundaries (which subtract,
never grant), and STS `AssumeRole` — where **both** the caller's policy and the role's
trust policy must agree.

### `s3.py` — it is flat

`reports/2024/q1.csv` is one opaque key. Folders are invented at list time by splitting
on a delimiter. There is no directory object, which is why an empty folder cannot exist
and renaming one is O(objects).

**The limit case:** in a versioned bucket, `DELETE` pushes a *delete marker*. A plain
`GET` now 404s while the bytes sit underneath, still billed. Only deleting a specific
`version_id` frees anything — which is why "I emptied the bucket" and "the bill went
down" are different claims.

Also: multipart ETags end in `-<part count>` and are **not** the object's MD5.

### `sqs.py` — at-least-once, and why

`receive()` is a **lease**, not a read. Only `delete()` removes a message.

**The limit case you must build:** a consumer whose work outlasts the visibility timeout.

```
t=0   consumer A receives 'expensive-job'
t=11  consumer B receives 'expensive-job'   <- A's lease expired
t=12  A finishes and deletes: False          <- its handle is stale
```

Two consumers processed one message. That is the queue choosing duplication over loss.
Your handler is idempotent or it is wrong — there is no third option.

### `dynamodb.py` — the partition key decides everything

**The limit case:** 40 WCU across 4 partitions is 10 per partition. Write 30 items under
one partition key and it throttles after 10 — with the table 75% idle. *Adding capacity
does not help.* The key has to spread.

Also: `query` reads one partition; `scan` reads everything and filters afterwards, so a
scan returning 3 of a million items costs a million reads.

### `lambda_svc.py` — the container outlives your invocation

Anything outside the handler **survives**: excellent for a connection pool, a disaster
for a cache you assumed was empty.

**The limit case:** reserved concurrency is a ceiling *and* a floor. Reserving 6 of 10
for one function silently drops every other function in the account to 4 — they were
never touched.

And sync vs async failure is the same bug with a different blast radius: sync returns the
error to the caller; async retries **three times**, then dead-letters.

### `sns.py` — push, and the filter that runs at the topic

SNS pushes and drops on failure; SQS buffers. That is why `SNS → SQS → consumer` is the
standard shape rather than an accident.

Filter policies use the same rule as IAM conditions — AND across keys, OR within one, and
a **missing attribute never matches** — and catch people the same way. Plus EventBridge,
which matches the *shape* of a nested event, and fires every matching rule with no
deduplication.

### `kms.py` — envelope encryption

KMS generates a data key, hands it to you twice (plaintext + wrapped), and forgets it. You
encrypt locally. **One KMS call per object, not per byte** — which is why the 4KB payload
limit never constrains you.

**The limit case:** rotation creates a new key *version*; old versions are retained so old
ciphertext still decrypts. Zero bytes of data are re-encrypted. Delete a version and that
ciphertext is unrecoverable forever — which is why key deletion has a mandatory waiting
period.

> The cipher here is XOR and the file says so loudly. **Not encryption.** The envelope
> *structure* is the lesson; substitute AES-GCM and nothing about the shape changes.

### `vpc.py` — stateful vs stateless

The clearest demonstration in the directory. Identical intent, opposite outcome:

```
Security group:
  SG inbound    203.0.113.5 -> :443  allow
  SG reply      implicitly allowed (stateful)
  connection: WORKS

Network ACL, same rules:
  NACL inbound  203.0.113.5:* -> :443  allow (rule 100)
  NACL outbound reply -> 203.0.113.5:49152  DENY (no rule matched)
  connection: FAILS
```

The request was allowed both times. The NACL dropped the **reply**, which goes to an
ephemeral port nobody remembers to allow. This is why `test_connection` models a whole
connection rather than a rule — evaluate only the request and the bug is invisible.

Also: a `/28` gives **11** usable hosts, not 16 (AWS reserves 5), and route tables match
the longest prefix, not the first entry.

### `capstone.py` — the failures compose too

`S3 → SNS → SQS → Lambda → DynamoDB`, KMS on the payload, IAM on every call.

The result worth sitting with:

```
=== A failure surfaces one layer away from its cause ===
  12 uploads -> queue depth 12
  drain: {'processed': 5, 'throttled': 0, 'failed': 5}
```

Five Lambda invocations errored. The **cause** is DynamoDB — every document shares
`tenant='acme'`, so they hash to one partition holding a quarter of the table's capacity.
The alarm fires on Lambda; the fix is in the data model. That mismatch between where a
failure is *visible* and where it is *caused* is most of what makes distributed debugging
hard.

---

## What you will learn deeply, and what you will not

An honest answer, per file. "Deep" here means you could re-derive the behaviour and
predict what a real outage looks like; "partial" means you have the core mechanism and
are missing the operational surface around it.

| Service | Depth | What you genuinely own afterwards | What is deliberately missing |
|---|---|---|---|
| **IAM / STS** | **deep** | The evaluation order, why Deny wins in any order, why a missing condition key fails closed, boundaries as a cap rather than a grant, and trust policies as the direction that protects you from another account | Resource-based policies (bucket policies, key policies), SCPs and org-level denies, ABAC and policy variables, session tags, access analyzer |
| **SQS** | **deep** | Visibility timeouts as *leases*, why at-least-once is the design and not a defect, redelivery, DLQ thresholds, FIFO groups and deduplication windows | Long polling as an API parameter, batch APIs, per-message delays, extending a visibility timeout mid-work |
| **DynamoDB** | **deep on the part that matters** | Composite keys, why a hot partition throttles an idle-looking table, query versus scan as an O(result) versus O(table) distinction, conditional writes, GSIs as separate asynchronous tables, and both billing modes | LSIs, transactions, TTL, adaptive capacity and burst credits, global tables, PartiQL, streams beyond a list |
| **KMS** | **deep on envelope encryption** | Why the master key never touches your data, encryption context as authenticated metadata, and why rotation re-encrypts *keys* and never *data* | Grants, key policies, asymmetric and HMAC keys, multi-region keys, custom key stores, and real cryptography — this uses XOR |
| **S3** | **partial** | The flat keyspace and why "folders" are a listing illusion, ETags including the multipart surprise, versioning and delete markers, prefix listing costs | Storage classes and lifecycle transitions (priced in `optimize.py`, not implemented), replication, presigned URLs, Object Lock, strong-consistency semantics, event notification fan-out beyond the capstone |
| **Lambda** | **partial** | Cold starts and warm state, the execution environment outliving your invocation, concurrency as an account-wide quota, async retry and dead-lettering | VPC-attached ENI cold starts, layers, provisioned concurrency, SnapStart, event source mapping backpressure, response streaming |
| **SNS / EventBridge** | **partial** | Fanout, filter policies evaluated *at the topic*, why a missing attribute never matches, and structural pattern matching | FIFO topics, delivery retry policies and backoff, archive and replay, schema registry, cross-account buses |
| **VPC** | **partial** | CIDR arithmetic, longest-prefix routing, and the stateful/stateless distinction that explains most "the rule looks right" tickets | NAT (priced but not implemented), VPC endpoints, peering and Transit Gateway, DNS resolution, flow logs, IPv6 |
| **Cost and billing** | **deep** | The two rounding rules, graduated tiers, fixed versus variable lines, unit economics, and the crossover behind every cost rule — computed from the price sheet rather than recalled | Savings Plans and Reserved Instances, EDP discounts, Cost Explorer's own data model, tagging enforcement, anomaly detection |

The pattern is worth noticing. The four **deep** rows are the ones where the mechanism
*is* the service. The four **partial** rows are services whose core is simple and whose
difficulty lives in an operational surface — storage classes, cold-start topology, retry
policy, network plumbing — that is genuinely large and genuinely learnable elsewhere.
Knowing which kind of service you are looking at is most of what "knowing AWS" means.

---

## The bill

The last three files are the ones the other eight were quietly built for. Every service
above already counts what it does — `s3.stats`, `table.stats`, `function.stats` — because
a meter is a first-class part of a cloud service. These files read those counters and
turn them into money.

### `pricing.py` — two rounding rules, and why a bill is a group-by

The price sheet is given to you; retyping a price list teaches nothing. What you build is
the arithmetic, and it starts with a distinction that costs people real money:

- **Pro-rata** dimensions. "$0.005 per 1,000 PUTs" means one PUT costs $0.000005. You are
  not rounded up to a thousand.
- **Quantised** dimensions. A 1.1 KB DynamoDB write costs **2** WCU. A 100 KB object in
  Standard-IA is billed as **128 KB**. An object stored one day in Deep Archive is billed
  for **180 days**.

Then `Bill` — a list of line items rather than a total, because "how much" is never the
question. `Bill.scaled()` is the one to get right: fixed lines (a NAT gateway hour, a KMS
key month, provisioned capacity, an idle poller) do **not** scale with traffic.

```
   traffic        total        fixed   fixed %
    0.001x       $36.06       $35.85     99.4%
        1x      $242.52       $35.85     14.8%
      100x   $20,702.53       $35.85      0.2%
```

Same architecture, opposite advice at each end. That is why "should we use X" has no
answer without a volume attached.

### `billing.py` — metering what you built

Nothing here reaches inside a service to recompute anything; it reads the counters and
prices them. Measured results, all from the toy services:

- **The versioning trap.** 200 objects put, 200 deleted. `list_objects` returns 0 keys —
  the console is empty — and the billable bytes did not move, plus 200 delete markers.
- **The minimum object size.** The *same* 8 MB as 2,000 × 4 KB objects and as 8 × 1 MB
  objects, per GB-month:

  | class | 2,000 × 4 KB | 8 × 1 MB |
  |---|---|---|
  | standard | $0.021 | $0.021 |
  | standard_ia | **$0.364** | $0.012 |
  | glacier_ir | $0.345 | $0.011 |

  Standard-IA's sticker price is half Standard's. On 4 KB objects it bills at 32× that,
  because every object under 128 KB is billed as 128 KB — so "move the small cold files
  to IA to save money" makes them **17× more expensive than Standard**.
- **The minimum duration.** Deep Archive costs the same for 1 day as for 180.
- **Where the request count is not the message count.** The same 1,000 SQS messages:

  | strategy | work requests | idle requests |
  |---|---|---|
  | short poll, receive 1 | 3,000 | 50,000 |
  | long poll, receive 1 | 3,000 | 43 |
  | long poll, receive 10 | 1,200 | 43 |

  Identical work done. The expensive setting is the default, and the idle line is *fixed*
  — a queue that goes quiet gets **more** expensive per message.
- **Which KMS line is bigger is the diagnosis.** 2,000 records through `EnvelopeCipher`
  costs $1.01: a dollar of key and six-tenths of a cent of requests. 500 keys and *zero*
  API calls costs $500. Key sprawl is an org-chart decision that arrives as a line item.

### `optimize.py` — crossovers, not rules of thumb

Every section names the decision as the number where the advice *flips*, derived from the
price sheet rather than recalled:

- **DynamoDB provisioned vs on-demand: 14.44% utilisation** — and identically so for reads
  and for writes, because AWS priced both modes with the same ratio. A workload with a
  sharp daily peak sits at 5–10% while feeling busy all day, which means on-demand — the
  mode everyone calls expensive — is the cheaper one for it. Provisioned capacity is not a
  discount; it is a bet that you will use what you reserved.
- **Lambda memory.** One formula — `duration = io_wait + cpu_work × 1769/memory` — and
  three opposite answers:

  | shape of work | cheapest | fastest | cost, 128 MB → 10 GB |
  |---|---|---|---|
  | CPU-bound | 1769 MB | 10240 MB | **1.00×** (flat) |
  | mixed | 128 MB | 10240 MB | 4.95× |
  | I/O-bound | 128 MB | 10240 MB | 41.94× |

  For CPU-bound work the cost line is *flat*: twice the memory runs in half the time, so
  the GB-seconds cancel. Leaving that function at the 128 MB default buys a 12× slower
  function at no saving whatsoever. For I/O-bound work every extra MB is billed against a
  wait you cannot shorten.
- **NAT gateway vs gateway endpoint: no crossover at all.** An S3/DynamoDB gateway
  endpoint is free at every volume, forever. At 10 TB/month of S3 traffic that is $548
  against $0, and the fix is a route-table entry that cannot change behaviour. Interface
  endpoints *are* priced, and there the crossover is real: routing 30 services privately
  across 3 AZs buys 90 endpoints to replace 3 NAT gateways.
- **Storage class as a function of use, not temperature.** The decision table has two
  axes — reads per month and retention — and neither is "how cold does this feel". And
  the model deliberately does not price the axis that decides it: Deep Archive answers a
  read in 12 hours. A cost model with only dollars in it will confidently recommend an
  outage.
- **Reading the bill.** The capstone pipeline, scaled to a million uploads a month, with
  the candidate changes ranked by dollars saved:

  ```
  change                                        line       saves   of bill
  drop to one NAT gateway (and lose an AZ)    $98.55      $65.70     44.4%
  S3 gateway endpoint (a route-table entry)   $11.25      $11.25      7.6%
  CloudFront in front of the downloads        $22.50      $10.12      6.8%
  long polling on both queues                  $0.21       $0.21      0.1%
  Graviton on the indexer                      $0.01   $0.002431      0.0%
  BatchWriteItem, 10 writes per call           $0.10          $0      0.0%
  ```

  Two rows repay a second reading. The route-table entry is free to make and beats every
  code change on the list. And `BatchWriteItem` saves **exactly nothing** — it is one API
  call, but DynamoDB still bills a write unit per item. Batching is a throughput
  optimisation there and a cost optimisation in SQS. Same word, two services, opposite
  answers.
- **The question metering cannot answer.** Allocating that shared bill across six tenants
  by request count and by bytes gives answers 6× apart at the ends, and nothing in the
  counters can settle it: the NAT gateway and the KMS key are shared, and no meter
  anywhere says whose fault they are. Pick a rule, write it down, and understand that the
  rule you picked is now the incentive your teams optimise against.

> Prices are approximate, us-east-1, and dated in `PRICES`. They are there so the
> **ratios** are right. Check the current price list before you spend money.

---

## The rest of AWS, and what it is made of

Rather than 200 shallow files, here is the honest map. Most services are a mechanism you
have already built, with different packaging:

| Service | Is essentially | Built in |
|---|---|---|
| Kinesis, MSK | A queue with ordered shards and replay | `sqs.py` + partitioning |
| ECS, Fargate, App Runner | Lambda with longer-lived containers | `lambda_svc.py` |
| Step Functions | A state machine over Lambda invocations | `lambda_svc.py` |
| RDS, Aurora | A database; the AWS part is failover and backups | — |
| ElastiCache | A cache; see [`system-design/`](../../reference/system-design/) | — |
| EFS, FSx | A filesystem, so *not* S3's flat model | `s3.py` (by contrast) |
| CloudFront | A CDN; edge caching and invalidation | [`context-caching/`](../../week-03/context-caching/) |
| ELB, API Gateway | Routing + throttling + health checks | `vpc.py`, `lambda_svc.py` |
| Route 53 | DNS with health-checked routing policies | [`dns-server/`](../../week-14/dns-server/) |
| Secrets Manager, Parameter Store | KMS plus versioning and rotation | `kms.py` |
| Cognito | STS with a user directory in front | `iam.py` |
| CloudTrail | The audit log the capstone writes | `capstone.py` |
| CloudWatch, X-Ray | Metrics, alarms, budgets, tracing | [`deploy-and-debug/`](../../week-04/deploy-and-debug/) |
| Organizations, SCPs | IAM evaluation with another deny layer | `iam.py` |
| CloudFormation, CDK | A dependency graph with rollback | — |
| Glue, Athena, EMR | Query planning over object storage | `s3.py` |
| SageMaker, Bedrock | Model serving | [`context-caching/`](../../week-03/context-caching/) |

Two of those rows — **CloudFormation's dependency graph with rollback**, and **Kinesis's
ordered shards with replay** — have genuinely distinct mechanisms and are the best
candidates for a ninth and tenth file. The extensions list below starts there.

## What this is not

- **Not a mock for testing against.** Use [LocalStack](https://localstack.cloud) or
  [moto](https://github.com/getmoto/moto) for that; they aim for API fidelity, this aims
  for understanding.
- **Not API-compatible.** No boto3 surface, no XML, no signatures, no regions, no
  eventual-consistency delays on the control plane.
- **Not secure.** `kms.py` uses XOR. Nothing here is real cryptography.
- **Not a billing system.** `pricing.py` carries an approximate, dated us-east-1 price
  sheet so the *ratios* are right. No Savings Plans, no Reserved Instances, no enterprise
  discounts, no regional variation. Do not quote these numbers at anyone.

## Extensions worth trying

1. **CloudFormation** — a dependency graph, topological ordering, and rollback on failure.
   The interesting part is what happens when rollback *itself* fails.
2. **Kinesis** — ordered shards with a retention window and replay from a sequence number.
   Contrast with `sqs.py`: replay changes the consumer contract completely.
3. **Add IAM to every other file.** Right now only the capstone authorises. Wiring
   `evaluate()` into `s3.put_object` and friends is what a real service does.
4. **S3 lifecycle rules** — actually *implement* the transitions `optimize.py` only
   prices: move to a colder class after N days, expire non-current versions, abort
   incomplete multipart uploads. Then bill the same bucket before and after, and check the
   answer against `best_storage_class`.
5. **DynamoDB burst credits and autoscaling.** `dynamodb_crossover` assumes you provision
   for the peak. Model burst credits and an autoscaler with a lag, and find how much of
   the 14.4% gap the lag gives back.
6. **Cross-account access.** A bucket policy on one side, an identity policy on the other,
   and a role in between — then work out which of the three is actually granting it.
7. **A cost anomaly detector.** Bill the same account on consecutive days and alert on the
   line item that moved, not the total. That is the whole product, and it is twenty lines
   on top of `Bill.by_dimension()`.
8. **Tag-based showback.** Give every resource a tag, allocate the shared lines by a rule
   you defend in writing, and see how quickly someone games it.

---

## Structure

```
aws-from-scratch/
├── README.md
├── check.py              # progress checker — run this first
├── iam.py                # templates with TODOs and DESIGN DECISION blocks
├── s3.py
├── sqs.py
├── dynamodb.py
├── lambda_svc.py
├── sns.py
├── kms.py
├── vpc.py
├── capstone.py
├── pricing.py            # the price sheet is given; the arithmetic is not
├── billing.py            # meters the eight services above
├── optimize.py           # the crossovers, and reading a bill
└── solutions/
```

```bash
cd solutions
python3 iam.py            # the three-line rule, and STS in both directions
python3 s3.py             # flat keys, ETags, delete markers
python3 sqs.py            # the visibility-timeout limit case
python3 dynamodb.py       # hot partitions, query vs scan
python3 lambda_svc.py     # cold starts, concurrency, async retries
python3 sns.py            # fanout, filter policies, EventBridge
python3 kms.py            # envelope encryption and rotation
python3 vpc.py            # stateful vs stateless, side by side
python3 capstone.py       # the pipeline and its failures
python3 pricing.py        # rounding rules, tiers, fixed vs variable
python3 billing.py        # the same services, now with a meter on them
python3 optimize.py       # every rule of thumb, replaced by its crossover
```

Pure Python 3 standard library. Everything runs in about a second.

## Related directories

- [`dynamo-paper/`](../../week-10/dynamo-paper/) — the 2007 paper DynamoDB is built on
- [`deploy-and-debug/`](../../week-04/deploy-and-debug/) — operating and debugging this kind of system
- [`system-design/`](../../reference/system-design/) — the patterns underneath most of these services
- [`PHILOSOPHY.md`](../../PHILOSOPHY.md) — why this repo is built the way it is
