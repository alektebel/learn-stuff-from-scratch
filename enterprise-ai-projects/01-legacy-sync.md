# 1 — Bi-directional legacy sync engine

## What it is

Two systems of record — your SaaS and a customer's on-prem SQL database — that both
accept writes to the same logical entities, kept in sync, with a defined answer for what
happens when both change the same row before either has seen the other's change.

The word doing all the work is **bi-directional**. One-directional sync is a solved
problem you can buy. Bi-directional sync is a distributed systems problem with no
general solution, and the whole project is choosing which specific, restricted version
of it you are going to solve.

## What it actually demonstrates

Not "you can bridge modern AI with messy enterprise data" — there is no AI in this
project and there does not need to be. What it demonstrates is that you know
**conflict resolution is a product decision, not a technical one**, and that you are
willing to write down the resolution rule in terms a customer's operations lead can
argue with.

Last-write-wins is a rule. It is also a rule that silently destroys data, and the
version of this project worth building is the one where you can say exactly which
data, how often, and what the customer sees when it happens.

## The substrate

Run a real legacy database. Two credible options:

```bash
# Oracle 23c Free — the successor to XE. Use this, not gvenzl/oracle-xe,
# which the same author deprecated.
docker run -d -p 1521:1521 -e ORACLE_PASSWORD=secret \
  -v oracle-data:/opt/oracle/oradata gvenzl/oracle-free

# or SQL Server
docker run -d -p 1433:1433 -e ACCEPT_EULA=Y -e MSSQL_SA_PASSWORD=Str0ng!Passw0rd \
  mcr.microsoft.com/mssql/server:2022-latest
```

Then make the schema hostile, because a schema you designed this morning is not the
thing you are claiming to handle. Give it, at minimum:

- a composite primary key with a meaningless surrogate alongside it, both in use;
- dates stored as `VARCHAR2(8)` in `YYYYMMDD`, with some rows in `DDMMYYYY`;
- soft deletes via an `ACTIVE_FLG CHAR(1)` that is sometimes `'N'`, sometimes `'0'`,
  sometimes `NULL`;
- a trigger that rewrites a column on update, so your writes come back different from
  what you sent;
- `NUMBER` columns with no precision, holding values that lose digits in a float.

Every one of those is ordinary in a system of that age. If your sync engine cannot
survive them, it does not do what the project claims.

For change capture, use **Debezium**. Its Oracle connector reads redo logs through
**LogMiner**, which needs no extra licence; the XStream adapter is lower latency but
requires a GoldenGate licence you do not have. You will have to enable supplemental
logging, which is exactly the kind of "please ask your DBA" step that makes this
project realistic.

## The decisions

**Conflict resolution rule.** The real options, with costs:

| Rule | Cost |
|---|---|
| Last-write-wins on a timestamp | Clock skew between two machines silently decides which customer's edit survives. Requires trusting a clock you do not control. |
| Version vectors / per-replica counters | Correct detection, but you must *store* the vectors and *present* conflicts to somebody. Now you have built a UI. |
| CRDTs | Convergence by construction, no conflict UI. But you must express the business entity as a CRDT, and "customer record" mostly is not one — LWW-register per field is usually what you end up with, which is LWW again with better bookkeeping. |
| Designate a field-level owner | Simple, explainable, and the one that most often ships. Cost: you must get the customer to agree on ownership per field, which is a meeting, not a commit. |

Pick one and write down the case where it loses data. If you cannot construct that case,
you do not understand the rule you picked.

**Change capture: CDC or polling.** CDC (Debezium) gets you ordering and deletes; it also
gets you a Kafka dependency, a privileged database account, and a DBA conversation.
Polling on `LAST_MODIFIED` is deployable in an afternoon and cannot see deletes, misses
updates within the polling window, and breaks on rows whose `LAST_MODIFIED` the trigger
does not update. Build polling first *because* you will hit its limits and then you will
know why CDC exists.

**Where the sync state lives.** Not in either system of record. A third store holding
the mapping (their key ↔ your key), the last-seen version on each side, and the
conflict log. Cost: a third thing to operate, back up, and reconcile when *it* is wrong.

**Loop suppression.** Your write to their database produces a CDC event that your own
consumer sees. Without a marker distinguishing "originated here", you have an infinite
loop that will look like a performance problem for about an hour before you find it.

## Where it breaks

The customer restores their database from a backup taken three days ago. Every version
number you were tracking is now in the past, every mapping still points at rows that no
longer have the values you think they do, and nothing errors.

Build for that case explicitly — a full-reconciliation mode that compares state rather
than replaying changes — or state in your README that you do not handle it. Both are
acceptable; not knowing is not.

## Resources

- Debezium Oracle connector documentation — <https://debezium.io/documentation/reference/stable/connectors/oracle.html> `[v]` — read the LogMiner vs XStream section and the supplemental-logging prerequisites before writing anything.
- Shapiro, Preguiça, Baquero, Zawirski, *Conflict-free Replicated Data Types*, INRIA RR-7686 (2011), also SSS 2011. The reference for what convergence without coordination costs you.
- Terry et al., *Managing Update Conflicts in Bayou*, SOSP 1995. The original design where application-specific merge procedures and a conflict UI are first-class; closest in spirit to what this project needs.
- Kleppmann, *Designing Data-Intensive Applications*, ch. 5 (replication) and ch. 11 (stream processing). Chapter 5's "handling write conflicts" section is the shortest correct treatment of this problem in print.
- `dynamo-paper/` in this repo — vector clocks and sibling reconciliation, implemented. If version vectors are your chosen rule, you have already built the mechanism.
