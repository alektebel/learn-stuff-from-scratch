# AWS From Scratch — Solutions

Complete implementations of every template in the parent directory. Pure Python 3
standard library; everything runs in about a second.

```bash
python3 iam.py  s3.py  sqs.py  dynamodb.py  lambda_svc.py  sns.py  kms.py  vpc.py
python3 capstone.py
python3 pricing.py  billing.py  optimize.py
```

## What each file demonstrates

### `iam.py`
The three-line rule, with the property that matters:

```
admin alone                           ALLOW
admin + guardrail                     DENY  explicit Deny in Guardrail (NoDeletes)
guardrail + admin (order swapped)     DENY  explicit Deny in Guardrail (NoDeletes)
```

Order does not change the answer, because statements are partitioned by effect rather
than walked in sequence. Conditions AND across keys and OR within one, and a **missing
context key never matches** — conditions fail closed.

STS checks **both** directions: an outsider whose own policy allows `sts:AssumeRole` is
still refused by the role's trust policy.

### `s3.py`
Flat keys with delimiter-invented folders; multipart ETags ending `-3`; and versioning:

```
delete -> pushed marker v000003
get   -> NoSuchKey: doc.txt (a delete marker is on top)
versions still stored: 3 (22 bytes, all billable)
versioned get -> b'version one'
```

Plus abandoned multipart uploads, which nothing lists by default and everything bills.

### `sqs.py`
The lease, and the duplicate it creates:

```
t=0   consumer A receives 'expensive-job' (receive_count=1)
t=11  consumer B receives ['expensive-job'] — the lease expired
t=12  A finishes and deletes with its stale handle: False
```

**Note the implementation detail that makes this work:** `receive()` returns a `copy` of
the message so each consumer holds its own receipt handle. Sharing one object lets a
redelivery rewrite the earlier consumer's handle, and the stale delete wrongly succeeds —
that was a real bug here, caught by the checker.

`oldest_age()` counts in-flight messages too; a message being retried forever is exactly
what the age alarm exists to catch.

### `dynamodb.py`
```
table capacity: 40 WCU, spread over 4 partitions = 10 per partition
wrote 10 items, then: partition 'p0': 11.0 write units requested, 10.0 available

query('alice'): 3 items, read 3
scan(filter):   3 items, read 12
```

Two implementation notes that were both bugs first:

- **Partitions are keyed by the FULL composite key.** Keying by sort key alone made
  `alice/000` and `bob/000` collide — silent data loss rather than an error.
- **`_partition` uses `hashlib.md5`, not `hash()`.** Python randomises string hashing per
  process, so `hash()` would place a key in a different partition every run and make every
  capacity result irreproducible.

### `lambda_svc.py`
```
invoke 0: <COLD 850ms env=1>  {'calls_in_this_env': 1}
invoke 1: <warm  50ms env=1>  {'calls_in_this_env': 2}

reserved 6 for 'critical'
unreserved pool left for everything else: 4
10 events to 'api' -> 4 ran, 6 throttled      <- 'api' was never changed
```

Async invocation retries three times and then dead-letters; sync surfaces the error
immediately. Same bug, different blast radius.

### `sns.py`
```
message               pager  email  firehose
prod critical           yes    yes       yes
staging critical          -    yes       yes
no env attribute          -    yes       yes
```

`publish()` threads `now` through to SQS subscribers. Without it a topic on wall-clock
time enqueues into a simulated-clock queue "in the future", and the messages silently
never become visible — which is exactly what happened before this was fixed.

EventBridge matches nested shapes, and an event matching two rules fires both with no
deduplication.

### `kms.py`
```
plaintext:       2900 bytes
sent to KMS:        0 bytes of your data
round-trips:        1 per object, regardless of size

rotated -> current version is now 2
old ciphertext still decrypts: b'written before rotation'
bytes of data re-encrypted by the rotation: 0
```

Then the limit case: delete version 1 and that ciphertext is gone permanently.

### `vpc.py`
Security group vs NACL with identical rules, side by side — the SG connection works, the
NACL connection fails on the reply. `test_connection` models the whole connection
precisely so this is visible.

### `capstone.py`
The pipeline, and the diagnosis that matters:

```
drain: {'processed': 5, 'throttled': 0, 'failed': 5}
```

Lambda errored; DynamoDB caused it. The failed messages were never deleted, so their
leases expired and they came back — nothing was lost, because the queue sits between the
topic and the function.

### `pricing.py`
The two rounding rules, side by side, and what they do to a schema decision:

```
pro-rata:   1 S3 PUT costs 0.00000500  (not rounded up to a whole 1,000)
quantised:  a 1.1 KB DynamoDB write costs 2 WCU, not 1.1
            a 0.2 KB write also costs 1 WCU  <- 80% of it is waste
```

Then `Bill.scaled()`, which is the one that has to be right:

```
   traffic        total        fixed   fixed %
    0.001x       $36.06       $35.85     99.4%
        1x      $242.52       $35.85     14.8%
      100x   $20,702.53       $35.85      0.2%
```

Fixed lines — a NAT gateway hour, a KMS key month, provisioned capacity, an idle poller —
do not scale with traffic. A `scaled()` that multiplies everything hides exactly the
effect it was built to show.

### `billing.py`
The versioning trap, measured rather than asserted:

```
after 200 puts:     live=20.0 MB  noncurrent=0.0 MB
after 200 deletes:  live=0.0 MB   noncurrent=20.0 MB
LIST now returns 0 keys. The console is empty.
Billable bytes went from 20.0 MB to 20.0 MB — it did not move.
```

And the S3 minimum billable object size, which inverts the advice it is usually given
with — the *same* 8 MB, in two object sizes, per GB-month:

```
class              2000 x 4 KB   $/GB-mo      8 x 1 MB   $/GB-mo
standard             $0.000175    0.0209     $0.000180    0.0214
standard_ia          $0.003052    0.3638     $0.000098    0.0116
```

Standard-IA is half Standard's sticker price and 17x Standard's actual price here.

`bill_sqs` puts empty receives on their own `idle-poll-requests` line, marked fixed. That
is not tidiness: idle polling scales with wall-clock time and the number of pollers, so a
queue that goes **quiet** gets more expensive per message — backwards from every other
line on a bill, and invisible if you fold it into the request count.

### `optimize.py`
Every section is a crossover derived from the price sheet, not a rule recalled:

```
crossover (writes): 14.44% utilisation
crossover (reads):  14.44% utilisation
```

Identical, because AWS priced both modes with the same ratio — one number to remember.

The Lambda memory sweep is the same formula three times with opposite answers:

```
CPU-bound     128 MB -> 10 GB:  1.00x cost, 80x faster   <- more memory is free speed
I/O-bound     128 MB -> 10 GB: 41.94x cost, 1.7x faster  <- every MB is waste
```

And the ranked bill for the capstone pipeline at a million uploads a month, where the
route-table entry beats every code change and `BatchWriteItem` saves exactly nothing —
one API call, still one write unit per item.

## Implementation notes

- **`iam.evaluate` returns on the first matching Deny** and collects Allows otherwise.
  Never iterate letting the last match win.
- **A permissions boundary never grants**; `evaluate_with_boundary` requires both.
- **`compute_etag` takes an optional `parts` list** — that is what produces the `-N` form.
- **`Queue.receive` returns copies**; see above.
- **`Table.consume` lives on the Partition**, not the Table. Capacity per partition is the
  entire reason hot keys throttle.
- **`Function` environments have a TTL**, so warm state is neither reliable nor reliably
  absent.
- **`matches_filter` treats a missing attribute as no-match**, matching IAM's fail-closed
  rule.
- **`generate_data_key` binds the encryption context into the wrap**, so decrypting
  requires supplying it exactly.
- **`test_connection` evaluates the reply on the ephemeral port**, which is what makes the
  stateless NACL fail where a stateful SG succeeds.
- **`get_item` increments `scanned_items` as well as `reads`.** `scanned_items` means
  "items touched", which is the billable quantity; a GetItem touches exactly one. Keep
  them in separate counters and every cost model built on these stats has to guess which
  calls were which.
- **`billable_units` subtracts an epsilon before the ceiling.** Without it an exact 4.0 KB
  read bills as 2 RCU whenever the float lands at 4.0000000000000009.
- **`rank_savings` keys by `service/dimension`, never by dimension alone.** Lambda, SQS
  and KMS all have a line called `requests`; summing them because they share a word makes
  a cost model agree with itself and disagree with the invoice.
- **`money()` prints six decimals below a cent.** A serverless line item is routinely
  $0.0000004, and rounding a hundred of those to $0.00 is how a cost dashboard reports
  that a workload is free.
