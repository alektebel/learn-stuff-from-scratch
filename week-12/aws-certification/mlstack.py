"""The SageMaker and Bedrock surface, mapped onto mechanisms you already built.

Real-time endpoints are lambda_svc.py concurrency plus ml-inference batching. Feature Store is dynamodb.py's partition key with a database-engine point-lookup behind it. Pipelines are the dependency graph from TODO 9.1. Batch transform, async inference and serverless inference are four points on one latency/cost curve. Naming them is recall; placing them on the curve is not.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def inference_option_for(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def endpoint_cost(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def feature_store_access(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def pipeline_order(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def training_instance_for(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def guardrail_check(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


