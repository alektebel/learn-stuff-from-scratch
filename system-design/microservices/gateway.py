"""An API gateway: path routing, client-side load balancing, and safe retries.

Source: the API Gateway and Backend-for-Frontend patterns; Envoy/Istio retry policy;
RFC 9110 (HTTP semantics) on idempotent methods. A gateway is the single front door for a
set of services: it maps a request path to a service, chooses one healthy instance, and
retries only when doing so cannot duplicate an effect.

DESIGN DECISION - how are paths routed?
    Longest matching prefix wins, and a prefix matches only on a path boundary
    (`/api` matches `/api/orders` and `/api`, not `/apis`). Naive `startswith` routing
    sends `/apix` to the `/api` service. Cost: no regex or header-based routing.

DESIGN DECISION - client-side round-robin or server-side LB?
    The gateway is a client of the registry and picks the instance itself, so it can
    spread load without a second hop. Server-side LB (a separate load balancer) hides
    instances but adds a hop and a second health model. We round-robin over the resolved
    healthy instances; a stateless gateway replica needs no coordination with the others.
    Cost: uneven instance capacities are ignored (least-connections would adapt).

DESIGN DECISION - when is a request safe to retry?
    Only when the method is idempotent (GET, HEAD, PUT, DELETE, OPTIONS) AND the failure
    could be transient (a 5xx or a connection error). A 4xx is the client's fault:
    retrying cannot help. A POST may have already created something, so retrying it can
    duplicate a side effect; the application must make it idempotent (an idempotency key)
    before the gateway may retry it.
    Cost: a POST that failed on a flaky connection is surfaced to the client instead of
    being retried for it.

DESIGN DECISION - re-pick on retry?
    Yes: a retry is a new attempt against a freshly chosen healthy instance, which is what
    turns one dead replica into a non-event. Retrying the same endpoint would just fail
    again.
    Cost: a request may be served by an instance that is behind (no read-your-writes).
"""

__all__ = ["Gateway"]

IDEMPOTENT = frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS"})


class Gateway:
    def __init__(self, registry, routes, *, max_retries=2):
        # routes: list of (prefix, service); the longest matching prefix wins
        self.registry = registry
        self.routes = list(routes)
        self.max_retries = max_retries
        self._next = {}  # service -> next round-robin index

    def match(self, path):
        # TODO: Longest matching prefix where path == prefix or path starts with prefix.rstrip('/') + '/'. A bare '/' route catches everything. Return the service or None.
        raise NotImplementedError("Gateway.match")

    def pick(self, service, *, now):
        # TODO: endpoints = registry.resolve(service, now); None if empty; otherwise index = self._next.get(service, 0) % len, bump self._next[service] = index + 1, return endpoints[index].
        raise NotImplementedError("Gateway.pick")

    def call(self, method, path, *, now, invoke):
        # TODO: service = match(path); None -> 404. Attempt up to max_retries + 1 times: pick an instance (None -> 503), invoke it, treat ConnectionError as 503; return as soon as status < 500; a 5xx is retried only if method is in IDEMPOTENT; after the loop return the last status.
        raise NotImplementedError("Gateway.call")


if __name__ == "__main__":
    from registry import ServiceRegistry

    registry = ServiceRegistry()
    registry.register("orders", "a", "10.0.0.1:80", ttl=60, now=0.0)
    registry.register("orders", "b", "10.0.0.2:80", ttl=60, now=0.0)
    gateway = Gateway(registry, [("/", "orders")], max_retries=2)

    seen = []

    def flaky(endpoint):
        seen.append(endpoint)
        return 500 if len(seen) == 1 else 200

    print(f"GET /orders -> {gateway.call('GET', '/orders', now=0.0, invoke=flaky)} "
          f"after trying {seen} (retried on a fresh instance)")

    seen.clear()

    def post_once(endpoint):
        seen.append(endpoint)
        return 500

    print(f"POST /orders -> {gateway.call('POST', '/orders', now=0.0, invoke=post_once)} "
          f"after trying {seen} (a POST is never retried: side effects)")
