"""The tool interface (phase 2, LEARN mode) — provided infrastructure.

A tool is typed: it advertises a JSON-schema `ToolSpec` the model sees, and it
runs inside the task root. The rule that matters is at the boundary: a tool
turns a bad call into a `ToolResult`, it does not raise into the loop. That is
the same discipline phase 1 applied to malformed bash arguments
(`harness_lab/core/loop.py::_decode_command`): one bad call ends that call, not
the run.

Sources
-------
- Claude Code tool documentation (Read/Edit/Write/Glob/Grep): the exact-substring
  edit that must be unique is the Edit contract; Read returns a numbered window;
  Glob and Grep are read-only discovery.
- OpenHands / aider file-edit tools: a failed edit is reported back to the model
  as text it can act on, never as an exception.

DESIGN DECISION — tools return `ToolResult`, they do not raise at the boundary.
  A `ToolError` is still raised internally by the provided plumbing (the path
  guard) and is caught once, in `registry.call_tool`, so both styles — return a
  failure or raise a `ToolError` — reach the model as the same text. Cost: the
  caller must check `.ok` instead of using try/except.

DESIGN DECISION — every path is resolved under the task root first.
  `resolve` refuses anything that escapes the root, so a tool cannot read or
  write outside its task even if the model is talked into `../../etc/passwd`.
  Cost: absolute symlinks inside the root that point out of it are refused too.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from harness_lab.llm.base import ToolSpec

__all__ = [
    "ToolError",
    "PathOutsideRoot",
    "NotFound",
    "NotUnique",
    "ToolResult",
    "Tool",
    "resolve",
]


class ToolError(Exception):
    """A user-facing tool failure: reported to the model as text, never fatal."""


class PathOutsideRoot(ToolError):
    """The requested path is not inside the task root."""


class NotFound(ToolError):
    """The requested file does not exist (or is not a file)."""


class NotUnique(ToolError):
    """An edit's `old` text occurs zero or more than one time."""


@dataclass(frozen=True)
class ToolResult:
    """What a tool returns: success plus output, or a failure plus a reason."""

    ok: bool
    output: str = ""
    error: str | None = None

    @classmethod
    def success(cls, output: str = "") -> "ToolResult":
        return cls(True, output, None)

    @classmethod
    def failure(cls, error: str) -> "ToolResult":
        return cls(False, "", error)


class Tool(Protocol):
    spec: ToolSpec

    def run(self, **kwargs) -> ToolResult: ...


def resolve(root, relative: str) -> Path:
    """Resolve `relative` under `root`, refusing any escape.

    Raises `PathOutsideRoot` when the result is outside the root (a `..` walk or
    an absolute path). The root itself is allowed (`.` resolves to it).
    """
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise PathOutsideRoot(f"{relative!r} is outside the task root")
    return candidate


if __name__ == "__main__":
    import tempfile

    root = Path(tempfile.mkdtemp())
    (root / "a.txt").write_text("hi")
    print("tool path guard")
    print(f"  resolve('.') -> {resolve(root, '.')}")
    print(f"  resolve('a.txt') -> {resolve(root, 'a.txt')}")
    for bad in ("../secret", "/etc/passwd"):
        try:
            resolve(root, bad)
            print(f"  resolve({bad!r}) -> !!! allowed")
        except PathOutsideRoot as exc:
            print(f"  resolve({bad!r}) -> refused: {exc}")
