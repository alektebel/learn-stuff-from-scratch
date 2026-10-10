"""MCP From Scratch — the ERP the tools read and write.

Provided, not a stage: the domain is not the exercise. Small on purpose, and
strict about business failures, because stages 7-9 are about what a server does
with a failure — not about what a failure is.

Every mutation is a CHANGE: a plain dict that describes what should become true
(`draft`, `approve`, `set_quantity`), with `diff()` saying which fields move from
where to where. That shape is what lets a person be shown the change instead of
the tool call, and what lets an approval be bound to a specific change.

`apply()` validates the change it is handed, every time: a change is data, and
data from a client is input like any other. The diff a customer approved and the
change that gets applied are the same object here, or stage 9 is theatre.
"""

import copy

DEFAULT_VENDORS = {
    "v1": {"vendor_id": "v1", "name": "Northwind Fasteners", "balance": 12000},
    "v2": {"vendor_id": "v2", "name": "Acme Industrial", "balance": 3400},
    "v3": {"vendor_id": "v3", "name": "Baltic Tooling", "balance": 0},
}

DEFAULT_ITEMS = {
    "i1": {"item_id": "i1", "name": "M8 bolt", "unit_cost": 3},
    "i2": {"item_id": "i2", "name": "Steel plate", "unit_cost": 41},
}

KINDS = ("draft_order", "approve_order", "set_quantity")


class ErpError(Exception):
    """A business failure: the request was well-formed and the world said no."""


class Erp:
    def __init__(self, *, vendors=None, items=None, orders=None):
        self.vendors = copy.deepcopy(DEFAULT_VENDORS if vendors is None else vendors)
        self.items = copy.deepcopy(DEFAULT_ITEMS if items is None else items)
        self.orders = copy.deepcopy(orders or {})

    # --- reads -------------------------------------------------------------

    def read(self, vendor_id):
        vendor = self.vendors.get(vendor_id)
        if vendor is None:
            raise ErpError(f"unknown vendor {vendor_id!r}")
        return dict(vendor)

    def report(self, table, where=None, columns=None):
        """A read-only projection. `where` values are COMPARED, never parsed —
        there is no query language here for a value to escape into."""
        tables = {"vendors": self.vendors, "items": self.items, "orders": self.orders}
        rows = tables.get(table)
        if rows is None:
            raise ErpError(f"unknown table {table!r}")
        chosen = list(columns) if columns else sorted(
            {key for row in rows.values() for key in row})
        where = where or {}
        out = []
        for key in sorted(rows):
            row = rows[key]
            if all(row.get(column) == value for column, value in sorted(where.items())):
                out.append([row.get(column) for column in chosen])
        return {"columns": chosen, "rows": out}

    # --- the change builders ----------------------------------------------

    def draft(self, reference, vendor_id, item_id, quantity, *, identity):
        self._vendor(vendor_id)
        self._item(item_id)
        self._quantity(quantity)
        if reference in self.orders:
            raise ErpError(f"a purchase order {reference!r} already exists — do not "
                           f"retry, ask the user")
        return {"kind": "draft_order", "reference": str(reference),
                "vendor_id": vendor_id, "item_id": item_id,
                "quantity": int(quantity), "status": "draft", "identity": identity}

    def approve(self, reference, *, identity):
        order = self._order(reference)
        if order["status"] == "approved":
            raise ErpError(f"purchase order {reference!r} is already approved — "
                           f"nothing to do, do not retry")
        return {"kind": "approve_order", "reference": reference,
                "status": "approved", "identity": identity}

    def set_quantity(self, reference, quantity, *, identity):
        self._order(reference)
        self._quantity(quantity)
        return {"kind": "set_quantity", "reference": reference,
                "quantity": int(quantity), "identity": identity}

    # --- the diff, and applying it ----------------------------------------

    def diff(self, change):
        """What `apply(change)` would change, from where to where. A field that
        does not exist yet reads `from: None`."""
        kind = change.get("kind")
        if kind == "draft_order":
            return [{"field": field, "from": None, "to": change[field]}
                    for field in ("reference", "vendor_id", "item_id", "quantity", "status")]
        if kind == "approve_order":
            return [{"field": "status",
                     "from": self._order(change["reference"])["status"],
                     "to": "approved"}]
        if kind == "set_quantity":
            return [{"field": "quantity",
                     "from": self._order(change["reference"])["quantity"],
                     "to": change["quantity"]}]
        raise ErpError(f"unknown change {kind!r}")

    def apply(self, change, *, identity):
        kind = change.get("kind")
        if kind not in KINDS:
            raise ErpError(f"unknown change {kind!r}")
        if kind == "draft_order":
            vendor_id, item_id = change.get("vendor_id"), change.get("item_id")
            self._vendor(vendor_id)
            self._item(item_id)
            self._quantity(change.get("quantity"))
            reference = change.get("reference")
            if not isinstance(reference, str) or not reference:
                raise ErpError("a purchase order needs a reference")
            if reference in self.orders:
                raise ErpError(f"a purchase order {reference!r} already exists — do "
                               f"not retry, ask the user")
            self.orders[reference] = {
                "reference": reference, "vendor_id": vendor_id, "item_id": item_id,
                "quantity": int(change["quantity"]), "status": "draft",
                "identity": identity}
            return dict(self.orders[reference])
        if kind == "approve_order":
            self.approve(change.get("reference"), identity=identity)
            order = self.orders[change["reference"]]
            order["status"] = "approved"
            order["identity"] = identity
            return dict(order)
        self.set_quantity(change.get("reference"), change.get("quantity"),
                          identity=identity)
        order = self.orders[change["reference"]]
        order["quantity"] = int(change["quantity"])
        order["identity"] = identity
        return dict(order)

    # --- checks ------------------------------------------------------------

    def _vendor(self, vendor_id):
        if vendor_id not in self.vendors:
            raise ErpError(f"unknown vendor {vendor_id!r}")
        return self.vendors[vendor_id]

    def _item(self, item_id):
        if item_id not in self.items:
            raise ErpError(f"unknown item {item_id!r}")
        return self.items[item_id]

    def _order(self, reference):
        order = self.orders.get(reference)
        if order is None:
            raise ErpError(f"unknown purchase order {reference!r}")
        return order

    def _quantity(self, quantity):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ErpError(f"quantity must be a positive whole number, got {quantity!r}")
        return quantity
