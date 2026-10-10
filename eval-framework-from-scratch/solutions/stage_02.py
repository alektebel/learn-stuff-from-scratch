"""Eval Framework From Scratch — stage 2: the metric plugins.

DESIGN DECISION — why is a metric a plugin looked up by name?
    The runner must not know what it measures. A suite names its metrics, and the
    registry is what turns a name into a callable, exactly once. A metric that is
    not registered is then a configuration bug with a message, not an absent
    number in a log nobody reads twice. The alternative — a chain of
    `if name == ...` inside the runner — puts the metric catalogue into the
    machine and makes every new metric a change to the framework.

DESIGN DECISION — why does `bind` resolve the whole list before anything runs?
    A missing plugin must fail before the first case, not in the tenth record.
    Resolving lazily turns a typo into a run that has already spent its model
    calls and its judge budget, whose second metric is quietly missing, and whose
    failure is attributed to the system under test as a metric error. Resolving
    the whole list up front makes the typo a refusal that happens before any
    measurement exists.

DESIGN DECISION — why are a raise, a `bool`, a `str`, `nan` and `inf` recorded
    as errors rather than turned into values?
    Attribution, and the shape of a record. A plugin that raises is OUR bug — the
    case under test may be perfect — so letting it kill the run, or folding it
    into a number, blames the wrong side. A `bool` is not a measurement
    (`True == 1` in Python, so a flag becomes a perfect score), a `str` is not a
    number however much it looks like one, and `nan`/`inf` are not numbers a mean
    can survive: `nan` poisons every sum it enters and `inf` makes a spread
    meaningless. All of them go into `errors` keyed by the metric's NAME — the
    key is what a record is read by — and nothing goes into `values`.

DESIGN DECISION — why is `None` "not applicable" instead of `0.0`?
    A zero is a measurement: it votes in every mean and drags the score down. A
    metric that cannot see this case — a judge metric on a case with no
    reference, say — has measured nothing, so the honest entry is `None`, which
    stage 5 counts only as a smaller denominator. Storing `0.0` (or dropping the
    key) turns "we did not measure this" into either a wrong score or an
    invisible gap.
"""

from math import isfinite

from lab import ConfigError


class MetricRegistry:
    """The name -> callable table a suite's `metrics` list is resolved against."""

    def __init__(self):
        """An empty registry. The table belongs to the instance, not the class."""
        self._metrics = {}

    def register(self, name, fn):
        """Add `fn` under `name`. A duplicate name, or a plugin that is not
        callable, is refused: the run must not guess which of the two it has."""
        if not callable(fn):
            raise ConfigError("metric plugin %r is not callable: %r" % (name, fn))
        if name in self._metrics:
            raise ConfigError("metric plugin %r is already registered" % (name,))
        self._metrics[name] = fn

    def resolve(self, name):
        """The callable registered under `name`, or a ConfigError that names both
        the missing plugin and the ones that do exist."""
        try:
            return self._metrics[name]
        except KeyError:
            known = ", ".join(sorted(self._metrics)) or "(none registered)"
            raise ConfigError("unknown metric plugin %r; known plugins: %s"
                              % (name, known)) from None

    def bind(self, names):
        """Resolve every name in `names` up front into the ordered
        `((name, fn), ...)` a runner hands to `apply_metrics`."""
        return tuple((name, self.resolve(name)) for name in names)


def _describe(value):
    """The bad value, with the type that made it bad, short enough for a record."""
    if isinstance(value, bool):
        return "bool %r" % (value,)
    if isinstance(value, str):
        return "str %r" % (value,)
    if isinstance(value, float):
        return "float %r" % (value,)
    return "%s %r" % (type(value).__name__, value)


def _bad(name, value):
    """The metric error for an answer that is neither a number nor `None`."""
    return "%s: %s is not a finite number or None" % (name, _describe(value))


def _is_number(value):
    """A finite real number — and not a `bool`, because `True == 1` in Python."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return isfinite(value)


def apply_metrics(case, answer, bound):
    """Measure one answer with the already-bound metrics.

    Returns `{"values": {name: float | None}, "errors": {name: str}}`: a finite
    number is a value, `None` is "not applicable to this case" (the entry stays,
    so stage 5 can shrink its `n`), and every failure — a raise, a `bool`, a
    `str`, `nan`, `inf` — is an error under the metric's name and never a value.
    """
    values, errors = {}, {}
    for name, fn in bound:
        try:
            value = fn(case, answer)
        except Exception as exc:                                # noqa: BLE001
            errors[name] = "%s: %s" % (type(exc).__name__, exc)
            continue
        if value is None:
            values[name] = None
            continue
        if not _is_number(value):
            errors[name] = _bad(name, value)
            continue
        values[name] = float(value)
    return {"values": values, "errors": errors}
