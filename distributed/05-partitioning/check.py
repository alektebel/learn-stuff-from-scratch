"""
Progress checker for the partitioning templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.
"""

import os
import pathlib
import random
import shutil
import subprocess
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

#: The key set every distribution check shares. Seeded, so thresholds are stable.
SEED = 20261010
NODES = [f"node-{i}" for i in range(8)]


def sample_keys(n: int, seed: int = SEED) -> List[str]:
    """`n` deterministic 64-bit hex keys from an explicit seed."""
    rng = random.Random(seed)
    return [f"{rng.getrandbits(64):016x}" for _ in range(n)]


# ---------------------------------------------------------------------------
# Steps 1-2: hashring.py
# ---------------------------------------------------------------------------

def check_ring_tokens() -> None:
    from hashring import HashRing, _hash

    assert isinstance(_hash("probe"), int), (
        f"_hash() returned {type(_hash('probe')).__name__}, not an int: the ring needs a numeric id space")

    ring = HashRing(vnodes=4)
    ring.add_node("a")
    ring.add_node("b")
    tokens = ring.tokens()
    assert len(tokens) == 8, (
        f"a 2-node ring with 4 vnodes should have 8 positions, got {len(tokens)}: "
        "are you adding one position per virtual node?")
    assert tokens == sorted(tokens), (
        "tokens() is not sorted: a lookup uses bisect and needs the positions in order")
    for node in ("a", "b"):
        assert sum(1 for _, owner in tokens if owner == node) == 4, (
            f"node {node!r} does not occupy exactly `vnodes` positions")
    ring.remove_node("a")
    assert len(ring.tokens()) == 4, "remove_node() did not take all of a node's virtual positions"

    # A ring must be reproducible across processes. Python's built-in hash() of a
    # string is salted per process (PYTHONHASHSEED), so a ring built with it moves
    # every key on restart; SHA-256 does not.
    probe = "import hashring; print(hashring._hash('determinism-probe'))"
    here = os.path.dirname(os.path.abspath(__file__))
    outputs = []
    for seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        done = subprocess.run([sys.executable, "-c", probe], cwd=here,
                              capture_output=True, text=True, env=env, timeout=60)
        assert done.returncode == 0, f"_hash() crashed in a fresh process: {done.stderr.strip()}"
        outputs.append(done.stdout.strip())
    assert outputs[0] and outputs[0] == outputs[1], (
        f"_hash() differs across processes ({outputs[0]} vs {outputs[1]}): you are using the "
        "built-in hash(), which is salted by PYTHONHASHSEED. Keys would move to different nodes "
        "on every restart - use a stable digest such as hashlib.sha256.")


def check_lookup_stable() -> None:
    from hashring import HashRing

    keys = sample_keys(500)
    nodes = NODES

    def build() -> "HashRing":
        ring = HashRing(vnodes=256)
        for node in nodes:
            ring.add_node(node)
        return ring

    first, second = build(), build()
    for key in keys:
        owner = first.node_for(key)
        assert owner in nodes, f"node_for({key!r}) returned {owner!r}, which is not on the ring"
        assert first.node_for(key) == owner, (
            "node_for() returned a different node for the same key: a lookup must be pure")
        assert second.node_for(key) == owner, (
            "two identically-built rings disagree about a key. Something changes between ring "
            "instances - is a token hashed together with id(self), time, or random()? The ring "
            "must depend only on the node names and the virtual-node count.")

    tokens = first.tokens()
    for key in keys:
        first.node_for(key)
    assert first.tokens() == tokens, (
        "node_for() changed the ring: a lookup is a read-only operation")


# ---------------------------------------------------------------------------
# Steps 3-7: partitioner.py
# ---------------------------------------------------------------------------

def check_distribution_even() -> None:
    from partitioner import DEFAULT_VNODES, EVENNESS_BOUND, Partitioner

    keys = sample_keys(20000)
    p = Partitioner(NODES, vnodes=DEFAULT_VNODES)
    counts = p.counts(keys)
    assert set(counts) == set(NODES), (
        f"counts() must name every node; got {sorted(counts)}")
    assert sum(counts.values()) == len(keys), (
        f"counts() covers {sum(counts.values())} of {len(keys)} keys: every key must land on exactly one node")
    even = p.evenness(counts)
    assert even <= EVENNESS_BOUND, (
        f"peak/mean = {even:.3f} exceeds the stated bound {EVENNESS_BOUND} with "
        f"{DEFAULT_VNODES} virtual nodes. Without virtual nodes one node owns a huge arc; "
        "make sure each node is placed at `vnodes` positions before sorting them.")


def check_join_moves_share() -> None:
    from partitioner import Partitioner

    keys = sample_keys(20000)
    p = Partitioner(NODES, vnodes=256)
    before = p.assign(keys)
    moved = p.join("node-8", keys)
    after = p.assign(keys)

    assert moved == {k for k in keys if before[k] != after[k]}, (
        "join() returned a different set than the keys whose owner actually changed")
    assert moved, "joining a node moved no keys at all"
    assert all(after[k] == "node-8" for k in moved), (
        "a key moved on join but did not land on the new node: only keys inside the new node's "
        "arcs may change owner")
    share = len(moved) / len(keys)
    assert share < 0.25, (
        f"{share:.1%} of keys moved when one of nine nodes joined. Consistent hashing moves only "
        "the new node's share (~1/9); if nearly everything moved you are rehashing with "
        "hash(key) % num_nodes instead of walking the ring.")


def check_leave_moves_share() -> None:
    from partitioner import Partitioner

    keys = sample_keys(20000)
    p = Partitioner(NODES, vnodes=256)
    before = p.assign(keys)
    departed = "node-3"
    owned = {k for k in keys if before[k] == departed}
    moved = p.leave(departed, keys)
    after = p.assign(keys)

    assert moved == owned, (
        f"leaving {departed} moved {len(moved)} keys but it owned {len(owned)}: exactly the "
        "departed node's keys should change owner and nothing else")
    assert all(after[k] != departed for k in keys), "a key still maps to the node that left"
    share = len(moved) / len(keys)
    assert 0 < share < 0.25, (
        f"{share:.1%} of keys moved on leave; it should be roughly one node's share (~1/8)")
    counts = p.counts(keys)
    assert set(counts) == set(NODES) - {departed}, "counts() still lists the departed node"
    assert p.evenness(counts) <= 1.25, (
        f"after leaving one of eight nodes the remaining ring is uneven (peak/mean "
        f"{p.evenness(counts):.3f}): the departed node's keys should spread over its successors")


def check_few_vnodes_uneven() -> None:
    """Limit case: too few virtual nodes gives a badly uneven ring."""
    from partitioner import EVENNESS_BOUND, Partitioner

    keys = sample_keys(20000)
    few = Partitioner(NODES, vnodes=1)
    many = Partitioner(NODES, vnodes=256)
    e_few = few.evenness(few.counts(keys))
    e_many = many.evenness(many.counts(keys))

    assert e_few >= 1.5, (
        f"with a single virtual node per node the ring measures peak/mean = {e_few:.3f}; this "
        "case is supposed to be badly uneven, so the measurement is not seeing the real shares")
    assert e_many <= EVENNESS_BOUND, (
        f"with 256 virtual nodes the ring measures peak/mean = {e_many:.3f}, over the bound "
        f"{EVENNESS_BOUND}. That is what one position per node looks like: are the extra virtual "
        "nodes actually being added?")


def check_hot_key() -> None:
    """Limit case: a hot key overloads one node even with a balanced ring."""
    from partitioner import EVENNESS_BOUND, Partitioner

    keys = sample_keys(20000)
    p = Partitioner(NODES, vnodes=256)
    even = p.evenness(p.counts(keys))
    assert even <= EVENNESS_BOUND, (
        f"the ring is not even to begin with (peak/mean {even:.3f}); fix step 3 first")

    hot = keys[0]
    weights = {key: 1 for key in keys}
    weights[hot] = 1_000_000
    loads = p.load(keys, weights)
    total = sum(loads.values())
    hot_node = p.ring.node_for(hot)
    share = loads[hot_node] / total
    mean = total / len(NODES)
    assert share > 0.9, (
        f"the hot key's node carries only {share:.1%} of the weighted load, but {hot!r} is read "
        "a million times: load() must weight each key by its access count, not count keys equally. "
        "An even ring balances keys, not work.")
    assert loads[hot_node] > 2 * mean, (
        "the hot key did not make its node the clear outlier: weights are being ignored")

    uniform = p.load(keys)
    um = sum(uniform.values()) / len(NODES)
    assert max(uniform.values()) <= EVENNESS_BOUND * um, (
        "with uniform weights load() should mirror the even key counts")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("hashring.py", "ring: virtual tokens and a stable hash", check_ring_tokens),
    ("hashring.py", "lookup is pure and reproducible", check_lookup_stable),
    ("partitioner.py", "keys distribute within the stated bound", check_distribution_even),
    ("partitioner.py", "join moves only the new node's share", check_join_moves_share),
    ("partitioner.py", "leave hands over exactly one node's keys", check_leave_moves_share),
    ("partitioner.py", "limit: too few virtual nodes is uneven", check_few_vnodes_uneven),
    ("partitioner.py", "limit: a hot key overloads its node", check_hot_key),
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
    print(f"\n{BOLD}Partitioning and Rebalancing — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<16} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<16} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<16} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built a partitioning ring.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
