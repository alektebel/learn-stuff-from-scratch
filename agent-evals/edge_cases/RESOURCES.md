# edge_cases — resources

What to read before writing the core, restated here so the module stands alone. Nothing
below is copied; each entry says where it comes from and what it means for this module.
Where a claim is from a description rather than code we read, it says so.

## Why generate cases at all

**Fuzzing** — AFL (<https://github.com/google/AFL>), OSS-Fuzz
(<https://google.github.io/oss-fuzz/>). A fuzzer does not guess inputs one at a time; it
mutates known-good inputs and keeps the mutations that reach new behaviour. This module is
the mutation half, pointed at evaluation inputs rather than binaries: take a gold task and
transform it. The lesson kept here is that a mutation must *differ* from its source, or it
proves nothing — hence `is_trivial`.

**Property-based testing** — Hypothesis (<https://hypothesis.readthedocs.io/>). A property
test states a law ("the reverse of the reverse is the original") and a generator tries to
break it, shrinking failures to a minimal case. The lesson for this module is determinism:
a seed must reproduce the exact inputs, so the generated set can be diffed between runs.
(Based on the project's public documentation, not read line-by-line.)

## Measuring novelty without comparing everything

**MinHash and shingling** — Broder, "On the resemblance and containment of documents"
(1997); Manku, Jain & Das Sarma, "Detecting near-duplicates for web crawling" (WWW 2007).
Shingling turns a document into the set of its overlapping k-character substrings; Jaccard
similarity of two shingle sets is the resemblance. MinHash compresses each set to a fixed
signature of minimum hash values; the fraction of positions where two signatures agree
estimates their Jaccard similarity. This module uses it because a gold set can be large and
comparing every pair exactly is wasteful; the estimate is good enough to gate on.

**SimHash / near-duplicate detection** — Charikar, "Similarity estimation techniques from
rounding algorithms" (STOC 2002). The other classic sketch. Noted so the choice is explicit:
this module uses MinHash, and the contract fixes the signature size (L3) so the estimate is
reproducible.

## The traps these cases probe

**Unicode confusables** — Unicode Technical Standard #39, "Unicode Security Mechanisms"
(<https://www.unicode.org/reports/tr39/>). Visually identical characters can have different
codepoints; a normalisation step that only case-folds and collapses whitespace does not
remove them (L4 says cosmetic differences are duplicates, but a homoglyph is a real
difference). The `unicode` family exists to make a system meet one on purpose.

**Prompt injection** — OWASP, "Top 10 for LLM Applications", LLM01: Prompt Injection
(<https://genai.owasp.org/>). Model output and retrieved text can carry instructions the
application should not obey. The `injection` family inserts one such phrase so the input
distribution has it. (Based on the published list, not read in code.)

**Contamination between train and eval** — overlaps [#14 contamination](../contamination/).
A near-copy of a gold task is the same failure a contaminated benchmark has: it inflates
scores because it is not really new. `deduplicate` is this module's defence, and it is the
reason novelty is measured rather than assumed.

## How to verify the contract

- The provided infrastructure tests (`normalize`, `shingles`, `jaccard`, `minhash`) pass
  today: `cd agent-evals && python3.12 -m pytest -q tests/test_edge_cases.py`.
- The core tests carry `xfail(raises=NotImplementedError)`: they report `xfailed` now and
  turn into `xpassed` once the core is written.
- A correct implementation must make every core test pass; a reference was used to confirm
  the contract is satisfiable and that the obvious bugs (a transform that returns the source
  unchanged, dedup that never fires, MinHash seeded by Python's salted `hash()`, an empty
  gold set that crashes) each fail at least one test.
