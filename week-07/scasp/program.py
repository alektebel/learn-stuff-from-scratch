"""
Four programs, already parsed. Provided. Do not edit to paper over a
failing check.

A clause is (head, body) where head is an atom and body is a list of
literals. An atom is (predicate, args). An arg is:
    ("const", name)  |  ("var", name)  |  ("fun", name, (args...))
A literal is ("pos", atom) or ("neg", atom).

s(CASP) papers:
  Arias, Carro, Salazar, Marple, Gupta.
  "Constraint Answer Set Programming without Grounding." TPLP 2018.
  Marple, Bansal, Min, Gupta. "Goal-directed execution of answer set
  programs." PPDP 2012. (s(ASP), the parent)
"""

from typing import List, Tuple

Arg = tuple
Atom = Tuple[str, Tuple[Arg, ...]]
Literal = Tuple[str, Atom]                 # 'pos' | 'neg'
Clause = Tuple[Atom, List[Literal]]


def const(name: str) -> Arg:
    return ("const", name)


def var(name: str) -> Arg:
    return ("var", name)


def fun(name: str, *args: Arg) -> Arg:
    return ("fun", name, args)


def atom(pred: str, *args: Arg) -> Atom:
    return (pred, args)


def pos(pred: str, *args: Arg) -> Literal:
    return ("pos", atom(pred, *args))


def neg(pred: str, *args: Arg) -> Literal:
    return ("neg", atom(pred, *args))


def fact(pred: str, *args: Arg) -> Clause:
    return (atom(pred, *args), [])


def rule(head: Atom, *body: Literal) -> Clause:
    return (head, list(body))


# p :- q.  q :- p.   even loop, coinductive success.
EVEN_LOOP: List[Clause] = [
    rule(atom("p"), pos("q")),
    rule(atom("q"), pos("p")),
]


# p :- not p.   odd loop through negation — not an answer set.
ODD_LOOP: List[Clause] = [
    rule(atom("p"), neg("p")),
]


# member/2, Prolog lists encoded as fun('.', Head, Tail) and const('[]').
def cons(head: Arg, tail: Arg) -> Arg:
    return fun(".", head, tail)


NIL = const("[]")


def list_of(*names: str) -> Arg:
    acc: Arg = NIL
    for name in reversed(names):
        acc = cons(const(name), acc)
    return acc


MEMBER: List[Clause] = [
    rule(atom("member", var("X"), cons(var("X"), var("_"))),),
    rule(atom("member", var("X"), cons(var("_"), var("T"))),
         pos("member", var("X"), var("T"))),
]


# Default negation. Tweety does not fly; Opus does.
FLIES: List[Clause] = [
    rule(atom("bird", var("X")), pos("penguin", var("X"))),
    rule(atom("bird", var("X")), pos("sparrow", var("X"))),
    rule(atom("flies", var("X")),
         pos("bird", var("X")),
         neg("penguin", var("X"))),
    fact("penguin", const("tweety")),
    fact("sparrow", const("opus")),
]


# p(a).     so not p(b) should succeed, not p(a) should fail.
UNIT: List[Clause] = [
    fact("p", const("a")),
]
