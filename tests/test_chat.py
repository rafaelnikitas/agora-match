import unittest

from agora_match.catalog import build_catalog
from agora_match.chat import answer_question, retrieve_evidence


class MatchChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = build_catalog()["games"][0]

    def test_same_question_adapts_to_each_audience_with_same_evidence(self):
        question = "How many of the last attacks ended in crosses?"
        answers = {persona: answer_question(self.game, question, persona, "N8") for persona in ("fan", "analyst", "coach")}
        self.assertEqual(len({answer["text"] for answer in answers.values()}), 3)
        self.assertEqual({tuple(f["value"] for f in answer["facts"]) for answer in answers.values()}, {("8/8", "4/8")})
        self.assertTrue(all(answer["facts"][0]["source"] for answer in answers.values()))

    def test_plain_language_mode_shortens_answers_without_changing_evidence(self):
        question = "How many of the last attacks ended in crosses?"
        detailed = answer_question(self.game, question, "analyst", "N8")
        plain = answer_question(self.game, question, "analyst", "N8", simplify=True)
        self.assertLess(len(plain["text"]), len(detailed["text"]))
        self.assertEqual(plain["facts"], detailed["facts"])
        self.assertEqual(plain["caveat"], detailed["caveat"])

    def test_plain_language_preserves_each_roles_purpose(self):
        answers = {role: answer_question(self.game, "How many attacks ended in crosses?", role, "N8", simplify=True)
                   for role in ("fan", "analyst", "coach")}
        self.assertEqual(len({a["text"] for a in answers.values()}), 3)
        self.assertIn("supporting sample", answers["analyst"]["text"])
        self.assertIn("Review cue", answers["coach"]["text"])
        self.assertEqual(answers["coach"]["facts"], answers["fan"]["facts"])

    def test_history_answer_cites_current_event_and_sample_window(self):
        answer = answer_question(self.game, "Why is this corner important?", "analyst")
        self.assertEqual(answer["topic"], "history")
        self.assertIn("3/7 matches", answer["text"])
        self.assertTrue(any("EV_CORNER_1" in fact["source"] for fact in answer["facts"]))
        self.assertIn("not a prediction", answer["caveat"])

    def test_player_answer_uses_named_player_not_selected_player(self):
        answer = answer_question(self.game, "How is Luca Gray playing?", "fan", "N8")
        self.assertEqual(answer["player_id"], "N11")
        self.assertIn("Luca Gray", answer["text"])

    def test_player_history_compares_live_output_with_recent_and_season_averages(self):
        answer = answer_question(self.game, "Compare Luca Gray's xG with his last five matches", "analyst")
        self.assertEqual(answer["topic"], "player_history")
        self.assertEqual(answer["player_id"], "N11")
        self.assertEqual([fact["label"] for fact in answer["facts"][:3]], [
            "xG · current match", "xG · last 5 average", "xG · season sample average",
        ])
        self.assertTrue(all("synthetic" in fact["source"] for fact in answer["facts"]))
        self.assertIn("current-match xg", answer["text"])

    def test_team_history_compares_live_attack_pattern_with_prior_matches(self):
        answer = answer_question(self.game, "Compare the last 8 crosses with the historical average", "analyst")
        self.assertEqual(answer["topic"], "team_history")
        self.assertTrue(any("Cross-ending attacks in last 8" in fact["label"] for fact in answer["facts"][:3]))
        self.assertTrue(any("Cross attacks per prior match" in fact["label"] for fact in answer["facts"][:3]))
        self.assertIn("synthetic records", answer["caveat"])

    def test_selected_player_does_not_capture_a_team_pattern_question(self):
        answer = answer_question(self.game, "Compare the last 8 crosses with their historical average", "analyst", "N8")
        self.assertEqual(answer["topic"], "team_history")
        self.assertTrue(any("Cross attacks per prior match" in fact["label"] for fact in answer["facts"][:3]))

    def test_follow_up_uses_prior_user_question_to_resolve_player(self):
        answer = answer_question(
            self.game,
            "Compare that with his last five matches",
            "fan",
            conversation=[{"role": "user", "content": "How is Luca Gray playing today?"}],
        )
        self.assertEqual(answer["topic"], "player_history")
        self.assertEqual(answer["player_id"], "N11")

    def test_set_piece_history_keeps_event_specific_answer(self):
        answer = answer_question(self.game, "Compare this corner with the last 7 matches", "analyst")
        self.assertEqual(answer["topic"], "history")
        self.assertTrue(any(fact["label"] == "Latest tagged set piece" for fact in answer["facts"]))

    def test_wide_matchup_question_returns_visual_case_board_evidence(self):
        answer = answer_question(self.game, "Show all cases where the fullback faced the winger", "analyst")
        self.assertEqual(answer["topic"], "fullback_winger")
        self.assertEqual(answer["visualization"]["type"], "fullback_winger_cases")
        cases = answer["visualization"]["cases"]
        self.assertEqual(len(cases), 8)
        self.assertEqual(len({case["event_id"] for case in cases}), 8)
        players = {player["id"]: player for player in self.game["players"]}
        self.assertTrue(all(players[case["player_id"]]["role"] == "W" and players[case["opponent_id"]]["role"] == "FB" for case in cases))
        self.assertIn("prior minute-level snapshot", answer["caveat"])

    def test_referee_is_not_a_dedicated_chat_topic(self):
        answer = answer_question(self.game, "How busy has the referee been?", "coach")
        self.assertNotEqual(answer["topic"], "referee")

    def test_general_question_does_not_assume_selected_player(self):
        evidence = retrieve_evidence(self.game, "What is the story of this match?", "N8")
        self.assertEqual(evidence["topic"], "match")

    def test_invalid_persona_is_rejected(self):
        with self.assertRaises(ValueError):
            answer_question(self.game, "What happened?", "studio")


if __name__ == "__main__":
    unittest.main()
