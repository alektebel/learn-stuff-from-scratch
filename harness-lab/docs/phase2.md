# Phase 2 — The seven-subsystem core

Status: **started.** Two slices are contracted here. The typed **tool layer**:
the registry, the tool specs and the path guard are shipped, and the five tool
bodies (`harness_lab/tools/fs.py`) are the learner's work. The **permissions**
subsystem: the rule/policy data types and the guarded dispatch are shipped, and
the rule engine (`harness_lab/safety/match.py`) is the learner's. The remaining
subsystems are outlined below and each gets its own slice before the phase
closes. Phase 2 closes when the core matches or beats phase 1 on the suite
(`docs/phase1.md`, 95 %); that closing run needs Docker and the live endpoint, so
the phase cannot close in an environment without them.

## What it is

The seven canonical subsystems of a coding harness, each with a minimal
implementation behind an interface:

1. **Agent loop** — phase 1's linear loop, now selecting typed tools instead of
   only `bash`.
2. **LLM integration** — the `Model` protocol from phase 1 (unchanged).
3. **Tools & actions** — **contracted slice**: typed `read_file` / `write_file` /
   `edit_file` / `glob` / `search`, exact-substring editing.
4. **Memory & context** — threshold compaction **with provenance** (amendment 4):
   every summary records which messages it came from.
5. **Safety & permissions** — **contracted slice**: `allow` / `ask` / `deny` per
   tool and per pattern, as an ordered rule list with a fail-closed default.
6. **Orchestration** — subagents (a later slice; phase 5 in the original plan).
7. **Extensibility** — hooks, skills, MCP (a later slice).

Outside the subsystem list but required by the phase's closing criterion is the
**registry of subsystems**: the core must not know the phase-3 variants, which
are selected by config (`harness.toml`) behind interfaces.

## Slice: the tool layer (LEARN mode)

Sources: Claude Code's Read/Edit/Write/Glob/Grep tool documentation (the
unique-substring Edit contract, the numbered Read window); OpenHands and aider
edit tools (a failed edit is returned to the model as text, never an exception).
Restated, not copied.

**Shipped as infrastructure** (no agent logic):

- `harness_lab/tools/base.py` — `ToolResult`, the `ToolError` tree
  (`PathOutsideRoot`, `NotFound`, `NotUnique`), the `Tool` protocol, and
  `resolve(root, relative)`, which refuses any path outside the task root.
- `harness_lab/tools/registry.py` — `build_tools(root)`, `tool_specs(tools)` and
  `call_tool(tools, name, arguments)`, which decodes the model's JSON, dispatches,
  and turns an unknown tool, malformed JSON, a missing keyword or a `ToolError`
  into a `ToolResult` the model can read (never an exception into the loop).
- The five `ToolSpec`s (name, description, JSON schema) live on the tool classes.

**The learner writes** (`harness_lab/tools/fs.py`): the `run` body of each tool.

## The interface

```python
# harness_lab/tools/base.py
ToolResult(ok, output="", error=None)         # .success(output) / .failure(error)
class ToolError(Exception): ...               # -> a failure result, never fatal
PathOutsideRoot(ToolError) / NotFound(ToolError) / NotUnique(ToolError)
resolve(root, relative) -> Path               # raises PathOutsideRoot on an escape
class Tool(Protocol):
    spec: ToolSpec
    def run(self, **kwargs) -> ToolResult: ...

# harness_lab/tools/registry.py
build_tools(root) -> dict[str, Tool]          # one instance per tool, keyed by name
tool_specs(tools) -> list[ToolSpec]           # name-sorted, what the loop advertises
call_tool(tools, name, arguments) -> ToolResult   # arguments: a JSON string or a dict

# harness_lab/tools/fs.py  — the learner implements each run
ReadFile(root).run(path, offset=1, limit=2000) -> ToolResult
WriteFile(root).run(path, content) -> ToolResult
EditFile(root).run(path, old, new) -> ToolResult
Glob(root).run(pattern) -> ToolResult
Search(root).run(pattern, path=".") -> ToolResult
```

**Each tool, exactly** (what `tests/test_tools.py` pins):

- **read_file** — the file's lines `[offset, offset + limit)`, joined, with their
  original line endings. A missing file, a non-text file, `offset < 1` or
  `limit < 1` is a failure; an offset past the end is an empty success.
- **write_file** — create or overwrite, creating parent directories; a success
  whose output names the path. Writing the root itself is refused.
- **edit_file** — replace the **single** occurrence of `old`. An empty `old`, an
  `old` that is absent, or one that occurs more than once are failures — the file
  is left unchanged in every failure case.
- **glob** — files under the root matching a glob pattern, root-relative and
  sorted, one per line; no matches is an empty success.
- **search** — for every line a regex matches, `relative_path:line_number:line`,
  sorted; an invalid regex is a failure.

## Acceptance

Every tool test is an `xfail(raises=NotImplementedError)` today and must pass
once `fs.py` is written; a wrong tool fails hard. The registry, spec and path
guard tests pass today.

| # | Requirement | Tests |
|---|---|---|
| 1 | Five typed tools build and advertise a valid function schema | `test_registry_builds_five_typed_tools`, `test_every_spec_is_a_valid_function_schema` |
| 2 | A bad call returns a result, it does not raise | `test_unknown_tool_is_a_failure`, `test_malformed_json_is_a_failure`, `test_non_object_arguments_are_a_failure` |
| 3 | The path guard refuses escapes | `test_path_guard_refuses_escapes`, `test_read_outside_root_is_refused` |
| 4 | `read_file` windows by `offset`/`limit`; missing file fails | `test_read_whole_file`, `test_read_window_uses_offset_and_limit`, `test_read_missing_file_is_a_failure` |
| 5 | `write_file` creates parents and round-trips | `test_write_creates_parents_and_reads_back` |
| 6 | `edit_file` replaces a unique occurrence | `test_edit_replaces_the_unique_occurrence` |
| 7 | `glob` lists matches, sorted, relative; none is empty-ok | `test_glob_lists_matching_files_relative_and_sorted` |
| 8 | `search` reports `path:line:text`, sorted; bad regex fails | `test_search_reports_path_line_and_text`, `test_search_invalid_regex_is_a_failure` |

## Limit cases

- **L1 — ambiguous edit.** `old` occurs twice: the edit must refuse and leave the
  file untouched, not pick one. Test `test_edit_ambiguous_old_is_a_failure`.
- **L2 — empty `old`.** `""` matches everywhere; it is a failure, not an
  insert-everywhere. Test `test_edit_empty_old_is_a_failure`.
- **L3 — absent `old`.** A model that guesses wrong gets "not found" and the file
  is unchanged. Test `test_edit_absent_old_is_a_failure`.
- **L4 — escape attempt.** `../secret` and `/etc/passwd` never reach the
  filesystem. Tests `test_path_guard_refuses_escapes`, `test_read_outside_root_is_refused`.
- **L5 — bad arguments never crash the loop.** Unknown tool, malformed JSON,
  non-object arguments and a missing keyword all become failure results.
  Tests 2 above.

## Slice: permissions (LEARN mode)

Sources: Claude Code permission rules (an allow/deny list keyed by tool and an
argument matcher with a default); OpenHands confirmation policy (per-action
never/always/ask). Restated, not copied.

**Shipped as infrastructure**: `harness_lab/safety/policy.py` — `Rule` and
`Policy` (which validate their inputs: the decision is one of three, every
pattern compiles), `parse_policy` (from plain data, e.g. a `harness.toml`
section), and `guarded_call_tool(policy, tools, name, arguments, approve=None)`,
which asks the rule engine for a decision and only then runs the tool through
`call_tool`.

**The learner writes** (`harness_lab/safety/match.py`): `command_string` and
`decide`.

```python
# harness_lab/safety/policy.py
DECISIONS = ("allow", "ask", "deny")
Rule(tool, pattern=None, decision="ask")          # validates decision and regex
Policy(rules=(), default="ask")                   # validates default
parse_policy({"default": ..., "rules": [...]}) -> Policy
guarded_call_tool(policy, tools, name, arguments, approve=None) -> ToolResult

# harness_lab/safety/match.py  — the learner implements both
command_string(tool, arguments) -> str            # bash->command; file tools->path; glob/search->pattern
decide(policy, tool, arguments) -> str            # first matching rule, else policy.default
```

**The rule engine, exactly** (what `tests/test_safety.py` pins):

- `command_string` picks the field per tool: `bash` → the command; `read_file` /
  `edit_file` / `write_file` → the path; `glob` / `search` → the pattern. An
  argument that is a JSON string is decoded first; malformed JSON, a non-dict, a
  missing field, a non-string value or an unknown tool all yield `""`.
- `decide` walks the rules **in order**; the first whose `tool` is the call's
  tool or `"*"`, and whose `pattern` is `None` or matches with `re.search`, wins.
  No match → `policy.default`.
- `guarded_call_tool`: `allow` runs; `deny` never runs; `ask` runs only if an
  approver returns True (otherwise refused). Every refusal is a failure result.

### Acceptance

Every engine test is `xfail(raises=NotImplementedError)` today and must pass once
`match.py` is written; the data-type, validation and parsing tests pass today.

| # | Requirement | Tests |
|---|---|---|
| 1 | `command_string` picks the per-tool field; bad input is `""` | `test_command_string_picks_the_field_per_tool`, `test_command_string_is_empty_on_bad_input` |
| 2 | No matching rule → the default | `test_decide_returns_the_default_when_no_rule_matches` |
| 3 | First match wins; the pattern is a `re.search` regex | `test_decide_first_match_wins_and_pattern_is_a_regex` |
| 4 | A wildcard-tool rule matches every tool | `test_wildcard_tool_rule_matches_every_tool` |
| 5 | `allow` runs, `deny` does not, `ask` needs approval | `test_guarded_call_allows_and_runs`, `test_guarded_call_denies_without_running`, `test_guarded_call_asks_and_needs_approval` |
| 6 | Rules validate (decision, regex, default) and parse in order | `test_rule_rejects_an_unknown_decision`, `test_rule_rejects_a_bad_regex`, `test_policy_rejects_an_unknown_default`, `test_parse_policy_keeps_rule_order_and_default` |

### Limit cases

- **L1 — order is precedence.** A broad `allow` before a narrow `deny` swallows
  it: the deny must come first. Test `test_order_matters_a_broad_allow_before_a_deny_wins`.
- **L2 — `re.search`, not `re.fullmatch`.** `"rm"` must catch `"echo hi && rm -rf
  /"`; a rule that wants an exact match anchors with `^...$`. Test 3 above.
- **L3 — fail closed.** An unlisted call returns the default, and the default is
  `ask`, not `allow`. Test 2 above.
- **L4 — a malformed call cannot bypass a rule.** Non-dict arguments yield `""`,
  which no pattern requiring content matches; the safe path is the default.
  Test 1 above.
- **L5 — deny never runs the tool.** Even with an approver present, `deny` is not
  overridable. Test `test_guarded_call_denies_without_running`.

## Out of scope / blocked

- **Closing the phase needs Docker + the live endpoint.** The tool layer is
  deterministic; the phase's comparison to phase 1 is an evaluation run.
- **No fuzzy or LLM-repaired edits** (phase 4: aider's RelativeIndenter,
  opencode/hermes' fuzzy cascade). Phase 2's edit is exact.
- **No tool concurrency.** Claude Code batches calls by concurrency safety
  (phase 3, `claude_code` variant); here a batch runs in order.
- **No enforcement wired into the loop yet.** `guarded_call_tool` decides and
  runs, but the phase-1 loop does not consult the policy or the typed tools; it
  still advertises `bash` and calls `sandbox.exec`. Wiring both into the loop is
  the next step below, and it edits the learner's `run_loop`, so it is the
  learner's to do or needs a BUILD flip — the slices here are deliberately
  additive and touch no existing core.
- **No shell rewiring.** The loop still advertises `bash` (phase 1); swapping in
  the typed tools is part of integrating this slice, and is the next step.

## Design decisions

- **Tools return a result, they do not raise at the boundary.** The path guard
  raises internally; `call_tool` catches once. Cost: callers check `.ok`.
- **Exact, unique substring for edits.** No offsets (the model has none) and no
  fuzzy matching (that is a variant). Cost: the model quotes more context.
- **The registry is the only JSON decoding point.** The loop passes arguments
  through unchanged, so the decode-and-recover logic lives in one place, as
  `_decode_command` does in phase 1.
- **`read_file` returns raw text, not numbered lines.** Numbering is a UI
  convention; the phase-1 edit contract does not need it. A numbered window is a
  small, deliberate follow-up (and a candidate exercise).

## How to run

```sh
cd harness-lab
python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q tests/test_tools.py tests/test_safety.py
# today: 11 infrastructure tests pass, 21 slice tests xfail (raises=NotImplementedError)
.venv/bin/python -m pytest -q        # whole suite; Docker tests skip without a daemon
```

A reference implementation was used to confirm each contract is satisfiable (the
12 tool tests and the 9 permission tests xpass); it is not committed — the tests
are the check.

## Next (proposal, for confirmation)

1. **Subsystem 4, compaction with provenance** — threshold compaction whose every
   summary names the source messages it came from (amendment 4), tested with the
   scripted backend. Additive, deterministic, no Docker — the next slice.
2. **Wire the tools and the policy into the loop** — advertise the typed specs,
   dispatch through `call_tool`, and consult `guarded_call_tool`, keeping the
   bash fallback; then one evaluation run to confirm the floor does not drop.
   This edits the learner's `run_loop`, so it is the learner's to do or needs an
   explicit BUILD flip for that piece.
3. **The registry of subsystems** — load subsystems and variants from
   `harness.toml` behind interfaces, failing on an incompatible combination.
4. **Close the phase** — the seven-subsystem core matches or beats phase 1 on the
   suite (needs Docker + the live endpoint).

Each is a slice with its own contract; the phase closes only with the suite
comparison to phase 1.
