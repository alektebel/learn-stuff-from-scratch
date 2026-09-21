"""
Progress checker for the AWS-from-scratch templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

Nothing here imports solutions/. It tests YOUR code.
"""

import math
import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# IAM
# ---------------------------------------------------------------------------

def check_iam_basics() -> None:
    from iam import ALLOW, DENY, Policy, Statement, evaluate

    read = Policy([Statement(ALLOW, "s3:Get*", "arn:aws:s3:::reports/*")], name="R")
    assert evaluate([read], "s3:GetObject", "arn:aws:s3:::reports/a.csv").allowed
    assert not evaluate([read], "s3:PutObject", "arn:aws:s3:::reports/a.csv").allowed, \
        "s3:Get* must not match s3:PutObject"
    assert not evaluate([read], "s3:GetObject", "arn:aws:s3:::other/a.csv").allowed, \
        "the resource ARN must be checked, not just the action"
    assert not evaluate([], "s3:GetObject", "arn:aws:s3:::x").allowed, \
        "no policies at all means implicit deny, never allow"

    admin = Policy([Statement(ALLOW, "*", "*")], name="Admin")
    guard = Policy([Statement(DENY, "s3:Delete*", "arn:aws:s3:::reports/*")],
                   name="Guard")
    for order in ([admin, guard], [guard, admin]):
        decision = evaluate(order, "s3:DeleteObject", "arn:aws:s3:::reports/a.csv")
        assert not decision.allowed, (
            "an explicit Deny must beat any Allow, in EITHER order. Policies "
            "are evaluated as a set — collect all denies first, then allows. "
            "If order changed your answer, you are iterating and letting the "
            "last match win, like a firewall.")
    assert evaluate([admin, guard], "s3:GetObject", "arn:aws:s3:::reports/a.csv").allowed


def check_iam_conditions() -> None:
    from iam import _condition_holds, ALLOW, Policy, Statement, evaluate, evaluate_with_boundary

    policy = Policy([Statement(
        ALLOW, "s3:GetObject", "arn:aws:s3:::b/*",
        condition={"IpAddress": {"aws:SourceIp": "10.0.0.0/8"},
                   "Bool": {"aws:SecureTransport": "true"}})], name="C")

    assert evaluate([policy], "s3:GetObject", "arn:aws:s3:::b/k",
                    {"aws:SourceIp": "10.1.1.1",
                     "aws:SecureTransport": True}).allowed
    assert not evaluate([policy], "s3:GetObject", "arn:aws:s3:::b/k",
                        {"aws:SourceIp": "10.1.1.1",
                         "aws:SecureTransport": False}).allowed, (
        "conditions AND across keys — both must hold")
    assert not evaluate([policy], "s3:GetObject", "arn:aws:s3:::b/k",
                        {"aws:SecureTransport": True}).allowed, (
        "a MISSING context key must never match. Conditions fail closed; "
        "treating absent as 'anything goes' is a security bug.")

    multi = Policy([Statement(ALLOW, "s3:*", "*",
                              condition={"StringEquals": {"env": ["prod", "staging"]}})])
    assert evaluate([multi], "s3:GetObject", "x", {"env": "prod"}).allowed
    assert evaluate([multi], "s3:GetObject", "x", {"env": "staging"}).allowed, \
        "values within one key are OR — any listed value may match"
    assert not evaluate([multi], "s3:GetObject", "x", {"env": "dev"}).allowed

    broad = [Policy([Statement(ALLOW, "*", "*")])]
    boundary = Policy([Statement(ALLOW, "s3:*", "*")])
    assert evaluate_with_boundary(broad, boundary, "s3:GetObject", "x").allowed
    assert not evaluate_with_boundary(broad, boundary, "iam:CreateUser", "x").allowed, \
        "a permissions boundary caps what identity policies may grant"
    assert not evaluate_with_boundary([Policy([])], boundary, "s3:GetObject", "x").allowed, \
        "a boundary must never GRANT on its own — it only subtracts"

    # Two bugs that pass every assertion above, both of which fail OPEN.
    from iam import matches_resource
    assert not matches_resource("arn:aws:s3:::b/Public/*", "arn:aws:s3:::b/public/k"), (
        "resource matching must be CASE-SENSITIVE. S3 keys are, so folding case "
        "here lets a policy written for `Public/` grant `public/` as well — an "
        "authorisation function that grants more than it says. `matches_action` "
        "IS case-insensitive; copying that `.lower()` down here is the mistake.")
    assert matches_resource("arn:aws:s3:::b/*", "arn:aws:s3:::b/Any/Key"), \
        "a wildcard still crosses slashes"

    for actual, want in ((True, False), (False, True)):
        assert _condition_holds("Bool", actual, ["false"]) is want, (
            f"Bool condition with actual={actual} against a policy value of "
            f'"false" returned {not want}. `bool("false")` is True — every '
            "non-empty string is truthy — so coercing the POLICY value inverts "
            "the condition. Parse the string instead. This is the deny-"
            "unencrypted-traffic policy, and inverted it allows the plaintext "
            "request and denies the TLS one.")

def check_sts() -> None:
    from iam import (ALLOW, Credentials, Policy, Role, Statement, assume_role,
                     evaluate)

    role = Role("arn:aws:iam::111:role/App",
                trust=Policy([Statement(ALLOW, "sts:AssumeRole",
                                        "arn:aws:iam::111:role/App",
                                        condition={"ArnLike": {
                                            "aws:PrincipalArn":
                                            "arn:aws:iam::111:user/*"}})]),
                permissions=[Policy([Statement(ALLOW, "s3:*", "*")])])

    insider = Credentials("arn:aws:iam::111:user/dev", [
        Policy([Statement(ALLOW, "sts:AssumeRole", "*")])])
    session = assume_role(insider, role, "s1")
    assert evaluate(session.policies, "s3:GetObject", "x").allowed, \
        "the session must carry the ROLE's permissions, not the caller's"

    outsider = Credentials("arn:aws:iam::999:user/mallory", [
        Policy([Statement(ALLOW, "sts:AssumeRole", "*")])])
    try:
        assume_role(outsider, role, "s2")
        raise AssertionError(
            "an outsider whose OWN policy allows sts:AssumeRole was let in. The "
            "role's TRUST policy must be checked too — that is the direction "
            "that protects you from another account.")
    except PermissionError:
        pass

    no_permission = Credentials("arn:aws:iam::111:user/intern", [Policy([])])
    try:
        assume_role(no_permission, role, "s3")
        raise AssertionError("the caller's own policy must also allow "
                             "sts:AssumeRole — both directions are required")
    except PermissionError:
        pass


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------

def check_s3_objects() -> None:
    from s3 import S3, S3Error, compute_etag

    s3 = S3()
    s3.create_bucket("b")
    etag = s3.put_object("b", "k", b"hello")
    assert etag == compute_etag(b"hello")
    assert s3.get_object("b", "k").body == b"hello"

    try:
        s3.get_object("b", "missing")
        raise AssertionError("a missing key must raise NoSuchKey")
    except S3Error as exc:
        assert exc.code == "NoSuchKey"

    multi = compute_etag(b"x" * 300, parts=[b"x" * 100] * 3)
    assert multi.endswith("-3"), (
        f"a multipart ETag must end with '-<part count>', got {multi}. It is "
        "the MD5 of the concatenated part MD5s, NOT the MD5 of the object — "
        "which is why you cannot verify a multipart upload against a local md5.")
    assert multi != compute_etag(b"x" * 300)
    # The suffix alone is not the property. The digest half must be the MD5 of
    # the CONCATENATED PART DIGESTS, so re-splitting the same bytes differently
    # gives a different ETag -- which is the actual reason a multipart object
    # cannot be verified against a local md5.
    import hashlib
    parts = [b"x" * 100] * 3
    expected = hashlib.md5(b"".join(hashlib.md5(p).digest() for p in parts)).hexdigest()
    assert multi.split("-")[0] == expected, (
        f"the digest half of a multipart ETag is {multi.split('-')[0]}; it must "
        f"be the MD5 of the concatenated part MD5s ({expected}). Hashing the "
        "whole body and appending '-N' produces a plausible-looking ETag that "
        "is wrong, and the part count alone does not catch it.")
    other = compute_etag(b"x" * 300, parts=[b"x" * 150] * 2)
    assert other.split("-")[0] != multi.split("-")[0], (
        "the same 300 bytes split into 2 parts instead of 3 must give a "
        "DIFFERENT digest. The part size changes the answer; that is why the "
        "ETag is not the object's MD5.")


def check_s3_listing_and_versioning() -> None:
    from s3 import S3, S3Error

    s3 = S3()
    s3.create_bucket("b")
    for key in ("a/1.txt", "a/2.txt", "b/1.txt", "top.txt"):
        s3.put_object("b", key, b"x")

    flat = s3.list_objects("b")
    assert flat["keys"] == ["a/1.txt", "a/2.txt", "b/1.txt", "top.txt"], \
        f"without a delimiter every key is returned flat: {flat['keys']}"

    folders = s3.list_objects("b", delimiter="/")
    assert folders["keys"] == ["top.txt"], f"got {folders['keys']}"
    assert sorted(folders["common_prefixes"]) == ["a/", "b/"], (
        f"got {folders['common_prefixes']}. The delimiter is what INVENTS "
        "folders — keys sharing a prefix collapse into a common prefix. There "
        "is no directory object anywhere.")

    scoped = s3.list_objects("b", prefix="a/", delimiter="/")
    assert scoped["keys"] == ["a/1.txt", "a/2.txt"]

    versioned = S3()
    versioned.create_bucket("v", versioning=True)
    versioned.put_object("v", "doc", b"one")
    versioned.put_object("v", "doc", b"two")
    assert versioned.get_object("v", "doc").body == b"two"
    assert len(versioned.list_object_versions("v", "doc")) == 2, \
        "a versioned bucket keeps both versions, it does not overwrite"

    versioned.delete_object("v", "doc")
    try:
        versioned.get_object("v", "doc")
        raise AssertionError("a plain GET must fail once a delete marker is on top")
    except S3Error:
        pass

    history = versioned.list_object_versions("v", "doc")
    assert len(history) == 3, (
        f"after the delete there should be 3 entries (2 versions + a delete "
        f"marker), found {len(history)}. DELETE in a versioned bucket does not "
        "delete — it pushes a marker, and the bytes stay billable.")
    assert history[-1].is_delete_marker
    first = history[0]
    assert versioned.get_object("v", "doc", first.version_id).body == b"one", \
        "a versioned GET must still reach the data under the marker"

    assert versioned.list_objects("v")["keys"] == [], \
        "a key whose latest version is a delete marker must not be listed"


# ---------------------------------------------------------------------------
# SQS
# ---------------------------------------------------------------------------

def check_sqs_visibility() -> None:
    from sqs import Queue

    queue = Queue("q", visibility_timeout=10)
    queue.send("job", now=0)
    assert queue.depth(now=0)["visible"] == 1

    first = queue.receive(now=0)
    assert len(first) == 1 and first[0].receive_count == 1
    assert queue.depth(now=0) == {"visible": 0, "delayed": 0, "in_flight": 1}, \
        "a received message is in flight, not gone — receive is a LEASE"

    assert queue.receive(now=5) == [], \
        "a leased message must stay hidden until the visibility timeout expires"

    second = queue.receive(now=11)
    assert len(second) == 1, (
        "once the lease expires the message MUST come back. That redelivery is "
        "at-least-once semantics working as designed — the queue chose "
        "duplication over loss.")
    assert second[0].receive_count == 2

    assert not queue.delete(first[0].receipt_handle), (
        "the FIRST consumer's receipt handle is now stale and its delete must "
        "fail. If it succeeded, both consumers share one Message object and "
        "the second receive overwrote the first's handle — give each receive "
        "its own view.")
    assert queue.delete(second[0].receipt_handle)
    assert queue.depth(now=12)["visible"] == 0

    extended = Queue("e", visibility_timeout=10)
    extended.send("slow", now=0)
    held = extended.receive(now=0)[0]
    extended.change_visibility(held.receipt_handle, 60, now=5)
    assert extended.receive(now=11) == [], \
        "change_visibility must extend the lease — the fix for slow consumers"


def check_sqs_dlq_and_fifo() -> None:
    from sqs import Queue

    dlq = Queue("dlq")
    main = Queue("main", visibility_timeout=1, max_receives=2, dead_letter=dlq)
    main.send("poison", now=0)
    for attempt in range(5):
        main.receive(now=attempt * 2)
    assert len(dlq.messages) == 1, (
        f"after exceeding max_receives the message must move to the DLQ, found "
        f"{len(dlq.messages)}. Without one it is retried forever, consuming "
        "throughput and hiding the messages behind it.")
    assert main.depth(now=100)["visible"] == 0

    fifo = Queue("f.fifo", fifo=True, visibility_timeout=30)
    for i in range(3):
        fifo.send(f"A{i}", group_id="A", now=0)
    fifo.send("B0", group_id="B", now=0)

    batch = fifo.receive(max_messages=10, now=0)
    groups = [m.group_id for m in batch]
    assert groups.count("A") == 1, (
        f"a FIFO queue must deliver only ONE in-flight message per group, got "
        f"{groups}. Ordering within a group costs you parallelism within it.")
    assert "B" in groups, "a different group is not blocked"

    dedup = Queue("d.fifo", fifo=True)
    assert dedup.send("pay", "A", "order-7", now=0) is not None
    assert dedup.send("pay", "A", "order-7", now=10) is None, \
        "a duplicate dedup_id within the 5-minute window must be dropped"
    assert dedup.send("pay", "A", "order-7", now=400) is not None, \
        "outside the window it is accepted again"

    aged = Queue("a", visibility_timeout=1)
    aged.send("m", now=0)
    aged.receive(now=0)
    assert aged.oldest_age(now=300) > 250, (
        "oldest_age must count IN-FLIGHT messages too. A message being retried "
        "forever is exactly the case the age alarm exists to catch.")


# ---------------------------------------------------------------------------
# DynamoDB
# ---------------------------------------------------------------------------

def check_dynamo_keys() -> None:
    from dynamodb import ConditionalCheckFailed, DynamoError, Table

    table = Table("t", partition_key="pk", sort_key="sk",
                  read_capacity=100, write_capacity=100, num_partitions=4)
    for pk in ("alice", "bob", "carol"):
        for n in range(2):
            table.put_item({"pk": pk, "sk": f"{n:03d}", "v": n}, now=0)

    assert table.get_item("alice", "000", now=0)["v"] == 0
    assert table.get_item("bob", "000", now=0)["v"] == 0, (
        "alice/000 and bob/000 must be distinct items. If bob's overwrote "
        "alice's, your partition is keyed by the SORT key alone — it must be "
        "keyed by the full composite key.")
    assert table.get_item("nobody", "000", now=0) is None

    rows = table.query("alice", now=0)
    assert len(rows) == 2 and all(r["pk"] == "alice" for r in rows), \
        f"query must return only the requested partition, got {rows}"

    try:
        table.put_item({"sk": "x"}, now=0)
        raise AssertionError("an item without the partition key must raise")
    except DynamoError:
        pass

    table.put_item({"pk": "new", "sk": "1", "v": 1},
                   condition=lambda existing: existing is None, now=0)
    try:
        table.put_item({"pk": "new", "sk": "1", "v": 2},
                       condition=lambda existing: existing is None, now=0)
        raise AssertionError(
            "a failed condition must raise ConditionalCheckFailed. This is how "
            "you get idempotent creates and optimistic locking with no lock "
            "service at all.")
    except ConditionalCheckFailed:
        pass
    assert table.get_item("new", "1", now=0)["v"] == 1, \
        "the failed conditional write must not have changed anything"


def check_dynamo_capacity() -> None:
    from dynamodb import Table, ThroughputExceeded

    table = Table("t", partition_key="pk", read_capacity=100, num_partitions=1)
    table.put_item({"pk": "x"}, now=0)
    partition = table.partitions["p0"]

    partition.read_used = 0.0
    table.get_item("x", consistent=False, now=0)
    eventual = partition.read_used
    partition.read_used = 0.0
    table.get_item("x", consistent=True, now=0)
    assert partition.read_used == eventual * 2, (
        f"a strongly consistent read must cost twice an eventually consistent "
        f"one ({partition.read_used} vs {eventual})")

    hot = Table("h", partition_key="day", sort_key="seq",
                read_capacity=40, write_capacity=40, num_partitions=4)
    assert hot.per_partition_write == 10.0, (
        "table capacity is divided ACROSS partitions — that division is the "
        "entire reason a hot key throttles while the table looks idle")
    written = 0
    try:
        for n in range(30):
            hot.put_item({"day": "same-key", "seq": f"{n:04d}"}, now=0)
            written += 1
        raise AssertionError(
            "30 writes to ONE partition key with 10 WCU per partition must "
            "throttle. If it did not, capacity is being checked table-wide "
            "instead of per partition, and the most common DynamoDB surprise "
            "cannot be reproduced.")
    except ThroughputExceeded:
        pass
    assert written == 10, f"expected 10 writes before throttling, got {written}"

    spread = Table("s", partition_key="day", sort_key="seq",
                   read_capacity=40, write_capacity=40, num_partitions=4)
    for n in range(20):
        spread.put_item({"day": f"key-{n}", "seq": "0"}, now=0)   # must not throttle

    counts = Table("c", partition_key="pk", read_capacity=1000,
                   write_capacity=1000, num_partitions=4)
    for pk in ("alice", "bob", "carol"):
        counts.put_item({"pk": pk, "v": 1}, now=0)
    before = counts.stats["scanned_items"]
    counts.query("alice", now=0)
    query_cost = counts.stats["scanned_items"] - before
    before = counts.stats["scanned_items"]
    counts.scan(lambda i: i["pk"] == "alice", now=0)
    scan_cost = counts.stats["scanned_items"] - before
    assert scan_cost > query_cost, (
        f"scan read {scan_cost} items, query read {query_cost}. A scan must "
        "read EVERY item and filter afterwards — that is why a scan returning "
        "3 of a million items still costs a million reads.")


# ---------------------------------------------------------------------------
# Lambda
# ---------------------------------------------------------------------------

def check_lambda_lifecycle() -> None:
    from lambda_svc import Function, LambdaService

    service = LambdaService(account_concurrency=10)

    def handler(event, context):
        context["env"]["n"] = context["env"].get("n", 0) + 1
        return context["env"]["n"]

    service.register(Function("f", handler, init_ms=800, env_ttl_s=300))

    first = service.invoke("f", {}, now=0)
    assert first.cold, "the first invocation must be a cold start"
    assert first.billed_ms >= 800, \
        f"a cold start must include the init cost, billed {first.billed_ms}"

    second = service.invoke("f", {}, now=1)
    assert not second.cold, "the second invocation must reuse the environment"
    assert second.billed_ms < first.billed_ms
    assert second.result == 2, (
        f"warm state must survive between invocations, got {second.result}. "
        "Anything outside the handler persists — great for a connection pool, "
        "a disaster for a cache you assumed was empty.")

    stale = service.invoke("f", {}, now=1000)
    assert stale.cold, "an environment past its TTL must be replaced"
    assert stale.result == 1, "a fresh environment starts with fresh state"

    timed_out = service.invoke("f", {}, now=2000, duration_ms=99_999)
    assert timed_out.error and "timed out" in timed_out.error.lower()
    assert timed_out.billed_ms > 0, "a timeout is billed in full"


def check_lambda_concurrency() -> None:
    from lambda_svc import Function, LambdaService, Throttled

    service = LambdaService(account_concurrency=10)
    service.register(Function("api", lambda e, c: "ok", init_ms=10))

    succeeded, throttled = service.concurrent_invoke(
        "api", [{} for _ in range(15)], now=0)
    assert succeeded == 10 and throttled == 5, (
        f"15 simultaneous events against a limit of 10 must shed 5, got "
        f"{succeeded} ran / {throttled} throttled. Throttling is a QUOTA, not "
        "a speed problem.")

    service.register(Function("critical", lambda e, c: "ok",
                              reserved_concurrency=6))
    assert service.unreserved_capacity() == 4, (
        f"reserving 6 of 10 must leave 4 for everything else, got "
        f"{service.unreserved_capacity()}. Reserved concurrency is carved out "
        "whether it is used or not — which is how one reservation throttles an "
        "unrelated function.")

    succeeded, throttled = service.concurrent_invoke(
        "api", [{} for _ in range(10)], now=100)
    assert succeeded == 4, (
        f"'api' was never changed, yet it can now only run {succeeded}. That "
        "silent reduction is the point of the check.")

    # A reservation is a floor AND a ceiling. The assertions above only prove
    # the floor -- that other functions lost capacity. Prove the ceiling too, or
    # a function that ignores its own reservation passes every test here.
    succeeded, throttled = service.concurrent_invoke(
        "critical", [{} for _ in range(10)], now=200)
    assert succeeded == 6 and throttled == 4, (
        f"'critical' reserved 6 and ran {succeeded}. Reserved concurrency caps "
        "the function as well as protecting it -- it cannot borrow from the "
        "unreserved pool, which is the half people forget when they reserve "
        "capacity to make a function faster.")

    # A timeout is billed for the full timeout, not for the work actually done.
    slow = Function("slow", lambda e, c: "ok", init_ms=0, timeout_s=1)
    service.register(slow)
    before = slow.stats["billed_ms"]
    result = service.invoke("slow", {}, now=300, duration_ms=5000)
    assert result.error, "a 5s run against a 1s timeout must fail"
    assert slow.stats["billed_ms"] - before == 1000, (
        f"a timed-out invocation billed {slow.stats['billed_ms'] - before} ms; "
        "it must be billed for the full timeout (1000 ms). Billing the actual "
        "duration makes a runaway function look cheap in the very run where it "
        "cost you the most.")

    dlq: List[object] = []

    def explode(event, context):
        raise ValueError("nope")

    service.register(Function("bad", explode, init_ms=10, dead_letter=dlq))
    attempts = service.invoke_async("bad", {"job": 1}, now=200)
    assert len(attempts) == 3, (
        f"an async invocation must be retried before giving up, got "
        f"{len(attempts)} attempt(s). A non-idempotent handler runs three "
        "times — three charges, three emails.")
    assert dlq == [{"job": 1}], "the exhausted event must reach the dead letter"

    sync = service.invoke("bad", {"job": 2}, now=300)
    assert sync.error, "a synchronous failure surfaces to the caller immediately"


# ---------------------------------------------------------------------------
# SNS / EventBridge
# ---------------------------------------------------------------------------

def check_sns_fanout_and_filters() -> None:
    from sns import Topic, matches_filter
    from sqs import Queue

    topic = Topic("t")
    a, b = Queue("a"), Queue("b")
    seen: List[str] = []
    topic.subscribe("sqs", a, "a")
    topic.subscribe("sqs", b, "b")
    topic.subscribe("lambda", lambda e, c: seen.append(e["Message"]), "fn")

    result = topic.publish("hello", now=0)
    assert result["delivered"] == 3, f"one publish, three deliveries: {result}"
    assert a.depth(now=0)["visible"] == 1 and b.depth(now=0)["visible"] == 1, (
        "SNS must deliver to SQS on the SAME clock it was given. If the queues "
        "look empty, `now` is not being threaded through to the subscriber and "
        "messages landed in the future.")
    assert seen == ["hello"]

    # Everything above subscribed WITHOUT a filter policy, so none of it proves
    # publish() consults one. A topic that ignores filter policies entirely
    # passes every assertion so far -- and quietly fans every message out to
    # every subscriber, which is a correctness bug and a bill.
    filtered = Topic("f")
    prod, dev = Queue("prod"), Queue("dev")
    filtered.subscribe("sqs", prod, "prod", filter_policy={"env": ["prod"]})
    filtered.subscribe("sqs", dev, "dev", filter_policy={"env": ["dev"]})
    result = filtered.publish("deploy", attributes={"env": "prod"}, now=0)
    assert result["delivered"] == 1 and result["filtered"] == 1, (
        f"one matching subscriber and one filtered out, got {result}. If both "
        "were delivered, publish() is not applying the filter policy at all.")
    assert prod.depth(now=0)["visible"] == 1 and dev.depth(now=0)["visible"] == 0, (
        "the message must reach 'prod' and NOT 'dev'. The filter runs at the "
        "topic, before delivery -- which is the whole reason it saves money "
        "rather than merely saving the subscriber some work.")

    assert matches_filter(None, {"any": "thing"}), "no policy means deliver"
    assert matches_filter({"s": ["a", "b"]}, {"s": "b"}), \
        "values within one key are OR"
    assert not matches_filter({"s": ["a"], "e": ["prod"]}, {"s": "a"}), (
        "keys AND: a policy naming two attributes needs BOTH, and a MISSING "
        "attribute never matches — the same fail-closed rule as IAM conditions")
    assert not matches_filter({"s": ["a"]}, {"s": "z"})
    assert matches_filter({"n": [{"numeric": [">", 100]}]}, {"n": 500})
    assert not matches_filter({"n": [{"numeric": [">", 100]}]}, {"n": 5})
    assert matches_filter({"r": [{"prefix": "us-"}]}, {"r": "us-east-1"})
    assert matches_filter({"x": [{"anything-but": "no"}]}, {"x": "yes"})
    assert matches_filter({"k": [{"exists": False}]}, {"other": 1}), \
        "{'exists': False} matches when the attribute is absent"


def check_eventbridge() -> None:
    from sns import EventBus, matches_event_pattern

    assert matches_event_pattern({"source": ["aws.ec2"]}, {"source": "aws.ec2"})
    assert not matches_event_pattern({"source": ["aws.ec2"]}, {"source": "aws.s3"})
    assert not matches_event_pattern({"source": ["aws.ec2"]}, {"other": 1}), \
        "a key absent from the event cannot match"
    assert matches_event_pattern(
        {"detail": {"state": ["terminated"]}},
        {"detail": {"state": "terminated", "id": "i-1"}}), \
        "patterns must nest — EventBridge matches the SHAPE of the event"
    assert not matches_event_pattern(
        {"detail": {"state": ["terminated"]}},
        {"detail": {"state": "running"}})

    bus = EventBus()
    one: List[dict] = []
    two: List[dict] = []
    bus.add_rule("a", {"source": ["aws.ec2"]}, one.append)
    bus.add_rule("b", {"detail": {"status": ["FAILED"]}}, two.append)

    fired = bus.put_event({"source": "aws.ec2",
                           "detail": {"status": "FAILED"}})
    assert set(fired) == {"a", "b"}, (
        f"an event matching two rules must fire BOTH, got {fired}. Nothing "
        "deduplicates that — a good way to double-process an event.")
    assert bus.put_event({"source": "aws.s3"}) == []


# ---------------------------------------------------------------------------
# KMS
# ---------------------------------------------------------------------------

def check_kms_envelope() -> None:
    from kms import KMS, EnvelopeCipher, KMSError

    kms = KMS()
    key = kms.create_key("k")
    cipher = EnvelopeCipher(kms, "k")

    data_key = kms.generate_data_key("k")
    assert len(data_key.plaintext) == 32
    assert data_key.encrypted.wrapped != data_key.plaintext, \
        "the wrapped copy must not equal the plaintext copy"
    assert kms.decrypt_data_key(data_key.encrypted) == data_key.plaintext, \
        "unwrapping must recover exactly the plaintext data key"

    document = b"secret" * 500
    ciphertext, wrapped = cipher.encrypt(document)
    assert ciphertext != document
    assert cipher.decrypt(ciphertext, wrapped) == document
    assert len(ciphertext) == len(document), \
        "envelope encryption keeps the data with YOU — size is unchanged"

    calls_before = key.stats["data_keys"]
    cipher.encrypt(b"x" * 100_000)
    assert key.stats["data_keys"] == calls_before + 1, (
        "one KMS call per OBJECT, not per byte — that is the whole reason the "
        "4KB KMS payload limit does not constrain you")


def check_kms_context_and_rotation() -> None:
    from kms import KMS, EnvelopeCipher, KMSError

    kms = KMS()
    key = kms.create_key("k")
    cipher = EnvelopeCipher(kms, "k")

    ciphertext, wrapped = cipher.encrypt(b"tenant A", {"tenant": "A"})
    assert cipher.decrypt(ciphertext, wrapped, {"tenant": "A"}) == b"tenant A"
    for wrong in ({"tenant": "B"}, {}, None):
        try:
            cipher.decrypt(ciphertext, wrapped, wrong)
            raise AssertionError(
                f"decrypting with context {wrong} must fail. The encryption "
                "context is authenticated data — not secret, but it must match, "
                "and it is what lets an IAM condition scope a key to a tenant.")
        except KMSError:
            pass

    old_cipher, old_wrapped = cipher.encrypt(b"before")
    assert old_wrapped.version == 1
    assert key.rotate() == 2
    new_cipher, new_wrapped = cipher.encrypt(b"after")
    assert new_wrapped.version == 2, "new encryptions use the new version"
    assert cipher.decrypt(old_cipher, old_wrapped) == b"before", (
        "old ciphertext MUST still decrypt after rotation. Rotation re-encrypts "
        "KEYS, never DATA — one that broke old ciphertext would be an outage.")
    assert cipher.decrypt(new_cipher, new_wrapped) == b"after"

    key.versions = [v for v in key.versions if v.version != 1]
    try:
        cipher.decrypt(old_cipher, old_wrapped)
        raise AssertionError("ciphertext wrapped under a deleted key version "
                             "must be unrecoverable, and say so clearly")
    except KMSError:
        pass


# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------

def check_vpc_cidr() -> None:
    from vpc import Cidr, Vpc

    assert Cidr("10.0.0.0/16").contains(Cidr("10.0.1.0/24"))
    assert not Cidr("10.0.0.0/16").contains(Cidr("10.1.0.0/24"))
    assert Cidr("10.0.1.0/24").overlaps(Cidr("10.0.1.128/25"))
    assert not Cidr("10.0.1.0/24").overlaps(Cidr("10.0.2.0/24"))
    assert Cidr("10.0.0.0/28").usable_hosts() == 11, (
        f"a /28 has 16 addresses but only 11 usable — AWS reserves 5 per "
        f"subnet, got {Cidr('10.0.0.0/28').usable_hosts()}")

    vpc = Vpc("v", "10.0.0.0/16")
    vpc.add_subnet("a", "10.0.1.0/24")
    for bad in ("10.0.1.128/25", "192.168.0.0/24"):
        try:
            vpc.add_subnet("bad", bad)
            raise AssertionError(f"{bad} must be rejected (overlap or outside)")
        except ValueError:
            pass

    subnet = vpc.subnets["a"]
    subnet.add_route("0.0.0.0/0", "igw")
    subnet.add_route("10.1.0.0/16", "peering")
    subnet.add_route("10.1.5.0/24", "tgw")
    assert subnet.route_for("10.1.5.7") == "tgw", (
        "route tables match the LONGEST PREFIX, not the first entry — "
        "10.1.5.7 matches three routes and must take the /24")
    assert subnet.route_for("10.1.9.9") == "peering"
    assert subnet.route_for("8.8.8.8") == "igw"
    assert subnet.route_for("10.0.1.5") == "local"


def check_stateful_vs_stateless() -> None:
    """The difference that causes the most VPC confusion."""
    from vpc import NetworkAcl, SecurityGroup, test_connection

    sg = SecurityGroup("sg")
    sg.allow_inbound("tcp", 443, 443, "0.0.0.0/0")
    result = test_connection("203.0.113.5", "10.0.1.10", 443, security_group=sg)
    assert result["allowed"], (
        "a security group is STATEFUL: allowing the request in implicitly "
        "allows the reply out. No return rule is ever needed.")

    naive = NetworkAcl("naive")
    naive.add("in", 100, "allow", "tcp", 443, 443, "0.0.0.0/0")
    naive.add("out", 100, "allow", "tcp", 443, 443, "0.0.0.0/0")
    result = test_connection("203.0.113.5", "10.0.1.10", 443, acl=naive)
    assert not result["allowed"], (
        "identical rules on a NACL must FAIL. A NACL is STATELESS: the reply is "
        "a separate packet going to an EPHEMERAL port (49152-65535), and "
        "nothing here allows that. This is the single most common VPC bug, and "
        "if your model does not reproduce it, it is not modelling the "
        "connection — only the request.")

    fixed = NetworkAcl("fixed")
    fixed.add("in", 100, "allow", "tcp", 443, 443, "0.0.0.0/0")
    fixed.add("out", 100, "allow", "tcp", 1024, 65535, "0.0.0.0/0")
    assert test_connection("203.0.113.5", "10.0.1.10", 443,
                           acl=fixed)["allowed"], \
        "with an ephemeral-port outbound rule the connection must work"

    ordered = NetworkAcl("o")
    ordered.add("in", 100, "deny", "tcp", 22, 22, "0.0.0.0/0")
    ordered.add("in", 200, "allow", "tcp", 22, 22, "10.0.0.0/8")
    allowed, why = ordered.evaluate("in", "tcp", 22, "10.0.5.5")
    assert not allowed, (
        "NACL rules are evaluated in NUMBER order, first match wins — the deny "
        f"at 100 must shadow the allow at 200. Got: {why}")
    assert not sg.evaluate("in", "tcp", 22, "10.0.5.5"), \
        "a security group has no deny rules: absence of an allow IS the deny"


# ---------------------------------------------------------------------------
# Capstone
# ---------------------------------------------------------------------------

def check_capstone() -> None:
    from capstone import AccessDenied, build, drain, upload

    system = build()
    result = upload(system, system["uploader"], "acme", "report.pdf",
                    b"payload", now=0)
    assert result["delivered"] == 1, f"the pdf should reach the queue: {result}"
    assert system["queue"].depth(now=0)["visible"] == 1

    outcome = drain(system, now=1)
    assert outcome["processed"] == 1, f"the worker should index it: {outcome}"
    rows = system["documents"].query("acme", now=2)
    assert len(rows) == 1 and rows[0]["doc_id"] == "report.pdf", \
        f"the pipeline must land a row in DynamoDB, got {rows}"

    try:
        upload(system, system["uploader"], "acme", "private/pay.pdf",
               b"x", now=3)
        raise AssertionError(
            "the explicit Deny on the private/ prefix must block the upload "
            "BEFORE anything is encrypted, stored or published")
    except AccessDenied:
        pass
    assert "private/pay.pdf" not in system["cloud"].s3.buckets["uploads"].objects, \
        "an authorisation failure must leave no side effects behind"

    before = system["queue"].depth(now=4)["visible"]
    result = upload(system, system["uploader"], "acme", "photo.png", b"x",
                    content_type="image/png", now=4)
    assert result["filtered"] == 1 and result["delivered"] == 0, \
        "the filter policy must drop the png at the TOPIC, not at the consumer"
    assert system["queue"].depth(now=4)["visible"] == before

    denied = [line for line in system["cloud"].audit if line.startswith("DENY")]
    assert denied, "the audit trail must record denied calls, not only allowed ones"

    # The pipeline "works" end to end whether or not the payload was ever
    # encrypted -- the row lands in DynamoDB either way. Check the bytes.
    stored = system["cloud"].s3.get_object("uploads", "report.pdf")
    assert stored.body != b"payload", (
        "the object in S3 is the plaintext that was uploaded. Envelope "
        "encryption that returns a ciphertext and then stores the original is "
        "the failure mode this capstone exists to make visible: every assertion "
        "above still passes.")
    assert stored.metadata.get("kms_version"), (
        "the object must record which key version wrapped it. Without it the "
        "ciphertext is unreadable after a rotation retires that version.")

    # A message whose handler failed must NOT be deleted -- the visibility
    # timeout is what returns it. Deleting first loses the work silently.
    from lambda_svc import Function
    system["cloud"].lambda_service.register(
        Function("boom", lambda e, c: (_ for _ in ()).throw(ValueError("x"))))
    system["queue"].send("acme/again.pdf", now=200)
    original = system["cloud"].lambda_service.functions["indexer"]
    system["cloud"].lambda_service.functions["indexer"] = \
        system["cloud"].lambda_service.functions["boom"]
    outcome = drain(system, now=200)
    system["cloud"].lambda_service.functions["indexer"] = original
    assert outcome["processed"] == 0, f"the handler raised, so nothing was processed: {outcome}"
    held = system["queue"].depth(now=200)
    assert held["visible"] + held["in_flight"] >= 1, (
        "a message whose handler FAILED is gone from the queue. Deleting on "
        "receive rather than on SUCCESS loses the work with no error anywhere "
        "-- which is the reason the queue sits between the topic and the "
        f"function at all. Depth after the failed drain: {held}")
    recovered = drain(system, now=400)
    assert recovered["processed"] == 1, (
        f"once the lease expired the message must be redelivered and succeed "
        f"this time, got {recovered}. That redelivery is the whole value of "
        "acknowledging on success instead of on receipt.")


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

def check_pricing_arithmetic() -> None:
    from pricing import billable_units, per_unit, price, prorate, tiered_cost

    assert abs(per_unit(0.20, 1e6) - 2e-7) < 1e-15, \
        "$0.20 per million is $0.0000002 each"
    assert abs(per_unit(0.005, 1000) - 5e-6) < 1e-15
    try:
        per_unit(0.20, 0)
        raise AssertionError("a zero denominator must raise, not divide")
    except (ValueError, ZeroDivisionError):
        pass

    assert billable_units(1.1, 1.0) == 2, "a 1.1 KB write costs 2 WCU"
    assert billable_units(0.2, 1.0) == 1, "a 200-byte write still costs 1 WCU"
    assert billable_units(5.0, 4.0) == 2, "a 5 KB consistent read costs 2 RCU"
    assert billable_units(4.0, 4.0) == 1, (
        "an EXACT 4 KB read is 1 RCU, not 2. If you got 2, ceil() is seeing "
        "4.0000000000000009 — subtract a small epsilon before the ceiling.")
    assert billable_units(0.0, 1.0) == 1, "the minimum is one unit, not zero"

    tiers = [(100.0, 0.09), (float("inf"), 0.05)]
    assert abs(tiered_cost(50.0, tiers) - 4.5) < 1e-9
    assert abs(tiered_cost(150.0, tiers) - (100 * 0.09 + 50 * 0.05)) < 1e-9, (
        "graduated tiers price the PORTION in each tier. 150 units is "
        "100 at the first rate plus 50 at the second — not 150 at either.")
    assert tiered_cost(0.0, tiers) == 0.0

    egress = price("network", "internet_out_tiers")
    assert tiered_cost(300_000.0, egress) > 300_000.0 * egress[-1][1], (
        "at 300 TB the graduated answer must exceed the top-rate answer — "
        "the first 10 TB are charged at 0.09, not 0.05")

    assert abs(prorate(730.0, 365.0) - 365.0) < 1e-9, \
        "half a month of a monthly charge is half the charge"


def check_bill() -> None:
    from pricing import Bill, FreeTier, money

    assert money(0) == "$0"
    small = money(4e-7)
    assert small not in ("$0.00", "$0"), (
        f"money(0.0000004) printed {small!r}. Rounding sub-cent line items to "
        "$0.00 and then summing a hundred of them is how a cost model reports "
        "zero for a workload that costs real money.")
    assert money(1234.5) == "$1,234.50"

    bill = Bill("t", 730.0)
    bill.add("lambda", "requests", 20e6, "request", 2e-7)
    bill.add("network", "nat-gateway-hours", 730.0, "hour", 0.045)
    bill.add("s3", "puts", 1e6, "request", 5e-6)
    assert abs(bill.total - (4.0 + 32.85 + 5.0)) < 1e-9
    assert bill.dominant().dimension == "nat-gateway-hours"
    assert list(bill.by_service()) == ["network", "s3", "lambda"], (
        "by_service must be sorted most expensive first — the ordering IS the "
        "product")
    assert abs(bill.share(bill.dominant()) - 32.85 / 41.85) < 1e-9
    assert [i.dimension for i in bill.by_dimension()][0] == "nat-gateway-hours"

    ten = bill.scaled(10.0)
    fixed = [i for i in ten.items if i.dimension == "nat-gateway-hours"][0]
    variable = [i for i in ten.items if i.dimension == "requests"][0]
    assert abs(fixed.cost - 32.85) < 1e-9, (
        "a NAT gateway hour does not scale with traffic. If scaled() multiplied "
        "it, the fixed-versus-variable crossover — the reason cost advice flips "
        "with volume — becomes invisible.")
    assert abs(variable.cost - 40.0) < 1e-9, "variable lines DO scale"
    assert abs(bill.total - 41.85) < 1e-9, "scaled() must not mutate the original"

    tiered = Bill("g")
    tiered.add_tiered("network", "internet-out-gb", 150.0, "GB",
                      [(100.0, 0.09), (float("inf"), 0.05)])
    assert abs(tiered.total - 11.5) < 1e-9
    assert abs(tiered.items[0].unit_price - 11.5 / 150.0) < 1e-9, \
        "a tiered line should record its EFFECTIVE unit price"

    free = Bill("f")
    free.add("lambda", "requests", 1_500_000.0, "request", 2e-7)
    discounted, waived = FreeTier.apply(free)
    assert abs(waived - 0.2) < 1e-9, (
        f"1M of 1.5M Lambda requests are free, so $0.20 is waived, not "
        f"${waived:.4f}")
    assert abs(discounted.total - 0.1) < 1e-9
    assert abs(free.total - 0.3) < 1e-9, "apply() must not mutate the original"


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------

def check_billing_s3() -> None:
    from billing import bill_s3, stored_bytes
    from s3 import S3

    s3 = S3()
    s3.create_bucket("b", versioning=True)
    for n in range(10):
        s3.put_object("b", f"k{n}", b"x" * 100_000)
    before = stored_bytes(s3)
    assert before["live"] == 1_000_000 and before["noncurrent"] == 0

    for n in range(10):
        s3.delete_object("b", f"k{n}")
    after = stored_bytes(s3)
    assert after["live"] == 0, "a delete marker hides the current version"
    assert after["noncurrent"] == 1_000_000, (
        "a plain DELETE in a versioned bucket deletes NOTHING. The bytes move "
        "from 'live' to 'noncurrent' and stay fully billable. If noncurrent is "
        "0 here you are reading only the visible listing, which is exactly the "
        "mistake that makes a bucket cost more than the data in it.")
    assert after["total"] == before["total"], "the billable total did not move"
    assert after["delete_markers"] == 10

    # The 128 KB minimum billable object size, on objects far below it.
    small = S3()
    small.create_bucket("s")
    for n in range(100):
        small.put_object("s", f"k{n}", b"x" * 4096)
    standard = bill_s3(small, storage_class="standard", days=30.4167)
    ia = bill_s3(small, storage_class="standard_ia", days=30.4167)

    def storage(bill):
        return sum(i.cost for i in bill.items
                   if i.dimension == "storage-gb-months")

    assert storage(ia) > storage(standard) * 10, (
        f"Standard-IA storage on 4 KB objects came out at {storage(ia):.8f} "
        f"versus Standard's {storage(standard):.8f}. IA's sticker price is HALF "
        "Standard's, but every object under 128 KB is billed as 128 KB — so on "
        "4 KB objects IA is ~32x its sticker price and far more expensive than "
        "Standard. Miss this and 'move cold data to IA' makes the bill go up.")

    # The minimum storage DURATION.
    week = bill_s3(small, storage_class="deep_archive", days=7)
    month = bill_s3(small, storage_class="deep_archive", days=30)
    half_year = bill_s3(small, storage_class="deep_archive", days=180)
    assert abs(storage(week) - storage(half_year)) < 1e-12, (
        "Deep Archive has a 180-day minimum. Storing an object for a week must "
        "cost the same as storing it for 180 days.")
    assert abs(storage(month) - storage(half_year)) < 1e-12
    year = bill_s3(small, storage_class="deep_archive", days=365)
    assert storage(year) > storage(half_year), "past the minimum it grows again"

    assert any(i.dimension == "deletes" and i.cost == 0 for i in month.items), \
        "DELETE is free, and the line belongs on the bill at $0 anyway"


def check_billing_services() -> None:
    from billing import (bill_dynamodb, bill_kms, bill_lambda, bill_network,
                         bill_sns, bill_sqs)
    from dynamodb import Table
    from kms import KMS, EnvelopeCipher
    from lambda_svc import Function, LambdaService
    from sns import Topic
    from sqs import Queue

    # -- DynamoDB: the same table, both modes ------------------------------
    table = Table("t", partition_key="pk", sort_key="sk",
                  read_capacity=100, write_capacity=100, num_partitions=4)
    for n in range(50):
        table.put_item({"pk": f"p{n}", "sk": "0"}, now=0.0)
    # A filtered scan: 50 items touched, exactly 1 returned. The gap between
    # those two numbers is what the read line has to be built from.
    returned = table.scan(lambda item: item["pk"] == "p7", now=1.0)
    assert len(returned) == 1

    provisioned = bill_dynamodb(table, mode="provisioned", hours=730.0)
    on_demand = bill_dynamodb(table, mode="on_demand", hours=730.0)
    assert abs(provisioned.total - (100 * 730 * 0.00065 + 100 * 730 * 0.00013)) < 1e-6, (
        "provisioned bills RESERVED capacity x hours. Nothing about the traffic "
        "may appear in the number.")

    busier = Table("t2", partition_key="pk", read_capacity=100,
                   write_capacity=100, num_partitions=4)
    for n in range(200):
        busier.put_item({"pk": f"p{n}"}, now=n * 0.05)
    assert abs(bill_dynamodb(busier, mode="provisioned", hours=730.0).total
               - provisioned.total) < 1e-6, (
        "4x the traffic on the same reserved capacity must cost the SAME in "
        "provisioned mode. That is the entire risk of provisioning, and the "
        "entire reason the crossover exists.")

    reads = [i for i in on_demand.items if i.dimension == "on-demand-reads"][0]
    assert abs(reads.quantity - 25.0) < 1e-9, (
        f"the read line billed {reads.quantity} units for a scan that touched "
        "50 items and returned 1. It must be 25 (50 items x 0.5 RRU each). If "
        "you got 0.5 you billed returned_items — but DynamoDB charges for what "
        "it READ, not what it gave back, and that difference IS the whole "
        "scan-versus-query cost argument.")

    try:
        bill_dynamodb(table, mode="spot")
        raise AssertionError("an unknown billing mode must raise, not guess")
    except ValueError:
        pass

    # -- Lambda ------------------------------------------------------------
    service = LambdaService(account_concurrency=4)
    function = Function("f", lambda event, ctx: None, memory_mb=512,
                        init_ms=500.0)
    service.register(function)
    for n in range(20):
        service.invoke("f", {}, now=n * 0.5)
    priced = bill_lambda(function)
    gb_seconds = [i for i in priced.items if i.dimension == "gb-seconds"][0]
    expected = function.stats["billed_ms"] / 1000.0 * 512 / 1024.0
    assert abs(gb_seconds.quantity - expected) < 1e-9, (
        f"GB-seconds is billed_ms/1000 x memory_mb/1024, so {expected:.4f}, not "
        f"{gb_seconds.quantity:.4f}. Getting the 1024 wrong is a 2x error that "
        "looks completely plausible on a dashboard.")
    arm = bill_lambda(function, arch="arm")
    assert arm.total < priced.total, "Graviton GB-seconds are ~20% cheaper"

    # -- SQS: idle polling is its own, FIXED, line -------------------------
    queue = Queue("q")
    for n in range(100):
        queue.send(f"m{n}", now=0.0)
    for message in queue.receive(max_messages=10, now=1.0):
        queue.delete(message.receipt_handle)
    sqs_bill = bill_sqs(queue, empty_receives=50_000)
    idle = [i for i in sqs_bill.items if i.dimension == "idle-poll-requests"]
    assert idle and idle[0].quantity == 50_000, (
        "empty receives belong on their own line named 'idle-poll-requests'. "
        "Fold them into 'requests' and they scale with traffic, which is "
        "backwards: idle polling scales with wall-clock time and the number of "
        "pollers, so a queue that goes QUIET gets more expensive per message.")
    scaled = sqs_bill.scaled(100.0)
    scaled_idle = [i for i in scaled.items
                   if i.dimension == "idle-poll-requests"][0]
    assert scaled_idle.quantity == 50_000, \
        "and because it is fixed, 100x the traffic must not change it"

    # -- SNS: the protocol is the price ------------------------------------
    topic = Topic("t")
    sink = Queue("sink")
    topic.subscribe("sqs", sink, "free")
    topic.subscribe("http", lambda *a: None, "paid",
                    filter_policy={"level": ["high"]})
    for n in range(100):
        topic.publish("m", {"level": "high" if n % 10 == 0 else "low"}, now=0.0)
    sns_bill = bill_sns(topic)
    dimensions = {i.dimension: i for i in sns_bill.items}
    assert "deliveries-sqs" in dimensions and "deliveries-http" in dimensions, (
        "deliveries must be split BY PROTOCOL. SQS is free, HTTP is $0.60/M "
        "and SMS is $6,450/M — one line for 'deliveries' averages across a "
        "five-order-of-magnitude spread and tells you nothing.")
    assert dimensions["deliveries-sqs"].cost == 0.0
    assert dimensions["deliveries-http"].quantity == 10, \
        "the filter policy must have stopped 90 of them at the topic"
    assert dimensions["filtered-deliveries"].cost == 0.0

    # -- KMS ---------------------------------------------------------------
    kms = KMS()
    kms.create_key("k")
    cipher = EnvelopeCipher(kms, "k")
    for _ in range(1000):
        cipher.encrypt(b"x", {"t": "a"})
    kms_bill = bill_kms(kms)
    keys = [i for i in kms_bill.items if i.dimension == "key-months"][0]
    requests = [i for i in kms_bill.items if i.dimension == "requests"][0]
    assert keys.cost == 1.0 and requests.quantity == 1000
    assert keys.cost > requests.cost, (
        "at 1,000 records the KEY costs more than every API call put together. "
        "Which of these two lines is bigger is the diagnosis: key-months means "
        "key sprawl, requests means a per-record call pattern.")

    # -- Network: cross-AZ is billed on BOTH sides -------------------------
    net = bill_network(cross_az_gb=1000.0, internet_in_gb=5000.0)
    cross = [i for i in net.items if i.dimension == "cross-az-gb"][0]
    assert cross.quantity == 2000.0, (
        f"1,000 GB of cross-AZ traffic bills {cross.quantity} GB, not 2,000. "
        "It is charged on the sending side AND the receiving side — $0.02/GB "
        "round trip, which is the number people forget when they spread a "
        "chatty service across AZs.")
    assert [i for i in net.items if i.dimension == "internet-in-gb"][0].cost == 0.0, \
        "ingress is free"


# ---------------------------------------------------------------------------
# Optimize
# ---------------------------------------------------------------------------

def check_crossovers() -> None:
    from optimize import (best_memory, best_storage_class, dynamodb_crossover,
                          lambda_duration_ms, lambda_memory_sweep,
                          nat_vs_gateway_endpoint, nat_vs_interface_endpoint,
                          storage_class_cost)

    write = dynamodb_crossover("write")
    read = dynamodb_crossover("read")
    assert abs(write - 0.14444) < 0.001, (
        f"got {write:.4f}. One WCU costs $0.00065/hour and delivers 3,600 write "
        "units in that hour; those units on demand cost 3,600 x $1.25/1M. "
        "Setting them equal gives 14.44%.")
    assert abs(write - read) < 1e-9, (
        "reads and writes must give the SAME crossover — AWS priced both modes "
        "with the same ratio, which is why there is only one number to know")

    assert abs(lambda_duration_ms(1769, 900.0, 0.0) - 900.0) < 1e-6, \
        "1,769 MB is one vCPU, so CPU work takes exactly its nominal time"
    assert abs(lambda_duration_ms(884.5, 900.0, 0.0) - 1800.0) < 1e-6, \
        "half the memory is half the CPU, so twice the duration"
    assert abs(lambda_duration_ms(10240, 100.0, 400.0) - 417.28) < 0.1, \
        "the io_wait term must NOT shrink with memory — that is the whole point"

    cpu_bound = lambda_memory_sweep(900.0, 0.0)
    costs = [row["cost"] for row in cpu_bound]
    assert max(costs) / min(costs) < 1.02, (
        f"CPU-bound cost varied by {max(costs) / min(costs):.2f}x across the "
        "memory range. It should be nearly FLAT: twice the memory runs in half "
        "the time, so the GB-seconds cancel. This is why leaving a CPU-bound "
        "function at 128 MB buys a 12x slower function for no saving at all.")
    cheapest, fastest = best_memory(cpu_bound)
    assert fastest == 10240, "more memory is always faster for CPU-bound work"

    io_bound = lambda_memory_sweep(20.0, 400.0)
    cheapest, fastest = best_memory(io_bound)
    assert cheapest == 128 and fastest == 10240, (
        "for I/O-bound work the cheapest and fastest settings must be at "
        "OPPOSITE ends. The wait does not shrink, so every extra MB is billed "
        "against a duration you cannot reduce.")

    gateway = nat_vs_gateway_endpoint(10_000.0)
    assert gateway["through_endpoint"] == 0.0 and gateway["saving"] > 0, (
        "an S3/DynamoDB gateway endpoint is free at every volume, forever. "
        "There is no crossover, which is what makes it the best line in the "
        "file: a route-table entry that cannot change behaviour.")
    assert nat_vs_gateway_endpoint(100_000.0)["saving"] > \
        nat_vs_gateway_endpoint(1_000.0)["saving"]

    assert nat_vs_interface_endpoint(1_000.0, services=1)["saving"] > 0
    assert nat_vs_interface_endpoint(1_000.0, services=30)["saving"] < 0, (
        "interface endpoints are NOT free — $0.01/hour per AZ per service. "
        "Route thirty services privately across three AZs and you have bought "
        "ninety endpoints to replace three NAT gateways.")

    # 180 days is 5.92 months, so anything shorter bills identically.
    month = storage_class_cost(1.0, 1.0, 0.0, "deep_archive")
    five = storage_class_cost(1.0, 5.0, 0.0, "deep_archive")
    assert abs(month - five) < 1e-12, (
        "Deep Archive has a 180-day minimum, so 1 month and 5 months must cost "
        "exactly the same. A lifecycle rule that archives objects and deletes "
        "them a month later costs six times what the storage rate suggests, "
        "and the console shows the data as gone.")
    assert storage_class_cost(1.0, 12.0, 0.0, "deep_archive") > five, \
        "past the minimum it grows with time again"

    tiny = storage_class_cost(1.0, 1.0, 0.0, "standard_ia", object_kb=4.0)
    big = storage_class_cost(1.0, 1.0, 0.0, "standard_ia", object_kb=1024.0)
    assert abs(tiny / big - 32.0) < 0.01, (
        f"1 GB of 4 KB objects in Standard-IA costs {tiny / big:.1f}x what the "
        "same GB in 1 MB objects costs. 128/4 = 32.")

    hot, _ = best_storage_class(1.0, 12.0, 10.0)
    assert hot == "standard", (
        "read ten times a month, Standard wins — the retrieval charge on every "
        "colder class overwhelms the storage saving. Nothing in this decision "
        "is about how 'cold' the data feels.")


def check_measured_optimisations() -> None:
    from pricing import Bill
    from optimize import (allocate, measure_data_key_reuse,
                          measure_query_vs_scan, measure_queue_strategies,
                          rank_savings)

    keys = measure_data_key_reuse(1000, 100)
    assert keys["calls_per_record"] == 1000, \
        "EnvelopeCipher.encrypt calls GenerateDataKey once per record"
    assert keys["calls_batched"] == 10, \
        "one data key per 100 records is 10 calls for 1,000 records"
    assert keys["cost_batched"] <= keys["cost_per_record"]
    assert keys["cost_batched"] >= 1.0, (
        "the floor is the key itself at $1.00/month. Below a few hundred "
        "thousand records there is no money in the request line to save, and "
        "reusing data keys widens the blast radius for nothing.")

    scan = measure_query_vs_scan(tenants=40, per_tenant=10)
    assert scan["query_items"] == 10, "a query touches only its own partition"
    assert scan["scan_items"] == 400, (
        f"the scan touched {scan['scan_items']} items. A scan reads EVERY item "
        "and filters afterwards, so it must touch all 400 to return 10.")
    assert abs(scan["ratio"] - 40.0) < 1e-9, \
        "the ratio IS table size / result size, and it grows with the table"

    rows = measure_queue_strategies(200)
    short, long_poll, batched = rows
    assert short["idle_requests"] > long_poll["idle_requests"] * 100, \
        "long polling must collapse the idle column, not shave it"
    assert batched["work_requests"] < long_poll["work_requests"], \
        "batching divides the receive and delete calls"
    assert all(row["drained"] == 200 for row in rows), \
        "all three strategies must do the SAME work — otherwise it is not a "\
        "comparison"

    bill = Bill("b")
    bill.add("lambda", "requests", 10e6, "request", 2e-7)      # $2
    bill.add("sqs", "requests", 100e6, "request", 4e-7)        # $40
    bill.add("network", "nat-gateway-hours", 730.0, "hour", 0.045)
    ranked = rank_savings(bill, {"halve sqs": ("sqs/requests", 0.5),
                                 "halve lambda": ("lambda/requests", 0.5)})
    assert [row["change"] for row in ranked] == ["halve sqs", "halve lambda"], \
        "rank by dollars saved, descending"
    assert abs(ranked[0]["saving"] - 20.0) < 1e-9, (
        f"halving the SQS line saves $20, not ${ranked[0]['saving']:.2f}. If "
        "you got $21 you summed every line whose dimension is 'requests' — but "
        "Lambda, SQS and KMS all have a line by that name, and adding them "
        "because they share a word makes the model disagree with the invoice.")
    try:
        rank_savings(bill, {"typo": ("sqs/reqests", 0.5)})
        raise AssertionError(
            "a misspelled line silently 'saved' $0. Raise instead — a change "
            "that appears to save nothing because of a typo is the worst "
            "possible output from a ranking tool.")
    except KeyError:
        pass

    split = allocate(bill, {"a": 1.0, "b": 3.0})
    assert abs(sum(split.values()) - bill.total) < 1e-9, \
        "an allocation must add back up to the bill"
    assert abs(split["b"] / split["a"] - 3.0) < 1e-9


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("iam.py", "explicit deny > allow > implicit deny", check_iam_basics),
    ("iam.py", "conditions and permissions boundaries", check_iam_conditions),
    ("iam.py", "STS assume-role: both directions", check_sts),
    ("s3.py", "objects, ETags and multipart", check_s3_objects),
    ("s3.py", "prefix listing and delete markers", check_s3_listing_and_versioning),
    ("sqs.py", "visibility timeout and redelivery", check_sqs_visibility),
    ("sqs.py", "dead letters, FIFO and dedup", check_sqs_dlq_and_fifo),
    ("dynamodb.py", "composite keys, query, conditions", check_dynamo_keys),
    ("dynamodb.py", "capacity, hot partitions, scan cost", check_dynamo_capacity),
    ("lambda_svc.py", "cold starts and warm state", check_lambda_lifecycle),
    ("lambda_svc.py", "concurrency, reservations, async retry", check_lambda_concurrency),
    ("sns.py", "fanout and filter policies", check_sns_fanout_and_filters),
    ("sns.py", "EventBridge pattern matching", check_eventbridge),
    ("kms.py", "envelope encryption", check_kms_envelope),
    ("kms.py", "encryption context and rotation", check_kms_context_and_rotation),
    ("vpc.py", "CIDR, subnets and longest-prefix routing", check_vpc_cidr),
    ("vpc.py", "stateful SG vs stateless NACL", check_stateful_vs_stateless),
    ("capstone.py", "the pipeline, and its failures", check_capstone),
    ("pricing.py", "rounding rules and graduated tiers", check_pricing_arithmetic),
    ("pricing.py", "line items, fixed vs variable, free tier", check_bill),
    ("billing.py", "S3: versioning, and the two minimums", check_billing_s3),
    ("billing.py", "metering every other service", check_billing_services),
    ("optimize.py", "the crossovers, derived not recalled", check_crossovers),
    ("optimize.py", "measured savings, and reading a bill", check_measured_optimisations),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

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
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}AWS From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None

    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue

        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<20} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<20} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<20} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you built the core of AWS.{RESET}")
        print(f"  {GREY}Now run each file's own demo to see the measurements,{RESET}")
        print(f"  {GREY}then compare your approach with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The TODO comments in that file walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
