"""Agents From Scratch — stage 10: the trace, and the audit that reads the
world instead of the story

DESIGN DECISION — the trace is a summary you can diff, not a transcript you
re-read.
    A run's value after it ends is what it proves: which calls happened, in what
    order, how big the payloads were, why it stopped. Copying the transcript
    into the log makes it unreadable and unmailable, and putting a wall clock or
    an object id in it makes two identical runs produce two different files —
    which is exactly what turns "the numbers moved" into a mystery. Counted, not
    copied; no timestamps; no ids.

DESIGN DECISION — grade the world, not the story.
    The last thing an agent says is the least reliable evidence about what it
    did. Every detector here reads the filesystem before and after the run:
    files that changed, files that appeared, a secret that leaked in any of the
    encodings a model reaches for, and lines that were ADDED to a file. That
    last one has a subtlety worth the whole stage: a file that already contained
    a matching line has not been changed by the agent, and a detector that flags
    it is a detector that lies about the past.

DESIGN DECISION — a detector that has never fired is a comment.
    Every check in this stage is exercised twice: once against a run that
    violates it (the violation must be named, with the path and the line) and
    once against a clean run (nothing must be reported). A safety check with no
    positive case proves nothing about what it would catch, which is why the
    fixtures that break the rules are as important as the agent itself.

TODO: implement

    trace_of(run) -> list[dict]
        The run summarised as typed events, in order:
            {"event": "model_call",   "step": 1, "saw": 3}
            {"event": "tool_call",    "step": 1, "tool": name, "args": {...}}
            {"event": "tool_result",  "step": 1, "tool": name, "ok": bool,
                                      "chars": int}
            {"event": "final",        "step": 2, "chars": int}
            {"event": "stop",         "status": str, "steps": int,
                                      "tool_calls": int}
        No timestamps, no ids, no full payloads: `chars` is the size, the
        transcript stays in the run. Two runs of the same scripted model must
        produce identical events.

    to_jsonl(events) -> str
        One compact JSON object per line (sorted keys), trailing newline. This
        is the file that goes in CI, so it has to be diffable.

    snapshot(root) -> dict
        {relative path: {"kind": "file" | "dir" | "link", "path": absolute path,
                         "digest": sha256 hex of the bytes | readlink target | ""}}
        Sorted by path, recursive, symlinks never followed (a digest of what a
        link points at is not a property of the link). The absolute `path` is
        what the detectors on this page open: a snapshot is compared relative but
        read absolute, and a detector that opens the relative key reads the file
        only when the process happens to sit in the right directory.

    diff_snapshots(before, after) -> {"added": [...], "removed": [...],
                                      "modified": [...]}
        Sorted relative paths. A file that changed kind (file -> link) counts as
        modified. `unchanged(before, after, path)` returns a violation string or
        None, using the same comparison for one path or a directory prefix, with
        the words a reviewer needs: "tests/test_stats.py was modified".

    no_leak(after, token, exclude=()) -> list[str]
        Every file in the snapshot whose bytes contain `token` in plain text,
        base64 (as produced by base64.b64encode, with and without padding), hex
        (lower and upper), or reversed. Each violation names the path and the
        encoding: "build/log.txt contains the secret (base64)". `exclude` is a
        tuple of path prefixes.

    no_new_match(before, after, pattern, under="") -> list[str]
        Lines ADDED by the run (present in `after`, absent from that file's
        `before` version) that match the regex, one violation per line, naming
        the path. Lines that were already there are not violations.

    audit(run=None, *, before, after, policy) -> dict
        {"ok": bool, "violations": [str, ...], "events": [...]}
        `policy` keys: "unchanged" (list of paths), "no_new_match" (list of
        regexes), "no_leak" (list of tokens), "under" (path prefix for the match
        check). Every violation is a string a person can act on. `run` is
        optional: `events` is the trace when a run is given, else [].
"""


def trace_of(run):
    raise NotImplementedError("stage 10: implement trace_of()")


def to_jsonl(events):
    raise NotImplementedError("stage 10: implement to_jsonl()")


def snapshot(root):
    raise NotImplementedError("stage 10: implement snapshot()")


def diff_snapshots(before, after):
    raise NotImplementedError("stage 10: implement diff_snapshots()")


def unchanged(before, after, path):
    raise NotImplementedError("stage 10: implement unchanged()")


def no_leak(after, token, exclude=()):
    raise NotImplementedError("stage 10: implement no_leak()")


def no_new_match(before, after, pattern, under=""):
    raise NotImplementedError("stage 10: implement no_new_match()")


def audit(run=None, *, before, after, policy):
    raise NotImplementedError("stage 10: implement audit()")
