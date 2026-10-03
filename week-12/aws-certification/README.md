# AWS Certification — the half `aws-from-scratch` does not cover

**SKELETON.** Files, signatures and the checker contract are in place. Nothing
is implemented, no checks are written. See [`../../TODO.md`](../../TODO.md) §10.

## Read this before you plan around it

`aws-from-scratch/` will not get you through an AWS exam on its own, and the
reason is structural rather than a gap in effort.

This repo is deliberately **anti-recall**. Its whole standard, from
[`PHILOSOPHY.md`](../../PHILOSOPHY.md), is that you can re-derive a design
decision and name the alternative that was rejected. AWS exams are
**substantially recall**: service names, quotas, defaults, retrieval times,
which of six connectivity options fits. You cannot derive an arbitrary quota
from first principles, and no amount of understanding will tell you what
Amazon called something.

So the knowledge splits in two, and this directory keeps the split visible:

| | Derivable | Arbitrary |
|---|---|---|
| examples | which service clears this RPO at least cost; whether IOPS or throughput binds; where serverless overtakes provisioned | default quotas, Glacier retrieval tiers, service names, hard limits |
| how you get it | `aws-from-scratch/` gave you the mechanisms; `check.py` here grades the reasoning | `drill.py`, spaced repetition, daily, deliberately **not** graded by `check.py` |

**The honest split:** having done `aws-from-scratch/` you hold the harder half,
and it is the half that separates people who reason from people who crammed. It
is also not sufficient. Budget real time for the drill.

## What you build

| File | What it grades | Stubs |
|---|---|---|
| `decide.py` | Service selection under constraints — the shape of nearly every scenario question | 6 |
| `storage.py` | S3 classes, lifecycle arithmetic, EBS ceilings, EFS vs FSx | 7 |
| `network.py` | Topology and reachability; the six ways to join two networks; Route 53 policies | 6 |
| `resilience.py` | DR patterns with RPO and RTO as computed numbers | 6 |
| `mlstack.py` | SageMaker and Bedrock mapped onto mechanisms you already built | 6 |
| `wellarchitected.py` | The six pillars as a scored review with trade-offs | 5 |
| `drill.py` | Spaced repetition over the arbitrary facts — **not** graded here | 6 |

```bash
cd week-12/aws-certification
python3 check.py          # 10 graded checks — NOT YET WRITTEN
python3 drill.py          # daily, and it is not a checker
```

## The exams, and what your standing is

Verify codes and blueprints against the current official exam guide before
planning around any of this — codes change, services are renamed and retired,
and this file has a knowledge cutoff.

| Exam | What it wants | What `aws-from-scratch/` already gives you |
|---|---|---|
| **AI Practitioner** (foundational) | Terminology, responsible AI, the Bedrock/SageMaker surface | Little of it directly — this is mostly vocabulary. Cheapest to clear, least valuable. |
| **ML Engineer – Associate** | SageMaker pipelines, feature store, data prep, deployment options, monitoring | The mechanisms under all of it: `context-caching/`, `ml-inference/`, `mlops/`, plus DynamoDB partitioning for Feature Store. The product surface is the gap — `mlstack.py`. |
| **Solutions Architect – Associate** | ~60 services, chosen under constraints; storage, networking, DR, cost | The reasoning core, and a real advantage on cost questions from `pricing.py` and `optimize.py`. The breadth is the gap. |
| **Solutions Architect – Professional** | Multi-account, migration, and trade-offs **between** pillars | `wellarchitected.py` is aimed here. This one rewards your kind of preparation the most and is the one worth actually wanting. |

## The four things this directory is really for

1. **Elimination, with a named reason.** The exam rewards ruling three options
   out, and a procedure that only returns a winner cannot tell you why it was
   not the other one — which is precisely the case where you get it wrong.
2. **Boundaries, not lookups.** Change one requirement and the right answer
   should change. If your decision table returns the same service across a
   boundary you can compute, it has memorised the scenario rather than the rule.
3. **The cheapest option that clears the bar, not the best one.** The most
   common wrong answer on DR and storage questions is the *better* architecture.
   `resilience.py` grades cheapest-that-clears on purpose.
4. **Crossovers you already know how to find.** Serverless versus provisioned
   inference is the same shape as the DynamoDB provisioned/on-demand crossover
   you derived in `optimize.py`. Several exam "rules of thumb" are a crossover
   with the arithmetic hidden.

## Related

- [`aws-from-scratch/`](../../week-01/aws-from-scratch/) — the eight mechanisms, and the bill
- [`system-design/`](../../reference/system-design/) — the patterns underneath most services
- [`deploy-and-debug/`](../../week-04/deploy-and-debug/) — operating what you chose
- [`dynamo-paper/`](../../week-10/dynamo-paper/) — why DynamoDB is shaped that way

## Sources

- **The current official exam guides.** TODO §10.10 says to diff them against
  the check list before writing anything, and to treat any conflict as the guide
  being right. This directory has a knowledge cutoff; they do not.
- **AWS Well-Architected Framework** and its lenses — `wellarchitected.py`.
- **AWS Service Quotas**, the **price list API**, and each service's **FAQ** —
  the three sources §12b ranks above the user guide, for three different kinds
  of question.
- Roediger & Karpicke, **"Test-Enhanced Learning"**, 2006 — why `drill.py` is
  retrieval practice rather than review, and why it is separate from `check.py`.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-12--aws-certification-and-deployment)

---

[← Week 6](../) · [Roadmap](../../ROADMAP.md) · [What remains](../../REMAINING.md)
