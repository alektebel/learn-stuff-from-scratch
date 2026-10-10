"""
Progress checker for the infrastructure-as-code templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.
"""

import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, Dict, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _idempotent_pair() -> Tuple[Dict, Dict]:
    """A spec and a state that are equal, but written with property keys in a
    different order. Reordering keys is not drift, so the plan must be empty."""
    spec = {
        "resources": {
            "vpc": {"type": "aws_vpc", "properties": {"cidr_block": "10.0.0.0/16"}},
            "subnet": {
                "type": "aws_subnet",
                "properties": {"cidr_block": "10.0.1.0/24", "map_public": True},
                "depends_on": ["vpc"],
            },
            "web": {
                "type": "aws_instance",
                "properties": {"ami": "ami-001", "instance_type": "t3.micro"},
                "depends_on": ["subnet"],
            },
        }
    }
    state = {
        "resources": {
            "web": {
                "type": "aws_instance",
                "properties": {"instance_type": "t3.micro", "ami": "ami-001"},
                "depends_on": ["subnet"],
            },
            "subnet": {
                "type": "aws_subnet",
                "properties": {"map_public": True, "cidr_block": "10.0.1.0/24"},
                "depends_on": ["vpc"],
            },
            "vpc": {"type": "aws_vpc", "properties": {"cidr_block": "10.0.0.0/16"}},
        }
    }
    return spec, state


# ---------------------------------------------------------------------------
# Steps 1-3: spec.py
# ---------------------------------------------------------------------------

def check_spec_parse() -> None:
    from spec import Resource, SpecError, parse_document

    document = {
        "resources": {
            "vpc": {"type": "aws_vpc", "properties": {"cidr_block": "10.0.0.0/16"}},
            "subnet": {"type": "aws_subnet", "properties": {}, "depends_on": ["vpc"]},
        }
    }
    resources = parse_document(document)
    assert set(resources) == {"vpc", "subnet"}, (
        f"parse_document returned {sorted(resources)}; every declared resource must be parsed")
    assert isinstance(resources["vpc"], Resource), (
        "parse_document must return Resource records, not raw dicts")
    assert resources["vpc"].type == "aws_vpc", "the 'type' field was not read"
    assert resources["vpc"].properties == {"cidr_block": "10.0.0.0/16"}, "properties were not read"
    assert resources["subnet"].depends_on == ("vpc",), (
        f"depends_on should be ('vpc',), got {resources['subnet'].depends_on!r}")

    malformed = {
        "no resources mapping": {},
        "resources is not a mapping": {"resources": []},
        "missing type": {"resources": {"x": {"properties": {}}}},
        "unknown dependency": {"resources": {"x": {"type": "t", "depends_on": ["ghost"]}}},
        "depends_on is a string, not a list": {"resources": {"x": {"type": "t", "depends_on": "y"}}},
        "properties is not a mapping": {"resources": {"x": {"type": "t", "properties": []}}},
        "bad lifecycle": {"resources": {"x": {"type": "t", "lifecycle": "immortal"}}},
    }
    for label, bad in malformed.items():
        try:
            parse_document(bad)
        except SpecError:
            continue
        raise AssertionError(
            f"parse_document accepted malformed input ({label}): {bad!r}. "
            "A bad document is a SpecError, not silent drift.")


def check_spec_canonical() -> None:
    from spec import Resource, canonical, dependents, parse_document, same_config

    assert canonical({"a": 1, "b": 2}) == canonical({"b": 2, "a": 1}), (
        "canonical() differs for the same properties written in a different key order: "
        "sort the keys, or an equal state is reported as drift")
    web = Resource("web", "aws_instance", {"ami": "a", "instance_type": "t"})
    same = Resource("web", "aws_instance", {"instance_type": "t", "ami": "a"})
    assert same_config(web, same), (
        "same_config() says equal resources differ when their property keys are reordered")
    assert not same_config(web, Resource("web", "aws_instance", {"ami": "z", "instance_type": "t"})), (
        "same_config() ignored a changed property value")
    assert not same_config(web, Resource("web", "aws_vpc", {"ami": "a", "instance_type": "t"})), (
        "same_config() ignored a changed resource type")
    assert same_config(web, Resource("web2", "aws_instance",
                                     {"ami": "a", "instance_type": "t"}, ("x",), True)), (
        "depends_on/lifecycle are planning metadata, not configuration: changing them is not drift")

    resources = parse_document({
        "resources": {
            "vpc": {"type": "vpc"},
            "subnet": {"type": "subnet", "depends_on": ["vpc"]},
            "web": {"type": "web", "depends_on": ["vpc", "subnet"]},
        }
    })
    graph = dependents(resources)
    assert graph["vpc"] == {"subnet", "web"}, f"dependents(vpc) = {graph['vpc']}, expected subnet and web"
    assert graph["subnet"] == {"web"}, f"dependents(subnet) = {graph['subnet']}, expected web"
    assert graph["web"] == set(), "nothing depends on web"


def check_spec_find_cycle() -> None:
    from spec import find_cycle, parse_document

    cyclic = parse_document({
        "resources": {
            "a": {"type": "svc", "depends_on": ["b"]},
            "b": {"type": "svc", "depends_on": ["c"]},
            "c": {"type": "svc", "depends_on": ["a"]},
        }
    })
    loop = find_cycle(cyclic)
    assert loop is not None, (
        "find_cycle() missed a three-node cycle a -> b -> c -> a; a DFS must mark nodes "
        "in-progress and report the loop instead of returning None")
    assert loop[0] == loop[-1], f"a cycle must be a closed list (start == end), got {loop}"
    assert set(loop[:-1]) == {"a", "b", "c"}, f"the cycle should span a, b and c, got {loop}"

    acyclic = parse_document({
        "resources": {
            "a": {"type": "svc"},
            "b": {"type": "svc", "depends_on": ["a"]},
            "c": {"type": "svc", "depends_on": ["a", "b"]},
        }
    })
    assert find_cycle(acyclic) is None, "find_cycle() invented a cycle in an acyclic graph"

    self_loop = parse_document({"resources": {"a": {"type": "svc", "depends_on": ["a"]}}})
    assert find_cycle(self_loop) == ["a", "a"], (
        f"a self-dependency is a cycle ['a', 'a'], got {find_cycle(self_loop)}")


# ---------------------------------------------------------------------------
# Steps 4-8: planner.py
# ---------------------------------------------------------------------------

def check_idempotent() -> None:
    """Accept 1: with state equal to spec the plan is empty."""
    from planner import plan

    spec, state = _idempotent_pair()
    actions = plan(spec, state)
    assert actions == [], (
        f"state equal to spec must give an empty plan, got {[str(a) for a in actions]}. "
        "If an update appears, the two property dicts were written with different key order - "
        "compare them canonically (sorted keys), not by string identity.")


def check_drift() -> None:
    """Accept 2: a changed attribute updates, a removed resource deletes."""
    from planner import plan

    spec = {
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
    state = {
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
    actions = plan(spec, state)
    kinds = {(action.action, action.name) for action in actions}
    assert ("update", "web") in kinds, (
        f"a changed attribute (web.ami) must produce an update; got {sorted(kinds)}")
    assert ("create", "cache") in kinds, (
        f"a resource only in the spec must produce a create; got {sorted(kinds)}")
    assert ("delete", "legacy") in kinds, (
        f"a resource only in the state must produce a delete; got {sorted(kinds)}")
    assert not ({"create", "update", "delete"} & {action for action, name in kinds if name == "vpc"}), (
        "vpc is identical in spec and state and must not appear in the plan")
    web = next(action for action in actions if action.name == "web")
    assert tuple(web.changes) == ("ami",), (
        f"the update for web should list its changed property ('ami',), got {tuple(web.changes)}")


def check_order_by_dependency() -> None:
    """Accept 3: creates precede dependents; deletes follow them."""
    from planner import plan

    spec = {
        "resources": {
            "db": {"type": "aws_db_instance", "properties": {"engine": "postgres"}},
            "app": {"type": "aws_instance", "properties": {"ami": "a"}, "depends_on": ["db"]},
        }
    }
    state = {
        "resources": {
            "lb": {"type": "aws_lb", "properties": {"name": "lb"}},
            "svc": {"type": "aws_ecs_service", "properties": {"name": "svc"}, "depends_on": ["lb"]},
        }
    }
    order = [(action.action, action.name) for action in plan(spec, state)]
    assert ("create", "db") in order and ("create", "app") in order, (
        f"expected creates for db and app, got {order}")
    assert order.index(("create", "db")) < order.index(("create", "app")), (
        f"app depends_on db, so db must be created first; got {order}")
    assert ("delete", "svc") in order and ("delete", "lb") in order, (
        f"expected deletes for svc and lb, got {order}")
    assert order.index(("delete", "svc")) < order.index(("delete", "lb")), (
        f"svc depends_on lb, so svc must be deleted first (deletes follow dependents); got {order}")


def check_stateful_rename() -> None:
    """Limit case: a rename is create-before-destroy for a stateful resource."""
    from planner import plan

    spec = {
        "resources": {
            "db-prod": {
                "type": "aws_db_instance",
                "properties": {"engine": "postgres", "size": "m5"},
                "lifecycle": "stateful",
            },
        }
    }
    state = {
        "resources": {
            "db": {
                "type": "aws_db_instance",
                "properties": {"engine": "postgres", "size": "m5"},
                "lifecycle": "stateful",
            },
        }
    }
    actions = plan(spec, state)
    order = [(action.action, action.name) for action in actions]
    assert ("create", "db-prod") in order and ("delete", "db") in order, (
        f"a renamed logical id is a create plus a delete, got {order}")
    assert order.index(("create", "db-prod")) < order.index(("delete", "db")), (
        f"a stateless-looking destroy-before-create is wrong here: the resource is stateful, so "
        f"the new one must be created before the old one is destroyed. Got {order}")
    created = next(action for action in actions if action.action == "create")
    assert created.replacement_of == "db", (
        f"the create should record which resource it replaces (got {created.replacement_of!r}); "
        "match the added and removed resources by identical configuration")


def check_cycle_reported() -> None:
    """Limit case: a cycle in the dependency graph is reported, not looped on."""
    from spec import DependencyCycle
    from planner import plan

    cyclic = {
        "resources": {
            "a": {"type": "svc", "properties": {"x": 1}, "depends_on": ["b"]},
            "b": {"type": "svc", "properties": {"x": 1}, "depends_on": ["a"]},
        }
    }
    # (a) no drift at all: the cycle must still be reported, because a cyclic
    # template cannot be ordered even when nothing would change.
    try:
        result = plan(cyclic, cyclic)
    except DependencyCycle as exc:
        message = str(exc)
        assert "a" in message and "b" in message, (
            f"the cycle report must name its members, got {message!r}")
    else:
        raise AssertionError(
            f"a dependency cycle must raise DependencyCycle, but plan() returned {result}. "
            "A planner that only inspects the actions it is about to order misses a cycle that "
            "produces no actions; call find_cycle on the dependency graph first.")

    # (b) with drift in the cyclic group: a recursive sort would follow the loop
    # forever, so the cycle must be detected rather than recursed into.
    drifted = {
        "resources": {
            "a": {"type": "svc", "properties": {"x": 2}, "depends_on": ["b"]},
            "b": {"type": "svc", "properties": {"x": 2}, "depends_on": ["a"]},
        }
    }
    try:
        plan(drifted, cyclic)
    except DependencyCycle:
        pass
    else:
        raise AssertionError(
            "a cycle with pending changes must still be reported as DependencyCycle, "
            "not returned as a partial plan or recursed into until the stack overflows")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("spec.py", "parse spec/state, reject malformed input", check_spec_parse),
    ("spec.py", "canonical config and dependents graph", check_spec_canonical),
    ("spec.py", "find_cycle reports a dependency loop", check_spec_find_cycle),
    ("planner.py", "idempotent: state == spec gives no actions", check_idempotent),
    ("planner.py", "changed attribute updates, removed resource deletes", check_drift),
    ("planner.py", "creates precede dependents, deletes follow them", check_order_by_dependency),
    ("planner.py", "limit: stateful rename is create-before-destroy", check_stateful_rename),
    ("planner.py", "limit: a dependency cycle is reported, not looped on", check_cycle_reported),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}Infra as Code and Drift — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built an IaC planner.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
