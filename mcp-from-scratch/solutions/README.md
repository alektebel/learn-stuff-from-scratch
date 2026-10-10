# solutions/ — reference implementation

`mcp_server.py` here is a complete, drop-in implementation of the `McpServer` core
(JSON-RPC dispatch, revision handshake, `tools/list`, schema-validated `tools/call`
with the two error channels, idempotent retries, the per-session sequence policy and
the streamable-HTTP framing). The module stays in LEARN mode: the file next to it,
`../mcp_server.py`, is still the stub, and this reference exists so the answer can be
checked, and so a wrong implementation can be told from a right one.

## Run the contract against the reference

```bash
cd mcp-from-scratch
rm -rf /tmp/mcp-ref && cp -r . /tmp/mcp-ref
cp solutions/mcp_server.py /tmp/mcp-ref/mcp_server.py
cd /tmp/mcp-ref && python -m pytest -q
# 6 passed, 12 xpassed  (the 12 xfail core tests xpass: the reference makes them true)
```

Any Python 3.12+ with pytest works; `python3.12 -m venv` + `pip install pytest` if the
environment has none.

## Mutation test

```bash
python mcp-from-scratch/_build/mutations.py
```

Twelve planted bugs, one per mechanism (echo the requested revision, skip fail-closed,
answer notifications, return a result for an unknown method, raise instead of an
`isError` result for an unknown tool, drop `additionalProperties`, drop required
fields, drop type checks, drop idempotent replay, skip the session policy, drop the
caller identity, answer 400 as 500). Every one is **CAUGHT** by the contract: a wrong
implementation fails a test instead of passing.

## Expected demo output

```bash
$ python mcp_server.py
tools: ['get_open_orders', 'get_vendor_balance', 'create_purchase_order']
orders: [{"reference": "SO-1001", "date": "2026-09-30", "amount": 1250.0}, {"reference": "SO-1014", "date": "2026-10-05", "amount": 480.0}]
balance: {"vendor": "Acme Supplies", "balance": 4200.0}
```
