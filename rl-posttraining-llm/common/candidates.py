"""
candidates.py — a fixed pool of candidate completions per task.

A real GRPO run samples completions token-by-token from an LLM. We can't do that
without a GPU, so for the CPU exercises we give each task a small pool of
pre-written candidate completions: some correct, some wrong-but-plausible, some
malformed. The tabular policy from grpo.py learns a distribution *over this pool*.

This keeps the RL machinery (sampling a group, scoring with the real reward
functions, computing group-relative advantages, updating) completely real while
swapping the token-level generator for a discrete choice you can inspect.

Each candidate is a full tagged completion, scored by common/rewards.py exactly
as a real completion would be.
"""
from __future__ import annotations

from tiny_sql_env import TASKS, Task


# For each task: a list of candidate completions. Index 0..N. The RL agent's job
# is to learn to place probability mass on the correct one(s) using only reward.
CANDIDATES: dict[str, list[str]] = {
    "q1": [
        "<think>count customers where country ES</think><sql>SELECT COUNT(*) FROM customers WHERE country='ES'</sql>",  # correct
        "<think>count all customers</think><sql>SELECT COUNT(*) FROM customers</sql>",  # plausible, wrong
        "<sql>SELECT name FROM customers WHERE country='ES'</sql>",  # wrong shape, no reasoning
        "SELECT COUNT(*) FROM custmers WHERE country='ES'",  # malformed (typo, no tags)
    ],
    "q2": [
        "<think>avg price of electronics</think><sql>SELECT AVG(price) FROM products WHERE category='electronics'</sql>",  # correct
        "<think>avg of all prices</think><sql>SELECT AVG(price) FROM products</sql>",  # plausible, wrong
        "<sql>SELECT price FROM products WHERE category='electronics'</sql>",  # wrong
        "<sql>SELECT AVG(prace) FROM products</sql>",  # malformed column
    ],
    "q3": [
        "<think>products with no orders</think><sql>SELECT name FROM products WHERE id NOT IN (SELECT product_id FROM orders)</sql>",  # correct
        "<think>all product names</think><sql>SELECT name FROM products</sql>",  # plausible, wrong
        "<sql>SELECT name FROM products WHERE id IN (SELECT product_id FROM orders)</sql>",  # inverted logic
        "<sql>SELECT name FROM orders</sql>",  # wrong table
    ],
    "q4": [
        "<think>sum qty for Ana via join</think><sql>SELECT SUM(o.quantity) FROM orders o JOIN customers c ON o.customer_id=c.id WHERE c.name='Ana'</sql>",  # correct
        "<think>sum all quantities</think><sql>SELECT SUM(quantity) FROM orders</sql>",  # plausible, wrong
        "<sql>SELECT quantity FROM orders JOIN customers ON orders.customer_id=customers.id WHERE name='Ana'</sql>",  # wrong agg
        "<sql>SELECT SUM(quantity) FROM orders WHERE name='Ana'</sql>",  # malformed (no join, bad col)
    ],
    "q5": [
        "<think>revenue per category, top 1</think><sql>SELECT p.category FROM orders o JOIN products p ON o.product_id=p.id GROUP BY p.category ORDER BY SUM(p.price*o.quantity) DESC LIMIT 1</sql>",  # correct
        "<think>category by count</think><sql>SELECT p.category FROM orders o JOIN products p ON o.product_id=p.id GROUP BY p.category ORDER BY COUNT(*) DESC LIMIT 1</sql>",  # plausible, wrong metric
        "<sql>SELECT category FROM products ORDER BY price DESC LIMIT 1</sql>",  # ignores quantity/orders
        "<sql>SELECT p.category FROM products p ORDER BY SUM(price) LIMIT 1</sql>",  # malformed
    ],
}

# Index of the intended-correct candidate, for reporting only (never used as a
# training signal — the agent must discover it from reward).
CORRECT_INDEX: dict[str, int] = {q: 0 for q in CANDIDATES}


def task_by_qid(qid: str) -> Task:
    return next(t for t in TASKS if t.qid == qid)
