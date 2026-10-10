"""Typed agent tools (phase 2): read/edit/write/glob/search over a task root.

`base` and `registry` are provided infrastructure; `fs` holds the five tool
bodies the learner writes.
"""

from harness_lab.tools.base import (  # noqa: F401
    NotFound,
    NotUnique,
    PathOutsideRoot,
    Tool,
    ToolError,
    ToolResult,
    resolve,
)
from harness_lab.tools.fs import EditFile, Glob, ReadFile, Search, WriteFile  # noqa: F401
from harness_lab.tools.registry import build_tools, call_tool, tool_specs  # noqa: F401

__all__ = [
    "EditFile",
    "Glob",
    "NotFound",
    "NotUnique",
    "PathOutsideRoot",
    "ReadFile",
    "Search",
    "Tool",
    "ToolError",
    "ToolResult",
    "WriteFile",
    "build_tools",
    "call_tool",
    "resolve",
    "tool_specs",
]
