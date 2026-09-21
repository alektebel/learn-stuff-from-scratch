import pathlib, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2] / "week-09" / "database-engine"

BUGS = [
 (1, "pager.py", "delete renumbers the surviving slots",
  '''        offset, _ = SLOT.unpack_from(self.data, HEADER.size + slot * SLOT.size)
        SLOT.pack_into(self.data, HEADER.size + slot * SLOT.size, offset, 0)
        self.dirty = True''',
  '''        rest = [self.read(s) for s in range(slot + 1, slots)]
        for i, record in enumerate(rest):
            SLOT.pack_into(self.data, HEADER.size + (slot + i) * SLOT.size,
                           *SLOT.unpack_from(self.data,
                                             HEADER.size + (slot + i + 1) * SLOT.size))
        self._set_header(page_type, slots - 1, start - SLOT.size, end)'''),

 (1, "pager.py", "free_space forgets the slot directory entry",
  "        return max(0, end - start - SLOT.size)",
  "        return max(0, end - start)"),

 (2, "pager.py", "eviction ignores the pin count",
  "        victims = sorted((used, pid) for pid, used in self.access.items()\n"
  "                         if self.frames[pid].pins == 0)",
  "        victims = sorted((used, pid) for pid, used in self.access.items())"),

 (2, "pager.py", "a hit does not refresh recency",
  '''        if page_id in self.frames:
            self.stats["hits"] += 1
            self.access[page_id] = self.clock
            return self.frames[page_id]''',
  '''        if page_id in self.frames:
            self.stats["hits"] += 1
            return self.frames[page_id]'''),

 (3, "btree.py", "a leaf split MOVES the separator instead of copying it",
  '''            separator = node.keys[middle]                     # COPY up
            sibling.keys = node.keys[middle:]
            sibling.values = node.values[middle:]''',
  '''            separator = node.keys[middle]
            sibling.keys = node.keys[middle + 1:]
            sibling.values = node.values[middle + 1:]'''),

 (4, "btree.py", "a split forgets to relink the leaf chain",
  "            sibling.next_leaf = node.next_leaf                # keep the chain\n"
  "            node.next_leaf = sibling.page_id",
  "            sibling.next_leaf = node.next_leaf"),

 (5, "btree.py", "delete never rebalances",
  "        if path and len(leaf.keys) < (self.order + 1) // 2:\n"
  "            self._rebalance(leaf, path)",
  "        if False:\n            self._rebalance(leaf, path)"),

 (6, "wal.py", "commit forces the data pages too",
  '''        record = self.log.append(COMMIT, txn=txn, prev_lsn=self.active[txn])
        self.log.flush(record.lsn)
        del self.active[txn]''',
  '''        record = self.log.append(COMMIT, txn=txn, prev_lsn=self.active[txn])
        self.log.flush(record.lsn)
        for page_id in list(self.pages):
            self.flush_page(page_id)
        del self.active[txn]'''),

 (7, "wal.py", "redo skips the losers",
  '''        for record in log[start:]:
            if record.kind not in (UPDATE, CLR):
                continue''',
  '''        for record in log[start:]:
            if record.kind not in (UPDATE, CLR):
                continue
            if record.txn in losers:
                continue'''),

 (8, "wal.py", "the write-ahead rule, violated",
  '        self.log.flush(self.page_lsn.get(page_id, 0))       # WRITE-AHEAD RULE',
  '        pass                                                # rule skipped'),

 (9, "mvcc.py", "visibility ignores the concurrent-transaction set",
  "        if xid >= self.xmax or xid in self.active:\n            return False",
  "        if xid >= self.xmax:\n            return False"),

 (10, "mvcc.py", "the write path always checks the BEGIN snapshot",
  "        snapshot = self._snapshot_for(txn)\n        for version in reversed(chain):",
  "        snapshot = txn.snapshot\n        for version in reversed(chain):"),

 (11, "mvcc.py", "vacuum uses the newest transaction as its horizon",
  "        horizon = self.oldest_snapshot()",
  "        horizon = self.next_xid"),

 (12, "sql.py", "keywords classified before the longest match",
  '''    ("IDENT",   r"[A-Za-z_][A-Za-z0-9_]*"),''',
  '''    ("KW",      r"(?i:SELECT|FROM|WHERE|COUNT)"),
    ("IDENT",   r"[A-Za-z_][A-Za-z0-9_]*"),'''),

 (13, "sql.py", "AND and OR given the same precedence",
  '    "OR": (1, False), "AND": (2, False),',
  '    "OR": (1, False), "AND": (1, False),'),

 (14, "executor.py", "Limit materialises instead of stopping the pull",
  '''        if self.limit is not None and self.emitted >= self.limit:
            return None                  # stop pulling — the pipeline halts here''',
  '''        if self.limit is not None and self.emitted >= self.limit:
            while self.children[0].next() is not None:
                pass
            return None'''),

 (15, "executor.py", "the hash join scans its build side",
  '''            matches = self.table.get(row.get(self.probe_key), [])''',
  '''            matches = [b for b in self.build_rows
                       if (self.rows_in := self.rows_in + 1)
                       and b.get(self.build_key) == row.get(self.probe_key)]'''),

 (16, "planner.py", "index cost forgets that heap fetches are random",
  "            + matching * RANDOM_PAGE_COST                   # one fetch per row",
  "            + matching * SEQ_PAGE_COST                      # one fetch per row"),

 (17, "planner.py", "predicates float above the join instead of onto the scan",
  '''        node = SeqScan(table.name, table.rows, alias)
        if predicates:
            node = Filter(node, _evaluate(_and_all(predicates)),
                          repr(_and_all(predicates)))
        return node''',
  '''        return SeqScan(table.name, table.rows, alias)'''),

 (18, "database.py", "rollback leaves the inserted row in the heap",
  '''        for table_name, row in reversed(self.inserted):''',
  '''        for table_name, row in []:'''),
]

failures = []
for step, filename, label, old, new in BUGS:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "s"
        shutil.copytree(ROOT / "solutions", work,
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(ROOT / "check.py", work / "check.py")
        target = work / filename
        text = target.read_text()
        if old not in text:
            failures.append(f"[{step}] {label}: PATCH DID NOT APPLY")
            print(f"  step {step:>2}  PATCH-FAIL {label}")
            continue
        target.write_text(text.replace(old, new, 1))
        result = subprocess.run([sys.executable, "check.py", str(step)],
                                cwd=work, capture_output=True, text=True,
                                timeout=300)
        caught = "✗" in result.stdout
        print(f"  step {step:>2}  {'caught' if caught else 'MISSED':<7} {label}")
        if not caught:
            failures.append(f"[{step}] {label}\n{result.stdout}")

print()
if failures:
    print("PROBLEMS:")
    for f in failures:
        print(" ", f)
    sys.exit(1)
print(f"all {len(BUGS)} injected bugs were caught")
