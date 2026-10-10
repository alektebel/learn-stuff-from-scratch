# Queue and Fanout From Scratch — Solutions

Complete versions of every template in the parent directory. Pure Python 3, no
dependencies, deterministic. Run them from inside this directory (they import each other
by name):

```bash
python3 sqs.py    # visibility timeout, redelivery, DLQ, naive vs idempotent consumer
python3 sns.py    # fanout to two queues and a webhook; filter policies
```

## Expected output

`python3 sqs.py`:

```
Visibility timeout and at-least-once redelivery (logical clock)
  receive            -> in flight, receive_count=1, size=1
  +29s               -> receive() returns 0 (still invisible)
  +30s               -> redelivered, receive_count=2 (at-least-once)
  ack                -> size=0 (gone for good)
Poison message, max_receives=3 -> dead-letter queue
  delivered 3x   -> source size=0, dlq size=1
  dlq copy records source_receive_count=3
Naive vs idempotent consumer facing the same redelivery
  naive       effects applied=2, duplicates skipped=0
  idempotent  effects applied=1, duplicates skipped=1
```

`python3 sns.py`:

```
Fanout: publish once, deliver to every subscriber
  subscribers=3 reached=3
  queue orders-a=1  orders-b=1  webhook=1
Filter policies: a subscriber only sees what it asked for
  after 2 publishes: all=2 eu=1 alert-webhook=1
```

## What the numbers mean

- **`+29s` returns 0, `+30s` redelivers.** The visibility timeout is exactly the window
  `receive()` sets; nothing happens until the clock crosses it. That redelivery is the
  source of at-least-once duplicates.
- **`ack -> size=0`.** An acknowledged message is deleted, not merely hidden; advancing
  the clock a million seconds later still returns nothing.
- **`delivered 3x` then `dlq size=1`.** With `max_receives=3` the body is delivered three
  times; the fourth receive attempt disposes of it into the dead-letter queue instead.
- **`naive effects applied=2`, `idempotent effects applied=1`.** Both consumers receive the
  same redelivery after a crash-before-ack. The naive one applies the effect twice; the
  idempotent one recognizes the message id, counts the duplicate it skipped and applies
  the effect once. This is why at-least-once exists.
- **filter policies:** the unfiltered `all` queue gets both publishes; the `region=eu`
  queue and the `kind=alert` webhook each get exactly the one that matches.

## The planted bugs this checker was tested against

Nine classic mistakes are planted in copies of these solutions by
`_build/mutations.py`; each must be caught by its check. Notably:

- letting the visibility timeout never lapse, or letting `change_visibility` collapse the
  lease to "now", both break the reappearance guarantee (step 1);
- acking by message id instead of by the current receipt handle silently deletes a message
  another consumer is processing (step 2);
- reprocessing the redelivered id makes the "idempotent" consumer apply an effect twice
  (step 6);
- fanning out to only the first subscriber, or ignoring filter policies, breaks broadcast
  and selective delivery (steps 5 and 7).

See the parent `README.md` for the full table. Every one is caught.
