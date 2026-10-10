"""Agents From Scratch — stage 4: what the model actually said

SOLUTION. A small scanner finds the first balanced object (string- and
escape-aware), the envelope is normalised, and the loop inserts one honest
assistant message plus a note the model can act on. Nothing in here guesses
what a tool call means.
"""

import json
import re

FENCE = re.compile(r"```(?:json)?[ \t]*\r?\n(.*?)```", re.S)
KEYS = ("tool", "args", "final")


def _balanced_object(text):
    """The first balanced {...} in `text`, or None. Brace counting that ignores
    braces inside strings, because a JSON argument is often a brace."""
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for position in range(start, len(text)):
            char = text[position]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:position + 1]
        start = text.find("{", start + 1)
    return None


def _problem(reason, raw_text, repaired=()):
    return {"ok": False, "decision": None, "problem": reason,
            "repaired": list(repaired), "raw_text": raw_text}


def parse_decision(raw, names=None):
    repaired = []
    if isinstance(raw, dict):
        raw_text = raw
        payload = dict(raw)
    elif isinstance(raw, str):
        raw_text = raw
        body = raw
        fence = FENCE.search(body)
        if fence:
            body = fence.group(1)
            repaired.append("unwrapped a fenced block")
        candidate = _balanced_object(body)
        if candidate is None:
            return _problem("no JSON object in the reply", raw_text, repaired)
        if candidate != body.strip():
            repaired.append("took the first JSON object out of the reply")
        try:
            payload = json.loads(candidate)
        except ValueError as exc:
            return _problem(f"not valid JSON: {exc}", raw_text, repaired)
    else:
        return _problem(f"the reply was a {type(raw).__name__}, not a decision",
                        raw_text=repr(raw))

    if not isinstance(payload, dict):
        return _problem(f"the reply was a JSON {type(payload).__name__}, not an "
                        f"object", raw_text, repaired)

    normalised = {}
    renamed = []
    for key, value in payload.items():
        low = key.strip().lower() if isinstance(key, str) else key
        if low in normalised:
            return _problem(f"two spellings of the key {low!r} in one reply",
                            raw_text, repaired)
        if low != key:
            renamed.append(f"matched the key {key!r} to {low!r}")
        normalised[low] = value
    repaired.extend(renamed)
    extra = [k for k in normalised if k not in KEYS]
    if extra:
        repaired.append("ignored extra keys: " + ", ".join(sorted(map(str, extra))))

    has_final, has_tool = "final" in normalised, "tool" in normalised
    if has_final and has_tool:
        return _problem("the reply has both 'final' and 'tool': a decision is one "
                        "or the other", raw_text, repaired)
    if has_final:
        if not isinstance(normalised["final"], str):
            return _problem(f"'final' is a {type(normalised['final']).__name__}, "
                            f"not a string", raw_text, repaired)
        return {"ok": True, "decision": {"final": normalised["final"]},
                "problem": None, "repaired": repaired, "raw_text": raw_text}
    if has_tool:
        name = normalised["tool"]
        if not isinstance(name, str) or not name.strip():
            return _problem(f"'tool' is {name!r}, not a tool name", raw_text, repaired)
        args = normalised.get("args", {})
        if not isinstance(args, dict):
            return _problem(
                f"'args' is a {type(args).__name__}, not an object. The envelope "
                f"gets repaired, the meaning does not: a parser that splits an "
                f"arguments string has invented the tool call", raw_text, repaired)
        if names:
            for known in names:
                if name != known and name.strip().lower() == known.lower():
                    repaired.append(f"matched the tool name {name!r} to {known!r}")
                    name = known
                    break
        return {"ok": True, "decision": {"tool": name, "args": args},
                "problem": None, "repaired": repaired, "raw_text": raw_text}
    return _problem("neither 'final' nor 'tool' in the reply", raw_text, repaired)


NOTE = ("Your previous reply could not be used: {problem}. Reply with a single "
        "JSON object, either {{\"tool\": <name>, \"args\": {{...}}}} or "
        "{{\"final\": <text>}}.")


def _copy(message):
    out = dict(message)
    if isinstance(out.get("args"), dict):
        out["args"] = dict(out["args"])
    return out


def run_parsed(model, toolbox, task, system=None, max_steps=8, messages=None,
               repairs=2):
    if messages is not None:
        transcript = [_copy(m) for m in messages]
    else:
        transcript = []
        if system:
            transcript.append({"role": "system", "content": system})
        if task is not None:
            transcript.append({"role": "user", "content": task})

    seen, tool_calls, problems = [], [], []
    steps = 0
    used = 0
    status = "max_steps"
    answer = None

    while steps < max_steps:
        shown = [_copy(m) for m in transcript]
        seen.append(shown)
        steps += 1

        parsed = parse_decision(model(shown), getattr(toolbox, "names", None))
        if not parsed["ok"]:
            problems.append(parsed["problem"])
            if used >= repairs:
                status = "unparsed"
                break
            used += 1
            transcript.append({"role": "assistant",
                               "content": _as_text(parsed["raw_text"])})
            transcript.append({"role": "user",
                               "content": NOTE.format(problem=parsed["problem"])})
            continue

        decision = parsed["decision"]
        if "final" in decision:
            answer = decision["final"]
            transcript.append({"role": "assistant", "content": answer})
            status = "answered"
            break

        name, args = decision["tool"], decision["args"]
        transcript.append({"role": "assistant", "tool": name, "args": args})
        result = toolbox.call(name, args)
        transcript.append({"role": "tool", "tool": name,
                           "ok": bool(result.get("ok")),
                           "content": result.get("content", "")})
        tool_calls.append(name)

    return {"status": status, "answer": answer, "steps": steps,
            "tool_calls": tool_calls, "messages": transcript, "seen": seen,
            "repairs": used, "problems": problems}


def _as_text(raw_text):
    if isinstance(raw_text, str):
        return raw_text
    try:
        return json.dumps(raw_text, sort_keys=True)
    except TypeError:
        return repr(raw_text)
