from validators import validate_email


def register(name: str, email: str) -> dict:
    return {"name": name, "email": validate_email(email)}


def change_email(user: dict, new_email: str) -> dict:
    return {**user, "email": validate_email(new_email)}


def invite(inviter: dict, emails: list[str]) -> list[str]:
    out = []
    for e in emails:
        e = validate_email(e)
        if e != inviter["email"]:
            out.append(e)
    return out
