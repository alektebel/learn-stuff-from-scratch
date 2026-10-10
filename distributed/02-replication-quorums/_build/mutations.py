"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    # (description, file, exact text in solutions/<file>, replacement, check step)

    # network.py -----------------------------------------------------------
    ("delivery ordered by send, not by time", "network.py",
     "        heapq.heappush(self._queue, (self.now + delay, self._seq, src, dst, payload))",
     "        heapq.heappush(self._queue, (self._seq, self._seq, src, dst, payload))",
     "1"),
    ("partitions are ignored (everyone can talk)", "network.py",
     "    def _connected(self, a: str, b: str) -> bool:\n"
     "        if self._groups is None:\n"
     "            return True\n"
     "        return any(a in group and b in group for group in self._groups)",
     "    def _connected(self, a: str, b: str) -> bool:\n"
     "        return True",
     "2"),

    # replica.py -----------------------------------------------------------
    ("the log accepts gaps and double writes", "replica.py",
     "        index = entry[\"index\"]\n"
     "        if index != len(self.log):\n"
     "            return False\n"
     "        self.log.append(dict(entry))",
     "        self.log.append(dict(entry))",
     "3"),
    ("truncate drops the entry but keeps its value", "replica.py",
     "        del self.log[index:]\n"
     "        self.applied = {}\n"
     "        for entry in self.log:\n"
     "            self.applied[entry[\"key\"]] = (entry[\"version\"], entry[\"value\"])",
     "        del self.log[index:]",
     "4"),

    # quorum.py ------------------------------------------------------------
    ("read returns the first response, not the newest version", "quorum.py",
     "        best: Optional[tuple] = None\n"
     "        for name in nodes:\n"
     "            got = self.replicas[name].value(key)\n"
     "            if got is not None and (best is None or got[0] > best[0]):\n"
     "                best = got\n"
     "        return None if best is None else best[1]",
     "        for name in nodes:\n"
     "            got = self.replicas[name].value(key)\n"
     "            if got is not None:\n"
     "                return got[1]\n"
     "        return None",
     "5"),
    ("read ignores the requested quorum", "quorum.py",
     "        nodes = self.names[:self.R] if from_ is None else list(from_)",
     "        nodes = self.names[:self.R]",
     "6"),
    ("commit_index counts entries instead of positions", "quorum.py",
     "        index = -1\n"
     "        while self.holders(index + 1) >= self.W:\n"
     "            index += 1\n"
     "        return index",
     "        return len(self.replicas[self.leader].log)",
     "7"),
    ("a minority write is acknowledged without W replicas", "quorum.py",
     "        if self.holders(index) >= self.W:\n"
     "            return index",
     "        return index",
     "8"),
    ("a refused write leaves the forked entry behind", "quorum.py",
     "        for replica in self.replicas.values():\n"
     "            if replica.get(index) is not None:\n"
     "                replica.truncate(index)\n"
     "                self.net.send(self.leader, replica.name, {\"kind\": \"truncate\", \"index\": index})\n"
     "        self.net.flush()\n"
     "        raise NotEnoughReplicas(",
     "        raise NotEnoughReplicas(",
     "8"),
    ("a write waits for every replica, not a quorum", "quorum.py",
     "        if self.holders(index) >= self.W:\n"
     "            return index",
     "        if self.holders(index) >= self.N:\n"
     "            return index",
     "9"),
]
