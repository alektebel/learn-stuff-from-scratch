"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
    "registry.py": {
        "ServiceRegistry.register": "Store {(service, instance_id): {endpoint, ttl, expires_at: now + ttl, draining: False}}, replacing any previous registration.",
        "ServiceRegistry.heartbeat": "Look up the key; if absent return False; else set expires_at = now + the stored ttl and return True.",
        "ServiceRegistry.deregister": "pop the key with a default and return whether it existed.",
        "ServiceRegistry.start_draining": "Look up the key; if absent return False; else set draining = True and return True.",
        "ServiceRegistry.resolve": "Collect endpoints for this service where NOT draining and now < expires_at; return them sorted by str(instance_id) so callers are deterministic.",
        "ServiceRegistry.sweep": "Delete every key whose now >= expires_at and return how many you removed.",
    },
    "gateway.py": {
        "Gateway.match": "Longest matching prefix where path == prefix or path starts with prefix.rstrip('/') + '/'. A bare '/' route catches everything. Return the service or None.",
        "Gateway.pick": "endpoints = registry.resolve(service, now); None if empty; otherwise index = self._next.get(service, 0) % len, bump self._next[service] = index + 1, return endpoints[index].",
        "Gateway.call": "service = match(path); None -> 404. Attempt up to max_retries + 1 times: pick an instance (None -> 503), invoke it, treat ConnectionError as 503; return as soon as status < 500; a 5xx is retried only if method is in IDEMPOTENT; after the loop return the last status.",
    },
    "contract.py": {
        "breaking_changes": "Old field removed -> reason. Same field type changed -> reason. Optional -> required -> reason. A field only in new and required -> reason. Return sorted(reasons).",
        "compatibility": "Return 'breaking' if breaking_changes(old, new) is non-empty, else 'compatible'.",
    },
}
