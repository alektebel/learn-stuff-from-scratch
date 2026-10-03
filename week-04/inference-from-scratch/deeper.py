"""
Step 12 — Keep going deeper
===========================
The four ideas every serving paper after vLLM is about.

1. Multi-GPU tensor parallel: shard columns of each matmul. A decode
   step does an all-reduce of the partial activations. Cost is
   constant in batch (bad for decode) and why people disaggregate.
2. Prefill/decode disaggregation: prefill is compute-bound, decode is
   bandwidth-bound. Different machines. KV must move from prefill
   worker to decode worker — that transfer is the new bottleneck.
3. KV offload: blocks migrate GPU -> CPU -> disk. A hit on GPU is
   free; a hit on CPU costs a memcpy; a miss is a recompute or a page-in.
4. Routing: cache-aware routing sends a request to the replica that
   already holds its prefix. Random routing destroys prefix cache hit
   rate; the checker measures that.

TODO: the four functions. Pure logic, no real NCCL.
"""

from typing import Dict, List, Sequence, Tuple


def tp_decode_bytes(d_model: int, layers: int, world_size: int,
                    allreduce_bytes_per_layer: int) -> Dict[str, int]:
    """Bytes of matmul I/O per rank, plus all-reduce.

    TODO:
      matmul_bytes = layers * (d_model * d_model * 2) // world_size
                    (the 2 is K and V or a stand-in; just be consistent)
      comm_bytes   = layers * allreduce_bytes_per_layer
      comm_fraction = comm_bytes / (matmul_bytes + comm_bytes)
    Return those three keys. comm_fraction must RISE with world_size
    if allreduce_bytes_per_layer is held constant — that is the lesson.
    """
    raise NotImplementedError


def disagg_transfer(prefill_tokens: int, layers: int, d_model: int,
                    bytes_per: int = 2) -> int:
    """KV bytes that have to move from the prefill worker to the decode
    worker. 2 (K and V) * layers * tokens * d_model * bytes_per.
    """
    raise NotImplementedError


def offload_hit(level: str, gpu_ms: float = 0.1, cpu_ms: float = 2.0,
                disk_ms: float = 20.0) -> float:
    """TODO: return the latency of a block hit at that level.
    "gpu" / "cpu" / "disk". Unknown -> ValueError.
    """
    raise NotImplementedError


def route(request_prefix: str,
          replica_prefixes: Sequence[str]) -> int:
    """Cache-aware routing: pick the replica whose stored prefix is the
    longest prefix of request_prefix. Ties -> lowest index.

    TODO: replica_prefixes[i] is the prefix replica i already has cached.
    Return that index. An empty stored prefix matches nothing except the
    empty request (length 0), which loses to any real match.
    """
    raise NotImplementedError


def random_vs_aware(requests: Sequence[str],
                    replica_prefixes: Sequence[str],
                    random_choices: Sequence[int]
                    ) -> Dict[str, float]:
    """Hit rate = fraction of requests whose chosen replica's stored
    prefix is a (non-empty) prefix of the request.

    TODO: aware uses route(); random uses random_choices[i] for request i.
    Return {aware: float, random: float}. The checker asserts aware > random
    on a constructed workload.
    """
    raise NotImplementedError
