"""
Where does this repository cover a concept, and how deeply?

    python3 coverage.py "write skew" "isolation level" "B-tree"
    python3 coverage.py --file topics.txt          # one concept per line (# comments allowed)

For each concept, searches tracked files (git ls-files) case-insensitively and classifies
every hit by what kind of file it is in, because a mention is not coverage:

  CODE+CHECK  the term appears in a module that has a check.py   (built and graded)
  CODE        the term appears in .py/.c/.cu/.lean/.hs source     (built, ungraded)
  DOCS        README/guide/design docs                           (explained, not built)
  LINK        RESOURCES.md                                       (only a link)

The verdict per concept is its strongest level. Directories are listed so a human can open
them and confirm: a word match can still be a false positive ("index" in a loop variable),
so always read the top hits before claiming coverage.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

LEVELS = ["LINK", "DOCS", "CODE", "CODE+CHECK"]
SOURCE_EXT = {".py", ".c", ".h", ".cu", ".lean", ".hs", ".rs", ".go", ".ts", ".js"}
SKIP_PARTS = {"node_modules", ".venv", "__pycache__", ".claude"}


def repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(out.stdout.strip() or ".")


def tracked_files(root: Path) -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    files = []
    for line in out.stdout.splitlines():
        p = Path(line)
        if SKIP_PARTS & set(p.parts):
            continue
        files.append(p)
    return files


def module_of(rel: Path) -> str:
    return rel.parts[0] if len(rel.parts) > 1 else "(root)"


def classify(rel: Path, graded_modules: set[str]) -> str:
    if rel.name == "RESOURCES.md":
        return "LINK"
    if rel.suffix in SOURCE_EXT and "solutions" not in rel.parts:
        top = module_of(rel)
        graded = any(str(rel).startswith(m + "/") or top == m for m in graded_modules)
        return "CODE+CHECK" if graded else "CODE"
    if rel.suffix in SOURCE_EXT:
        return "CODE"
    return "DOCS"


def find_graded(root: Path, files: list[Path]) -> set[str]:
    """Directories containing a check.py (a graded module), as path prefixes."""
    return {str(p.parent) for p in files if p.name == "check.py"}


def scan(concepts: list[str], root: Path) -> dict:
    files = tracked_files(root)
    graded = find_graded(root, files)
    texts = {}
    for rel in files:
        try:
            texts[rel] = (root / rel).read_text(errors="ignore").lower()
        except (OSError, UnicodeDecodeError):
            continue
    report = {}
    for concept in concepts:
        rx = re.compile(r"\b" + re.escape(concept.lower()) + r"\b")
        hits = defaultdict(lambda: defaultdict(int))  # level -> module -> count
        for rel, text in texts.items():
            n = len(rx.findall(text))
            if n:
                hits[classify(rel, graded)][module_of(rel)] += n
        best = max((LEVELS.index(l) for l in hits), default=-1)
        report[concept] = (LEVELS[best] if best >= 0 else "NONE", hits)
    return report


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("concepts", nargs="*")
    ap.add_argument("--file", type=Path)
    a = ap.parse_args(argv)
    concepts = list(a.concepts)
    if a.file:
        concepts += [l.strip() for l in a.file.read_text().splitlines() if l.strip() and not l.startswith("#")]
    if not concepts:
        ap.error("give concepts or --file")
    report = scan(concepts, repo_root())
    width = max(len(c) for c in concepts)
    for concept, (verdict, hits) in report.items():
        print(f"{concept:<{width}}  {verdict}")
        for level in reversed(LEVELS):
            if level in hits:
                mods = sorted(hits[level].items(), key=lambda kv: -kv[1])[:6]
                print(f"{'':<{width}}    {level:<10} " + ", ".join(f"{m} ({n})" for m, n in mods))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
