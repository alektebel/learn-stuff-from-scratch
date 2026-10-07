"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

Each entry is (description, file, exact text in solutions/<file>, replacement,
check step). One classic mistake per exercise:

1. soft 404        - the server answers an unknown path with status 200.
2. duplicate titles - every page gets the home page's <title>.
3. missing description - the description tag is never emitted.
"""

MUTATIONS = [
    (
        "soft 404: unknown path served with status 200",
        "serve.py",
        "            self._respond(404, not_found())",
        "            self._respond(200, not_found())",
        "1",
    ),
    (
        "duplicate titles: every page uses the home page's <title>",
        "pages.py",
        '        f"<title>{title}</title>\\n"',
        '        "<title>Acme Tools — ship a small site</title>\\n"',
        "2",
    ),
    (
        "missing description: the meta description is never emitted",
        "pages.py",
        "    if description:\n",
        "    if False:\n",
        "3",
    ),
]
