# Queue and Fanout From Scratch

An SQS-shaped queue and an SNS-shaped topic, in pure Python (standard library only),
built one mechanism at a time. It re-implements the two shapes that AWS uses to
decouple services -- a **visibility-timeout queue** with at-least-once redelivery, and a
**publish/subscribe topic** that fans a message out to every subscriber -- so you can
run the failure modes yourself instead of reading about them.

Source material: `awsdocs:sqs` (visibility timeout, dead-letter queues, at-least-once
delivery) and `awsdocs:sns` (fanout, subscription filter policies, message attributes).
Restated from scratch; no code or text copied.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| A queue that does not lose in-flight work | visibility timeout, redelivery, `change_visibility` | `sqs.py` | 1, 3 |
| Acknowledgement | `ack` deletes the message; receipt handles rotate | `sqs.py` | 2 |
| A poison-pill guard | max receives, then the dead-letter queue | `sqs.py` | 4 |
| Surviving duplicates | an idempotent consumer over an at-least-once queue | `sqs.py` | 6 |
| Broadcast | a topic fanning out to queue and webhook subscribers | `sns.py` | 5 |
| Selective delivery | subscription filter policies over message attributes | `sns.py` | 7 |

## How to use this directory

The top-level `sqs.py` and `sns.py` are **templates**: each function you implement keeps
its signature and docstring, has a `TODO` with a hint, and raises `NotImplementedError`.
`solutions/` holds working versions for when you are stuck or to compare afterwards.

```bash
cd cloud/03-queue-fanout
python3 check.py        # what to build next; stops at the first gap
python3 check.py 4      # one step
python3 check.py --all  # everything
```

`check.py` runs 7 checks against **your** code and never imports `solutions/`. Time is a
`Clock` you advance explicitly -- nothing sleeps, so every scenario is deterministic.

## The ladder: MVP first, then the limit cases

**v1 -- a queue that hides a received message.** `receive()` marks a message in flight
for the visibility timeout; it reappears if nobody acks it. That alone is at-least-once
delivery (check 1).

**v2 -- acknowledgement.** `ack` deletes the message for good. The hard part is *which*
receipt handle is being acked: a handle from a delivery that has already been
redelivered must not delete the message the current consumer is holding (check 2).

**v3 -- the poison pill.** Retry forever is an outage, not resilience. After `max_receives`
deliveries the message is dead-lettered instead of redelivered (check 4).

**v4 -- the duplicate is not hypothetical.** v1's redelivery *is* a duplicate: process,
crash before ack, get it again. A naive consumer applies the effect twice; an idempotent
one recognizes the message id and skips it (check 6). This is the limit case the queue
exists to force on you.

**v5 -- broadcast.** A topic publishes once and every matching subscriber gets its own
copy. Subscribers are queues (durable buffering) or webhooks (push) (check 5).

**v6 -- selective delivery.** A subscription filter policy so a subscriber only receives
the attributes it asked for (check 7).

## Design decisions, named

Each file opens with its decisions and their costs. In short:

- **Receipt handles rotate on every delivery** (`sqs.py`). `ack` and `change_visibility`
  act on the current handle, not the message id; a stale ack returns `False` instead of
  destroying a live message. Cost: an ack is not idempotent across redeliveries.
- **The lease lives on the message, checked by the injected clock** (`sqs.py`). No reaper
  thread and no `sleep`; invisibility is enforced lazily at the next `receive()`. Cost:
  `size()` counts an in-flight message until someone polls again.
- **Standard-queue semantics, scanned in send order** (`sqs.py`). We keep duplicates
  (the interesting failure) but scan FIFO so checks are predictable. Cost: real standard
  queues may still reorder, which this model does not.
- **`max_receives` means "N deliveries, then out"** (`sqs.py`). A reading of the SQS
  `maxReceiveCount` rule; the other reading shifts the count by one.
- **Fanout copies the message per subscriber, synchronously** (`sns.py`). One subscriber
  cannot see or mutate another's copy. Cost: no retries, backoff or per-subscription DLQ.
- **A filter policy is `{attribute: [allowed, ...]}`** (`sns.py`). The common core of SNS
  filter policies; `anything-but`, prefixes and body matching are out of scope. Cost: a
  policy language, simplified, but the property under test -- only matching subscribers
  receive -- is exact.
- **Webhooks are local receivers, not HTTP** (`sns.py`). Keeps the module standard-library
  only and deterministic. Cost: no signatures, headers or network failures.

## Questions to answer before reading the solutions

1. A consumer receives a message, finishes the work, and then `ack`s with a receipt handle
   it cached from the *first* delivery. What should happen, and why is that the safe
   choice rather than deleting the message anyway?
2. `change_visibility` can hide a message indefinitely by resetting the window forever.
   Name a legitimate use and the abuse it enables.
3. With `max_receives=3`, exactly how many times is the body delivered before it reaches
   the DLQ in this model? Where is the off-by-one, and which SQS wording did we choose?
4. The idempotent consumer deduplicates by message id. What breaks if the producer sends
   the same logical event twice (two different ids)? What key would you use instead?
5. A publish with a filter policy that no subscriber matches returns an empty list. Is
   that an error, and what does real SNS do with an unmatched message?
6. `Topic.publish` returns the ids it reached. Why does that list have to be returned by
   the caller's synchronous call rather than observed later?

## Verification, and how the checker was tested

Nine classic bugs were planted in copies of the solutions, and each has to be caught by
its check (this is the mutation table; `_build/mutations.py`):

| Planted bug | File | Caught by |
|---|---|---|
| the visibility timeout never lapses | `sqs.py` | step 1 |
| `change_visibility` does not extend the lease | `sqs.py` | step 1 |
| `ack` ignores the receipt handle (a stale ack deletes) | `sqs.py` | step 2 |
| a delayed message is visible immediately | `sqs.py` | step 3 |
| no dead-letter after max receives | `sqs.py` | step 4 |
| the idempotent consumer reprocesses the duplicate | `sqs.py` | step 6 |
| fanout delivers only to the first subscriber | `sns.py` | step 5 |
| a webhook delivery is dropped | `sns.py` | step 5 |
| the subscription filter policy is ignored | `sns.py` | step 7 |

Run it yourself:

```bash
python3 ../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py
```

## Limits (what is deliberately left out)

- **No persistence.** Queues and topics live in memory; there is no WAL or disk format.
- **No real timers or threads.** The `Clock` is advanced by hand. Real SQS reaps expired
  leases on its own schedule; here invisibility is checked lazily on the next receive.
- **No retry/backoff or per-subscription DLQ on SNS delivery.** A webhook that raises would
  just propagate; real SNS retries and can dead-letter.
- **Standard-queue semantics only.** No FIFO queue with a deduplication window, message
  groups or ordering guarantees.
- **Filter policies are a subset.** No `anything-but`, prefix, numeric or nested-body
  matching; no raw-message-delivery distinction between the SNS envelope and the body.
- **No IAM, encryption, long polling or batch APIs.** `receive(max_messages)` exists but
  there is no `WaitTimeSeconds`, no message-attribute data types, no server-side
  encryption.
