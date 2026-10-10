"""
Progress checker for the SQS + SNS queue/fanout templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.
"""

import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Steps 1-4: sqs.py
# ---------------------------------------------------------------------------

def check_queue_visibility() -> None:
    from sqs import Clock, Queue

    clock = Clock()
    q = Queue("q", clock, visibility_timeout=30)
    assert q.size() == 0
    msg_id = q.send("hello")
    assert q.size() == 1

    first = q.receive()
    assert len(first) == 1, "receive() should hand out the one visible message"
    held = first[0]
    assert held.body == "hello" and held.receive_count == 1
    assert held.receipt_handle, "a received message needs a receipt handle before it can be acked"

    assert q.receive() == [], "a received message is invisible for its whole visibility timeout"
    clock.advance(29)
    assert q.receive() == [], "the message reappeared before the visibility timeout elapsed"
    clock.advance(1)
    again = q.receive()
    assert len(again) == 1 and again[0].id == msg_id, (
        "an unacknowledged message must reappear after the visibility timeout")
    assert again[0].receive_count == 2, (
        f"redelivery count is {again[0].receive_count}, expected 2: every receive increments it")
    assert q.size() == 1

    # change_visibility moves the deadline of the *current* delivery.
    assert q.change_visibility(again[0].receipt_handle, 100) is True
    clock.advance(30)
    assert q.receive() == [], (
        "change_visibility did not extend the window: the message showed up before the new deadline")
    assert q.change_visibility("not-a-handle", 5) is False, (
        "change_visibility must refuse an unknown receipt handle")


def check_queue_ack() -> None:
    from sqs import Clock, Queue

    clock = Clock()
    q = Queue("q", clock, visibility_timeout=10)
    q.send("a")
    held = q.receive()[0]
    assert q.ack(held.receipt_handle) is True
    assert q.size() == 0 and q.receive() == []
    clock.advance(1000)
    assert q.receive() == [], "an acknowledged message must be gone for good, not redelivered"
    assert q.ack(held.receipt_handle) is False, "acking the same handle twice must report False"

    # A stale handle -- one from a delivery that has since been redelivered --
    # must not delete the message out from under the current consumer.
    q.send("b")
    first = q.receive()[0]
    first_handle, first_id = first.receipt_handle, first.id
    clock.advance(10)
    second = q.receive()[0]
    assert second.id == first_id and second.receipt_handle != first_handle, (
        "a redelivery must issue a fresh receipt handle, not replay the old one")
    assert q.ack(first_handle) is False, (
        "a stale receipt handle deleted the message: ack must match the CURRENT handle, "
        "never the message id")
    assert q.size() == 1
    assert q.ack(second.receipt_handle) is True
    assert q.size() == 0


def check_queue_delay() -> None:
    from sqs import Clock, Queue

    clock = Clock()
    q = Queue("q", clock, visibility_timeout=10)
    q.send("later", delay_seconds=5)
    assert q.visible() == [], "a delayed message must stay invisible until its delay elapses"
    assert q.receive() == [], "a delayed message must stay invisible until its delay elapses"
    clock.advance(4)
    assert q.visible() == [], "the delayed message showed up one second early"
    clock.advance(1)
    assert len(q.visible()) == 1, "the delayed message never became visible"
    got = q.receive()
    assert len(got) == 1 and got[0].body == "later", "the delayed message never became visible"
    assert got[0].sent_at == 0, "the message should carry the logical time it was sent at"


def check_dead_letter() -> None:
    from sqs import Clock, Queue

    clock = Clock()
    dlq = Queue("dlq", clock)
    q = Queue("q", clock, visibility_timeout=10, max_receives=3, dead_letter_queue=dlq)
    q.send("poison")

    deliveries = 0
    for _ in range(10):
        got = q.receive()
        if got:
            deliveries += 1
            assert got[0].body == "poison"
        clock.advance(10)

    assert deliveries == 3, (
        f"max_receives=3 must give exactly 3 deliveries, got {deliveries}: a message past "
        "max_receives is not delivered again")
    assert q.size() == 0 and q.receive() == [], "the poison message stayed in the source queue"
    assert dlq.size() == 1, f"expected one message in the dead-letter queue, found {dlq.size()}"
    dead = dlq.receive(visibility_timeout=10)[0]
    assert dead.body == "poison"
    assert dead.source_receive_count == 3, (
        "the dead-letter copy must record how many receives it took (source_receive_count)")


# ---------------------------------------------------------------------------
# Steps 5-7: sns.py
# ---------------------------------------------------------------------------

def check_topic_fanout() -> None:
    from sqs import Clock, Queue
    from sns import Topic, Webhook

    clock = Clock()
    topic = Topic("orders", clock)
    q1 = Queue("orders-a", clock)
    q2 = Queue("orders-b", clock)
    hook = Webhook("https://example.test/hook")
    s1 = topic.subscribe_queue(q1)
    s2 = topic.subscribe_queue(q2)
    s3 = topic.subscribe_webhook(hook)
    assert len({s1, s2, s3}) == 3, "every subscription needs its own id"

    reached = topic.publish("order.created", {"type": "order"})
    assert set(reached) == {s1, s2, s3}, (
        f"publish reached {reached}, expected every one of the three subscriptions")
    assert q1.size() == 1 and q2.size() == 1, (
        "each queue subscription must receive its own durable copy")
    assert [d["body"] for d in hook.deliveries] == ["order.created"], (
        "the webhook subscription received nothing")
    assert hook.deliveries[0]["attributes"] == {"type": "order"}, (
        "the delivered copy must carry the message attributes")
    assert q2.receive()[0].attributes == {"type": "order"}, (
        "a queue copy must carry the message attributes too")

    # A subscription added after a publish only sees later publishes.
    q3 = Queue("orders-c", clock)
    topic.subscribe_queue(q3)
    assert q3.size() == 0, "a new subscriber must not receive messages published before it joined"
    topic.publish("order.shipped")
    assert q3.size() == 1, "the new subscriber did not receive the later publish"
    assert q1.size() == 2, "an existing subscriber missed the later publish"


def check_idempotent_consumer() -> None:
    from sqs import Clock, Consumer, IdempotentConsumer, Queue

    clock = Clock()

    # A duplicate is not exotic: process, crash before ack, visibility lapses, redeliver.
    naive_seen = []
    naive_q = Queue("naive", clock, visibility_timeout=10)
    naive_q.send("charge-card")
    naive = Consumer(naive_q, lambda m: naive_seen.append(m.body))
    naive.poll(ack=False)  # handler ran, then the process "died" before ack
    clock.advance(10)
    naive.poll()
    assert len(naive_seen) == 2, (
        "the naive consumer must process the redelivery too -- that is the at-least-once duplicate "
        "the limit case is about")
    assert naive_q.size() == 0

    # The idempotent consumer must apply the effect once and recognize the copy.
    effects = []
    idem_q = Queue("idem", clock, visibility_timeout=10)
    idem_q.send("charge-card")
    idem = IdempotentConsumer(idem_q, lambda m: effects.append(m.body))
    idem.poll(ack=False)
    clock.advance(10)
    idem.poll()
    assert len(effects) == 1, (
        f"the idempotent consumer applied the effect {len(effects)} times: a redelivered message "
        "must be recognized by its id and skipped, not processed again")
    assert idem.duplicates == 1, "the idempotent consumer must count the duplicate it skipped"
    assert idem_q.size() == 0


def check_filter_policy() -> None:
    from sqs import Clock, Queue
    from sns import Topic, Webhook

    clock = Clock()
    topic = Topic("events", clock)
    all_q = Queue("all", clock)
    eu_q = Queue("eu", clock)
    hook = Webhook("https://example.test/hook")
    topic.subscribe_queue(all_q)
    topic.subscribe_queue(eu_q, filter_policy={"region": ["eu"]})
    topic.subscribe_webhook(hook, filter_policy={"kind": ["alert"]})

    topic.publish("info", {"region": "us", "kind": "info"})
    assert all_q.size() == 1, "the unfiltered subscriber gets everything"
    assert eu_q.size() == 0 and hook.deliveries == [], (
        "a subscription filter must block a message whose attributes do not match")

    topic.publish("alarm", {"region": "eu", "kind": "alert"})
    assert all_q.size() == 2, "the unfiltered subscriber missed a later publish"
    assert eu_q.size() == 1, "the region=eu subscriber missed a matching message"
    assert len(hook.deliveries) == 1 and hook.deliveries[0]["body"] == "alarm", (
        "the kind=alert webhook filter did not fire on the matching message")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("sqs.py", "visibility timeout: an unacked message reappears", check_queue_visibility),
    ("sqs.py", "ack removes a message for good (stale handles refused)", check_queue_ack),
    ("sqs.py", "delayed delivery", check_queue_delay),
    ("sqs.py", "max receives -> dead-letter queue", check_dead_letter),
    ("sns.py", "publish reaches every subscriber", check_topic_fanout),
    ("sqs.py", "at-least-once duplicates need an idempotent consumer", check_idempotent_consumer),
    ("sns.py", "subscription filter policy", check_filter_policy),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}SQS + SNS From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<8} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<8} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<8} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built a queue and a topic.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
