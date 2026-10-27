"""Enrich the hand-authored seed scenarios into one coherent synthetic event feed.

Every public metric is calculated downstream from these generated records. The
seed scenario only controls the football story; it does not inject final KPIs.
"""

from __future__ import annotations

import math
import random
from typing import Any


ROLE_CENTRES = {"GK": (5, 34), "CB": (31, 34), "FB": (43, 14), "DM": (49, 34), "CM": (58, 34), "W": (76, 18), "ST": (80, 34)}


def _seed(game_id: str) -> int:
    return sum((index + 1) * byte for index, byte in enumerate(game_id.encode()))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def enrich_synthetic_state(game: dict[str, Any]) -> dict[str, Any]:
    rng = random.Random(_seed(game["match"]["game_id"]))
    players = {player["id"]: player for player in game["players"]}
    events = list(game["events"])

    # Convert the attack sequence into a trace of passes, pressure and outcomes.
    for attack in game["attacks"]:
        team_players = [p for p in game["players"] if p["team"] == attack["team"] and p["role"] != "GK"]
        if not team_players:
            continue
        attack_events = [e for e in events if e.get("attack_id") == attack["id"]]
        endpoint = attack_events[0] if attack_events else None
        if endpoint is None:
            continue
        actors = rng.sample(team_players, min(3, len(team_players)))
        final_x, final_y = float(endpoint.get("x", 55)), float(endpoint.get("y", 34))
        start_x = _clamp(final_x - rng.uniform(16, 34), 4, 94)
        start_y = _clamp(final_y + rng.uniform(-18, 18), 3, 65)
        for index in range(2):
            x1 = start_x + (final_x - start_x) * index / 2
            y1 = start_y + (final_y - start_y) * index / 2
            x2 = start_x + (final_x - start_x) * (index + 1) / 2
            y2 = start_y + (final_y - start_y) * (index + 1) / 2
            passer = actors[index]
            receiver = actors[index + 1]
            distance = round(math.hypot(x2 - x1, y2 - y1), 1)
            complete = rng.random() < (0.84 if attack["end_type"] != "turnover" else 0.72)
            events.append({
                "id": f"PASS_{attack['id']}_{index + 1}", "minute": round(attack["minute"] - 0.38 + index * 0.16, 2),
                "team": attack["team"], "player_id": passer["id"], "receiver_id": receiver["id"],
                "type": "pass", "outcome": "complete" if complete else "incomplete",
                "possession_id": f"POS_{attack['id']}", "attack_id": attack["id"],
                "x": round(x1, 1), "y": round(y1, 1), "end_x": round(x2, 1), "end_y": round(y2, 1),
                "pass_distance_m": distance, "pass_difficulty": round(_clamp(distance / 42 + rng.random() * .35, .05, .99), 2),
                "xa": round(rng.uniform(.02, .28), 2) if index == 1 and attack.get("led_to_shot") and complete else 0,
                "big_chance_created": bool(index == 1 and attack.get("led_to_shot") and complete and rng.random() < .28),
            })
        if attack.get("led_to_shot"):
            shooter = actors[-1]
            goal = attack["id"] == "A18" and game["match"]["home_score"] > 0
            events.append({
                "id": f"SHOT_{attack['id']}", "minute": round(attack["minute"] + .12, 2), "team": attack["team"],
                "player_id": shooter["id"], "type": "shot", "outcome": "goal" if goal else rng.choice(["saved", "blocked", "off_target"]),
                "possession_id": f"POS_{attack['id']}", "attack_id": attack["id"],
                "x": round(_clamp(final_x + rng.uniform(-8, 4), 75, 103), 1), "y": round(_clamp(final_y + rng.uniform(-9, 9), 4, 64), 1),
                "xg": round(rng.uniform(.04, .42), 2), "big_chance": rng.random() < .25,
                "assist_player_id": actors[-2]["id"] if goal and len(actors) > 1 and any(e.get("id") == f"PASS_{attack['id']}_2" and e.get("outcome") == "complete" for e in events) else None,
            })
        # Give the opposition a recorded defensive action in the same phase.
        defenders = [p for p in game["players"] if p["team"] != attack["team"] and p["role"] in {"CB", "FB", "DM", "CM"}]
        if defenders and attack["end_type"] in {"cross", "shot", "turnover"}:
            defender = rng.choice(defenders)
            events.append({
                "id": f"DEF_{attack['id']}", "minute": round(attack["minute"] + .06, 2), "team": defender["team"],
                "player_id": defender["id"], "opponent_id": actors[-1]["id"],
                "type": rng.choice(["duel", "clearance", "interception"]), "duel_type": "ground",
                "outcome": rng.choice(["won", "lost"]), "possession_id": f"POS_{attack['id']}",
                "attack_id": attack["id"], "x": round(final_x, 1), "y": round(final_y, 1),
            })

    # Promote the existing tagged matchup observations into ordinary events.
    for item in game.get("matchup_events", []):
        player = players[item["player_id"]]
        related = next((e for e in events if e.get("player_id") == item["player_id"] and abs(float(e["minute"]) - item["minute"]) < 2), None)
        action = item["action"]
        event_type = "dribble" if action == "dribble attempt" else "pass" if action == "forward pass" else "duel"
        outcome = {"stopped": "lost", "route blocked": "incomplete", "beat defender": "won"}.get(item["result"], item["result"])
        events.append({
            "id": item["id"], "minute": item["minute"], "team": player["team"], "player_id": player["id"],
            "opponent_id": item["opponent_id"], "type": event_type, "outcome": outcome,
            "duel_type": "aerial" if "aerial" in action else "ground", "possession_id": f"POS_MX_{item['id']}",
            "x": item.get("x", related.get("x", 55) if related else 55), "y": item.get("y", related.get("y", 34) if related else 34),
            "pass_distance_m": 14 if event_type == "pass" else 0,
        })

    # One goal event per scoreboard goal keeps the feed and displayed score aligned.
    for side, count in ((game["match"]["home"], game["match"]["home_score"]), (game["match"]["away"], game["match"]["away_score"])):
        team_players = [p for p in game["players"] if p["team"] == side and p["role"] in {"ST", "W", "CM"}]
        for goal_index in range(count):
            scorer = team_players[goal_index % len(team_players)]
            if not any(e.get("type") == "shot" and e.get("outcome") == "goal" and e.get("team") == side for e in events):
                events.append({
                    "id": f"GOAL_{'H' if side == game['match']['home'] else 'A'}_{goal_index + 1}",
                    "minute": 50 + goal_index * 4, "team": side, "player_id": scorer["id"], "type": "shot", "outcome": "goal",
                    "x": 91, "y": 34, "xg": .31, "big_chance": True, "possession_id": f"POS_GOAL_{goal_index + 1}",
                })

    # Seed a tracking stream at one-minute intervals. Position, speed, heatmaps,
    # role comparisons, and effort changes are all derived from these samples.
    centers = {}
    for player in game["players"]:
        x, y = ROLE_CENTRES.get(player["role"], (50, 34))
        if player["team"] != game["match"]["home"]:
            x, y = 105 - x, 68 - y
        centers[player["id"]] = [x + rng.uniform(-7, 7), y + rng.uniform(-7, 7)]
    speed_peaks = {p["id"]: rng.uniform(26, 35) * (.78 if p["role"] == "GK" else 1) for p in game["players"]}
    snapshots = []
    for minute in range(game["match"]["minute"] + 1):
        ball = [55 + 35 * math.sin(minute / 8), 34 + 24 * math.sin(minute / 5.5)]
        positions = []
        for player in game["players"]:
            cx, cy = centers[player["id"]]
            # The focal marking scenario is encoded in trajectories, not a final label.
            if player["id"] == "N3" and minute >= 60:
                cx += (minute - 60) * 1.2
            if player["id"] == "E10" and minute >= 60:
                cx += (minute - 60) * 2.0
            if minute:
                cx += rng.gauss(0, 1.5) + (ball[0] - cx) * .018
                cy += rng.gauss(0, 1.7) + (ball[1] - cy) * .018
            cx, cy = _clamp(cx, 2, 103), _clamp(cy, 2, 66)
            centers[player["id"]] = [cx, cy]
            sprint = rng.random() < (.09 if minute < 60 else .055)
            if player["id"] == "N8" and minute >= 60:
                sprint = rng.random() < .025
            speed = min(speed_peaks[player["id"]], rng.uniform(21, speed_peaks[player["id"]]) if sprint else max(0, rng.gauss(7.2, 2.7)))
            # Two deliberate, disclosed synthetic examples make the review cues testable:
            # N8's late high-speed output falls, and a defensive channel opens at 70'.
            if player["id"] == "N8" and 20 <= minute < 30 and minute % 2 == 0:
                speed = 24.0
            if player["id"] == "N8" and 60 <= minute < 70:
                speed = 7.0
            if minute == 55 and player["id"] == "E3": cx = 35.0
            if minute == 55 and player["id"] == "E4": cx = 43.0
            if minute == 70 and player["id"] == "E3": cx = 25.0
            if minute == 70 and player["id"] == "E4": cx = 51.0
            if minute == 70 and player["id"] == "N10": cx, cy = 38.0, 34.0
            if minute == 55 and player["id"] == "N3": cx = 30.0
            if minute == 55 and player["id"] == "E10": cx = 34.0
            if minute == 70 and player["id"] == "N3": cx = 18.0
            if minute == 70 and player["id"] == "E10": cx = 40.0
            positions.append({
                "player_id": player["id"], "team": player["team"], "role": player["role"], "number": player["number"],
                "x": round(cx, 1), "y": round(cy, 1), "speed_kmh": round(speed, 1),
            })
        snapshots.append({"minute": minute, "ball": {"x": round(ball[0], 1), "y": round(ball[1], 1)}, "positions": positions})

    # Add ordinary synthetic stoppage events to the match sequence. Referee
    # positions, timing analytics, and decision-quality views are out of scope.
    incident_minutes = [7.6, 13.8, 20.4, 27.7, 34.2, 42.6, 49.4, 56.8, 63.6, min(game["match"]["minute"] - 1, 69.2)]
    for index, incident in enumerate(incident_minutes, 1):
        action_type = ["foul", "throw_in", "foul", "offside", "corner"][index % 5]
        event_id = f"STOP_{index:02d}"
        incident_x, incident_y = round(rng.uniform(18, 92), 1), round(rng.uniform(5, 63), 1)
        if action_type == "corner":
            incident_x,incident_y=(105 if index%2 else 0),(0 if index%2 else 68)
        events.append({"id": event_id, "minute": incident, "team": game["match"]["home" if index % 2 else "away"], "player_id": None, "type": action_type, "outcome": "awarded" if action_type != "offside" else "flagged", "x": incident_x, "y": incident_y})

    # Pairs describe which opponents the synthetic defensive model is tracking.
    marking_pairs = [
        {"defender_id": "N3", "opponent_id": "E10"}, {"defender_id": "N4", "opponent_id": "E11"},
        {"defender_id": "N2", "opponent_id": "E9"}, {"defender_id": "E3", "opponent_id": "N10"},
    ]
    game.update({
        "events": sorted(events, key=lambda event: (event["minute"], event["id"])),
        "tracking_snapshots": snapshots, "marking_pairs": marking_pairs,
        "synthetic_schema_version": 2,
    })
    game.pop("matchup_events", None)
    game.pop("defensive_responsibilities", None)
    game.pop("load_windows", None)
    return game
