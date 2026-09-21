"""
Capstone — a serverless application from the pieces. Complete Solution.

    upload to S3
      -> S3 event notification
        -> SNS topic (fanout, with a filter policy)
          -> SQS queue (durable buffer)
            -> Lambda (concurrency-limited)
              -> DynamoDB (partition-keyed, throttleable)
    with KMS encrypting the payload and IAM gating every single call.

The point is not that it works. It is that the FAILURES compose too, and each
one is a mechanism you built and can now recognise anywhere:

  IAM denies      -> the call never happens, and the error names the statement
  Lambda throttle -> events queue instead of being lost, because SQS buffers
  Dynamo throttle -> a hot partition key, not a capacity shortage
  Poison event    -> retried, then dead-lettered rather than retried forever
"""

from typing import Any, Dict, List, Optional

from dynamodb import Table, ThroughputExceeded
from iam import ALLOW, DENY, Credentials, Policy, Statement, evaluate
from kms import KMS, EnvelopeCipher
from lambda_svc import Function, LambdaService, Throttled
from s3 import S3
from sns import Topic
from sqs import Queue


class AccessDenied(Exception):
    pass


class Cloud:
    """A tiny account: services, plus the IAM check every call goes through."""

    def __init__(self):
        self.s3 = S3()
        self.kms = KMS()
        self.lambda_service = LambdaService(account_concurrency=5)
        self.tables: Dict[str, Table] = {}
        self.topics: Dict[str, Topic] = {}
        self.queues: Dict[str, Queue] = {}
        self.audit: List[str] = []

    def authorize(self, credentials: Credentials, action: str,
                  resource: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Every call goes through this. In a real account it is the ONLY thing
        standing between a bug and someone else's data."""
        raise NotImplementedError


def build() -> Dict[str, Any]:
    raise NotImplementedError


def upload(system: Dict[str, Any], credentials: Credentials, tenant: str,
           key: str, body: bytes, content_type: str = "application/pdf",
           now: float = 0.0) -> Dict[str, Any]:
    """The full write path, with every gate in place."""
    raise NotImplementedError


def drain(system: Dict[str, Any], now: float = 0.0,
          batch: int = 10) -> Dict[str, int]:
    """Poll the queue and invoke the function — an event source mapping."""
    raise NotImplementedError


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS the behaviour.

    The solution's demo is the reference — but write yours first and predict
    the numbers before running it. A result that surprises you is a gap in your
    model that passing tests did not reveal.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
