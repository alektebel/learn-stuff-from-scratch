"""Eval Framework From Scratch — stage 7: records whose bytes two runs share.

DESIGN DECISION — why is a record one canonical line, with its keys sorted?
    The log is not a pretty document, it is a thing that gets compared. The
    resume (stage 10) asks whether the bytes after a crash equal the bytes of an
    uninterrupted run, the diff (stage 9) compares two runs of the same suite,
    and a human runs `diff` over two of them at three in the morning. A dict that
    serialises in insertion order would make those comparisons depend on how a
    record happened to be built, so the line is sorted and carries no whitespace:
    two runs that measured the same thing produce the same bytes, and a
    difference in the log is a difference in the run.

DESIGN DECISION — why is there no `default=` in the serialiser?
    `json.dumps(..., default=str)` never fails, and that is the problem. A value
    JSON cannot write is a bug in the record, and a bug that reaches the log as
    `"<lab.Actor object at 0x7f3c...>"` has been laundered into a field the
    analysis reads as a name; the address even differs between runs, so the two
    runs that produced it no longer share bytes and the failure surfaces far from
    its cause. Raising here surfaces it at the append that caused it.

DESIGN DECISION — why does `append` flush every record?
    The log is the only record of a run that may be interrupted, so its
    guarantee must not depend on the process exiting cleanly: "appended" has to
    mean "readable now" — by the resume that starts after this process died, and
    by any reader inside it. Buffering the writes and flushing at exit instead
    makes the log's contents a function of how the process ended, which is
    exactly the variable the log exists to remove.

DESIGN DECISION — why does the reader refuse a bad line, and why is `tolerant`
only about the final one?
    A line that is not a JSON object means the log is damaged, and a silent skip
    turns a damaged log into a shorter run whose numbers are computed over the
    survivors: the mistake is invisible and the measurement is wrong. The one
    damage the framework itself can produce is the writer dying mid-record, which
    leaves a final line with no terminator and no complete record under it;
    `tolerant=True` (the resume) drops that line and nothing else. Every other
    bad line — including a final one that was terminated — still raises, because
    a terminated line that does not parse was written as a complete record and is
    corruption, not a truncation.
"""

import json
import os

from lab import ConfigError
from stage_03 import round_metrics


def canonical(record):
    """The record as one canonical line of JSON: sorted keys, no whitespace.

    The metric values are rounded to `METRIC_DP` on a copy, never on the record
    handed in, so a caller may keep the value it measured. A record holding
    something JSON cannot serialise raises `TypeError`: there is no `default=`,
    because there is no harmless way to write an object into a field the
    analysis reads as a name.
    """
    rounded = round_metrics(record)
    return json.dumps(rounded, sort_keys=True, separators=(",", ":"))


def record_line(record):
    """The record as the log writes it: the canonical line and its terminator.

    The terminator is part of the record's bytes, not decoration: a file whose
    last line has none may have been cut mid-write, and the tolerant reader needs
    that evidence to tell a truncation from corruption.
    """
    return canonical(record) + "\n"


class RunLog:
    """An append-only log of records, one canonical line each.

    The file is opened in append mode and the handle is kept open, so a run that
    writes ten thousand records opens it once; every record is flushed before
    `append` returns. The parent directory is created on the first append, so a
    log may live in a directory the run created for itself.
    """

    def __init__(self, path):
        self.path = path
        self._handle = None

    def _open(self):
        """The append handle, opening the file and its directory on first use."""
        if self._handle is None:
            parent = os.path.dirname(os.path.abspath(self.path))
            os.makedirs(parent, exist_ok=True)
            self._handle = open(self.path, "a", encoding="utf-8")
        return self._handle

    def append(self, record):
        """Write one record and flush it: appended means readable now.

        The record is written as `record_line(record)`, so the bytes on disk are
        the canonical line and one terminator, and nothing else.
        """
        handle = self._open()
        handle.write(record_line(record))
        handle.flush()


def _is_object(line):
    """Whether `line` is complete JSON for an object — the only shape a record has."""
    try:
        return isinstance(json.loads(line), dict)
    except ValueError:
        return False


def _reject(path, number, line):
    """The refusal for a line that is not a record, naming where it was."""
    return ConfigError("%s: line %d is not a JSON object: %r" % (path, number, line))


def read_records(path, *, tolerant=False):
    """The records a log holds, in order; a log that does not exist is empty.

    Every line must be a JSON object, and a bad line raises `ConfigError` naming
    its line number. With `tolerant=True` the one damage a writer can leave
    behind is forgiven: a final line with no terminator (the writer died
    mid-record) is dropped. Any other bad line — earlier, or terminated — still
    raises, because skipping it would silently shrink the run.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        return []
    if not text:
        return []
    parts = text.split("\n")
    tail = parts.pop()
    if tail:
        if tolerant and not _is_object(tail):
            tail = None
        else:
            parts.append(tail)
    records = []
    for number, line in enumerate(parts, start=1):
        try:
            value = json.loads(line)
        except ValueError:
            raise _reject(path, number, line)
        if not isinstance(value, dict):
            raise _reject(path, number, line)
        records.append(value)
    return records
