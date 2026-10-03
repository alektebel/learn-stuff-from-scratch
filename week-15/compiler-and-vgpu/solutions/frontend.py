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
    """Split source into tokens, dropping whitespace and comments."""
    tokens: List[Token] = []
    position = 0
    while position < len(source):
        match = _MASTER.match(source, position)
        if match is None:
            raise ParseError(f"unexpected character {source[position]!r} at "
                             f"position {position}")
        kind = match.lastgroup
        text = match.group()
        position = match.end()
        if kind in ("SKIP", "COMMENT"):
            continue
        if kind == "NAME" and text in KEYWORDS:
            kind = text.upper()
        tokens.append(Token(kind, text, match.start()))
    return tokens


# ---------------------------------------------------------------------------
# AST
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

    # -- helpers ------------------------------------------------------------

    def peek(self) -> Optional[Token]:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def next(self) -> Token:
        token = self.peek()
        if token is None:
            raise ParseError("unexpected end of input")
        self.index += 1
        return token

    def accept(self, text: str) -> bool:
        token = self.peek()
        if token is not None and token.text == text:
            self.index += 1
            return True
        return False

    def expect(self, text: str) -> Token:
        token = self.peek()
        if token is None or token.text != text:
            got = "end of input" if token is None else repr(token.text)
            raise ParseError(f"expected {text!r}, got {got}")
        return self.next()

    # -- expressions --------------------------------------------------------

    def parse_expr(self, min_power: int = 0) -> Expr:
        """Precedence climbing.

        Parse a primary, then keep absorbing operators whose binding power is
        at least min_power, recursing with power+1 for the right operand. That
        +1 is what makes the operators left-associative: a - b - c parses as
        (a - b) - c, not a - (b - c).
        """
        left = self.parse_primary()
        while True:
            token = self.peek()
            if token is None or token.kind != "OP":
                break
            power = PRECEDENCE.get(token.text)
            if power is None or power < min_power:
                break
            self.next()
            right = self.parse_expr(power + 1)
            left = Binary(token.text, left, right)
        return left

    def parse_primary(self) -> Expr:
        token = self.next()
        if token.kind == "NUMBER":
            return Num(int(token.text))
        if token.kind == "TID":
            return Tid()
        if token.kind == "MEM":
            self.expect("[")
            address = self.parse_expr()
            self.expect("]")
            return Load(address)
        if token.kind == "NAME":
            return Var(token.text)
        if token.text == "(":
            inner = self.parse_expr()
            self.expect(")")
            return inner
        if token.text == "-":                    # unary minus
            return Binary("-", Num(0), self.parse_primary())
        raise ParseError(f"unexpected {token.text!r} at position {token.position}")

    # -- statements ---------------------------------------------------------

    def parse_block(self) -> List[Stmt]:
        self.expect("{")
        body: List[Stmt] = []
        while not self.accept("}"):
            body.append(self.parse_stmt())
        return body

    def parse_stmt(self) -> Stmt:
        token = self.peek()
        if token is None:
            raise ParseError("unexpected end of input")

        if token.kind == "IF":
            self.next()
            self.expect("(")
            condition = self.parse_expr()
            self.expect(")")
            then_body = self.parse_block()
            else_body = self.parse_block() if self.accept("else") else []
            return If(condition, then_body, else_body)

        if token.kind == "WHILE":
            self.next()
            self.expect("(")
            condition = self.parse_expr()
            self.expect(")")
            return While(condition, self.parse_block())

        if token.kind == "MEM":
            self.next()
            self.expect("[")
            address = self.parse_expr()
            self.expect("]")
            self.expect("=")
            value = self.parse_expr()
            self.expect(";")
            return Store(address, value)

        if token.kind == "NAME":
            name = self.next().text
            self.expect("=")
            value = self.parse_expr()
            self.expect(";")
            return Assign(name, value)

        raise ParseError(f"cannot start a statement with {token.text!r}")

    def parse_program(self) -> List[Stmt]:
        body: List[Stmt] = []
        while self.peek() is not None:
            body.append(self.parse_stmt())
        return body


def parse(source: str) -> List[Stmt]:
    return Parser(tokenize(source)).parse_program()


def render(node, indent: int = 0) -> str:
    """Pretty-print an AST. Worth writing — most parser bugs are obvious the
    moment you can see the tree."""
    pad = "  " * indent
    if isinstance(node, list):
        return "\n".join(render(item, indent) for item in node)
    if isinstance(node, Num):
        return f"{pad}Num {node.value}"
    if isinstance(node, Var):
        return f"{pad}Var {node.name}"
    if isinstance(node, Tid):
        return f"{pad}Tid"
    if isinstance(node, Load):
        return f"{pad}Load\n{render(node.address, indent + 1)}"
    if isinstance(node, Binary):
        return (f"{pad}Binary {node.op}\n{render(node.left, indent + 1)}\n"
                f"{render(node.right, indent + 1)}")
    if isinstance(node, Assign):
        return f"{pad}Assign {node.name}\n{render(node.value, indent + 1)}"
    if isinstance(node, Store):
        return (f"{pad}Store\n{render(node.address, indent + 1)}\n"
                f"{render(node.value, indent + 1)}")
    if isinstance(node, If):
        text = f"{pad}If\n{render(node.condition, indent + 1)}\n{pad}then:\n"
        text += render(node.then_body, indent + 1)
        if node.else_body:
            text += f"\n{pad}else:\n" + render(node.else_body, indent + 1)
        return text
    if isinstance(node, While):
        return (f"{pad}While\n{render(node.condition, indent + 1)}\n{pad}do:\n"
                + render(node.body, indent + 1))
    return f"{pad}?{node}"


def _demo() -> None:
    print("=== Tokens ===")
    for token in tokenize("x = a + 2 * b;")[:10]:
        print(f"  {token}")

    print("\n=== Precedence: 1 + 2 * 3 ===")
    print(render(parse("x = 1 + 2 * 3;")))
    print("  '*' binds tighter, so it is the deeper node — the tree encodes the")
    print("  precedence, and code generation just walks it.")

    print("\n=== Left associativity: 10 - 3 - 2 ===")
    print(render(parse("x = 10 - 3 - 2;")))
    print("  (10 - 3) - 2 = 5, not 10 - (3 - 2) = 9. That is the power+1.")

    print("\n=== A whole program ===")
    source = """
    i = 0;
    total = 0;
    while (i < 4) {
      if (mem[i] > 10) { total = total + mem[i]; } else { total = total + 1; }
      i = i + 1;
    }
    mem[100] = total;
    """
    print(render(parse(source)))

    print("\n=== Errors ===")
    for bad, why in [("x = ;", "missing expression"),
                     ("x = 1", "missing semicolon"),
                     ("if x { }", "missing parenthesis"),
                     ("x = 1 $ 2;", "bad character")]:
        try:
            parse(bad)
            print(f"  {why:<22} NO ERROR — that is a bug")
        except ParseError as exc:
            print(f"  {why:<22} {exc}")


if __name__ == "__main__":
    _demo()
