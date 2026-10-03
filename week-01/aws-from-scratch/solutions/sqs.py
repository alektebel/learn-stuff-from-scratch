"""
SQS — queues, and why "at least once" is a promise about YOUR code. Complete Solution.

DESIGN DECISION — delete on receive, or lease with a visibility timeout?
  Deleting on receive gives at-most-once: a consumer that crashes loses the
  message.
  CHOSEN: the lease. receive() hides a message for `visibility_timeout`
  seconds; only an explicit delete() removes it. A crashed consumer means the
  message reappears. The unavoidable consequence is DUPLICATE delivery — which
  is not a bug in the queue, it is the price of not losing work, and it is why
  every SQS consumer must be idempotent.

DESIGN DECISION — how is time modelled?
  Real timeouts make tests slow and flaky.
  CHOSEN: an injectable clock. Every method takes `now`, defaulting to
  time.time(). Timeout behaviour becomes exactly reproducible, and the limit
  case below can be demonstrated in microseconds instead of minutes.
"""

import copy
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple


class Message:
    def __init__(self, body: str, message_id: str, group_id: str = "",
                 dedup_id: str = ""):
        self.body = body
        self.message_id = message_id
        self.group_id = group_id
        self.dedup_id = dedup_id
        self.receipt_handle: Optional[str] = None
        self.visible_at: float = 0.0
        self.receive_count = 0
        self.first_received: Optional[float] = None

    def __repr__(self) -> str:
        return f"<Message {self.message_id} {self.body!r} recv={self.receive_count}>"


class Queue:
    def __init__(self, name: str, visibility_timeout: float = 30.0,
                 fifo: bool = False, max_receives: int = 3,
                 dead_letter: Optional["Queue"] = None,
                 delay_seconds: float = 0.0):
        self.name = name
        self.visibility_timeout = visibility_timeout
        self.fifo = fifo
        self.max_receives = max_receives
        self.dead_letter = dead_letter
        self.delay_seconds = delay_seconds
        self.messages: List[Message] = []
        self.in_flight: Dict[str, Message] = {}
        self.dedup_window: Dict[str, float] = {}
        self.stats = {"sent": 0, "received": 0, "deleted": 0,
                      "redelivered": 0, "dead_lettered": 0}

    # -- producing ----------------------------------------------------------

    def send(self, body: str, group_id: str = "", dedup_id: str = "",
             now: Optional[float] = None) -> Optional[str]:
        """Enqueue. FIFO queues deduplicate within a 5-minute window."""
        now = time.time() if now is None else now

        if self.fifo and dedup_id:
            last = self.dedup_window.get(dedup_id)
            if last is not None and now - last < 300:
                return None            # silently dropped, exactly as SQS does
            self.dedup_window[dedup_id] = now

        message = Message(body, str(uuid.uuid4())[:8], group_id, dedup_id)
        message.visible_at = now + self.delay_seconds
        self.messages.append(message)
        self.stats["sent"] += 1
        return message.message_id

    # -- consuming ----------------------------------------------------------

    def receive(self, max_messages: int = 1,
                now: Optional[float] = None) -> List[Message]:
        """Lease up to max_messages, hiding them for the visibility timeout.

        A standard queue may return messages in any order, and may return the
        same message to two consumers if one's lease expired while it was still
        working. A FIFO queue serialises per group_id: while a message from a
        group is in flight, no other message from that group is delivered.
        """
        now = time.time() if now is None else now
        self._recover_expired(now)

        blocked_groups = {m.group_id for m in self.in_flight.values()} \
            if self.fifo else set()

        taken: List[Message] = []
        for message in list(self.messages):
            if len(taken) >= max_messages:
                break
            if message.visible_at > now:
                continue
            if self.fifo and message.group_id in blocked_groups:
                continue

            message.receive_count += 1
            if message.first_received is None:
                message.first_received = now
            if message.receive_count > 1:
                self.stats["redelivered"] += 1

            # Poison-pill protection: after max_receives, move it aside.
            if message.receive_count > self.max_receives:
                self.messages.remove(message)
                if self.dead_letter is not None:
                    self.dead_letter.messages.append(message)
                    self.dead_letter.stats["sent"] += 1
                self.stats["dead_lettered"] += 1
                continue

            handle = str(uuid.uuid4())[:8]
            message.receipt_handle = handle
            message.visible_at = now + self.visibility_timeout
            self.messages.remove(message)
            self.in_flight[handle] = message
            if self.fifo:
                blocked_groups.add(message.group_id)
            # Hand the consumer its OWN view. Real SQS gives each receive a
            # distinct receipt handle; sharing one object would let a later
            # redelivery silently rewrite an earlier consumer's handle, and the
            # stale-handle case below would stop being demonstrable.
            taken.append(copy.copy(message))
            self.stats["received"] += 1
        return taken

    def delete(self, receipt_handle: str) -> bool:
        """Acknowledge. This — not receive() — is what removes a message."""
        message = self.in_flight.pop(receipt_handle, None)
        if message is None:
            return False               # expired lease: someone else has it now
        self.stats["deleted"] += 1
        return True

    def change_visibility(self, receipt_handle: str, timeout: float,
                          now: Optional[float] = None) -> bool:
        """Extend a lease mid-work — the fix for slow consumers."""
        now = time.time() if now is None else now
        message = self.in_flight.get(receipt_handle)
        if message is None:
            return False
        message.visible_at = now + timeout
        return True

    def _recover_expired(self, now: float) -> None:
        """Return timed-out leases to the queue. This is where duplicates
        are born, and it is deliberate."""
        for handle, message in list(self.in_flight.items()):
            if message.visible_at <= now:
                del self.in_flight[handle]
                message.receipt_handle = None
                self.messages.append(message)

    # -- inspection ---------------------------------------------------------

    def depth(self, now: Optional[float] = None) -> Dict[str, int]:
        now = time.time() if now is None else now
        return {"visible": sum(1 for m in self.messages if m.visible_at <= now),
                "delayed": sum(1 for m in self.messages if m.visible_at > now),
                "in_flight": len(self.in_flight)}

    def oldest_age(self, now: Optional[float] = None) -> float:
        """ApproximateAgeOfOldestMessage — the alarm that actually matters.

        Queue DEPTH is a poor alarm: a healthy high-throughput queue is deep.
        Age tells you whether anything is being drained at all.
        """
        now = time.time() if now is None else now
        pending = list(self.messages) + list(self.in_flight.values())
        ages = [now - m.first_received for m in pending
                if m.first_received is not None]
        return max(ages) if ages else 0.0


def _demo() -> None:
    print("=== Delete, not receive, is the acknowledgement ===")
    queue = Queue("jobs", visibility_timeout=30)
    queue.send("job-1", now=0)
    queue.send("job-2", now=0)

    batch = queue.receive(max_messages=2, now=0)
    print(f"  received {len(batch)}: {[m.body for m in batch]}")
    print(f"  depth after receive: {queue.depth(now=0)}")
    queue.delete(batch[0].receipt_handle)
    print(f"  after deleting one:  {queue.depth(now=0)}")

    print("\n=== The limit case: work outlasts the visibility timeout ===")
    slow = Queue("slow", visibility_timeout=10)
    slow.send("expensive-job", now=0)

    first = slow.receive(now=0)[0]
    print(f"  t=0   consumer A receives {first.body!r} "
          f"(receive_count={first.receive_count})")
    second = slow.receive(now=11)
    print(f"  t=11  consumer B receives {[m.body for m in second]} "
          f"— the lease expired while A was still working")
    print(f"        receive_count is now {second[0].receive_count}")
    delivered = slow.delete(first.receipt_handle)
    print(f"  t=12  A finishes and deletes with its stale handle: {delivered}")
    print("\n  TWO consumers processed the same message. That is at-least-once")
    print("  delivery, working as designed — the queue chose duplication over")
    print("  loss. Your handler must be idempotent, or extend the lease with")
    print("  change_visibility while it works. There is no third option.")

    extended = Queue("extended", visibility_timeout=10)
    extended.send("expensive-job", now=0)
    held = extended.receive(now=0)[0]
    extended.change_visibility(held.receipt_handle, 60, now=5)
    print(f"\n  with change_visibility at t=5: another receive at t=11 gets "
          f"{len(extended.receive(now=11))} messages")

    print("\n=== Poison pills go to a dead-letter queue ===")
    dlq = Queue("jobs-dlq")
    main = Queue("jobs", visibility_timeout=5, max_receives=3, dead_letter=dlq)
    main.send("always-fails", now=0)
    for attempt in range(5):
        received = main.receive(now=attempt * 6)
        state = f"attempt {attempt}: got {len(received)}"
        if received:
            state += f", receive_count={received[0].receive_count}"
        print(f"  {state}")
    print(f"  main queue: {main.depth(now=100)}, DLQ holds {len(dlq.messages)}")
    print("  Without a DLQ this message is retried until the end of time,")
    print("  consuming throughput and hiding the ones behind it.")

    print("\n=== FIFO serialises per group, standard does not ===")
    fifo = Queue("orders.fifo", fifo=True, visibility_timeout=30)
    for i in range(3):
        fifo.send(f"customer-A-step-{i}", group_id="A", now=0)
    fifo.send("customer-B-step-0", group_id="B", now=0)

    batch = fifo.receive(max_messages=10, now=0)
    print(f"  first receive: {[m.body for m in batch]}")
    print("  Only ONE message from group A — the next waits until it is deleted.")
    fifo.delete(batch[0].receipt_handle)
    print(f"  after ack:     {[m.body for m in fifo.receive(max_messages=10, now=1)]}")
    print("  Ordering per group costs you parallelism within that group. Group")
    print("  by the thing that must be ordered, and no more.")

    print("\n=== FIFO deduplication ===")
    dedup = Queue("dedup.fifo", fifo=True)
    print(f"  send #1: {dedup.send('charge-order-7', 'A', 'order-7', now=0)}")
    print(f"  send #2: {dedup.send('charge-order-7', 'A', 'order-7', now=10)} "
          "(dropped, within the 5-minute window)")
    print(f"  send #3: {dedup.send('charge-order-7', 'A', 'order-7', now=400)} "
          "(window expired)")
    print(f"  queue depth: {dedup.depth(now=400)['visible']}")

    print("\n=== Alarm on AGE, not depth ===")
    stuck = Queue("stuck", visibility_timeout=1)
    stuck.send("first", now=0)
    stuck.receive(now=0)
    print(f"  depth at t=300: {stuck.depth(now=300)}")
    print(f"  age of oldest:  {stuck.oldest_age(now=300):.0f}s")
    print("  A healthy high-throughput queue is deep. Depth alarms cry wolf;")
    print("  age tells you whether anything is draining at all.")


if __name__ == "__main__":
    _demo()
