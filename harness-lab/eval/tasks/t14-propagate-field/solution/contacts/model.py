from dataclasses import dataclass


@dataclass
class Contact:
    name: str
    email: str
    phone: str | None = None
