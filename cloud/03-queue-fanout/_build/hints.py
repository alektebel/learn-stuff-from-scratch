"""Hints for .claude/skills/graded-module/scripts/make_templates.py."""
HINTS = {
 "sqs.py": {
  "Queue.send": "Create a message with a fresh deterministic id, visible_at = clock.now + delay_seconds, and append it to the queue. Return the id.",
  "Queue.receive": "Walk messages in order: skip any still in flight (now < visible_at); if its receive_count already reached max_receives, dispose of it (DLQ or discard) instead of delivering; otherwise increment receive_count, issue a NEW receipt handle, set visible_at = now + timeout, and collect it.",
  "Queue.ack": "Delete the message whose CURRENT receipt_handle equals the one passed in. Return True. A stale handle (from a delivery that has been superseded) must return False -- match the handle, never the message id.",
  "Queue.change_visibility": "Reset the current delivery's visible_at to clock.now + timeout; return False for a handle that is not current.",
  "Queue._dispose": "Retire a message that used up its receives: remove it from this queue, then send it to dead_letter_queue with source_receive_count if one is set, else count it discarded.",
  "Queue.size": "Return how many messages the queue still owns (visible and in flight).",
  "Queue.visible": "Return the messages a receive() right now would hand out: now >= visible_at.",
  "Consumer.poll": "Receive up to max_messages, call the handler once per delivery, and ack each unless the caller passed ack=False (which simulates a crash after processing).",
  "IdempotentConsumer.poll": "Same as Consumer.poll, but keep a set of message ids already applied: a redelivered id is counted as a duplicate, skipped, and acked without running the handler again.",
 },
 "sns.py": {
  "Webhook.deliver": "Record one delivery: append {\"body\": body, \"attributes\": a copy of attributes} to self.deliveries.",
  "Subscription.matches": "With no filter policy, everything matches. Otherwise every policy attribute must be present on the message and its value must be in the allowed list.",
  "Subscription.deliver": "Queue subscriber: enqueue a durable copy with the attributes. Webhook subscriber: call target.deliver. Copy the attributes so subscribers cannot share mutable state.",
  "Topic.subscribe_queue": "Add a subscription of kind queue with the given filter policy and return its id.",
  "Topic.subscribe_webhook": "Add a subscription of kind webhook with the given filter policy and return its id.",
  "Topic.publish": "Deliver one copy to EVERY subscription whose filter matches; count published and delivered; return the list of subscription ids reached.",
  "Topic.subscribers": "Return the ids of the subscriptions currently attached.",
 },
}
