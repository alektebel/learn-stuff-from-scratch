"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    ("Bool compared as a string",
     "conditions.py",
     '        return any(bool(actual) == (option.lower() == "true") for option in strings)',
     '        return any(actual == option for option in strings)',
     "1"),
    ("unknown operator silently passes",
     "conditions.py",
     '    raise ValueError(f"unsupported condition operator {operator!r}")',
     '    return True',
     "1"),
    ("a missing key slips through a negated operator",
     "conditions.py",
     "            if key not in context:\n"
     "                # Fail closed: a key the policy names but the request does not carry\n"
     "                # cannot satisfy the condition.\n"
     "                return False\n"
     "            if not condition_holds(operator, context[key], options):\n"
     "                return False",
     "            if not condition_holds(operator, context.get(key), options):\n"
     "                return False",
     "2"),
    ("single Statement object is not wrapped",
     "policy.py",
     "    if isinstance(raw, dict):\n"
     "        raw = [raw]",
     "    if isinstance(raw, dict):\n"
     "        raw = list(raw)",
     "3"),
    ("action matching is case-sensitive",
     "policy.py",
     "    return fnmatch.fnmatchcase(action.lower(), pattern.lower())",
     "    return fnmatch.fnmatchcase(action, pattern)",
     "4"),
    ("resource matching ignores wildcards",
     "policy.py",
     "    return fnmatch.fnmatchcase(resource, pattern)",
     "    return resource == pattern",
     "5"),
    ("explicit deny does not win",
     "policy.py",
     "            if statement.effect == DENY:",
     "            if False:",
     "7"),
    ("implicit deny becomes allow",
     "policy.py",
     '    return Decision(False, "implicit Deny — no statement allows this")',
     '    return Decision(True, "implicit Allow — nobody denied it")',
     "9"),
]
