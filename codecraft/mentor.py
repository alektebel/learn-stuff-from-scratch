"""The mentor: ask a NAN model what you are actually misunderstanding.

The rule-based coach in `adapt.py` sees the *shape* of your failure (stuck vs
flailing, which concept tag). It cannot read your code. This module can: it
sends the failing stage's source, the exact error, and your attempt history to
a model on the NAN subscription and asks for the misconception behind it.

It is deliberately not a solution generator. The system prompt forbids printing
the fix; the value is naming the wrong mental model so the fix becomes obvious.

Stdlib only (`urllib`). A browser-like User-Agent is required — the API sits
behind Cloudflare, which rejects the default Python agent with error 1010.

    NAN_API_KEY must be in the environment. Endpoint and model are configurable:

        python3 codecraft/cli.py config --model glm5.3
        python3 codecraft/cli.py config --mentor off
"""

import hashlib
import json
import os
import re
import urllib.error
import urllib.request

from .store import HERE

CACHE = os.path.join(HERE, "mentor_cache.json")

DEFAULT_ENDPOINT = "https://api.nan.builders/v1"
DEFAULT_MODEL = "deepseek-v4-flash"
USER_AGENT = "opencode"          # allowlisted by the API's CDN

SYSTEM = """You are the mentor inside "codecraft", a tool that teaches \
computer-science systems by having a learner build them from scratch in a \
repository of graded stage templates. The learner's own test just failed.

Your job is to diagnose the MISUNDERSTANDING behind the failure. Not to fix \
their code, and not to be encouraging.

Hard rules:
- Never output corrected code, and no code block longer than a single short \
expression. The learner must write the fix.
- Be specific to THIS error and THIS code. Generic advice is a failure.
- No praise, no padding, no restating the error back to them.
- Name the concept, not a line number.
- If they have failed this stage many times, you may describe the algorithm in \
plain words, but still no code.

Answer in exactly this shape and nothing else, under 150 words total:
MISCONCEPTION: <the wrong mental model, in one sentence>
MODEL: <the correct model, as a rule they can apply, in one or two sentences>
TRY: <one concrete experiment or question they can answer themselves>"""


# ---------------------------------------------------------------------------
# configuration + availability
# ---------------------------------------------------------------------------

def endpoint(profile):
    return (profile.get("config", {}).get("endpoint")
            or os.environ.get("NAN_BASE_URL") or DEFAULT_ENDPOINT).rstrip("/")


def model(profile):
    return profile.get("config", {}).get("model") or DEFAULT_MODEL


def api_key():
    return os.environ.get("NAN_API_KEY") or os.environ.get("NAN_KEY") or ""


def available(profile):
    if profile.get("config", {}).get("mentor") == "off":
        return False, "mentor is off (config --mentor auto to enable)"
    if not api_key():
        return False, "NAN_API_KEY is not set"
    return True, ""


# ---------------------------------------------------------------------------
# transport
# ---------------------------------------------------------------------------

def _chat(profile, messages, max_tokens=420, timeout=60):
    key = api_key()
    payload = json.dumps({
        "model": model(profile),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        endpoint(profile) + "/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read(200).decode("utf-8", "replace")
        hint = {401: "check NAN_API_KEY", 403: "blocked by the CDN (UA)",
                404: "wrong endpoint", 429: "rate limited"}.get(exc.code, "")
        raise RuntimeError(f"HTTP {exc.code} {detail.strip()} {hint}".strip())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network: {exc.reason}")
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"unexpected response: {str(data)[:200]}")


# ---------------------------------------------------------------------------
# context assembly
# ---------------------------------------------------------------------------

def _read_stage_source(course, file, limit=6000):
    path = os.path.join(course["dir"], file) if file else ""
    if not path or not os.path.exists(path):
        return "(stage file not found)"
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return f"(could not read: {exc})"
    return text[:limit] + ("\n# ... (truncated)" if len(text) > limit else "")


def _history_note(profile, course_name, stage):
    cstate = profile["courses"].get(course_name, {})
    row = cstate.get("stages", {}).get(str(stage), {})
    bits = [f"attempts: {row.get('attempts', 1)}",
            f"consecutive non-passing runs: {row.get('fail_streak', 1)}"]
    if row.get("attempts_to_pass"):
        bits.append(f"it took {row['attempts_to_pass']} attempts to pass earlier")
    if row.get("last_category"):
        bits.append(f"failure category: {row['last_category']}")
    sigs = row.get("signatures", {})
    if sigs:
        top = max(sigs.items(), key=lambda kv: kv[1])
        bits.append(f"repeated failure ({top[1]}x): {top[0]}")
    pats = profile.get("patterns", {})
    worst = sorted(pats.items(), key=lambda kv: kv[1].get("count", 0), reverse=True)
    if worst and worst[0][1].get("count", 0) >= 3:
        label, p = worst[0]
        bits.append(f"cross-course habit: {label} ({p['count']}x)")
    return "; ".join(bits)


def _prompt_context(course, stage_id, meta, error, profile):
    row = profile["courses"].get(course["name"], {}).get("stages", {}).get(str(stage_id), {})
    stuck = row.get("fail_streak", 0)
    return f"""COURSE: {course['title']} — {course.get('description', '')}
STAGE {stage_id}: {meta.get('title', '')}  (file: {meta.get('file', '')})
CONCEPTS: {', '.join(meta.get('tags', [])) or '(none tagged)'}
THE STAGE ASKS: {meta.get('action', '(unspecified)')}
THE LEARNER MUST PREDICT: {meta.get('predict', '(unspecified)')}
HISTORY: {_history_note(profile, course['name'], stage_id)}
CONSECUTIVE FAILURES: {stuck}

THE CHECKER SAID:
{error or '(no message)'}

THE LEARNER'S CURRENT FILE:
```python
{_read_stage_source(course, meta.get('file', ''))}
```

{('They have failed many times; describe the algorithm in words, still no code.'
  ) if stuck >= 5 else 'Keep it tight.'}"""


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"(MISCONCEPTION|MODEL|TRY)\s*:\s*", re.I)


def _parse_sections(text):
    parts = _SECTION_RE.split(text)
    sections = []
    for i in range(1, len(parts) - 1, 2):
        label = parts[i].strip().upper()
        body = parts[i + 1].strip()
        sections.append(({"MISCONCEPTION": "misconception",
                          "MODEL": "the model",
                          "TRY": "try this"}[label], body))
    if not sections:
        sections = [("mentor", " ".join(text.split()))]
    return sections


def _cache_key(course, stage_id, file, source, error):
    h = hashlib.sha1()
    for part in (course["name"], str(stage_id), file or "", source, error or ""):
        h.update(part.encode("utf-8", "replace"))
    return h.hexdigest()


def _cache_load():
    if not os.path.exists(CACHE):
        return {}
    try:
        with open(CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _cache_save(cache):
    try:
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, indent=2)
    except OSError:
        pass


def diagnose(profile, course, stage_id, error, use_cache=True):
    """Return (sections, model_name, cached) or raise RuntimeError."""
    meta = course["stages"].get(stage_id, {})
    source = _read_stage_source(course, meta.get("file", ""))
    key = _cache_key(course, stage_id, meta.get("file", ""), source, error or "")
    if use_cache:
        hit = _cache_load().get(key)
        if hit:
            return _parse_sections(hit["text"]), hit.get("model", ""), True

    user = ("Here is the failing stage. Diagnose the misunderstanding.\n\n"
            + _prompt_context(course, stage_id, meta, error, profile))
    text = _chat(profile, [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": user}])
    cache = _cache_load()
    cache[key] = {"text": text, "model": model(profile)}
    _cache_save(cache)
    return _parse_sections(text), model(profile), False


def ask(profile, course, stage_id, question):
    meta = course["stages"].get(stage_id, {})
    user = (f"Question from the learner: {question}\n\n"
            + _prompt_context(course, stage_id, meta, "(no failure: they are asking)",
                              profile))
    text = _chat(profile, [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": user}])
    return _parse_sections(text), model(profile)
