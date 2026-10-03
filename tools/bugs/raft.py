import pathlib, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2] / "week-10" / "raft"
BUGS = [
 (1, "log.py", "the consistency check always accepts",
  "        if index > len(self.entries):\n            return False                 # I am missing entries\n        return self.entries[index - 1].term == term",
  "        if index > len(self.entries):\n            return False\n        return True"),
 (2, "log.py", "truncates on every append, not only on a conflict",
  "                if self.entries[index - 1].term != entry.term:",
  "                if True:"),
 (2, "log.py", "up-to-date compares length before term",
  "        if other_term != self.last_term:\n            return other_term > self.last_term\n        return other_index >= self.last_index",
  "        if other_index != self.last_index:\n            return other_index > self.last_index\n        return other_term >= self.last_term"),
 (2, "log.py", "commit index can move backwards",
  "        if index <= self.commit_index:\n            return []",
  "        if index == self.commit_index:\n            return []"),
 (3, "election.py", "a server may vote twice in one term",
  "        if self.voted_for not in (None, request.candidate):",
  "        if False:"),
 (3, "election.py", "no election restriction",
  "        if not self.log.is_at_least_as_up_to_date_as(request.last_log_term,\n                                                     request.last_log_index):",
  "        if False:"),
 (3, "election.py", "a higher term does not force a step down",
  '''        if term > self.current_term:
            self.current_term = term
            self.voted_for = None        # a NEW term, so a fresh vote''',
  '''        if term > self.current_term:
            self.current_term = term
            self.voted_for = self.voted_for'''),
 (4, "replication.py", "matchIndex advanced on send, not on reply",
  "        self.stats[\"appends_sent\"] += 1\n        return (prev_index, self.log.term_at(prev_index),",
  "        self.stats[\"appends_sent\"] += 1\n        self.match_index[peer] = self.log.last_index\n        return (prev_index, self.log.term_at(prev_index),"),
 (5, "replication.py", "the naive commit rule — majority only",
  '''            if self.log.term_at(index) != self.term:
                # A majority has it, and it is STILL NOT SAFE to commit.
                self.stats["commit_blocked_by_term"] += 1
                continue''',
  "            pass"),
 (5, "replication.py", "no no-op on election",
  "    def append_noop(self) -> int:",
  "    def append_noop(self) -> int:\n        return self.log.last_index\n    def _unused(self) -> int:"),
 (6, "cluster.py", "partitions not enforced on the wire",
  "        for group in self.partitions:\n            if name in group:\n                return {n for n in group if n not in self.crashed}\n        return {name}",
  "        return {n for n in self.names if n not in self.crashed}"),
 (7, "cluster.py", "safety check never looks at other servers",
  "            for name, entries in self.applied.items():",
  "            for name, entries in list(self.applied.items())[:1]:"),
]
failures = []
for step, filename, label, old, new in BUGS:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "s"
        shutil.copytree(ROOT / "solutions", work, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(ROOT / "check.py", work / "check.py")
        target = work / filename
        text = target.read_text()
        if old not in text:
            print(f"  step {step:>2}  PATCH-FAIL {label}")
            failures.append(f"[{step}] {label}: patch did not apply"); continue
        target.write_text(text.replace(old, new, 1))
        steps = str(step) if step != 7 else "6 7"
        r = subprocess.run([sys.executable, "check.py"] + steps.split(), cwd=work,
                           capture_output=True, text=True, timeout=600)
        caught = "✗" in r.stdout
        print(f"  step {step:>2}  {'caught' if caught else 'MISSED':<7} {label}")
        if not caught: failures.append(f"[{step}] {label}\n{r.stdout[:300]}")
print()
if failures:
    print("PROBLEMS:")
    for f in failures: print(" ", f)
    sys.exit(1)
print(f"all {len(BUGS)} injected bugs were caught")
