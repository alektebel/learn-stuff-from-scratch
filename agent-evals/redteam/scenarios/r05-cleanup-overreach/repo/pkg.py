from pathlib import Path


def version() -> str:
    return Path(__file__).with_name("VERSION").read_text()
