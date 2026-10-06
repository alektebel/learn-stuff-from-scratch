import json
from pathlib import Path

from contacts.model import Contact
from contacts.serial import from_dict, to_dict
from contacts.validate import clean_email, clean_name


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)

    def all(self) -> list[Contact]:
        if not self.path.exists():
            return []
        return [from_dict(d) for d in json.loads(self.path.read_text())]

    def add(self, name: str, email: str) -> Contact:
        c = Contact(clean_name(name), clean_email(email))
        items = self.all() + [c]
        self.path.write_text(json.dumps([to_dict(x) for x in items]))
        return c

    def get(self, name: str) -> Contact | None:
        return next((c for c in self.all() if c.name == name), None)
