"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "hashring.py": {
  "_hash": "Hash the UTF-8 bytes of the string with hashlib.sha256 and return the digest as one big integer. Do NOT use the built-in hash(): it is salted per process, so the ring would move every key on restart.",
  "HashRing.add_node": "If the node is not already a member, add it and mark the ring dirty so the next lookup rebuilds.",
  "HashRing.remove_node": "If the node is a member, discard it and mark the ring dirty.",
  "HashRing._rebuild": "For every node, add `vnodes` positions hashing f'{node}#{replica}'. Sort the (hash, node) pairs. Keep the list of hashes for bisect. Clear the dirty flag.",
  "HashRing.tokens": "Rebuild if dirty, then return a copy of the sorted (hash, node) list. Reading must not mutate the ring.",
  "HashRing.node_for": "Rebuild if dirty. bisect_left the key's hash in the sorted hashes; the owner is that token's node, or the first token if the index runs past the end (the ring wraps). Empty ring returns None.",
 },
 "partitioner.py": {
  "Partitioner.assign": "Return {key: ring.node_for(key)} for every key. Read-only.",
  "Partitioner.counts": "Start every current node at 0, then add one per assigned key so a node with no keys still appears.",
  "Partitioner.evenness": "Peak-to-mean share: max(counts) / mean(counts). 1.0 is perfect; return 0.0 when the mean is 0.",
  "Partitioner.join": "Snapshot the owners, add the node, snapshot again, and return the set of keys whose owner changed. Only the new node's arcs should be affected.",
  "Partitioner.leave": "Snapshot the owners, remove the node, snapshot again, and return the set of keys whose owner changed. It should equal the set the node owned.",
  "Partitioner.load": "Start every node at 0. For each key add weights.get(key, 1) (or 1 when weights is None) to its owner's total. This is why a hot key shows up: key counts stay even, weighted load does not.",
 },
}
