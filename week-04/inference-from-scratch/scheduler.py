"""
Step 5 — A scheduler
====================
Queues, priorities, backpressure, cancellation, timeouts.

A Request: {id, prompt_len, max_new, priority (int, higher wins),
            enqueued_at (tick), deadline (tick or None)}

The scheduler holds:
  waiting  — not yet prefilling
  running  — in the current batch
  done     — finished, cancelled, or timed out

Policies the checker pins:
  pop()           highest priority, then lowest enqueued_at, then id
  admit()         False when running+waiting would exceed max_in_flight
                  (backpressure: the caller should refuse the HTTP request)
  cancel(id)      remove from waiting or mark running as cancelled;
                  a cancelled running request is dropped at the next tick
  expire(now)     any request with deadline <= now leaves as "timeout"
  tick(now)       expire, then fill running from waiting up to max_batch
"""

from typing import Dict, List, Optional


class Scheduler:
    def __init__(self, max_batch: int = 4, max_in_flight: int = 8):
        self.max_batch = max_batch
        self.max_in_flight = max_in_flight
        self.waiting: List[Dict] = []
        self.running: List[Dict] = []
        self.done: List[Dict] = []

    def admit(self, request: Dict) -> bool:
        """TODO: True and append to waiting if in-flight < max_in_flight.
        in-flight = len(waiting)+len(running). False otherwise.
        Do not enqueue on False.
        """
        raise NotImplementedError

    def pop(self) -> Optional[Dict]:
        """TODO: remove and return the next waiting request, or None.
        Sort key: (-priority, enqueued_at, id).
        """
        raise NotImplementedError

    def cancel(self, request_id: str) -> bool:
        """TODO: True if it was waiting or running.
        Waiting: remove, append to done with status='cancelled'.
        Running: set status='cancelled' in place (tick will move it).
        Unknown id: False.
        """
        raise NotImplementedError

    def expire(self, now: int) -> List[str]:
        """TODO: move every waiting/running request with a deadline <= now
        to done with status='timeout'. Return their ids.
        Requests with deadline is None never expire.
        """
        raise NotImplementedError

    def tick(self, now: int) -> List[Dict]:
        """TODO:
        1. expire(now)
        2. move running requests marked cancelled to done
        3. while len(running) < max_batch: pop() and append to running
        Return the current running list (a copy).
        """
        raise NotImplementedError
