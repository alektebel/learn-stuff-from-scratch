"""
An SNS-shaped topic: publish once, fan out to every subscriber
=============================================================

Source: awsdocs:sns -- "Amazon SNS fanout", "Amazon SNS subscription filter
policies", "Amazon SNS message attributes". Restated here in our own words.

Amazon SNS is pub/sub rather than a queue: a *publisher* sends one message to a
*topic*, and the topic pushes a copy to every *subscription* that matches. The
subscriber is typically another SQS queue (the classic "SNS fanout to SQS"
pattern, which combines broadcast with durable buffering) or an HTTP/S webhook.
A subscription can attach a **filter policy** -- a small document over the
message attributes -- so it receives only the subset it cares about. Filtering
happens at the topic, before delivery; the subscriber never sees the messages it
did not ask for.

DESIGN DECISION - fanout copies the message per subscriber, and delivery is
synchronous
`publish()` calls each matching subscriber's delivery method in subscription
order and returns the list of subscription ids that were reached. One subscriber
cannot see or mutate another's copy (attributes are copied). Real SNS decouples
this with retries and a per-subscription DLQ; here it is a direct call so a check
can assert exactly who got what without waiting. Cost: there is no retry/backoff
and no asynchronous failure surface, so this model cannot show a flaky webhook.

DESIGN DECISION - a filter policy is "attribute must match one of these values"
SNS filter policies are JSON documents over message attributes (and, in the
advanced form, the JSON body), supporting `anything-but`, prefixes, numeric
ranges and nesting. We implement the common core: `{attribute: [allowed, ...]}`
matches when, for *every* listed attribute, the message carries it and its value
is in the allowed list. An empty/None policy matches everything. This is
deliberately not the full language; the cost is that negation and body matching
are out of scope, but the important property -- "a topic with filters delivers
only to the matching subscribers" -- is exactly what is tested.

DESIGN DECISION - subscribers are queues or webhooks, not a generic transport
A queue subscription durably enqueues a copy; a webhook subscription records the
POST body on a local `Webhook` receiver. Modelling the webhook as an object with
a `deliveries` list (rather than real HTTP) keeps the module standard-library
only and deterministic. Cost: no network, headers, signatures or retries -- only
the fact that the delivery arrived once, in order.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqs import Clock, Queue


class Webhook:
    """A local stand-in for an HTTP/S endpoint that records its deliveries."""

    def __init__(self, url: str):
        self.url = url
        self.deliveries: List[Dict[str, object]] = []

    def deliver(self, body: str, attributes: Optional[Dict[str, str]] = None) -> None:
        self.deliveries.append({"body": body, "attributes": dict(attributes or {})})


class Subscription:
    """One endpoint attached to a topic, with an optional filter policy."""

    def __init__(
        self,
        sub_id: str,
        kind: str,
        target,
        filter_policy: Optional[Dict[str, List[str]]] = None,
    ):
        self.id = sub_id
        self.kind = kind  # "queue" or "webhook"
        self.target = target
        self.filter_policy = filter_policy

    def matches(self, attributes: Optional[Dict[str, str]]) -> bool:
        """True when every filter-policy attribute is present and allowed."""
        if not self.filter_policy:
            return True
        attributes = attributes or {}
        for name, allowed in self.filter_policy.items():
            if attributes.get(name) not in allowed:
                return False
        return True

    def deliver(self, body: str, attributes: Optional[Dict[str, str]] = None) -> None:
        if self.kind == "queue":
            self.target.send(body, attributes=attributes)
        else:
            self.target.deliver(body, attributes)


class Topic:
    """An SNS-shaped topic. Publish once; every matching subscription gets a copy."""

    def __init__(self, name: str, clock: Clock):
        self.name = name
        self.clock = clock
        self._subscriptions: List[Subscription] = []
        self._next_id = 0
        self.published = 0
        self.delivered = 0

    def _add(self, kind: str, target, filter_policy) -> str:
        self._next_id += 1
        sub_id = f"{self.name}-sub-{self._next_id}"
        self._subscriptions.append(Subscription(sub_id, kind, target, filter_policy))
        return sub_id

    def subscribe_queue(self, queue: Queue, filter_policy=None) -> str:
        """Attach a queue. Its copy is a durable message, not a callback."""
        return self._add("queue", queue, filter_policy)

    def subscribe_webhook(self, webhook: Webhook, filter_policy=None) -> str:
        """Attach a webhook receiver."""
        return self._add("webhook", webhook, filter_policy)

    def publish(self, body: str, attributes: Optional[Dict[str, str]] = None) -> List[str]:
        """Deliver `body` to every matching subscriber; return the ids reached."""
        self.published += 1
        reached: List[str] = []
        for subscription in self._subscriptions:
            if subscription.matches(attributes):
                subscription.deliver(body, attributes)
                reached.append(subscription.id)
                self.delivered += 1
        return reached

    def subscribers(self) -> List[str]:
        return [s.id for s in self._subscriptions]


def _demo() -> None:
    clock = Clock()
    topic = Topic("orders", clock)
    q_a = Queue("orders-a", clock)
    q_b = Queue("orders-b", clock)
    hook = Webhook("https://example.test/hooks/orders")
    topic.subscribe_queue(q_a)
    topic.subscribe_queue(q_b)
    topic.subscribe_webhook(hook)

    reached = topic.publish("order.created", {"region": "eu", "kind": "order"})
    print("Fanout: publish once, deliver to every subscriber")
    print(f"  subscribers={len(topic.subscribers())} reached={len(reached)}")
    print(f"  queue orders-a={q_a.size()}  orders-b={q_b.size()}  webhook={len(hook.deliveries)}")

    print("Filter policies: a subscriber only sees what it asked for")
    topic2 = Topic("alerts", clock)
    all_q = Queue("all", clock)
    eu_q = Queue("eu", clock)
    alert_hook = Webhook("https://example.test/hooks/alerts")
    topic2.subscribe_queue(all_q)
    topic2.subscribe_queue(eu_q, filter_policy={"region": ["eu"]})
    topic2.subscribe_webhook(alert_hook, filter_policy={"kind": ["alert"]})
    topic2.publish("info", {"region": "us", "kind": "info"})
    topic2.publish("alarm", {"region": "eu", "kind": "alert"})
    print(f"  after 2 publishes: all={all_q.size()} eu={eu_q.size()} alert-webhook={len(alert_hook.deliveries)}")


if __name__ == "__main__":
    _demo()
