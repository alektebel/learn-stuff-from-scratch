"""fake_erp.py — deterministic in-memory ERP used as the test substrate.

Test infrastructure, fully implemented: the learner's server is written against the
``Erp`` protocol and tested against ``FakeErp``. Domain model mirrors what ERPNext or
Odoo would expose (customers, open sales orders, vendor balances / accounts payable,
purchase orders) without any of their machinery — no network, no Docker, stdlib only.

Every public call appends ``(method, args, identity)`` to ``calls`` so tests can check
*who* reached the ERP, not just what. There is no clock and no randomness anywhere:
same inputs, same outputs, always.
"""
from __future__ import annotations

from typing import Any, Protocol


class PolicyViolation(Exception):
    """A rule over sequences/sessions forbids this call.

    Raised even though the call, taken alone, is allowed — the violation is a
    property of the trajectory, not of the call (SPEC, limit L3).
    """


class Erp(Protocol):
    """The only surface the MCP server is allowed to know about.

    ``identity`` is keyword-only everywhere: it is metadata about *who* is calling,
    recorded by the ERP, never a business argument.
    """

    def open_orders(
        self, customer: str, *, identity: str | None = None
    ) -> list[dict[str, Any]]: ...

    def vendor_balance(self, vendor: str, *, identity: str | None = None) -> float: ...

    def create_purchase_order(
        self, reference: str, vendor: str, amount: float, *, identity: str | None = None
    ) -> dict[str, Any]: ...

    @property
    def orders(self) -> tuple[dict[str, Any], ...]: ...


class FakeErp:
    """Deterministic, in-memory stand-in for the legacy ERP."""

    CUSTOMERS = ("Northwind Traders", "Contoso Ltd", "Globex SA")
    VENDORS = ("Acme Supplies", "Brass & Co", "Cortado GmbH")

    _OPEN_ORDERS: dict[str, tuple[dict[str, Any], ...]] = {
        "Northwind Traders": (
            {"reference": "SO-1001", "date": "2026-09-30", "amount": 1250.0},
            {"reference": "SO-1014", "date": "2026-10-05", "amount": 480.0},
        ),
        "Contoso Ltd": (
            {"reference": "SO-1007", "date": "2026-10-02", "amount": 9900.0},
        ),
        "Globex SA": (),
    }
    _VENDOR_BALANCES: dict[str, float] = {
        "Acme Supplies": 4200.0,
        "Brass & Co": 0.0,
        "Cortado GmbH": 15750.5,
    }

    def __init__(self) -> None:
        self._orders: list[dict[str, Any]] = []
        # (method, args-dict, identity) for every public call, in call order
        self.calls: list[tuple[str, dict[str, Any], str | None]] = []

    def _log(self, method: str, **args: Any) -> None:
        identity = args.pop("identity")
        self.calls.append((method, args, identity))

    # -- reads -------------------------------------------------------------------
    def open_orders(self, customer: str, *, identity: str | None = None) -> list[dict[str, Any]]:
        self._log("open_orders", customer=customer, identity=identity)
        try:
            rows = self._OPEN_ORDERS[customer]
        except KeyError:
            raise KeyError(f"unknown customer {customer!r}") from None
        return [dict(row) for row in rows]  # copies: the caller cannot mutate the fixture

    def vendor_balance(self, vendor: str, *, identity: str | None = None) -> float:
        self._log("vendor_balance", vendor=vendor, identity=identity)
        try:
            return self._VENDOR_BALANCES[vendor]
        except KeyError:
            raise KeyError(f"unknown vendor {vendor!r}") from None

    # -- writes ------------------------------------------------------------------
    def create_purchase_order(
        self, reference: str, vendor: str, amount: float, *, identity: str | None = None
    ) -> dict[str, Any]:
        self._log(
            "create_purchase_order",
            reference=reference,
            vendor=vendor,
            amount=amount,
            identity=identity,
        )
        if vendor not in self._VENDOR_BALANCES:
            raise KeyError(f"unknown vendor {vendor!r}")
        if any(order["reference"] == reference for order in self._orders):
            # the error text is part of the interface: it tells the caller what to do
            raise ValueError(
                f"a purchase order with reference {reference!r} already exists — "
                "do not retry, ask the user"
            )
        order = {
            "reference": reference,
            "vendor": vendor,
            "amount": amount,
            "number": len(self._orders) + 1,
        }
        self._orders.append(order)
        return dict(order)

    @property
    def orders(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(order) for order in self._orders)
