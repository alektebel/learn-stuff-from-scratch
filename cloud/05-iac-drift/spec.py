"""
Declarative infrastructure specs and current state, as plain data.

Source: AWS CloudFormation documentation (`awsdocs:cloudformation`), the template
anatomy. A template's `Resources` declare each resource under a logical name with
a `Type`, its `Properties`, and an optional `DependsOn` list; a *stack* is the
deployed instance of that template. Restated from scratch: a **spec** document is
the desired set of resources, a **state** document is what is deployed right now,
and both are ordinary dicts - no AWS SDK, no credentials, no network, so the
whole module runs on `python3 file.py`.

DESIGN DECISION - one shape for the spec and for the state?
    Option A: keep the state in the shape a provider API returns (a flat list of
    physical resources with ARNs), and the spec in template shape, then write a
    translation layer between the two.
    Option B: parse both into the same `Resource` record.
    Chosen: B. The diff then compares like with like and there is no field-rename
    table that can itself drift. Cost: physical ids and provider metadata that a
    real state file carries are dropped, so two identical-looking resources cannot
    be told apart by id - only by logical name.

DESIGN DECISION - what makes two resources "the same"?
    The logical name identifies a resource; its *configuration* is `type` plus
    `properties`. Those are compared canonically (JSON with sorted keys), so
    writing the same properties in a different order is not drift. `depends_on`
    and `lifecycle` are planning metadata: they order actions, they are not
    deployed configuration. Chosen: `same_config` = type + canonical properties.
    Cost: a renamed logical id with identical configuration looks like a create
    plus a delete; `planner.py` is where that is recognised as a rename.

DESIGN DECISION - when is invalid input rejected?
    At parse time, loudly. A missing type, non-mapping properties, or a
    `depends_on` naming a resource that is not declared is a broken document, not
    drift - and a diff against a broken document would hide it. Chosen:
    `parse_document` raises `SpecError` for all of them. Cost: a template that
    legitimately depends on something managed outside the document (an imported
    parameter or a data source) is rejected unless the caller adds it; this module
    has no notion of data sources.

DESIGN DECISION - is a dependency cycle rejected at parse time?
    No. A cycle is a well-formed document and a *planning* condition: it only
    matters when you try to order actions. Chosen: `parse_document` accepts it and
    `find_cycle` reports it, so the planner owns the decision of what to do. Cost:
    a caller that parses but never plans must call `find_cycle` itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set


class SpecError(ValueError):
    """A spec or state document is not well-formed."""


class DependencyCycle(SpecError):
    """The dependency graph contains a cycle and cannot be ordered."""


@dataclass(frozen=True)
class Resource:
    """One logical resource in a spec or a state document.

    `properties` is the deployed configuration; `depends_on` and `stateful` are
    planning metadata and are deliberately excluded from `same_config`.
    """

    name: str
    type: str
    properties: Mapping[str, Any] = field(default_factory=dict)
    depends_on: Sequence[str] = ()
    stateful: bool = False

    def __str__(self) -> str:  # pragma: no cover - cosmetic only
        kind = "stateful" if self.stateful else "stateless"
        return f"{self.name} ({self.type}, {kind})"


def canonical(properties: Mapping[str, Any]) -> str:
    """A stable string form of a property document, with key order ignored.

    Two documents that differ only in insertion order serialise to the same
    string, so they compare equal. This is the whole basis of "no drift".
    """
    # TODO: Serialise the properties with json.dumps(..., sort_keys=True, separators=(',', ':')) so two dicts written with different key order produce the same string. Without sort_keys, an unchanged resource looks like drift.
    raise NotImplementedError("canonical")


def same_config(a: Resource, b: Resource) -> bool:
    """True when `a` and `b` deploy the same configuration.

    Compares `type` and canonical `properties` only; `depends_on`, `lifecycle`
    and the logical name are metadata and do not make a resource drift.
    """
    # TODO: True when the two resources have the same `type` AND the same `canonical(properties)`. Ignore the logical name, depends_on and lifecycle: those are planning metadata, not configuration.
    raise NotImplementedError("same_config")


def parse_resource(name: str, body: Mapping[str, Any]) -> Resource:
    """Validate one resource body and build a `Resource`.

    Raises `SpecError` if the body is not a mapping, has no string `type`, has
    non-mapping `properties`, a `depends_on` that is not a list of names, or a
    `lifecycle` other than `stateful`/`stateless`.
    """
    # TODO: Validate the body: a string `type`, a mapping `properties` (default {}), a list/tuple `depends_on` of non-empty strings, and a `lifecycle` of 'stateful'/'stateless'. Raise SpecError on anything else; return a Resource with depends_on as a tuple and stateful = (lifecycle == 'stateful').
    raise NotImplementedError("parse_resource")


def parse_document(document: Mapping[str, Any]) -> Dict[str, Resource]:
    """Parse a spec or state document into `{name: Resource}`.

    The document must be a mapping with a `resources` mapping. Every
    `depends_on` must name a declared resource; an unknown name is a `SpecError`
    rather than a silently ignored edge.
    """
    # TODO: Require a mapping with a `resources` mapping. Parse each entry with parse_resource, then reject any depends_on naming a resource that is not declared (SpecError). Iterate sorted() so the result order is deterministic.
    raise NotImplementedError("parse_document")


def dependents(resources: Mapping[str, Resource]) -> Dict[str, Set[str]]:
    """Map each resource to the set of resources that depend on it.

    `graph[b]` is every `a` with `b in a.depends_on`. Edges to names that are not
    in `resources` are ignored (they cannot be ordered anyway).
    """
    # TODO: Invert the depends_on edges: for every resource `a` and each `d` in a.depends_on, add `a` to graph[d]. Start every name at an empty set, and skip edges to names not in the document.
    raise NotImplementedError("dependents")


def find_cycle(resources: Mapping[str, Resource]) -> Optional[List[str]]:
    """Return a dependency cycle as a closed list, or `None` if there is none.

    The result starts and ends with the same name, e.g. `["a", "b", "a"]`; a
    self-dependency is `["a", "a"]`. Nodes are visited in sorted order so the
    answer is deterministic. This is a depth-first walk that marks nodes
    in-progress (GREY): meeting a GREY node means we have closed a loop.
    """
    # TODO: Depth-first search with three colours (white/grey/black) and an explicit stack. Meeting a GREY dependency closes a loop: return stack[index(dep):] + [dep]. Visit names and dependencies in sorted order so the reported cycle is deterministic. Return None when the walk finishes.
    raise NotImplementedError("find_cycle")


def _demo() -> None:
    spec_document = {
        "resources": {
            "vpc": {"type": "aws_vpc", "properties": {"cidr_block": "10.0.0.0/16"}},
            "subnet": {
                "type": "aws_subnet",
                "properties": {"cidr_block": "10.0.1.0/24"},
                "depends_on": ["vpc"],
            },
            "web": {
                "type": "aws_instance",
                "properties": {"ami": "ami-001", "instance_type": "t3.micro"},
                "depends_on": ["subnet"],
            },
        }
    }
    resources = parse_document(spec_document)
    print(f"parsed {len(resources)} resources: {sorted(resources)}")
    print("dependents:")
    for name, users in sorted(dependents(resources).items()):
        print(f"  {name:<7} <- {sorted(users)}")

    state_properties = {"instance_type": "t3.micro", "ami": "ami-001"}
    state_web = Resource("web", "aws_instance", state_properties)
    print(f"same config written in a different key order: "
          f"{same_config(resources['web'], state_web)}")

    cyclic = parse_document({
        "resources": {
            "a": {"type": "svc", "depends_on": ["b"]},
            "b": {"type": "svc", "depends_on": ["c"]},
            "c": {"type": "svc", "depends_on": ["a"]},
        }
    })
    print(f"cycle in a 3-node graph: {' -> '.join(find_cycle(cyclic) or [])}")
    print(f"cycle in an acyclic graph: {find_cycle(resources)}")


if __name__ == "__main__":
    _demo()
