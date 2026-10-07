"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
 ("evict without write-back", "pager.py", "                self._write_to_disk(victim, bytes(data))  # write back before dropping\n", "", "2"),
 ("split by count", "btree.py", "            i = _split_point([4 + len(k) + len(v) for k, v in entries])", "            i = len(entries) // 2", "6"),
 ("no CRC check", "wal.py", "        if zlib.crc32(payload) != crc:\n            return  # corrupt or torn inside the payload\n", "", "7"),
 ("replay uncommitted", "wal.py", "        elif kind == \"commit\":\n            out.extend(pending.pop(tx, []))", "        elif kind == \"commit\":\n            pass\n    for ops in pending.values():\n        out.extend(ops)\n    if False:\n        pass", "9"),
 ("no first-committer-wins", "mvcc.py", "                if s._last_commit_ts(key) > self.start_ts:\n                    self._finish(\"aborted\")\n                    raise SerializationFailure(f\"write-write", "                if False:\n                    self._finish(\"aborted\")\n                    raise SerializationFailure(f\"write-write", "12"),
 ("no range validation", "mvcc.py", "                    if lo <= key < hi and s._last_commit_ts(key) > self.start_ts:", "                    if False:", "13"),
 ("async index applied immediately", "table.py", "    def _index_add(self, t: Txn, row: dict) -> None:\n        for col in self.indexes:\n            if col in row:\n                self.queue.append", "    def _index_add(self, t: Txn, row: dict) -> None:\n        return Table._index_add(self, t, row)\n        for col in self.indexes:\n            if col in row:\n                self.queue.append", "17"),
]
