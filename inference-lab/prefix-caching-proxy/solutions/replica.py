"""
Fake Inference Replicas with a Token-Level Prefix Cache
=======================================================
Provided infrastructure for the prefix-caching proxy: this file is *not* what
you implement. It gives you N identical "servers", each holding its own prefix
cache, behind a tiny stdlib HTTP endpoint.

What a replica does with one request:
  1. match the incoming prompt against its cache -> `reused` tokens
  2. recompute the rest                         -> `recomputed = len(prompt) - reused`
  3. generate deterministic output tokens
  4. insert prompt + output back into its cache, so the *next* request that
     shares that prefix pays less prefill.

Why this matters for the proxy: the same request placed on a warm replica and
on a cold one produces a completely different `reused`/`recomputed` split. The
router you build decides which one happens.

DESIGN DECISION - how is the prefix cache shaped?
  A token trie: one node per token, shared prefixes physically shared, and
  `size` counts *unique* stored tokens. The alternative is a list of whole
  sequences matched by pairwise comparison; it is simpler but does not share
  storage, so eviction cannot tell a hot shared system prompt from a cold
  unique tail. The trie costs a `refs` counter per node, but it makes "shared
  prefixes survive, unique tails evict" fall out of the structure.

DESIGN DECISION - what counts against cache capacity?
  Unique tokens with at least one live sequence, not sequence count. A 48-token
  system prompt reused by 100 requests is 48 tokens, not 4800. This is the
  property that makes prefix caching worth doing, so the model has to price it
  correctly.

DESIGN DECISION - what gets inserted?
  The whole served sequence (prompt + generated output), as a real engine does.
  Output tokens are request-specific, so they are exactly the pollution the
  router has to work around: prefix affinity keeps prompts warm, but every
  request still drags unique tail tokens through the cache.

DESIGN DECISION - output tokens?
  `model_output` is a pure function of the prompt and generation length, and is
  deliberately independent of the replica. Any replica returns the same tokens,
  so a correctness check can recompute the expected answer without knowing
  which replica served it.

Run `python3 replica.py` for the demo: two requests sharing a prefix on one
replica, then the same traffic scattered as a cold repeat.
"""

import http.client
import json
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_CACHE_TOKENS = 400
DEFAULT_GEN_LEN = 16
_HTTP_TIMEOUT = 5.0


def model_output(prompt, gen_len=DEFAULT_GEN_LEN):
    """Deterministic generated tokens: a pure function of prompt and gen_len."""
    seed = 0
    for token in prompt:
        seed = (seed * 1000003 + token + 1) & 0xFFFFFFFFFFFFFFFF
    out = []
    for _ in range(gen_len):
        seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        out.append((seed >> 17) % 50000)
    return out


class _Node:
    __slots__ = ("children", "refs")

    def __init__(self):
        self.children = {}
        self.refs = 0


class PrefixCache:
    """Token trie with LRU eviction of whole sequences."""

    def __init__(self, capacity_tokens=DEFAULT_CACHE_TOKENS):
        self.capacity = capacity_tokens
        self.root = _Node()
        self.size = 0
        self._seqs = OrderedDict()

    def match(self, tokens):
        """Longest cached prefix length of `tokens`."""
        node = self.root
        i = 0
        n = len(tokens)
        while i < n:
            child = node.children.get(tokens[i])
            if child is None:
                break
            node = child
            i += 1
        return i

    def insert(self, tokens):
        """Store a sequence; return the number of new unique tokens held."""
        key = tuple(tokens)
        if key in self._seqs:
            self._seqs.move_to_end(key)
            return 0
        node = self.root
        created = 0
        for token in tokens:
            child = node.children.get(token)
            if child is None:
                child = _Node()
                node.children[token] = child
                created += 1
            child.refs += 1
            node = child
        self._seqs[key] = True
        self.size += created
        self._evict()
        return created

    def _evict(self):
        while self.size > self.capacity and len(self._seqs) > 1:
            key = next(iter(self._seqs))
            self._seqs.pop(key)
            self._drop_path(key)

    def _drop_path(self, key):
        node = self.root
        path = []
        for token in key:
            child = node.children[token]
            path.append((node, token, child))
            node = child
        for parent, token, child in reversed(path):
            child.refs -= 1
            if child.refs <= 0:
                del parent.children[token]
                self.size -= 1


class Replica:
    """One inference replica: a prefix cache plus accounting."""

    def __init__(self, replica_id, cache_capacity=DEFAULT_CACHE_TOKENS):
        self.id = replica_id
        self.port = None
        self.cache = PrefixCache(cache_capacity)
        self.load = 0          # tokens recomputed so far (work not already cached)
        self.active = 0        # requests currently in flight
        self.requests = 0
        self.tokens_reused = 0
        self.tokens_recomputed = 0

    def cached_prefix_len(self, prompt):
        return self.cache.match(prompt)

    def handle(self, prompt, gen_len=DEFAULT_GEN_LEN):
        prompt = list(prompt)
        reused = self.cache.match(prompt)
        recomputed = len(prompt) - reused
        output = model_output(prompt, gen_len)
        self.cache.insert(prompt + output)
        self.requests += 1
        self.tokens_reused += reused
        self.tokens_recomputed += recomputed
        self.load += recomputed
        return {
            "replica": self.id,
            "reused": reused,
            "recomputed": recomputed,
            "gen_len": gen_len,
            "output": output,
        }

    @property
    def hit_rate(self):
        total = self.tokens_reused + self.tokens_recomputed
        return self.tokens_reused / total if total else 0.0


class _Handler(BaseHTTPRequestHandler):
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
        result = self.server.replica.handle(prompt, gen_len)
        data = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # keep the test output quiet
        pass


class ReplicaServer:
    """A Replica reachable over HTTP on an ephemeral 127.0.0.1 port."""

    def __init__(self, replica):
        self.replica = replica
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.daemon_threads = True
        self.httpd.replica = replica
        self.port = self.httpd.server_address[1]
        replica.port = self.port
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


def post_json(port, path, obj, timeout=_HTTP_TIMEOUT):
    """POST a JSON object to 127.0.0.1:port and return the parsed JSON reply."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("POST", path, json.dumps(obj).encode(),
                     {"Content-Type": "application/json"})
        response = conn.getresponse()
        data = response.read()
        if response.status == 501:
            raise NotImplementedError(data.decode("utf-8", "replace"))
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {data!r}")
        return json.loads(data)
    finally:
        conn.close()


def serve_replicas(n=3, cache_capacity=DEFAULT_CACHE_TOKENS):
    """Start n replicas and return their ReplicaServer objects (already running)."""
    servers = []
    try:
        for i in range(n):
            servers.append(ReplicaServer(Replica(i, cache_capacity)).start())
    except Exception:
        stop_replicas(servers)
        raise
    return servers


def stop_replicas(servers):
    for server in servers:
        try:
            server.stop()
        except Exception:  # noqa: BLE001 - best effort shutdown
            pass


def _demo():
    print("replica prefix cache — reused vs recomputed on one replica")
    replica = Replica(0, cache_capacity=200)
    base = list(range(1000, 1048))
    first = replica.handle(base + list(range(2000, 2008)), 8)
    second = replica.handle(base + list(range(3000, 3008)), 8)
    print(f"  request 1 (cold): reused={first['reused']:3d} recomputed={first['recomputed']:3d}")
    print(f"  request 2 (same {len(base)}-token prefix): "
          f"reused={second['reused']:3d} recomputed={second['recomputed']:3d}")
    cold = Replica(1, cache_capacity=200).handle(base + list(range(4000, 4008)), 8)
    print(f"  same prompt on a cold replica: reused={cold['reused']:3d}")
    print(f"  cache holds {replica.cache.size} unique tokens of {replica.cache.capacity}")


if __name__ == "__main__":
    _demo()
