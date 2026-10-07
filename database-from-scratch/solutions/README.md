# Database From Scratch — Solutions

Complete versions of every template in the parent directory. Pure Python 3, no dependencies.
Run them from inside this directory (they import each other by name):

```bash
python3 pager.py       # 10 pages through a 4-page cache: write-backs and hits
python3 btree.py       # 50k keys: height 3, one lookup reads 3 pages
python3 wal.py         # crash with an uncommitted transaction and a torn tail; recover
python3 mvcc.py        # the lost update at each isolation level
python3 anomalies.py   # the anomaly x isolation-level matrix
python3 table.py       # index vs full scan; atomic vs async index after an update
```

Expected matrix (`anomalies.py`):

```
                     READ_UNCOMMITTED  READ_COMMITTED  SNAPSHOT  SERIALIZABLE
dirty read                 OCCURS            -             -          -
non-repeatable read        OCCURS          OCCURS          -          -
phantom                    OCCURS          OCCURS          -          -
lost update                OCCURS          OCCURS          -          -
write skew                 OCCURS          OCCURS        OCCURS       -
```

Lost update is prevented at SNAPSHOT by first-committer-wins, not by the snapshot itself.
Real READ COMMITTED engines often prevent `UPDATE x = x + 1` by re-reading the row under
a lock; the read-modify-write in application code shown here is not protected.
