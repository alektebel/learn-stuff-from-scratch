"""`codecraft new` — scaffold an authored course you can fill in.

The generated directory is immediately runnable: every stage is a template that
raises NotImplementedError, so `codecraft run <course>` reports TODO and the
adaptive engine starts coaching you before you have written a single check.

Authoring a course is authoring its tests. The scaffolds put the two together:
`course.py` holds the metadata and the checks; the stage files hold the code.
"""

import os
import re

from .manifests import REPO_ROOT


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


_README = """# {title}

{description}

A codecraft course. Each stage is a template under `stage_NN.py`; the grader
lives in `course.py`. Run it and let the tool adapt to you:

```bash
python3 codecraft/cli.py run {slug}
python3 codecraft/cli.py hint {slug}     # when a nudge is not enough
```

Fill `course.py`'s checks with the assertions that actually define the stage —
the mistakes that are easy to make and hard to notice, not line coverage.
"""

_STAGE = '''"""{title} — stage {n}: {stage_title}

DESIGN DECISION — why this interface?
    Write your reason here before you write the body. The reason is half the
    lesson; without it this is just syntax.

TODO: implement `solve`. The check for this stage imports it.
"""


def solve(*args, **kwargs):
    raise NotImplementedError("stage {n}: implement solve()")
'''

_SOLUTION = '''"""/{title} — stage {n} ({stage_title})

Write the finished, runnable version here, and make it print a real
measurement rather than a claim. Compare against `stage_{n:02d}.py`.
"""


def solve(*args, **kwargs):
    raise NotImplementedError
'''

_COURSE_HEAD = '''"""Course manifest — read codecraft/api.py for the full shape.

TITLE / DESCRIPTION / LEVEL / ORDER are course metadata.
STAGES is the graded sequence; each stage names the file to implement, the
concept tags it exercises, the one micro-action when it fails, the number to
predict when it passes, and a `check` function that asserts the requirement.
"""

from codecraft.api import stage

TITLE = {title!r}
DESCRIPTION = {description!r}
LEVEL = "custom"
ORDER = 99
'''


def create(slug: str, title: str = "", description: str = "", stages: int = 2,
           force: bool = False) -> str:
    slug = _slug(slug)
    title = title or slug.replace("-", " ").title()
    description = description or f"Learn {title} by building it from scratch."
    target = os.path.join(REPO_ROOT, slug)
    if os.path.exists(target) and not force:
        raise FileExistsError(
            f"{target} already exists (pass --force to write into it)")
    os.makedirs(os.path.join(target, "solutions"), exist_ok=True)

    with open(os.path.join(target, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(_README.format(title=title, description=description, slug=slug))

    stage_titles = [f"stage {i} requirement" for i in range(1, stages + 1)]
    for n in range(1, stages + 1):
        with open(os.path.join(target, f"stage_{n:02d}.py"), "w",
                  encoding="utf-8") as fh:
            fh.write(_STAGE.format(title=title, n=n,
                                   stage_title=stage_titles[n - 1]))
        with open(os.path.join(target, "solutions", f"stage_{n:02d}.py"), "w",
                  encoding="utf-8") as fh:
            fh.write(_SOLUTION.format(title=title, n=n,
                                      stage_title=stage_titles[n - 1]))

    with open(os.path.join(target, "course.py"), "w", encoding="utf-8") as fh:
        fh.write(_COURSE_HEAD.format(title=title, description=description))
        for n in range(1, stages + 1):
            fh.write(f'''

def check_{n}():
    from stage_{n:02d} import solve
    result = solve()
    raise NotImplementedError(
        "course {slug!r}: write the real assertions for stage {n} in course.py")
    assert result is not None, "replace this with a requirement that can fail"


''')
        fh.write("STAGES = [\n")
        for n in range(1, stages + 1):
            fh.write(f'''    stage(
        {n},
        file="stage_{n:02d}.py",
        title={stage_titles[n - 1]!r},
        tags=[],
        action="State the one concrete thing to implement for stage {n}.",
        predict="State the number or behaviour to predict before running.",
        check=check_{n},
    ),
''')
        fh.write("]\n")

    return target
