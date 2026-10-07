"""Terminal rendering. The point is the *smallest* useful thing to read.

Default output after a run is the checker's own block plus three or four
coach lines. Detail escalates only when the history says you are stuck.
"""

import textwrap

GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


class Ink:
    def __init__(self, colour: bool):
        self.colour = colour

    def __call__(self, text, code=""):
        if not self.colour or not code:
            return text
        return f"{code}{text}{RESET}"

    def bold(self, t):
        return self(t, BOLD)

    def grey(self, t):
        return self(t, GREY)


def _wrap(label, text, ink, width=76):
    if not text:
        return []
    head = textwrap.wrap(text, width=width) or [""]
    lines = [f"  {ink(label.ljust(8), BOLD)}{head[0]}"]
    for extra in head[1:]:
        lines.append(f"  {' ' * 8}{extra}")
    return lines


def render_advice(advice, meta, ink: Ink):
    kind = advice["kind"]
    stage = advice.get("stage")
    where = ""
    if stage:
        where = (f"stage {stage}  {advice.get('file', '')}"
                 f"  \u2014 {advice.get('stage_title', '')}")
    lines = ["", ink(f"  codecraft \u00b7 {advice['title']}"
                     + (f" \u00b7 {where}" if where else ""), BOLD)]

    if kind == "not-started":
        lines += _wrap("start", advice["action"], ink)
        lines += _wrap("run", advice["pace"], ink)
        return "\n".join(lines)

    if kind == "done":
        lines += _wrap("done", advice["pace"], ink)
        if advice.get("pattern"):
            lines += _wrap("pattern", advice["pattern"], ink)
        if advice.get("review"):
            labels = ", ".join(f"{t} ({n})" for n, t, _ in advice["review"])
            lines += _wrap("review", f"still unretired: {labels}. "
                                     f"run: python3 codecraft/cli.py review", ink)
        return "\n".join(lines)

    lines += _wrap("cause", advice["cause"] or "no detail captured", ink)

    if kind == "accelerate":
        lines += _wrap("pace", advice["pace"], ink)
        lines += _wrap("next", f"open stage {stage} ({advice['file']}) and "
                               f"implement it without hints.", ink)
        return "\n".join(lines)

    lines += _wrap("now", advice["action"] or "re-read the stage docstring.", ink)

    if advice.get("hint_level", 0) >= 1 and kind in ("stuck", "flailing"):
        lines += _wrap("pace", advice["pace"], ink)
        lines += _wrap("try", advice["experiment"], ink)
    elif kind == "focused":
        lines += _wrap("pace", advice["pace"], ink)

    if advice.get("predict"):
        lines += _wrap("predict", advice["predict"], ink)
    if advice.get("pattern"):
        lines += _wrap("pattern", advice["pattern"], ink)
    if advice.get("reference") and advice.get("hint_level", 0) >= 2:
        lines += _wrap("ref", advice["reference"], ink)
    if advice.get("hint_hint"):
        lines += [f"  {ink(advice['hint_hint'], GREY)}"]
    return "\n".join(lines)


def render_hint(advice, meta, ladder, ink: Ink):
    lines = ["", ink(f"  codecraft \u00b7 hint ladder for stage "
                     f"{advice.get('stage')} ({advice.get('file')})", BOLD)]
    for i, hint in enumerate(ladder):
        lines += _wrap(f"hint {i}", hint, ink)
    lines += [f"  {ink('read top-down; stop as soon as you can act.', GREY)}"]
    return "\n".join(lines)


def render_dashboard(profile, courses, ink: Ink):
    lines = ["", ink("  codecraft \u00b7 your learning board", BOLD), ""]
    for course in courses:
        cstate = profile["courses"].get(course["name"], {})
        total = cstate.get("total") or len(course["stages"])
        passed = cstate.get("last_passed", 0)
        if not cstate:
            state = ink("not started", GREY)
            nxt = f"start stage {min(course['stages']) if course['stages'] else 1}"
        elif passed == total and total:
            state = ink("complete", GREEN)
            nxt = "author or pick the next course"
        else:
            state = ink(f"{passed}/{total}", YELLOW if passed else GREY)
            nxt = f"stage {cstate.get('next_step')} " \
                  f"({course['stages'].get(cstate.get('next_step'), {}).get('file', '')})"
        lines.append(f"  {course['title']:<32} {state:<20} {ink(nxt, GREY)}")
    pats = profile.get("patterns", {})
    top = sorted(pats.items(), key=lambda kv: kv[1].get("count", 0), reverse=True)[:3]
    if top:
        lines.append("")
        lines.append(ink("  recurring mistakes", BOLD))
        for label, row in top:
            lines.append(f"    {label:<26} {row['count']}x across "
                         f"{len(row['courses'])} courses")
    lines.append("")
    lines.append(ink("  next: python3 codecraft/cli.py run <course>", GREY))
    lines.append(ink("  plan: python3 codecraft/cli.py path", GREY))
    return "\n".join(lines)


def render_review(profile, items, ink: Ink):
    lines = ["", ink("  codecraft \u00b7 review queue", BOLD), ""]
    if not items:
        lines.append("  nothing due \u2014 concepts you stumble on surface here.")
        return "\n".join(lines)
    for name, tag, c in items:
        lines.append(f"  {ink(tag, BOLD)}  {ink('(' + name + ')', GREY)}")
        lines.append(f"    failed {c.get('fails', 0)}x, "
                     f"{store_label(c)}. Re-derive it from memory, then re-run "
                     f"the course to retire it.")
    return "\n".join(lines)


def store_label(c):
    return {0: "shaky", 1: "learning", 2: "getting there",
            3: "solid"}.get(c.get("box", 0), "learning")
