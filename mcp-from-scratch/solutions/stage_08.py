"""MCP From Scratch — stage 8: idempotency, because the caller will retry

SOLUTION. The key is required and declared in the schema, the fingerprint is
sha256 of the canonical arguments, and every outcome that reached the ERP —
success or business failure — is replayed byte for byte. A validation failure
is not an outcome: nothing was attempted, so there is nothing to remember.
"""

import copy
import hashlib
import json

from erp import ErpError
from stage_01 import ERRORS, ProtocolError

_TOOL_NAME = "create_purchase_order"

CREATE_ORDER_SCHEMA = {
    "type": "object",
    "properties": {
        "idempotencyKey": {"type": "string", "minLength": 8},
        "reference": {"type": "string"},
        "vendor_id": {"type": "string"},
        "item_id": {"type": "string"},
        "quantity": {"type": "integer"},
    },
    "required": ["idempotencyKey", "reference", "vendor_id", "item_id", "quantity"],
}

_DESCRIPTION = (
    "Create a draft purchase order and apply it. idempotencyKey is required: the "
    "same key with the same arguments is answered from the ledger without a "
    "second write, and the same key with different arguments is refused."
)


def _fingerprint(params):
    body = json.dumps(params, sort_keys=True, separators=(",", ":"), default=repr)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _text_result(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


class Ledger:
    def __init__(self, erp):
        self.erp = erp
        self.applied = {}
        self.reused = 0

    def _validate(self, params):
        if not isinstance(params, dict):
            raise ProtocolError(ERRORS["invalid_params"],
                                f"{_TOOL_NAME} takes an object of arguments",
                                {"tool": _TOOL_NAME})
        missing = [name for name in CREATE_ORDER_SCHEMA["required"]
                   if name not in params]
        if missing:
            raise ProtocolError(
                ERRORS["invalid_params"],
                f"missing required parameter {', '.join(sorted(missing))} for "
                f"{_TOOL_NAME}", {"tool": _TOOL_NAME})
        key = params["idempotencyKey"]
        if not isinstance(key, str) or len(key) < 8:
            raise ProtocolError(
                ERRORS["invalid_params"],
                f"idempotencyKey must be a string of at least 8 characters, got "
                f"{key!r}", {"tool": _TOOL_NAME})
        return params

    def create_order(self, params, session):
        params = self._validate(params)
        key = params["idempotencyKey"]
        fingerprint = _fingerprint(params)

        if key in self.applied:
            entry = self.applied[key]
            if entry["fingerprint"] != fingerprint:
                return _text_result(
                    f"idempotency key {key!r} was already used for a different "
                    f"request, so this one was not applied; the key stays spent — "
                    f"do not retry, ask the user", is_error=True)
            self.reused += 1
            return copy.deepcopy(entry["result"] if entry["outcome"] == "ok"
                                 else entry["message"])

        identity = (session or {}).get("identity") or "anonymous"
        try:
            change = self.erp.draft(params["reference"], params["vendor_id"],
                                    params["item_id"], params["quantity"],
                                    identity=identity)
            order = self.erp.apply(change, identity=identity)
        except ErpError as exc:
            message = _text_result(
                f"purchase order {params['reference']!r} was refused by the ERP: "
                f"{exc}. The idempotency key {key!r} is spent — a retry returns "
                f"this same failure, never a second attempt", is_error=True)
            self.applied[key] = {"fingerprint": fingerprint, "outcome": "error",
                                 "message": copy.deepcopy(message)}
            return message

        result = _text_result(
            f"purchase order {order['reference']!r} for vendor {order['vendor_id']!r} "
            f"({order['quantity']} x {order['item_id']!r}) is {order['status']}")
        self.applied[key] = {"fingerprint": fingerprint, "outcome": "ok",
                             "result": copy.deepcopy(result)}
        return result


def install(server, ledger):
    server.add_tool(_TOOL_NAME, _DESCRIPTION, CREATE_ORDER_SCHEMA,
                    ledger.create_order, mutates=True)
