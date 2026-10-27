import unittest

from agora_match.catalog import build_catalog


class PlayerIntelligenceTests(unittest.TestCase):
    def test_rating_trace_is_capped_starts_neutral_and_links_events(self):
        game = build_catalog()["games"][0]
        trace = game["match_intelligence"]["rating_timelines"]["N8"]
        self.assertEqual(trace[0], {"minute": 0, "rating": 6.0, "label": "Kick-off", "event_id": None})
        self.assertTrue(all(4.5 <= point["rating"] <= 9.8 for point in trace))
        event_ids = {event["id"] for event in game["events"]}
        self.assertTrue(all(point["event_id"] in event_ids for point in trace[1:]))

    def test_matchup_summaries_keep_denominators_and_explainable_event_rows(self):
        game = build_catalog()["games"][0]
        matchup = next(item for item in game["match_intelligence"]["matchups"] if item["player_id"] == "N8")
        self.assertEqual(matchup["opponent_id"], "E6")
        self.assertEqual(matchup["attempts"], len(matchup["events"]))
        self.assertEqual(matchup["stopped"], 2)
        self.assertTrue(all({"minute", "action", "result"} <= event.keys() for event in matchup["events"]))

    def test_coach_metrics_use_role_peers_and_show_unavailable_decision_time(self):
        game = build_catalog()["games"][0]
        board = game["match_intelligence"]["coach_board"]
        n8 = next(row for row in board["players"] if row["player_id"] == "N8")
        self.assertGreater(n8["max_speed_kmh"], 0)
        self.assertGreater(n8["role_peer_max_speed_kmh"], 0)
        self.assertLess(n8["high_speed_sample_change_pct"], -25)
        self.assertFalse(board["decision_time_available"])
        n3 = next(row for row in board["players"] if row["player_id"] == "N3")
        self.assertEqual(n3["paired_spacing"]["status"], "widened")
        self.assertGreater(n3["paired_spacing"]["distance_after_m"], n3["paired_spacing"]["distance_before_m"])

    def test_referee_analysis_is_out_of_scope(self):
        game = build_catalog()["games"][0]
        self.assertNotIn("referee", game["match_intelligence"])
        self.assertFalse(any(event["team"] == "Officials" for event in game["events"]))
        self.assertTrue(all("referee" not in snapshot for snapshot in game["tracking_snapshots"]))


if __name__ == "__main__":
    unittest.main()
