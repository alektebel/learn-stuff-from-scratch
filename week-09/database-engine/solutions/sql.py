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
    tokens: List[Token] = []
    position = 0
    while position < len(text):
        match = MASTER.match(text, position)
        if not match:
            raise SQLError(f"unexpected character {text[position]!r} at "
                           f"column {position + 1}")
        kind = match.lastgroup
        value = match.group()
        position = match.end()
        if kind in ("WS", "COMMENT"):
            continue
        if kind == "IDENT":
            # Longest-match first, THEN classify. Doing it the other way makes
            # `SELECTED` lex as SELECT + ED, and the parse error that follows
            # points at the wrong place entirely.
            upper = value.upper()
            if upper in KEYWORDS:
                kind, value = "KEYWORD", upper
        elif kind == "NUMBER":
            value = float(value) if "." in value else int(value)
        elif kind == "STRING":
            value = value[1:-1].replace("''", "'")
        tokens.append(Token(kind, value, match.start() + 1))
    tokens.append(Token("EOF", None, len(text) + 1))
    return tokens


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
        statement = self.statement()
        self.accept("PUNCT", ";")
        if not self.at("EOF"):
            raise SQLError(f"unexpected {self.current.value!r} after the end of "
                           f"the statement, at column {self.current.column}")
        return statement

    def statement(self) -> Any:
        if self.accept("KEYWORD", "EXPLAIN"):
            return Explain(self.statement())
        for keyword in ("BEGIN", "COMMIT", "ROLLBACK"):
            if self.accept("KEYWORD", keyword):
                return Transactional(keyword)
        if self.at("KEYWORD", "SELECT"):
            return self.select()
        if self.at("KEYWORD", "INSERT"):
            return self.insert()
        if self.at("KEYWORD", "UPDATE"):
            return self.update()
        if self.at("KEYWORD", "DELETE"):
            return self.delete()
        if self.at("KEYWORD", "CREATE"):
            return self.create()
        raise SQLError(f"expected a statement at column {self.current.column}, "
                       f"found {self.current.value!r}")

    def select(self) -> Select:
        self.expect("KEYWORD", "SELECT")
        distinct = self.accept("KEYWORD", "DISTINCT") is not None
        columns = [self.select_item()]
        while self.accept("PUNCT", ","):
            columns.append(self.select_item())

        self.expect("KEYWORD", "FROM")
        table = self.expect("IDENT").value
        alias = self.table_alias()

        joins = []
        while True:
            kind = "INNER"
            if self.accept("KEYWORD", "LEFT"):
                kind = "LEFT"
                self.accept("KEYWORD", "INNER")
            elif self.accept("KEYWORD", "INNER"):
                kind = "INNER"
            elif not self.at("KEYWORD", "JOIN"):
                break
            self.expect("KEYWORD", "JOIN")
            other = self.expect("IDENT").value
            other_alias = self.table_alias()
            self.expect("KEYWORD", "ON")
            joins.append((kind, other, other_alias, self.expression()))

        where = self.expression() if self.accept("KEYWORD", "WHERE") else None

        group_by: List[Column] = []
        if self.accept("KEYWORD", "GROUP"):
            self.expect("KEYWORD", "BY")
            group_by.append(self.column_ref())
            while self.accept("PUNCT", ","):
                group_by.append(self.column_ref())
        having = self.expression() if self.accept("KEYWORD", "HAVING") else None

        order_by: List[Tuple[Any, bool]] = []
        if self.accept("KEYWORD", "ORDER"):
            self.expect("KEYWORD", "BY")
            while True:
                expression = self.expression()
                descending = False
                if self.accept("KEYWORD", "DESC"):
                    descending = True
                else:
                    self.accept("KEYWORD", "ASC")
                order_by.append((expression, descending))
                if not self.accept("PUNCT", ","):
                    break

        limit = offset = None
        if self.accept("KEYWORD", "LIMIT"):
            limit = self.expect("NUMBER").value
        if self.accept("KEYWORD", "OFFSET"):
            offset = self.expect("NUMBER").value

        return Select(columns, table, alias, joins, where, group_by, having,
                      order_by, limit, offset, distinct)

    def table_alias(self) -> Optional[str]:
        """`FROM users u` and `FROM users AS u`, both optional.

        A bare alias is only safe because keywords lex as KEYWORD rather than
        IDENT — otherwise `FROM users WHERE ...` would read WHERE as the alias
        and then fail somewhere confusing. The tokeniser decision from the top
        of this file is what makes this two lines instead of a lookahead table.
        """
        if self.accept("KEYWORD", "AS"):
            return self.expect("IDENT").value
        token = self.accept("IDENT")
        return token.value if token else None

    def select_item(self) -> Any:
        if self.accept("OP", "*"):
            return Star()
        return self.expression()

    def column_ref(self) -> Column:
        name = self.expect("IDENT").value
        if self.accept("PUNCT", "."):
            return Column(self.expect("IDENT").value, table=name)
        return Column(name)

    def insert(self) -> Insert:
        self.expect("KEYWORD", "INSERT")
        self.expect("KEYWORD", "INTO")
        table = self.expect("IDENT").value
        columns: List[str] = []
        if self.accept("PUNCT", "("):
            columns.append(self.expect("IDENT").value)
            while self.accept("PUNCT", ","):
                columns.append(self.expect("IDENT").value)
            self.expect("PUNCT", ")")
        self.expect("KEYWORD", "VALUES")
        rows = []
        while True:
            self.expect("PUNCT", "(")
            row = [self.expression()]
            while self.accept("PUNCT", ","):
                row.append(self.expression())
            self.expect("PUNCT", ")")
            rows.append(row)
            if not self.accept("PUNCT", ","):
                break
        return Insert(table, columns, rows)

    def update(self) -> Update:
        self.expect("KEYWORD", "UPDATE")
        table = self.expect("IDENT").value
        self.expect("KEYWORD", "SET")
        assignments = []
        while True:
            name = self.expect("IDENT").value
            self.expect("OP", "=")
            assignments.append((name, self.expression()))
            if not self.accept("PUNCT", ","):
                break
        where = self.expression() if self.accept("KEYWORD", "WHERE") else None
        return Update(table, assignments, where)

    def delete(self) -> Delete:
        self.expect("KEYWORD", "DELETE")
        self.expect("KEYWORD", "FROM")
        table = self.expect("IDENT").value
        where = self.expression() if self.accept("KEYWORD", "WHERE") else None
        return Delete(table, where)

    def create(self) -> Any:
        self.expect("KEYWORD", "CREATE")
        if self.accept("KEYWORD", "INDEX"):
            name = self.expect("IDENT").value
            self.expect("KEYWORD", "ON")
            table = self.expect("IDENT").value
            self.expect("PUNCT", "(")
            column = self.expect("IDENT").value
            self.expect("PUNCT", ")")
            return CreateIndex(name, table, column)

        self.expect("KEYWORD", "TABLE")
        table = self.expect("IDENT").value
        self.expect("PUNCT", "(")
        columns: List[Tuple[str, str]] = []
        primary_key = None
        while True:
            name = self.expect("IDENT").value
            type_token = self.expect("KEYWORD")
            columns.append((name, type_token.value))
            if self.accept("KEYWORD", "PRIMARY"):
                self.expect("KEYWORD", "KEY")
                primary_key = name
            if not self.accept("PUNCT", ","):
                break
        self.expect("PUNCT", ")")
        return CreateTable(table, columns, primary_key)

    # -- expressions --------------------------------------------------------

    def expression(self, min_precedence: int = 0) -> Any:
        """Precedence climbing.

        Parse one operand, then keep absorbing operators whose precedence is at
        least `min_precedence`, recursing with a HIGHER minimum for
        left-associative operators and the SAME one for right-associative. Two
        loops and a table replace one function per precedence level, and the
        grammar becomes something you can read.
        """
        left = self.unary()
        while True:
            token = self.current
            key = token.value if token.kind in ("OP", "KEYWORD") else None
            if key not in PRECEDENCE:
                break
            precedence, right_associative = PRECEDENCE[key]
            if precedence < min_precedence:
                break
            self.position += 1

            if key == "IS":
                negated = self.accept("KEYWORD", "NOT") is not None
                self.expect("KEYWORD", "NULL")
                left = UnaryOp("IS NOT NULL" if negated else "IS NULL", left)
                continue
            if key == "IN":
                self.expect("PUNCT", "(")
                items = [self.expression()]
                while self.accept("PUNCT", ","):
                    items.append(self.expression())
                self.expect("PUNCT", ")")
                left = BinOp("IN", left, items)
                continue

            next_minimum = precedence if right_associative else precedence + 1
            left = BinOp(key, left, self.expression(next_minimum))
        return left

    def unary(self) -> Any:
        if self.accept("KEYWORD", "NOT"):
            return UnaryOp("NOT", self.expression(3))
        if self.accept("OP", "-"):
            return UnaryOp("-", self.unary())
        return self.primary()

    def primary(self) -> Any:
        if self.accept("PUNCT", "("):
            inner = self.expression()
            self.expect("PUNCT", ")")
            return inner
        token = self.current
        if token.kind == "NUMBER" or token.kind == "STRING":
            self.position += 1
            return Literal(token.value)
        if self.accept("KEYWORD", "NULL"):
            return Literal(None)
        if token.kind == "KEYWORD" and token.value in ("COUNT", "SUM", "AVG",
                                                       "MIN", "MAX"):
            self.position += 1
            self.expect("PUNCT", "(")
            argument = Star() if self.accept("OP", "*") else self.expression()
            self.expect("PUNCT", ")")
            return Aggregate(token.value, argument)
        if token.kind == "IDENT":
            return self.column_ref()
        raise SQLError(f"expected a value at column {token.column}, "
                       f"found {token.value!r}")


def parse(text: str) -> Any:
    return Parser(text).parse()


def _demo() -> None:
    print("=" * 74)
    print("SQL — text to a tree that says WHAT, never HOW")
    print("=" * 74)

    print("\n1. The tokeniser trap")
    print("-" * 74)
    for word in ("SELECT", "SELECTED", "select", "counted", "COUNT"):
        token = tokenize(word)[0]
        print(f"  {word:<10} -> {token}")
    print("  SELECTED is ONE identifier. Match the longest word first, then ask")
    print("  whether the whole word is a keyword. Classify first and `SELECTED`")
    print("  lexes as SELECT + ED, and the parse error points at the wrong")
    print("  place — the same alternation-order bug as `//` after `/` in a lexer.")

    print("\n2. Precedence, from a table rather than a function per level")
    print("-" * 74)
    for text in ("1 + 2 * 3",
                 "(1 + 2) * 3",
                 "a = 1 AND b = 2 OR c = 3",
                 "NOT a = 1 AND b = 2",
                 "price * quantity > 100 AND status = 'open'"):
        print(f"  {text:<45} {Parser(text).expression()!r}")
    print("  `a = 1 AND b = 2 OR c = 3` groups as ((a=1 AND b=2) OR c=3) —")
    print("  AND binds tighter than OR, which is the one people get wrong when")
    print("  they write it and the reason to always parenthesise.")

    print("\n3. Statements")
    print("-" * 74)
    statements = [
        "CREATE TABLE users (id INT PRIMARY KEY, name TEXT, age INT)",
        "CREATE INDEX idx_age ON users (age)",
        "INSERT INTO users (id, name, age) VALUES (1, 'alice', 30), (2, 'bob', 25)",
        "SELECT name, age FROM users WHERE age > 25 ORDER BY age DESC LIMIT 10",
        "SELECT COUNT(*), MAX(age) FROM users GROUP BY city HAVING COUNT(*) > 2",
        "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
        "UPDATE users SET age = age + 1 WHERE name = 'alice'",
        "DELETE FROM users WHERE age IS NULL",
        "SELECT * FROM users WHERE id IN (1, 2, 3)",
    ]
    for text in statements:
        node = parse(text)
        print(f"  {text[:58]:<58} -> {type(node).__name__}")

    parsed = parse("SELECT name FROM users WHERE age > 25 AND city = 'lisbon'")
    print(f"\n  WHERE tree: {parsed.where!r}")
    print("  Nothing in that tree mentions an index, a scan, or an order of")
    print("  evaluation. It says WHAT was asked. planner.py is free to choose")
    print("  HOW precisely because the parser refused to.")

    print("\n4. Errors that point at the problem")
    print("-" * 74)
    for text in ("SELECT name users",
                 "SELECT FROM users",
                 "INSERT INTO users VALUES (1, 'a'",
                 "SELECT * FROM users WHERE age >",
                 "SELECT * FROM users; DROP TABLE users"):
        try:
            parse(text)
            print(f"  {text:<42} -> parsed (unexpectedly)")
        except SQLError as error:
            print(f"  {text:<42} -> {error}")
    print("  Each message names the column and what was expected. That is the")
    print("  entire argument for writing the parser by hand: a generated one")
    print("  reports a state number, and a user cannot act on a state number.")

    print("\n" + "=" * 74)
    print("Next: planner.py decides how to execute one of these trees.")
    print("=" * 74)


if __name__ == "__main__":
    _demo()
