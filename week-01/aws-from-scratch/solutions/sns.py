"""
SNS + EventBridge — fanout and pattern matching. Complete Solution.

DESIGN DECISION — push or pull?
  SQS is pull: a consumer asks, and a message waits until someone does.
  SNS is push: the topic delivers to every subscriber, now, and if a subscriber
  is down the message is retried and then dropped.
  CHOSEN: model push, and model the consequence — the classic architecture is
  SNS *in front of* SQS precisely so that fanout gets push semantics while each
  consumer keeps a durable buffer it controls.

DESIGN DECISION — filter at the subscriber or at the topic?
  Filtering in the subscriber is simpler and costs you a delivery per message
  per subscriber, most of which get thrown away.
  CHOSEN: filter policies evaluated at the topic. It also forces the semantics
  into the open: attributes AND across keys, OR within a key's value list —
  the same rule as IAM conditions, and wrong-footed for the same reason.
"""

import fnmatch
from typing import Any, Callable, Dict, List, Optional, Sequence


class Subscription:
    def __init__(self, protocol: str, endpoint: Any, name: str = "",
                 filter_policy: Optional[Dict[str, Any]] = None,
                 raw_delivery: bool = False):
        self.protocol = protocol          # "sqs", "lambda", "http"
        self.endpoint = endpoint
        self.name = name or protocol
        self.filter_policy = filter_policy
        self.raw_delivery = raw_delivery
        self.delivered = 0
        self.filtered_out = 0
        self.failed = 0

    def __repr__(self) -> str:
        return f"<Sub {self.name} delivered={self.delivered} filtered={self.filtered_out}>"


def matches_filter(policy: Optional[Dict[str, Any]],
                   attributes: Dict[str, Any]) -> bool:
    """SNS filter-policy semantics.

    The rule, which trips people up in exactly the same way IAM conditions do:
      - every KEY in the policy must match (AND)
      - any VALUE in that key's list may match (OR)
      - a key absent from the message attributes does NOT match

    Supported value forms: a literal, {"prefix": ...}, {"anything-but": ...},
    {"numeric": ["<", 5]}, and {"exists": true/false}.
    """
    if not policy:
        return True

    for key, allowed in policy.items():
        if not isinstance(allowed, list):
            allowed = [allowed]

        exists_rules = [rule for rule in allowed
                        if isinstance(rule, dict) and "exists" in rule]
        if exists_rules:
            wanted = exists_rules[0]["exists"]
            if (key in attributes) != wanted:
                return False
            continue

        if key not in attributes:
            return False               # missing attribute never matches

        value = attributes[key]
        if not any(_value_matches(rule, value) for rule in allowed):
            return False
    return True


def _value_matches(rule: Any, value: Any) -> bool:
    if isinstance(rule, dict):
        if "prefix" in rule:
            return str(value).startswith(rule["prefix"])
        if "anything-but" in rule:
            excluded = rule["anything-but"]
            excluded = excluded if isinstance(excluded, list) else [excluded]
            return value not in excluded
        if "numeric" in rule:
            spec = rule["numeric"]
            number = float(value)
            for index in range(0, len(spec), 2):
                operator, bound = spec[index], float(spec[index + 1])
                if operator == "<" and not number < bound:
                    return False
                if operator == "<=" and not number <= bound:
                    return False
                if operator == ">" and not number > bound:
                    return False
                if operator == ">=" and not number >= bound:
                    return False
                if operator == "=" and not number == bound:
                    return False
            return True
        return False
    return rule == value


class Topic:
    def __init__(self, name: str):
        self.name = name
        self.subscriptions: List[Subscription] = []
        self.stats = {"published": 0, "deliveries": 0, "filtered": 0, "failed": 0}

    def subscribe(self, protocol: str, endpoint: Any, name: str = "",
                  filter_policy: Optional[Dict[str, Any]] = None) -> Subscription:
        subscription = Subscription(protocol, endpoint, name, filter_policy)
        self.subscriptions.append(subscription)
        return subscription

    def publish(self, message: str,
                attributes: Optional[Dict[str, Any]] = None,
                now: Optional[float] = None) -> Dict[str, int]:
        """Deliver to every matching subscriber. One publish, N deliveries.

        `now` is threaded through to SQS subscribers so a simulated clock stays
        consistent end to end. Without it, a topic on wall-clock time enqueues
        messages "in the future" relative to a test running at t=0, and they
        silently never become visible.
        """
        attributes = attributes or {}
        self.stats["published"] += 1
        delivered = filtered = failed = 0

        for subscription in self.subscriptions:
            if not matches_filter(subscription.filter_policy, attributes):
                subscription.filtered_out += 1
                filtered += 1
                continue
            try:
                self._deliver(subscription, message, attributes, now)
                subscription.delivered += 1
                delivered += 1
            except Exception:                        # noqa: BLE001
                # A push subscriber that is down loses the message after
                # retries. This is why SNS -> SQS -> consumer is the standard
                # shape: the queue is the buffer the subscriber controls.
                subscription.failed += 1
                failed += 1

        self.stats["deliveries"] += delivered
        self.stats["filtered"] += filtered
        self.stats["failed"] += failed
        return {"delivered": delivered, "filtered": filtered, "failed": failed}

    @staticmethod
    def _deliver(subscription: Subscription, message: str,
                 attributes: Dict[str, Any],
                 now: Optional[float] = None) -> None:
        if subscription.protocol == "sqs":
            subscription.endpoint.send(message, now=now)
        elif subscription.protocol == "lambda":
            subscription.endpoint({"Message": message,
                                   "MessageAttributes": attributes}, {})
        elif subscription.protocol == "http":
            subscription.endpoint(message, attributes)
        else:
            raise ValueError(f"unknown protocol {subscription.protocol!r}")


# ---------------------------------------------------------------------------
# EventBridge: the same idea, with structural pattern matching
# ---------------------------------------------------------------------------

def matches_event_pattern(pattern: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """EventBridge matches the SHAPE of the event, not flat attributes.

    The difference from SNS: patterns nest, and a list in a pattern means "any
    of these", while a nested dict means "descend and keep matching". Content
    filters ({"prefix": ...}, {"numeric": [...]}) work at any depth.
    """
    for key, expected in pattern.items():
        if key not in event:
            return False
        actual = event[key]

        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                return False
            if not matches_event_pattern(expected, actual):
                return False
        elif isinstance(expected, list):
            if not any(_value_matches(rule, actual) for rule in expected):
                return False
        else:
            if actual != expected:
                return False
    return True


class EventBus:
    def __init__(self, name: str = "default"):
        self.name = name
        self.rules: List[Dict[str, Any]] = []
        self.stats = {"events": 0, "matched": 0}

    def add_rule(self, name: str, pattern: Dict[str, Any],
                 target: Callable[[Dict[str, Any]], None]) -> None:
        self.rules.append({"name": name, "pattern": pattern, "target": target,
                           "matched": 0})

    def put_event(self, event: Dict[str, Any]) -> List[str]:
        """An event may match zero, one or many rules — all of them fire."""
        self.stats["events"] += 1
        fired: List[str] = []
        for rule in self.rules:
            if matches_event_pattern(rule["pattern"], event):
                rule["matched"] += 1
                rule["target"](event)
                fired.append(rule["name"])
        if fired:
            self.stats["matched"] += 1
        return fired


def _demo() -> None:
    from sqs import Queue

    print("=== Fanout: one publish, many deliveries ===")
    topic = Topic("orders")
    billing = Queue("billing")
    shipping = Queue("shipping")
    audit_log: List[str] = []

    topic.subscribe("sqs", billing, "billing")
    topic.subscribe("sqs", shipping, "shipping")
    topic.subscribe("lambda", lambda e, c: audit_log.append(e["Message"]), "audit")

    result = topic.publish("order-1234 placed")
    print(f"  publish -> {result}")
    print(f"  billing queue: {billing.depth()['visible']}, "
          f"shipping: {shipping.depth()['visible']}, audit: {len(audit_log)}")
    print("  SNS pushes; SQS buffers. The standard SNS -> SQS -> consumer shape")
    print("  exists so fanout is push while each consumer keeps a durable queue.")

    print("\n=== Filter policies: AND across keys, OR within one ===")
    alerts = Topic("alerts")
    pager: List[str] = []
    email: List[str] = []
    everything: List[str] = []

    alerts.subscribe("http", lambda m, a: pager.append(m), "pagerduty",
                     filter_policy={"severity": ["critical", "high"],
                                    "env": ["prod"]})
    alerts.subscribe("http", lambda m, a: email.append(m), "email",
                     filter_policy={"severity": ["critical", "high", "low"]})
    alerts.subscribe("http", lambda m, a: everything.append(m), "firehose")

    cases = [
        ("prod critical", {"severity": "critical", "env": "prod"}),
        ("prod low", {"severity": "low", "env": "prod"}),
        ("staging critical", {"severity": "critical", "env": "staging"}),
        ("no env attribute", {"severity": "critical"}),
    ]
    print(f"  {'message':<20}{'pager':>7}{'email':>7}{'firehose':>10}")
    for label, attributes in cases:
        before = (len(pager), len(email), len(everything))
        alerts.publish(label, attributes)
        after = (len(pager), len(email), len(everything))
        marks = ["yes" if a > b else "-" for a, b in zip(after, before)]
        print(f"  {label:<20}{marks[0]:>7}{marks[1]:>7}{marks[2]:>10}")
    print("\n  'staging critical' misses the pager: BOTH keys must match.")
    print("  'no env attribute' also misses — a missing attribute never matches,")
    print("  which is the same fail-closed rule as IAM conditions, and catches")
    print("  people the same way. The unfiltered subscriber gets everything.")

    print("\n=== Content filters ===")
    filtered = Topic("metrics")
    hits: List[str] = []
    filtered.subscribe("http", lambda m, a: hits.append(m), "big-spend",
                       filter_policy={"amount": [{"numeric": [">", 100]}],
                                      "region": [{"prefix": "us-"}]})
    for label, attributes in [("small us", {"amount": 50, "region": "us-east-1"}),
                              ("big us", {"amount": 500, "region": "us-east-1"}),
                              ("big eu", {"amount": 500, "region": "eu-west-1"})]:
        before = len(hits)
        filtered.publish(label, attributes)
        print(f"  {label:<12}{'delivered' if len(hits) > before else 'filtered out'}")

    print("\n=== EventBridge matches the shape of the event ===")
    bus = EventBus()
    terminations: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    bus.add_rule("ec2-terminated",
                 {"source": ["aws.ec2"],
                  "detail": {"state": ["terminated", "stopping"]}},
                 terminations.append)
    bus.add_rule("any-failure",
                 {"detail": {"status": ["FAILED"]}},
                 failures.append)

    events = [
        {"source": "aws.ec2", "detail": {"state": "terminated", "id": "i-1"}},
        {"source": "aws.ec2", "detail": {"state": "running", "id": "i-2"}},
        {"source": "aws.batch", "detail": {"status": "FAILED", "job": "j-9"}},
        {"source": "aws.ec2", "detail": {"state": "stopping", "status": "FAILED"}},
    ]
    for event in events:
        fired = bus.put_event(event)
        print(f"  {str(event)[:58]:<60} -> {fired or 'no rule'}")
    print("\n  The last event matched BOTH rules. Nothing deduplicates that —")
    print("  each target fires independently, which is the point of a bus and")
    print("  a good way to double-process an event if you did not expect it.")


if __name__ == "__main__":
    _demo()
