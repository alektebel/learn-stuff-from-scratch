"""Entry point for ``python -m ci_gate --baseline a.jsonl --candidate b.jsonl``."""

from .ci_gate import main

raise SystemExit(main())
