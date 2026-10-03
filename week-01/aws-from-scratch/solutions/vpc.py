"""
VPC — CIDR, routing, and the difference that causes the most confusion:
security groups are STATEFUL, network ACLs are NOT. Complete Solution.

DESIGN DECISION — model packets, or model rules?
  Evaluating rules in isolation tells you what a rule says. It does not tell
  you whether a connection works, and "the rule looks right but it does not
  connect" is the entire genre of VPC bug.
  CHOSEN: model a CONNECTION — a request packet and its reply — and evaluate
  both directions. The stateful/stateless difference then appears as a
  behavioural result rather than a fact to memorise: the same ruleset that
  works for a security group silently drops the RETURN traffic on a NACL.

DESIGN DECISION — how much CIDR arithmetic to implement?
  Python has `ipaddress`. Using it would skip the part worth understanding:
  that a /24 inside a /16 is a containment test on the network address, and
  that subnets in one VPC must not overlap.
  CHOSEN: use `ipaddress` for parsing, but implement containment, overlap and
  the usable-host count by hand, since those are the numbers people get wrong.
"""

import ipaddress
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

# AWS reserves 5 addresses in every subnet: network, VPC router, DNS, future
# use, and broadcast. A /28 gives you 11 usable hosts, not 16 — which is how
# people run out of addresses in a subnet they sized "with room to spare".
AWS_RESERVED_PER_SUBNET = 5


class Cidr:
    def __init__(self, notation: str):
        self.network = ipaddress.ip_network(notation, strict=False)
        self.notation = notation

    def contains(self, other: "Cidr") -> bool:
        return (int(other.network.network_address) >= int(self.network.network_address)
                and int(other.network.broadcast_address)
                <= int(self.network.broadcast_address))

    def contains_ip(self, address: str) -> bool:
        return ipaddress.ip_address(address) in self.network

    def overlaps(self, other: "Cidr") -> bool:
        return (int(self.network.network_address) <= int(other.network.broadcast_address)
                and int(other.network.network_address)
                <= int(self.network.broadcast_address))

    def usable_hosts(self) -> int:
        total = self.network.num_addresses
        return max(0, total - AWS_RESERVED_PER_SUBNET)

    def __repr__(self) -> str:
        return self.notation


class Rule(NamedTuple):
    number: int
    action: str                 # "allow" or "deny"
    protocol: str               # "tcp", "udp", "icmp", "-1"
    port_from: int
    port_to: int
    cidr: str

    def matches(self, protocol: str, port: int, address: str) -> bool:
        if self.protocol not in ("-1", protocol):
            return False
        if self.protocol != "-1" and not self.port_from <= port <= self.port_to:
            return False
        return Cidr(self.cidr).contains_ip(address)


class SecurityGroup:
    """STATEFUL. If a request is allowed out, the reply is allowed back in —
    regardless of the inbound rules. You never write a rule for return traffic.
    """

    def __init__(self, group_id: str, name: str = ""):
        self.group_id = group_id
        self.name = name or group_id
        self.inbound: List[Rule] = []
        self.outbound: List[Rule] = [
            Rule(1, "allow", "-1", 0, 65535, "0.0.0.0/0")]   # AWS default

    def allow_inbound(self, protocol: str, port_from: int, port_to: int,
                      cidr: str) -> None:
        self.inbound.append(Rule(len(self.inbound) + 1, "allow", protocol,
                                 port_from, port_to, cidr))

    def evaluate(self, direction: str, protocol: str, port: int,
                 address: str) -> bool:
        """Allow-only: there is no deny rule. Absence of an allow IS the deny."""
        rules = self.inbound if direction == "in" else self.outbound
        return any(rule.matches(protocol, port, address) for rule in rules)


class NetworkAcl:
    """STATELESS. Every packet is evaluated on its own, in rule-number order,
    first match wins. Return traffic needs its OWN rule — on ephemeral ports.
    """

    def __init__(self, acl_id: str):
        self.acl_id = acl_id
        self.inbound: List[Rule] = []
        self.outbound: List[Rule] = []

    def add(self, direction: str, number: int, action: str, protocol: str,
            port_from: int, port_to: int, cidr: str) -> None:
        rules = self.inbound if direction == "in" else self.outbound
        rules.append(Rule(number, action, protocol, port_from, port_to, cidr))
        rules.sort(key=lambda r: r.number)

    def evaluate(self, direction: str, protocol: str, port: int,
                 address: str) -> Tuple[bool, str]:
        """Lowest rule number that matches decides. No match means deny."""
        rules = self.inbound if direction == "in" else self.outbound
        for rule in rules:
            if rule.matches(protocol, port, address):
                return rule.action == "allow", f"rule {rule.number} ({rule.action})"
        return False, "no rule matched — implicit deny"


class Subnet:
    def __init__(self, subnet_id: str, cidr: str, public: bool = False,
                 acl: Optional[NetworkAcl] = None):
        self.subnet_id = subnet_id
        self.cidr = Cidr(cidr)
        self.public = public
        self.acl = acl
        self.route_table: List[Tuple[str, str]] = [("local", "local")]

    def add_route(self, destination: str, target: str) -> None:
        self.route_table.append((destination, target))

    def route_for(self, address: str) -> str:
        """Most specific match wins — the longest prefix, not the first entry."""
        best, best_length = "blackhole", -1
        for destination, target in self.route_table:
            if destination == "local":
                if self.cidr.contains_ip(address) and self.cidr.network.prefixlen > best_length:
                    best, best_length = "local", self.cidr.network.prefixlen
                continue
            network = Cidr(destination)
            if network.contains_ip(address) and network.network.prefixlen > best_length:
                best, best_length = target, network.network.prefixlen
        return best


class Vpc:
    def __init__(self, vpc_id: str, cidr: str):
        self.vpc_id = vpc_id
        self.cidr = Cidr(cidr)
        self.subnets: Dict[str, Subnet] = {}

    def add_subnet(self, subnet_id: str, cidr: str, public: bool = False,
                   acl: Optional[NetworkAcl] = None) -> Subnet:
        candidate = Cidr(cidr)
        if not self.cidr.contains(candidate):
            raise ValueError(f"{cidr} is not inside the VPC range {self.cidr}")
        for existing in self.subnets.values():
            if existing.cidr.overlaps(candidate):
                raise ValueError(f"{cidr} overlaps existing subnet "
                                 f"{existing.subnet_id} ({existing.cidr})")
        subnet = Subnet(subnet_id, cidr, public, acl)
        self.subnets[subnet_id] = subnet
        return subnet


def test_connection(source_ip: str, dest_ip: str, port: int,
                    security_group: Optional[SecurityGroup] = None,
                    acl: Optional[NetworkAcl] = None,
                    protocol: str = "tcp",
                    ephemeral_port: int = 49152) -> Dict[str, Any]:
    """Evaluate a whole connection: the request AND its reply.

    This is the function that makes the stateful/stateless difference visible.
    A security group evaluates the request; the reply is implied. A NACL
    evaluates both packets independently, and the reply arrives on an EPHEMERAL
    port — which no one remembers to allow.
    """
    steps: List[str] = []
    allowed = True

    if acl is not None:
        ok, why = acl.evaluate("in", protocol, port, source_ip)
        steps.append(f"NACL inbound  {source_ip}:* -> :{port}  {'allow' if ok else 'DENY'} ({why})")
        allowed &= ok

    if security_group is not None:
        ok = security_group.evaluate("in", protocol, port, source_ip)
        steps.append(f"SG inbound    {source_ip} -> :{port}  {'allow' if ok else 'DENY'}")
        allowed &= ok

    # The reply.
    if security_group is not None:
        steps.append(f"SG reply      implicitly allowed (stateful — no rule needed)")

    if acl is not None:
        ok, why = acl.evaluate("out", protocol, ephemeral_port, source_ip)
        steps.append(f"NACL outbound reply -> {source_ip}:{ephemeral_port}  "
                     f"{'allow' if ok else 'DENY'} ({why})")
        allowed &= ok

    return {"allowed": allowed, "steps": steps}


def _demo() -> None:
    print("=== CIDR: the five addresses you do not get ===")
    print(f"  {'CIDR':<18}{'total':>8}{'usable':>9}")
    for notation in ("10.0.0.0/16", "10.0.1.0/24", "10.0.2.0/28", "10.0.3.0/30"):
        cidr = Cidr(notation)
        print(f"  {notation:<18}{cidr.network.num_addresses:>8}"
              f"{cidr.usable_hosts():>9}")
    print("  AWS reserves 5 per subnet. A /28 gives 11 hosts, not 16 — which is")
    print("  how a subnet sized 'with room to spare' runs out.")

    print("\n=== Subnets must fit, and must not overlap ===")
    vpc = Vpc("vpc-1", "10.0.0.0/16")
    vpc.add_subnet("public-a", "10.0.1.0/24", public=True)
    vpc.add_subnet("private-a", "10.0.2.0/24")
    print(f"  added: {list(vpc.subnets)}")
    for bad, why in [("10.0.1.128/25", "overlaps public-a"),
                     ("192.168.0.0/24", "outside the VPC range")]:
        try:
            vpc.add_subnet("bad", bad)
            print(f"  {bad}: accepted — that is a bug")
        except ValueError as exc:
            print(f"  {bad:<16} rejected: {exc}")

    print("\n=== Routing: longest prefix wins, not first match ===")
    subnet = vpc.subnets["private-a"]
    subnet.add_route("0.0.0.0/0", "nat-gateway")
    subnet.add_route("10.1.0.0/16", "peering-connection")
    subnet.add_route("10.1.5.0/24", "transit-gateway")
    for address in ("10.0.2.15", "10.1.9.9", "10.1.5.7", "8.8.8.8"):
        print(f"  {address:<12} -> {subnet.route_for(address)}")
    print("  10.1.5.7 matches three routes and takes the /24. Route tables are")
    print("  not ordered rule lists — specificity decides.")

    print("\n=== THE difference: stateful vs stateless ===")
    web_sg = SecurityGroup("sg-web")
    web_sg.allow_inbound("tcp", 443, 443, "0.0.0.0/0")

    naive_acl = NetworkAcl("acl-naive")
    naive_acl.add("in", 100, "allow", "tcp", 443, 443, "0.0.0.0/0")
    naive_acl.add("out", 100, "allow", "tcp", 443, 443, "0.0.0.0/0")

    print("\n  Identical intent: 'allow HTTPS in'.")
    print("\n  Security group:")
    result = test_connection("203.0.113.5", "10.0.1.10", 443, security_group=web_sg)
    for step in result["steps"]:
        print(f"    {step}")
    print(f"    connection: {'WORKS' if result['allowed'] else 'FAILS'}")

    print("\n  Network ACL, same rules:")
    result = test_connection("203.0.113.5", "10.0.1.10", 443, acl=naive_acl)
    for step in result["steps"]:
        print(f"    {step}")
    print(f"    connection: {'WORKS' if result['allowed'] else 'FAILS'}")

    print("\n  The request was allowed both times. The NACL dropped the REPLY,")
    print("  because a reply goes back to an ephemeral port (49152-65535) and")
    print("  nothing allowed that. A security group needed no such rule — it")
    print("  remembers the connection.")

    fixed_acl = NetworkAcl("acl-fixed")
    fixed_acl.add("in", 100, "allow", "tcp", 443, 443, "0.0.0.0/0")
    fixed_acl.add("out", 100, "allow", "tcp", 1024, 65535, "0.0.0.0/0")
    result = test_connection("203.0.113.5", "10.0.1.10", 443, acl=fixed_acl)
    print(f"\n  With an ephemeral-port outbound rule: "
          f"{'WORKS' if result['allowed'] else 'FAILS'}")

    print("\n=== NACL rule order matters; SG rule order does not ===")
    ordered = NetworkAcl("acl-ordered")
    ordered.add("in", 100, "deny", "tcp", 22, 22, "0.0.0.0/0")
    ordered.add("in", 200, "allow", "tcp", 22, 22, "10.0.0.0/8")
    ordered.add("out", 100, "allow", "-1", 0, 65535, "0.0.0.0/0")
    ok, why = ordered.evaluate("in", "tcp", 22, "10.0.5.5")
    print(f"  internal SSH with deny at 100, allow at 200: "
          f"{'allow' if ok else 'DENY'} ({why})")
    print("  First match wins by NUMBER, so the broad deny at 100 shadows the")
    print("  specific allow at 200. Security groups have no deny rules at all,")
    print("  so this failure mode simply cannot happen there.")


if __name__ == "__main__":
    _demo()
