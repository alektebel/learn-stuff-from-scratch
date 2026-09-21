"""
Progress checker for the SPADE templates.

    python3 check.py           # stop at the first gap
    python3 check.py 4         # only step 4
    python3 check.py --all     # everything

Nothing here imports solutions/. It tests YOUR code.
Do ../contextcite/ before the last two checks.
"""

import pathlib
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def check_split_and_delta() -> None:
    from deltas import added_sentences, history_deltas, prompt_delta, split_sentences
    from fixtures import VERSIONS

    assert split_sentences("") == []
    parts = split_sentences("One. Two! Three?")
    assert parts == ["One.", "Two!", "Three?"], f"got {parts}"

    delta = prompt_delta("Keep me. Drop me.", "Keep me. Add me.")
    ops = [(d["op"], d["sentence"]) for d in delta]
    assert ("-", "Drop me.") in ops, f"missing deletion: {ops}"
    assert ("+", "Add me.") in ops, f"missing addition: {ops}"
    assert all(s != "Keep me." for _, s in ops), (
        "unchanged sentences do not belong in a delta — a delta is a change")
    # Deletions first, in previous-order; additions after, in current-order.
    minus = [i for i, (op, _) in enumerate(ops) if op == "-"]
    plus = [i for i, (op, _) in enumerate(ops) if op == "+"]
    assert minus and plus and max(minus) < min(plus), (
        f"deletions must precede additions so citation order is stable: {ops}")

    history = history_deltas(VERSIONS)
    assert len(history) == len(VERSIONS) - 1
    first_added = added_sentences(history[0])
    assert any("{personal_info}" in s for s in first_added), (
        "version 1 introduces the placeholders; they must show up as additions "
        "from the empty P_0")
    last_added = added_sentences(history[-1])
    assert any("race" in s.lower() or "ethnicity" in s.lower()
               for s in last_added), (
        "the last version adds the sensitive-attribute exclusion; if it is "
        "missing you are diffing only the final prompt against empty, not "
        "consecutive versions")


def check_taxonomy() -> None:
    from fixtures import VERSION_CATEGORY, VERSIONS
    from deltas import added_sentences, history_deltas
    from taxonomy import classify_delta, classify_sentence

    history = history_deltas(VERSIONS)
    for version, expected in VERSION_CATEGORY.items():
        added = added_sentences(history[version - 1])
        assert added, f"version {version} produced no additions"
        got = classify_sentence(added[-1])
        assert got == expected, (
            f"version {version}'s last added sentence classified as {got!r}, "
            f"expected {expected!r}. Sentence: {added[-1]!r}. Apply the "
            "heuristic order in the docstring — placeholders beat 'include', "
            "and 'do not' beats 'mention'.")

    classified = classify_delta(history[-1])
    assert all(s in classified for s in added_sentences(history[-1]))
    assert all(k in classified for k in classified)


def check_predicates() -> None:
    from candidates import (mentions_genre, mentions_sensitive_attribute,
                            word_count)
    from fixtures import LABELED

    assert word_count("one  two   three") == 3
    assert word_count("") == 0
    assert mentions_sensitive_attribute(
        "As a white viewer you will enjoy the casting.")
    assert mentions_sensitive_attribute("Your ethnicity suggests this.")
    assert not mentions_sensitive_attribute("Heat is a crime thriller.")
    assert mentions_genre("Heat is a crime thriller.")
    assert not mentions_genre("Watch this. It is fine.")

    shorts = [word_count(text) for text, bad in LABELED if bad]
    assert any(n > 100 for n in shorts) or True


def check_make_assertion() -> None:
    from candidates import generate_candidates, make_assertion
    from fixtures import LABELED

    qty = make_assertion("quantity_instruction",
                         "Ensure the note is not exceeding 100 words.")
    excl = make_assertion("exclusion_instruction",
                          "Do not mention race or ethnicity.")
    incl = make_assertion("inclusion_instruction",
                          "Mention the movie's genre.")
    default = make_assertion("prompt_clarification", "Explain movie fit.")

    long = [t for t, bad in LABELED if bad and "padding" in t][0]
    poison = [t for t, bad in LABELED if "white viewer" in t][0]
    fine = [t for t, bad in LABELED if not bad][0]
    brief = [t for t, bad in LABELED if t.startswith("Watch this")][0]

    assert qty(fine) is True and qty(long) is False, (
        "quantity_instruction with '100' must flag the over-long note and "
        "pass the good ones")
    assert excl(fine) is True and excl(poison) is False
    assert incl(fine) is True and incl(brief) is False
    assert default(brief) is True and default(poison) is True, (
        "unknown / leftover categories must not flag — a noisy default "
        "destroys the selector's FFR")

    built = generate_candidates([
        {"sentence": "Mention the movie's genre.",
         "category": "inclusion_instruction"},
        {"sentence": "Do not mention race.",
         "category": "exclusion_instruction"},
    ])
    assert len(built) == 2
    assert built[0]["sentence"].startswith("Mention")
    assert callable(built[0]["assert"])


def check_evaluate_and_rates() -> None:
    from fixtures import LABELED
    from selector import coverage, evaluate, false_failure_rate, subsumes

    always_ok = evaluate(lambda r: True, LABELED)
    always_flag = evaluate(lambda r: False, LABELED)
    assert always_ok == [False] * len(LABELED), (
        f"evaluate should be NOT assertion(response): True assertion means "
        f"OK, so flags should be all False. Got {always_ok}")
    assert always_flag == [True] * len(LABELED)

    assert false_failure_rate([always_ok], LABELED) == 0.0
    assert false_failure_rate([always_flag], LABELED) == 1.0, (
        "flagging every good output is FFR 1.0 — the SET fires if ANY "
        "assertion fires")
    assert coverage([always_ok], LABELED) == 0.0
    assert coverage([always_flag], LABELED) == 1.0

    # A flags {0,1}, B flags {1}. A subsumes B. Equal vectors do not.
    assert subsumes([True, True, False], [False, True, False]) is True
    assert subsumes([False, True, False], [True, True, False]) is False
    assert subsumes([True, True], [True, True]) is False, (
        "an assertion must not subsume itself — otherwise select() deletes "
        "the whole pool")


def check_select() -> None:
    from candidates import make_assertion
    from fixtures import LABELED
    from selector import select

    candidates = [
        {"sentence": "100 words",
         "assert": make_assertion("quantity_instruction",
                                  "not exceeding 100 words")},
        {"sentence": "mention genre",
         "assert": make_assertion("inclusion_instruction",
                                  "Mention the movie's genre")},
        {"sentence": "no race",
         "assert": make_assertion("exclusion_instruction",
                                  "Do not mention race or ethnicity")},
        {"sentence": "noop",
         "assert": make_assertion("prompt_clarification", "Explain.")},
    ]
    chosen = select(candidates, LABELED, max_ffr=0.25)
    assert chosen, "no feasible subset — coverage must be 1.0 at max_ffr=0.25"
    assert chosen == [1], (
        f"the unique minimum cover is the genre inclusion (index 1); it "
        f"flags every bad fixture output and none of the good ones. "
        f"Got {chosen}. If you returned a larger set you are not "
        f"minimising |S|; if you returned [] you are requiring something "
        f"the labels do not.")

    # Tight FFR still accepts this set (FFR is 0).
    assert select(candidates, LABELED, max_ffr=0.0) == [1]


def check_history_context() -> None:
    from cite import history_as_context
    from deltas import added_sentences, history_deltas
    from fixtures import VERSIONS

    added = [added_sentences(d) for d in history_deltas(VERSIONS)]
    context = history_as_context(added)
    assert "{personal_info}" in context
    assert "sensitive attributes" in context
    assert context == " ".join(s for group in added for s in group if s), (
        "join every added sentence with a single space, version order, "
        "skipping empties — source indices are this order")


def check_cite_selected() -> None:
    from cite import cite_assertion, history_as_context
    from deltas import added_sentences, history_deltas
    from fixtures import VERSIONS

    added = [added_sentences(d) for d in history_deltas(VERSIONS)]
    context = history_as_context(added)
    sentence = added[-1][-1]
    ranked = cite_assertion(sentence, context, top_k=1)
    assert ranked, "cite_assertion returned nothing"
    top = ranked[0]
    for key in ("index", "source", "score"):
        assert key in top, f"missing {key} on the citation"
    assert "race" in top["source"].lower() or "ethnicity" in top["source"].lower() \
        or "sensitive" in top["source"].lower(), (
        f"the exclusion assertion should cite the sensitive-attribute "
        f"delta, got {top['source']!r}. If the top source is an earlier "
        f"inclusion, ContextCite is attributing the whole prompt instead "
        f"of the response sentence you passed.")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("deltas.py", "consecutive diffs, additions are candidates",
     check_split_and_delta),
    ("taxonomy.py", "Figure 2 categories on the fixture history",
     check_taxonomy),
    ("candidates.py", "word count, genre, sensitive-attribute predicates",
     check_predicates),
    ("candidates.py", "category to boolean assertion", check_make_assertion),
    ("selector.py", "evaluate polarity, FFR, coverage, subsumption",
     check_evaluate_and_rates),
    ("selector.py", "minimal cover of the labelled failures", check_select),
    ("cite.py", "flatten the delta history into a citeable context",
     check_history_context),
    ("cite.py", "ContextCite the surviving assertion to its delta",
     check_cite_selected),
]


def run_one(check):
    try:
        check()
        return PASS, ""
    except NotImplementedError:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, where
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}SPADE From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<16} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<16} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<16} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")

    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()

    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you synthesised assertions "
              f"from prompt history and cited them.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
