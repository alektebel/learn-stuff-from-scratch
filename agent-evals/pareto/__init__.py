"""pareto — agent-evals #10: cost-quality frontier per tenant.

Re-exports the public interface so that ``import pareto`` and ``python -m pareto`` both work.
"""

from .pareto import Point, dominates, frontier, main, pareto, points, render, wilson

__all__ = ["Point", "dominates", "frontier", "main", "pareto", "points", "render", "wilson"]
