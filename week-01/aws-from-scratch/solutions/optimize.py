"""
Optimize — turning each price into a decision with a number. Complete Solution.

billing.py answers "what did this cost". This file answers the only question
that is actually actionable: "what should I change, and by how much does it
help".

Every section here follows the same shape, and it is the shape worth copying:

    1. Name the decision as a CROSSOVER, not a rule.
       "On-demand is cheaper for spiky workloads" is folklore. "On-demand is
       cheaper below 14.4% utilisation" is a decision you can make with a
       CloudWatch graph.
    2. Compute the crossover from the price sheet, never from memory. Prices
       move; the derivation does not.
    3. Then check the crossover against something MEASURED, so a wrong model
       shows up as a disagreement rather than as confidence.

DESIGN DECISION — a list of best practices, or a set of crossover functions?
  A checklist is easier to write and it is what most cost guides are.
  CHOSEN: functions that return the number where the advice FLIPS. Every
  genuine cost rule has a regime where it is wrong, and the regime boundary is
  the only part of the rule that is worth memorising. "Use Glacier for cold
  data" is true until you read the data, at which point it is 6x worse.
  REJECTED: a scoring/recommendation engine. It would hide the arithmetic,
  which is the entire thing being taught.

WHAT THIS IS NOT
  Not a substitute for AWS Cost Explorer, Compute Optimizer, or your own
  measurements. The models here are simple enough to be checked by hand, which
  is why they are useful for learning and not for procurement.
"""

import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from billing import (bill_dynamodb, bill_kms, bill_lambda, bill_network,
                     bill_s3, bill_sns, bill_sqs, stored_bytes)
from pricing import (Bill, HOURS_PER_MONTH, billable_units, money, per_unit,
                     price, tiered_cost)


# ---------------------------------------------------------------------------
# 1. DynamoDB: provisioned or on-demand
# ---------------------------------------------------------------------------

def dynamodb_crossover(kind: str = "write") -> float:
    """The utilisation at which provisioned capacity becomes cheaper.

    One provisioned WCU costs $0.00065 per hour and delivers 3,600 write units
    in that hour. Buying those 3,600 units on demand costs 3,600 x $1.25/1M.
    Set them equal:

        provisioned_hourly = utilisation x 3600 x on_demand_per_unit

    Everything else — burst behaviour, adaptive capacity, autoscaling lag — is
    a refinement on top of this one line. Note that the answer comes out the
    same for reads and for writes, because AWS priced both modes with the same
    ratio. That is a deliberate pricing decision, not a coincidence, and it
    means you only ever have to remember ONE number.
    """
    if kind == "write":
        hourly = price("dynamodb", "provisioned_wcu_hour")
        on_demand = per_unit(price("dynamodb", "on_demand_write_per_million"), 1e6)
    elif kind == "read":
        hourly = price("dynamodb", "provisioned_rcu_hour")
        on_demand = per_unit(price("dynamodb", "on_demand_read_per_million"), 1e6)
    else:
        raise ValueError("kind must be 'read' or 'write'")
    return hourly / (3600.0 * on_demand)


def dynamodb_mode_table(peak_per_second: float,
                        utilisations: Sequence[float]) -> List[Dict[str, Any]]:
    """Cost of both modes across a range of utilisations, at a fixed peak.

    Provisioning is sized for the PEAK; billing is against the AVERAGE. The gap
    between those two numbers is the whole decision, and it is why a workload
    with a sharp daily peak can be at 5% utilisation while looking busy.
    """
    rows = []
    for utilisation in utilisations:
        writes = peak_per_second * utilisation * 3600 * HOURS_PER_MONTH
        provisioned = (peak_per_second * HOURS_PER_MONTH
                       * price("dynamodb", "provisioned_wcu_hour"))
        on_demand = writes * per_unit(
            price("dynamodb", "on_demand_write_per_million"), 1e6)
        rows.append({"utilisation": utilisation, "writes": writes,
                     "provisioned": provisioned, "on_demand": on_demand,
                     "cheaper": "provisioned" if provisioned < on_demand
                                else "on-demand"})
    return rows


# ---------------------------------------------------------------------------
# 2. Lambda: how much memory
# ---------------------------------------------------------------------------

def lambda_duration_ms(memory_mb: float, cpu_work_ms_at_1_vcpu: float,
                       io_wait_ms: float = 0.0) -> float:
    """Model a function's duration as a function of its memory setting.

    Lambda does not sell you CPU. It sells you memory, and gives you CPU in
    proportion: roughly one vCPU at 1,769 MB, scaling linearly below and above.
    So the CPU-bound part of your work speeds up as you buy memory, and the
    part that is waiting on the network does not, at all.

        duration = io_wait + cpu_work x (1769 / memory)

    That single formula explains the entire memory-sizing question, and why
    the answer is completely different for two functions that look identical.
    """
    vcpu = memory_mb / 1769.0
    return io_wait_ms + cpu_work_ms_at_1_vcpu / max(vcpu, 1e-9)


def lambda_memory_sweep(cpu_work_ms: float, io_wait_ms: float = 0.0,
                        invocations: float = 1e6, arch: str = "x86",
                        memories: Sequence[int] = (128, 256, 512, 1024, 1769,
                                                   3008, 10240)
                        ) -> List[Dict[str, Any]]:
    """Cost and latency at each memory setting, for a given shape of work."""
    rows = []
    gb_price = price("lambda", f"gb_second_{arch}")
    request_price = per_unit(price("lambda", "request_per_million"), 1e6)
    for memory in memories:
        duration = lambda_duration_ms(memory, cpu_work_ms, io_wait_ms)
        billed_ms = math.ceil(duration / price("lambda", "billing_granularity_ms")) \
            * price("lambda", "billing_granularity_ms")
        gb_seconds = (memory / 1024.0) * (billed_ms / 1000.0) * invocations
        rows.append({"memory_mb": memory, "duration_ms": duration,
                     "gb_seconds": gb_seconds,
                     "cost": gb_seconds * gb_price + invocations * request_price})
    return rows


def best_memory(rows: Sequence[Dict[str, Any]]) -> Tuple[int, int]:
    """(cheapest memory, fastest memory). When they are the same number, more
    memory is FREE SPEED and leaving the default at 128 MB is pure loss."""
    return (min(rows, key=lambda r: r["cost"])["memory_mb"],
            min(rows, key=lambda r: r["duration_ms"])["memory_mb"])


# ---------------------------------------------------------------------------
# 3. Network: NAT gateway, or an endpoint
# ---------------------------------------------------------------------------

def nat_vs_gateway_endpoint(gb_per_month: float, azs: int = 3,
                            hours: float = HOURS_PER_MONTH) -> Dict[str, float]:
    """S3 and DynamoDB traffic: through the NAT, or through a gateway endpoint.

    There is NO crossover here, which is the answer. A gateway endpoint costs
    nothing per hour and nothing per GB, forever. Every byte of S3 or DynamoDB
    traffic that leaves a private subnet through a NAT gateway is $0.045 spent
    for no reason, and the fix is a route-table entry.

    This is the highest-value line in the file: it is a one-line change, it
    cannot break anything (the traffic stays inside AWS either way), and on a
    data-heavy workload it is often the largest single saving available.
    """
    nat = bill_network(nat_gateways=azs, nat_gb=gb_per_month, hours=hours).total
    endpoint = 0.0
    return {"through_nat": nat, "through_endpoint": endpoint,
            "saving": nat - endpoint,
            "nat_still_needed_for": "package installs, third-party APIs, "
                                    "anything not S3 or DynamoDB"}


def nat_vs_interface_endpoint(gb_per_month: float, services: int = 1,
                              azs: int = 3,
                              hours: float = HOURS_PER_MONTH) -> Dict[str, float]:
    """For every OTHER AWS service, the endpoint is an interface endpoint, and
    it is not free: $0.01/hour per AZ per service, plus $0.01/GB.

    Now there IS a crossover, and it has two terms — one per service you route
    privately, one per GB you move. Route thirty services privately to save a
    NAT gateway and you have bought thirty endpoints instead.
    """
    nat = bill_network(nat_gateways=azs, nat_gb=gb_per_month, hours=hours).total
    endpoint = bill_network(interface_endpoints=services * azs,
                            interface_endpoint_gb=gb_per_month,
                            hours=hours).total
    breakeven_services = nat / (azs * hours * price("network",
                                                    "interface_endpoint_hour")) \
        if gb_per_month == 0 else float("nan")
    return {"through_nat": nat, "through_endpoints": endpoint,
            "saving": nat - endpoint, "breakeven_services": breakeven_services}


# ---------------------------------------------------------------------------
# 4. S3: which storage class
# ---------------------------------------------------------------------------

def storage_class_cost(gb: float, months: float, reads_per_month: float,
                       storage_class: str, object_kb: float = 1024.0) -> float:
    """Total cost of holding 1 GB for `months`, read `reads_per_month` times.

    Three terms, and people usually remember only the first:
      storage    x max(months, minimum duration)
      retrieval  x reads          <- free in Standard, $0.02/GB in Deep Archive
      minimum billable object size               <- 128 KB in the IA classes
    """
    unit_price, min_days, min_object_kb, retrieval = \
        price("s3", "storage_gb_month")[storage_class]
    padding = max(1.0, min_object_kb / object_kb)
    billed_months = max(months, min_days / 30.4167)
    return (gb * padding * unit_price * billed_months
            + gb * retrieval * reads_per_month * months)


def best_storage_class(gb: float, months: float, reads_per_month: float,
                       object_kb: float = 1024.0) -> Tuple[str, float]:
    options = {klass: storage_class_cost(gb, months, reads_per_month, klass,
                                         object_kb)
               for klass in price("s3", "storage_gb_month")}
    winner = min(options, key=lambda k: options[k])
    return winner, options[winner]


# ---------------------------------------------------------------------------
# 5. KMS: one data key per record, or one per batch
# ---------------------------------------------------------------------------

def measure_data_key_reuse(records: int, records_per_key: int) -> Dict[str, Any]:
    """MEASURED, not modelled — against the KMS you built.

    Envelope encryption already means the master key never touches your data.
    The second half of the idea is that a data key can cover MANY records, and
    that is what turns a per-record KMS call into a per-batch one.

    The security cost is real and worth stating: reusing one data key across a
    batch means one compromised data key exposes the whole batch, and it makes
    per-record crypto-shredding impossible. That is a trade, not a free win —
    but it is a trade you should make knowingly rather than by default.
    """
    from kms import KMS, EnvelopeCipher

    kms = KMS()
    kms.create_key("app")
    cipher = EnvelopeCipher(kms, "app")
    for _ in range(records):
        cipher.encrypt(b"record", {"tenant": "acme"})
    per_record_calls = kms.keys["app"].stats["data_keys"]

    batched = KMS()
    batched.create_key("app")
    batches = math.ceil(records / max(1, records_per_key))
    for _ in range(batches):
        batched.generate_data_key("app", {"tenant": "acme"})
        # ...and the batch's records are encrypted locally under that one key.
    batch_calls = batched.keys["app"].stats["data_keys"]

    return {"records": records,
            "calls_per_record": per_record_calls,
            "calls_batched": batch_calls,
            "cost_per_record": bill_kms(kms).total,
            "cost_batched": bill_kms(batched).total,
            "request_reduction": per_record_calls / max(1, batch_calls)}


# ---------------------------------------------------------------------------
# 6. SQS: batching and polling
# ---------------------------------------------------------------------------

def measure_queue_strategies(messages: int = 500) -> List[Dict[str, Any]]:
    """MEASURED against the SQS you built. Same messages, same work done."""
    from sqs import Queue

    strategies = [
        ("short poll, receive 1", 1, 20 * 60 * 5),   # 20/s of empty polling
        ("long poll,  receive 1", 1, 3 * 5),         # a 20s wait: 3/minute
        ("long poll,  receive 10", 10, 3 * 5),
    ]
    rows = []
    for label, batch, empty in strategies:
        queue = Queue("work")
        for n in range(messages):
            queue.send(f"m{n}", now=0.0)
        drained = 0
        while drained < messages:
            received = queue.receive(max_messages=batch, now=1.0)
            if not received:
                break
            for message in received:
                queue.delete(message.receipt_handle)
                drained += 1
        priced = bill_sqs(queue, receive_batch=batch, empty_receives=empty)
        rows.append({"strategy": label, "drained": drained,
                     "work_requests": sum(i.quantity for i in priced.items
                                          if i.dimension == "requests"),
                     "idle_requests": sum(i.quantity for i in priced.items
                                          if i.dimension == "idle-poll-requests"),
                     "cost_per_month_at_1000x": priced.total * 1000})
    return rows


# ---------------------------------------------------------------------------
# 7. DynamoDB: query or scan
# ---------------------------------------------------------------------------

def measure_query_vs_scan(tenants: int = 40, per_tenant: int = 10
                          ) -> Dict[str, Any]:
    """MEASURED. The cost ratio is the table size divided by the result size,
    and it grows without limit as the table grows. A scan that is fine in
    staging is a bill in production, and nothing about the code changed."""
    from dynamodb import Table

    table = Table("docs", partition_key="tenant", sort_key="doc",
                  read_capacity=5000, write_capacity=5000, num_partitions=4)
    for t in range(tenants):
        for d in range(per_tenant):
            table.put_item({"tenant": f"t{t}", "doc": f"{d:04d}"}, now=0.0)

    before = table.stats["scanned_items"]
    table.query("t0", now=1.0)
    query_items = table.stats["scanned_items"] - before

    before = table.stats["scanned_items"]
    table.scan(lambda item: item["tenant"] == "t0", now=1.0)
    scan_items = table.stats["scanned_items"] - before

    rate = per_unit(price("dynamodb", "on_demand_read_per_million"), 1e6)
    return {"table_items": tenants * per_tenant,
            "query_items": query_items, "scan_items": scan_items,
            "ratio": scan_items / max(1, query_items),
            "query_cost_per_million": query_items * 0.5 * rate * 1e6,
            "scan_cost_per_million": scan_items * 0.5 * rate * 1e6}


# ---------------------------------------------------------------------------
# 8. Reading a bill: rank the work
# ---------------------------------------------------------------------------

def rank_savings(bill: Bill, candidates: Dict[str, Tuple[str, float]]
                 ) -> List[Dict[str, Any]]:
    """Given a bill and a set of proposed changes, rank them by dollars saved.

    `candidates` maps a change's name to ("service/dimension", fraction
    removed). The output is deliberately boring: a sorted list. It exists to
    make the obvious point that a 90% saving on a 2% line is a 1.8% saving, and
    that engineers reliably pick the interesting optimisation over the large
    one.

    Note the key: SERVICE and dimension, not dimension alone. "requests" names
    a Lambda line, an SQS line and a KMS line, and summing them because they
    share a word is the sort of quiet error that makes a cost model agree with
    itself and disagree with the invoice.
    """
    by_line: Dict[str, float] = {}
    for item in bill.items:
        key = f"{item.service}/{item.dimension}"
        by_line[key] = by_line.get(key, 0.0) + item.cost

    ranked = []
    for name, (dimension, fraction) in candidates.items():
        if dimension not in by_line:
            raise KeyError(f"no line {dimension!r} on this bill; "
                           f"have {sorted(by_line)}")
        current = by_line[dimension]
        saving = current * fraction
        ranked.append({"change": name, "dimension": dimension,
                       "line_cost": current, "saving": saving,
                       "bill_share": saving / bill.total if bill.total else 0.0})
    return sorted(ranked, key=lambda row: -row["saving"])


def allocate(bill: Bill, weights: Dict[str, float]) -> Dict[str, float]:
    """Split a shared bill across tenants by some weight you chose.

    There is no correct answer here and that is the lesson. A NAT gateway, a
    KMS key and a queue are shared; nothing in the metering says which tenant
    caused which fraction of them. Allocating by request count and allocating
    by bytes give different answers, both defensible, and whichever one you
    pick becomes the incentive your teams optimise against.
    """
    total_weight = sum(weights.values()) or 1.0
    return {tenant: bill.total * weight / total_weight
            for tenant, weight in weights.items()}


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=" * 78)
    print("OPTIMIZE — every rule of thumb, replaced by the number where it flips")
    print("=" * 78)

    # -- 1 -----------------------------------------------------------------
    print("\n1. DynamoDB: provisioned or on-demand")
    print("-" * 78)
    for kind in ("write", "read"):
        print(f"  crossover ({kind}s): "
              f"{100 * dynamodb_crossover(kind):.2f}% utilisation")
    print("  Identical for both, because AWS priced the two modes with the")
    print("  same ratio. One number to remember: about 14%.")

    print(f"\n  A table provisioned for a 100/s peak, over a month:")
    print(f"    {'utilisation':>12}{'writes/month':>16}{'provisioned':>14}"
          f"{'on-demand':>14}  cheaper")
    for row in dynamodb_mode_table(100, (0.02, 0.05, 0.1, 0.1444, 0.2, 0.5, 1.0)):
        print(f"    {100 * row['utilisation']:>10.1f}% {row['writes']:>15,.0f}"
              f"{money(row['provisioned']):>14}{money(row['on_demand']):>14}"
              f"  {row['cheaper']}")
    print("  Read that table twice. A workload with a sharp daily peak sits")
    print("  at 5-10% utilisation while feeling busy all day, and for every")
    print("  row in that range on-demand — the mode everyone calls the")
    print("  expensive one — is the cheaper mode. Provisioned capacity is not")
    print("  a discount. It is a bet that you will use what you reserved.")

    # -- 2 -----------------------------------------------------------------
    print("\n2. Lambda: how much memory")
    print("-" * 78)
    for label, cpu_ms, io_ms in (("CPU-bound (image resize)", 900.0, 0.0),
                                 ("mixed (parse + one API call)", 200.0, 150.0),
                                 ("I/O-bound (wait on a database)", 20.0, 400.0)):
        rows = lambda_memory_sweep(cpu_ms, io_ms)
        cheapest, fastest = best_memory(rows)
        print(f"\n  {label}")
        print(f"    {'memory':>8}{'duration':>11}{'$/1M invocations':>19}"
              f"{'vs 128 MB':>12}")
        base = rows[0]["cost"]
        for row in rows:
            mark = ""
            if row["memory_mb"] == cheapest:
                mark += "  <- cheapest"
            if row["memory_mb"] == fastest and fastest != cheapest:
                mark += "  <- fastest"
            elif row["memory_mb"] == fastest:
                mark += " AND fastest"
            print(f"    {row['memory_mb']:>6} MB{row['duration_ms']:>9.0f} ms"
                  f"{money(row['cost']):>19}{row['cost'] / base:>11.2f}x{mark}")

    print("\n  For CPU-bound work the cost line is almost FLAT: you buy CPU in")
    print("  proportion to memory, so twice the memory runs in half the time")
    print("  for the same GB-seconds. Leaving that function at the 128 MB")
    print("  default buys you a 12x slower function at no saving whatsoever.")
    print("  For I/O-bound work the opposite holds: the wait does not shrink,")
    print("  so every extra MB is billed against a duration you cannot reduce.")
    print("  Same service, same slider, opposite advice — and the only way to")
    print("  tell which function you have is to measure the curve.")

    arm = lambda_memory_sweep(900.0, 0.0, arch="arm")[3]["cost"]
    x86 = lambda_memory_sweep(900.0, 0.0, arch="x86")[3]["cost"]
    print(f"\n  And Graviton: {money(x86)} -> {money(arm)} per million, a "
          f"{100 * (1 - arm / x86):.0f}% cut for a one-line config change.")

    # -- 3 -----------------------------------------------------------------
    print("\n3. Network: NAT gateway, or an endpoint")
    print("-" * 78)
    print(f"    {'S3 traffic/month':>18}{'via NAT (3 AZ)':>16}{'via gateway ep':>16}"
          f"{'saving':>12}")
    for gb in (100.0, 1_000.0, 10_000.0, 100_000.0):
        result = nat_vs_gateway_endpoint(gb)
        print(f"    {gb:>15,.0f} GB{money(result['through_nat']):>16}"
              f"{money(result['through_endpoint']):>16}"
              f"{money(result['saving']):>12}")
    print("  There is no crossover. A gateway endpoint for S3 and DynamoDB is")
    print("  free at every volume, forever. If your private subnets reach S3")
    print("  through a NAT gateway, that is a route-table entry away from being")
    print("  the largest single saving on the bill.")

    print(f"\n  Interface endpoints are different — they cost money, so they")
    print(f"  have a real crossover:")
    print(f"    {'services routed':>16}{'via NAT':>12}{'via endpoints':>16}"
          f"{'winner':>14}")
    for services in (1, 3, 10, 30):
        result = nat_vs_interface_endpoint(1_000.0, services=services)
        winner = "endpoints" if result["saving"] > 0 else "NAT"
        print(f"    {services:>16}{money(result['through_nat']):>12}"
              f"{money(result['through_endpoints']):>16}{winner:>14}")
    print("  Route ten services privately and you have bought thirty endpoints")
    print("  (one per AZ each) to replace three NAT gateways. 'Endpoints are")
    print("  cheaper than NAT' stops being true somewhere in that table.")

    # -- 4 -----------------------------------------------------------------
    print("\n4. S3: which storage class, as a function of how you USE the data")
    print("-" * 78)
    print(f"    {'reads/GB/month':>15}", end="")
    retentions = (1.0, 6.0, 24.0)
    for months in retentions:
        print(f"{f'kept {months:.0f} mo':>18}", end="")
    print()
    for reads in (0.0, 0.05, 0.25, 1.0, 4.0):
        print(f"    {reads:>15.2f}", end="")
        for months in retentions:
            klass, cost = best_storage_class(1.0, months, reads)
            print(f"{klass:>13}{money(cost):>5}" if False else
                  f"{klass:>18}", end="")
        print()
    print("  Nothing in that table is about how COLD the data is. It is about")
    print("  how often you read it and how long you keep it, because those are")
    print("  the two terms the price sheet actually has.")

    print(f"\n  The same 1 GB kept 1 month, priced in every class:")
    print(f"    {'class':<16}{'never read':>14}{'read once':>14}{'read 4x':>14}")
    for klass in price("s3", "storage_gb_month"):
        costs = [storage_class_cost(1.0, 1.0, r, klass) for r in (0, 1, 4)]
        print(f"    {klass:<16}" + "".join(money(c).rjust(14) for c in costs))
    print("  Deep Archive read four times in a month costs several times what")
    print("  Standard does. And note what this model does NOT price: Deep")
    print("  Archive answers a read in up to 12 hours, Standard in 12")
    print("  milliseconds. The table above says deep_archive wins at 0 reads")
    print("  even for one month — arithmetically true, and still the wrong")
    print("  choice if anyone might need the data this week. A cost model")
    print("  that only has dollars in it will confidently recommend an")
    print("  outage. The latency column is yours to add.")

    # -- 5 -----------------------------------------------------------------
    print("\n5. KMS: one data key per record, or one per batch")
    print("-" * 78)
    print(f"    {'records/key':>12}{'KMS calls':>12}{'request line':>16}"
          f"{'total':>12}")
    for per_key in (1, 10, 100, 1000):
        result = measure_data_key_reuse(2000, per_key)
        requests = result["cost_batched"] - price("kms", "key_month")
        print(f"    {per_key:>12}{result['calls_batched']:>12,}"
              f"{money(requests):>16}{money(result['cost_batched']):>12}")
    request_price = per_unit(price("kms", "request_per_10000"), 10_000)
    key_month = price("kms", "key_month")
    print(f"\n  The floor is {money(key_month)}: the key itself. At this volume")
    print("  there is no money in the request line to save, and reusing data")
    print("  keys buys a wider blast radius for nothing in return. The same")
    print("  comparison projected upwards, where it does start to matter:")
    print(f"    {'records/month':>16}{'per record':>14}{'per 1000':>14}"
          f"{'saved':>14}")
    for volume in (2e3, 1e6, 2e8):
        each = key_month + volume * request_price
        batched = key_month + (volume / 1000) * request_price
        print(f"    {volume:>16,.0f}{money(each):>14}{money(batched):>14}"
              f"{money(each - batched):>14}")
    print(f"  The break-even for caring at all is roughly "
          f"{key_month / request_price:,.0f} records a month —")
    print("  the point where the request line reaches the price of the key.")

    # -- 6 -----------------------------------------------------------------
    print("\n6. SQS: polling and batching, measured")
    print("-" * 78)
    print(f"    {'strategy':<24}{'drained':>9}{'work':>9}{'idle':>9}"
          f"{'total':>9}{'$/mo at 1000x':>16}")
    for row in measure_queue_strategies(500):
        total = row["work_requests"] + row["idle_requests"]
        print(f"    {row['strategy']:<24}{row['drained']:>9}"
              f"{row['work_requests']:>9,.0f}{row['idle_requests']:>9,.0f}"
              f"{total:>9,.0f}{money(row['cost_per_month_at_1000x']):>16}")
    print("  Identical messages delivered, three different bills. Long polling")
    print("  deletes the idle column outright. Batching collapses the receive")
    print("  and delete calls tenfold — but not the sends, which is why the")
    print("  work column falls 2.5x and not 10x. Both are opt-in, which is why")
    print("  a first SQS bill is usually mostly calls that returned nothing.")

    # -- 7 -----------------------------------------------------------------
    print("\n7. DynamoDB: query or scan, measured")
    print("-" * 78)
    result = measure_query_vs_scan()
    print(f"  table holds {result['table_items']} items; both operations return"
          f" the same 10")
    print(f"    query touched {result['query_items']:>4} items")
    print(f"    scan  touched {result['scan_items']:>4} items  "
          f"({result['ratio']:.0f}x)")
    print(f"    per million operations: query "
          f"{money(result['query_cost_per_million'])}, scan "
          f"{money(result['scan_cost_per_million'])}")
    print("  The ratio IS the table size divided by the result size, so it")
    print("  grows without bound as the table does. The scan that was fine in")
    print("  staging with 400 rows is the same code at 400 million.")

    # -- 8 -----------------------------------------------------------------
    print("\n8. The pipeline you built, priced — and then optimised")
    print("-" * 78)
    import capstone

    system = capstone.build()
    cloud = system["cloud"]
    for n in range(120):
        capstone.upload(system, system["uploader"], f"tenant{n % 6}",
                        f"docs/{n:04d}.pdf", b"x" * 250_000, now=n * 0.5)
    capstone.drain(system, now=200.0, batch=10)

    uploads = 120
    bill = Bill("upload pipeline", HOURS_PER_MONTH)
    bill_s3(cloud.s3, bill=bill)
    bill_dynamodb(system["documents"], mode="on_demand", bill=bill)
    for function in cloud.lambda_service.functions.values():
        bill_lambda(function, bill=bill)
    for queue in cloud.queues.values():
        # 20s long polls, two pollers, all month: a fixed line that does not
        # scale with uploads, which is why bill.scaled leaves it alone.
        bill_sqs(queue, empty_receives=2 * 3 * 60 * 24 * 30, bill=bill)
    bill_sns(system["topic"], bill=bill)
    bill_kms(cloud.kms, bill=bill)
    # Every uploaded document is downloaded once, and the upload path reaches
    # S3 through the NAT gateway. Both derived from the traffic, so both scale.
    document_gb = uploads * 250_000 / 1e9
    bill_network(nat_gateways=3, nat_gb=document_gb,
                 internet_out_gb=document_gb, bill=bill)

    per_million = bill.scaled(1e6 / uploads, "upload pipeline @ 1M uploads/mo")
    print(per_million.format(top=8, notes=False))

    top = per_million.dominant()
    print(f"\n  Dominant line: {top.service}/{top.dimension} at "
          f"{100 * per_million.share(top):.0f}%.")
    print(f"  Unit economics: "
          f"{money(per_million.total / 1e6 * 1000)} per thousand uploads.")

    print("\n  Ranked by dollars saved, not by how interesting the change is:")
    ranked = rank_savings(per_million, {
        "S3 gateway endpoint (a route-table entry)":
            ("network/nat-processing-gb", 1.0),
        "CloudFront in front of the downloads":
            ("network/internet-out-gb", 0.45),
        "drop to one NAT gateway (and lose an AZ)":
            ("network/nat-gateway-hours", 2 / 3),
        "long polling on both queues":
            ("sqs/idle-poll-requests", 0.998),
        "Graviton on the indexer":
            ("lambda/gb-seconds", 0.20),
        "BatchWriteItem, 10 writes per call":
            ("dynamodb/on-demand-writes", 0.0),
    })
    print(f"    {'change':<42}{'line':>11}{'saves':>12}{'of bill':>10}")
    for row in ranked:
        print(f"    {row['change']:<42}{money(row['line_cost']):>11}"
              f"{money(row['saving']):>12}{100 * row['bill_share']:>9.1f}%")
    print("  Two of those are worth reading twice. The route-table entry is")
    print("  free to make, cannot change behaviour, and beats every code")
    print("  change on the list. And BatchWriteItem saves exactly nothing:")
    print("  it is ONE API call, but DynamoDB still bills a write unit per")
    print("  item. Batching is a latency and throughput optimisation there,")
    print("  not a cost one — unlike SQS, where batching genuinely divides")
    print("  the bill by ten. Same word, two services, opposite answers.")

    print("\n  Allocating the shared bill across six tenants, two ways:")
    by_requests = allocate(per_million, {f"tenant{n}": 1.0 for n in range(6)})
    weights = {f"tenant{n}": float(n + 1) for n in range(6)}
    by_bytes = allocate(per_million, weights)
    print(f"    {'tenant':<10}{'even split':>14}{'by volume':>14}{'ratio':>10}")
    for tenant in by_requests:
        print(f"    {tenant:<10}{money(by_requests[tenant]):>14}"
              f"{money(by_bytes[tenant]):>14}"
              f"{by_bytes[tenant] / by_requests[tenant]:>9.2f}x")
    spread = max(by_bytes.values()) / min(by_bytes.values())
    print(f"  Same bill, same tenants, and the two rules disagree by "
          f"{spread:.0f}x at the")
    print("  ends. Nothing in the metering can settle it: the NAT gateway and")
    print("  the KMS key are shared, and no counter anywhere says whose fault")
    print("  they are. Pick a rule, write it down, and understand that the")
    print("  rule you picked is now the incentive your teams optimise against.")

    print("\n" + "=" * 78)
    print("The habit worth keeping: never accept a cost rule without its")
    print("crossover. 'Use X for Y' is a claim about a regime, and the regime")
    print("boundary is the only part that survives a change in your traffic.")
    print("=" * 78)


if __name__ == "__main__":
    _demo()
