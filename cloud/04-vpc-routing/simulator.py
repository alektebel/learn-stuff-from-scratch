"""
The packet simulator: routes, security groups and NACLs in one walk
===================================================================

Source: AWS documentation, *How Amazon VPC works* -- the path a packet takes
(``awsdocs:vpc``). The behaviour is restated here, never copied.

A connection between two instances inside a VPC crosses five decision points in
order, and reverses to cross five more:

    request   client -> server:  egress security group, subnet NACL outbound,
                                 route lookup, peer subnet NACL inbound,
                                 peer ingress security group
    response  server -> client:  egress security group, subnet NACL outbound,
                                 route lookup, peer subnet NACL inbound,
                                 peer ingress security group

The simulator returns not just accept/drop but the **trace** of every step, and
names the layer that dropped the packet. That is the difference between "it did
not work" and a lesson: "the NACL on the server subnet dropped the response
because its outbound rule was written for port 443, not the ephemeral range".

Note the asymmetry the trace makes visible. The route lookup only delivers when
the winning route's target is ``local``: a more specific route to a NAT gateway,
or the default route when the local route is missing, sends the packet out of
the VPC and it never reaches the peer endpoint. The security groups are stateful
so the response passes with no rule; the NACLs are stateless so the response is
judged all over again -- and that is exactly where a plausible configuration
fails.

DESIGN DECISION -- why a named ``local`` target instead of "the peer is in the same VPC"?
Checking the address against the VPC CIDR would pass even when a more specific
route overrides it, which is the routing bug the module wants to expose.
**Chosen: the route table must actually resolve the peer's address to the
``local`` target.** Cost: the demo must build a local route, as AWS does
automatically.

DESIGN DECISION -- return a bool, or a trace?
A bool is what a caller usually wants, but the lesson lives in *which* layer
decided. **Chosen: a :class:`Decision` carrying ``accepted``, a
``dropped_at`` layer name, and the ordered steps.** Cost: the caller reads
``decision.accepted`` instead of a bare truth value; ``__bool__`` is defined so
``if decision:`` still works.

DESIGN DECISION -- does the connection table live across both directions of one simulation?
Yes, and it is the same :class:`SecurityGroupSet` on each endpoint, so a request
opened in the first half is recognised as the response in the second. **Chosen:
one ``simulate_connection`` call owns both halves and both endpoints' state.**
Cost: two calls never share state, which is deliberate -- a fresh call is a
fresh connection.

    python3 simulator.py   # prints an accepted trace and a NACL-killed one
"""

from __future__ import annotations

from collections import namedtuple
from ipaddress import ip_address, ip_network

from security import NetworkACL, Packet, SecurityGroup, SecurityGroupSet

Step = namedtuple("Step", "layer allowed detail")


class Subnet:
    """A subnet: a CIDR and the NACL attached to it."""

    def __init__(self, name, cidr, nacl):
        self.name = name
        self.cidr = ip_network(cidr)
        self.nacl = nacl

    def __repr__(self):
        return f"Subnet({self.name!r}, {self.cidr})"


class Endpoint:
    """An instance: an address, its subnet, and the security groups on it."""

    def __init__(self, name, address, subnet, security_groups):
        self.name = name
        self.ip = str(ip_address(address))
        self.subnet = subnet
        if isinstance(security_groups, SecurityGroupSet):
            self.security_groups = security_groups
        elif isinstance(security_groups, SecurityGroup):
            self.security_groups = SecurityGroupSet(security_groups)
        else:
            self.security_groups = SecurityGroupSet(*security_groups)

    def __repr__(self):
        return f"Endpoint({self.name!r}, {self.ip}, {self.subnet.name!r})"


class Vpc:
    """A VPC: its CIDR, its route table, and the subnets and endpoints in it."""

    def __init__(self, name, cidr, route_table):
        self.name = name
        self.cidr = ip_network(cidr)
        self.route_table = route_table
        self.subnets = []
        self.endpoints = []

    def add_subnet(self, subnet):
        self.subnets.append(subnet)
        return subnet

    def add_endpoint(self, endpoint):
        self.endpoints.append(endpoint)
        return endpoint

    def __repr__(self):
        return f"Vpc({self.name!r}, {self.cidr})"


class Decision:
    """The result of one simulated connection: accepted, where it stopped, and why."""

    def __init__(self, accepted, steps=None, dropped_at=None):
        self.accepted = bool(accepted)
        self.steps = list(steps or ())
        self.dropped_at = dropped_at

    def __bool__(self):
        return self.accepted

    def layers(self):
        return [step.layer for step in self.steps]

    def __repr__(self):
        verdict = "ACCEPTED" if self.accepted else f"DROPPED at {self.dropped_at}"
        return f"Decision({verdict}, {len(self.steps)} steps)"


def simulate_connection(vpc, client, server, protocol="tcp",
                        client_port=40000, server_port=443):
    """Walk a request and its response through route table, NACLs and SGs.

    The request is a packet ``client -> server``; if every layer allows it, the
    reversed packet is walked back. A security group remembers the connection so
    the response needs no rule; a NACL does not, so the response is judged again
    and must have its own rule covering the client's ephemeral port.

    Returns a :class:`Decision`. ``decision.dropped_at`` names the first layer
    that denied a packet: ``"client-sg-outbound"``, ``"client-nacl-outbound"``,
    ``"route"``, ``"server-nacl-inbound"``, ``"server-sg-inbound"``,
    ``"server-sg-outbound"``, ``"server-nacl-outbound"``, ``"route-return"``,
    ``"client-nacl-inbound"`` or ``"client-sg-inbound"``.
    """
    # TODO: Walk request then response. Request: client egress SG, client-subnet NACL outbound (dst_port, dst_ip), route lookup for server.ip that must resolve to 'local', server-subnet NACL inbound (dst_port, src_ip), server ingress SG. Response: server egress SG (the set is stateful, so the response passes), server-subnet NACL outbound (response dst_port = the client's EPHEMERAL port, dst_ip), route for client.ip, client-subnet NACL inbound, client ingress SG. Record every step and return early with the layer that dropped.
    raise NotImplementedError("simulate_connection")


if __name__ == "__main__":
    from routes import RouteTable
    from security import EPHEMERAL_PORTS, Rule, SecurityGroup

    def make_vpc(server_ephemeral=True):
        table = RouteTable([("10.0.0.0/16", "local"), ("0.0.0.0/0", "igw-1")])
        vpc = Vpc("vpc-1", "10.0.0.0/16", table)

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
        client = vpc.add_endpoint(Endpoint(
            "client", "10.0.1.10", subnet_a,
            SecurityGroup("client", rules=[Rule("outbound", "tcp", 443, "10.0.2.0/24")])))
        server = vpc.add_endpoint(Endpoint(
            "server", "10.0.2.20", subnet_b,
            SecurityGroup("server", rules=[Rule("inbound", "tcp", 443, "10.0.1.0/24")])))
        return vpc, client, server

    def show(title, decision):
        print(title)
        for step in decision.steps:
            mark = "allow" if step.allowed else "DROP "
            print(f"  {mark} {step.layer:<22} {step.detail}")
        print(f"  => {decision!r}\n")

    print("Packet simulator -- a whole HTTPS connection, decision by decision\n")
    vpc, client, server = make_vpc(server_ephemeral=True)
    show("Fully allowed: the SGs are stateful, the NACLs allow both directions", 
         simulate_connection(vpc, client, server))
    vpc, client, server = make_vpc(server_ephemeral=False)
    show("NACL outbound only allows 443: the ephemeral return is dropped",
         simulate_connection(vpc, client, server))
