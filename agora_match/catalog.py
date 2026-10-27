"""Shared application payload for the Python server and static web build."""

from typing import Any

from .synthetic import build_demo_games
from .synthetic_enrichment import enrich_synthetic_state
from .feeds import build_historical_feeds


def build_catalog() -> dict[str, Any]:
    games = []
    for raw_state in build_demo_games():
        state = enrich_synthetic_state(raw_state)
        for attack in state['attacks']:
            attack['available_second'] = max([round(attack['minute']*60)] + [round(e['minute']*60) for e in state['events'] if e.get('attack_id')==attack['id']])
        state_payload = state | {"data_provenance": {"source_kind":"synthetic", "generator":"Agora seeded scenarios", "schema_version":"1.1", "seeded_by":state["match"]["game_id"]}}
        team_feed, player_feed = build_historical_feeds(state_payload)
        state_payload["player_history_context"] = player_feed["players"]
        state_payload["team_history_context"] = {
            team: {
                "summary": history["summary"],
                "matches": [
                    {
                        "match_id": match["match_id"],
                        "opponent": match["opponent"],
                        "venue": match["venue"],
                        "result": match["result"],
                        "team_metrics": match["team_metrics"],
                        "tactical_style": match["tactical_style"],
                    }
                    for match in history["matches"]
                ],
                "provenance": "synthetic generated historical fixture",
            }
            for team, history in team_feed["teams"].items()
        }
        from .projection import project_game
        games.append(project_game(state_payload))
    return {"synthetic": True, "schema_version": "1.0", "games": games}
