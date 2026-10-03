"""
Justification trees.

A successful s(CASP) query is not a boolean. It is a tree:

    node = {
        "atom": Atom,            # the call that succeeded
        "kind": "fact" | "rule" | "coinductive" | "negation",
        "subst": Subst,          # bindings used at this node
        "children": [node, ...], # body literals, in order
    }

This is the proof object. LINC will hang provenance off it.
Replay is: walk the tree. Traceable is: every leaf is a fact
in the program or a coinductive close or a neq.

DESIGN DECISION — the tree is the result, the substitution is
  a projection.
  Returning only the subst is an annotation scheme for a
  reasoner. You cannot ask "why does tweety not fly" of a
  substitution. CHOSEN: query_tree returns the root; the subst
  is root["subst"].
"""

from typing import Any, Dict, List, Optional

from program import Clause, Literal
from term import Subst

Node = Dict[str, Any]


def query_tree(goal: List[Literal], program: List[Clause],
               max_steps: int = 64) -> Optional[Node]:
    """Like coinductive.query, but every success builds a node.

    TODO: kind="coinductive" when you close an even loop (no
    children). kind="negation" when the call was a dual
    (predicate starts with 'not_'). kind="fact" when the
    matching clause had an empty body. kind="rule" otherwise.
    """
    raise NotImplementedError


def atoms_used(node: Node) -> List:
    """Every atom that appears as a fact-leaf, in preorder.

    TODO: this is the lineage of the proof. Tweety-not-flies
    must mention penguin(tweety). Opus-flies must mention
    sparrow(opus) and must NOT mention penguin(tweety).
    """
    raise NotImplementedError


def pretty(node: Node, indent: int = 0) -> str:
    """A readable dump. The checker does not grade format,
    only that pretty(tree) contains the predicate names of
    the fact leaves. Useful for the journal.
    """
    raise NotImplementedError
