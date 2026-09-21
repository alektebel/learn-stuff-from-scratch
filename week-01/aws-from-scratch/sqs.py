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
        raise NotImplementedError
    # -- consuming ----------------------------------------------------------

    def receive(self, max_messages: int = 1,
                now: Optional[float] = None) -> List[Message]:
        """Lease up to max_messages, hiding them for the visibility timeout.

        A standard queue may return messages in any order, and may return the
        same message to two consumers if one's lease expired while it was still
        working. A FIFO queue serialises per group_id: while a message from a
        group is in flight, no other message from that group is delivered.

        TODO:
        1. _recover_expired(now) FIRST — expired leases return to the queue,
           and this is where duplicate delivery is born. It is deliberate.
        2. For a FIFO queue, collect the group_ids already in flight; those
           groups are blocked.
        3. For each visible message: bump receive_count; if it now exceeds
           max_receives, move it to the dead-letter queue instead of delivering.
        4. Otherwise mint a NEW receipt handle, set visible_at = now + timeout,
           move it into in_flight, and hand the consumer a COPY.

        Step 4's copy matters: real SQS gives each receive its own handle. If
        two consumers share one Message object, a redelivery silently rewrites
        the first consumer's handle and its stale delete wrongly succeeds.
        """
        raise NotImplementedError

    def delete(self, receipt_handle: str) -> bool:
        """Acknowledge. This — not receive() — is what removes a message."""
        raise NotImplementedError

    def change_visibility(self, receipt_handle: str, timeout: float,
                          now: Optional[float] = None) -> bool:
        """Extend a lease mid-work — the fix for slow consumers."""
        raise NotImplementedError

    def _recover_expired(self, now: float) -> None:
        """Return timed-out leases to the queue. This is where duplicates
        are born, and it is deliberate."""
        raise NotImplementedError
    # -- inspection ---------------------------------------------------------

    def depth(self, now: Optional[float] = None) -> Dict[str, int]:
        raise NotImplementedError

    def oldest_age(self, now: Optional[float] = None) -> float:
        """ApproximateAgeOfOldestMessage — the alarm that actually matters.

        Queue DEPTH is a poor alarm: a healthy high-throughput queue is deep.
        Age tells you whether anything is being drained at all.
        """
        raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS the behaviour.

    The solution's demo is the reference — but write yours first and predict
    the numbers before running it. A result that surprises you is a gap in your
    model that passing tests did not reveal.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
