"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries a decision the node grades is listed, so make_templates
stubs it and replaces its body with ``raise NotImplementedError``. The dataclasses,
``Rule``/``NACLRule`` matching and the packet/trace plumbing are provided: the lesson
is longest-prefix lookup, stateful vs stateless filtering, and the walk.
"""

HINTS = {
 "routes.py": {
  "RouteTable.lookup":
      "Consider every route whose destination contains the address and keep the one with the "
      "greatest prefixlen (longest-prefix match). The default route 0.0.0.0/0 has prefixlen 0, "
      "so it loses to any more specific route. Return None when nothing matches. Do NOT return "
      "the first route added: the answer must not depend on insertion order.",
 },
 "security.py": {
  "SecurityGroup.allows":
      "Scan the rules of this direction; the first whose protocol, port range and CIDR match "
      "allows. Security groups have no deny rule, so no match falls through to the default "
      "(inbound/outbound, both False here). Check protocol AND port AND source/destination CIDR.",
  "SecurityGroupSet.permits":
      "Stateful first: if the packet REVERSED is already in self.connections, this is the "
      "response and it is allowed with no rule. Otherwise pick remote_ip (source for inbound, "
      "destination for outbound) and consult the groups; on a match, record packet.flow() so the "
      "response is covered. A denied packet records nothing.",
  "NetworkACL.evaluate":
      "Stateless: judge this packet in this direction only. Walk rules already sorted by number, "
      "keep those whose direction matches, and return allow/deny of the FIRST whose "
      "protocol/port/CIDR match. No match falls through to the implicit deny (return False). Do "
      "not consult the other direction and do not look at stored connections.",
 },
 "simulator.py": {
  "simulate_connection":
      "Walk request then response. Request: client egress SG, client-subnet NACL outbound "
      "(dst_port, dst_ip), route lookup for server.ip that must resolve to 'local', server-subnet "
      "NACL inbound (dst_port, src_ip), server ingress SG. Response: server egress SG (the set is "
      "stateful, so the response passes), server-subnet NACL outbound (response dst_port = the "
      "client's EPHEMERAL port, dst_ip), route for client.ip, client-subnet NACL inbound, client "
      "ingress SG. Record every step and return early with the layer that dropped.",
 },
}
