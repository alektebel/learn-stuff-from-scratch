"""A DATA step engine: the imperative answer, and why it survived.

SQL says WHAT. A DATA step says HOW, one row at a time, and that difference is
not a matter of taste -- it changes which transformations are easy.

The model is small and strange, and every part of it matters:

    the PDV        a Program Data Vector: one row's variables, held between
                   statements. It is a register file, not a row.
    implicit loop  the whole step runs once PER INPUT ROW, automatically, and
                   writes the PDV out at the bottom unless told otherwise.
    RETAIN         a variable that is NOT reset between iterations, which is how
                   you carry a running total without a window function.
    BY groups      with `first.x` and `last.x` flags, which is how you do
                   per-group logic without GROUP BY -- and it requires sorted
                   input, which is the catch.
    MERGE          a row-at-a-time join over sorted inputs, and its semantics
                   differ from a SQL join in ways that surprise people.
    OUTPUT/DELETE  explicit control of what leaves the step. One input row can
                   produce zero rows, or ten.

That last one is the real answer to "why does this still exist". A DATA step
can emit a variable number of rows per input row, carry state across rows, and
branch -- all things SQL needs a window function, a recursive CTE or a UDF to
express, if it can express them at all.

The demo runs the same five transformations both ways and reports which is
shorter and which is clearer, which are not always the same answer.

Pairs with `week-18/sas-lineage-tool/`, which parses these rather than runs them.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence


class PDV:
    """The Program Data Vector: the variables of the row being built.

    DESIGN DECISION worth arguing with: everything is mutable and global to the
    step. That is what makes RETAIN and the implicit loop expressible, and it is
    also why a long DATA step is hard to reason about. Modern dataframe APIs
    chose the opposite and gave up the implicit loop to get it.

    TODO
    """


class DataStep:
    """One step: input, statements, and the implicit loop around them.

    TODO
    """


def retain(*args, **kwargs) -> Any:
    """Mark a variable as surviving the implicit loop. TODO"""
    raise NotImplementedError


def by_groups(rows: Sequence[Dict[str, Any]], keys: Sequence[str]
              ) -> Iterator[Dict[str, Any]]:
    """Annotate each row with first.<k> and last.<k> flags.

    Requires the input SORTED by `keys`. Run it on unsorted input and it
    silently produces wrong groups rather than an error -- which is the single
    most common DATA step bug, and the check asserts it is detected.

    TODO
    """
    raise NotImplementedError


def merge(*args, **kwargs) -> Iterator[Dict[str, Any]]:
    """A row-at-a-time merge over sorted inputs.

    Compare against `executor.NestedLoopJoin` and `executor.HashJoin`. A MERGE
    is not an inner join, not a left join, and not quite a full outer join: on
    a many-to-many match its behaviour is a documented surprise. Reproduce it,
    then say which SQL join it actually equals.

    TODO
    """
    raise NotImplementedError


def output(*args, **kwargs) -> None:
    """Emit the current PDV explicitly. TODO"""
    raise NotImplementedError


def run_step(*args, **kwargs) -> List[Dict[str, Any]]:
    """Execute the implicit loop to exhaustion. TODO"""
    raise NotImplementedError


def same_transformation_in_sql(*args, **kwargs) -> str:
    """The SQL that does the same thing, for the comparison table.

    Five cases, and the interesting ones are where the answer is 'you cannot,
    cleanly': a running total that resets on a condition, and emitting a
    variable number of rows per input row.

    TODO
    """
    raise NotImplementedError
