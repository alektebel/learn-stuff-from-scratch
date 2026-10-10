"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
    "conditions.py": {
        "condition_holds": "Dispatch on the operator name over one actual value and a list: positive operators match when ANY listed value matches, negated operators when NONE do. An unknown operator raises ValueError, never returns True.",
        "evaluate_condition": "Every key of every block must hold (AND across keys); the operator ORs within one key's value list. A key missing from the context fails closed — return False, including for negated operators, so test presence before comparing. Null is the exception: it asks whether the key exists.",
    },
    "policy.py": {
        "parse_policy": "Accept a JSON string, bytes, or a decoded dict. Statement may be a single object or a list, and Action/Resource may be a scalar or a list. Build Statement objects and wrap them in a Policy.",
        "matches_action": "Lower-case both the action and the pattern, then fnmatch.fnmatchcase. `*` spans colons, so `s3*` matches `s3:GetObject`. Never use fnmatch.fnmatch: it case-folds through the OS and is platform-dependent.",
        "matches_resource": "fnmatch.fnmatchcase(resource, pattern): case-sensitive, and `*` crosses both `:` and `/`, so a bucket wildcard covers keys with slashes.",
        "statement_matches": "NotAction inverts the action test (the statement applies to everything NOT named); otherwise the action must match an entry. The resource must match an entry, and then the condition must hold.",
        "evaluate": "Walk every statement of every policy. A matching Deny returns Deny immediately; remember whether any Allow matched. At the end: Allow if one matched, otherwise implicit Deny. Never let the last matching statement win.",
    },
}
