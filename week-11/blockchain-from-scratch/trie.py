"""The Merkle-Patricia trie, and a state root that commits to everything.

Bitcoin commits to transactions; Ethereum commits to the whole world state, so any client can be handed a proof that an account has a balance -- or a proof that it does NOT exist. Exclusion proofs are the part a plain Merkle tree cannot do, and they are why the trie is a trie.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

class Trie:
    """TODO"""


def insert(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def get(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def root(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def proof(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def verify_proof(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


def exclusion_proof(*args, **kwargs) -> Any:
    """TODO"""
    raise NotImplementedError


