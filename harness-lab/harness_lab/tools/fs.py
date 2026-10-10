"""The five typed filesystem tools (phase 2, LEARN mode).

Each class advertises a `ToolSpec` (provided) and implements `run(**kwargs)`
(the learner's work). A tool returns a `ToolResult`; it may raise a `ToolError`
for a user-facing failure, which `registry.call_tool` turns into a failure
result. Paths are resolved with `base.resolve`, so a tool cannot escape its task
root.

Contract (docs/phase2.md has the reasoning):

- `read_file(path, offset=1, limit=2000)` → the file's lines `[offset, offset +
  limit)` joined; a missing file or a non-text file is a failure; an offset or
  limit below 1 is a failure; an offset past the end is an empty success.
- `write_file(path, content)` → create or overwrite, creating parent
  directories; success text names the path.
- `edit_file(path, old, new)` → replace the **single** occurrence of `old`.
  Empty `old`, `old` absent, or `old` present more than once are failures.
- `glob(pattern)` → matching files relative to the root, sorted, one per line;
  no matches is an empty success.
- `search(pattern, path=".")` → `relative_path:line_number:line` for every line
  a regex matches, sorted; an invalid regex is a failure.

DESIGN DECISION — `edit_file` replaces by exact substring and requires uniqueness.
  It cannot be an index-based edit (the model does not know byte offsets) nor a
  fuzzy one (phase 2 is exact; fuzzy edits are a phase-4 variant). Cost: the
  model must quote enough context to make `old` unique, and a common slip — a
  short `old` — fails loudly instead of corrupting the file.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness_lab.llm.base import ToolSpec
from harness_lab.tools.base import NotFound, NotUnique, ToolError, ToolResult, resolve

__all__ = ["ReadFile", "WriteFile", "EditFile", "Glob", "Search"]


class ReadFile:
    spec = ToolSpec(
        name="read_file",
        description=("Read a text file from the task root. `offset` is the 1-based "
                     "first line and `limit` the maximum number of lines."),
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"},
                           "offset": {"type": "integer"},
                           "limit": {"type": "integer"}},
            "required": ["path"],
        },
    )

    def __init__(self, root) -> None:
        self.root = root

    def run(self, path: str, offset: int = 1, limit: int = 2000) -> ToolResult:
        # TODO: resolve(path); a missing file or non-text file is a NotFound/ToolError;
        # offset or limit below 1 is a ToolError; otherwise return the lines
        # [offset, offset + limit) joined (an offset past the end is an empty success).
        raise NotImplementedError("ReadFile.run")


class WriteFile:
    spec = ToolSpec(
        name="write_file",
        description=("Create or overwrite a text file in the task root, creating "
                     "parent directories as needed."),
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    )

    def __init__(self, root) -> None:
        self.root = root

    def run(self, path: str, content: str) -> ToolResult:
        # TODO: resolve(path); refuse the task root itself; mkdir the parents;
        # write the content; return a success whose output names the path.
        raise NotImplementedError("WriteFile.run")


class EditFile:
    spec = ToolSpec(
        name="edit_file",
        description=("Replace the single occurrence of `old` with `new` in a file. "
                     "Fails if `old` is absent or appears more than once."),
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}, "old": {"type": "string"},
                           "new": {"type": "string"}},
            "required": ["path", "old", "new"],
        },
    )

    def __init__(self, root) -> None:
        self.root = root

    def run(self, path: str, old: str, new: str) -> ToolResult:
        # TODO: resolve(path); require an existing file; reject an empty `old`; count
        # text.count(old) and reject 0 (ToolError "not found") or >1 (NotUnique); else
        # write back the single replacement.
        raise NotImplementedError("EditFile.run")


class Glob:
    spec = ToolSpec(
        name="glob",
        description=("List files under the task root matching a glob pattern, "
                     "e.g. '**/*.py'. Paths are relative to the root."),
        parameters={
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    )

    def __init__(self, root) -> None:
        self.root = root

    def run(self, pattern: str) -> ToolResult:
        # TODO: glob the pattern under the resolved root, keep the files, and return
        # their root-relative posix paths sorted, one per line (empty success if none).
        raise NotImplementedError("Glob.run")


class Search:
    spec = ToolSpec(
        name="search",
        description=("Search file contents under a path with a regular expression; "
                     "returns 'path:line:match' for each matching line."),
        parameters={
            "type": "object",
            "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}},
            "required": ["pattern"],
        },
    )

    def __init__(self, root) -> None:
        self.root = root

    def run(self, pattern: str, path: str = ".") -> ToolResult:
        # TODO: compile the regex (an invalid one is a ToolError); pick the single file
        # or walk the directory; return 'rel_path:line_number:line' for each matching
        # line, sorted.
        raise NotImplementedError("Search.run")


if __name__ == "__main__":
    import tempfile

    root = Path(tempfile.mkdtemp())
    (root / "pkg").mkdir()
    (root / "pkg" / "m.py").write_text("x = 1\nTARGET = 'a'\ny = 1\n")
    tools = {cls.spec.name: cls(root) for cls in (ReadFile, WriteFile, EditFile, Glob, Search)}
    print("typed tools demo")
    print("  read:", repr(tools["read_file"].run("pkg/m.py").output))
    print("  edit:", tools["edit_file"].run("pkg/m.py", "x = 1", "x = 2").output)
    try:
        tools["edit_file"].run("pkg/m.py", "= ", "= ")
        ambiguous = "no error"
    except ToolError as exc:
        ambiguous = str(exc)
    print("  ambiguous:", ambiguous)
    print("  glob:", repr(tools["glob"].run("**/*.py").output))
    print("  search:", repr(tools["search"].run("TARGET").output))
