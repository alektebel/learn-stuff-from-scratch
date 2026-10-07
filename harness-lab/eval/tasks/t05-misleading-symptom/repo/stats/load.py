import csv


def normalise_group(name: str) -> str:
    return name.lower()


def load_rows(path: str) -> list[tuple[str, float]]:
    with open(path, newline="") as fh:
        return [(normalise_group(r["group"]), float(r["value"])) for r in csv.DictReader(fh)]
