"""One live call through the configured transport.

    HARNESS_LAB_BASE_URL=... HARNESS_LAB_API_KEY=... HARNESS_LAB_MODEL=... \
        python -m eval.live_smoke "reply with one word"

This is the only place outside `eval/` that spends money: the rest of
harness-lab runs against the scripted backend for free. It prints the token
usage and the computed cost so a model's price can be recorded.
"""

from __future__ import annotations

import sys

from harness_lab.llm.base import ModelError
from harness_lab.llm.messages import Message

from eval.agents import build_model

DEFAULT_PROMPT = "Reply with the single word: pong"


def main(argv: list[str]) -> int:
    prompt = " ".join(argv) or DEFAULT_PROMPT
    model = build_model()
    completion = model.complete([Message(role="user", content=prompt)])
    usage = completion.usage
    print(f"model:       {model.name}")
    print(f"stop_reason: {completion.stop_reason}")
    print(f"text:        {completion.message.content!r}")
    print(f"usage:       in={usage.input_tokens} out={usage.output_tokens} "
          f"cached={usage.cached_tokens}")
    print(f"cost_eur:    {model.price.cost(usage):.6f}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ModelError as exc:
        print(f"model error: {exc}", file=sys.stderr)
        sys.exit(2)
