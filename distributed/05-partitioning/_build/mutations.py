"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    # (description, file, exact text in solutions/<file>, replacement, check step)

    # hashring.py ---------------------------------------------------------
    ("built-in salted hash instead of a stable digest", "hashring.py",
     '    return int.from_bytes(hashlib.sha256(data.encode("utf-8")).digest(), "big")',
     '    return hash(data) & ((1 << 256) - 1)',
     "1"),
    ("ring salted with the instance identity", "hashring.py",
     '                tokens.append((_hash(f"{node}#{replica}"), node))',
     '                tokens.append((_hash(f"{node}#{replica}#{id(self)}"), node))',
     "2"),
    ("virtual tokens not sorted before bisect", "hashring.py",
     "        tokens.sort()\n",
     "",
     "3"),
    ("virtual nodes ignored (one position per node)", "hashring.py",
     "            for replica in range(self.vnodes):",
     "            for replica in range(1):",
     "6"),

    # partitioner.py ------------------------------------------------------
    ("join reports every key as moved", "partitioner.py",
     '    def join(self, node: str, keys: Sequence[str]) -> Set[str]:\n'
     '        """Add `node`; return exactly the keys whose owner changed."""\n'
     "        before = self.assign(keys)\n"
     "        self.ring.add_node(node)\n"
     "        after = self.assign(keys)\n"
     "        return {key for key in keys if before[key] != after[key]}\n",
     '    def join(self, node: str, keys: Sequence[str]) -> Set[str]:\n'
     '        """Add `node`; return exactly the keys whose owner changed."""\n'
     "        before = self.assign(keys)\n"
     "        self.ring.add_node(node)\n"
     "        after = self.assign(keys)\n"
     "        return set(keys)\n",
     "4"),
    ("leave reports every key as moved", "partitioner.py",
     '    def leave(self, node: str, keys: Sequence[str]) -> Set[str]:\n'
     '        """Remove `node`; return exactly the keys whose owner changed."""\n'
     "        before = self.assign(keys)\n"
     "        self.ring.remove_node(node)\n"
     "        after = self.assign(keys)\n"
     "        return {key for key in keys if before[key] != after[key]}\n",
     '    def leave(self, node: str, keys: Sequence[str]) -> Set[str]:\n'
     '        """Remove `node`; return exactly the keys whose owner changed."""\n'
     "        before = self.assign(keys)\n"
     "        self.ring.remove_node(node)\n"
     "        after = self.assign(keys)\n"
     "        return set(keys)\n",
     "5"),
    ("evenness always reports a perfect ring", "partitioner.py",
     "        return max(values) / mean",
     "        return 1.0",
     "6"),
    ("load counts keys equally, ignoring access weights", "partitioner.py",
     "            weight = 1 if weights is None else weights.get(key, 1)",
     "            weight = 1",
     "7"),
]
