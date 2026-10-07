"""
Prefix-Caching Proxy — From Scratch
===================================
Requires: replica.py, policy.py.

This is a real HTTP reverse proxy in front of N replica servers. A client POSTs
`/generate` to the proxy; the proxy picks a replica, forwards the request, and
returns the replica's reply (including how many prompt tokens it reused). The
HTTP plumbing and the replica servers are provided; what you implement is the
one decision that makes the proxy a cache-aware router: **where the request
goes, decided from the prompt before it is sent**.

`Proxy.generate`:
  1. choose a replica by calling `self.policy.choose(self.replicas, prompt)`
     on the *incoming prompt* — never on a previous reply;
  2. forward `{"prompt": [...], "gen_len": n}` to that replica's `/generate`;
  3. remember the reply and return the parsed JSON.

The response's `replica` field is the fake server's own id, so callers can see
the routing decision without the proxy having to advertise it.

DESIGN DECISION - where does routing happen: in the proxy or the client?
  In the proxy, because that is the first place all replicas are visible. The
  alternative (a client library that picks a replica) pushes cache policy into
  every caller and makes it impossible to change without redeploying them.

DESIGN DECISION - in-process cache inspection or a lookup RPC to each replica?
  The proxy reads each replica's cache directly (`replica.cached_prefix_len`),
  standing in for a shared routing table a real deployment keeps in the
  scheduler. An RPC fan-out per request would be more faithful to a
  disaggregated setup but adds a round trip to the hot path and a failure mode
  (a slow replica stalls every decision) that the lesson does not need.

DESIGN DECISION - what does the proxy do on a replica error?
  It propagates the failure; retries and fallback to another replica belong to
  the gateway project (#13), not here. Keeping the proxy transparent makes the
  cache-hit comparison honest: a request is served exactly once, by exactly one
  replica.

Run `python3 proxy.py` for the demo: two requests sharing a prefix, and a third
that is cold and falls back to the least-loaded replica.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from replica import DEFAULT_GEN_LEN, post_json


class Proxy:
    """Routes prompts to replicas and forwards them over HTTP."""

    def __init__(self, replicas, policy):
        self.replicas = list(replicas)
        self.policy = policy
        self.last_response = None
        self.requests = 0

    def generate(self, prompt, gen_len=DEFAULT_GEN_LEN, timeout=5.0):
        """TODO: route on the PROMPT, forward to the chosen replica, return its reply.

        - `replica = self.policy.choose(self.replicas, list(prompt))`
          (the decision must use *this* prompt; a previous reply's tokens are a
          different sequence and will route somewhere else);
        - `reply = post_json(replica.port, "/generate",
                             {"prompt": list(prompt), "gen_len": gen_len},
                             timeout=timeout)`;
        - store it on `self.last_response`, bump `self.requests`, return `reply`.
        """
        chosen = self.policy.choose(self.replicas, list(prompt))
        reply = post_json(chosen.port, "/generate",
                          {"prompt": list(prompt), "gen_len": gen_len},
                          timeout=timeout)
        self.last_response = reply
        self.requests += 1
        return reply


class _ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):  # noqa: N802 (stdlib spelling)
        if self.path != "/generate":
            self.send_error(404, "only POST /generate")
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            prompt = body["prompt"]
            gen_len = int(body.get("gen_len", DEFAULT_GEN_LEN))
        except Exception as exc:  # noqa: BLE001
            self.send_error(400, f"bad request: {exc}")
            return
        try:
            reply = self.server.proxy.generate(prompt, gen_len)
        except NotImplementedError as exc:
            # The learner's routing is not written yet; 501 lets check.py report TODO
            # rather than a generic upstream failure.
            message = f"proxy routing not implemented: {exc}".encode()
            self.send_response(501)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)
            return
        except Exception as exc:  # noqa: BLE001
            self.send_error(502, f"upstream failure: {exc}")
            return
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # keep the test output quiet
        pass


class ProxyServer:
    """The Proxy reachable over HTTP on an ephemeral 127.0.0.1 port."""

    def __init__(self, proxy):
        self.proxy = proxy
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _ProxyHandler)
        self.httpd.daemon_threads = True
        self.httpd.proxy = proxy
        self.port = self.httpd.server_address[1]
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


def _demo():
    from replica import serve_replicas, stop_replicas
    from policy import LongestPrefixPolicy
    from workload import traced_workload

    servers = serve_replicas(3, cache_capacity=400)
    replicas = [server.replica for server in servers]
    proxy_server = ProxyServer(Proxy(replicas, LongestPrefixPolicy())).start()
    try:
        tenant_prompt = traced_workload(num_requests=1)[0]["prompt"]
        for label in ("first", "second"):
            reply = post_json(proxy_server.port, "/generate",
                              {"prompt": tenant_prompt, "gen_len": 16})
            print(f"  {label:6s} request -> replica {reply['replica']}: "
                  f"reused={reply['reused']:3d} recomputed={reply['recomputed']:3d}")
        cold = post_json(proxy_server.port, "/generate",
                         {"prompt": [9_000_000 + i for i in range(20)], "gen_len": 4})
        print(f"  cold   request -> replica {cold['replica']}: "
              f"reused={cold['reused']:3d} (fallback to least loaded)")
        print(f"  proxy handled {proxy_server.proxy.requests} requests")
    finally:
        proxy_server.stop()
        stop_replicas(servers)


if __name__ == "__main__":
    _demo()
