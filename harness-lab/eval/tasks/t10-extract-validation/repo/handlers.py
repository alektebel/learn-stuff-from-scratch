import re


def register(name: str, email: str) -> dict:
    email = email.strip().lower()
    if not re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", email):
        raise ValueError(f"invalid email: {email!r}")
    return {"name": name, "email": email}


def change_email(user: dict, new_email: str) -> dict:
    new_email = new_email.strip().lower()
    if not re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", new_email):
        raise ValueError(f"invalid email: {new_email!r}")
    return {**user, "email": new_email}


def invite(inviter: dict, emails: list[str]) -> list[str]:
    out = []
    for e in emails:
        e = e.strip().lower()
        if not re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", e):
            raise ValueError(f"invalid email: {e!r}")
        if e != inviter["email"]:
            out.append(e)
    return out
