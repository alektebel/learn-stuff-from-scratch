def euros(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"
