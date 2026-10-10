"""The permission matcher (phase 2, subsystem 5, LEARN mode).

The learner writes these two functions; `policy.py` (provided) validates the
rules and applies a decision, and this is where a rule is actually matched
against a call. A mistake here is a security hole, so the contract is exact.

Contract (docs/phase2.md has the reasoning):

- `command_string(tool, arguments)` → the call's canonical string, the text a
  rule's pattern is matched against:
  - `bash` → `arguments["command"]`;
  - `read_file`, `edit_file`, `write_file` → `arguments["path"]`;
  - `glob`, `search` → `arguments["pattern"]`.
  `arguments` may be a JSON string or a dict; a missing field, a non-string
  value, malformed JSON or an unknown tool all yield `""`.
- `decide(policy, tool, arguments)` → the first rule that matches decides:
  `rule.tool` is the call's tool or `"*"`, and `rule.pattern` is `None` (any) or
  a regex matched with `re.search` against `command_string(tool, arguments)`.
  If no rule matches, return `policy.default`.

DESIGN DECISION — `re.search`, not `re.fullmatch`.
  A rule should match a dangerous fragment anywhere in a command (`"&& rm -rf
  /"`), not only a string equal to the pattern. Cost: a rule must anchor with
  `^...$` when it wants an exact match.
"""

from __future__ import annotations

import json
import re


def command_string(tool: str, arguments) -> str:
    # TODO: decode `arguments` when it is a JSON string (malformed -> ""); pick the
    # field per tool (bash -> "command"; read_file/edit_file/write_file -> "path";
    # glob/search -> "pattern"); return it only if it is a string, else "".
    raise NotImplementedError("command_string")


def decide(policy, tool: str, arguments) -> str:
    # TODO: walk policy.rules in order; the first with rule.tool in (tool, "*") and
    # (rule.pattern is None or re.search(rule.pattern, command_string(tool, arguments)))
    # decides; return policy.default when none match.
    raise NotImplementedError("decide")
