"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
    "policy.py": {
        "least_loaded": "Return min(replicas, key=lambda r: (r.load, r.id)); the lowest load, lowest id to break ties. Do not mutate.",
        "LongestPrefixPolicy.choose": "Score every replica with replica.cached_prefix_len(prompt). If the best score is 0 return least_loaded(replicas); otherwise return the replica with the largest score, ties broken by (load, id).",
    },
    "proxy.py": {
        "Proxy.generate": "chosen = self.policy.choose(self.replicas, list(prompt)); reply = post_json(chosen.port, '/generate', {'prompt': list(prompt), 'gen_len': gen_len}, timeout=timeout); set self.last_response = reply; bump self.requests; return reply.",
    },
}
