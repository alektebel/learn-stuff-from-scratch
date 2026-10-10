"""The tool registry (phase 2, provided infrastructure).

Ties the tools to the loop: `build_tools(root)` constructs one instance of each
typed tool bound to a task root; `tool_specs` is what the loop advertises to the
model; `call_tool` decodes a model's JSON arguments and runs the named tool,
turning any failure into a `ToolResult` the model can read.

This is the one place that catches `ToolError`, so the loop never sees an
exception from a bad tool call (mirrors `_decode_command` in phase 1).
"""

from __future__ import annotations

import json
from typing import Mapping, Sequence

from harness_lab.llm.base import ToolSpec
from harness_lab.tools.base import Tool, ToolError, ToolResult
from harness_lab.tools.fs import EditFile, Glob, ReadFile, Search, WriteFile

TOOL_CLASSES: tuple[type, ...] = (ReadFile, WriteFile, EditFile, Glob, Search)


def build_tools(root) -> dict[str, Tool]:
    """One instance of every typed tool, bound to `root`, keyed by tool name."""
    return {cls.spec.name: cls(root) for cls in TOOL_CLASSES}


def tool_specs(tools: Mapping[str, Tool]) -> list[ToolSpec]:
    """The JSON-schema specs, in a stable (name-sorted) order."""
    return [tools[name].spec for name in sorted(tools)]


def call_tool(tools: Mapping[str, Tool], name: str, arguments) -> ToolResult:
    """Run `name` with `arguments` (a JSON string or a dict) and return a result.

    Never raises for a bad call: an unknown tool, malformed JSON, non-object
    arguments, a missing/extra keyword or a `ToolError` all come back as
    `ToolResult.failure(...)`. Unexpected exceptions still propagate — those are
    bugs, not user errors.
    """
    tool = tools.get(name)
    if tool is None:
        return ToolResult.failure(f"unknown tool {name!r}")
    payload = arguments
    if isinstance(arguments, str):
        try:
            payload = json.loads(arguments)
        except (json.JSONDecodeError, TypeError):
            return ToolResult.failure("tool arguments were not valid JSON")
    if not isinstance(payload, dict):
        return ToolResult.failure("tool arguments were not a JSON object")
    try:
        return tool.run(**payload)
    except ToolError as exc:
        return ToolResult.failure(str(exc))
    except TypeError as exc:
        return ToolResult.failure(f"bad arguments for {name!r}: {exc}")


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    root = Path(tempfile.mkdtemp())
    tools = build_tools(root)
    print("tool registry — typed tools")
    print("  specs:", ", ".join(spec.name for spec in tool_specs(tools)))
    print("  unknown tool ->", call_tool(tools, "nope", "{}").error)
    print("  bad json     ->", call_tool(tools, "read_file", "{not json").error)
