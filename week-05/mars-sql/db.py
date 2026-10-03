"""
Provided — a two-table company database and a tiny SQL executor.

Not an exercise. The Generation Agent talks to `execute`, and the errors
it returns are the observations the ReAct loop is supposed to use.

    departments(id, name, manager_id)
    employees(id, name, dept_id, title)

Running question:
    "Who is the manager of the Sales department?"

Gold SQL (one of several equivalent forms the executor accepts):
    SELECT employees.name
    FROM employees
    JOIN departments ON employees.id = departments.manager_id
    WHERE departments.name = 'Sales'
"""

import re
from typing import Dict, List, Sequence, Tuple, Union

Row = Dict[str, Union[int, str]]
Result = Union[List[Row], str]          # rows, or an error string

DEPARTMENTS: List[Row] = [
    {"id": 1, "name": "Sales", "manager_id": 10},
    {"id": 2, "name": "Engineering", "manager_id": 11},
    {"id": 3, "name": "HR", "manager_id": 12},
]

EMPLOYEES: List[Row] = [
    {"id": 10, "name": "Ada Lovelace", "dept_id": 1, "title": "Director"},
    {"id": 11, "name": "Alan Turing", "dept_id": 2, "title": "Director"},
    {"id": 12, "name": "Grace Hopper", "dept_id": 3, "title": "Director"},
    {"id": 13, "name": "Katherine Johnson", "dept_id": 2, "title": "Analyst"},
    {"id": 14, "name": "Claude Shannon", "dept_id": 1, "title": "Rep"},
]

TABLES: Dict[str, List[Row]] = {
    "departments": DEPARTMENTS,
    "employees": EMPLOYEES,
}

SCHEMA: Dict[str, List[str]] = {
    "departments": ["id", "name", "manager_id"],
    "employees": ["id", "name", "dept_id", "title"],
}

QUESTION = "Who is the manager of the Sales department?"
GOLD_NAME = "Ada Lovelace"

# Table-name typos the paper's Figure 5 analogue will emit on purpose.
TYPOS = {"fprm": "departments", "emplyees": "employees", "deptments": "departments"}


class OperationalError(Exception):
    pass


def describe(table: str) -> List[str]:
    if table not in TABLES:
        raise OperationalError(f"no such table: {table}")
    return list(SCHEMA[table])


def _norm(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip()).rstrip(";").strip()


def execute(sql: str) -> List[Row]:
    """A deliberately small executor. Supports:

      SELECT <table>.<col>|<col> FROM <table>
      SELECT ... FROM a JOIN b ON a.<col> = b.<col> WHERE <table>.<col> = '<val>'
      SELECT ... FROM <table> WHERE <col> = '<val>'

    Unknown tables raise OperationalError with the name. That string is
    what the Generation Agent has to read. Do not catch it inside execute.
    """
    text = _norm(sql)
    lowered = text.lower()

    for typo in TYPOS:
        if re.search(rf"\b{typo}\b", lowered):
            raise OperationalError(f"no such table: {typo}")

    # FROM / JOIN table names.
    from_m = re.search(r"\bfrom\s+([a-z_]+)", lowered)
    if not from_m:
        raise OperationalError("syntax: missing FROM")
    left = from_m.group(1)
    if left not in TABLES:
        raise OperationalError(f"no such table: {left}")

    join_m = re.search(r"\bjoin\s+([a-z_]+)\s+on\s+"
                       r"([a-z_]+)\.([a-z_]+)\s*=\s*([a-z_]+)\.([a-z_]+)",
                       lowered)
    where_m = re.search(r"\bwhere\s+([a-z_]+)\.([a-z_]+)\s*=\s*'([^']+)'",
                        text, flags=re.I)
    if where_m is None:
        where_m = re.search(r"\bwhere\s+([a-z_]+)\s*=\s*'([^']+)'",
                            text, flags=re.I)

    select_m = re.search(r"\bselect\s+(.*?)\s+from\b", lowered)
    if not select_m:
        raise OperationalError("syntax: missing SELECT")
    selected = [p.strip() for p in select_m.group(1).split(",")]

    if join_m:
        right = join_m.group(1)
        if right not in TABLES:
            raise OperationalError(f"no such table: {right}")
        a_tbl, a_col = join_m.group(2), join_m.group(3)
        b_tbl, b_col = join_m.group(4), join_m.group(5)
        # Resolve aliases: we only accept real table names as qualifiers.
        if a_tbl not in TABLES or b_tbl not in TABLES:
            raise OperationalError("join qualifier must be a table name")
        rows = []
        for left_row in TABLES[left]:
            for right_row in TABLES[right]:
                pair = {left: left_row, right: right_row}
                if pair[a_tbl][a_col] != pair[b_tbl][b_col]:
                    continue
                if where_m:
                    if where_m.lastindex == 3:
                        w_tbl, w_col, w_val = where_m.group(1), where_m.group(2), where_m.group(3)
                        if str(pair[w_tbl.lower()][w_col.lower()]) != w_val:
                            continue
                    else:
                        w_col, w_val = where_m.group(1), where_m.group(2)
                        # Unqualified WHERE: must match exactly one side.
                        matches = [r for r in (left_row, right_row)
                                   if w_col.lower() in r
                                   and str(r[w_col.lower()]) == w_val]
                        if not matches:
                            continue
                projected = {}
                for item in selected:
                    if "." in item:
                        t, c = item.split(".", 1)
                        projected[c] = pair[t][c]
                    else:
                        # Unqualified: prefer the left table, then right.
                        if item in left_row:
                            projected[item] = left_row[item]
                        else:
                            projected[item] = right_row[item]
                rows.append(projected)
        return rows

    rows = list(TABLES[left])
    if where_m:
        if where_m.lastindex == 3:
            _, w_col, w_val = where_m.group(1), where_m.group(2), where_m.group(3)
        else:
            w_col, w_val = where_m.group(1), where_m.group(2)
        rows = [r for r in rows if str(r[w_col.lower()]) == w_val]

    out = []
    for row in rows:
        projected = {}
        for item in selected:
            col = item.split(".", 1)[-1]
            if col not in row:
                raise OperationalError(f"no such column: {col}")
            projected[col] = row[col]
        out.append(projected)
    return out


def gold_rows() -> List[Row]:
    return execute(
        "SELECT employees.name FROM employees "
        "JOIN departments ON employees.id = departments.manager_id "
        "WHERE departments.name = 'Sales'"
    )


def schema_sentences() -> List[str]:
    """One sentence per column — the ContextCite sources for cite.py."""
    sentences = []
    for table, columns in SCHEMA.items():
        for column in columns:
            sentences.append(f"The {table} table has a column {column}.")
    return sentences
