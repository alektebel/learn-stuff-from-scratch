"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

Each mutation is a mistake a learner plausibly makes, and the step that must catch it.
"""
MUTATIONS = [
    # --- registry.py ------------------------------------------------------
    ("resolve ignores TTL expiry", "registry.py",
     '            if record["draining"] or now >= record["expires_at"]:',
     '            if record["draining"]:',
     "2"),
    ("sweep removes live instances too", "registry.py",
     '        dead = [key for key, record in self.instances.items() if now >= record["expires_at"]]',
     '        dead = list(self.instances)',
     "2"),
    ("start_draining does nothing", "registry.py",
     '        record["draining"] = True\n        return True',
     '        return True',
     "3"),
    # --- gateway.py -------------------------------------------------------
    ("prefix matches without a path boundary", "gateway.py",
     '            boundary = prefix.rstrip("/")\n'
     '            if path == prefix or (boundary and path.startswith(boundary + "/")) or prefix == "/":',
     '            boundary = prefix.rstrip("/")\n'
     '            if True:',
     "5"),
    ("load balancer always picks the first instance", "gateway.py",
     '        index = self._next.get(service, 0) % len(endpoints)\n'
     '        self._next[service] = index + 1',
     '        index = 0\n        self._next[service] = 0',
     "6"),
    ("gateway retries a POST", "gateway.py",
     '            if method not in IDEMPOTENT:\n                return status',
     '            if False:\n                return status',
     "8"),
    ("gateway retries a 4xx", "gateway.py",
     '            if status < 500:\n                return status',
     '            if status < 400:\n                return status',
     "9"),
    # --- contract.py ------------------------------------------------------
    ("new required field treated as compatible", "contract.py",
     '        if name not in old_fields and new_field.get("required"):\n'
     '            reasons.append(f"new required field {name!r}")',
     '        pass',
     "11"),
    ("type change ignored", "contract.py",
     '        if old_field.get("type") != new_field.get("type"):',
     '        if False:',
     "12"),
]
