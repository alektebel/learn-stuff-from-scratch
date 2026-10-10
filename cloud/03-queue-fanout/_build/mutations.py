"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py."""
MUTATIONS = [
    # sqs.py -----------------------------------------------------------------
    ("visibility timeout never lapses",
     "sqs.py",
     "            message.visible_at = now + timeout\n",
     "            message.visible_at = now + 10 ** 9\n",
     "1"),
    ("change_visibility does not extend the lease",
     "sqs.py",
     "                message.visible_at = self.clock.now + timeout\n",
     "                message.visible_at = self.clock.now\n",
     "1"),
    ("ack ignores the receipt handle (stale ack deletes)",
     "sqs.py",
     "            if message.receipt_handle is not None and message.receipt_handle == receipt_handle:\n",
     "            if message.receipt_handle is not None:\n",
     "2"),
    ("delayed message is visible immediately",
     "sqs.py",
     "            visible_at=now + delay_seconds,\n",
     "            visible_at=now,\n",
     "3"),
    ("no dead-letter after max receives",
     "sqs.py",
     "            if self.max_receives is not None and message.receive_count >= self.max_receives:\n",
     "            if False:\n",
     "4"),
    ("idempotent consumer reprocesses the duplicate",
     "sqs.py",
     "            if message.id in self.seen:\n"
     "                self.duplicates += 1\n"
     "            else:\n"
     "                self.seen.add(message.id)\n"
     "                self.handler(message)\n"
     "                self.processed += 1\n",
     "            self.handler(message)\n"
     "            self.processed += 1\n",
     "6"),
    # sns.py -----------------------------------------------------------------
    ("fanout delivers only to the first subscriber",
     "sns.py",
     "        for subscription in self._subscriptions:\n",
     "        for subscription in self._subscriptions[:1]:\n",
     "5"),
    ("webhook delivery dropped",
     "sns.py",
     "            self.target.deliver(body, attributes)\n",
     "            pass\n",
     "5"),
    ("subscription filter policy ignored",
     "sns.py",
     "        if not self.filter_policy:\n"
     "            return True\n"
     "        attributes = attributes or {}\n"
     "        for name, allowed in self.filter_policy.items():\n"
     "            if attributes.get(name) not in allowed:\n"
     "                return False\n"
     "        return True\n",
     "        return True\n",
     "7"),
]
