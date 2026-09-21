"""
SQL — tokeniser, parser, AST. Complete Solution.

SQL is the only interface most people ever have to everything in the other
files. This turns text into a tree; planner.py decides how to execute the tree;
executor.py runs it.

DESIGN DECISION — a parser generator, or recursive descent by hand?
  yacc/ANTLR/lark would be shorter and the grammar would be a document.
  CHOSEN: hand-written recursive descent with precedence climbing, for the same
  reason `../c-compiler/` and `../compiler-and-vgpu/` do it: the error messages
  are the product. "expected FROM after the select list, found 'WHERE' at
  column 24" is a hand-written message. A generated parser says "syntax error"
  and gives you a state number. Every database you have ever used has a
  hand-written parser, and this is why.

DESIGN DECISION — one pass to a physical plan, or an AST first?
  You could execute while parsing. It is fewer lines and it is what a toy
  interpreter does.
  CHOSEN: parse to an AST that describes WHAT was asked, never HOW to do it.
  The separation is the entire reason a query optimiser can exist: `SELECT *
  FROM t WHERE id = 5` says nothing about using an index, and the planner is
  free to choose because the AST did not choose for it. Collapse these two
  stages and you have hard-coded every execution strategy into the grammar.

DESIGN DECISION — where does operator precedence live?
  CHOSEN: a table, plus one loop (`_binary`), rather than one function per
  precedence level. The classic recursive-descent shape — parse_or calls
  parse_and calls parse_comparison calls parse_sum — works, but adding a level
  means a new function and edits to two neighbours. Precedence climbing puts
  the whole grammar in a dict you can read at a glance.

THE TOKENISER TRAP, stated up front because everyone hits it:
  `SELECTED` must lex as one identifier, not the keyword SELECT followed by the
  identifier ED. Match the longest identifier FIRST, then ask whether that
  whole word is a keyword. The same class of bug as putting `//` after `/` in a
  lexer's alternation — see the comment in `../compiler-and-vgpu/frontend.py`,
  where exactly that shipped and had to be fixed.

Learning Path:
1. tokenize — and get the keyword rule right: longest identifier FIRST, then
   ask whether the whole word is a keyword
2. Parser.expression — precedence climbing, driven by the PRECEDENCE table
3. Parser.select — the clause order, then joins, GROUP BY, ORDER BY, LIMIT
4. insert / update / delete / create
5. Error messages that name a column and what was expected. They are the
   product, and they are the reason this is hand-written.
"""

import re
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

KEYWORDS = {
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
    "DELETE", "CREATE", "TABLE", "INDEX", "ON", "ORDER", "BY", "ASC", "DESC",
    "LIMIT", "OFFSET", "AND", "OR", "NOT", "NULL", "IS", "IN", "JOIN", "INNER",
    "LEFT", "GROUP", "HAVING", "AS", "COUNT", "SUM", "AVG", "MIN", "MAX",
    "BEGIN", "COMMIT", "ROLLBACK", "EXPLAIN", "PRIMARY", "KEY", "INT", "TEXT",
    "REAL", "DISTINCT",
}

# Order matters and it is load-bearing. Two-character operators must precede
# their one-character prefixes or `<=` lexes as `<` then `=`, and IDENT must
# come before anything that could match a prefix of a word.
TOKEN_SPEC = [
    ("WS",      r"[ \t\r\n]+"),
    ("COMMENT", r"--[^\n]*"),
    ("NUMBER",  r"\d+\.\d+|\d+"),
    ("STRING",  r"'(?:[^']|'')*'"),
    ("IDENT",   r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP",      r"<>|!=|<=|>=|=|<|>|\+|-|\*|/|%|\|\|"),
    ("PUNCT",   r"[(),.;]"),
]
MASTER = re.compile("|".join(f"(?P<{name}>{pattern})"
                             for name, pattern in TOKEN_SPEC))


class Token(NamedTuple):
    kind: str
    value: Any
    column: int

    def __repr__(self) -> str:
        return f"{self.kind}({self.value!r})"


class SQLError(Exception):
    """A parse error that says where and what was expected.

    The column is not decoration. A 400-character generated query is unreadable
    without it, and this is the class of error a user sees most often.
    """


def tokenize(text: str) -> List[Token]:
    raise NotImplementedError


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------

class Column(NamedTuple):
    name: str
    table: Optional[str] = None

    def __repr__(self) -> str:
        return f"{self.table + '.' if self.table else ''}{self.name}"


class Literal(NamedTuple):
    value: Any

    def __repr__(self) -> str:
        return repr(self.value)


class BinOp(NamedTuple):
    op: str
    left: Any
    right: Any

    def __repr__(self) -> str:
        return f"({self.left!r} {self.op} {self.right!r})"


class UnaryOp(NamedTuple):
    op: str
    operand: Any

    def __repr__(self) -> str:
        return f"({self.op} {self.operand!r})"


class Aggregate(NamedTuple):
    function: str
    argument: Any

    def __repr__(self) -> str:
        return f"{self.function}({self.argument!r})"


class Star(NamedTuple):
    def __repr__(self) -> str:
        return "*"


class Select(NamedTuple):
    columns: List[Any]
    table: str
    alias: Optional[str]
    joins: List[Tuple[str, str, Optional[str], Any]]  # kind, table, alias, ON
    where: Optional[Any]
    group_by: List[Column]
    having: Optional[Any]
    order_by: List[Tuple[Any, bool]]       # (expression, descending)
    limit: Optional[int]
    offset: Optional[int]
    distinct: bool


class Insert(NamedTuple):
    table: str
    columns: List[str]
    rows: List[List[Any]]


class Update(NamedTuple):
    table: str
    assignments: List[Tuple[str, Any]]
    where: Optional[Any]


class Delete(NamedTuple):
    table: str
    where: Optional[Any]


class CreateTable(NamedTuple):
    table: str
    columns: List[Tuple[str, str]]
    primary_key: Optional[str]


class CreateIndex(NamedTuple):
    name: str
    table: str
    column: str


class Transactional(NamedTuple):
    kind: str                              # BEGIN / COMMIT / ROLLBACK


class Explain(NamedTuple):
    statement: Any


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# (precedence, right_associative). Higher binds tighter. Adding a level is one
# line here, not a new function and edits to its two neighbours.
PRECEDENCE: Dict[str, Tuple[int, bool]] = {
    "OR": (1, False), "AND": (2, False),
    "=": (4, False), "<>": (4, False), "!=": (4, False), "<": (4, False),
    ">": (4, False), "<=": (4, False), ">=": (4, False), "IS": (4, False),
    "IN": (4, False),
    "||": (5, False),
    "+": (6, False), "-": (6, False),
    "*": (7, False), "/": (7, False), "%": (7, False),
}


class Parser:
    def __init__(self, text: str):
        self.text = text
        self.tokens = tokenize(text)
        self.position = 0

    # -- token plumbing -----------------------------------------------------

    @property
    def current(self) -> Token:
        return self.tokens[self.position]

    def at(self, kind: str, value: Any = None) -> bool:
        token = self.current
        return token.kind == kind and (value is None or token.value == value)

    def accept(self, kind: str, value: Any = None) -> Optional[Token]:
        if self.at(kind, value):
            token = self.current
            self.position += 1
            return token
        return None

    def expect(self, kind: str, value: Any = None) -> Token:
        token = self.accept(kind, value)
        if token is None:
            wanted = value or kind
            raise SQLError(f"expected {wanted} at column {self.current.column}, "
                           f"found {self.current.value!r}")
        return token

    # -- statements ---------------------------------------------------------

    def parse(self) -> Any:
        raise NotImplementedError

    def statement(self) -> Any:
        raise NotImplementedError

    def select(self) -> Select:
        raise NotImplementedError

    def table_alias(self) -> Optional[str]:
        """`FROM users u` and `FROM users AS u`, both optional.

        A bare alias is only safe because keywords lex as KEYWORD rather than
        IDENT — otherwise `FROM users WHERE ...` would read WHERE as the alias
        and then fail somewhere confusing. The tokeniser decision from the top
        of this file is what makes this two lines instead of a lookahead table.
        """
        raise NotImplementedError

    def select_item(self) -> Any:
        raise NotImplementedError

    def column_ref(self) -> Column:
        raise NotImplementedError

    def insert(self) -> Insert:
        raise NotImplementedError

    def update(self) -> Update:
        raise NotImplementedError

    def delete(self) -> Delete:
        raise NotImplementedError

    def create(self) -> Any:
        raise NotImplementedError

    # -- expressions --------------------------------------------------------

    def expression(self, min_precedence: int = 0) -> Any:
        """Precedence climbing.

        Parse one operand, then keep absorbing operators whose precedence is at
        least `min_precedence`, recursing with a HIGHER minimum for
        left-associative operators and the SAME one for right-associative. Two
        loops and a table replace one function per precedence level, and the
        grammar becomes something you can read.
        """
        raise NotImplementedError

    def unary(self) -> Any:
        raise NotImplementedError

    def primary(self) -> Any:
        raise NotImplementedError


def parse(text: str) -> Any:
    return Parser(text).parse()


def _demo() -> None:
    """Once the checks pass, write a demo that PRINTS these four things:

    1. The tokeniser trap. Lex SELECT, SELECTED, select, counted and COUNT.
       SELECTED must be ONE identifier.

    2. Precedence, from the table. Show `1 + 2 * 3`, `(1 + 2) * 3`,
       `a = 1 AND b = 2 OR c = 3` and `NOT a = 1 AND b = 2` as parsed trees.
       AND binding tighter than OR is the one people get wrong.

    3. One example of every statement form, printing the AST node type.

    4. Five broken statements and the error each produces. Every message should
       name the column and what was expected — that is the entire argument for
       writing the parser by hand rather than generating it.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
