import csv
import io

from contacts.model import Contact


def to_csv(contacts: list[Contact]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["name", "email", "phone"])
    for c in contacts:
        w.writerow([c.name, c.email, c.phone or ""])
    return buf.getvalue()
