# RESOURCES — contamination

Reading list for the contamination module. Every entry says **why** to read
it, restated in our own words — nothing here is copied. Tag per the repo
convention: `[v]` = confident it exists as described; `[verify]` = written
from memory (titles, venues, arXiv ids), confirm the exact reference before
relying on it. All links are from memory in this offline environment.

## 13-gram contamination detection

1. **"Language Models are Few-Shot Learners"** — Brown et al., 2020
   (arXiv:2005.14165), Appendix C on contamination. `[v]`
   Why: the canonical statement of the 13-gram rule this module defaults
   to — benchmark overlap was removed by flagging 13-token collisions
   between training text and eval sets, and the appendix is honest about
   what that filter catches and misses. Restated: a shared run of 13
   consecutive tokens is long enough to treat as copying, not coincidence.
2. **"Extracting Training Data from Large Language Models"** — Carlini et
   al., 2020 (arXiv:2012.07805). `[v]`
   Why: the *why it matters* paper — models regurgitate memorised training
   text, including benchmark items and personal data. This module is the
   cheap before-the-fact check for one documented failure mode.
3. **"Deduplicating Training Data Makes Language Models Better"** — Lee,
   Ainslie, Iyyer, Thompson, 2021 (arXiv:2107.06499). `[verify]`
   Why: the pipeline this module miniaturises — normalise → shingle →
   hash → compare — plus evidence that near-duplicate removal changes both
   memorisation and benchmark scores.
4. **"The Pile: An 800GB Dataset of Diverse Text for Language Modeling"** —
   Gao, Biderman et al., 2021 (arXiv:2101.00027). `[verify]`
   Why: a public corpus with per-source contamination checks; skim for the
   practical messiness (boilerplate, licence headers, mirrored sites) that
   motivates normalisation before any matching.

## MinHash / Jaccard

5. **Broder, "On the resemblance and containment of documents"**,
   Compression and Complexity of Sequences 1997. `[verify]`
   Why: origin of Jaccard "resemblance" for documents and of min-wise
   permutation sampling. Read for the error intuition the tests rely on:
   the estimate's variance shrinks like 1/num_perm.
6. **Broder et al., "Syntactic clustering of the Web"**, WWW6, 1997. `[verify]`
   Why: the production version of #5 — shingling + MinHash sketches at web
   scale — i.e. what our `tokenize` / `ngram` / `minhash` trio is a toy of.
7. **Leskovec, Rajaraman, Ullman, "Mining of Massive Datasets", chapter 3
   ("Finding Similar Items")** — free PDF from the Stanford course page. `[v]`
   Why: the most readable derivation of shingling, Jaccard, MinHash and
   LSH banding; this module is basically that chapter's exercise set, with
   the LSH banding deliberately cut (see SPEC.md, out of scope).
8. **`datasketch` documentation (MinHash / MinHashLSH)** —
   https://ekzhu.github.io/datasketch/ `[v]`
   Why: see how a real library exposes the same knobs we hardcode
   (`num_perm`, a seed) — and note it has the same requirement we do: seed
   it or the estimates are not reproducible across runs.

## Near-duplicate detection

9. **Manku, Jain, Das Sarma, "Detecting Near-Duplicates for Web
   Crawling"**, WWW '07 (the SimHash paper). `[verify]`
   Why: the rival family — SimHash + Hamming distance. Read the first
   pages to see the design fork we took (set-based Jaccard/MinHash) and
   what the fingerprint approach would have bought us.
10. **Dodge et al., "Documenting Large Webtext Corpora: A Case Study on
    the Colossal Clean Crawled Corpus"**, 2021 (arXiv:2104.08758). `[verify]`
    Why: shows normalisation choices (whitespace, punctuation, boilerplate
    stripping) doing real work in a production corpus — the same choices
    our `normalise` makes in miniature, with ablations to justify them.
