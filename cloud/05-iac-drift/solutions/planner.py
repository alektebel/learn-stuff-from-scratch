"""
The plan: turn a spec and a state document into ordered create/update/delete
actions.

Source: AWS CloudFormation documentation (`awsdocs:cloudformation`) - change sets
and stack-update behaviour: creates run after the resources they depend on, and
deletes run after the resources that depend on them (dependents are torn down
first). Restated from scratch: diff the desired resources against the deployed
ones, then topologically order the actions so each resource is built after what
it needs and destroyed before what it feeds.

DESIGN DECISION - one recursive pass, or diff then order?
    Option A: walk the spec recursively and emit actions as you go.
    Option B: `compute_drift` produces an unordered set of actions, and
    `order_actions` imposes the dependencies.
    Chosen: B. The diff is a pure set comparison that is trivial to test (it must
    be empty when the documents match), and ordering is a separate graph problem
    with its own limit case (a cycle). Cost: an action carries only type/name, so
    the ordering step has to rebuild the dependency edges instead of reading them
    off the recursion.

DESIGN DECISION - in what order do unrelated actions run?
    The topological order only fixes what the dependencies require. To stay
    deterministic - and to make the rename limit case bite - the root actions are
    visited in a fixed priority: deletes, then updates, then creates, with ties
    broken by name. Chosen: destroy-first by *default*, overridden by an explicit
    edge for a stateful rename. Cost: a stateless rename is torn down before it is
    rebuilt, which briefly frees its identifier but is otherwise harmless.

DESIGN DECISION - is a rename two actions or one?
    A renamed logical id is absent under the new name and present under the old
    one, so the diff necessarily sees a create and a delete. For a *stateful*
    resource (a database, a bucket) running the delete first destroys the data; a
    create-before-destroy flow rebuilds first and swaps. Chosen: detect the pair
    by identical configuration and, when either side is stateful, pin the create
    before the delete. Cost: matching on identical configuration misses a rename
    that also changes a property - that correctly shows up as an unrelated create
    and delete, which is what the diff actually says.

DESIGN DECISION - how is a dependency cycle handled?
    A cycle cannot be ordered, and a recursive sort that follows it would recurse
    forever. `plan` asks `find_cycle` first and raises `DependencyCycle` naming
    the loop; the ordering walk also marks in-progress nodes and raises if it
    meets one, so a cycle introduced while ordering cannot loop either. Chosen:
    report, do not loop. Cost: `plan` returns nothing for a cyclic document; the
    caller must fix the template.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple

from spec import (
    DependencyCycle,
    Resource,
    dependents,
    find_cycle,
    parse_document,
    same_config,
)

__all__ = ["Action", "compute_drift", "rename_pairs", "order_actions", "plan"]

#: Root-visit priority when the dependencies leave the order free. Deletes first,
#: then updates, then creates; ties are broken by action name then resource name.
_ORDER = {"delete": 0, "update": 1, "create": 2}


@dataclass(frozen=True)
class Action:
    """One step of a plan. `action` is `create`, `update` or `delete`."""

    action: str
    name: str
    type: str
    changes: Sequence[str] = ()
    replacement_of: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - cosmetic only
        if self.action == "update":
            extra = f" ({', '.join(self.changes)})" if self.changes else ""
        elif self.replacement_of:
            extra = f" (rename of {self.replacement_of})"
        else:
            extra = ""
        return f"{self.action} {self.name}{extra}"


def compute_drift(
    spec: Mapping[str, Resource], state: Mapping[str, Resource]
) -> List[Action]:
    """The unordered diff between the desired and the deployed resources.

    Names only in `spec` are creates, names only in `state` are deletes, and
    names in both whose configuration changed are updates carrying the changed
    property keys. Equal names with equal configuration produce nothing, so when
    the two documents match the result is empty. Creates that pair with a removed
    resource are annotated with `replacement_of`.
    """
    actions: List[Action] = []
    for name in sorted(set(spec) | set(state)):
        if name in spec and name not in state:
            actions.append(Action("create", name, spec[name].type))
        elif name in state and name not in spec:
            actions.append(Action("delete", name, state[name].type))
        elif not same_config(spec[name], state[name]):
            property_keys = set(spec[name].properties) | set(state[name].properties)
            changed = tuple(sorted(
                key for key in property_keys
                if spec[name].properties.get(key) != state[name].properties.get(key)
            ))
            actions.append(Action("update", name, spec[name].type, changes=changed))

    replacements = {new: old for new, old, _ in rename_pairs(spec, state)}
    if replacements:
        actions = [
            replace(action, replacement_of=replacements[action.name])
            if action.action == "create" and action.name in replacements
            else action
            for action in actions
        ]
    return actions


def rename_pairs(
    spec: Mapping[str, Resource], state: Mapping[str, Resource]
) -> List[Tuple[str, str, bool]]:
    """Match removed resources with added ones of identical configuration.

    Returns `(new_name, old_name, stateful)` for each match, greedily pairing in
    sorted name order and using each removed resource once. `stateful` is true if
    either the desired or the deployed side declares a stateful lifecycle.
    """
    removed = sorted(name for name in state if name not in spec)
    added = sorted(name for name in spec if name not in state)
    pairs: List[Tuple[str, str, bool]] = []
    taken: Set[str] = set()
    for new in added:
        for old in removed:
            if old in taken:
                continue
            if same_config(spec[new], state[old]):
                stateful = spec[new].stateful or state[old].stateful
                pairs.append((new, old, stateful))
                taken.add(old)
                break
    return pairs


def _sort_key(key: Tuple[str, str]) -> Tuple[int, str, str]:
    action, name = key
    return (_ORDER[action], action, name)


def order_actions(
    actions: Sequence[Action],
    spec: Mapping[str, Resource],
    state: Mapping[str, Resource],
) -> List[Action]:
    """Topologically order the actions by dependency.

    Edges: a create/update follows the create/update of everything it depends on;
    a delete precedes the delete of everything that depends on it; and a stateful
    rename pins its create before its delete. Unrelated actions are visited by
    `_sort_key` (deletes first). Raises `DependencyCycle` if the action graph
    itself contains a loop.
    """
    action_of: Dict[Tuple[str, str], Action] = {
        (action.action, action.name): action for action in actions
    }
    prereqs: Dict[Tuple[str, str], Set[Tuple[str, str]]] = {
        key: set() for key in action_of
    }

    def add(before: Tuple[str, str], after: Tuple[str, str]) -> None:
        if before in action_of and after in action_of and before != after:
            prereqs[after].add(before)

    # A resource is built after the resources it depends on.
    for key, action in action_of.items():
        if action.action in ("create", "update"):
            for dep in spec[action.name].depends_on:
                add(("create", dep) if ("create", dep) in action_of else ("update", dep), key)

    # A resource is destroyed before the resources that depend on it.
    dependents_of = dependents(state)
    for key, action in action_of.items():
        if action.action == "delete":
            for user in dependents_of.get(action.name, ()):
                add(("delete", user), key)

    # A stateful rename is create-before-destroy, not the other way round.
    for new, old, stateful in rename_pairs(spec, state):
        if stateful:
            add(("create", new), ("delete", old))

    order: List[Tuple[str, str]] = []
    done: Set[Tuple[str, str]] = set()
    active: List[Tuple[str, str]] = []
    active_set: Set[Tuple[str, str]] = set()

    def visit(key: Tuple[str, str]) -> None:
        if key in done:
            return
        if key in active_set:
            start = active.index(key)
            names = [name for _, name in active[start:]] + [key[1]]
            raise DependencyCycle("dependency cycle: " + " -> ".join(names))
        active.append(key)
        active_set.add(key)
        for before in sorted(prereqs[key], key=_sort_key):
            visit(before)
        active.pop()
        active_set.discard(key)
        done.add(key)
        order.append(key)

    for key in sorted(action_of, key=_sort_key):
        visit(key)
    return [action_of[key] for key in order]


def plan(
    spec_document: Mapping[str, object], state_document: Mapping[str, object]
) -> List[Action]:
    """Parse both documents and return the ordered plan.

    An empty list means the deployed state already matches the spec. Raises
    `SpecError` for a malformed document and `DependencyCycle` for a cyclic
    dependency graph - a cycle is reported before any ordering is attempted, so
    it is caught even when no action would have been produced.
    """
    spec = parse_document(spec_document)
    state = parse_document(state_document)

    for resources in (spec, state):
        cycle = find_cycle(resources)
        if cycle:
            raise DependencyCycle("dependency cycle: " + " -> ".join(cycle))

    actions = compute_drift(spec, state)
    return order_actions(actions, spec, state)


def _demo() -> None:
    spec_document = {
        "resources": {
            "vpc": {"type": "aws_vpc", "properties": {"cidr_block": "10.0.0.0/16"}},
            "web": {
                "type": "aws_instance",
                "properties": {"ami": "ami-new", "instance_type": "t3.micro"},
                "depends_on": ["vpc"],
            },
            "cache": {
                "type": "aws_elasticache_cluster",
                "properties": {"node_type": "cache.t3.micro"},
                "depends_on": ["vpc"],
            },
        }
    }
    state_document = {
        "resources": {
            "vpc": {"type": "aws_vpc", "properties": {"cidr_block": "10.0.0.0/16"}},
            "web": {
                "type": "aws_instance",
                "properties": {"ami": "ami-old", "instance_type": "t3.micro"},
                "depends_on": ["vpc"],
            },
            "legacy": {"type": "aws_s3_bucket", "properties": {"bucket": "old"}},
        }
    }
    print("plan for a spec with one create, one update and one delete:")
    for index, action in enumerate(plan(spec_document, state_document), start=1):
        print(f"  {index}. {action}")

    print(f"\nidempotent when state == spec: "
          f"{plan(spec_document, spec_document) == []}")

    rename_spec = {"resources": {
        "db-prod": {
            "type": "aws_db_instance",
            "properties": {"engine": "postgres"},
            "lifecycle": "stateful",
        },
    }}
    rename_state = {"resources": {
        "db": {
            "type": "aws_db_instance",
            "properties": {"engine": "postgres"},
            "lifecycle": "stateful",
        },
    }}
    order = [(a.action, a.name) for a in plan(rename_spec, rename_state)]
    print(f"stateful rename db -> db-prod: {order}  "
          f"create first: {order[0] == ('create', 'db-prod')}")

    cyclic = {"resources": {
        "a": {"type": "svc", "properties": {"x": 1}, "depends_on": ["b"]},
        "b": {"type": "svc", "properties": {"x": 1}, "depends_on": ["a"]},
    }}
    try:
        plan(cyclic, cyclic)
        print("cycle: no error (wrong)")
    except DependencyCycle as exc:
        print(f"cycle: {exc}")


if __name__ == "__main__":
    _demo()
