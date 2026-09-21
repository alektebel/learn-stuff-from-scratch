"""Blocks, headers, Merkle trees, and the proof that a light client can check.

A block header commits to every transaction through one 32-byte root. That is what lets a phone verify a payment without the chain: an SPV proof is log2(n) hashes, and tampering with any transaction changes the root. Build the tree, build the proof, and measure the proof size against the block size.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

def merkle_root(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def merkle_proof(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def verify_proof(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def block_hash(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def validate_header(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def validate_chain(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


