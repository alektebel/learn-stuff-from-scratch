"""Service discovery: a registry that tracks instances, their health, and draining.

Source: Kleppmann, "Designing Data-Intensive Applications" ch. 1 (request routing and
service discovery); the Eureka/Consul models; Kubernetes liveness and readiness probes.
Microservices are many short-lived processes at addresses that change on every deploy.
Callers cannot be configured with a static list, so instances register themselves, send
heartbeats to stay advertised, and are removed when their TTL lapses or when they drain
for shutdown.

DESIGN DECISION - pull registry, DNS, or a static list?
    A pull registry centralizes health: a client resolves fresh endpoints on each call and
    the registry can drop dead ones. DNS SRV works but caches for its TTL and knows
    nothing about liveness. A static list cannot survive a deploy. We choose the registry.
    Cost: one more service to run and a resolver hop on the request path.

DESIGN DECISION - heartbeat TTL vs active health checks.
    Instances heartbeat every `ttl / 3`; the registry expires an instance that misses
    `ttl`. This is cheap and survives a registry restart, but a dead instance is advertised
    for up to one TTL. Active checks detect faster and know *why* an instance is down.
    Cost: failover detection is delayed by up to `ttl`.

DESIGN DECISION - what does "draining" mean and who sets it?
    `start_draining` keeps the instance in the registry but removes it from `resolve`, so
    no NEW request is routed to it while in-flight requests finish. Only then does the
    process `deregister`. Marking it gone immediately (deregister) would drop requests
    already on the wire.
    Cost: a shrinking window where the instance is alive but receives no traffic.

DESIGN DECISION - exact TTL comparison.
    `now >= expires_at` expires, so a `ttl` of 0 is immediately dead and a heartbeat must
    arrive strictly before the deadline. This matches the absolute-expiry rule used
    elsewhere in this repository. Cost: none.
"""

__all__ = ["ServiceRegistry"]


class ServiceRegistry:
    def __init__(self):
        # (service, instance_id) -> {"endpoint", "ttl", "expires_at", "draining"}
        self.instances = {}

    def register(self, service, instance_id, endpoint, *, ttl, now):
        self.instances[(service, instance_id)] = {
            "endpoint": endpoint, "ttl": ttl, "expires_at": now + ttl, "draining": False}

    def heartbeat(self, service, instance_id, *, now):
        record = self.instances.get((service, instance_id))
        if record is None:
            return False
        record["expires_at"] = now + record["ttl"]
        return True

    def deregister(self, service, instance_id):
        return self.instances.pop((service, instance_id), None) is not None

    def start_draining(self, service, instance_id):
        record = self.instances.get((service, instance_id))
        if record is None:
            return False
        record["draining"] = True
        return True

    def resolve(self, service, *, now):
        healthy = []
        for (name, instance_id), record in self.instances.items():
            if name != service:
                continue
            if record["draining"] or now >= record["expires_at"]:
                continue
            healthy.append((instance_id, record["endpoint"]))
        return [endpoint for _, endpoint in sorted(healthy, key=lambda pair: str(pair[0]))]

    def sweep(self, *, now):
        dead = [key for key, record in self.instances.items() if now >= record["expires_at"]]
        for key in dead:
            del self.instances[key]
        return len(dead)


if __name__ == "__main__":
    registry = ServiceRegistry()
    for i in range(3):
        registry.register("checkout", f"pod-{i}", f"10.0.0.{i}:8080", ttl=30, now=0.0)
    print(f"resolved at t=0: {registry.resolve('checkout', now=0.0)}")
    registry.heartbeat("checkout", "pod-1", now=10.0)     # refresh only pod-1
    registry.start_draining("checkout", "pod-0")          # graceful shutdown starts
    print(f"after pod-1 heartbeat + pod-0 draining at t=31: "
          f"{registry.resolve('checkout', now=31.0)}  (pod-2's TTL lapsed, pod-0 drains)")
    print(f"sweep removed {registry.sweep(now=31.0)} expired instance(s)")
    print(f"remaining keys: {sorted(registry.instances)}")
