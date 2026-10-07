"""The adaptive decision: given everything known about you, what now?

Inputs: your profile (attempts per stage, per-concept mastery, recurring
mistakes), the course you are in, and the result of the run you just did.

Output: one `Advice` describing the *kind* of moment you are in, the smallest
thing to do next, and how much to reveal. The renderer turns that into a few
lines of terminal text. The rules are intentionally legible — you should be
able to see why the tool said what it said, and disagree with it.
"""

import os

from . import patterns, store

# How many consecutive non-passing runs before we stop calling it "normal".
STUCK_AFTER = 3
# A concept recurs enough across courses to call it a habit of thought.
PATTERN_AFTER = 3


def _course_state(profile: dict, name: str) -> dict:
    return profile["courses"].get(name, {})


def _consecutive_first_try(cstate: dict, frontier: int) -> int:
    """Stages immediately before the frontier that passed on the first run."""
    count = 0
    for sid in range(frontier - 1, 0, -1):
        row = cstate.get("stages", {}).get(str(sid))
        if not row:
            break
        if row.get("last_status") == "PASS" and row.get("attempts_to_pass") == 1 \
                and not row.get("fails"):
            count += 1
        else:
            break
    return count


def _due_review(profile: dict, limit: int = 3):
    """Concepts you once got wrong and have not fully retired."""
    out = []
    for name, cstate in profile["courses"].items():
        for tag, c in cstate.get("concepts", {}).items():
            if c.get("ever_failed") and c.get("box", 0) < store.CONCEPT_BOXES:
                out.append((c.get("last", 0), name, tag, c))
    out.sort(reverse=True)
    return [(name, tag, c) for _, name, tag, c in out[:limit]]


def _pattern_note(profile: dict, prefer: str = "") -> str:
    pats = profile.get("patterns", {})
    ranked = sorted(pats.items(), key=lambda kv: kv[1].get("count", 0), reverse=True)
    if prefer and prefer in pats and pats[prefer].get("count", 0) >= 2:
        ranked.sort(key=lambda kv: 0 if kv[0] == prefer else 1, reverse=False)
    for label, row in ranked:
        if row.get("count", 0) >= PATTERN_AFTER and len(row.get("courses", [])) >= 2:
            return (f"{label}: {row['count']} misses across "
                    f"{len(row['courses'])} courses. That is a habit, not a one-off.")
    return ""


def decide(profile: dict, course: dict, result: dict = None,
           all_courses=None) -> dict:
    """Produce the Advice dict for the current moment."""
    name = course["name"]
    cstate = _course_state(profile, name)
    style = profile.get("config", {}).get("style", "balanced")
    stages = course["stages"]

    advice = {
        "kind": "focused", "course": name, "title": course["title"],
        "stage": None, "file": "", "stage_title": "", "cause": "", "action": "",
        "predict": "", "experiment": "", "reference": "", "pattern": "",
        "hint_level": 0, "hint_hint": "", "pace": "", "review": [], "next_course": "",
        "mentor": False,
    }

    # --- never run ---------------------------------------------------------
    first_id = min(stages) if stages else 1
    if not cstate:
        advice.update({
            "kind": "not-started",
            "stage": first_id,
            "file": stages.get(first_id, {}).get("file", ""),
            "stage_title": stages.get(first_id, {}).get("title", ""),
            "action": (stages.get(first_id, {}).get("action")
                       or "Read the course README, open the stage template, "
                          "and implement the first function."),
            "pace": f"Run: python3 codecraft/cli.py run {name}",
        })
        return advice

    total = result["total"] if result else cstate.get("total", len(stages))
    next_step = result["next_step"] if result else cstate.get("next_step")

    # --- everything passes -------------------------------------------------
    if next_step is None and total:
        advice["kind"] = "done"
        advice["pace"] = _recommend_next(course, all_courses)
        advice["pattern"] = _pattern_note(profile)
        advice["review"] = _due_review(profile)
        return advice

    frontier = next_step or first_id
    row = cstate.get("stages", {}).get(str(frontier), {})
    meta = stages.get(frontier, {})
    streak = row.get("fail_streak", 0)
    last_status = row.get("last_status", "TODO")
    sigs = row.get("signatures", {})
    distinct = len(sigs)
    dominant = max(sigs.values()) if sigs else 0
    category = row.get("last_category", "")

    # --- classify the moment ----------------------------------------------
    if last_status == "TODO" and streak < STUCK_AFTER:
        kind = "focused"
    elif distinct >= 3 and dominant <= 1:
        kind = "flailing"
    elif streak >= STUCK_AFTER:
        kind = "stuck"
    else:
        kind = "focused"

    # --- fill the advice ---------------------------------------------------
    advice.update({
        "kind": kind,
        "mentor": kind in ("stuck", "flailing"),
        "stage": frontier,
        "file": meta.get("file", row.get("file", "")),
        "stage_title": meta.get("title", row.get("title", "")),
        "action": meta.get("action", ""),
        "predict": meta.get("predict", ""),
        "experiment": ("Reproduce the smallest failing case in a scratch file, "
                       "print the intermediate values, and name the first one "
                       "that is wrong before you edit anything."),
        "reference": _reference(course, meta),
        "pattern": _pattern_note(profile, prefer=category),
        "cause": patterns.condense(row.get("last_detail", "")),
        "hint_hint": f"stuck? run: python3 codecraft/cli.py hint {name}",
    })

    # hints the learner explicitly asked for always win
    requested = store.hint_level(profile, name, frontier)
    auto = 0
    if kind in ("stuck", "flailing"):
        auto = 1
    if style == "deep":
        auto = min(auto, 0) if kind == "focused" else auto
    elif style == "fast" and kind == "focused" and streak >= 2:
        auto = 1
    advice["hint_level"] = max(requested, auto)

    # --- pacing ------------------------------------------------------------
    first_tries = _consecutive_first_try(cstate, frontier)
    if kind == "focused" and first_tries >= 2 and style != "deep":
        advice.update({
            "kind": "accelerate",
            "pace": (f"You have passed {first_tries} stages in a row on the "
                     f"first try — start stage {frontier} now and leave hints "
                     "closed. If it yields on the first run, the built-in "
                     "curriculum is below your level; consider authoring a "
                     "harder course (python3 codecraft/cli.py new ...)."),
        })
    elif kind == "stuck":
        advice["pace"] = (f"Run {streak} on the same failure. Stop re-running "
                          "unchanged: change exactly one thing per attempt.")
    elif kind == "flailing":
        advice["pace"] = ("Different failure every run — you are changing too "
                          "much at once. Freeze everything, get the smallest "
                          "case passing, then move one step back toward the full "
                          "requirement.")
    else:
        advice["pace"] = "One function at a time; re-run after each."

    advice["review"] = _due_review(profile)
    return advice


def _reference(course: dict, meta: dict) -> str:
    if meta.get("solution"):
        return meta["solution"]
    sol = os.path.join(course["dir"], "solutions", meta.get("file", ""))
    if meta.get("file") and os.path.exists(sol):
        return f"solutions/{meta['file']}"
    return os.path.join(course["name"], meta.get("file", "")) if meta.get("file") else ""


def _recommend_next(course: dict, all_courses) -> str:
    if not all_courses:
        return "Course complete."
    after = [c for c in all_courses if c["order"] > course["order"]]
    if after:
        nxt = after[0]
        return (f"Course complete. Next: {nxt['title']} "
                f"(python3 codecraft/cli.py run {nxt['name']}).")
    return "Course complete — and it is the last built-in course. Time to author one."


def hints_for(advice: dict, meta: dict, level: int):
    """The escalating hint ladder for a stage. level 0..3."""
    action = meta.get("action", "")
    predict = meta.get("predict", "")
    reference = advice.get("reference", "")
    explicit = list(meta.get("hints", []))
    ladder = explicit + [
        action or "Re-read the stage docstring; it states what and why.",
        (f"Smallest experiment: {advice.get('experiment', '')} "
         f"Then predict: {predict}") if predict else
        advice.get("experiment", ""),
        (f"Read {reference} — but only after attempting; a solution read cold "
         "is just more prose.") if reference else
        "Ask for the solution reference and read it after attempting.",
    ]
    ladder = [h for h in ladder if h]
    return ladder[:level + 1]
