"""
Billing — metering the services you actually built.

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

Learning Path:
1. stored_bytes and bill_s3 — including the versioning trap and the two S3
   minimums (object size, storage duration)
2. bill_dynamodb — both modes from the same table, so the crossover is
   computable
3. bill_lambda — GB-seconds, and the three things people forget
4. bill_sqs and bill_sns — where request count is not message count, and where
   the protocol string is the price
5. bill_kms and bill_network — the fixed lines, and the dimension nothing in
   your code counts
6. bill_account and per_unit_of_work — the whole thing, per unit of work
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from pricing import (Bill, FreeTier, HOURS_PER_MONTH, LineItem, PRICES,
                     billable_units, money, per_unit, price, prorate,
                     tiered_cost)


def utilisation(used: float, available: float) -> str:
    """TODO: a readable utilisation string.

    Percentages lie at both ends. 0.00% and 100.00% are both common answers and
    only one of them is informative, so print anything under 0.1% as a ratio
    ("1 in 1,051,200") instead, and handle used == 0 and available == 0.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------

def stored_bytes(s3: Any) -> Dict[str, int]:
    """Split what is stored into what you can SEE and what you are PAYING for.

    TODO: walk every bucket, every key, every version. Return
    {"live", "noncurrent", "delete_markers", "total"} where `live` is the size
    of the CURRENT version of each key (unless a delete marker is on top) and
    `noncurrent` is everything underneath.

    A plain DELETE in a versioned bucket does not delete. It pushes a delete
    marker, and every byte underneath stays on the invoice forever. `live` is
    what a LIST shows you; `noncurrent` is the part that is invisible in the
    console and fully billable. When someone asks why the bucket costs more
    than the data in it, this function is the answer.
    """
    raise NotImplementedError


def bill_s3(s3: Any, storage_class: str = "standard", days: float = 30.0,
            retrieved_gb: float = 0.0, bill: Optional[Bill] = None) -> Bill:
    """Price an S3 service object from its own counters.

    TODO — four dimensions, and two rules that only exist in the cheap classes:
    1. STORAGE. Sum every non-delete-marker version, but pad each object up to
       the class's minimum billable object size first: a 4 KB object in
       Standard-IA is billed as 128 KB. Apply the tiered price for `standard`
       and the flat one otherwise.
    2. DURATION. Bill max(days, the class's minimum days). Deleting from Deep
       Archive after a week still costs 180 days.
    3. REQUESTS. puts, gets, lists and deletes from s3.stats, each at the
       per-1000 rate for this class. LIST is priced as a PUT-class request.
       DELETE is free — say so on the line, along with how many delete markers
       it left behind.
    4. RETRIEVAL, if retrieved_gb: free in Standard, $0.02/GB in Deep Archive.

    Which dimension dominates depends entirely on your object size. A million
    1 KB objects and one 1 GB object hold the same bytes; the million costs
    1000x more in requests and, in any IA class, 128x more in storage.

    Take an optional `bill` to append to, so an account-level bill can be
    assembled from many services without merging afterwards.
    """
    raise NotImplementedError


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

    TODO:
    1. Recover the table's total capacity: per_partition_* x num_partitions.
    2. write_units = stats["writes"] x billable_units(avg_item_kb, 1)
       read_units  = stats["scanned_items"] x billable_units(avg_item_kb, 4)
                     x (1.0 consistent, 0.5 eventually consistent)
       Note it is scanned_items — items TOUCHED — not returned_items. That
       distinction is the entire scan-versus-query cost argument.
    3. provisioned: capacity x hours at the hourly rate, and put the
       utilisation in the note (capacity is per SECOND, so an hour of reserved
       capacity is 3,600 units you either used or threw away).
       on_demand: the unit counts at the per-million rate.
       Anything else: ValueError.
    4. Storage above the 25 GB free allowance, if storage_gb.
    5. One extra write line per GSI. A GSI is a second table: every write to
       the base table is a write to it too, and it is invisible in your code.

    So the question is never "which is cheaper" — it is "what is my
    utilisation", and there is an exact crossover. optimize.py computes it.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Lambda
# ---------------------------------------------------------------------------

def bill_lambda(function: Any, arch: str = "x86",
                bill: Optional[Bill] = None) -> Bill:
    """Price a function from its billed_ms and its memory setting.

    TODO: two priced dimensions and one free one.
      requests    stats["invocations"] at the per-million rate
      gb-seconds  billed_ms / 1000 x memory_mb / 1024, at the arch's rate
      throttles   stats["throttles"] at ZERO — put it on the bill anyway

    The GB-second is the one that matters, and it is the product of a number
    you chose (memory) and a number you mostly did not (duration) — which is
    why memory sizing is a real optimisation problem rather than a slider.

    Three things people forget, all visible in the counters you already have:
      * A COLD START's initialisation time is billed. Fixing cold starts is a
        latency win AND a cost win.
      * A TIMEOUT is billed for the full timeout, then retried, and billed
        again. A function that times out costs more than one that succeeds.
      * A THROTTLE is free. Nothing ran. It is the cheapest possible failure
        and the most expensive possible outage — which is exactly why it
        belongs on the bill at $0, where someone will see it.
    """
    raise NotImplementedError


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

    TODO:
    1. requests = ceil(sent/send_batch) + ceil(received/receive_batch)
                  + ceil(deleted/receive_batch)
    2. empty_receives goes on its OWN line, dimension "idle-poll-requests",
       because idle polling scales with wall-clock time and the number of
       pollers, NOT with traffic. _FIXED_DIMENSIONS already knows that name,
       so Bill.scaled will leave it alone — which is the point. A queue that
       goes quiet does not get cheaper to poll; it gets more expensive per
       message, backwards from every other line on the bill.
    3. A redelivered message is a NEW billable receive, on every retry.

    Short polling at 20 polls per second on an idle queue costs ~52M requests
    a month for zero work done. Long polling collapses that to ~3 a minute. It
    is one parameter, and the expensive setting is the default.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# SNS
# ---------------------------------------------------------------------------

def bill_sns(topic: Any, bill: Optional[Bill] = None) -> Bill:
    """Price a topic.

    TODO:
    1. publishes at the per-million rate.
    2. Group topic.subscriptions by protocol and sum each one's `delivered`.
       Price each group at its own protocol rate — one line per protocol, named
       "deliveries-<protocol>".
    3. A zero-cost line for stats["filtered"], if any.

    Deliveries are priced BY PROTOCOL, over five orders of magnitude: SQS and
    Lambda are free, HTTP is $0.60/M, email $20/M, SMS $6,450/M. The same
    fanout costs $0 or $6,450 depending on one string.

    And the filter policy: every filtered-out delivery is a delivery you did
    not pay for AND a downstream invocation you did not pay for. Filtering at
    the topic is one of the very few optimisations that is free to apply and
    saves money on two services at once.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# KMS
# ---------------------------------------------------------------------------

def bill_kms(kms: Any, months: float = 1.0,
             bill: Optional[Bill] = None) -> Bill:
    """Price KMS: len(kms.keys) key-months, plus every encrypt, decrypt and
    GenerateDataKey as one request.

    TODO: two lines. Then read them, because which one dominates tells you
    which problem you have:

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
    raise NotImplementedError


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

    TODO: add a line per non-zero argument. Two of them have a twist:
      * internet_out_gb is TIERED (use add_tiered).
      * cross_az_gb is billed on BOTH sides — the quantity on the line is
        double the traffic. Say so in the note, or you will forget.

    Memorise the asymmetries:
      IN from the internet          free
      OUT to the internet           $0.09/GB after the first 100 GB
      cross-AZ                      $0.01/GB EACH WAY — $0.02 round trip
      same-AZ, private IP           free
      through a NAT gateway         $0.045/GB ON TOP of the above
      through an S3 gateway endpoint  free, and it replaces the NAT hop
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# CloudWatch
# ---------------------------------------------------------------------------

def bill_cloudwatch(log_gb: float = 0.0, retained_gb: float = 0.0,
                    insights_scanned_gb: float = 0.0, custom_metrics: int = 0,
                    bill: Optional[Bill] = None) -> Bill:
    """TODO: four lines, same pattern as bill_network.

    Observability is not free, and on a serverless bill it is routinely the
    third line down. $0.50/GB to INGEST is the number to remember: a debug log
    line you left on in a hot path costs more than the compute that emitted it,
    and ingest is 16x the price of keeping what you ingested.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# The whole account
# ---------------------------------------------------------------------------

def bill_account(cloud: Any, hours: float = HOURS_PER_MONTH, **kwargs: Any) -> Bill:
    """Walk a capstone Cloud and price everything in it.

    TODO: one Bill, passed into every meter so the line items accumulate in
    one place. s3, then every table, function, queue and topic, then kms, then
    optional network and cloudwatch blocks from kwargs.

    This is Cost Explorer in twenty lines: enumerate resources, meter each one,
    concatenate the line items, group by whatever question you are asking.
    """
    raise NotImplementedError


def per_unit_of_work(bill: Bill, units: float, label: str = "request") -> str:
    """Unit economics. The only cost number that survives a growth plan.

    TODO: cost per million `label`s, then the top five lines the same way.

    "$240/month" is meaningless without the denominator. "$0.000012 per upload"
    tells you the gross margin on a feature, tells you what a free tier costs
    you, and multiplies correctly when the traffic 10x's.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    """Once the checks pass, write a demo that MEASURES these, using the toy
    services from this directory rather than made-up numbers:

    1. S3, the versioning trap. Put 200 objects in a versioned bucket, delete
       all 200, then print stored_bytes before and after alongside
       list_objects. The console is empty; the billable bytes did not move.
       Then price the same 8 MB as 2,000 x 4 KB objects and as 8 x 1 MB
       objects across four storage classes, in $/GB-month. Standard-IA should
       come out at ~32x its sticker price on the small objects — and therefore
       MORE expensive than Standard, which is the opposite of why anyone moves
       data there. Finish with a days sweep on deep_archive showing the cost
       flat below 180 days.

    2. DynamoDB, the same table priced both ways, with the utilisation in the
       note. Predict the ratio first.

    3. Lambda, a real Function driven through the service, with the cold-start
       milliseconds pulled out of billed_ms as their own percentage.

    4. SNS and SQS. Publish with a filter policy in place and show the filtered
       deliveries as a zero line. Then the same queue traffic under three
       polling strategies, with work requests and idle requests in separate
       columns.

    5. KMS twice: one key with per-record GenerateDataKey calls, and 500 keys
       with no calls at all. The second is more expensive, which tells you
       which mistake costs more.

    6. Network, which nothing measured — 2 TB in, 500 GB out, 1 TB cross-AZ,
       three NAT gateways. Note that no counter anywhere in your code produced
       any of these numbers.

    Predict every table before running it.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
