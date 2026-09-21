# Spectral Graph Algorithms — From Scratch

## Goal

Build spectral graph algorithms to understand:
- How the graph **Laplacian matrix** encodes connectivity and cuts
- How **eigenvalues/eigenvectors** of the Laplacian reveal graph structure
- How **spectral bisection** partitions a graph into balanced halves
- How **spectral clustering** finds k natural communities
- How **PageRank** ranks nodes via the dominant eigenvector
- The **Cheeger inequality**: relating the spectral gap λ₂ to the edge conductance h(G)

---

## Background

Spectral methods turn graph problems into linear-algebra problems.
For a graph G with n nodes, the **unnormalized Laplacian** is:

```
L = D − A
```

where `A` is the adjacency matrix and `D` is the diagonal degree matrix.
`L` is symmetric positive semi-definite; its eigenvalues satisfy:

```
0 = λ₁ ≤ λ₂ ≤ … ≤ λₙ
```

Key facts:
- **λ₁ = 0** always (constant vector is in the null space)
- **λ₂ > 0** iff the graph is connected (**algebraic connectivity** / Fiedler value)
- The corresponding eigenvector (the **Fiedler vector**) encodes the "best" bisection
- The **Cheeger inequality** bounds the edge conductance: `λ₂/2 ≤ h(G) ≤ √(2λ₂)`

The **normalized Laplacian** `Lsym = D⁻¹∕²L D⁻¹∕²` is preferred for graphs with
highly variable degree because it accounts for each node's degree.

---

## Learning Path

### Phase 1 — Graph Laplacian (Beginner)

1. **Adjacency & degree matrices**
   - Build `A` from an edge list; `D[i,i] = deg(i)`
   - Verify `L·1 = 0` (all-ones vector is in the null space)

2. **Unnormalized Laplacian**
   - `L = D − A`
   - Eigendecomposition: `np.linalg.eigh(L)` (use `eigh`, not `eig`, because L is symmetric)

3. **Normalized Laplacian**
   - `Lsym = D⁻¹∕² L D⁻¹∕²`
   - Eigenvalues lie in [0, 2]; `λ = 2` iff the graph is bipartite

---

### Phase 2 — Graph Partitioning (Intermediate)

4. **Fiedler vector**
   - Second eigenvector of L (index 1 after sorting by eigenvalue)
   - Sign of each entry determines the partition: positive → set A, negative → set B

5. **Spectral bisection**
   - Threshold the Fiedler vector at 0 (or at the median for balanced cuts)
   - Count the cut edges; compare with a random bisection

---

### Phase 3 — Spectral Clustering (Intermediate)

6. **k-way spectral clustering**
   - Compute the k smallest eigenvectors of `Lsym` (skip the trivial zero eigenvector)
   - Stack them as rows to get an n×k embedding matrix
   - Run k-means on the rows
   - Nodes in the same k-means cluster belong to the same community

7. **Why it works** — the embedding maps each node to a point in ℝᵏ such that
   well-connected nodes are close together; k-means then finds natural groups

---

### Phase 4 — PageRank & Cheeger (Advanced)

8. **PageRank (power iteration)**
   - Random-surfer model: with probability `d` follow a link, with `1−d` jump anywhere
   - Transition matrix `M = d · A_col_stochastic + (1−d)/n · ones`
   - Repeat: `r ← M · r` until convergence
   - The stationary vector `r` gives the rank of each node

9. **Cheeger inequality**
   - For every subset S ⊆ V the conductance is `Φ(S) = cut(S,V\S) / min(vol(S), vol(V\S))`
   - `h(G) = minₛ Φ(S)` — expensive to compute exactly (NP-hard)
   - The Cheeger bounds connect h(G) to the spectral gap λ₂

---

## Building and Running

```bash
cd spectral-graphs/

# Run the template (will raise NotImplementedError until you fill in the TODOs)
python spectral_graphs.py

# Run the complete reference solution
python solutions/spectral_graphs_solution.py
```

---

## Directory Structure

```
spectral-graphs/
├── README.md
├── spectral_graphs.py          ← template: fill in the TODOs
└── solutions/
    └── spectral_graphs_solution.py   ← reference implementation
```

---

## Dependencies

```bash
pip install numpy
```

`numpy` is used for dense eigendecompositions and matrix operations.
For very large sparse graphs, `scipy.sparse.linalg.eigsh` can be used
as a drop-in replacement for `np.linalg.eigh` to compute only the k
smallest eigenpairs efficiently.

---

## Resources

### Books
- [Spectral Graph Theory — Fan Chung (free PDF)](https://mathweb.ucsd.edu/~fan/research/revised.html)
- [Graph Theory and Its Applications — Gross & Yellen](https://www.routledge.com/Graph-Theory-and-Its-Applications/Gross-Yellen-Zhang/p/book/9781584885054)
- [Mathematics for Machine Learning — Deisenroth et al.](https://mml-book.com)

### Papers & Lectures
- [A Tutorial on Spectral Clustering — von Luxburg (2007)](https://arxiv.org/abs/0711.0189)
- [Normalized Cuts and Image Segmentation — Shi & Malik (2000)](https://people.eecs.berkeley.edu/~malik/papers/SM-ncut.pdf)
- [The PageRank Citation Ranking: Bringing Order to the Web — Page et al. (1999)](http://ilpubs.stanford.edu:8090/422/)

### Courses
- [CS224W: Machine Learning with Graphs (Stanford)](https://web.stanford.edu/class/cs224w/)
- [Spectral Graph Theory (Yale)](https://cs.yale.edu/homes/spielman/561/)

## Sources

- von Luxburg, **"A Tutorial on Spectral Clustering"**, 2007 — start here; it explains which Laplacian to use and why it matters.
- Shi & Malik, **"Normalized Cuts and Image Segmentation"**, PAMI 2000.
- Chung, **Spectral Graph Theory** — the book, for the eigenvalue bounds.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-18--the-tail)
