"""Each test breaks the real tree in one way and checks that the validator notices."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tree  # noqa: E402
import tracks  # noqa: E402

NODES, BOOKS = tree.load()


def problems_after(mutate):
    nodes = copy.deepcopy(NODES)
    mutate(nodes)
    return tree.validate(nodes, BOOKS)


def node(nodes, nid):
    return next(n for n in nodes if n["id"] == nid)


class TreeTests(unittest.TestCase):
    def test_real_tree_is_valid(self):
        self.assertEqual(tree.validate(NODES, BOOKS), [])

    def test_cycle(self):
        p = problems_after(lambda ns: node(ns, "foundations-01-linear-algebra")["requires"].append("prml-14-combining-models"))
        self.assertTrue(any("cycle" in x for x in p), p)

    def test_unknown_prerequisite(self):
        p = problems_after(lambda ns: node(ns, "prml-09-mixtures-em")["requires"].append("prml-99-nope"))
        self.assertTrue(any("unknown node" in x for x in p), p)

    def test_unknown_book(self):
        p = problems_after(lambda ns: node(ns, "prml-09-mixtures-em")["sources"].append("hastie:9"))
        self.assertTrue(any("source" in x for x in p), p)

    def test_duplicate_id(self):
        p = problems_after(lambda ns: ns.append(copy.deepcopy(ns[0])))
        self.assertTrue(any("duplicate" in x for x in p), p)

    def test_done_without_checker(self):
        def mutate(ns):
            n = node(ns, "foundations-01-linear-algebra")
            n["deliverable"] = "math/foundations/zz-not-built"
            n["status"] = "done"
        p = problems_after(mutate)
        self.assertTrue(any("check.py does not exist" in x for x in p), p)

    def test_done_before_prerequisite(self):
        def mutate(ns):
            n = node(ns, "foundations-02-analytic-geometry")
            n["requires"] = ["lean-01-galois-path"]  # a node that is not done
            n["status"] = "done"
        p = problems_after(mutate)
        self.assertTrue(any("prerequisite" in x for x in p), p)

    def test_bad_id_format_and_track(self):
        p = problems_after(lambda ns: node(ns, "prml-09-mixtures-em").update(track="stats"))
        self.assertTrue(any("unknown track" in x for x in p), p)

    def test_missing_acceptance(self):
        p = problems_after(lambda ns: node(ns, "prml-09-mixtures-em").update(accept=[]))
        self.assertTrue(any("acceptance" in x for x in p), p)

    def test_ready_follows_done(self):
        ns = copy.deepcopy(NODES)
        for n in ns:
            n["status"] = "todo"
        ready = [n["id"] for n in tree.ready_nodes(ns)]
        self.assertIn("foundations-01-linear-algebra", ready)
        self.assertNotIn("foundations-02-analytic-geometry", ready)
        node(ns, "foundations-01-linear-algebra")["status"] = "done"
        ready = [n["id"] for n in tree.ready_nodes(ns)]
        self.assertIn("foundations-02-analytic-geometry", ready)

    def test_order_respects_edges(self):
        order = tree.topological_order(NODES)
        pos = {i: k for k, i in enumerate(order)}
        for n in NODES:
            for r in n["requires"]:
                self.assertLess(pos[r], pos[n["id"]], f"{r} must come before {n['id']}")

    def test_unknown_difficulty(self):
        p = problems_after(lambda ns: node(ns, "lowlevel-01-bit-representation").update(difficulty=9))
        self.assertTrue(any("difficulty" in x for x in p), p)

    def test_unknown_kind(self):
        p = problems_after(lambda ns: node(ns, "lowlevel-01-bit-representation").update(kind="boss"))
        self.assertTrue(any("kind" in x for x in p), p)

    def test_deliverable_outside_track_root(self):
        p = problems_after(lambda ns: node(ns, "lowlevel-01-bit-representation")
                           .update(deliverable="math/lowlevel/01-bit-representation"))
        self.assertTrue(any("deliverable" in x for x in p), p)

    def test_unknown_source_is_rejected(self):
        p = problems_after(lambda ns: node(ns, "cloud-01-object-store").update(sources=["nosuch:s3"]))
        self.assertTrue(any("source" in x for x in p), p)

    def test_doc_source_is_accepted(self):
        # docs (specs, manuals) live beside books in the same registry
        self.assertEqual(tree.validate(NODES, BOOKS), [])
        self.assertIn("raft", BOOKS)
        self.assertIn("awsiam", BOOKS)


class GamificationTests(unittest.TestCase):
    def test_exists_earns_no_xp(self):
        self.assertEqual(tracks.node_xp({"status": "exists", "difficulty": 5}), 0)

    def test_capstone_doubles(self):
        skill = tracks.node_xp({"status": "todo", "difficulty": 4})
        boss = tracks.node_xp({"status": "todo", "difficulty": 4, "kind": "capstone"})
        self.assertEqual(boss, 2 * skill)
        self.assertGreater(skill, 0)

    def test_level_increases_with_xp(self):
        self.assertEqual(tracks.level_for(0)[1], "Novice")
        self.assertLess(tracks.level_for(0)[0], tracks.level_for(10_000)[0])

    def test_badge_needs_every_node(self):
        ns = [{"track": "cloud", "status": "todo"}, {"track": "cloud", "status": "done"}]
        self.assertFalse(tracks.badges(ns)["tracks"]["cloud"])
        ns[0]["status"] = "exists"
        self.assertTrue(tracks.badges(ns)["tracks"]["cloud"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
