"""The tiny API an authored course uses to describe its stages.

A course is a directory containing `course.py`:

    from codecraft.api import stage

    TITLE = "Build a Bloom Filter"
    DESCRIPTION = "A probabilistic set, from hashing to false-positive math."

    def check_1():
        from bloom import BloomFilter
        bf = BloomFilter(bits=64, hashes=2)
        bf.add("x")
        assert "x" in bf
        assert "y" not in bf, "a fresh filter must not report false members"

    STAGES = [
        stage(
            1,
            file="bloom.py",
            title="add and contains",
            tags=["hashing", "data-structure"],
            action="Implement add() to set the k bit positions.",
            predict="can contains() ever be certain an item is absent?",
            hints=["bits = bits[:] to avoid shared state",
                   "use one hash salt per position"],
            check=check_1,
        ),
        ...
    ]

`codecraft run <course>` imports this file, runs each `check`, records the
attempt, and hands the result to the adaptive engine. `hints` are optional —
when omitted, the engine generates them from `action`/`predict`.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class Stage:
    id: int
    file: str
    title: str
    check: Callable[[], None]
    tags: List[str] = field(default_factory=list)
    action: str = ""
    predict: str = ""
    hints: List[str] = field(default_factory=list)
    solution: Optional[str] = None   # e.g. "solutions/bloom.py: BloomFilter.add"

    def meta(self) -> Dict[str, object]:
        return {
            "file": self.file,
            "title": self.title,
            "tags": list(self.tags),
            "action": self.action,
            "predict": self.predict,
            "hints": list(self.hints),
            "solution": self.solution,
        }


def stage(id: int, file: str, title: str, check: Callable[[], None],
          tags: Optional[List[str]] = None, action: str = "", predict: str = "",
          hints: Optional[List[str]] = None,
          solution: Optional[str] = None) -> Stage:
    """Convenience constructor so course.py stays readable."""
    return Stage(
        id=id, file=file, title=title, check=check, tags=list(tags or []),
        action=action, predict=predict, hints=list(hints or []),
        solution=solution,
    )
