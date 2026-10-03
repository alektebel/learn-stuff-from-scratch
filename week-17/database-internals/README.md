# Database Internals — the deep half

**SKELETON.** Signatures and the checker contract are in place; nothing is
implemented and no checks are written. See [`../../TODO.md`](../../TODO.md) §14.

Everything here builds on [`../../week-09/database-engine/`](../../week-09/database-engine/).
Finish that first — the measurements here are all *against* its Volcano executor
and its cost planner, and without a baseline they measure nothing.

## The result worth the whole directory

> **Query optimisers do not fail because their cost models are wrong. They fail
> because the inputs are.**

Leis et al., *"How Good Are Query Optimizers, Really?"* (VLDB 2015). Cardinality
estimation error compounds roughly **multiplicatively** with each join, so a
four-way join can be off by orders of magnitude — and the planner then picks a
bad plan **correctly**, from bad numbers.

`estimation.py` reproduces it. It is three afternoons of work and it changes how
you read every `EXPLAIN` output for the rest of your life.

## What you build

| File | Mechanism | Stubs |
|---|---|---|
| `estimation.py` | Histograms, the independence assumption, and error compounding | 8 |
| `sketches.py` | HyperLogLog, Count-Min, reservoir sampling — what statistics *are* | 7 |
| `columnar.py` | Column layout, RLE / dictionary / frame-of-reference, late materialization | 8 |
| `vectorized.py` | Batch-at-a-time against the Volcano model you already built | 7 |
| `joins.py` | Sort-merge, Grace hash, radix partitioning — and spilling | 7 |
| `concurrency.py` | 2PL vs OCC vs MVCC under swept contention | 8 |

```bash
cd week-17/database-internals
python3 check.py          # 11 graded checks — NOT YET WRITTEN
```

No `solutions/`, on purpose.

## Five things you will be able to say afterwards

1. **Why your `EXPLAIN` lies.** Not the cost model — the row estimates, and how
   fast they decay across joins.
2. **What a "statistic" actually is.** Not a scan: a HyperLogLog register array
   and a Count-Min table, each with a *provable* error bound rather than a hoped
   one. Count-Min's guarantee is one-sided, and that asymmetry is why it is
   usable at all.
3. **Where the Volcano model's time goes.** One virtual call per tuple per
   operator. Batch a thousand and measure — then read Neumann (VLDB 2011) for
   the other answer, which is to compile the query rather than interpret it.
4. **What happens when the build side does not fit.** Grace hash join, and its
   `3(|R|+|S|)` I/O cost. Then skew, which breaks it, because one partition is
   still too big.
5. **Which concurrency control to pick, as a crossover rather than an opinion.**
   OCC beats 2PL at low contention and loses at high; MVCC readers never block
   and write skew still gets through. Sweep the conflict rate and name the
   number where they cross.

## The thing to hold on to

Every check here is a **crossover or a curve**, not a single measurement. That
is deliberate: at one contention level, one selectivity or one batch size, every
one of these techniques looks either obviously right or obviously pointless. The
content is entirely in where they change places.

## Sources

- Leis, Gubichev, Mirchev, Boncz, Kemper & Neumann, **"How Good Are Query
  Optimizers, Really?"**, VLDB 2015 — `estimation.py`, and the reason this
  directory exists.
- Flajolet, Fusy, Gandouet & Meunier, **"HyperLogLog"**, AofA 2007; Cormode &
  Muthukrishnan, **"An Improved Data Stream Summary: the Count-Min Sketch"**,
  J. Algorithms 2005 — `sketches.py`.
- Stonebraker et al., **"C-Store: A Column-oriented DBMS"**, VLDB 2005;
  Abadi, Madden & Ferreira, **"Integrating Compression and Execution in
  Column-Oriented Database Systems"**, SIGMOD 2006 — `columnar.py`.
- Boncz, Zukowski & Nes, **"MonetDB/X100: Hyper-Pipelining Query Execution"**,
  CIDR 2005; Neumann, **"Efficiently Compiling Efficient Query Plans for Modern
  Hardware"**, VLDB 2011 — `vectorized.py`, and its alternative.
- Kitsuregawa, Tanaka & Moto-oka, **"Application of Hash to Data Base Machine
  and Its Architecture"**, 1983 — the Grace hash join; and Manegold, Boncz &
  Kersten on radix partitioning.
- Kung & Robinson, **"On Optimistic Methods for Concurrency Control"**, TODS
  1981; Cahill, Röhm & Fekete, **"Serializable Isolation for Snapshot
  Databases"**, SIGMOD 2008 — `concurrency.py`.
- Petrov, **Database Internals**, 2019 — the book that covers most of this in
  one place, if you want a narrative rather than eight papers.

---

[← Week 17](../) · [Database engine](../../week-09/database-engine/) · [Sources](../../REFERENCES.md)
