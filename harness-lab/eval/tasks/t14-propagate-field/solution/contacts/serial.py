from contacts.model import Contact


def to_dict(c: Contact) -> dict:
    return {"name": c.name, "email": c.email, "phone": c.phone}


def from_dict(d: dict) -> Contact:
    return Contact(name=d["name"], email=d["email"], phone=d.get("phone"))
