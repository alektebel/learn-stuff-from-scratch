"""
Spectral Graph Algorithms — Reference Solution
===============================================
Complete implementations of all algorithms in spectral_graphs.py.

Run: python solutions/spectral_graphs_solution.py
"""

import itertools
import math
from typing import Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

class Graph:
    """Undirected weighted graph stored as a dense adjacency matrix."""

    def __init__(self, n: int) -> None:
        self.n = n
        self._adj: np.ndarray = np.zeros((n, n), dtype=float)

    def add_edge(self, u: int, v: int, weight: float = 1.0) -> None:
        self._adj[u, v] = weight
        self._adj[v, u] = weight

    def adjacency_matrix(self) -> np.ndarray:
        return self._adj.copy()

    def degree_matrix(self) -> np.ndarray:
        """Return the n×n diagonal degree matrix."""
        degrees = self._adj.sum(axis=1)          # weighted degree of each node
        return np.diag(degrees)

    def edges(self) -> List[Tuple[int, int, float]]:
        result = []
        for u in range(self.n):
            for v in range(u + 1, self.n):
                if self._adj[u, v] != 0.0:
                    result.append((u, v, float(self._adj[u, v])))
        return result


# ---------------------------------------------------------------------------
# Spectral algorithms
# ---------------------------------------------------------------------------

class SpectralGraph:
    """Collection of spectral graph algorithms."""

    # ------------------------------------------------------------------
    # Phase 1 — Laplacians
    # ------------------------------------------------------------------

    def laplacian(self, graph: Graph) -> np.ndarray:
        """Compute the unnormalized graph Laplacian L = D − A."""
        D = graph.degree_matrix()
        A = graph.adjacency_matrix()
        return D - A

    def normalized_laplacian(self, graph: Graph) -> np.ndarray:
        """Compute the symmetric normalized Laplacian Lsym = D^{-1/2} L D^{-1/2}."""
        L = self.laplacian(graph)
        # degrees from the diagonal of D
        degrees = np.diag(graph.degree_matrix())
        d_inv_sqrt = np.where(degrees > 0, 1.0 / np.sqrt(degrees), 0.0)
        D_inv_sqrt = np.diag(d_inv_sqrt)
        return D_inv_sqrt @ L @ D_inv_sqrt

    # ------------------------------------------------------------------
    # Phase 2 — Graph Partitioning
    # ------------------------------------------------------------------

    def fiedler_vector(self, graph: Graph) -> np.ndarray:
        """Compute the Fiedler vector (eigenvector for the second smallest eigenvalue)."""
        L = self.laplacian(graph)
        eigenvalues, eigenvectors = np.linalg.eigh(L)
        # eigh returns eigenvectors as columns sorted by ascending eigenvalue
        return eigenvectors[:, 1]

    def spectral_bisection(
        self, graph: Graph
    ) -> Tuple[List[int], List[int]]:
        """Partition nodes into two sets via the sign of the Fiedler vector."""
        fiedler = self.fiedler_vector(graph)
        partition_a = [i for i, v in enumerate(fiedler) if v >= 0]
        partition_b = [i for i, v in enumerate(fiedler) if v < 0]
        return partition_a, partition_b

    # ------------------------------------------------------------------
    # Phase 3 — Spectral Clustering
    # ------------------------------------------------------------------

    def spectral_embedding(self, graph: Graph, k: int) -> np.ndarray:
        """Build an n×k spectral embedding from the k smallest non-trivial eigenvectors."""
        Lsym = self.normalized_laplacian(graph)
        eigenvalues, eigenvectors = np.linalg.eigh(Lsym)
        # Take eigenvectors at indices 1 … k (skip the trivial zero eigenvector)
        embedding = eigenvectors[:, 1 : k + 1]   # shape n×k
        # Row-normalise (skip zero-norm rows for isolated nodes)
        norms = np.linalg.norm(embedding, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        return embedding / norms

    def spectral_clustering(
        self,
        graph: Graph,
        k: int,
        max_iter: int = 300,
        n_init: int = 10,
        random_state: Optional[int] = None,
    ) -> List[int]:
        """Cluster nodes into k groups using spectral clustering."""
        X = self.spectral_embedding(graph, k)
        return self._kmeans(X, k, max_iter, n_init, random_state)

    # ------------------------------------------------------------------
    # Phase 4 — PageRank & Cheeger
    # ------------------------------------------------------------------

    def pagerank(
        self,
        graph: Graph,
        damping: float = 0.85,
        max_iter: int = 100,
        tol: float = 1e-6,
    ) -> np.ndarray:
        """Compute PageRank scores via power iteration."""
        n = graph.n
        A = graph.adjacency_matrix()

        # Build column-stochastic matrix P (avoid division by zero warnings)
        col_sums = A.sum(axis=0)
        safe_sums = np.where(col_sums > 0, col_sums, 1.0)
        P = A / safe_sums
        P[:, col_sums == 0] = 1.0 / n   # dangling nodes teleport uniformly

        # Power iteration — apply teleportation as a scalar term (avoids n×n matrix)
        r = np.ones(n) / n
        for _ in range(max_iter):
            r_new = damping * (P @ r) + (1.0 - damping) / n
            if np.abs(r_new - r).sum() < tol:
                break
            r = r_new
        return r_new

    def cheeger_constant(self, graph: Graph) -> float:
        """Compute the exact Cheeger constant h(G) by exhaustive subset enumeration."""
        n = graph.n
        A = graph.adjacency_matrix()
        degrees = A.sum(axis=1)
        vol_total = degrees.sum()

        h = float("inf")
        all_nodes = list(range(n))

        # Enumerate all non-empty proper subsets
        for size in range(1, n):
            for subset in itertools.combinations(all_nodes, size):
                s_set = set(subset)
                complement = [v for v in all_nodes if v not in s_set]

                vol_s = sum(degrees[i] for i in s_set)
                min_vol = min(vol_s, vol_total - vol_s)
                if min_vol == 0:
                    continue

                cut = sum(
                    A[u, v]
                    for u in s_set
                    for v in complement
                )
                phi = cut / min_vol
                if phi < h:
                    h = phi

        return h

    def verify_cheeger_inequality(
        self, graph: Graph
    ) -> Dict[str, float]:
        """Verify λ₂/2 ≤ h(G) ≤ √(2·λ₂).

        The Cheeger inequality uses λ₂ of the *normalized* Laplacian Lsym.
        """
        Lsym = self.normalized_laplacian(graph)
        eigenvalues = np.linalg.eigh(Lsym)[0]
        lambda2 = float(sorted(eigenvalues)[1])

        h = self.cheeger_constant(graph)
        lower_bound = lambda2 / 2.0
        upper_bound = math.sqrt(2.0 * lambda2)

        return {
            "lambda2": lambda2,
            "h": h,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "lower_satisfied": float(lower_bound <= h + 1e-9),
            "upper_satisfied": float(h <= upper_bound + 1e-9),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _kmeans(
        X: np.ndarray,
        k: int,
        max_iter: int,
        n_init: int,
        random_state: Optional[int],
    ) -> List[int]:
        """Simple k-means (no external libraries required)."""
        rng = np.random.default_rng(random_state)
        n = X.shape[0]
        best_labels: Optional[np.ndarray] = None
        best_inertia = float("inf")

        for _ in range(n_init):
            idx = rng.choice(n, size=k, replace=False)
            centroids = X[idx].copy()

            labels = np.zeros(n, dtype=int)
            for _iter in range(max_iter):
                dists = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)
                new_labels = np.argmin(dists, axis=1)

                if np.array_equal(new_labels, labels) and _iter > 0:
                    break
                labels = new_labels

                for c in range(k):
                    members = X[labels == c]
                    if len(members) > 0:
                        centroids[c] = members.mean(axis=0)

            inertia = sum(
                float(np.linalg.norm(X[i] - centroids[labels[i]]) ** 2)
                for i in range(n)
            )
            if inertia < best_inertia:
                best_inertia = inertia
                best_labels = labels.copy()

        return list(best_labels)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _build_path_graph(n: int) -> Graph:
    """Build a path graph 0 — 1 — 2 — … — (n-1)."""
    g = Graph(n)
    for i in range(n - 1):
        g.add_edge(i, i + 1)
    return g


def _build_cycle_graph(n: int) -> Graph:
    """Build a cycle graph 0 — 1 — … — (n-1) — 0."""
    g = Graph(n)
    for i in range(n):
        g.add_edge(i, (i + 1) % n)
    return g


def _build_two_cliques(k: int) -> Graph:
    """Build two k-cliques connected by a single bridge edge."""
    n = 2 * k
    g = Graph(n)
    for i in range(k):
        for j in range(i + 1, k):
            g.add_edge(i, j)
    for i in range(k, n):
        for j in range(i + 1, n):
            g.add_edge(i, j)
    # single bridge
    g.add_edge(k - 1, k)
    return g


def _test() -> None:
    sg = SpectralGraph()
    tol = 1e-8

    # ------------------------------------------------------------------
    print("=== Phase 1: Laplacians ===")

    g4 = _build_cycle_graph(4)

    # degree matrix
    D = g4.degree_matrix()
    assert D.shape == (4, 4), "degree_matrix shape"
    assert np.allclose(np.diag(D), [2, 2, 2, 2]), "cycle-4 degrees"
    print("  degree_matrix: OK")

    # unnormalized Laplacian — L·1 = 0
    L = sg.laplacian(g4)
    ones = np.ones(4)
    assert np.allclose(L @ ones, np.zeros(4), atol=tol), "L·1 should be 0"
    assert np.allclose(L, L.T, atol=tol), "L should be symmetric"
    print("  laplacian (L·1=0, symmetric): OK")

    # normalized Laplacian — eigenvalues in [0,2]
    Lsym = sg.normalized_laplacian(g4)
    eigs = np.linalg.eigh(Lsym)[0]
    assert np.all(eigs >= -tol), "Lsym eigenvalues >= 0"
    assert np.all(eigs <= 2.0 + tol), "Lsym eigenvalues <= 2"
    print("  normalized_laplacian (eigenvalues in [0,2]): OK")

    # ------------------------------------------------------------------
    print("\n=== Phase 2: Graph Partitioning ===")

    g_two = _build_two_cliques(4)   # two 4-cliques + bridge
    fv = sg.fiedler_vector(g_two)
    assert fv.shape == (8,), "fiedler_vector shape"
    # The two cliques should have opposite signs
    clique_a_signs = np.sign(fv[:4])
    clique_b_signs = np.sign(fv[4:])
    assert np.all(clique_a_signs == clique_a_signs[0]), "clique A same sign"
    assert np.all(clique_b_signs == clique_b_signs[0]), "clique B same sign"
    assert clique_a_signs[0] != clique_b_signs[0], "cliques have opposite signs"
    print("  fiedler_vector (two-clique sign test): OK")

    pa, pb = sg.spectral_bisection(g_two)
    assert set(pa) | set(pb) == set(range(8)), "bisection covers all nodes"
    assert set(pa) & set(pb) == set(), "bisection is disjoint"
    assert set(pa) in ({0,1,2,3}, {4,5,6,7}), "bisection recovers cliques"
    print("  spectral_bisection: OK")

    # ------------------------------------------------------------------
    print("\n=== Phase 3: Spectral Clustering ===")

    g_two2 = _build_two_cliques(5)  # two 5-cliques
    labels = sg.spectral_clustering(g_two2, k=2, random_state=42)
    assert len(labels) == 10, "clustering label count"
    # Both cliques should receive the same intra-clique label
    assert len(set(labels[:5])) == 1, "clique A should be one cluster"
    assert len(set(labels[5:])) == 1, "clique B should be one cluster"
    assert labels[0] != labels[5], "the two cliques get different labels"
    print("  spectral_clustering (two 5-cliques): OK")

    # ------------------------------------------------------------------
    print("\n=== Phase 4: PageRank ===")

    # Simple chain: higher-indegree nodes should rank higher
    g_chain = Graph(4)
    g_chain.add_edge(0, 1)
    g_chain.add_edge(1, 2)
    g_chain.add_edge(2, 1)  # 1 and 2 point to each other
    g_chain.add_edge(2, 3)
    r = sg.pagerank(g_chain, damping=0.85, max_iter=200)
    assert r.shape == (4,), "pagerank shape"
    assert abs(r.sum() - 1.0) < 1e-5, f"pagerank should sum to 1, got {r.sum()}"
    print(f"  pagerank (scores): {np.round(r, 4)}: OK")

    # ------------------------------------------------------------------
    print("\n=== Phase 4: Cheeger Inequality ===")

    g_small = _build_cycle_graph(6)
    info = sg.verify_cheeger_inequality(g_small)
    assert info["lower_satisfied"] == 1.0, (
        f"Cheeger lower bound violated: λ₂/2={info['lower_bound']:.4f} > h={info['h']:.4f}"
    )
    assert info["upper_satisfied"] == 1.0, (
        f"Cheeger upper bound violated: h={info['h']:.4f} > √(2λ₂)={info['upper_bound']:.4f}"
    )
    print(
        f"  Cheeger (6-cycle): λ₂={info['lambda2']:.4f}, h={info['h']:.4f}, "
        f"bounds=[{info['lower_bound']:.4f}, {info['upper_bound']:.4f}]: OK"
    )

    # ------------------------------------------------------------------
    print("\nAll tests passed!")


if __name__ == "__main__":
    _test()
