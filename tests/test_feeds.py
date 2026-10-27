import unittest

from agora_match.catalog import build_catalog
from agora_match.feeds import build_live_feed_files


class SyntheticFeedTests(unittest.TestCase):
    def test_all_feeds_are_reproducible_and_marked_synthetic(self):
        catalog = build_catalog()
        first = build_live_feed_files(catalog)
        self.assertEqual(first, build_live_feed_files(catalog))
        self.assertEqual(set(first), {"team_history.json", "player_history.json", "live_events.json", "live_tactical_metrics.json", "live_wearables.json"})
        for feed in first.values():
            self.assertEqual(feed["data_mode"], "synthetic")
            self.assertEqual(set(feed["games"]), {game["match"]["game_id"] for game in catalog["games"]})

    def test_historical_match_ledgers_reconcile_scores_and_minutes(self):
        catalog = build_catalog()
        files = build_live_feed_files(catalog)
        for game in catalog["games"]:
            hist = files["team_history.json"]["games"][game["match"]["game_id"]]
            for team, record in hist["teams"].items():
                self.assertEqual(len(record["matches"]), 7)
                self.assertEqual(record["summary"]["wins"] + record["summary"]["draws"] + record["summary"]["losses"], 7)
                for match in record["matches"]:
                    self.assertEqual(sum(p["minutes_played"] for p in match["players"]), 990)
                    self.assertEqual(sum(p["stats"]["goals"] for p in match["players"]), match["score_for"])
                    self.assertEqual(match["result"], "draw" if match["score_for"] == match["score_against"] else "win" if match["score_for"] > match["score_against"] else "loss")
            players = files["player_history.json"]["games"][game["match"]["game_id"]]["players"]
            self.assertEqual(len(players), 22)
            self.assertTrue(all(len(player["matches"]) == 7 for player in players.values()))

    def test_live_tracking_options_and_wearables_have_linked_bounded_samples(self):
        feeds = build_live_feed_files(build_catalog())
        for game_id, tactical in feeds["live_tactical_metrics.json"]["games"].items():
            self.assertTrue(tactical["event_options"])
            event_ids = {event["id"] for event in feeds["live_events.json"]["games"][game_id]["events"]}
            self.assertTrue({option["event_id"] for option in tactical["event_options"]} <= event_ids)
            for frame in tactical["frames"]:
                self.assertEqual(len(frame["players"]), 22)
                self.assertTrue(0 <= frame["ball"]["x"] <= 105)
                self.assertTrue(0 <= frame["ball"]["y"] <= 68)
                self.assertTrue(all(0 <= p["x"] <= 105 and 0 <= p["y"] <= 68 for p in frame["players"]))
            wearables = feeds["live_wearables.json"]["games"][game_id]
            self.assertIn("not medical", wearables["metrics_note"])
            self.assertEqual(len(wearables["players"]), 22)
            self.assertTrue(all(len(p["samples"]) >= 60 for p in wearables["players"].values()))

    def test_ball_replay_has_one_second_samples_and_discloses_interpolation(self):
        catalog = build_catalog()
        tactical = build_live_feed_files(catalog)["live_tactical_metrics.json"]["games"]
        for game in catalog["games"]:
            feed = tactical[game["match"]["game_id"]]
            track = feed["ball_track"]
            last_second = int(game["match"]["minute"] * 60 + game["match"].get("second", 0))
            self.assertEqual(feed["ball_track_resolution_seconds"], 1)
            self.assertIn("not observed tracking", feed["ball_track_method"])
            self.assertEqual(track[0]["second"], 0)
            self.assertEqual(track[-1]["second"], last_second)
            self.assertTrue(all(b["second"] - a["second"] == 1 for a, b in zip(track, track[1:])))
            self.assertTrue(all(0 <= point["x"] <= 105 and 0 <= point["y"] <= 68 for point in track))

    def test_set_piece_ball_anchors_agree_with_the_event_location(self):
        feeds=build_live_feed_files(build_catalog())
        for gid,event_feed in feeds['live_events.json']['games'].items():
            track=feeds['live_tactical_metrics.json']['games'][gid]['ball_track']
            for event in event_feed['events']:
                if event['type'] in {'corner','direct_free_kick'}:
                    point=track[round(event['minute']*60)]
                    self.assertEqual((point['x'],point['y']),(event['x'],event['y']))


if __name__ == "__main__":
    unittest.main()
