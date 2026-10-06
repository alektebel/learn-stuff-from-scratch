import re


def clean_email(email: str) -> str:
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", email):
        raise ValueError(f"invalid email {email!r}")
    return email


def clean_name(name: str) -> str:
    name = " ".join(name.split())
    if not name:
        raise ValueError("empty name")
    return name
