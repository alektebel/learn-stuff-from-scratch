"""
Optimize — turning each price into a decision with a number.

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

Learning Path:
1. dynamodb_crossover — derive 14.4% from the price sheet, do not look it up
2. lambda_duration_ms and the memory sweep — one formula, three opposite
   answers
3. nat_vs_gateway_endpoint — the case where there is no crossover, and why
   that makes it the most valuable line in the file
4. storage_class_cost — three terms, of which people remember one
5. The measured sections: data-key reuse, queue batching, query versus scan
6. rank_savings and allocate — reading a bill, and the question metering
   cannot answer
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

    TODO: derive it, do not look it up.

    One provisioned WCU costs $0.00065 per hour and delivers 3,600 write units
    in that hour. Buying those 3,600 units on demand costs 3,600 x $1.25/1M.
    Set them equal:

        provisioned_hourly = utilisation x 3600 x on_demand_per_unit

    Return the utilisation, as a fraction. Everything else — burst behaviour,
    adaptive capacity, autoscaling lag — is a refinement on top of that one
    line.

    Then run it for reads as well as writes and notice that the answer is the
    SAME. That is a deliberate pricing decision by AWS, not a coincidence, and
    it means you only ever have to remember one number.
    """
    raise NotImplementedError


def dynamodb_mode_table(peak_per_second: float,
                        utilisations: Sequence[float]) -> List[Dict[str, Any]]:
    """Cost of both modes across a range of utilisations, at a fixed peak.

    TODO: for each utilisation, rows of {"utilisation", "writes",
    "provisioned", "on_demand", "cheaper"}. Provision for the PEAK; bill
    on-demand against the AVERAGE.

    The gap between those two numbers is the whole decision, and it is why a
    workload with a sharp daily peak can sit at 5% utilisation while looking
    busy all day.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 2. Lambda: how much memory
# ---------------------------------------------------------------------------

def lambda_duration_ms(memory_mb: float, cpu_work_ms_at_1_vcpu: float,
                       io_wait_ms: float = 0.0) -> float:
    """Model a function's duration as a function of its memory setting.

    TODO:  duration = io_wait + cpu_work x (1769 / memory)

    Lambda does not sell you CPU. It sells you memory, and gives you CPU in
    proportion: roughly one vCPU at 1,769 MB, scaling linearly below and above.
    So the CPU-bound part of your work speeds up as you buy memory, and the
    part that is waiting on the network does not, at all.

    That single formula explains the entire memory-sizing question, and why the
    answer is completely different for two functions that look identical.
    """
    raise NotImplementedError


def lambda_memory_sweep(cpu_work_ms: float, io_wait_ms: float = 0.0,
                        invocations: float = 1e6, arch: str = "x86",
                        memories: Sequence[int] = (128, 256, 512, 1024, 1769,
                                                   3008, 10240)
                        ) -> List[Dict[str, Any]]:
    """TODO: cost and latency at each memory setting.

    Rows of {"memory_mb", "duration_ms", "gb_seconds", "cost"}. Round the
    duration up to the billing granularity before converting to GB-seconds —
    Lambda bills in 1 ms increments and the rounding matters on short
    functions. Include the per-request charge in the cost.
    """
    raise NotImplementedError


def best_memory(rows: Sequence[Dict[str, Any]]) -> Tuple[int, int]:
    """TODO: (cheapest memory, fastest memory).

    When they are the same number, more memory is FREE SPEED and leaving the
    default at 128 MB is pure loss. When they are far apart, you have an
    I/O-bound function and every extra MB is billed against a wait you cannot
    shorten.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 3. Network: NAT gateway, or an endpoint
# ---------------------------------------------------------------------------

def nat_vs_gateway_endpoint(gb_per_month: float, azs: int = 3,
                            hours: float = HOURS_PER_MONTH) -> Dict[str, float]:
    """S3 and DynamoDB traffic: through the NAT, or through a gateway endpoint.

    TODO: price both with bill_network and return the saving.

    There is NO crossover here, which is the answer. A gateway endpoint costs
    nothing per hour and nothing per GB, forever. Every byte of S3 or DynamoDB
    traffic that leaves a private subnet through a NAT gateway is $0.045 spent
    for no reason, and the fix is a route-table entry.

    This is the highest-value line in the file: it is a one-line change, it
    cannot break anything (the traffic stays inside AWS either way), and on a
    data-heavy workload it is often the largest single saving available. It is
    also the one nobody finds, because nothing in the application emits a
    metric for "bytes that went the expensive way".
    """
    raise NotImplementedError


def nat_vs_interface_endpoint(gb_per_month: float, services: int = 1,
                              azs: int = 3,
                              hours: float = HOURS_PER_MONTH) -> Dict[str, float]:
    """For every OTHER AWS service, the endpoint is an interface endpoint, and
    it is not free: $0.01/hour per AZ per service, plus $0.01/GB.

    TODO: price both. Note that you need `services x azs` endpoints.

    Now there IS a crossover, and it has two terms — one per service you route
    privately, one per GB you move. Route thirty services privately to save
    three NAT gateways and you have bought ninety endpoints instead.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 4. S3: which storage class
# ---------------------------------------------------------------------------

def storage_class_cost(gb: float, months: float, reads_per_month: float,
                       storage_class: str, object_kb: float = 1024.0) -> float:
    """Total cost of holding `gb` for `months`, read `reads_per_month` times.

    TODO — three terms, and people usually remember only the first:
      storage    x max(months, minimum duration in months)
      retrieval  x reads          <- free in Standard, $0.02/GB in Deep Archive
      padding for the minimum billable object size   <- 128 KB in the IA classes
    """
    raise NotImplementedError


def best_storage_class(gb: float, months: float, reads_per_month: float,
                       object_kb: float = 1024.0) -> Tuple[str, float]:
    """TODO: the cheapest class and its cost, over every class in the sheet.

    Then build the decision table (reads/month x retention) and notice that
    NOTHING in it is about how "cold" the data feels. It is about how often you
    read it and how long you keep it, because those are the only two terms the
    price sheet has.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 5. KMS: one data key per record, or one per batch
# ---------------------------------------------------------------------------

def measure_data_key_reuse(records: int, records_per_key: int) -> Dict[str, Any]:
    """MEASURED, not modelled — against the KMS you built.

    TODO:
    1. One KMS + EnvelopeCipher, encrypt `records` records. Read
       stats["data_keys"]: one call per record.
    2. A second KMS, call generate_data_key once per BATCH of records_per_key
       and encrypt that batch's records locally under it.
    3. Price both with bill_kms and return the counts, the costs and the ratio.

    Envelope encryption already means the master key never touches your data.
    The second half of the idea is that a data key can cover MANY records, and
    that is what turns a per-record KMS call into a per-batch one.

    The security cost is real and worth stating: reusing one data key across a
    batch means one compromised data key exposes the whole batch, and it makes
    per-record crypto-shredding impossible. That is a trade, not a free win —
    but it is a trade you should make knowingly rather than by default, and
    below a few hundred thousand records a month there is no money in it at
    all.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 6. SQS: batching and polling
# ---------------------------------------------------------------------------

def measure_queue_strategies(messages: int = 500) -> List[Dict[str, Any]]:
    """MEASURED against the SQS you built. Same messages, same work done.

    TODO: three strategies — short poll with receive 1, long poll with
    receive 1, long poll with receive 10 — each draining the same queue
    completely. Model the idle polling as `empty_receives`: short polling at
    20 calls a second, long polling at 3 a minute. Return the work requests
    and the idle requests SEPARATELY; a single total hides which of the two
    knobs did the work.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 7. DynamoDB: query or scan
# ---------------------------------------------------------------------------

def measure_query_vs_scan(tenants: int = 40, per_tenant: int = 10
                          ) -> Dict[str, Any]:
    """MEASURED. Build a table, query one partition, then scan with a filter
    that returns exactly the same items. Compare scanned_items.

    TODO: return the two item counts, their ratio, and the cost per million
    operations of each.

    The cost ratio is the table size divided by the result size, and it grows
    without limit as the table grows. A scan that is fine in staging is a bill
    in production, and nothing about the code changed.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 8. Reading a bill: rank the work
# ---------------------------------------------------------------------------

def rank_savings(bill: Bill, candidates: Dict[str, Tuple[str, float]]
                 ) -> List[Dict[str, Any]]:
    """Given a bill and a set of proposed changes, rank them by dollars saved.

    `candidates` maps a change's name to ("service/dimension", fraction
    removed).

    TODO: group the bill by "service/dimension", then for each candidate
    compute the saving and its share of the total. Sort by saving, descending.
    Raise on a dimension that is not on the bill — a change that saves nothing
    because you misspelled the line is the worst possible output here.

    Note the key: SERVICE and dimension, not dimension alone. "requests" names
    a Lambda line, an SQS line and a KMS line, and summing them because they
    share a word is the sort of quiet error that makes a cost model agree with
    itself and disagree with the invoice.

    The output is deliberately boring: a sorted list. It exists to make the
    obvious point that a 90% saving on a 2% line is a 1.8% saving, and that
    engineers reliably pick the interesting optimisation over the large one.
    """
    raise NotImplementedError


def allocate(bill: Bill, weights: Dict[str, float]) -> Dict[str, float]:
    """TODO: split a shared bill across tenants by some weight you chose.

    There is no correct answer here and that is the lesson. A NAT gateway, a
    KMS key and a queue are shared; nothing in the metering says which tenant
    caused which fraction of them. Allocating by request count and allocating
    by bytes give different answers, both defensible, and whichever one you
    pick becomes the incentive your teams optimise against.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    """Once the checks pass, write the demo. Eight sections, and for each one
    PREDICT the number before you run it:

    1. The DynamoDB crossover for reads and for writes (they match), then a
       table of both modes at 2% to 100% utilisation against a fixed peak.

    2. The Lambda memory sweep for three shapes of work: CPU-bound, mixed and
       I/O-bound. Mark the cheapest and the fastest row of each. On CPU-bound
       work they are the same row and the cost column is flat — more memory is
       free speed. On I/O-bound work the cost column rises 40x across the same
       range. Same slider, opposite advice. Then price Graviton.

    3. NAT versus gateway endpoint across four volumes (no crossover), then
       NAT versus interface endpoints across 1 to 30 services (a real one).

    4. The storage-class decision table, reads/month against retention. Then
       all six classes at 0, 1 and 4 reads. Say out loud what the model does
       NOT price: Deep Archive answers in 12 hours.

    5. Data-key reuse measured at 1, 10, 100 and 1000 records per key — and
       then projected up to where it stops being noise, with the break-even
       volume computed.

    6. The three queue strategies, work and idle requests in separate columns.

    7. Query versus scan, measured, with the ratio.

    8. The capstone pipeline: build it, run traffic through it, bill it, scale
       the bill to a million uploads a month, and find the dominant line.
       Then rank a handful of candidate changes by dollars saved — include at
       least one that saves NOTHING (BatchWriteItem still bills per item) and
       one that is a config change rather than a code change. Finally allocate
       the bill across tenants two different ways and look at how far apart
       the answers are.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
