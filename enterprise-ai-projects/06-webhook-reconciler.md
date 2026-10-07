# 6 — Idempotent webhook reconciler

## What it is

An event processor that consumes webhooks from a system you do not control, and produces
the correct final state regardless of duplicates, out-of-order delivery, retries, and
gaps.

## You have already built most of this

Before starting, read what is in this repo:

- `system-design/message_queue.py` — retries, exponential backoff, dead-letter queues.
- `system-design/idempotency_keys.py` — the key mechanism itself.
- `aws-from-scratch/sqs.py` — visibility timeouts and at-least-once redelivery.
- `aws-from-scratch/dynamodb.py` — conditional writes, which is how idempotency is
  usually enforced in practice.

That is the reliability core. **The part you have not built is in the name: the
reconciler.** Idempotency makes a repeated event harmless. It does nothing about an event
that arrives *before* the one it logically follows, and nothing about one that never
arrives at all. Those two are this project.

## What it actually demonstrates

Not "you build reliable integrations" in general — it demonstrates that you know
idempotency and ordering are different problems with different solutions, and that
at-least-once delivery plus a non-commutative handler is a correctness bug rather than a
performance one.

## The substrate

A broker whose redelivery semantics you did not choose, so that the awkward cases are
given to you rather than invented:

- **NATS JetStream** — explicit ack, redelivery, and a max-deliver limit that lands
  messages in a DLQ-equivalent.
- **Redis Streams** — consumer groups, pending-entries list, `XAUTOCLAIM`. The PEL is a
  particularly good teacher because you can see stuck messages directly.
- **RabbitMQ** — if you want to meet requeue-on-nack and the way it reorders.

And a real sender. Point Stripe's CLI (`stripe listen --forward-to`) or a GitHub webhook
at your endpoint, then make it fail: return 500s, hold the connection open past their
timeout, and watch what the real retry policy does. Their redelivery behaviour is a
specification you must satisfy, not one you get to design.

## The decisions

**Idempotency key: theirs or yours.** Their event id is stable across their retries, which
is what you want. It is not stable across *your* replays from a backup, and some senders
reuse ids across environments. A derived key (`hash(event_type, entity_id, version)`) is
robust to that and collides on genuinely distinct events with the same payload. Say which
you chose and which failure you accepted.

**Dedupe window.** Storing every key forever is correct and unbounded. A TTL is bounded
and wrong for any duplicate arriving after it. Real senders retry for hours to days —
look up the actual policy for your sender and set the window from that, not from a round
number.

**Ordering: sequence or state.** Two families:

- *Sequence-based.* Buffer out-of-order events and apply them in order. Requires a
  monotonic per-entity sequence number from the sender, which many do not provide.
  Requires deciding how long to wait for a gap before giving up.
- *State-based.* Ignore ordering; on any event, fetch current state from the sender's API
  and reconcile. Immune to ordering entirely. Costs an API call per event and a rate limit
  you now share with everything else.

State-based is usually right and is the less-taught answer. Build it second, after
sequence-based has failed on a gap that never closes.

**The DLQ is not a destination.** A dead-letter queue nobody reads is a data-loss
mechanism with extra steps. Decide who is paged, what the redrive procedure is, and how
you replay without re-triggering side effects. That last one is where idempotency earns
its keep.

**Sweeper.** Webhooks get lost — the sender had an outage, your endpoint was down past
their retry budget, a message expired in the PEL. A periodic full reconciliation against
the sender's API is the only thing that closes that hole. Every mature integration has
one; most tutorials omit it.

## Where it breaks

The sender changes their payload schema and starts sending a field you parse strictly.
Every event now fails, retries, exhausts, and lands in the DLQ — which fills at the
sender's full event rate while you are asleep. Your handler was correct; your parser was
brittle.

Decide up front whether unknown fields are tolerated and whether a parse failure is
retryable. A parse failure is *not* retryable, and treating it as one is how a DLQ becomes
a million messages.

## Resources

- Stripe, *Webhooks* and *Idempotent requests* — <https://docs.stripe.com/webhooks>, <https://docs.stripe.com/api/idempotent_requests>. The clearest public specification of a real retry policy, and the one to build against.
- NATS JetStream consumers — <https://docs.nats.io/nats-concepts/jetstream/consumers>
- Redis Streams introduction — <https://redis.io/docs/latest/develop/data-types/streams/>
- Helland, *Idempotence Is Not a Medical Condition*, ACM Queue 2012. Short, and the correct framing of why exactly-once is a property of the handler and not of the transport.
- `system-design/` and `aws-from-scratch/` in this repo, as listed above.
