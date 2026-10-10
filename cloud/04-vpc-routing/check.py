"""
Progress checker for the VPC-routing templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The acceptance criteria of node ``cloud-04-vpc-routing`` are enforced literally:
  1  the most specific matching prefix wins
  2  the longest match beats the default route (limit case)
  3  a security group's rule set is evaluated on protocol, port and CIDR
  4  a security-group rule allows the response without an explicit inbound rule
  5  a NACL must allow both directions and the ephemeral ports
  6  the packet simulator walks the decision and names the layer that drops
  7  a NACL that blocks the ephemeral return port kills an otherwise-allowed connection
"""

import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

# The order a packet crosses the layers, request then response. Step 6 and 7 assert
# this exact sequence so the simulator cannot silently skip a layer.
REQUEST_LAYERS = ["client-sg-outbound", "client-nacl-outbound", "route",
                  "server-nacl-inbound", "server-sg-inbound"]
RESPONSE_LAYERS = ["server-sg-outbound", "server-nacl-outbound", "route-return",
                   "client-nacl-inbound", "client-sg-inbound"]


# ---------------------------------------------------------------------------
# Step 1: route table, longest-prefix match
# ---------------------------------------------------------------------------

def check_longest_prefix_match() -> None:
    from routes import RouteTable

    table = RouteTable([("10.0.0.0/16", "local"), ("10.0.1.0/24", "nat-1"),
                        ("0.0.0.0/0", "igw-1")])
    route = table.lookup("10.0.1.5")
    assert route is not None and route.target == "nat-1", (
        f"lookup('10.0.1.5') resolved to {getattr(route, 'target', None)!r}, expected 'nat-1'. "
        "Three routes match (10.0.0.0/16, 10.0.1.0/24 and the default); the MOST SPECIFIC "
        "-- the greatest prefix length -- wins, not the first one added.")
    assert route.prefix_length == 24, (
        f"the winning route has prefix length {route.prefix_length}, expected 24: the winner is "
        "the matching route with the largest prefixlen.")
    assert table.lookup("10.0.2.9").target == "local", (
        "10.0.2.9 is only covered by the /16 local route, so it must resolve to 'local'")
    assert table.lookup("8.8.8.8").target == "igw-1", (
        "8.8.8.8 is outside the VPC, so only the default route matches")
    assert table.resolve("10.0.1.5") == "nat-1"

    # Order must not matter: rebuilding in the reverse order gives the same answers.
    reversed_table = RouteTable([("0.0.0.0/0", "igw-1"), ("10.0.1.0/24", "nat-1"),
                                 ("10.0.0.0/16", "local")])
    for probe, want in (("10.0.1.5", "nat-1"), ("10.0.2.9", "local"), ("8.8.8.8", "igw-1")):
        got = reversed_table.lookup(probe).target
        assert got == want, (
            f"reversing the insertion order changed lookup({probe}) from {want} to {got}: "
            "longest-prefix match must not depend on the order routes were added")

    empty = RouteTable([("10.0.0.0/16", "local")])
    assert empty.lookup("8.8.8.8") is None, (
        "with no matching route and no default, lookup must return None (the packet is dropped), "
        "not raise and not invent a route")


# ---------------------------------------------------------------------------
# Step 2: overlapping prefixes -- the longest match beats the default route (limit case)
# ---------------------------------------------------------------------------

def check_overlapping_prefixes() -> None:
    from routes import RouteTable

    routes = [("0.0.0.0/0", "igw-1"), ("10.0.0.0/8", "pcx-peering"),
              ("10.0.0.0/16", "local"), ("10.0.1.0/24", "nat-1"),
              ("10.0.1.7/32", "appliance-1")]
    expected = {"10.0.1.7": "appliance-1", "10.0.1.8": "nat-1", "10.0.99.1": "local",
                "10.1.0.1": "pcx-peering", "192.168.1.1": "igw-1"}
    # Add the default FIRST and LAST; a first-match implementation gives different answers.
    for order in (routes, list(reversed(routes))):
        table = RouteTable(order)
        for probe, want in expected.items():
            got = table.lookup(probe).target
            assert got == want, (
                f"lookup({probe}) = {got!r}, expected {want!r}. Overlapping prefixes: the "
                "longest (most specific) match wins. If the default route 0.0.0.0/0 shadows a "
                "more specific route, you are keeping the first match instead of the longest.")
        assert table.lookup("10.0.99.1").prefix_length == 16, (
            "inside 10.0.0.0/8 the /16 local route must beat both the /8 peering route and the "
            "default route")

    # A default route present but a /32 host route deliberately overrides it.
    table = RouteTable([("0.0.0.0/0", "igw-1"), ("10.0.1.7/32", "appliance-1")])
    assert table.lookup("10.0.1.7").target == "appliance-1", (
        "a /32 host route is the most specific match possible and must win over 0.0.0.0/0")
    assert table.lookup("10.0.1.8").target == "igw-1"


# ---------------------------------------------------------------------------
# Step 3: security-group rule evaluation
# ---------------------------------------------------------------------------

def check_security_group_rules() -> None:
    from security import SecurityGroup

    sg = SecurityGroup("web")
    sg.add_rule("inbound", "tcp", 443, "10.0.1.0/24")
    sg.add_rule("outbound", "tcp", 5432, "10.0.2.0/24")
    assert sg.allows("inbound", "tcp", 443, "10.0.1.5") is True, (
        "an inbound tcp/443 rule from 10.0.1.0/24 must allow 10.0.1.5:443")
    assert sg.allows("inbound", "tcp", 80, "10.0.1.5") is False, (
        "port 80 is not in the 443 rule: a security group has no wildcard unless you write one")
    assert sg.allows("inbound", "tcp", 443, "10.0.9.5") is False, (
        "10.0.9.5 is outside the rule's source CIDR: the source address must be checked")
    assert sg.allows("inbound", "udp", 443, "10.0.1.5") is False, (
        "the rule is tcp, not udp: the protocol must be checked")
    assert sg.allows("outbound", "tcp", 443, "10.0.2.5") is False, (
        "the only outbound rule is tcp/5432; a tcp/443 egress must still be denied")
    assert sg.allows("outbound", "tcp", 5432, "10.0.2.5") is True
    assert sg.allows("outbound", "tcp", 5432, "10.0.9.5") is False, (
        "the outbound rule's destination CIDR is 10.0.2.0/24, not the source address")

    ranged = SecurityGroup("ranged")
    ranged.add_rule("inbound", "tcp", (8000, 8010), "0.0.0.0/0")
    assert ranged.allows("inbound", "tcp", 8000, "1.2.3.4"), "the low end of the range is included"
    assert ranged.allows("inbound", "tcp", 8010, "1.2.3.4"), "the high end of the range is included"
    assert not ranged.allows("inbound", "tcp", 7999, "1.2.3.4"), "7999 is below the range"
    assert not ranged.allows("inbound", "tcp", 8011, "1.2.3.4"), "8011 is above the range"

    everything = SecurityGroup("egress-all")
    everything.add_rule("outbound", protocol="all")
    assert everything.allows("outbound", "tcp", 12345, "8.8.8.8"), (
        "an all-protocol, all-port rule must allow any tcp/udp traffic (the default AWS egress rule)")
    assert everything.allows("outbound", "udp", 53, "8.8.8.8")
    assert everything.allows("inbound", "tcp", 12345, "8.8.8.8") is False, (
        "the all-traffic rule was outbound; the inbound default is still deny")


# ---------------------------------------------------------------------------
# Step 4: stateful security groups -- the response needs no inbound rule (accept)
# ---------------------------------------------------------------------------

def check_security_group_stateful() -> None:
    from security import Packet, SecurityGroup, SecurityGroupSet

    server_group = SecurityGroup("server")
    server_group.add_rule("inbound", "tcp", 443, "10.0.1.0/24")   # no outbound rule at all
    client_group = SecurityGroup("client")
    client_group.add_rule("outbound", "tcp", 443, "10.0.2.0/24")  # no inbound rule at all
    server = SecurityGroupSet(server_group)
    client = SecurityGroupSet(client_group)

    request = Packet("10.0.1.10", "10.0.2.20", "tcp", 40000, 443)
    response = request.reversed()
    assert server.permits(request, "inbound") is True, "the inbound 443 rule allows the request"
    assert server.permits(response, "outbound") is True, (
        "the server has NO outbound rule, yet the response must pass: a security group is "
        "stateful and remembers the allowed request. Checking rules for the response is the bug.")
    assert client.permits(request, "outbound") is True, "the outbound 443 rule allows the request"
    assert client.permits(response, "inbound") is True, (
        "the client has NO inbound rule, yet the response must pass: it answers the connection "
        "the client opened. This is the criterion 'a security-group rule allows the response "
        "without an explicit inbound rule'.")

    # A response with no matching request must NOT be let through: no state is forged.
    fresh = SecurityGroupSet(server_group)
    assert fresh.permits(response, "outbound") is False, (
        "an unsolicited response (no prior request) must be denied: the stateful allowance is "
        "for the RETURN of an allowed connection, not for any packet that looks like one")
    # A denied request must not create state either.
    denied = Packet("10.0.1.10", "10.0.2.20", "tcp", 40001, 8080)
    assert server.permits(denied, "inbound") is False, "there is no inbound rule for 8080"
    assert server.permits(denied.reversed(), "outbound") is False, (
        "a DENIED request must not record a connection: otherwise its response would be allowed")


# ---------------------------------------------------------------------------
# Step 5: stateless NACLs -- both directions and the ephemeral ports (accept)
# ---------------------------------------------------------------------------

def check_network_acl_stateless() -> None:
    from security import EPHEMERAL_PORTS, NetworkACL, is_ephemeral

    low, high = EPHEMERAL_PORTS
    assert is_ephemeral(40000) and not is_ephemeral(443), (
        "443 is a service port; 40000 is in the Linux ephemeral range 32768-60999")

    acl = NetworkACL()
    acl.add_rule(100, "allow", "inbound", "tcp", 443, "0.0.0.0/0")
    acl.add_rule(100, "allow", "outbound", "tcp", 443, "0.0.0.0/0")
    acl.add_rule(110, "allow", "outbound", "tcp", EPHEMERAL_PORTS, "0.0.0.0/0")
    assert acl.evaluate("inbound", "tcp", 443, "10.0.1.10") is True, "the request is allowed in"
    assert acl.evaluate("outbound", "tcp", 40000, "10.0.1.10") is True, (
        "the rule for the ephemeral range must allow the response out to port 40000")

    # Without the ephemeral rule the response is denied -- the limit case in miniature.
    no_ephemeral = NetworkACL()
    no_ephemeral.add_rule(100, "allow", "inbound", "tcp", 443, "0.0.0.0/0")
    no_ephemeral.add_rule(100, "allow", "outbound", "tcp", 443, "0.0.0.0/0")
    assert no_ephemeral.evaluate("outbound", "tcp", 40000, "10.0.1.10") is False, (
        "an outbound rule for 443 does NOT cover the ephemeral 40000: a NACL is stateless, so "
        "the return traffic needs its own rule over the ephemeral range")

    # Stateless means the two directions are independent.
    one_way = NetworkACL()
    one_way.add_rule(100, "allow", "inbound", "tcp", 443, "0.0.0.0/0")
    assert one_way.evaluate("inbound", "tcp", 443, "10.0.1.10") is True
    assert one_way.evaluate("outbound", "tcp", 40000, "10.0.1.10") is False, (
        "allowing the inbound request must not implicitly allow the outbound response: the "
        "directions are evaluated separately")

    # Rule order: the lowest matching number wins, regardless of insertion order.
    ordered = NetworkACL()
    ordered.add_rule(200, "allow", "inbound", "tcp", 22, "0.0.0.0/0")
    ordered.add_rule(100, "deny", "inbound", "tcp", 22, "0.0.0.0/0")
    assert [rule.number for rule in ordered.rules] == [100, 200], (
        "NACL rules must be stored in number order, not insertion order")
    assert ordered.evaluate("inbound", "tcp", 22, "10.0.1.10") is False, (
        "the lower-numbered deny (100) beats the allow (200): rules are first-match by NUMBER")

    # Implicit deny when nothing matches.
    assert acl.evaluate("inbound", "tcp", 22, "10.0.1.10") is False, (
        "no rule matches tcp/22, so the implicit deny at the bottom of the ACL applies")
    assert acl.evaluate("outbound", "udp", 40000, "10.0.1.10") is False, (
        "the ephemeral rule is tcp; udp must fall through to the implicit deny")


# ---------------------------------------------------------------------------
# Simulator fixtures shared by steps 6 and 7
# ---------------------------------------------------------------------------

def _fleet(server_ephemeral=True):
    """A two-subnet VPC with a client and a server, ready for simulate_connection.

    When ``server_ephemeral`` is False the server subnet's NACL lacks the outbound
    rule over the ephemeral range, so the response dies on the way back.
    """
    from routes import RouteTable
    from security import EPHEMERAL_PORTS, NetworkACL, Rule, SecurityGroup, SecurityGroupSet
    from simulator import Endpoint, Subnet, Vpc

    vpc = Vpc("vpc-1", "10.0.0.0/16",
              RouteTable([("10.0.0.0/16", "local"), ("0.0.0.0/0", "igw-1")]))

    def web_nacl(ephemeral):
        acl = NetworkACL()
        acl.add_rule(100, "allow", "outbound", "tcp", 443, "0.0.0.0/0")
        acl.add_rule(100, "allow", "inbound", "tcp", 443, "0.0.0.0/0")
        if ephemeral:
            acl.add_rule(110, "allow", "outbound", "tcp", EPHEMERAL_PORTS, "0.0.0.0/0")
            acl.add_rule(110, "allow", "inbound", "tcp", EPHEMERAL_PORTS, "0.0.0.0/0")
        return acl

    subnet_a = vpc.add_subnet(Subnet("subnet-a", "10.0.1.0/24", web_nacl(True)))
    subnet_b = vpc.add_subnet(Subnet("subnet-b", "10.0.2.0/24", web_nacl(server_ephemeral)))
    client_sgs = SecurityGroupSet(
        SecurityGroup("client", rules=[Rule("outbound", "tcp", 443, "10.0.2.0/24")]))
    server_sgs = SecurityGroupSet(
        SecurityGroup("server", rules=[Rule("inbound", "tcp", 443, "10.0.1.0/24")]))
    client = vpc.add_endpoint(Endpoint("client", "10.0.1.10", subnet_a, client_sgs))
    server = vpc.add_endpoint(Endpoint("server", "10.0.2.20", subnet_b, server_sgs))
    return vpc, client, server


# ---------------------------------------------------------------------------
# Step 6: the packet simulator walks the decision
# ---------------------------------------------------------------------------

def check_packet_simulator() -> None:
    from simulator import simulate_connection

    vpc, client, server = _fleet()
    decision = simulate_connection(vpc, client, server)
    assert decision.accepted is True, (
        f"the connection should be accepted but dropped at {decision.dropped_at!r}. The SGs are "
        "stateful (no return rule needed) and both NACLs allow 443 and the ephemeral range.")
    assert decision.dropped_at is None
    assert decision.layers() == REQUEST_LAYERS + RESPONSE_LAYERS, (
        f"the simulator must walk request then response through all ten layers, got "
        f"{decision.layers()}. A missing layer means a filter was skipped.")
    assert all(step.allowed for step in decision.steps), (
        f"a step was denied on an allowed connection: "
        f"{[s for s in decision.steps if not s.allowed]}")
    assert any(step.layer == "route" and "10.0.2.20" in step.detail for step in decision.steps), (
        "the trace must name the route it used for the destination")

    # A missing ingress rule is dropped at the security group, not somewhere vague.
    from security import SecurityGroup, SecurityGroupSet
    from simulator import Endpoint
    bare = Endpoint("bare", "10.0.2.21", server.subnet, SecurityGroupSet(SecurityGroup("bare")))
    denied = simulate_connection(vpc, client, bare)
    assert denied.accepted is False and denied.dropped_at == "server-sg-inbound", (
        f"with no ingress rule the packet must be dropped at 'server-sg-inbound', got "
        f"accepted={denied.accepted}, dropped_at={denied.dropped_at!r}")

    # The route lookup is part of the walk: without the local route, the default route
    # sends the packet to the gateway and it never reaches the peer.
    from routes import RouteTable
    from simulator import Vpc
    routed = Vpc("vpc-2", "10.0.0.0/16", RouteTable([("0.0.0.0/0", "igw-1")]))
    routed.add_subnet(client.subnet)
    routed.add_subnet(server.subnet)
    lost = simulate_connection(routed, client, server)
    assert lost.accepted is False and lost.dropped_at == "route", (
        f"without a local route the packet is routed out of the VPC: expected a drop at 'route', "
        f"got accepted={lost.accepted}, dropped_at={lost.dropped_at!r}")


# ---------------------------------------------------------------------------
# Step 7: a NACL blocking the ephemeral return port kills the connection (limit case)
# ---------------------------------------------------------------------------

def check_nacl_blocks_return_port() -> None:
    from security import EPHEMERAL_PORTS
    from simulator import simulate_connection

    vpc, client, server = _fleet(server_ephemeral=False)
    decision = simulate_connection(vpc, client, server)
    assert decision.accepted is False, (
        "the server subnet's NACL has no outbound rule over the ephemeral range, so the response "
        "must be dropped -- yet the connection was reported accepted. A NACL is stateless: the "
        "return traffic has to be judged again, not assumed to be allowed.")
    assert decision.dropped_at == "server-nacl-outbound", (
        f"the response should die at the server subnet's NACL outbound step, got "
        f"{decision.dropped_at!r}. The request is allowed all the way in; it is the RETURN that "
        "the missing ephemeral rule kills.")
    assert decision.layers() == REQUEST_LAYERS + ["server-sg-outbound", "server-nacl-outbound"], (
        f"expected the request's five layers plus the response's SG (stateful, allowed) and the "
        f"failing NACL outbound, got {decision.layers()}")
    assert all(step.allowed for step in decision.steps[:6]), (
        "every step before the failing NACL outbound must be allowed, otherwise this is a "
        "different bug")

    # Repair it: adding the outbound ephemeral rule makes the same connection succeed.
    server.subnet.nacl.add_rule(110, "allow", "outbound", "tcp", EPHEMERAL_PORTS, "0.0.0.0/0")
    fixed = simulate_connection(vpc, client, server)
    assert fixed.accepted is True, (
        f"after adding the outbound ephemeral rule the connection must succeed, dropped at "
        f"{fixed.dropped_at!r}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("routes.py", "longest-prefix match", check_longest_prefix_match),
    ("routes.py", "overlapping prefixes beat the default", check_overlapping_prefixes),
    ("security.py", "security-group rule matching", check_security_group_rules),
    ("security.py", "stateful: response needs no inbound rule", check_security_group_stateful),
    ("security.py", "stateless NACL: both directions + ephemeral", check_network_acl_stateless),
    ("simulator.py", "the packet simulator walks the decision", check_packet_simulator),
    ("simulator.py", "NACL blocks the ephemeral return port", check_nacl_blocks_return_port),
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
    print(f"\n{BOLD}VPC Routing From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<13} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<13} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<13} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built VPC routing from scratch.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
