import unittest

from agora_match.insights import InsightCoordinator, HistoricalContextAgent, LivePatternAgent, PlayerLoadAgent, ShapeAgent
from agora_match.synthetic import build_demo_state


class SyntheticStateTests(unittest.TestCase):
    def test_fixture_is_reproducible_and_synthetic(self):
        self.assertEqual(build_demo_state(), build_demo_state())
        self.assertTrue(build_demo_state()["match"]["is_synthetic"])
        self.assertEqual(len(build_demo_state()["players"]), 22)

    def test_corner_context_uses_recent_match_aggregates(self):
        items = HistoricalContextAgent().detect(build_demo_state())
        self.assertEqual(len(items), 1)
        self.assertIn("3 of its last 7", items[0].fan_summary)
        self.assertIn("2/7", items[0].explorer_summary)
        self.assertIn("small sample", items[0].caveat)

    def test_tactics_detector_finds_cross_and_switch_patterns(self):
        items = LivePatternAgent().detect(build_demo_state())
        by_id = {item.id: item for item in items}
        self.assertIn("pattern-crosses", by_id)
        self.assertIn("8 of the last 8", by_id["pattern-crosses"].title)
        self.assertIn("pattern-switch", by_id)
        self.assertIn("4/6", by_id["pattern-switch"].explorer_summary)

    def test_load_signal_is_qualified_not_a_diagnosis(self):
        items = PlayerLoadAgent().detect(build_demo_state())
        self.assertEqual(len(items), 1)
        self.assertIn("not a diagnosis", items[0].caveat)
        self.assertIn("9", items[0].explorer_summary)
        self.assertIn("4", items[0].explorer_summary)

    def test_shape_signal_describes_space_not_player_blame(self):
        items = ShapeAgent().detect(build_demo_state())
        self.assertEqual(len(items), 1)
        self.assertIn("open space", items[0].caveat)
        self.assertIn("not individual marking responsibility", items[0].caveat)

    def test_coordinator_returns_ranked_evidence_backed_candidates(self):
        items = InsightCoordinator().collect(build_demo_state())
        self.assertGreaterEqual(len(items), 4)
        self.assertEqual([item["rank"] for item in items], list(range(1, len(items) + 1)))
        self.assertTrue(all(item["evidence"] for item in items))
        self.assertEqual(items[0]["id"], "history-set-piece")


if __name__ == "__main__":
    unittest.main()
