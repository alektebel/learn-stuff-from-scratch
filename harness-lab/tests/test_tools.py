"""The phase-2 tool-layer contract: typed read/edit/write/glob/search.

LEARN mode. The five tool bodies in `harness_lab/tools/fs.py` are the learner's
work, so every test that exercises a tool is an `xfail` expecting
`NotImplementedError`: while the stubs stand they report as xfailed, and once
the tools are written they must pass. A wrong tool fails hard, which is the
point. The registry, the specs and the path guard are provided infrastructure
and their tests pass today.

Contract: docs/phase2.md.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness_lab.tools import (  # noqa: E402
    PathOutsideRoot,
    build_tools,
    call_tool,
    resolve,
    tool_specs,
)

CORE = pytest.mark.xfail(
    raises=NotImplementedError,
    reason="phase-2 tool layer: the learner writes harness_lab/tools/fs.py (docs/phase2.md)",
)


def seed(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def call(tools, name, **kwargs):
    return call_tool(tools, name, json.dumps(kwargs))


# --- registry, specs and the path guard (infrastructure, pass today) ---------


def test_registry_builds_five_typed_tools(tmp_path):
    tools = build_tools(tmp_path)
    assert set(tools) == {"read_file", "write_file", "edit_file", "glob", "search"}


def test_every_spec_is_a_valid_function_schema(tmp_path):
    for spec in tool_specs(build_tools(tmp_path)):
        assert spec.name and spec.description
        assert spec.parameters["type"] == "object"
        assert isinstance(spec.parameters["properties"], dict)
        assert isinstance(spec.parameters["required"], list)
        assert set(spec.parameters["required"]) <= set(spec.parameters["properties"])


def test_unknown_tool_is_a_failure(tmp_path):
    result = call(build_tools(tmp_path), "nope", x=1)
    assert not result.ok and "unknown tool" in result.error


def test_malformed_json_is_a_failure(tmp_path):
    result = call_tool(build_tools(tmp_path), "read_file", "{not json")
    assert not result.ok and "JSON" in result.error


def test_non_object_arguments_are_a_failure(tmp_path):
    result = call_tool(build_tools(tmp_path), "read_file", "[1, 2]")
    assert not result.ok and "JSON object" in result.error


def test_path_guard_refuses_escapes(tmp_path):
    for bad in ("../outside", "/etc/passwd"):
        with pytest.raises(PathOutsideRoot):
            resolve(tmp_path, bad)
    assert resolve(tmp_path, "a.txt") == (tmp_path / "a.txt").resolve()


# --- the five tools (the learner's work) -------------------------------------


@CORE
def test_read_whole_file(tmp_path):
    seed(tmp_path, "a.txt", "alpha\nbeta\ngamma\n")
    result = call(build_tools(tmp_path), "read_file", path="a.txt")
    assert result.ok and result.output == "alpha\nbeta\ngamma\n"


@CORE
def test_read_window_uses_offset_and_limit(tmp_path):
    seed(tmp_path, "a.txt", "l1\nl2\nl3\nl4\n")
    tools = build_tools(tmp_path)
    assert call(tools, "read_file", path="a.txt", offset=2, limit=2).output == "l2\nl3\n"
    assert call(tools, "read_file", path="a.txt", offset=9).output == ""  # past the end


@CORE
def test_read_missing_file_is_a_failure(tmp_path):
    result = call(build_tools(tmp_path), "read_file", path="nope.txt")
    assert not result.ok and "no such file" in result.error


@CORE
def test_read_outside_root_is_refused(tmp_path):
    result = call(build_tools(tmp_path), "read_file", path="../secret")
    assert not result.ok


@CORE
def test_write_creates_parents_and_reads_back(tmp_path):
    tools = build_tools(tmp_path)
    result = call(tools, "write_file", path="pkg/mod.py", content="hi\n")
    assert result.ok and "pkg/mod.py" in result.output
    assert (tmp_path / "pkg" / "mod.py").read_text(encoding="utf-8") == "hi\n"
    assert call(tools, "read_file", path="pkg/mod.py").output == "hi\n"


@CORE
def test_edit_replaces_the_unique_occurrence(tmp_path):
    seed(tmp_path, "a.txt", "x = 1\ny = 1\n")
    tools = build_tools(tmp_path)
    result = call(tools, "edit_file", path="a.txt", old="x = 1", new="x = 2")
    assert result.ok
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "x = 2\ny = 1\n"


@CORE
def test_edit_absent_old_is_a_failure(tmp_path):
    seed(tmp_path, "a.txt", "hello\n")
    result = call(build_tools(tmp_path), "edit_file", path="a.txt", old="zzz", new="y")
    assert not result.ok and "not found" in result.error


@CORE
def test_edit_ambiguous_old_is_a_failure(tmp_path):
    # "1" occurs twice, so the edit must refuse rather than guess which one.
    seed(tmp_path, "a.txt", "x = 1\ny = 1\n")
    result = call(build_tools(tmp_path), "edit_file", path="a.txt", old="1", new="9")
    assert not result.ok and "2 times" in result.error
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "x = 1\ny = 1\n"


@CORE
def test_edit_empty_old_is_a_failure(tmp_path):
    seed(tmp_path, "a.txt", "hello\n")
    result = call(build_tools(tmp_path), "edit_file", path="a.txt", old="", new="x")
    assert not result.ok


@CORE
def test_glob_lists_matching_files_relative_and_sorted(tmp_path):
    seed(tmp_path, "a.txt", "")
    seed(tmp_path, "b/c.txt", "")
    seed(tmp_path, "b/d.py", "")
    tools = build_tools(tmp_path)
    assert call(tools, "glob", pattern="**/*.txt").output == "a.txt\nb/c.txt"
    assert call(tools, "glob", pattern="*.md").output == ""  # no match is an empty success


@CORE
def test_search_reports_path_line_and_text(tmp_path):
    seed(tmp_path, "a.py", "TODO: one\nok\n")
    seed(tmp_path, "b/c.py", "x\nTODO: two\n")
    result = call(build_tools(tmp_path), "search", pattern="TODO")
    assert result.ok
    assert result.output.splitlines() == ["a.py:1:TODO: one", "b/c.py:2:TODO: two"]


@CORE
def test_search_invalid_regex_is_a_failure(tmp_path):
    seed(tmp_path, "a.py", "x\n")
    result = call(build_tools(tmp_path), "search", pattern="(")
    assert not result.ok and "regular expression" in result.error
