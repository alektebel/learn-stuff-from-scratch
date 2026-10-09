"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
    "log.py": {
        "last_term": "Return the term of the last entry, or 0 for an empty log.",
        "is_up_to_date": "If the last terms differ, the higher term wins; otherwise the log with at least as many entries wins.",
        "choose_leader": "min() over `eligible` with key (-last_term, -len, name); default None. Highest term first, then longest, then name.",
        "quorum_index": "Walk indexes from 1 up. At each index count votes per distinct Entry; if the most-voted entry has fewer than `majority` votes (or the index is past every log), stop. Return the last index that reached a quorum.",
    },
    "cluster.py": {
        "ReplicaSet.elect": "eligible = names that can_lead; leader = choose_leader(logs, eligible); if a leader was found, bump term and epoch and _catch_up(). Return the leader.",
        "ReplicaSet.write": "Reject if there is no leader or it is down. In sync mode: if fewer than a majority are reachable, return False; append Entry(term, command), _follow each reachable follower, set commit_index = quorum_index(logs, majority) and return whether the new entry committed. In async mode: append and set commit_index to the leader's log length WITHOUT replicating, then return True.",
        "FencedStore.write": "Raise StaleEpoch if `epoch` is older than self.seen_epoch; otherwise remember the new epoch, store the value, and return it.",
    },
}
