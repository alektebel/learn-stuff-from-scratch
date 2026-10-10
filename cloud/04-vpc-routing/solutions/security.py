"""
Security groups and network ACLs
================================

Source: AWS documentation, *Security groups for your VPC* and *Network ACLs*
(``awsdocs:vpc``). The behaviour is restated here, never copied.

Two different filters sit in front of an instance:

* A **security group** is attached to the instance (to its elastic network
  interface). It is **stateful**: once a request is allowed in one direction,
  the response in the other direction is allowed automatically, with no rule for
  it. A security group has only *allow* rules and an implicit deny everywhere
  else; a new group denies all inbound and -- if you remove the default
  all-traffic egress rule, as this model does -- all outbound as well.

* A **network ACL** is attached to the subnet. It is **stateless**: every packet
  is judged on its own, in both directions and independently. Rules are numbered
  and evaluated from the lowest number; the first rule whose protocol, port and
  CIDR match decides, allow or deny. A custom NACL denies everything until
  rules are added.

The stateful/stateless distinction is the whole lesson. A stateful filter needs
only the forward rule. A stateless one needs an explicit rule for the return
traffic too, and because the client's source port for a new connection is an
*ephemeral* port (Linux 32768-60999), the return rule must cover that range --
not the service port. A NACL that allows inbound 443 but outbound only 443
lets the request in and drops the response.

DESIGN DECISION -- where does connection state live: in the group, or beside it?
A security group is configured identically on every instance that uses it, so
the tracked connections cannot live on the group or two instances would share
one connection table. **Chosen: a separate :class:`SecurityGroupSet` holds the
groups attached to one endpoint and the connections that endpoint has opened.**
Cost: the caller must keep one set per endpoint; the group stays a pure policy.

DESIGN DECISION -- what does a rule match on?
AWS rules name a protocol, a port range and a source/destination CIDR. For
inbound the port is the port on the instance, for outbound the destination port
on the remote host; the source port is never part of a rule. **Chosen: match
``(protocol, destination port, remote IP)``**, where the remote IP is the source
for inbound and the destination for outbound. Cost: it does not model ICMP type
and code or prefix-list references, which are left to the README's limits.

DESIGN DECISION -- default deny, or mirror AWS's default egress allow?
AWS ships every new group with an all-traffic egress rule, which would mask the
stateful return path the module exists to teach. **Chosen: default deny in both
directions, and the caller adds the all-traffic egress rule explicitly** (it is
just ``add_rule("outbound", protocol="all")``). Cost: the model is slightly
stricter than a fresh AWS group, and says so.

    python3 security.py    # prints the stateful and stateless decisions
"""

from __future__ import annotations

from ipaddress import ip_address, ip_network

# The Linux ephemeral-port range. AWS's NAT gateways and Network Load Balancers
# use 1024-65535; a Linux instance returns from 32768-60999. The module uses the
# narrower Linux range on purpose: it is the one a hand-written NACL usually
# forgets, and if a rule covers it the wider range is a superset anyway.
EPHEMERAL_PORTS = (32768, 60999)

DIRECTIONS = ("inbound", "outbound")


def is_ephemeral(port):
    """True if ``port`` falls in the Linux ephemeral range."""
    return EPHEMERAL_PORTS[0] <= int(port) <= EPHEMERAL_PORTS[1]


def _protocol_name(protocol):
    name = str(protocol).lower()
    if name in ("-1", "all", "any"):
        return "all"
    if name not in ("tcp", "udp", "icmp"):
        raise ValueError(f"unknown protocol {protocol!r}")
    return name


def _port_range(value):
    if value is None:
        return None
    if isinstance(value, int):
        return (value, value)
    low, high = (int(part) for part in value)
    if low > high:
        raise ValueError(f"port range {value!r} is inverted")
    return (low, high)


class _Match:
    """The (protocol, port range, CIDR) part shared by security-group and NACL rules."""

    def __init__(self, protocol="tcp", port_range=None, cidr="0.0.0.0/0"):
        self.protocol = _protocol_name(protocol)
        self.port_range = _port_range(port_range)
        try:
            self.cidr = ip_network(cidr, strict=False)
        except ValueError as exc:
            raise ValueError(f"{cidr!r} is not a CIDR prefix: {exc}") from None

    def matches(self, protocol, port, remote_ip):
        """True if a packet with this protocol, port and remote IP matches the rule."""
        if self.protocol != "all" and self.protocol != _protocol_name(protocol):
            return False
        if ip_address(remote_ip) not in self.cidr:
            return False
        if self.protocol in ("tcp", "udp") and self.port_range is not None:
            return self.port_range[0] <= int(port) <= self.port_range[1]
        return True

    def __repr__(self):
        ports = "" if self.port_range is None else f" {self.port_range[0]}-{self.port_range[1]}"
        return f"{self.protocol}{ports} {self.cidr}"


class Rule(_Match):
    """One security-group rule: a direction, a match, and (implicitly) allow."""

    def __init__(self, direction, protocol="tcp", port_range=None, cidr="0.0.0.0/0"):
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {DIRECTIONS}, got {direction!r}")
        super().__init__(protocol, port_range, cidr)
        self.direction = direction

    def __repr__(self):
        return f"Rule({self.direction}, {_Match.__repr__(self)})"


class SecurityGroup:
    """A set of allow rules attached to an endpoint, with an implicit deny."""

    def __init__(self, name, rules=None, default_inbound=False, default_outbound=False):
        self.name = name
        self.rules = list(rules or ())
        self.default_inbound = default_inbound
        self.default_outbound = default_outbound

    def add_rule(self, direction, protocol="tcp", port_range=None, cidr="0.0.0.0/0"):
        """Append an allow rule. Returns it, so a caller can keep a handle."""
        rule = Rule(direction, protocol, port_range, cidr)
        self.rules.append(rule)
        return rule

    def allows(self, direction, protocol, port, remote_ip):
        """True if some rule of ``direction`` matches; otherwise the default for it.

        Security groups have only allow rules: there is no rule that *denies*, so
        a match allows and the absence of a match falls through to the default
        (deny in both directions in this model).
        """
        for rule in self.rules:
            if rule.direction == direction and rule.matches(protocol, port, remote_ip):
                return True
        return self.default_inbound if direction == "inbound" else self.default_outbound

    def __repr__(self):
        return f"SecurityGroup({self.name!r}, {len(self.rules)} rules)"


class SecurityGroupSet:
    """The groups attached to one endpoint, plus that endpoint's connection table.

    This is the stateful half: a request permitted in one direction is remembered
    as a flow, and the reversed packet is permitted in the other direction
    without consulting any rule.
    """

    def __init__(self, *groups):
        self.groups = list(groups)
        self.connections = set()

    def add(self, group):
        self.groups.append(group)
        return self

    def _rule_allows(self, direction, protocol, port, remote_ip):
        return any(group.allows(direction, protocol, port, remote_ip) for group in self.groups)

    def permits(self, packet, direction):
        """True if ``packet`` is allowed to travel ``direction`` at this endpoint.

        Stateful check comes first: if the reversed flow was already allowed, this
        is its response and no rule is needed. Otherwise the rules for this
        direction are consulted, and a permitted packet records its flow so the
        response is covered.
        """
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {DIRECTIONS}, got {direction!r}")
        if packet.reversed().flow() in self.connections:
            return True
        remote_ip = packet.src_ip if direction == "inbound" else packet.dst_ip
        if self._rule_allows(direction, packet.protocol, packet.dst_port, remote_ip):
            self.connections.add(packet.flow())
            return True
        return False

    def __repr__(self):
        return f"SecurityGroupSet({len(self.groups)} groups, {len(self.connections)} connections)"


class NACLRule(_Match):
    """One numbered NACL rule: a direction, a match, and an allow/deny action."""

    def __init__(self, number, action, direction, protocol="tcp",
                 port_range=None, cidr="0.0.0.0/0"):
        if action not in ("allow", "deny"):
            raise ValueError(f"action must be 'allow' or 'deny', got {action!r}")
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {DIRECTIONS}, got {direction!r}")
        super().__init__(protocol, port_range, cidr)
        self.number = int(number)
        self.action = action
        self.direction = direction

    def __repr__(self):
        return f"NACLRule({self.number}, {self.action}, {self.direction}, {_Match.__repr__(self)})"


class NetworkACL:
    """A subnet's stateless filter: numbered rules, first match decides."""

    def __init__(self, rules=None):
        self.rules = list(rules or ())
        self._check_numbers()
        self._sort()

    def _check_numbers(self):
        seen = set()
        for rule in self.rules:
            key = (rule.direction, rule.number)
            if key in seen:
                raise ValueError(
                    f"duplicate {rule.direction} rule number {rule.number}: NACL numbers are unique per direction")
            seen.add(key)

    def _sort(self):
        self.rules.sort(key=lambda rule: rule.number)

    def add_rule(self, number, action, direction, protocol="tcp",
                 port_range=None, cidr="0.0.0.0/0"):
        """Append a numbered rule and restore number order."""
        rule = NACLRule(number, action, direction, protocol, port_range, cidr)
        self.rules.append(rule)
        self._check_numbers()
        self._sort()
        return rule

    def evaluate(self, direction, protocol, port, remote_ip):
        """Decide one packet in one direction: the lowest matching rule number wins.

        ``remote_ip`` is the source for inbound and the destination for outbound;
        ``port`` is the packet's destination port in either direction. The first
        matching rule's action decides. If no rule matches, the packet is denied
        -- the implicit ``*`` deny at the bottom of a custom NACL.
        """
        for rule in self.rules:
            if rule.direction != direction:
                continue
            if rule.matches(protocol, port, remote_ip):
                return rule.action == "allow"
        return False

    def __repr__(self):
        return f"NetworkACL({len(self.rules)} rules)"


class Packet:
    """A transport-layer packet: the 5-tuple a filter decides on."""

    def __init__(self, src_ip, dst_ip, protocol, src_port, dst_port):
        self.src_ip = str(ip_address(src_ip))
        self.dst_ip = str(ip_address(dst_ip))
        self.protocol = _protocol_name(protocol)
        self.src_port = int(src_port)
        self.dst_port = int(dst_port)

    def reversed(self):
        """The response to this packet: endpoints and ports swapped."""
        return Packet(self.dst_ip, self.src_ip, self.protocol, self.dst_port, self.src_port)

    def flow(self):
        return (self.protocol, self.src_ip, self.src_port, self.dst_ip, self.dst_port)

    def __eq__(self, other):
        return isinstance(other, Packet) and self.flow() == other.flow()

    def __hash__(self):
        return hash(self.flow())

    def __repr__(self):
        return (f"Packet({self.protocol} {self.src_ip}:{self.src_port} "
                f"-> {self.dst_ip}:{self.dst_port})")


if __name__ == "__main__":
    server = SecurityGroup("web", rules=[Rule("inbound", "tcp", 443, "10.0.1.0/24")])
    client = SecurityGroup("client", rules=[Rule("outbound", "tcp", 443, "10.0.2.0/24")])
    server_set, client_set = SecurityGroupSet(server), SecurityGroupSet(client)
    request = Packet("10.0.1.10", "10.0.2.20", "tcp", 40000, 443)
    response = request.reversed()
    print("Security groups are stateful -- no rule is needed for the response")
    print(f"  request  server inbound : {server_set.permits(request, 'inbound')}")
    print(f"  request  client outbound: {client_set.permits(request, 'outbound')}")
    print(f"  response server outbound: {server_set.permits(response, 'outbound')}"
          "   (the server group has no outbound rule at all)")
    print(f"  response client inbound : {client_set.permits(response, 'inbound')}"
          "   (the client group has no inbound rule at all)")

    lo, hi = EPHEMERAL_PORTS
    acl = NetworkACL()
    acl.add_rule(100, "allow", "inbound", "tcp", 443, "0.0.0.0/0")
    acl.add_rule(100, "allow", "outbound", "tcp", 443, "0.0.0.0/0")
    print("A NACL is stateless -- the request is allowed, the return is not")
    print(f"  request  inbound  443  : {acl.evaluate('inbound', 'tcp', 443, '10.0.1.10')}")
    print(f"  response outbound dst 40000 (client ephemeral)"
          f": {acl.evaluate('outbound', 'tcp', 40000, '10.0.1.10')}  (no ephemeral rule)")
    acl.add_rule(110, "allow", "outbound", "tcp", EPHEMERAL_PORTS, "0.0.0.0/0")
    print(f"  after adding an outbound rule for {lo}-{hi}: "
          f"{acl.evaluate('outbound', 'tcp', 40000, '10.0.1.10')}")
