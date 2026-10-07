import sys

from stats.load import load_rows
from stats.summary import summarise


def main(path: str) -> str:
    return "\n".join(f"{g},{n},{m:.2f}" for g, n, m in summarise(load_rows(path)))


if __name__ == "__main__":
    print(main(sys.argv[1]))
