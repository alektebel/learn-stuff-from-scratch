from contacts.model import Contact


def to_dict(c: Contact) -> dict:
    return {"name": c.name, "email": c.email}


def from_dict(d: dict) -> Contact:
    return Contact(name=d["name"], email=d["email"])
