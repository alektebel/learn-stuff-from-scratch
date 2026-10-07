"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    # Routing that ignores the prompt and just cycles: the classic "load balancer
    # is not a cache" bug.
    ("always round-robin", "policy.py",
     "        best = max(replicas, key=lambda replica: replica.cached_prefix_len(prompt))\n"
     "        best_len = best.cached_prefix_len(prompt)\n"
     "        if best_len == 0:\n"
     "            return least_loaded(replicas)\n"
     "        tied = [replica for replica in replicas\n"
     "                if replica.cached_prefix_len(prompt) == best_len]\n"
     "        return min(tied, key=lambda replica: (replica.load, replica.id))\n",
     "        self._rr = getattr(self, '_rr', 0)\n"
     "        replica = replicas[self._rr % len(replicas)]\n"
     "        self._rr += 1\n"
     "        return replica\n",
     "2"),

    # Any match is treated as good enough: the first warm replica wins even when a
    # later one shares much more.
    ("first match, not longest", "policy.py",
     "        best = max(replicas, key=lambda replica: replica.cached_prefix_len(prompt))\n"
     "        best_len = best.cached_prefix_len(prompt)\n",
     "        matching = [r for r in replicas if r.cached_prefix_len(prompt) > 0]\n"
     "        best = matching[0] if matching else replicas[0]\n"
     "        best_len = best.cached_prefix_len(prompt)\n",
     "2"),

    # The cold-start fallback is dropped: a 0-token match is handed to replica 0.
    ("ignore cold-start fallback", "policy.py",
     "    return min(replicas, key=lambda replica: (replica.load, replica.id))\n",
     "    return replicas[0]\n",
     "3"),

    # The next request is routed to whichever replica served the previous one,
    # read off the response, instead of on the incoming prompt.
    ("route on the response, not the prompt", "proxy.py",
     "        chosen = self.policy.choose(self.replicas, list(prompt))\n",
     "        chosen = (self.replicas[self.last_response['replica']]\n"
     "                  if self.last_response else self.policy.choose(self.replicas, list(prompt)))\n",
     "4"),
]
