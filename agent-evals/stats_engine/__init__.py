"""stats_engine -- agent-evals #7: paired bootstrap comparison over tasks.

Re-exports the public interface from stats_engine.stats_engine so that
``import stats_engine`` and ``python -m stats_engine`` both work.
"""

from .stats_engine import (
    REQUIRED_FIELDS,
    compare,
    main,
    paired_bootstrap_ci,
    paired_bootstrap_p,
    parse_jsonl,
    summarise_by_task,
)

__all__ = [
    "REQUIRED_FIELDS",
    "compare",
    "main",
    "paired_bootstrap_ci",
    "paired_bootstrap_p",
    "parse_jsonl",
    "summarise_by_task",
]
