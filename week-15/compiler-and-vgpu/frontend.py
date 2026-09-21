"""
Step 4 — Lexer and parser. Complete Solution.

Source text -> tokens -> abstract syntax tree.

DESIGN DECISION — hand-written recursive descent, or a parser generator?
  A generator (yacc, ANTLR) takes a grammar and produces a parser. Recursive
  descent is one function per grammar rule, written by hand.
  CHOSEN: recursive descent. The precedence climbing you write in
  parse_binary IS the operator-precedence rule, visible and steppable. A
  generated table gives you a working parser and no intuition, and when it
  reports a conflict you are debugging the generator, not your grammar.

DESIGN DECISION — how to encode operator precedence?
  Classic textbook approach: one grammar rule per level (expr -> term -> factor).
  It works, but adding a level means adding a function.
  CHOSEN: precedence climbing — one function, a table of binding powers. Adding
  an operator is one table entry.

The language, deliberately small:
    x = expr;                    assignment
    if (expr) { ... } else {...} conditional
    while (expr) { ... }         loop
    mem[expr] = expr;            store to global memory
    mem[expr]                    load
    tid                          the lane id (GPU) / 0 (CPU)
"""

import re
from typing import List, NamedTuple, Optional, Union

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

# ORDER MATTERS. Python's alternation takes the FIRST branch that matches, so
# COMMENT must come before OP — otherwise "//" is lexed as two '/' operators and
# the comment body becomes a stream of identifiers. Longer alternatives first is
# the same rule that puts "<=" before "<" inside the OP pattern.
TOKEN_SPEC = [
    ("COMMENT", r"//[^\n]*"),
    ("NUMBER", r"\d+"),
    ("NAME", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"<=|>=|==|!=|[-+*/%<>=]"),
    ("PUNCT", r"[(){};\[\]]"),
    ("SKIP", r"[ \t\n]+"),
]
_MASTER = re.compile("|".join(f"(?P<{name}>{pattern})"
                              for name, pattern in TOKEN_SPEC))

KEYWORDS = {"if", "else", "while", "tid", "mem"}


class Token(NamedTuple):
    kind: str
    text: str
    position: int

    def __repr__(self) -> str:
        return f"{self.kind}({self.text})"


class ParseError(Exception):
    pass


def tokenize(source: str) -> List[Token]:
    """Split source into tokens, dropping whitespace and comments.

    TODO:
    1. Walk the source with _MASTER.match(source, position).
    2. No match -> ParseError naming the offending character AND its position.
    3. Skip SKIP and COMMENT.
    4. A NAME whose text is in KEYWORDS becomes its own kind (IF, WHILE, TID,
       MEM). Doing this in the lexer keeps the parser from special-casing
       identifiers everywhere.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# AST — provided, so your parser and the checker agree on shapes
# ---------------------------------------------------------------------------


class Num(NamedTuple):
    value: int


class Var(NamedTuple):
    name: str


class Tid(NamedTuple):
    pass


class Load(NamedTuple):
    address: "Expr"


class Binary(NamedTuple):
    op: str
    left: "Expr"
    right: "Expr"


Expr = Union[Num, Var, Tid, Load, Binary]


class Assign(NamedTuple):
    name: str
    value: Expr


class Store(NamedTuple):
    address: Expr
    value: Expr


class If(NamedTuple):
    condition: Expr
    then_body: List["Stmt"]
    else_body: List["Stmt"]


class While(NamedTuple):
    condition: Expr
    body: List["Stmt"]


Stmt = Union[Assign, Store, If, While]

# Binding powers. Higher binds tighter. Adding an operator is one entry.
PRECEDENCE = {
    "<": 1, ">": 1, "<=": 1, ">=": 1, "==": 1, "!=": 1,
    "+": 2, "-": 2,
    "*": 3, "/": 3, "%": 3,
}


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.index = 0

    def peek(self) -> Optional[Token]:
        """TODO: the current token, or None at the end."""
        raise NotImplementedError

    def next(self) -> Token:
        """TODO: consume and return; ParseError at end of input."""
        raise NotImplementedError

    def accept(self, text: str) -> bool:
        """TODO: consume the token if its text matches; return whether it did."""
        raise NotImplementedError

    def expect(self, text: str) -> Token:
        """TODO: consume it or raise ParseError saying what was expected and
        what was found. "expected ';', got end of input" is a usable message."""
        raise NotImplementedError

    def parse_expr(self, min_power: int = 0) -> Expr:
        """Precedence climbing.

        TODO:
        1. left = self.parse_primary()
        2. Loop: peek. Stop unless it is an OP with a PRECEDENCE entry whose
           power is >= min_power.
        3. Consume it, parse the right side with parse_expr(power + 1), and
           wrap: left = Binary(op, left, right).

        That +1 is what makes operators LEFT-associative: it stops the right
        side from absorbing another operator at the same level, so 10 - 3 - 2
        parses as (10 - 3) - 2 = 5, not 10 - (3 - 2) = 9. Test that case.
        """
        raise NotImplementedError

    def parse_primary(self) -> Expr:
        """TODO: NUMBER -> Num; TID -> Tid; MEM -> '[' expr ']' -> Load;
        NAME -> Var; '(' expr ')' -> the inner expression; unary '-' ->
        Binary("-", Num(0), operand). Anything else is a ParseError naming the
        token and its position."""
        raise NotImplementedError

    def parse_block(self) -> List[Stmt]:
        """TODO: '{' then statements until '}'."""
        raise NotImplementedError

    def parse_stmt(self) -> Stmt:
        """TODO: dispatch on the leading token.
             IF     -> '(' expr ')' block, optional 'else' block  -> If
             WHILE  -> '(' expr ')' block                          -> While
             MEM    -> '[' expr ']' '=' expr ';'                   -> Store
             NAME   -> '=' expr ';'                                -> Assign
        Anything else: ParseError saying a statement cannot start there."""
        raise NotImplementedError

    def parse_program(self) -> List[Stmt]:
        """TODO: statements until the tokens run out."""
        raise NotImplementedError


def parse(source: str) -> List[Stmt]:
    return Parser(tokenize(source)).parse_program()


def render(node, indent: int = 0) -> str:
    """TODO: an indented dump of the AST.

    Write this one properly and early. Almost every parser bug is obvious the
    moment you can see the tree, and invisible otherwise.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, verify:

    1. `x = 1 + 2 * 3;` puts the '*' DEEPER in the tree than the '+'. The tree
       encodes precedence, so codegen never has to think about it.
    2. `x = 10 - 3 - 2;` nests to the LEFT. If it nests right, you passed
       `power` instead of `power + 1`.
    3. A whole program with if/else inside a while parses.
    4. Errors name a position: missing expression, missing semicolon, missing
       parenthesis, illegal character.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
