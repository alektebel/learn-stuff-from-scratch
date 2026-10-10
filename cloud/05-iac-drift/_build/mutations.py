"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    # (description, file, exact text in solutions/<file>, replacement, check step)

    # spec.py -------------------------------------------------------------
    ("resource type is not validated", "spec.py",
     '    if not isinstance(resource_type, str) or not resource_type:\n'
     '        raise SpecError(f"resource {name!r} needs a non-empty string \'type\'")',
     '    if False:\n'
     '        raise SpecError(f"resource {name!r} needs a non-empty string \'type\'")',
     "1"),
    ("canonical ignores property key order", "spec.py",
     '    return json.dumps(properties, sort_keys=True, separators=(",", ":"), default=str)',
     '    return json.dumps(properties, separators=(",", ":"), default=str)',
     "2"),
    ("cycle detection never sees the back-edge", "spec.py",
     "            if color[dep] == GREY:",
     "            if False:",
     "3"),

    # planner.py ----------------------------------------------------------
    ("a changed attribute is not an update", "planner.py",
     "        elif not same_config(spec[name], state[name]):",
     "        elif False:",
     "5"),
    ("a removed resource is not deleted", "planner.py",
     '        elif name in state and name not in spec:\n'
     '            actions.append(Action("delete", name, state[name].type))',
     '        elif name in state and name not in spec:\n'
     '            pass',
     "5"),
    ("dependencies do not order the creates", "planner.py",
     '        if action.action in ("create", "update"):',
     "        if False:",
     "6"),
    ("dependents are not deleted before their dependencies", "planner.py",
     '        if action.action == "delete":',
     "        if False:",
     "6"),
    ("a stateful rename is destroy-before-create", "planner.py",
     "        if stateful:\n"
     '            add(("create", new), ("delete", old))',
     "        if False:\n"
     '            add(("create", new), ("delete", old))',
     "7"),
    ("the plan ignores a dependency cycle", "planner.py",
     "    for resources in (spec, state):\n"
     "        cycle = find_cycle(resources)\n"
     "        if cycle:\n"
     '            raise DependencyCycle("dependency cycle: " + " -> ".join(cycle))',
     "    pass",
     "8"),
]
