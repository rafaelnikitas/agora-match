import unittest

from playerlens.catalog import build_catalog
from playerlens.player_profiles import build_player_profiles


class DemoCatalogTests(unittest.TestCase):
    def test_two_synthetic_matches_have_distinct_live_situations(self):
        catalog = build_catalog()
        games = catalog["games"]
        self.assertTrue(catalog["synthetic"])
        self.assertEqual(len(games), 2)
        self.assertEqual({game["match"]["game_id"] for game in games}, {"northbridge-eastport", "harbor-redvale"})
        self.assertEqual(len(games[0]["players"]), 22)
        self.assertEqual(len(games[1]["players"]), 22)
        self.assertTrue(all(game["match"]["is_synthetic"] for game in games))
        self.assertTrue(all(game["data_provenance"]["source_kind"] == "synthetic" for game in games))
        self.assertEqual(catalog["schema_version"], "1.0")

    def test_set_piece_context_and_recap_follow_selected_match(self):
        by_id = {game["match"]["game_id"]: game for game in build_catalog()["games"]}
        corner = by_id["northbridge-eastport"]
        free_kick = by_id["harbor-redvale"]
        corner_history = next(item for item in corner["insights"] if item["id"] == "history-set-piece")
        free_kick_history = next(item for item in free_kick["insights"] if item["id"] == "history-set-piece")
        self.assertIn("corner", corner_history["evidence"][-1]["value"])
        self.assertIn("direct free-kick", free_kick_history["evidence"][-1]["value"])
        self.assertIn("Northbridge", corner["recap"]["summary"])
        self.assertIn("Harbor City", free_kick["recap"]["summary"])
        self.assertTrue(corner["recap"]["evidence"])
        self.assertTrue(free_kick["recap"]["evidence"])

    def test_static_catalog_is_deterministic(self):
        self.assertEqual(build_catalog(), build_catalog())

    def test_player_profiles_have_repeatable_heatmaps_role_kpis_and_ranks(self):
        game = build_catalog()["games"][0]
        profiles = game["player_profiles"]
        self.assertEqual(len(profiles), 22)
        self.assertEqual(profiles, build_player_profiles(game))
        by_id = {profile["player_id"]: profile for profile in profiles}
        striker = next(player for player in game["players"] if player["role"] == "ST")
        striker_profile = by_id[striker["id"]]
        self.assertIn("penalty_area_touches", striker_profile["kpis"])
        self.assertEqual(len(striker_profile["heat_points"]), 42)
        self.assertTrue(all(1 <= profile["ranks"]["touches"] <= 22 for profile in profiles))
        self.assertEqual(striker_profile["ranks"]["touches"], 1 + sum(p["stats"]["touches"] > striker_profile["stats"]["touches"] for p in profiles))
        for team, score in ((game["match"]["home"], game["match"]["home_score"]), (game["match"]["away"], game["match"]["away_score"])):
            team_goals = sum(profile["stats"]["goals"] for profile in profiles if next(p for p in game["players"] if p["id"] == profile["player_id"])["team"] == team)
            self.assertEqual(team_goals, score)


if __name__ == "__main__":
    unittest.main()
