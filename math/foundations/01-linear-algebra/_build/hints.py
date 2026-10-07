"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that holds part of the algorithm is listed, so make_templates stubs it
and replaces its body with `raise NotImplementedError`. `_scale` is left implemented:
it is one line of boilerplate, not the lesson.
"""
HINTS = {
 "elimination.py": {
  "_pivot_row": "Return the index in [r, len(U)) whose column-c entry has the largest magnitude. Picking the largest is what makes elimination stable.",
  "_forward": "Walk the columns. For each: get the pivot row with _pivot_row, swap it into row r and count the swap, record c as a pivot, then for every row below subtract (row[c]/pivot) times the pivot row. Skip a column whose best entry is ~0.",
  "row_echelon": "Call _forward and return its first two values: the echelon matrix and the list of pivot columns.",
  "_reduce_aug": "Like _forward, but pivot only on the first ncols columns and eliminate ABOVE as well as below: normalize the pivot row, then subtract f·pivot_row from every OTHER row, carrying the trailing columns (b, or the identity) along.",
  "rank": "The number of pivots _reduce_aug finds in A alone.",
  "null_space": "Reduce A, then for each free column c (not a pivot) build a vector with 1 at c and, in each pivot row k, -R[k][c] at that row's pivot column. There are n - rank of them and each satisfies A·n = 0.",
  "solve": "Augment A with b, reduce. If any row is all-zero in the A part but non-zero in b, raise InconsistentSystem. If there are fewer pivots than unknowns, raise NotUnique. Otherwise read the unknowns off the b column.",
  "general_solution": "Do the same consistency check as solve, but return the particular solution (free variables set to 0) together with null_space(A), so particular + any combination of the basis is a solution.",
  "inverse": "Augment A with the identity and reduce on the n A-columns. Fewer than n pivots means SingularMatrix; otherwise the right half of the reduced matrix is the inverse.",
  "determinant": "Forward-eliminate. A rank below n means determinant 0. Otherwise multiply the pivot entries together and negate the product when the number of row swaps is odd.",
 },
}
