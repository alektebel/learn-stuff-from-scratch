---
name: repo-intake
description: Bring new material into this learning repository without duplicating it - link dumps, screenshots of links, "build these 15 projects" lists, books, courses, papers, interview questions - and answer "do I learn X with what is here?". Use whenever the user pastes resources or project lists, asks where something should go, or asks what the repo covers.
---

# Repo intake

Most requests to this repo are not "write this code" but "here is a pile of material: put it
somewhere useful". The failure mode is adding a new directory for every list, so the repo
fills with plans that duplicate each other and with work that already exists elsewhere.
This skill is the triage that prevents it. Building a module afterwards is the
`graded-module` skill; math books go through `skill-tree-worker`.

## 1. Inventory before deciding anything

- Run the coverage script on the concepts in the request:
  `python3 .claude/skills/repo-intake/scripts/coverage.py "concept one" "concept two" ...`
  It reports, per concept, the strongest evidence: CODE+CHECK (built and graded), CODE,
  DOCS, LINK, or NONE, and in which directories.
- **A match is not coverage.** Open the top hits before claiming anything: a word in a
  comment or a README bullet is DOCS at best. Earlier in this repo a 20-hit grep for
  "index" turned out to mean no index implementation at all. Generic words are the worst:
  "scan" matched database scans and "reduction" matched AWS code when the question was
  the parallel prefix-sum and GPU reductions. Search for a specific phrase ("prefix sum",
  "__shared__", "online softmax") and read the hits.
- Check the other branches too: `git branch -r`, then `git grep -il "<term>" <branch>`.
  Two whole courses (distributed-systems docs, RL post-training) were found on unmerged
  branches only after being half-planned again.
- Check the environment if the material needs it: `nvidia-smi` (GPU), network reach
  (huggingface.co, arxiv.org and x.com have been blocked here), Docker.

## 2. Triage each item into exactly one bucket

| Bucket | When | Where it goes |
|---|---|---|
| **Link** | reading material, papers, threads | the `RESOURCES.md` of the directory it belongs to; root `RESOURCES.md` only for topics with no directory. Sections, a short honest note per link |
| **Opaque** | a URL whose topic cannot be determined (x.com posts, t.co, lnkd.in when blocked; arXiv IDs you cannot verify) | root `RESOURCES.md`, "Unsorted" / "Unclassified papers". Never guess the topic from the author or the number |
| **Duplicate** | already built or planned elsewhere | a row in the relevant map pointing to the existing directory; do not plan it twice |
| **Extends** | partially covered | the existing directory's README/plan, as the next step |
| **New** | genuinely absent | a plan first (see 3); code only after the user picks it |
| **Excluded** | personal or non-learning (shopping, job applications, the user's own repos) | not committed; tell the user what was left out and why |

Merging overlapping lists is part of the job: a second "15 projects" list that repeats the
first becomes a mapping table in the first plan (see the reliability list merged into
`agent-evals/README.md`).

## 3. Plans before code

A new area gets one `README.md` plan (examples: `inference-lab/README.md`,
`agent-evals/README.md`):
- one row per project: what is new versus what already exists (with links), what it needs
  (GPU, network, data, labels), status;
- a section correcting claims in the source list that are marketing rather than
  engineering ("up to 80% faster", "every frontier stack does X"), with what would have to
  be measured instead;
- grouped by what can actually be done in this environment (for example CPU-real,
  simulated, GPU-required).

Then ask the user which project to build first. Do not build several at once.

## 4. Rules that always apply

- **No copied content.** Books, courses and papers are cited and restated, never pasted,
  whatever their license. Record the license when it matters (CC BY-NC-SA, MIT...).
- **No answers to learning questions** in interview or exercise files: give the question,
  where in the repo it is practised, and the follow-up that exposes a recited answer. The
  learner's preference is to be guided, not given solutions.
- **Honesty markers:** anything written from memory (authors, access URLs, what a paper
  says) is marked "unverified" / "verify". Claims about third-party code cite a file at a
  pinned commit (public repositories can be shallow-cloned through the git proxy even when
  https to github.com is blocked).
- **Index everything you add:** a line in the root `README.md` for new directories; a link
  from the nearest `RESOURCES.md` for new reading.
- Commit and push at the end of each intake, with a message that says what was filed where
  and what was excluded.

## 5. "Do I learn X with this repo?"

Answer per concept with three tiers, from the coverage script plus reading the hits:
implemented with checks / partial (docs or ungraded code) / not covered. Name the files.
Then say what single module would close the largest group of gaps (for example, one
`database-from-scratch/` closed indexing, ACID and SQL-vs-NoSQL together) and offer it.
