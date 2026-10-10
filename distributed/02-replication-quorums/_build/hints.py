"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "network.py": {
  "Network._connected": "Two nodes can talk when there is no partition, or when some group in `self._groups` contains BOTH ids. Return a bool.",
  "Network.send": "Drop the message (bump `self.dropped`) if `_connected(src, dst)` is False, and again with probability `self.drop`. Otherwise draw `delay = self.rng.randint(min_delay, max_delay)` when none is given, then push `(self.now + delay, self._seq, src, dst, payload)` onto the heap with `heapq.heappush`, bumping `self.sent` and `self._seq`.",
  "Network.deliver_due": "Pop from the heap while the earliest `deliver_at <= self.now`, collecting deliveries; then call `receive(src, payload)` on each destination that is registered. The heap's second field (sequence) keeps equal-time messages in send order.",
  "Network.step": "Advance the logical clock one tick (`self.now += 1`) and then deliver everything now due.",
  "Network.flush": "While the queue is non-empty, jump `self.now` to the earliest `deliver_at` and deliver due messages. This is the deterministic 'wait for the network to settle'.",
 },
 "replica.py": {
  "Replica.append": "Refuse unless `entry['index']` is exactly `len(self.log)` (that catches both gaps and duplicates). Then append a COPY of the entry and set `self.applied[key] = (version, value)`. Return the bool.",
  "Replica.truncate": "Ignore a negative index. Drop `self.log[index:]`, then rebuild `self.applied` from scratch by walking the remaining entries in order so a value from a removed write disappears.",
  "Replica.value": "Return `self.applied.get(key)`, a `(version, value)` tuple or None.",
  "Replica.receive": "A `paused` or `crashed` replica stays silent. Otherwise bump `self.received`, then dispatch: an `append` message calls `self.append(msg['entry'])`, a `truncate` message calls `self.truncate(msg['index'])`.",
 },
 "quorum.py": {
  "read_write_overlap": "Two subsets of N elements can be disjoint only when their sizes sum to at most N. Return `R + W > N`.",
  "ReplicatedLog.holders": "Count the replicas whose `get(index)` is not None: how many reached that log position.",
  "ReplicatedLog.commit_index": "Start at -1; while `self.holders(index + 1) >= self.W` advance. That is the longest prefix present on a write quorum.",
  "ReplicatedLog.write": "Flush the network, then use `index = len(leader.log)` as the version. Append locally, send an `append` message to every OTHER ACTIVE replica, flush, and if `self.holders(index) >= self.W` return the version. Otherwise roll back: truncate index on every replica that has it, flush, and raise `NotEnoughReplicas` -- a minority must not fork the log.",
  "ReplicatedLog.read": "Flush the network. Query `from_` if given else the first R names. Keep the `(version, value)` with the HIGHEST version and return its value (None if no replica holds the key).",
  "ReplicatedLog.catch_up": "Flush, then for every active non-leader replica send the leader's entries it is missing one at a time, flushing after each so the indices stay contiguous. Stop on a replica that did not advance (it is unreachable). Return the number of entries sent.",
 },
}
