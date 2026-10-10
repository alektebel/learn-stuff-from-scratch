"""
An SQS-shaped queue: visibility timeout, at-least-once redelivery, ack, DLQ
===========================================================================

Source: awsdocs:sqs -- "Amazon SQS visibility timeout", "Amazon SQS dead-letter
queues", "Amazon SQS at-least-once delivery". Restated here in our own words.

Amazon SQS is a hosted queue with *at-least-once* delivery. A consumer does not
remove a message when it reads it; it *receives* it, which hides it from other
consumers for a **visibility timeout**. If the consumer finishes and deletes the
message (an acknowledgement, `ack` here) the message is gone. If it crashes or
forgets to delete, the timeout lapses and the message becomes visible again and
is redelivered. That redelivery is where duplicates come from: at-least-once
means "one or more", so a consumer that must apply an effect exactly once has to
be idempotent on its own.

A queue can name a **dead-letter queue** and a `max_receives`. Once a message has
been received more times than that, SQS stops delivering it to the source queue
and moves it to the DLQ, so a poison message cannot be retried forever.

DESIGN DECISION - receipt handles rotate on every delivery
Receiving a message issues a new opaque *receipt handle*; delete and
change-visibility operate on the handle, not on the message id. If delivery
issues the same handle every time, an ack that raced past a redelivery and a few
retries would delete a message another consumer is now processing. Rotating the
handle makes a stale ack fail (return False) instead of destroying a live
message. Cost: a consumer must remember the handle from *its* receive, and an
ack is no longer idempotent across redeliveries -- which is exactly the
observable behaviour we want.

DESIGN DECISION - the message does not carry its lease; the queue does
`visible_at` is stored on the message and checked against the injected clock at
receive time. There is no background reaper thread: a queue is a passive data
structure, so time only moves when the test calls `clock.advance()`. This keeps
every scenario deterministic and repeatable, which a wall-clock timer cannot. The
cost is that invisibility is enforced lazily -- `size()` reports a message that
is "in flight" until the next receive, which is fine for a model but would need a
real timer in production.

DESIGN DECISION - FIFO order, standard-queue semantics
Real SQS standard queues are best-effort ordered and may deliver duplicates or
reorder; FIFO queues guarantee order and no duplicates within a dedup window. We
model the *standard* queue (at-least-once, duplicates allowed) because that is
the interesting failure mode, but we scan messages in send order so the model is
deterministic and a check can predict which message comes next. The cost: we do
not model out-of-order delivery, which real standard queues may still produce.

DESIGN DECISION - max_receives counts receives before the move
A message is delivered up to `max_receives` times. On the next receive attempt,
once its visibility has lapsed, it is disposed of instead. With a DLQ it is sent
there (carrying `source_receive_count`); without one it is discarded. So
`max_receives=3` means "three deliveries, then out" -- the threshold that a
poison-pill guard actually wants. Cost: this is an interpretation of the SQS
"exceeds maxReceiveCount" rule; the other reading (move on the receive that
would exceed) shifts the count by one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


class Clock:
    """A logical clock. Tests advance it; nothing ever sleeps."""

    def __init__(self, start: int = 0):
        self._now = int(start)

    @property
    def now(self) -> int:
        return self._now

    def advance(self, seconds: int) -> int:
        if seconds < 0:
            raise ValueError("the logical clock cannot run backwards")
        self._now += int(seconds)
        return self._now


@dataclass
class Message:
    """A queue message. `receipt_handle` is the current delivery's lease token."""

    id: str
    body: str
    attributes: Dict[str, str] = field(default_factory=dict)
    sent_at: int = 0
    visible_at: int = 0
    receive_count: int = 0
    receipt_handle: Optional[str] = None
    source_receive_count: Optional[int] = None  # set only on a DLQ copy


class Queue:
    """An SQS-shaped standard queue backed by an explicit logical clock."""

    def __init__(
        self,
        name: str,
        clock: Clock,
        visibility_timeout: int = 30,
        max_receives: Optional[int] = None,
        dead_letter_queue: "Optional[Queue]" = None,
    ):
        if visibility_timeout < 0:
            raise ValueError("visibility_timeout must be >= 0")
        if max_receives is not None and max_receives < 1:
            raise ValueError("max_receives must be >= 1 when set")
        self.name = name
        self.clock = clock
        self.visibility_timeout = visibility_timeout
        self.max_receives = max_receives
        self.dead_letter_queue = dead_letter_queue
        self._messages: List[Message] = []
        self._next_id = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.messages_deleted = 0
        self.messages_moved_to_dlq = 0
        self.messages_discarded = 0

    # -- producing ----------------------------------------------------------

    def send(
        self,
        body: str,
        attributes: Optional[Dict[str, str]] = None,
        delay_seconds: int = 0,
        source_receive_count: Optional[int] = None,
    ) -> str:
        """Enqueue `body`; return its message id. `delay_seconds` hides it first."""
        if delay_seconds < 0:
            raise ValueError("delay_seconds must be >= 0")
        self._next_id += 1
        now = self.clock.now
        message = Message(
            id=f"{self.name}-{self._next_id}",
            body=body,
            attributes=dict(attributes or {}),
            sent_at=now,
            visible_at=now + delay_seconds,
            source_receive_count=source_receive_count,
        )
        self._messages.append(message)
        self.messages_sent += 1
        return message.id

    # -- consuming ----------------------------------------------------------

    def receive(
        self, max_messages: int = 1, visibility_timeout: Optional[int] = None
    ) -> List[Message]:
        """Return visible messages and hide each for the visibility timeout.

        A message whose visibility has lapsed and whose receive count already
        reached `max_receives` is not delivered again: it is moved to the
        dead-letter queue (or discarded) instead.
        """
        if max_messages < 1:
            raise ValueError("max_messages must be >= 1")
        timeout = self.visibility_timeout if visibility_timeout is None else visibility_timeout
        if timeout < 0:
            raise ValueError("visibility_timeout must be >= 0")
        now = self.clock.now
        delivered: List[Message] = []
        for message in list(self._messages):
            if len(delivered) >= max_messages:
                break
            if now < message.visible_at:
                continue  # still in flight for another consumer
            if self.max_receives is not None and message.receive_count >= self.max_receives:
                self._dispose(message)
                continue
            message.receive_count += 1
            message.receipt_handle = f"{message.id}#{message.receive_count}"
            message.visible_at = now + timeout
            self.messages_received += 1
            delivered.append(message)
        return delivered

    def ack(self, receipt_handle: str) -> bool:
        """Delete the message the live receipt handle belongs to.

        Returns False for an unknown or stale handle -- notably a handle from a
        delivery that has already been redelivered to someone else.
        """
        for message in list(self._messages):
            if message.receipt_handle is not None and message.receipt_handle == receipt_handle:
                self._messages.remove(message)
                self.messages_deleted += 1
                return True
        return False

    def change_visibility(self, receipt_handle: str, timeout: int) -> bool:
        """Reset the current delivery's invisibility window. False if stale."""
        if timeout < 0:
            raise ValueError("timeout must be >= 0")
        for message in self._messages:
            if message.receipt_handle == receipt_handle:
                message.visible_at = self.clock.now + timeout
                return True
        return False

    def _dispose(self, message: Message) -> None:
        """Retire a message that has consumed all its allowed receives."""
        self._messages.remove(message)
        if self.dead_letter_queue is not None:
            self.dead_letter_queue.send(
                message.body,
                attributes=message.attributes,
                source_receive_count=message.receive_count,
            )
            self.messages_moved_to_dlq += 1
        else:
            self.messages_discarded += 1

    # -- introspection ------------------------------------------------------

    def size(self) -> int:
        """Number of messages still owned by this queue (visible or in flight)."""
        return len(self._messages)

    def visible(self) -> List[Message]:
        """Messages a receive() right now would hand out (including DLQ-pending)."""
        now = self.clock.now
        return [m for m in self._messages if now >= m.visible_at]


class Consumer:
    """The naive at-least-once consumer: process every delivery, then ack.

    This is the shape that *causes* the duplicate problem: if the process dies
    after the handler runs but before `ack`, the message comes back and the
    handler runs again. It is provided so the limit case can be demonstrated,
    not because it is correct.
    """

    def __init__(
        self,
        queue: Queue,
        handler: Callable[[Message], None],
        visibility_timeout: Optional[int] = None,
        max_messages: int = 10,
    ):
        self.queue = queue
        self.handler = handler
        self.visibility_timeout = visibility_timeout
        self.max_messages = max_messages
        self.processed = 0

    def poll(self, ack: bool = True) -> int:
        """Receive up to max_messages, run the handler, ack unless `ack` is False."""
        messages = self.queue.receive(self.max_messages, visibility_timeout=self.visibility_timeout)
        for message in messages:
            self.handler(message)
            self.processed += 1
            if ack:
                self.queue.ack(message.receipt_handle)
        return len(messages)


class IdempotentConsumer(Consumer):
    """At-least-once consumer that makes redelivery harmless.

    It remembers the message ids it has already applied an effect for, so a
    redelivered copy is acked but not processed a second time.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen: set = set()
        self.duplicates = 0

    def poll(self, ack: bool = True) -> int:
        messages = self.queue.receive(self.max_messages, visibility_timeout=self.visibility_timeout)
        for message in messages:
            if message.id in self.seen:
                self.duplicates += 1
            else:
                self.seen.add(message.id)
                self.handler(message)
                self.processed += 1
            if ack:
                self.queue.ack(message.receipt_handle)
        return len(messages)


def _demo() -> None:
    clock = Clock()
    dlq = Queue("orders-dlq", clock)
    q = Queue("orders", clock, visibility_timeout=30, max_receives=3, dead_letter_queue=dlq)

    print("Visibility timeout and at-least-once redelivery (logical clock)")
    q.send("order-1")
    held = q.receive()[0]
    print(f"  receive            -> in flight, receive_count={held.receive_count}, size={q.size()}")
    clock.advance(29)
    print(f"  +29s               -> receive() returns {len(q.receive())} (still invisible)")
    clock.advance(1)
    again = q.receive()[0]
    print(f"  +30s               -> redelivered, receive_count={again.receive_count} (at-least-once)")
    q.ack(again.receipt_handle)
    print(f"  ack                -> size={q.size()} (gone for good)")

    print("Poison message, max_receives=3 -> dead-letter queue")
    q.send("poison")
    deliveries = 0
    for _ in range(12):
        got = q.receive()
        if got:
            deliveries += 1
            clock.advance(30)
        else:
            clock.advance(30)
    print(f"  delivered {deliveries}x   -> source size={q.size()}, dlq size={dlq.size()}")
    print(f"  dlq copy records source_receive_count={dlq._messages[0].source_receive_count}")

    print("Naive vs idempotent consumer facing the same redelivery")
    for cls, label in ((Consumer, "naive"), (IdempotentConsumer, "idempotent")):
        effects = []
        cq = Queue(f"{label}-q", clock, visibility_timeout=10)
        cq.send("charge-card")
        consumer = cls(cq, lambda m: effects.append(m.body))
        consumer.poll(ack=False)  # handler ran, then the process "crashed"
        clock.advance(10)
        consumer.poll()
        dup = getattr(consumer, "duplicates", 0)
        print(f"  {label:11s} effects applied={len(effects)}, duplicates skipped={dup}")


if __name__ == "__main__":
    _demo()
