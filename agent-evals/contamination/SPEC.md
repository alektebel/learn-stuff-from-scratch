# contamination — train/eval overlap detection (LEARN mode)

## What it is

A small, dependency-free detector for **benchmark contamination**:
evaluation items that also appear — verbatim, near-verbatim, or as shared
boilerplate — in a training corpus. Given two lists of documents, `train`
and `eval`, the module reports which eval items were "seen in training" and
by which mechanism.

It is the detection half of the contamination story in `agent-evals`:
before you trust a benchmark score, you check the eval set was not part of
the training data.

Everything is standard library and deterministic: no numpy, no network, no
model calls, no built-in `hash()`.

## What it demonstrates

- **Exact matching is not enough.** Paraphrases and shared boilerplate evade
  string equality, so matching has to happen on a canonical form
  (`normalise`) and on shingles (token n-grams), not on raw text.
- **The n-gram length trade-off.** Short `n` flags innocuous boilerplate
  ("please check the original source…"); long `n` misses short borrows. The
  default of 13 tokens mirrors the 13-gram overlap rule used when auditing
  pre-training corpora (see RESOURCES.md): long enough that a shared
  13-gram is evidence of copying rather than coincidence.
- **Set similarity, exact vs estimated.** Jaccard is the exact oracle;
  MinHash is the scalable estimate — and the estimate only means anything
  if it is seeded (reproducible) and does not rest on Python's salted
  built-in `hash()`.
- **Reporting with reasons.** A caller wants one structure that says which
  eval item is contaminated and why, with a fixed precedence:
  exact > n-gram > near-duplicate.

## The interface

Module: `agent-evals/contamination/contamination.py`, imported as
`contamination.contamination`. Constants: `DEFAULT_N = 13`,
`DEFAULT_THRESHOLD = 0.8`, `DEFAULT_NUM_PERM = 128`, `DEFAULT_SEED = 0`.

```python
normalise(text: str) -> str
tokenize(text: str) -> list[str]
exact_matches(train: list[str], eval: list[str]) -> list[tuple[int, int]]
ngram_matches(train: list[str], eval: list[str], n: int = 13) -> list[tuple[int, int]]
jaccard(a: set, b: set) -> float          # implemented — test infrastructure
minhash(a: set, b: set, *, num_perm: int = 128, seed: int = 0) -> float
report(train: list[str], eval: list[str], *,
       n: int = 13, near_duplicate_threshold: float = 0.8) -> dict
```

Contracts the stubs must satisfy once implemented:

- `normalise` — drop fenced code blocks (a line starting with ``` or ~~~
  opens/closes a fence; the delimiter lines and everything between them
  disappear), lowercase, delete every punctuation character (anything in
  `string.punctuation`), collapse runs of whitespace to one space, strip
  the ends. Pins: `"Hello,   WORLD!"` → `"hello world"`;
  `"  don't  stop."` → `"dont stop"`.
- `tokenize` — `normalise(text).split()`.
- `exact_matches` — pairs `(i, j)`, `i` into `train`, `j` into `eval`,
  whose normalised texts are identical; ascending `(i, j)`, each pair once.
- `ngram_matches` — pairs whose normalised token lists share at least one
  n-gram (a tuple of `n` consecutive tokens). A text with fewer than `n`
  tokens has no n-grams: it can never match and must not crash. Each pair
  appears once even when several n-grams are shared.
- `minhash` — estimate of `jaccard(a, b)` from `num_perm` hash functions
  derived from `seed`; identical inputs give the identical float across
  calls and processes. Built-in `hash()` is forbidden (it is salted per
  process). Reference shape: `num_perm` independent hash functions, one
  min-hash signature per set, fraction of positions where signatures agree.
- `report` — keys:
  - `exact`: `exact_matches(train, eval)`
  - `ngram`: `ngram_matches(train, eval, n)`
  - `near_duplicate`: pairs `(i, j)` **not** in `exact` whose exact Jaccard
    of token sets is `>= near_duplicate_threshold`. The exact computation,
    not the MinHash estimate: `report` must be reproducible; MinHash is
    the scale path and is graded separately.
  - `n_eval`: `len(eval)`
  - `flagged`: `[(eval_j, reason), ...]` ascending by `eval_j`, one entry
    per eval item touched by any match; reason precedence
    `"exact"` > `"ngram"` > `"near_duplicate"`.

## Acceptance

Each item maps to a named test in `tests/test_contamination.py`.

1. An eval item that appears verbatim in train is flagged with reason
   `"exact"` and appears in both `exact` and `ngram`. →
   `test_exact_duplicate_is_flagged`
2. A paraphrase (same meaning, different words) is not flagged at all. →
   `test_paraphrase_is_not_flagged`
3. Shared boilerplate shorter than `n` tokens is invisible; the same
   boilerplate at exactly `n` tokens is caught with reason `"ngram"`. →
   `test_boilerplate_below_n_is_invisible`, `test_boilerplate_at_n_is_caught`
4. An eval item shorter than `n` tokens produces no n-gram matches and no
   crash. → `test_eval_shorter_than_n_is_safe`
5. `minhash` is within 0.05 of exact Jaccard on a fixed deterministic pair. →
   `test_minhash_tracks_jaccard`
6. `minhash` returns the identical float on repeated calls **and across two
   processes with different `PYTHONHASHSEED`** (so a built-in `hash()` cannot
   pass). → `test_minhash_is_deterministic`,
   `test_minhash_is_deterministic_across_processes`
7. `report` counts agree with the underlying functions (`exact`, `ngram`,
   `n_eval`, and empty `near_duplicate` on that fixture). →
   `test_report_counts_agree_with_functions`
8. Empty inputs give the empty report: `{"exact": [], "ngram": [],
   "near_duplicate": [], "n_eval": 0, "flagged": []}`. →
   `test_report_empty_inputs`

## Limit cases

Each one is a test a naive implementation fails.

- **`n` is a real knob, not decoration.** The same pair matches at `n=3`,
  not at `n=4`, and not at the default `n=13`. A naive implementation that
  ignores `n` (or compares unordered token sets) fails. →
  `test_ngram_window_tracks_n`
- **Normalisation is load-bearing.** Case, punctuation and whitespace
  differences must not hide a duplicate; normalisation is idempotent; and
  fenced code (delimiters *and* contents) disappears. A naive
  `text.lower()` fails the fence case. →
  `test_normalise_unifies_case_whitespace_punctuation`,
  `test_normalise_drops_fenced_code`
- **Threshold boundary.** Two texts differing in 2 of 21 tokens have
  token-set Jaccard 18/21 ≈ 0.857 ≥ 0.8 and are flagged `near_duplicate`; the edits
  sit at token positions 1 and 14, so no window of 13 consecutive tokens
  survives — only the near-duplicate mechanism fires. →
  `test_near_duplicate_is_flagged`
- **Jaccard conventions.** Both sets empty → 1.0 (identical); exactly one
  empty → 0.0. → `test_jaccard_both_empty_means_identical`,
  `test_jaccard_one_empty_means_disjoint`
- **The contract itself is checkable now.** Signatures, keyword-only tuning
  parameters and defaults (`n=13`, `num_perm=128`, `seed=0`,
  `threshold=0.8`). → `test_interface_contract`

## Out of scope / blocked

- **Scale.** MinHash LSH banding, Bloom filters, inverted indexes over
  millions of documents: no corpus here is big enough to need them.
  MinHash itself is in; LSH bucketing is not.
- **Semantic / embedding similarity.** Catching paraphrases that share zero
  tokens needs model embeddings — no network, no model API in this
  environment. Token-level overlap is the whole game here.
- **External libraries** (`datasketch`, numpy, regex backends): stdlib
  only, per the repo rules.
- **Policy.** Deciding what to do about contamination (decontaminate,
  re-weight, re-benchmark) is a different project; this module only
  detects and reports.
- **Unicode folding beyond `str.lower()`.** Keep the MVP honest and small;
  the fixtures are ASCII.

## How to run

```
cd /home/diego/orca/workspaces/learn-stuff-from-scratch/anthias/agent-evals
/tmp/opencode/venv/bin/python -m pytest -q tests/test_contamination.py
```

Expected while the core is unwritten: some `passed` (the shipped
infrastructure: Jaccard + the interface contract), the rest `xfailed`
(`raises=NotImplementedError`, deliberately not strict), zero
failures/errors. Each xfail turns into a pass as the matching stub is
implemented; a wrong implementation fails loudly.

## Design decisions

- **13 as the default `n`.** Long enough that a shared 13-gram is evidence
  of copying rather than coincidence; short enough that a single stolen
  sentence still trips it. Cost: boilerplate of exactly `n-1` tokens is
  invisible — accepted, and pinned as a limit case.
- **Delete punctuation instead of mapping it to space.** `"don't"` →
  `"dont"`, not `"don t"`: matching wants fewer spurious token splits, and
  consistency on both sides matters more than readability. Cost: hyphenated
  compounds merge into one token — harmless because it is applied to both
  sides equally.
- **Fences are stripped with their contents**, not just their delimiters:
  code inside a fence is boilerplate, not evidence of memorised prose.
  Cost: a memorised snippet hidden inside a fence goes undetected —
  accepted and documented.
- **`report` uses exact Jaccard, not MinHash, for `near_duplicate`.**
  Determinism and testability beat scale at this corpus size; MinHash is
  graded separately as the estimator you would swap in for millions of
  pairs. Cost: `report` is O(pairs) — fine here, wrong at scale.
- **One reason per eval item, fixed precedence** (exact > ngram >
  near_duplicate). Cost: `flagged` hides secondary evidence; the full
  lists stay available under their own keys.
- **Seed everything; never built-in `hash()`.** Built-in `hash()` is salted
  per process, so a MinHash built on it differs run to run — the whole
  point of this module is a verdict you can reproduce. Cost: you must
  derive your own hash family (`random.Random(seed)` + a fixed mixing
  function, or `hashlib.blake2b` with `key=`).
- **`jaccard` ships implemented as infrastructure.** It is the oracle the
  MinHash estimate is graded against; if the oracle were also a stub, the
  MinHash acceptance test would be unfalsifiable.
