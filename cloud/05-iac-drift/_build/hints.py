"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "spec.py": {
  "canonical": "Serialise the properties with json.dumps(..., sort_keys=True, separators=(',', ':')) so two dicts written with different key order produce the same string. Without sort_keys, an unchanged resource looks like drift.",
  "same_config": "True when the two resources have the same `type` AND the same `canonical(properties)`. Ignore the logical name, depends_on and lifecycle: those are planning metadata, not configuration.",
  "parse_resource": "Validate the body: a string `type`, a mapping `properties` (default {}), a list/tuple `depends_on` of non-empty strings, and a `lifecycle` of 'stateful'/'stateless'. Raise SpecError on anything else; return a Resource with depends_on as a tuple and stateful = (lifecycle == 'stateful').",
  "parse_document": "Require a mapping with a `resources` mapping. Parse each entry with parse_resource, then reject any depends_on naming a resource that is not declared (SpecError). Iterate sorted() so the result order is deterministic.",
  "dependents": "Invert the depends_on edges: for every resource `a` and each `d` in a.depends_on, add `a` to graph[d]. Start every name at an empty set, and skip edges to names not in the document.",
  "find_cycle": "Depth-first search with three colours (white/grey/black) and an explicit stack. Meeting a GREY dependency closes a loop: return stack[index(dep):] + [dep]. Visit names and dependencies in sorted order so the reported cycle is deterministic. Return None when the walk finishes.",
 },
 "planner.py": {
  "compute_drift": "Walk sorted(spec | state). Only in spec -> Action('create', ...). Only in state -> Action('delete', ...). In both and not same_config -> Action('update', ...) with `changes` = the sorted property keys whose values differ. Equal config -> no action at all. Finally annotate each create whose name is the new side of a rename_pair with replacement_of.",
  "rename_pairs": "Pair a removed name with an added name of identical configuration (same_config), greedily in sorted order and using each removed name once. Return (new, old, stateful) where stateful = spec[new].stateful or state[old].stateful.",
  "order_actions": "Build prereq edges: a create/update follows the create/update of each of its spec dependencies; a delete precedes the deletes of the resources that depend on it (use dependents(state)); a stateful rename pins create(new) before delete(old). Then a recursive DFS visits roots sorted by (delete, update, create) priority, following prereqs first and marking nodes in-progress; meeting an in-progress node raises DependencyCycle naming the loop. Return the actions in visit order.",
  "plan": "parse_document(spec) and parse_document(state). For BOTH graphs call find_cycle and raise DependencyCycle naming the loop if there is one (a cyclic template cannot be ordered even when it produces no actions). Then compute_drift and order_actions.",
 },
}
