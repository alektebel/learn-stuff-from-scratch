"""drift_monitor — agent-evals #9: find a quality regression in a trace.

Re-exports the public interface so that ``import drift_monitor`` and
``python -m drift_monitor`` both work.
"""

from .drift_monitor import (
    Alert,
    MonitorConfig,
    all_alerts,
    main,
    monitor,
    monitor_by,
    render,
)

__all__ = [
    "Alert",
    "MonitorConfig",
    "all_alerts",
    "main",
    "monitor",
    "monitor_by",
    "render",
]
