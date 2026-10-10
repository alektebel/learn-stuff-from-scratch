"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    # network.py: a message's own delay must decide when it arrives.
    ("delivery time ignored (FIFO arrivals)", "network.py",
     "        heapq.heappush(self._queue, (self.now + delay, self._seq, src, dst, msg))",
     "        heapq.heappush(self._queue, (self.now, self._seq, src, dst, msg))",
     "1"),
    ("a partition does not drop messages", "network.py",
     "        if self._groups is None:\n            return True\n        return any(a in g and b in g for g in self._groups)",
     "        return True",
     "2"),
    # raft.py: classic consensus bugs.
    ("committing without a majority", "raft.py",
     "            if on_majority >= self.majority:",
     "            if on_majority >= 1:",
     "8"),
    ("a stale-log candidate is granted the vote", "raft.py",
     "            up_to_date = (\n                msg[\"last_log_term\"] > self.last_log_term\n"
     "                or (msg[\"last_log_term\"] == self.last_log_term\n"
     "                    and msg[\"last_log_index\"] >= self.last_log_index)\n            )",
     "            up_to_date = True",
     "6"),
    ("applying entries before they are committed", "raft.py",
     "        while self.last_applied < self.commit_index:",
     "        while self.last_applied < len(self.log):",
     "5"),
    ("a conflicting log suffix is not truncated", "raft.py",
     "        del self.log[prev_index + i:]\n        self.log.extend(new_entries[i:])",
     "        self.log.extend(new_entries[i:])",
     "9"),
    ("a follower hearing a higher term does not step down", "raft.py",
     "        self.state = FOLLOWER\n        self.leader_id = msg[\"leader\"]",
     "        self.leader_id = msg[\"leader\"]",
     "9"),
    ("committing past the last entry the message carries", "raft.py",
     "            self.commit_index = min(msg[\"leader_commit\"], prev_index + len(new_entries))",
     "            self.commit_index = msg[\"leader_commit\"]",
     "10"),
]
