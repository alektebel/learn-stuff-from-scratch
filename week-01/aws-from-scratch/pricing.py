"""
Pricing — the price sheet, and the arithmetic that turns usage into money.

The PRICES dict below is given to you: it is reference data, not an exercise,
and retyping a price list teaches nothing. Everything after it is yours to
write.

Learning Path:
1. per_unit and billable_units — the two rounding rules, which look the same
   and are not
2. tiered_cost — graduated tiers, where a wrong assumption is a four-figure
   mistake
3. Bill — line items, grouping, and the dominant line
4. Bill.scaled — separating fixed lines from variable ones, which is why cost
   advice flips with scale
5. FreeTier — an allowance applied afterwards, so you can see both numbers

Everything in this directory so far counted MECHANISM. This file counts MONEY,
which is a different unit and obeys different rules. A bill is not "usage times
a number": it is a set of independent DIMENSIONS, each with its own unit, its
own rounding rule, its own tier schedule, and — this is the part that surprises
people — its own idea of what an "operation" is.

DESIGN DECISION — a price sheet as data, or prices inlined at each call site?
  Inlining is shorter. But the whole point of studying cost is comparison:
  this region against that one, this storage class against that one, today's
  sheet against next quarter's. A comparison you cannot diff is not a
  comparison.
  CHOSEN: one nested dict, PRICES, with every number in one place, tagged with
  a region and a date. When a number here is stale you change one line, and
  every estimate in the directory moves with it.
  REJECTED: fetching live prices from the AWS Price List API. Correct, and it
  would make this file a networking exercise rather than a costing one.

DESIGN DECISION — store AWS's published rate, or a normalised per-unit price?
  AWS publishes "$0.005 per 1,000 PUT requests" and "$0.20 per 1M requests" and
  "$0.023 per GB-month" — three different denominators on one invoice.
  CHOSEN: store exactly what AWS publishes, denominator and all, and convert in
  exactly ONE place (`per_unit`). Almost every wrong cloud estimate you will
  ever see is off by a factor of 1,000 or 1,000,000, and it is always because
  someone retyped a rate into a different denominator than the one it came in.
  Keeping the published form means a typo is visible against the pricing page.

DESIGN DECISION — how to handle rounding?
  There are two completely different rules on one bill and they are easy to
  confuse:
    * PRO-RATA dimensions. "$0.005 per 1,000 PUTs" means 1 PUT costs
      $0.000005. You are not rounded up to a thousand.
    * QUANTISED dimensions. A 1.1 KB DynamoDB write costs 2 WCU, not 1.1. A
      100 KB object in S3 Standard-IA is billed as 128 KB. An object stored for
      1 day in Glacier Deep Archive is billed for 180 days.
  CHOSEN: `per_unit` for the first, `billable_units` for the second, with the
  quantisation always spelled out at the call site. Conflating them is how you
  get a bill 2x your estimate and no idea which line moved.

WHAT THIS IS NOT
  These prices are APPROXIMATE, us-east-1, and dated. They are here so the
  RATIOS and the SHAPES are right — NAT gateway versus gateway endpoint,
  provisioned versus on-demand, standard versus deep archive. Do not quote them
  at anyone. Check the current price list before you spend money.
"""

import math
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# The sheet
# ---------------------------------------------------------------------------

REGION = "us-east-1"
PRICE_SHEET_DATE = "2025-01"

GREY, RESET = "\033[90m", "\033[0m"

# AWS bills a "month" as 730 hours (365 * 24 / 12), not 720 and not 744.
HOURS_PER_MONTH = 730.0

PRICES: Dict[str, Any] = {
    # -- S3 -----------------------------------------------------------------
    # Storage is per GB-month. Requests are per 1,000. Note that the CHEAPER
    # the storage class, the MORE EXPENSIVE its requests — that inversion is
    # the entire trap in lifecycle policies.
    "s3": {
        "storage_gb_month": {
            # (class): (price, minimum_days, minimum_object_kb, retrieval_per_gb)
            "standard":       (0.023,   0,   0, 0.0),
            "standard_ia":    (0.0125, 30, 128, 0.01),
            "onezone_ia":     (0.01,   30, 128, 0.01),
            "glacier_ir":     (0.004,  90, 128, 0.03),
            "glacier_flex":   (0.0036, 90,  40, 0.01),
            "deep_archive":   (0.00099, 180, 40, 0.02),
        },
        # Tiered by total stored volume, Standard class only.
        "storage_tiers": [(50_000.0, 0.023), (500_000.0, 0.022), (math.inf, 0.021)],
        "put_per_1000": {"standard": 0.005, "standard_ia": 0.01, "onezone_ia": 0.01,
                         "glacier_ir": 0.02, "glacier_flex": 0.03,
                         "deep_archive": 0.05},
        "get_per_1000": {"standard": 0.0004, "standard_ia": 0.001, "onezone_ia": 0.001,
                         "glacier_ir": 0.01, "glacier_flex": 0.0004,
                         "deep_archive": 0.0004},
        "list_per_1000": 0.005,      # LIST is priced as a PUT-class request
        "delete_per_1000": 0.0,      # DELETE is free. The STORAGE it fails to
                                     # free is not.
        "lifecycle_transition_per_1000": 0.01,
    },

    # -- DynamoDB -----------------------------------------------------------
    # Two billing modes for identical behaviour. The crossover between them is
    # the single most valuable number in this file.
    "dynamodb": {
        "provisioned_wcu_hour": 0.00065,
        "provisioned_rcu_hour": 0.00013,
        "on_demand_write_per_million": 1.25,
        "on_demand_read_per_million": 0.25,
        "storage_gb_month": 0.25,
        "free_storage_gb": 25.0,
        "wcu_item_kb": 1.0,          # one WCU covers 1 KB, ROUNDED UP
        "rcu_item_kb": 4.0,          # one RCU covers 4 KB strongly consistent
        "backup_gb_month": 0.10,
        "restore_per_gb": 0.15,
        "stream_read_per_100k": 0.02,
    },

    # -- Lambda -------------------------------------------------------------
    "lambda": {
        "request_per_million": 0.20,
        "gb_second_x86": 0.0000166667,
        "gb_second_arm": 0.0000133334,
        "billing_granularity_ms": 1.0,
        "free_requests_per_month": 1_000_000.0,
        "free_gb_seconds_per_month": 400_000.0,
    },

    # -- SQS / SNS / EventBridge -------------------------------------------
    # Priced per API REQUEST, not per message. One request carries up to ten
    # messages, which makes batching a straight 10x lever.
    "sqs": {
        "standard_per_million": 0.40,
        "fifo_per_million": 0.50,
        "free_requests_per_month": 1_000_000.0,
        "messages_per_batch": 10,
        "request_payload_kb": 64,    # a 200 KB message = 4 billable requests
    },
    "sns": {
        "publish_per_million": 0.50,
        # Delivery price depends entirely on the protocol, and spans five
        # orders of magnitude.
        "delivery_per_million": {
            "sqs": 0.0, "lambda": 0.0, "http": 0.60, "email": 20.0,
            "sms": 6450.0,           # ~$0.00645 each in the US
        },
        "free_publishes_per_month": 1_000_000.0,
    },
    "eventbridge": {
        "custom_event_per_million": 1.00,
        "aws_event_per_million": 0.0,     # service events are free to receive
        "archive_gb_month": 0.10,
    },

    # -- KMS ----------------------------------------------------------------
    # A fixed monthly charge per key, plus a per-request charge. Both matter,
    # and which one dominates tells you whether you have a key-sprawl problem
    # or a call-pattern problem.
    "kms": {
        "key_month": 1.00,
        "request_per_10000": 0.03,
        "free_requests_per_month": 20_000.0,
    },

    # -- Network ------------------------------------------------------------
    # The dimension nobody budgets for. Read the asymmetry carefully: bytes IN
    # are free, bytes OUT are not, and bytes sideways (cross-AZ) are charged in
    # BOTH directions.
    "network": {
        "internet_out_tiers": [(10_240.0, 0.09), (51_200.0, 0.085),
                               (153_600.0, 0.07), (math.inf, 0.05)],
        "internet_out_free_gb": 100.0,
        "internet_in_per_gb": 0.0,
        "cross_az_per_gb": 0.01,          # charged on EACH side: 0.02 round trip
        "same_az_private_per_gb": 0.0,
        "cross_region_per_gb": 0.02,
        "nat_gateway_hour": 0.045,
        "nat_gateway_per_gb": 0.045,      # ON TOP of any transfer charge
        "gateway_endpoint_hour": 0.0,     # S3 and DynamoDB: free, forever
        "gateway_endpoint_per_gb": 0.0,
        "interface_endpoint_hour": 0.01,  # per AZ
        "interface_endpoint_per_gb": 0.01,
        "public_ipv4_hour": 0.005,        # every attached address, since 2024
    },

    # -- Observability ------------------------------------------------------
    # Left in because it is routinely the third-largest line on a serverless
    # bill and nobody planned for it.
    "cloudwatch": {
        "logs_ingest_per_gb": 0.50,
        "logs_storage_gb_month": 0.03,
        "logs_insights_scan_per_gb": 0.005,
        "custom_metric_month": 0.30,
        "api_request_per_1000": 0.01,
    },

    # -- Free ---------------------------------------------------------------
    # Not a rounding error: these genuinely cost nothing, and it is worth
    # knowing which, because the ones that cost nothing are the ones you should
    # be using MORE of.
    "free": ["iam", "sts", "vpc", "security_groups", "network_acls",
             "route_tables", "s3_gateway_endpoint", "dynamodb_gateway_endpoint",
             "sqs_to_lambda_delivery", "cloudformation", "auto_scaling",
             "kms_aws_managed_key_storage"],
}


def price(*path: str) -> Any:
    """Look up a price by path, failing loudly on a typo.

    `PRICES["lambda"]["gb_second"]` returns None-ish confusion if you spell it
    wrong; this raises. Cost code that silently reads a missing price as zero
    produces an estimate that is confidently, quietly, wrong.
    """
    node: Any = PRICES
    for step in path:
        if not isinstance(node, dict) or step not in node:
            raise KeyError(f"no price at {'.'.join(path)} (failed at {step!r})")
        node = node[step]
    return node


# ---------------------------------------------------------------------------
# The two rounding rules
# ---------------------------------------------------------------------------

def per_unit(published_rate: float, per: float) -> float:
    """Convert a published rate into a price for ONE unit.

    per_unit(0.20, 1_000_000) -> 0.0000002 per Lambda request
    per_unit(0.005, 1_000)    -> 0.000005  per S3 PUT

    TODO: divide, and raise ValueError on a non-positive denominator.

    This is the only place a denominator is allowed to appear. Every
    factor-of-1000 error in a cost model happens because someone did this
    conversion twice, or not at all — so do it here, once, and never inline a
    "/1000" anywhere else in the directory.
    """
    raise NotImplementedError


def billable_units(quantity: float, unit_size: float,
                   minimum_units: float = 1.0) -> float:
    """Quantise: how many whole units a quantity is billed as.

    billable_units(1.1, 1.0) -> 2.0    a 1.1 KB DynamoDB write costs 2 WCU
    billable_units(0.2, 1.0) -> 1.0    a 200-byte write still costs 1 WCU
    billable_units(5.0, 4.0) -> 2.0    a 5 KB strongly consistent read: 2 RCU

    TODO: ceiling division, floored at minimum_units. Subtract a small epsilon
    before the ceiling or float representation will bill an exact 4.0 KB item
    as 2 units about as often as it does not.

    Note what this means for schema design: splitting one 4 KB item into four
    1 KB items quadruples your write cost for identical data. Item size is a
    pricing decision disguised as a modelling decision.
    """
    raise NotImplementedError


def tiered_cost(quantity: float, tiers: Sequence[Tuple[float, float]]) -> float:
    """Graduated tiers: each tier prices only the portion that falls in it.

    tiers is [(upper_bound, price_per_unit), ...] with the last bound infinite.
    150 GB against [(100, 0.09), (inf, 0.05)] costs 100*0.09 + 50*0.05, NOT
    150*0.05 and NOT 150*0.09.

    TODO: walk the tiers, taking min(remaining, upper - previous) from each.

    AWS uses graduated tiers everywhere except a handful of "your whole volume
    moves to the cheaper rate" deals. Assuming the wrong one at 10 TB of egress
    is a four-figure mistake, and it is the single most common error in a
    spreadsheet estimate.
    """
    raise NotImplementedError


def prorate(monthly_cost: float, hours: float) -> float:
    """TODO: a monthly charge for a partial month. Hourly resources are billed
    by the hour they exist, not by the month they were created in."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# The bill
# ---------------------------------------------------------------------------

class LineItem(NamedTuple):
    service: str
    dimension: str
    quantity: float
    unit: str
    unit_price: float
    cost: float
    note: str = ""


class Bill:
    """A list of line items you can add up, group, sort and explain.

    DESIGN DECISION — a running total, or a list of line items?
      A running float is one line of code and answers "how much".
      CHOSEN: the list, because "how much" is never the interesting question.
      "Which line is 80% of it" is, and you cannot recover that from a total.
      This is exactly why AWS's own Cost Explorer is a group-by tool rather
      than a number.
    """

    def __init__(self, name: str = "account", period_hours: float = HOURS_PER_MONTH):
        self.name = name
        self.period_hours = period_hours
        self.items: List[LineItem] = []

    # -- building -----------------------------------------------------------

    def add(self, service: str, dimension: str, quantity: float, unit: str,
            unit_price: float, note: str = "") -> LineItem:
        """TODO: append a LineItem with cost = quantity * unit_price, and
        return it. Keep the note — it is where a meter explains itself, and a
        line item with a number and no explanation is how a cost review turns
        into an argument about whose number is right."""
        raise NotImplementedError

    def add_tiered(self, service: str, dimension: str, quantity: float,
                   unit: str, tiers: Sequence[Tuple[float, float]],
                   note: str = "") -> LineItem:
        """TODO: cost from tiered_cost; store the EFFECTIVE unit price
        (cost / quantity) so the line still reads sensibly."""
        raise NotImplementedError

    def extend(self, other: "Bill") -> "Bill":
        """TODO: absorb another bill's line items. Return self."""
        raise NotImplementedError

    # -- reading ------------------------------------------------------------

    @property
    def total(self) -> float:
        raise NotImplementedError

    def by_service(self) -> Dict[str, float]:
        """TODO: {service: cost}, sorted most expensive first."""
        raise NotImplementedError

    def by_dimension(self) -> List[LineItem]:
        """TODO: every line item, most expensive first."""
        raise NotImplementedError

    def dominant(self) -> Optional[LineItem]:
        """TODO: the single biggest line, or None on an empty bill.

        Optimise this one or optimise nothing. A 90% saving on a line worth 2%
        of the bill is a 1.8% saving, and it cost you a week. Cost work is
        Amdahl's law with dollars.
        """
        raise NotImplementedError

    def share(self, item: LineItem) -> float:
        """TODO: this line as a fraction of the total. Guard the empty bill."""
        raise NotImplementedError

    def scaled(self, factor: float, name: Optional[str] = None) -> "Bill":
        """This bill at `factor` times the usage — for VARIABLE lines only.

        TODO:
        1. New Bill, same period.
        2. For each item: if _is_fixed(item), carry it through UNCHANGED.
           Otherwise multiply both quantity and cost by factor.

        Fixed lines (a NAT gateway hour, a KMS key month, provisioned capacity,
        an idle poller) do not scale with traffic. That asymmetry is the whole
        reason a small workload's bill looks nothing like a large one's: at low
        volume you are paying for the fixed lines, at high volume for the
        variable ones, and the advice flips at the crossover. A `scaled` that
        multiplies everything hides exactly the effect you built it to see.
        """
        raise NotImplementedError

    # -- printing -----------------------------------------------------------

    def format(self, top: Optional[int] = None, min_share: float = 0.0,
               notes: bool = True) -> str:
        """TODO: an aligned table — line, quantity, cost, share, and a bar.

        Worth the effort. Almost every conclusion in billing.py and optimize.py
        is something you SEE in this table rather than something you compute,
        and a bill you cannot read at a glance is a bill nobody reads.

        Print the note under its line when `notes` is set, and finish with a
        TOTAL row.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Bill {self.name} {money(self.total)} ({len(self.items)} lines)>"


_FIXED_DIMENSIONS = ("key-months", "nat-gateway-hours", "endpoint-hours",
                     "provisioned-wcu-hours", "provisioned-rcu-hours",
                     "public-ipv4-hours", "custom-metrics",
                     "idle-poll-requests")


def _is_fixed(item: LineItem) -> bool:
    return item.dimension in _FIXED_DIMENSIONS


def money(amount: float) -> str:
    """Print small money honestly.

    TODO: "$0" for zero; "$1,234.56" at or above a cent; six decimal places
    below it.

    A serverless line item is routinely $0.0000004. Rounding that to $0.00 and
    then summing a hundred of them is how a cost model reports zero for a
    workload that costs real money — and it is why the first cost dashboard
    anyone builds says everything is free.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# The free tier
# ---------------------------------------------------------------------------

class FreeTier:
    """Monthly allowances, applied as a subtraction AFTER the bill is built.

    DESIGN DECISION — subtract the free tier inside each meter, or afterwards?
      Inside is what the invoice looks like. Afterwards is what you want,
      because a bill that reads $0.00 teaches you nothing about the shape of
      your spend, and the free tier is a cliff: you learn nothing, then you
      learn everything at once.
      CHOSEN: build the true bill first, then optionally apply the allowance,
      and keep BOTH numbers. The gap between them is your runway.
    """

    ALLOWANCES = {
        ("lambda", "requests"): 1_000_000.0,
        ("lambda", "gb-seconds"): 400_000.0,
        ("sqs", "requests"): 1_000_000.0,
        ("sns", "publishes"): 1_000_000.0,
        ("kms", "requests"): 20_000.0,
        ("dynamodb", "storage-gb-months"): 25.0,
        ("network", "internet-out-gb"): 100.0,
    }

    @classmethod
    def apply(cls, bill: Bill) -> Tuple[Bill, float]:
        """Return (discounted bill, amount waived).

        TODO:
        1. Copy the allowance table — it is consumed as you go, and an
           allowance spent on one line is not available to the next.
        2. For each line, cover min(allowance, quantity) units at zero, bill
           the rest, and accumulate what you waived.
        3. Leave lines with no allowance untouched.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these five things:

    1. The two rounding rules side by side: one S3 PUT priced pro-rata, and a
       table of item size -> WCU showing that 0.3 KB and 1.0 KB cost the same
       while 1.1 KB costs double.

    2. Graduated tiers versus the naive "everything at the top rate" answer,
       across 100 GB to 300 TB of egress. Print the gap.

    3. A bill with seven or eight lines from different services, formatted, and
       then its dominant line. Pick quantities where the answer is a surprise
       — 20M S3 PUTs cost 25x what the 20M Lambda invocations that issued them
       cost, and nobody expects that.

    4. That same bill at 0.001x through 100x traffic, with the fixed portion in
       its own column. Watch the fixed share go from 99% to 0.2%. This is why
       "should we use X" has no answer without a volume attached.

    5. The free tier applied at several scales. Note how much it hides.

    Predict each number before you run it. A result that surprises you is a gap
    in your model that passing tests did not reveal.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
