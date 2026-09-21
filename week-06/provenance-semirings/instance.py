"""
The running instance. Provided. Do not edit to paper over a failing check.

Two relations, four tuples, one query that has *two* derivations of the
same result. That second derivation is why a set of source ids is not
enough: lineage({Ada, Bar}) is {a,b,c,d} either way, but how-provenance
is ac + bd, bag is 2, min-cost depends on which path is cheaper.

    Likes(person, food)     Serves(cafe, food)
    a: Ada, pie             c: Bar, pie
    b: Ada, tea             d: Bar, tea

    Q = π_{person, cafe} (Likes ⋈_{food} Serves)

    Q(Ada, Bar)  =  a⊗c  ⊕  b⊗d

Green, Karvounarakis, Tannen. "Provenance Semirings." PODS 2007.
"""

from typing import Dict, List, Tuple

Row = Dict[str, str]
Annotated = Tuple[Row, str]          # (tuple, variable name)

LIKES: List[Annotated] = [
    ({"person": "Ada", "food": "pie"}, "a"),
    ({"person": "Ada", "food": "tea"}, "b"),
]

SERVES: List[Annotated] = [
    ({"cafe": "Bar", "food": "pie"}, "c"),
    ({"cafe": "Bar", "food": "tea"}, "d"),
]

RESULT_KEY = {"person": "Ada", "cafe": "Bar"}

# Concrete valuations for the specialised semirings. Chosen so the two
# paths disagree: if your homomorphism collapses them you will fail.
TRUST = {"a": 0.9, "b": 0.5, "c": 0.8, "d": 0.4}     # path ac is 0.72, bd is 0.20
COST = {"a": 3, "b": 1, "c": 4, "d": 10}              # path ac is 7, bd is 11
SECURITY = {"a": 2, "b": 5, "c": 3, "d": 1}           # path ac is max=3, bd is max=5

# A directed graph for the Datalog checks. 1→3 both directly and via 2.
# The 2-cycle 4 ⇄ 5 is the limit case: How-provenance does not terminate.
EDGES = [
    ((1, 2), "e12"),
    ((2, 3), "e23"),
    ((1, 3), "e13"),
    ((4, 5), "e45"),
    ((5, 4), "e54"),
]
