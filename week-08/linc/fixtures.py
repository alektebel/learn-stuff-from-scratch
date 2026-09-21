"""
Three problems. Provided. Do not edit to paper over a failing check.

Each problem is a natural-language (premises, conclusion, label) plus
the gold FOL the parser is supposed to emit. Labels follow LINC /
ProofWriter: True, False, Uncertain.

There is no LLM in this directory. The gold parser looks these up.
The fault injector *corrupts* the gold FOL. The prover never sees
English.

Olausson, Gu, Lipkin, Zhang, Solar-Lezama, Tenenbaum, Levy.
"LINC: A Neurosymbolic Approach for Logical Reasoning by Combining
Language Models with First-Order Logic Provers." EMNLP 2023.
arXiv:2310.15164

Pan, Albalak, Wang, Wang. "Logic-LM: Empowering Large Language
Models with Symbolic Solvers for Faithful Deductive Reasoning."
EMNLP 2023 Findings.

Lyu, Chau, Gupta, Hovy. "Faithful Chain-of-Thought Reasoning."
AACL 2023.  (the chain is a program that is executed)
"""

from typing import Dict, List, Tuple

# FOL is the tagged-tuple language in fol.py:
#   ("pred", name, (terms,))
#   ("not", φ)  ("and", φ, ψ)  ("or", φ, ψ)  ("implies", φ, ψ)
#   ("forall", var, φ)  ("exists", var, φ)
#   term: ("const", name) | ("var", name)

def C(name: str):
    return ("const", name)


def V(name: str):
    return ("var", name)


def P(name: str, *args):
    return ("pred", name, args)


def Forall(var: str, body):
    return ("forall", var, body)


def Imp(a, b):
    return ("implies", a, b)


def Not(a):
    return ("not", a)


# --- problem 1: entailed ----------------------------------------------
# Fiona is a cat. All cats are mammals. All mammals drink water.
# Therefore Fiona drinks water.     True

P1_PREMISES_NL = [
    "Fiona is a cat.",
    "All cats are mammals.",
    "All mammals drink water.",
]
P1_CONCLUSION_NL = "Fiona drinks water."
P1_LABEL = "True"
P1_DOMAIN = ["fiona"]
P1_PREMISES_FOL = [
    P("cat", C("fiona")),
    Forall("x", Imp(P("cat", V("x")), P("mammal", V("x")))),
    Forall("x", Imp(P("mammal", V("x")), P("drinks", V("x")))),
]
P1_CONCLUSION_FOL = P("drinks", C("fiona"))


# --- problem 2: refuted -----------------------------------------------
# Tweety is a penguin. All penguins are birds. No penguin flies.
# Therefore Tweety flies.           False
# (Open-world "birds fly unless penguins" does *not* prove ¬flies.
#  False has to be derived, not assumed. This is the encoding.)

P2_PREMISES_NL = [
    "Tweety is a penguin.",
    "All penguins are birds.",
    "No penguin flies.",
]
P2_CONCLUSION_NL = "Tweety flies."
P2_LABEL = "False"
P2_DOMAIN = ["tweety"]
P2_PREMISES_FOL = [
    P("penguin", C("tweety")),
    Forall("x", Imp(P("penguin", V("x")), P("bird", V("x")))),
    Forall("x", Imp(P("penguin", V("x")), Not(P("flies", V("x"))))),
]
P2_CONCLUSION_FOL = P("flies", C("tweety"))


# --- problem 3: uncertain ---------------------------------------------
# Opus is a sparrow. All sparrows are birds.
# Therefore Opus flies.             Uncertain (nothing says birds fly)

P3_PREMISES_NL = [
    "Opus is a sparrow.",
    "All sparrows are birds.",
]
P3_CONCLUSION_NL = "Opus flies."
P3_LABEL = "Uncertain"
P3_DOMAIN = ["opus"]
P3_PREMISES_FOL = [
    P("sparrow", C("opus")),
    Forall("x", Imp(P("sparrow", V("x")), P("bird", V("x")))),
]
P3_CONCLUSION_FOL = P("flies", C("opus"))


def problems() -> List[Dict]:
    return [
        {
            "id": "p1",
            "premises_nl": P1_PREMISES_NL,
            "conclusion_nl": P1_CONCLUSION_NL,
            "premises_fol": P1_PREMISES_FOL,
            "conclusion_fol": P1_CONCLUSION_FOL,
            "label": P1_LABEL,
            "domain": P1_DOMAIN,
        },
        {
            "id": "p2",
            "premises_nl": P2_PREMISES_NL,
            "conclusion_nl": P2_CONCLUSION_NL,
            "premises_fol": P2_PREMISES_FOL,
            "conclusion_fol": P2_CONCLUSION_FOL,
            "label": P2_LABEL,
            "domain": P2_DOMAIN,
        },
        {
            "id": "p3",
            "premises_nl": P3_PREMISES_NL,
            "conclusion_nl": P3_CONCLUSION_NL,
            "premises_fol": P3_PREMISES_FOL,
            "conclusion_fol": P3_CONCLUSION_FOL,
            "label": P3_LABEL,
            "domain": P3_DOMAIN,
        },
    ]


def by_id(name: str) -> Dict:
    for p in problems():
        if p["id"] == name:
            return p
    raise KeyError(name)
