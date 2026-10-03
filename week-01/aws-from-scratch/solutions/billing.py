"""
Billing — metering the services you actually built. Complete Solution.

Every service in this directory already counts what it does: `s3.stats`,
`table.stats`, `function.stats`, `queue.stats`, `topic.stats`, `key.stats`.
That was not an accident. A meter is a first-class part of a cloud service, and
this file is the proof: nothing below reaches inside a service to recompute
anything. It reads the counters, converts them into billable dimensions, and
prices them.

DESIGN DECISION — meter inside each service, or from outside?
  Inside is how the services themselves are written (each one owns its stats
  dict). Pricing inside would be worse: it welds a price sheet into a data
  path, and it means changing a price means editing eight files.
  CHOSEN: services count UNITS, billing converts units to MONEY. This is the
  real split too — the metering pipeline and the pricing engine are different
  systems at AWS, which is why your usage shows up in CloudWatch instantly and
  on the bill hours later.

DESIGN DECISION — what to do when a counter does not exist?
  The toy SQS counts MESSAGES; SQS bills API REQUESTS, and one request carries
  up to ten messages. The toy has no way to know how you batched.
  CHOSEN: take the batching factor as an explicit argument with a pessimistic
  default of 1, and say so in the note on the line item. A cost model that
  quietly assumes the favourable case is worse than no cost model — you will
  believe it.
  REJECTED: adding a request counter to sqs.py. Tempting, and it would be more
  accurate, but the honest lesson is that YOUR OWN metering decides what
  questions you can answer later, and discovering that after the fact is the
  normal experience.

The single most important habit this file is trying to build: read a bill by
LINE, never by total. The total tells you whether to panic. Only the lines tell
you what to do.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from pricing import (Bill, FreeTier, HOURS_PER_MONTH, LineItem, PRICES,
                     billable_units, money, per_unit, price, prorate,
                     tiered_cost)


def utilisation(used: float, available: float) -> str:
    """Percentages lie at both ends. 0.00% and 100.00% are both common answers
    and only one of them is informative, so print the small ones as a ratio."""
    if available <= 0:
        return "no capacity"
    fraction = used / available
    if fraction >= 0.001:
        return f"{100 * fraction:.1f}%"
    return f"1 in {available / used:,.0f}" if used else "0 — nothing ran"


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------

def stored_bytes(s3: Any) -> Dict[str, int]:
    """Split what is stored into what you can SEE and what you are PAYING for.

    A plain DELETE in a versioned bucket does not delete. It pushes a delete
    marker, and every byte underneath stays on the invoice forever. `live` is
    what a LIST shows you; `noncurrent` is the part that is invisible in the
    console and fully billable. When someone asks why the bucket costs more
    than the data in it, this function is the answer.
    """
    live = noncurrent = markers = 0
    for bucket in s3.buckets.values():
        for history in bucket.objects.values():
            if not history:
                continue
            current = history[-1]
            for version in history:
                if version.is_delete_marker:
                    markers += 1
                elif version is current:
                    live += version.size
                else:
                    noncurrent += version.size
    return {"live": live, "noncurrent": noncurrent,
            "delete_markers": markers, "total": live + noncurrent}


def bill_s3(s3: Any, storage_class: str = "standard", days: float = 30.0,
            retrieved_gb: float = 0.0, bill: Optional[Bill] = None) -> Bill:
    """Price an S3 service object from its own counters.

    Four dimensions, and which one dominates depends entirely on your object
    size. A million 1 KB objects and one 1 GB object hold the same bytes; the
    million costs 1000x more in requests and, in any IA class, 128x more in
    storage because of the minimum billable object size.
    """
    bill = bill or Bill("s3", days * 24)
    class_price, min_days, min_object_kb, retrieval_per_gb = \
        price("s3", "storage_gb_month")[storage_class]

    sizes = stored_bytes(s3)
    objects = sum(len(h) for b in s3.buckets.values() for h in b.objects.values())

    # Minimum billable object size: a 4 KB object in Standard-IA is billed as
    # 128 KB. Applied per object, so it hits small-object workloads hardest.
    padded_gb = 0.0
    for bucket in s3.buckets.values():
        for history in bucket.objects.values():
            for version in history:
                if version.is_delete_marker:
                    continue
                kb = max(version.size / 1024.0, min_object_kb)
                padded_gb += kb / (1024.0 * 1024.0)

    # Minimum billable DURATION: delete an object from Deep Archive after a
    # day and you still pay for 180 days of it.
    billed_days = max(days, min_days)
    month_fraction = billed_days / 30.4167

    if storage_class == "standard":
        bill.add_tiered("s3", "storage-gb-months", padded_gb * month_fraction,
                        "GB-month", price("s3", "storage_tiers"),
                        f"{sizes['live'] / 1e6:.2f} MB live, "
                        f"{sizes['noncurrent'] / 1e6:.2f} MB non-current")
    else:
        bill.add("s3", "storage-gb-months", padded_gb * month_fraction,
                 "GB-month", class_price,
                 f"{storage_class}: {min_object_kb} KB minimum object, "
                 f"{min_days} day minimum")

    bill.add("s3", "puts", s3.stats["puts"], "request",
             per_unit(price("s3", "put_per_1000")[storage_class], 1000))
    bill.add("s3", "gets", s3.stats["gets"], "request",
             per_unit(price("s3", "get_per_1000")[storage_class], 1000))
    bill.add("s3", "lists", s3.stats["lists"], "request",
             per_unit(price("s3", "list_per_1000"), 1000),
             "LIST is priced as a PUT-class request, 12x a GET")
    bill.add("s3", "deletes", s3.stats["deletes"], "request", 0.0,
             f"DELETE is free; the {sizes['delete_markers']} delete markers "
             f"it left are not")
    if retrieved_gb:
        bill.add("s3", "retrieval-gb", retrieved_gb, "GB", retrieval_per_gb,
                 f"{storage_class} charges to READ your own data")
    bill.items[-1] = bill.items[-1]._replace(
        note=bill.items[-1].note + f" [{objects} versions stored]")
    return bill


# ---------------------------------------------------------------------------
# DynamoDB
# ---------------------------------------------------------------------------

def bill_dynamodb(table: Any, mode: str = "provisioned",
                  hours: float = HOURS_PER_MONTH, avg_item_kb: float = 1.0,
                  consistent_reads: bool = False, storage_gb: float = 0.0,
                  bill: Optional[Bill] = None) -> Bill:
    """Price a table in either billing mode. Same table, same traffic.

    PROVISIONED bills capacity you RESERVED, whether or not you used it. Idle
    capacity costs exactly as much as busy capacity.
    ON-DEMAND bills requests you MADE, at roughly 7x the per-request rate.

    So the question is never "which is cheaper" — it is "what is my
    utilisation", and there is an exact crossover. optimize.py computes it.
    """
    bill = bill or Bill(f"dynamodb/{table.name} [{mode}]", hours)
    write_capacity = table.per_partition_write * table.num_partitions
    read_capacity = table.per_partition_read * table.num_partitions

    write_units = table.stats["writes"] * billable_units(avg_item_kb, 1.0)
    read_units = table.stats["scanned_items"] * billable_units(
        avg_item_kb, 4.0) * (1.0 if consistent_reads else 0.5)

    if mode == "provisioned":
        # Utilisation is the whole story, so spell it out: capacity is measured
        # per SECOND, so an hour of reserved capacity is 3,600 units you either
        # used or threw away.
        write_available = write_capacity * hours * 3600
        read_available = read_capacity * hours * 3600
        bill.add("dynamodb", "provisioned-wcu-hours", write_capacity * hours,
                 "WCU-hour", price("dynamodb", "provisioned_wcu_hour"),
                 f"{write_units:,.0f} of {write_available:,.0f} reserved write "
                 f"units used ({utilisation(write_units, write_available)})")
        bill.add("dynamodb", "provisioned-rcu-hours", read_capacity * hours,
                 "RCU-hour", price("dynamodb", "provisioned_rcu_hour"),
                 f"{read_units:,.0f} of {read_available:,.0f} reserved read "
                 f"units used ({utilisation(read_units, read_available)})")
    elif mode == "on_demand":
        bill.add("dynamodb", "on-demand-writes", write_units, "WRU",
                 per_unit(price("dynamodb", "on_demand_write_per_million"), 1e6),
                 f"{table.stats['writes']:,} writes x "
                 f"{billable_units(avg_item_kb, 1.0):.0f} WCU each")
        bill.add("dynamodb", "on-demand-reads", read_units, "RRU",
                 per_unit(price("dynamodb", "on_demand_read_per_million"), 1e6),
                 f"{table.stats['scanned_items']:,} items TOUCHED "
                 f"(not {table.stats['returned_items']:,} returned)")
    else:
        raise ValueError(f"mode must be 'provisioned' or 'on_demand', got {mode!r}")

    if storage_gb:
        billable = max(0.0, storage_gb - price("dynamodb", "free_storage_gb"))
        bill.add("dynamodb", "storage-gb-months", billable, "GB-month",
                 price("dynamodb", "storage_gb_month"),
                 f"first {price('dynamodb', 'free_storage_gb'):.0f} GB free")

    for name in getattr(table, "indexes", {}):
        # A GSI is a second table. It has its own capacity and its own bill,
        # and every write to the base table is a write to it as well.
        bill.add("dynamodb", "gsi-write-amplification", write_units, "WRU",
                 per_unit(price("dynamodb", "on_demand_write_per_million"), 1e6),
                 f"GSI {name!r} — a projected write you did not issue")
    return bill


# ---------------------------------------------------------------------------
# Lambda
# ---------------------------------------------------------------------------

def bill_lambda(function: Any, arch: str = "x86",
                bill: Optional[Bill] = None) -> Bill:
    """Price a function from its billed_ms and its memory setting.

    Two dimensions: a flat per-invocation charge, and GB-seconds. The GB-second
    is the one that matters, and it is the product of a number you chose
    (memory) and a number you mostly did not (duration) — which is why memory
    sizing is a real optimisation problem rather than a slider.

    Three things people forget, all priced here:
      * A COLD START's initialisation time is billed. Fixing cold starts is a
        latency win AND a cost win.
      * A TIMEOUT is billed for the full timeout, then retried, and billed
        again. A function that times out costs more than one that succeeds.
      * A THROTTLE is free. Nothing ran. It is the cheapest possible failure
        and the most expensive possible outage.
    """
    bill = bill or Bill(f"lambda/{function.name}")
    stats = function.stats
    gb = function.memory_mb / 1024.0
    gb_seconds = stats["billed_ms"] / 1000.0 * gb

    bill.add("lambda", "requests", stats["invocations"], "request",
             per_unit(price("lambda", "request_per_million"), 1e6),
             f"{stats['cold_starts']} cold starts, "
             f"{stats['async_retries']} retries — all billed as requests")
    bill.add("lambda", "gb-seconds", gb_seconds, "GB-s",
             price("lambda", f"gb_second_{arch}"),
             f"{function.memory_mb} MB x {stats['billed_ms']:,.0f} ms billed")
    bill.add("lambda", "throttles", stats["throttles"], "throttle", 0.0,
             "throttles are FREE — nothing ran, which is the problem")
    return bill


# ---------------------------------------------------------------------------
# SQS
# ---------------------------------------------------------------------------

def bill_sqs(queue: Any, send_batch: int = 1, receive_batch: int = 1,
             empty_receives: int = 0, fifo: bool = False,
             bill: Optional[Bill] = None) -> Bill:
    """Price a queue. Note the argument list — it is the lesson.

    SQS bills API REQUESTS. The toy counts MESSAGES. Those differ by up to 10x
    (a batch) and by an unbounded amount in the other direction (an empty
    receive that returned nothing is still a request you pay for).

    Short polling at 20 polls per second on an idle queue costs
    ~52M requests a month for zero work done. Long polling collapses that to
    ~3 requests a minute. It is one parameter, and it is the difference between
    $21/month and $0.
    """
    bill = bill or Bill(f"sqs/{queue.name}")
    stats = queue.stats
    rate = price("sqs", "fifo_per_million" if fifo else "standard_per_million")

    sends = math.ceil(stats["sent"] / max(1, send_batch))
    receives = math.ceil(stats["received"] / max(1, receive_batch))
    deletes = math.ceil(stats["deleted"] / max(1, receive_batch))

    bill.add("sqs", "requests", sends + receives + deletes, "request",
             per_unit(rate, 1e6),
             f"{sends} send + {receives} receive + {deletes} delete; "
             f"batch {send_batch}/{receive_batch}")
    if empty_receives:
        # Kept as its OWN line, and marked fixed, because idle polling scales
        # with wall-clock time and the number of pollers — not with traffic. A
        # queue that goes quiet does not get cheaper to poll; it gets more
        # expensive per message, which is exactly backwards from every other
        # line on the bill.
        bill.add("sqs", "idle-poll-requests", empty_receives, "request",
                 per_unit(rate, 1e6),
                 "ReceiveMessage calls that returned nothing — billed in full")
    if stats["redelivered"]:
        bill.add("sqs", "redelivery-requests", stats["redelivered"], "request",
                 per_unit(rate, 1e6),
                 "a message redelivered after a visibility timeout is a NEW "
                 "billable receive, and it is billed again on every retry")
    return bill


# ---------------------------------------------------------------------------
# SNS
# ---------------------------------------------------------------------------

def bill_sns(topic: Any, bill: Optional[Bill] = None) -> Bill:
    """Price a topic. Deliveries are priced BY PROTOCOL, over five orders of
    magnitude: SQS and Lambda are free, HTTP is $0.60/M, email $20/M, SMS
    $6,450/M. The same fanout costs $0 or $6,450 depending on one string.

    And the filter policy: every filtered-out delivery is a delivery you did
    not pay for AND a downstream invocation you did not pay for. Filtering at
    the topic is one of the very few optimisations that is free to apply and
    saves money on two services at once.
    """
    bill = bill or Bill(f"sns/{topic.name}")
    bill.add("sns", "publishes", topic.stats["published"], "publish",
             per_unit(price("sns", "publish_per_million"), 1e6))

    by_protocol: Dict[str, int] = {}
    for subscription in topic.subscriptions:
        by_protocol[subscription.protocol] = (
            by_protocol.get(subscription.protocol, 0) + subscription.delivered)

    prices = price("sns", "delivery_per_million")
    for protocol, count in sorted(by_protocol.items()):
        rate = prices.get(protocol, 0.0)
        bill.add("sns", f"deliveries-{protocol}", count, "delivery",
                 per_unit(rate, 1e6),
                 "free" if rate == 0 else f"${rate}/million on {protocol}")

    filtered = topic.stats["filtered"]
    if filtered:
        bill.add("sns", "filtered-deliveries", filtered, "delivery", 0.0,
                 f"{filtered} deliveries a filter policy prevented — free "
                 f"here, and free downstream too")
    return bill


# ---------------------------------------------------------------------------
# KMS
# ---------------------------------------------------------------------------

def bill_kms(kms: Any, months: float = 1.0,
             bill: Optional[Bill] = None) -> Bill:
    """Price KMS. Two dimensions, and knowing which dominates tells you which
    problem you have.

      key-months dominate  -> KEY SPRAWL. One key per tenant sounds like
                              isolation; at 5,000 tenants it is $5,000/month
                              before a single API call. Encryption context on
                              a shared key gives you per-tenant separation for
                              $1.
      requests dominate    -> a CALL PATTERN problem. You are calling KMS per
                              record instead of per batch. This is exactly what
                              envelope encryption exists to fix, and
                              optimize.py measures the difference.
    """
    bill = bill or Bill("kms", months * HOURS_PER_MONTH)
    bill.add("kms", "key-months", len(kms.keys) * months, "key-month",
             price("kms", "key_month"),
             f"{len(kms.keys)} customer-managed keys")

    requests = sum(k.stats["encrypts"] + k.stats["decrypts"] + k.stats["data_keys"]
                   for k in kms.keys.values())
    bill.add("kms", "requests", requests, "request",
             per_unit(price("kms", "request_per_10000"), 10_000),
             "GenerateDataKey, Encrypt and Decrypt each count as one")
    return bill


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def bill_network(internet_out_gb: float = 0.0, internet_in_gb: float = 0.0,
                 cross_az_gb: float = 0.0, cross_region_gb: float = 0.0,
                 nat_gateways: int = 0, nat_gb: float = 0.0,
                 interface_endpoints: int = 0, interface_endpoint_gb: float = 0.0,
                 public_ipv4: int = 0, hours: float = HOURS_PER_MONTH,
                 bill: Optional[Bill] = None) -> Bill:
    """Price the network. There is no `stats` dict for this one, and that is
    the point: nothing in your code counts bytes on the wire, so this is the
    dimension you discover on the invoice.

    Memorise the asymmetries:
      IN from the internet          free
      OUT to the internet           $0.09/GB after the first 100 GB
      cross-AZ                      $0.01/GB EACH WAY — $0.02 round trip
      same-AZ, private IP           free
      through a NAT gateway         $0.045/GB ON TOP of the above
      through an S3 gateway endpoint  free, and it replaces the NAT hop
    """
    bill = bill or Bill("network", hours)
    if internet_in_gb:
        bill.add("network", "internet-in-gb", internet_in_gb, "GB",
                 price("network", "internet_in_per_gb"),
                 "ingress is free — which is why exfiltration is cheap and "
                 "backfilling is not")
    if internet_out_gb:
        bill.add_tiered("network", "internet-out-gb", internet_out_gb, "GB",
                        price("network", "internet_out_tiers"),
                        "graduated; first 100 GB/month waived by the free tier")
    if cross_az_gb:
        bill.add("network", "cross-az-gb", cross_az_gb * 2, "GB",
                 price("network", "cross_az_per_gb"),
                 f"{cross_az_gb:,.1f} GB of traffic, billed on BOTH sides")
    if cross_region_gb:
        bill.add("network", "cross-region-gb", cross_region_gb, "GB",
                 price("network", "cross_region_per_gb"))
    if nat_gateways:
        bill.add("network", "nat-gateway-hours", nat_gateways * hours, "hour",
                 price("network", "nat_gateway_hour"),
                 f"{nat_gateways} gateway(s) — one per AZ for high availability")
        bill.add("network", "nat-processing-gb", nat_gb, "GB",
                 price("network", "nat_gateway_per_gb"),
                 "charged even for traffic that never leaves AWS")
    if interface_endpoints:
        bill.add("network", "endpoint-hours", interface_endpoints * hours, "hour",
                 price("network", "interface_endpoint_hour"),
                 "per endpoint per AZ")
        bill.add("network", "endpoint-gb", interface_endpoint_gb, "GB",
                 price("network", "interface_endpoint_per_gb"))
    if public_ipv4:
        bill.add("network", "public-ipv4-hours", public_ipv4 * hours, "hour",
                 price("network", "public_ipv4_hour"),
                 "every attached public IPv4 address, since Feb 2024 — "
                 "including the ones on idle instances")
    return bill


# ---------------------------------------------------------------------------
# CloudWatch
# ---------------------------------------------------------------------------

def bill_cloudwatch(log_gb: float = 0.0, retained_gb: float = 0.0,
                    insights_scanned_gb: float = 0.0, custom_metrics: int = 0,
                    bill: Optional[Bill] = None) -> Bill:
    """Observability is not free, and on a serverless bill it is routinely the
    third line down. $0.50/GB to INGEST is the number to remember: a debug log
    line you left on in a hot path costs more than the compute that emitted it.
    """
    bill = bill or Bill("cloudwatch")
    if log_gb:
        bill.add("cloudwatch", "logs-ingest-gb", log_gb, "GB",
                 price("cloudwatch", "logs_ingest_per_gb"),
                 "ingest is 16x storage — the write is what costs, not the keep")
    if retained_gb:
        bill.add("cloudwatch", "logs-storage-gb-months", retained_gb, "GB-month",
                 price("cloudwatch", "logs_storage_gb_month"))
    if insights_scanned_gb:
        bill.add("cloudwatch", "insights-scanned-gb", insights_scanned_gb, "GB",
                 price("cloudwatch", "logs_insights_scan_per_gb"),
                 "you pay per QUERY, over the whole scanned range")
    if custom_metrics:
        bill.add("cloudwatch", "custom-metrics", custom_metrics, "metric-month",
                 price("cloudwatch", "custom_metric_month"),
                 "a metric per customer is a $0.30/month/customer decision")
    return bill


# ---------------------------------------------------------------------------
# The whole account
# ---------------------------------------------------------------------------

def bill_account(cloud: Any, hours: float = HOURS_PER_MONTH, **kwargs: Any) -> Bill:
    """Walk a capstone Cloud and price everything in it.

    This is Cost Explorer in twenty lines: enumerate resources, meter each one,
    concatenate the line items, group by whatever question you are asking.
    """
    bill = Bill("account", hours)
    bill_s3(cloud.s3, days=hours / 24.0, bill=bill)
    for table in cloud.tables.values():
        bill_dynamodb(table, mode=kwargs.get("dynamodb_mode", "on_demand"),
                      hours=hours, avg_item_kb=kwargs.get("avg_item_kb", 1.0),
                      bill=bill)
    for function in cloud.lambda_service.functions.values():
        bill_lambda(function, bill=bill)
    for queue in cloud.queues.values():
        bill_sqs(queue, send_batch=kwargs.get("send_batch", 1),
                 receive_batch=kwargs.get("receive_batch", 1),
                 empty_receives=kwargs.get("empty_receives", 0), bill=bill)
    for topic in cloud.topics.values():
        bill_sns(topic, bill=bill)
    bill_kms(cloud.kms, months=hours / HOURS_PER_MONTH, bill=bill)
    if kwargs.get("network"):
        bill_network(hours=hours, bill=bill, **kwargs["network"])
    if kwargs.get("cloudwatch"):
        bill_cloudwatch(bill=bill, **kwargs["cloudwatch"])
    return bill


def per_unit_of_work(bill: Bill, units: float, label: str = "request") -> str:
    """Unit economics. The only cost number that survives a growth plan.

    "$240/month" is meaningless without the denominator. "$0.000012 per upload"
    tells you the gross margin on a feature, tells you what a free tier costs
    you, and multiplies correctly when the traffic 10x's.
    """
    if units <= 0:
        return "no units of work"
    lines = [f"  {bill.total / units * 1e6:,.2f} USD per million {label}s "
             f"({units:,.0f} {label}s in this period)"]
    for item in bill.by_dimension()[:5]:
        lines.append(f"    {item.service}/{item.dimension:<26} "
                     f"{item.cost / units * 1e6:>12,.3f} per million")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    from dynamodb import Table
    from kms import KMS, EnvelopeCipher
    from lambda_svc import Function, LambdaService
    from s3 import S3
    from sns import Topic
    from sqs import Queue

    print("=" * 74)
    print("BILLING — the same services, now with a meter on them")
    print("=" * 74)

    # -- S3: the versioning trap, measured ---------------------------------
    print("\n1. S3 — 'I deleted everything and the bill did not move'")
    print("-" * 74)
    s3 = S3()
    s3.create_bucket("archive", versioning=True)
    payload = b"x" * 100_000
    for n in range(200):
        s3.put_object("archive", f"reports/{n:04d}.bin", payload)
    before = stored_bytes(s3)
    for n in range(200):
        s3.delete_object("archive", f"reports/{n:04d}.bin")
    after = stored_bytes(s3)
    listing = s3.list_objects("archive")

    print(f"  after 200 puts:     live={before['live'] / 1e6:.1f} MB  "
          f"noncurrent={before['noncurrent'] / 1e6:.1f} MB")
    print(f"  after 200 deletes:  live={after['live'] / 1e6:.1f} MB  "
          f"noncurrent={after['noncurrent'] / 1e6:.1f} MB")
    print(f"  LIST now returns {len(listing['keys'])} keys. The console is empty.")
    print(f"  Billable bytes went from {before['total'] / 1e6:.1f} MB to "
          f"{after['total'] / 1e6:.1f} MB — it did not move.")
    print(f"  Plus {after['delete_markers']} delete markers, each its own"
          f" billable version.")

    s3_bill = bill_s3(s3, days=30)
    print()
    print(s3_bill.format())

    print("\n  Storage classes are not a slider. Two buckets holding the SAME")
    print("  8 MB, one as 2,000 x 4 KB objects and one as 8 x 1 MB objects:")
    small, large = S3(), S3()
    small.create_bucket("small")
    large.create_bucket("large")
    for n in range(2000):
        small.put_object("small", f"k{n:05d}", b"x" * 4096)
    for n in range(8):
        large.put_object("large", f"k{n}", b"x" * 1_048_576)
    stored_gb = 8 * 1_048_576 / 1e9

    print(f"    {'class':<16}{'2000 x 4 KB':>14}{'$/GB-mo':>10}"
          f"{'8 x 1 MB':>14}{'$/GB-mo':>10}")
    for klass in ("standard", "standard_ia", "glacier_ir", "deep_archive"):
        a = bill_s3(_zeroed(small), storage_class=klass, days=30.4167).total
        b = bill_s3(_zeroed(large), storage_class=klass, days=30.4167).total
        print(f"    {klass:<16}{money(a):>14}{a / stored_gb:>10.4f}"
              f"{money(b):>14}{b / stored_gb:>10.4f}")
    print("  Standard-IA's sticker price is $0.0125/GB — about HALF Standard.")
    print("  On 4 KB objects it bills at 32x that, because every object under")
    print("  128 KB is billed as 128 KB. Moving small objects to IA to save")
    print("  money makes them more expensive than Standard, by a lot.")

    print("\n  And the minimum storage DURATION, on deep_archive:")
    print(f"    {'kept for':>10}{'billed as':>12}{'cost':>14}")
    for days in (1, 7, 30, 90, 180, 365):
        cost = bill_s3(_zeroed(large), storage_class="deep_archive",
                       days=days).total
        print(f"    {days:>7} d {max(days, 180):>9} d {money(cost):>14}")
    print("  Below 180 days the cost is flat, because you are billed for 180")
    print("  no matter what. A lifecycle rule that moves objects to Deep")
    print("  Archive and deletes them a month later costs SIX TIMES what you")
    print("  budgeted, and the console shows the storage as gone.")

    # -- DynamoDB: the two modes -------------------------------------------
    print("\n2. DynamoDB — the same table, both billing modes")
    print("-" * 74)
    table = Table("events", partition_key="tenant", sort_key="id",
                  read_capacity=1000, write_capacity=200, num_partitions=4)
    for n in range(500):
        table.put_item({"tenant": f"t{n % 50}", "id": f"{n:05d}",
                        "body": "x" * 900}, now=n * 0.2)
    table.query("t0", now=100.0)
    table.scan(lambda i: i["tenant"] == "t0", now=101.0)

    print(f"  500 writes, 1 query, 1 scan. Items touched: "
          f"{table.stats['scanned_items']}, returned: "
          f"{table.stats['returned_items']}.")
    for mode in ("provisioned", "on_demand"):
        priced = bill_dynamodb(table, mode=mode, hours=HOURS_PER_MONTH,
                               avg_item_kb=1.0)
        print(f"\n{priced.format()}")
    capacity = table.per_partition_write * table.num_partitions
    headroom = capacity * 3600 * HOURS_PER_MONTH
    print(f"\n  Provisioned costs $189.80 whether you send 500 writes or "
          f"{headroom / 1e6:,.0f} million —")
    print("  the reserved capacity is the product, not the traffic. On-demand")
    print("  costs a tenth of a cent here. That is not a recommendation: it is")
    print("  ONE point on a curve, and optimize.py finds where it crosses.")

    # -- Lambda ------------------------------------------------------------
    print("\n3. Lambda — cold starts, timeouts and throttles, priced")
    print("-" * 74)
    service = LambdaService(account_concurrency=4)

    def handler(event, context):
        return {"ok": True}

    fast = Function("fast", handler, memory_mb=512, init_ms=800.0)
    service.register(fast)
    for n in range(50):
        service.invoke("fast", {"n": n}, now=n * 0.5)
    print(f"  50 invocations, {fast.stats['cold_starts']} cold, "
          f"{fast.stats['billed_ms']:,.0f} ms billed")
    print()
    print(bill_lambda(fast).format())

    cold_ms = fast.stats["cold_starts"] * fast.init_ms
    print(f"\n  Of that, {cold_ms:,.0f} ms is INITIALISATION — "
          f"{100 * cold_ms / fast.stats['billed_ms']:.0f}% of the compute bill")
    print("  spent importing modules. At this size it is noise; on a function")
    print("  with a 4-second init and bursty traffic it is most of the bill.")

    # -- SQS and SNS -------------------------------------------------------
    print("\n4. SQS and SNS — where the request count is not the message count")
    print("-" * 74)
    queue = Queue("work")
    topic = Topic("uploads")
    topic.subscribe("sqs", queue, "worker")
    topic.subscribe("http", lambda *a: None, "pagerduty",
                    filter_policy={"severity": ["critical"]})
    for n in range(1000):
        topic.publish(f"event-{n}", {"severity": "info" if n % 100 else "critical"},
                      now=0.0)
    for _ in range(100):
        for message in queue.receive(max_messages=10, now=1.0):
            queue.delete(message.receipt_handle)

    print(bill_sns(topic).format())
    print("\n  1,000 published, 1,000 delivered to SQS for free, 10 delivered")
    print("  to the HTTP endpoint. The other 990 were dropped by a filter")
    print("  policy AT THE TOPIC — not billed here, and not billed downstream")
    print("  either, because the subscriber was never invoked.")
    print("\n  The same 1,000 deliveries, priced by protocol:")
    print(f"    {'protocol':<12}{'$/million':>12}{'1,000 deliveries':>20}")
    for protocol, rate in sorted(price("sns", "delivery_per_million").items(),
                                 key=lambda kv: kv[1]):
        print(f"    {protocol:<12}{rate:>12,.2f}{money(1000 * per_unit(rate, 1e6)):>20}")
    print("  One string in a subscription, five orders of magnitude. An SMS")
    print("  fanout that someone wires up 'to test' is a real incident.")

    print("\n  The same 1,000 messages, under three polling strategies:")
    print(f"    {'strategy':<28}{'work':>10}{'idle polls':>12}{'total':>10}"
          f"{'/mo at 100x':>14}")
    for label, kwargs in (
            ("short poll, receive 1", dict(receive_batch=1, empty_receives=50_000)),
            ("long poll,  receive 1", dict(receive_batch=1, empty_receives=43)),
            ("long poll,  receive 10", dict(receive_batch=10, empty_receives=43))):
        priced = bill_sqs(queue, **kwargs)
        work = sum(i.quantity for i in priced.items if i.dimension == "requests")
        idle = sum(i.quantity for i in priced.items
                   if i.dimension == "idle-poll-requests")
        print(f"    {label:<28}{work:>10,.0f}{idle:>12,.0f}{work + idle:>10,.0f}"
              f"{money(priced.total * 100):>14}")
    print("  Identical work done. Short polling at 20 calls a second spends")
    print("  94% of its request budget on receives that returned nothing, and")
    print("  batching divides the remaining 6% by ten. Both are defaults you")
    print("  have to opt out of.")

    # -- KMS ---------------------------------------------------------------
    print("\n5. KMS — which number is big tells you which mistake you made")
    print("-" * 74)
    kms = KMS()
    cipher = EnvelopeCipher(kms, "app")
    kms.create_key("app")
    for n in range(2000):
        cipher.encrypt(b"record", {"tenant": "acme"})
    per_record = bill_kms(kms)
    print(per_record.format())
    print("  2,000 records, 2,000 GenerateDataKey calls. The key-month line")
    print("  dominates only because the volume is small; at 20 million records")
    print("  the request line is $60 and the key is a rounding error.")

    sprawl = KMS()
    for n in range(500):
        sprawl.create_key(f"tenant-{n}")
    print(f"\n  A key per tenant, 500 tenants, zero API calls: "
          f"{money(bill_kms(sprawl).total)}/month.")
    print("  Encryption context on ONE key gives the same cryptographic")
    print("  separation for $1. Key sprawl is an org-chart decision that")
    print("  arrives as a line item.")

    # -- Network -----------------------------------------------------------
    print("\n6. Network — the dimension nothing in your code counts")
    print("-" * 74)
    net = bill_network(internet_out_gb=500.0, internet_in_gb=2_000.0,
                       cross_az_gb=1_000.0, nat_gateways=3, nat_gb=1_000.0,
                       public_ipv4=6)
    print(net.format())
    print("\n  2 TB in: free. 500 GB out: $45. 1 TB sideways between AZs:")
    print("  $20, because it is charged on both ends. And $98.55 for three NAT")
    print("  gateways to EXIST, before a byte moves. Nothing in the application")
    print("  emitted a metric for any of it.")

    print("\n" + "=" * 74)
    print("Next: optimize.py turns each of these into a decision with a number.")
    print("=" * 74)


def _zeroed(s3: Any) -> Any:
    """A copy with the request counters zeroed, so a storage-class comparison
    compares STORAGE and not the requests that happened to build the fixture."""
    import copy
    clone = copy.deepcopy(s3)
    clone.stats = {key: 0 for key in clone.stats}
    return clone


if __name__ == "__main__":
    _demo()
