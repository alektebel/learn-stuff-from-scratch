"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism: a route lookup that is first-match or shortest-prefix,
a security group that is stateless or ignores its rule match, a NACL that is stateful,
unordered or default-allow, and a simulator that skips the route or reuses the service
port for the return. Each must be CAUGHT by the step named; a MISSED mutation means the
check is too weak, not that the bug is acceptable.
"""
MUTATIONS = [
    # ---- routes.py: longest-prefix match -------------------------------------------
    # Keep the FIRST matching route instead of the most specific: the default route
    # added early would shadow the /24 below it.
    ("route lookup keeps the first match, not the longest", "routes.py",
     "            if best is None or route.prefix_length > best.prefix_length:\n"
     "                best = route\n",
     "            if best is None:\n"
     "                best = route\n", "1"),
    # Pick the SHORTEST matching prefix: the default route 0.0.0.0/0 always wins.
    ("route lookup picks the shortest prefix, so the default wins", "routes.py",
     "            if best is None or route.prefix_length > best.prefix_length:",
     "            if best is None or route.prefix_length < best.prefix_length:", "2"),

    # ---- security.py: security groups ----------------------------------------------
    # A security group that ignores its rule's port/protocol/CIDR allows everything in
    # that direction as soon as one rule of the direction exists.
    ("security group ignores the rule's protocol, port and CIDR", "security.py",
     "        for rule in self.rules:\n"
     "            if rule.direction == direction and rule.matches(protocol, port, remote_ip):\n"
     "                return True\n",
     "        for rule in self.rules:\n"
     "            if rule.direction == direction:\n"
     "                return True\n", "3"),
    # Drop the stateful half: the response now needs its own rule, so an allowed
    # connection's return traffic is denied.
    ("security group is stateless, so the response needs a rule", "security.py",
     "        if packet.reversed().flow() in self.connections:\n"
     "            return True\n",
     "", "4"),

    # ---- security.py: network ACLs -------------------------------------------------
    # Match rules in insertion order instead of by rule number, so a later-numbered
    # allow can shadow an earlier deny.
    ("NACL first-match uses insertion order, not rule number", "security.py",
     "        self.rules.sort(key=lambda rule: rule.number)\n",
     "        self.rules.sort(key=lambda rule: 0)\n", "5"),
    # An unmatched packet is allowed: no implicit deny at the bottom of the ACL.
    ("NACL has an implicit allow instead of an implicit deny", "security.py",
     "            if rule.matches(protocol, port, remote_ip):\n"
     "                return rule.action == \"allow\"\n"
     "        return False\n",
     "            if rule.matches(protocol, port, remote_ip):\n"
     "                return rule.action == \"allow\"\n"
     "        return True\n", "5"),

    # ---- simulator.py --------------------------------------------------------------
    # Judge the response against the NACL using the SERVICE port instead of the
    # client's ephemeral port: the missing ephemeral rule is never noticed.
    ("simulator reuses the service port for the return NACL check", "simulator.py",
     "                  server.subnet.nacl.evaluate(\"outbound\", response.protocol,\n"
     "                                              response.dst_port, response.dst_ip),\n",
     "                  server.subnet.nacl.evaluate(\"outbound\", response.protocol,\n"
     "                                              request.dst_port, response.dst_ip),\n", "7"),
    # Ignore the route lookup entirely, so a packet the default route would send out of
    # the VPC is still "delivered" to the peer.
    ("simulator ignores the route lookup", "simulator.py",
     "    if not record(\"route\", vpc.route_table.resolve(server.ip) == \"local\",\n",
     "    if not record(\"route\", True,\n", "6"),
]
