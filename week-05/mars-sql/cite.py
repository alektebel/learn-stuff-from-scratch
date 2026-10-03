"""
Step 4 — Cite the SQL back to schema sentences
==============================================
Join with ContextCite. The schema is the context; the SQL is the response.
The top-cited sources should be the columns the query actually uses
(employees.name, employees.id, departments.manager_id, departments.name).

If ContextCite points at employees.title, the attribution is listening
to the schema rather than to the SQL — which is the same failure mode
as whole-response attribution missing a poison sentence in contextcite/.
"""

from typing import Dict, List, Sequence


def schema_context(sentences: Sequence[str]) -> str:
    """TODO: join schema sentences with a space. Stable order."""
    raise NotImplementedError


def cite_sql(sql: str, context: str, top_k: int = 4) -> List[Dict]:
    """Run ContextCite; return top_k {"index","source","score"} dicts.

    TODO: same pattern as week-05/spade/cite.py — import ContextCiter
    from ../contextcite, use ToyLM(context, query=sql) or pass
    response=sql. Do ../contextcite/ first.
    """
    raise NotImplementedError


def used_columns(sql: str) -> List[str]:
    """Columns the SQL actually names, as 'table.column' when qualified,
    else just 'column'.

    TODO: a regex over identifiers around '.' is enough. Lowercase.
    The checker uses this to decide whether a citation is relevant.
    """
    raise NotImplementedError


def citations_are_relevant(citations: Sequence[Dict],
                           sql: str) -> bool:
    """True iff every cited source sentence mentions a column that
    used_columns(sql) also names (unqualified match is allowed).

    TODO: 'The employees table has a column title.' is NOT relevant
    to a query that never mentions title. That is the assertion.
    """
    raise NotImplementedError
