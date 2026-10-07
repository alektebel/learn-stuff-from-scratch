import re

_EMAIL = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")


def validate_email(address: str) -> str:
    address = address.strip().lower()
    if not _EMAIL.fullmatch(address):
        raise ValueError(f"invalid email: {address!r}")
    return address
