# aws-deploy — shipping it, for real

**SKELETON.** Signatures and the checker contract are in place; nothing is
implemented. See [`../../TODO.md`](../../TODO.md) §11.

## Why this exists

`week-01/aws-from-scratch/` teaches you *why* a service behaves as it does by
building a toy version. It says so itself: **"Not API-compatible. No boto3
surface, no XML, no signatures, no regions."** That is the right trade for
understanding and it leaves a real gap — after it you can derive why a hot
partition key throttles a table that looks idle, and you cannot run
`aws dynamodb put-item`.

Three goals, and the repo only served one and a half:

| Goal | Needs | Where |
|---|---|---|
| Understand | mechanisms | [`week-01/aws-from-scratch/`](../../week-01/aws-from-scratch/) |
| Pass certs | reasoning + recall | [`../aws-certification/`](../aws-certification/) |
| **Ship to real users** | an account, the SDK, IaC, a pipeline, cost guards | **here** |

The "200 services reduce to 8 mechanisms" argument is true for the first two
and **false for the third**. Knowing S3's flat namespace does not teach you
`aws s3 sync`, an Amplify build spec, a CloudFront invalidation, or what to do
when a deploy is green and the site 403s. Those are facts and muscle memory —
same category as `drill.py`, and not derivable.

## The split

| | Graded by `check.py` | Not graded, cannot be |
|---|---|---|
| | Policy documents, IaC graphs, idle-cost arithmetic, the deploy state machine — all **data**, all lintable offline with no account and no network | A real account, a real domain, a real failed build, and the hour you lose to DNS |
| | 42 stubs, 10 checks | [`RUNBOOK.md`](RUNBOOK.md), 7 phases |

`check_runbook_is_separate` asserts nothing here becomes network-capable, so
the boundary survives the directory growing.

## What you build

| File | Grades | Stubs |
|---|---|---|
| `credentials.py` | The resolution chain, and a static key where a session belongs | 6 |
| `policy.py` | Granted-minus-needed, wildcards on writes, trust policies | 7 |
| `template.py` | Dependency order, cycles, rollback, teardown orphans | 7 |
| `guard.py` | What bills at 3am, and an alarm faster than the spend | 6 |
| `deploy.py` | Fail at every step, end safe every time | 6 |

```bash
cd week-12/aws-deploy
python3 check.py          # 10 offline checks — NOT YET WRITTEN
```

## The one measurable claim

> Rebuild the entire stack from an empty account, from code, in **under an
> hour**, and tear it back down to a **zero bill**. Twice.

That is what "I control this" means operationally, and it is the only test here
that cannot be faked. Everything in the runbook is in service of it.

## Before you start

Phase 0 of the runbook is a billing alarm and short-lived credentials, and it is
marked DO NOT SKIP for a reason: the two ways this goes badly are a leaked key
and a forgotten resource that bills per hour. Both are cheap to prevent and
expensive to discover.

## Sources

[`../../REFERENCES.md`](../../REFERENCES.md#week-12--aws-certification-and-deployment)
carries the list. The ones that matter here are not papers:

- The **current AWS documentation** for every command in `RUNBOOK.md`. CLI
  syntax and console flows change; verify before you run.
- **AWS Service Quotas** — answers *"is this a limit or a bug"*.
- The **price list API** — beats the pricing page, and is what `guard.py` should
  be checked against.
- **AWS Security Best Practices** and the IAM docs — least privilege, permission
  boundaries, and the credential resolution chain `credentials.py` models.
- Beyer et al., **Site Reliability Engineering** (Google), ch. 3 — error budgets,
  for the health gate and rollback in `deploy.py`.

---

[← Week 12](../) · [Certification](../aws-certification/) · [Runbook](RUNBOOK.md)
