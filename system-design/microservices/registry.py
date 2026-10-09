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
        # TODO: Store {(service, instance_id): {endpoint, ttl, expires_at: now + ttl, draining: False}}, replacing any previous registration.
        raise NotImplementedError("ServiceRegistry.register")

    def heartbeat(self, service, instance_id, *, now):
        # TODO: Look up the key; if absent return False; else set expires_at = now + the stored ttl and return True.
        raise NotImplementedError("ServiceRegistry.heartbeat")

    def deregister(self, service, instance_id):
        # TODO: pop the key with a default and return whether it existed.
        raise NotImplementedError("ServiceRegistry.deregister")

    def start_draining(self, service, instance_id):
        # TODO: Look up the key; if absent return False; else set draining = True and return True.
        raise NotImplementedError("ServiceRegistry.start_draining")

    def resolve(self, service, *, now):
        # TODO: Collect endpoints for this service where NOT draining and now < expires_at; return them sorted by str(instance_id) so callers are deterministic.
        raise NotImplementedError("ServiceRegistry.resolve")

    def sweep(self, *, now):
        # TODO: Delete every key whose now >= expires_at and return how many you removed.
        raise NotImplementedError("ServiceRegistry.sweep")


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
