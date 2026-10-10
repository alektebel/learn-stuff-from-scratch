"""Agents From Scratch — stage 10: the trace, and the audit

SOLUTION. The trace is a fold over the run's own bookkeeping; the audit is a
snapshot comparison and four small detectors. The only tricky parts are the
encoding variants in no_leak and the line diff in no_new_match, and both are
there because the naive version is quietly useless.
"""

import base64
import hashlib
import json
import os
import re


def trace_of(run):
    events = []
    step = 0
    for message in run.get("messages", []):
        if message.get("role") == "assistant":
            if "tool" in message:
                step += 1
                events.append({"event": "tool_call", "step": step,
                               "tool": message.get("tool"),
                               "args": message.get("args") or {}})
            elif "content" in message:
                events.append({"event": "final", "step": max(step, 1),
                               "chars": len(str(message["content"]))})
        elif message.get("role") == "tool":
            events.append({"event": "tool_result", "step": max(step, 1),
                           "tool": message.get("tool"),
                           "ok": bool(message.get("ok")),
                           "chars": len(str(message.get("content", "")))})
    events.insert(0, {"event": "model_call", "step": 1,
                      "saw": len(run.get("messages", []))})
    for index in range(1, int(run.get("steps", 0))):
        events.insert(index, {"event": "model_call", "step": index + 1,
                              "saw": len(run.get("messages", []))})
    events.append({"event": "stop", "status": run.get("status"),
                   "steps": int(run.get("steps", 0)),
                   "tool_calls": len(run.get("tool_calls", []))})
    return events


def to_jsonl(events):
    return "".join(json.dumps(event, sort_keys=True,
                              separators=(",", ":")) + "\n" for event in events)


def snapshot(root):
    root = os.path.abspath(root)
    out = {}
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(dirs):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                dirs.remove(name)          # never walk through a link
                out[rel] = {"kind": "link", "path": full,
                            "digest": os.readlink(full)}
            else:
                out[rel] = {"kind": "dir", "path": full, "digest": ""}
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                out[rel] = {"kind": "link", "path": full,
                            "digest": os.readlink(full)}
            else:
                with open(full, "rb") as handle:
                    out[rel] = {"kind": "file", "path": full,
                                "digest": hashlib.sha256(handle.read()).hexdigest()}
    return dict(sorted(out.items()))


def diff_snapshots(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified = sorted(path for path in set(before) & set(after)
                      if before[path] != after[path])
    return {"added": added, "removed": removed, "modified": modified}


def unchanged(before, after, path):
    path = path.rstrip("/")
    keys = [key for key in set(before) | set(after)
            if key == path or key.startswith(path + "/")]
    for key in sorted(keys):
        if key not in after:
            return f"{key} was deleted"
        if key not in before:
            return f"{key} was created"
        if before[key] != after[key]:
            return f"{key} was modified"
    return None


def _encodings(token):
    raw = token.encode()
    return {
        "plain": [token],
        "base64": [base64.b64encode(raw).decode(),
                   base64.b64encode(raw).decode().rstrip("=")],
        "hex": [raw.hex(), raw.hex().upper()],
        "reversed": [token[::-1]],
    }


def no_leak(after, token, exclude=()):
    variants = _encodings(token)
    violations = []
    for path in sorted(after):
        if after[path]["kind"] != "file":
            continue
        if any(path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")
               for prefix in exclude):
            continue
        try:
            with open(after[path]["path"], "rb") as handle:
                blob = handle.read()
        except OSError:
            continue
        text = blob.decode("utf-8", "replace")
        for encoding, needles in variants.items():
            for needle in needles:
                if needle and (needle in text if encoding != "hex" else
                               needle in text or bytes.fromhex(needle) in blob):
                    violations.append(f"{path} contains the secret ({encoding})")
                    break
    return violations


def _added_lines(before_path, after_path, pattern):
    try:
        with open(after_path, encoding="utf-8", errors="replace") as handle:
            after_lines = handle.read().splitlines()
    except OSError:
        return []
    if before_path is None:
        before_lines = set()        # a new file: every line in it is new
    else:
        try:
            with open(before_path, encoding="utf-8", errors="replace") as handle:
                before_lines = set(handle.read().splitlines())
        except OSError:
            before_lines = set()
    return [line for line in after_lines
            if line not in before_lines and re.search(pattern, line)]


def no_new_match(before, after, pattern, under=""):
    prefix = under.rstrip("/")
    violations = []
    for path in sorted(after):
        if after[path]["kind"] != "file":
            continue
        if prefix and not (path == prefix or path.startswith(prefix + "/")):
            continue
        previous = None
        if path in before:
            if before[path]["digest"] == after[path]["digest"]:
                continue
            previous = before[path]["path"]
        for line in _added_lines(previous, after[path]["path"], pattern):
            violations.append(f"{path}: added {line.strip()[:120]!r}")
    return violations


def audit(run=None, *, before, after, policy):
    violations = []
    for path in policy.get("unchanged", ()):
        found = unchanged(before, after, path)
        if found:
            violations.append(found)
    for pattern in policy.get("no_new_match", ()):
        violations.extend(no_new_match(before, after, pattern,
                                       under=policy.get("under", "")))
    for token in policy.get("no_leak", ()):
        violations.extend(no_leak(after, token, exclude=policy.get("exclude", ())))
    returns = diff_snapshots(before, after)
    return {"ok": not violations, "violations": violations,
            "events": trace_of(run) if run else [],
            "added": returns["added"], "removed": returns["removed"],
            "modified": returns["modified"]}
