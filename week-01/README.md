# Week 1 · Aug 24–Aug 30, 2026

> **AWS, from its mechanisms up.**
> Start where the leverage is. Eight services, each reduced to the one mechanism that makes it behave the way it does — and then a meter and a price sheet on top, so every later week has a cost model to reason with.

## Finish this week

| Project | Hours | Track |
|---|---|---|
| [`aws-from-scratch/`](aws-from-scratch/) | 42 | core · spine |

**42 block hours**, plus the daily Lean slot (~8.4 h) = 50 h on the full track.

**~2 h on the live system this week** — see [`../LIVE.md`](../LIVE.md). Starting now is the point: ninety days of uptime takes ninety days.

## What to do, in order

1. `iam.py` **first, always.** The checker enforces it and everything else in the directory is gated by it. Learn the three-line evaluation rule before anything.
2. Then `s3.py`, `sqs.py`, `dynamodb.py` — checks 1 to 9. Flat keys, the visibility-timeout limit case, and the partition key that decides everything.
3. Then `lambda_svc.py`, `sns.py`, `kms.py`, `vpc.py`, `capstone.py`.
4. Finish with the billing layer: `pricing.py`, `billing.py`, `optimize.py`. **Predict the provisioned-vs-on-demand DynamoDB crossover before running `optimize.py`.** Most people are off by an order of magnitude.
5. **Build `drill.py` on day one, then run it every day.** It is a skeleton — a scheduler and about twenty cards is an hour's work, and you write the cards from the quotas and defaults you meet this week. Spaced repetition started in August is the difference between passing an exam in December and not; started in November it is worth nothing. Lives in [`../week-12/aws-certification/`](../week-12/aws-certification/).
6. **Get *anything* deployed this week** — see [`../LIVE.md`](../LIVE.md). A URL that returns `{"reply": "hello"}`, a health endpoint, one dashboard, one alarm you have tested by tripping it, and **the start date written down**. The model does not matter yet; what has to start is the clock. Your own transformer replaces the placeholder in week 3.
7. **If your real AWS account is live, do Phase 0 of [`../week-12/aws-deploy/RUNBOOK.md`](../week-12/aws-deploy/RUNBOOK.md) before you touch it** — root MFA, a tested budget alarm, IAM Identity Center instead of IAM users, no long-lived access keys. Nothing this week needs an account, but you will be tempted to poke at one, and the alarm should predate the temptation.

## Done means

- `week-01/aws-from-scratch/` prints 24/24.
- You can state IAM's evaluation rule from memory and say why policy order cannot change the answer.
- You can explain why a hot partition key throttles a table that looks idle.
- The drill is running and has a streak.

## Every day

1. **Implement** — longest block, first thing, hardest unfinished stub.
2. **Predict, then run** — write the number you expect before you run the demo. A surprise is a gap a passing test did not reveal.
3. **Make it green** — `python3 check.py` where one exists.
4. **Log, ten minutes** — one entry in [`../journal/`](../journal/).

**Sunday is regression day. No new code.** Re-run every checker built so far and write two sentences on what you can now re-derive that you could not last Sunday.

```bash
python3 ../progress.py --week 1
python3 ../progress.py --checks
```

[Roadmap](../ROADMAP.md) · [Sources](../REFERENCES.md#week-1) · [Week 2 →](../week-02/)
