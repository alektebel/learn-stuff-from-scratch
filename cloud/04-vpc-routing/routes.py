"""
Route tables and longest-prefix match
=====================================

Source: AWS documentation, *Amazon VPC route tables* and *How Amazon VPC works*
(``awsdocs:vpc``). The behaviour is restated here, never copied.

A route table is an ordered set of rules, each mapping a destination CIDR to a
target: ``local`` for addresses inside the VPC, an internet gateway, a NAT
gateway, a VPC peering connection, a transit gateway, or a blackhole when the
target has been deleted. When a packet is routed, the table is searched for
every route whose destination contains the packet's address, and the route with
the **longest prefix** -- the most specific match -- wins. The default route
``0.0.0.0/0`` has a prefix length of 0, so it matches every IPv4 address and
therefore always loses to any more specific route. Only when no route matches is
the packet dropped.

The whole point of this file is that "the first route that matches" is wrong: it
makes the answer depend on the order the routes were added, and it lets the
default route shadow the local route that should carry intra-VPC traffic.

DESIGN DECISION -- represent prefixes with ``ipaddress``, or as integer/bit-length pairs?
``ipaddress.ip_network`` already implements CIDR arithmetic, containment and
normalisation and it is in the standard library, so hand-rolling an integer mask
would add bugs without teaching anything about routing. **Chosen: ipaddress.**
Cost: parsing a string is slower than a bit shift, which is irrelevant for a
route table.

DESIGN DECISION -- how is the winner found: a trie, or a scan ordered by prefix length?
A longest-prefix trie is what a real router uses and is O(bits); a scan is
O(routes). **Chosen: scan the routes and keep the one with the greatest
``prefixlen`` among those that contain the address.** A VPC route table holds
tens of routes, and the scan makes the actual rule -- "the greatest prefix
length wins" -- visible on one line instead of hiding it inside a tree walk.
Cost: it does not scale to a full BGP table; that trie is a different exercise.

DESIGN DECISION -- how to model a blackhole route?
When a target is deleted the route stays in the table with state ``blackhole``:
it still matches, but the packet is dropped. **Chosen: keep the route and have
``resolve`` return ``None`` for a non-active state.** Returning ``None`` from
``lookup`` too would erase the difference between "there is no route" and "the
route exists but its target is gone", which are different operational problems.

    python3 routes.py      # prints what this table resolves, address by address
"""

from __future__ import annotations

from ipaddress import ip_address, ip_network

DEFAULT_ROUTE = "0.0.0.0/0"


class Route:
    """One destination CIDR mapped to a target.

    ``state`` is ``"active"`` for a usable target and ``"blackhole"`` when the
    target has gone away; a blackhole route still matches an address.
    """

    def __init__(self, destination, target, state="active"):
        try:
            self.destination = ip_network(destination, strict=False)
        except ValueError as exc:
            raise ValueError(f"{destination!r} is not a CIDR prefix: {exc}") from None
        self.target = target
        self.state = state

    @property
    def prefix_length(self):
        return self.destination.prefixlen

    def matches(self, address):
        """True if ``address`` lies inside this route's destination prefix."""
        return ip_address(address) in self.destination

    def __repr__(self):
        return f"Route({self.destination} -> {self.target!r}, {self.state})"


class RouteTable:
    """A set of routes, one per destination prefix, searched longest-prefix-first."""

    def __init__(self, routes=None):
        self._routes = []
        for destination, target in (routes or ()):
            self.add_route(destination, target)

    @property
    def routes(self):
        return list(self._routes)

    def __len__(self):
        return len(self._routes)

    def add_route(self, destination, target, state="active"):
        """Add a route. Duplicate destinations are refused, as AWS refuses them."""
        route = Route(destination, target, state)
        if any(existing.destination == route.destination for existing in self._routes):
            raise ValueError(
                f"duplicate destination {route.destination}: a route table has one route per prefix")
        self._routes.append(route)
        return route

    def lookup(self, address):
        """Return the most specific :class:`Route` matching ``address``, or ``None``.

        Longest-prefix match: consider every route whose destination contains the
        address and keep the one with the greatest prefix length. The default
        route (prefix length 0) only wins when nothing more specific matches.
        """
        # TODO: Consider every route whose destination contains the address and keep the one with the greatest prefixlen (longest-prefix match). The default route 0.0.0.0/0 has prefixlen 0, so it loses to any more specific route. Return None when nothing matches. Do NOT return the first route added: the answer must not depend on insertion order.
        raise NotImplementedError("RouteTable.lookup")

    def resolve(self, address):
        """The target that will carry ``address``, or ``None`` if it is dropped.

        ``None`` means either that no route matched, or that the winning route is
        a blackhole. Use :meth:`lookup` to tell the two apart.
        """
        route = self.lookup(address)
        if route is None or route.state != "active":
            return None
        return route.target


if __name__ == "__main__":
    table = RouteTable([
        (DEFAULT_ROUTE, "igw-1"),
        ("10.0.0.0/8", "pcx-peering"),
        ("10.0.0.0/16", "local"),
        ("10.0.1.0/24", "nat-1"),
        ("10.0.1.7/32", "appliance-1"),
    ])
    print("Route table -- longest prefix wins")
    for probe in ("10.0.1.7", "10.0.1.8", "10.0.99.1", "10.1.0.1", "192.168.1.1"):
        route = table.lookup(probe)
        print(f"  {probe:<16} -> {route.destination!s:<15} target {route.target}")
    print("A deleted target becomes a blackhole: the route still matches but drops the packet")
    table.add_route("203.0.113.0/24", "nat-dead", state="blackhole")
    print(f"  203.0.113.9      -> {table.lookup('203.0.113.9').state}, resolve = {table.resolve('203.0.113.9')!r}")
