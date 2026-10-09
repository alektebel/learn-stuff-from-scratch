"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

Each mutation is a mistake a learner plausibly makes, and the step that must catch it.
"""
MUTATIONS = [
    # --- log.py -----------------------------------------------------------
    ("up-to-date compares length, not term", "log.py",
     '        return candidate_term > other_term',
     '        return len(candidate) > len(other)',
     "2"),
    ("choose_leader ranks the longest log first", "log.py",
     '    return min(eligible, key=lambda name: (-last_term(logs[name]), -len(logs[name]), name),\n'
     '               default=None)',
     '    return min(eligible, key=lambda name: (-len(logs[name]), -last_term(logs[name]), name),\n'
     '               default=None)',
     "3"),
    ("commit index ignores the quorum", "log.py",
     '        if count < majority:\n            break',
     '        if False:\n            break',
     "4"),
    # --- cluster.py -------------------------------------------------------
    ("sync write acknowledges one replica", "cluster.py",
     '            if len(reachable) < self.majority():\n'
     '                return False\n'
     '            self.logs[self.leader].append(Entry(self.term, command))\n'
     '            for name in reachable:\n'
     '                if name != self.leader:\n'
     '                    self._follow(name)\n'
     '            self.commit_index = quorum_index(self.logs, self.majority())',
     '            self.logs[self.leader].append(Entry(self.term, command))\n'
     '            for name in reachable:\n'
     '                if name != self.leader:\n'
     '                    self._follow(name)\n'
     '            self.commit_index = len(self.logs[self.leader])',
     "6"),
    ("async replicates before acknowledging", "cluster.py",
     '        # async: acknowledge before replicating, so the log can be lost on failover\n'
     '        self.logs[self.leader].append(Entry(self.term, command))\n'
     '        self.commit_index = len(self.logs[self.leader])',
     '        self.logs[self.leader].append(Entry(self.term, command))\n'
     '        self._catch_up()\n'
     '        self.commit_index = len(self.logs[self.leader])',
     "8"),
    ("election does not bump the epoch", "cluster.py",
     '            self.term += 1\n'
     '            self.epoch += 1\n'
     '            self._catch_up()',
     '            self.term += 1\n'
     '            self._catch_up()',
     "10"),
    ("election ignores majority reachability", "cluster.py",
     '        eligible = [name for name in self.names if self.can_lead(name)]',
     '        eligible = [name for name in self.names if name not in self.down]',
     "10"),
    ("fencing store ignores the epoch", "cluster.py",
     '        if epoch < self.seen_epoch:',
     '        if False:',
     "10"),
]
