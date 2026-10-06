import json
import pathlib

EXPECTED = {
    "svc-auth.internal": 800, "svc-billing.internal": 1200, "svc-search.internal": 600,
    "svc-media.internal": 2500, "svc-geo.internal": 700, "svc-mail.internal": 900,
    "svc-ledger.internal": 3400, "svc-users.internal": 500,
}


def test_timeouts():
    cfg = json.loads(pathlib.Path("/work/config/upstreams.json").read_text())
    assert {u["host"]: u["timeout_ms"] for u in cfg["upstreams"]} == EXPECTED
    assert [u["host"] for u in cfg["upstreams"]] == list(EXPECTED), "order of entries changed"
