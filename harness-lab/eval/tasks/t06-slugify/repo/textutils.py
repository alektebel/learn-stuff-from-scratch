def truncate(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"
