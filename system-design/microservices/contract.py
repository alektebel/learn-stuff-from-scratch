"""Versioned service contracts: is a schema change backward compatible?

Source: the Robustness Principle and the "tolerant reader" pattern; Martin Fowler on
consumer-driven contracts; Google's API improvement proposals (AIP-180) on
compatibility. Two services evolve independently, so a producer must not change its
message shape in a way that breaks a consumer still running the old code.

We model a flat message schema: `{"fields": {name: {"type": ..., "required": bool}}}`.
Backward compatible means: a client written against `old` still works when the server
speaks `new`.

DESIGN DECISION - is adding a field compatible?
    Only if it is optional. A new **required** field breaks every old client: they do not
    send it, so the server rejects their messages. This is the most common accidental
    breaking change, and it is invisible in the happy-path test that always sends it.
    Cost: a producer that wants a required field must release a major version.

DESIGN DECISION - is removing a field compatible?
    No. Old clients still send it (and a strict server rejects unknown fields), and old
    consumers still read it. Renames are therefore breakings: a remove plus an add.
    Cost: fields are effectively append-only within a major version (mark them deprecated
    instead).

DESIGN DECISION - are type changes compatible?
    Conservatively breaking, even integer -> number. Without a formal subtyping lattice
    (JSON Schema's), "widening" is easy to get wrong (e.g. int64 crossing into a double,
    or a string enum). We flag any change and let a human decide.
    Cost: some benign widenings require a major version.

DESIGN DECISION - required -> optional?
    Compatible: the server becomes more tolerant, and old clients still send the field.
    The reverse (optional -> required) is breaking. Cost: none.
"""

__all__ = ["compatibility", "breaking_changes"]


def _fields(schema):
    return schema.get("fields", {})


def breaking_changes(old, new):
    """Reasons a client written against `old` breaks against `new`, sorted."""
    # TODO: Old field removed -> reason. Same field type changed -> reason. Optional -> required -> reason. A field only in new and required -> reason. Return sorted(reasons).
    raise NotImplementedError("breaking_changes")


def compatibility(old, new):
    # TODO: Return 'breaking' if breaking_changes(old, new) is non-empty, else 'compatible'.
    raise NotImplementedError("compatibility")


if __name__ == "__main__":
    v1 = {"fields": {"id": {"type": "string", "required": True},
                     "total": {"type": "number", "required": False}}}
    examples = {
        "add optional 'coupon'": {"fields": {**v1["fields"],
                                             "coupon": {"type": "string", "required": False}}},
        "add required 'region'": {"fields": {**v1["fields"],
                                             "region": {"type": "string", "required": True}}},
        "rename 'total' to 'amount'": {"fields": {"id": v1["fields"]["id"],
                                                  "amount": {"type": "number", "required": False}}},
    }
    for label, schema in examples.items():
        verdict = compatibility(v1, schema)
        reasons = breaking_changes(v1, schema)
        print(f"{verdict:10s}  {label:28s} {reasons if reasons else ''}")
