"""Generate detailed, reproducible synthetic history and live data feeds."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from statistics import mean
from typing import Any


OPPONENTS = ["Ironwood Rovers", "Stonehaven Athletic", "Westmere FC", "Ashcombe Town", "Riverside Vale", "Kingswell United", "Pineford City"]


def _seed(*parts: object) -> int:
    return sum((index + 1) * byte for index, byte in enumerate(":".join(map(str, parts)).encode()))


def _mean_stats(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, float]:
    return {key: round(mean(float(row.get(key, 0)) for row in rows), 2) if rows else 0.0 for key in keys}


def build_historical_feeds(game: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return team match ledgers and corresponding player appearance histories."""
    match_id = game["match"]["game_id"]
    team_history: dict[str, Any] = {"schema_version": "1.0", "data_mode": "synthetic", "game_id": match_id, "teams": {}}
    player_rows: dict[str, Any] = {}
    for team_index, team in enumerate((game["match"]["home"], game["match"]["away"])):
        team_players = [p for p in game["players"] if p["team"] == team]
        setpiece = game["history"][team]
        matches = []
        for index in range(setpiece["matches"]):
            rng = random.Random(_seed(match_id, team, "history", index))
            opponent = OPPONENTS[(index + team_index * 3) % len(OPPONENTS)]
            at_home = rng.random() < 0.5
            corner_for = setpiece["scored_from_corner"][index]
            free_kick_for = setpiece["scored_from_direct_free_kick"][index]
            corner_against = setpiece["conceded_from_corner"][index]
            free_kick_against = setpiece["conceded_from_direct_free_kick"][index]
            goals_for = corner_for + free_kick_for + rng.choices([0, 1, 2, 3], [0.32, 0.43, 0.20, 0.05])[0]
            goals_against = corner_against + free_kick_against + rng.choices([0, 1, 2, 3], [0.28, 0.44, 0.22, 0.06])[0]
            if goals_for == goals_against:
                result = "draw"
            else:
                result = "win" if goals_for > goals_against else "loss"

            # One or two fictional substitutions preserve eleven players on pitch.
            substituted = rng.sample(team_players[1:], k=rng.choice([1, 1, 2]))
            minutes_by_id = {p["id"]: 90 for p in team_players}
            substitutes = []
            for sub_index, outgoing in enumerate(substituted):
                minute = rng.randint(58, 79)
                minutes_by_id[outgoing["id"]] = minute
                role = outgoing["role"]
                sub_id = f"HIST-{team_index}-{index + 1}-SUB{sub_index + 1}"
                substitutes.append({"player_id": sub_id, "name": f"Synthetic substitute {team_index + 1}-{index + 1}-{sub_index + 1}", "role": role, "minutes_played": 90 - minute, "started": False, "is_synthetic_placeholder": True})

            appearances: list[dict[str, Any]] = []
            all_roster = [
                {"player_id": player["id"], "name": player["name"], "role": player["role"], "minutes_played": minutes_by_id[player["id"]], "started": True, "is_synthetic_placeholder": False}
                for player in team_players
            ] + substitutes
            eligible = [row for row in all_roster if row["minutes_played"] > 0]
            goal_weights = [3.6 if row["role"] in {"ST", "W"} else 2.2 if row["role"] == "CM" else 1.2 if row["role"] == "FB" else .55 for row in eligible]
            assigned_goals: dict[str, int] = defaultdict(int)
            assigned_assists: dict[str, int] = defaultdict(int)
            for _ in range(goals_for):
                scorer = rng.choices(eligible, weights=goal_weights, k=1)[0]
                assigned_goals[scorer["player_id"]] += 1
                if rng.random() < .78:
                    assist_pool = [row for row in eligible if row["player_id"] != scorer["player_id"]]
                    if assist_pool:
                        assigned_assists[rng.choice(assist_pool)["player_id"]] += 1

            for row in all_roster:
                mins = row["minutes_played"]
                scale = mins / 90
                role = row["role"]
                passes = max(1, round(rng.gauss({"GK": 22, "CB": 48, "FB": 43, "DM": 51, "CM": 57, "W": 31, "ST": 22}.get(role, 35) * scale, 5 * scale))) if mins else 0
                accuracy = rng.uniform(.72, .95) if role in {"GK", "CB", "DM", "CM"} else rng.uniform(.62, .88)
                shots = rng.randint(0, 2) if role in {"ST", "W", "CM"} and mins else 0
                goals = assigned_goals[row["player_id"]]
                xa = round(rng.uniform(0, .34) * scale, 2) if mins else 0
                stats = {
                    "minutes_played": mins,
                    "goals": goals,
                    "assists": assigned_assists[row["player_id"]],
                    "xg": round(goals * rng.uniform(.26, .55) + sum(rng.uniform(.02, .17) for _ in range(shots)), 2),
                    "xa": xa,
                    "shots": shots + goals,
                    "passes": passes,
                    "accurate_passes": round(passes * accuracy),
                    "touches": round(passes * 1.3 + rng.randint(4, 28) * scale) if mins else 0,
                    "key_passes": rng.randint(0, 3) if mins else 0,
                    "crosses": rng.randint(0, 5) if role in {"W", "FB"} and mins else 0,
                    "ground_duels": rng.randint(1, 8) if mins else 0,
                    "ground_duels_won": 0,
                    "aerial_duels": rng.randint(0, 5) if mins else 0,
                    "aerial_duels_won": 0,
                    "high_speed_efforts": round(rng.randint(2, 12) * scale) if mins else 0,
                    "high_speed_distance_m": round(rng.uniform(70, 280) * scale) if mins else 0,
                }
                stats["ground_duels_won"] = round(stats["ground_duels"] * rng.uniform(.38, .72))
                stats["aerial_duels_won"] = round(stats["aerial_duels"] * rng.uniform(.35, .70))
                appearance = row | {"stats": stats}
                appearances.append(appearance)
                if not row["is_synthetic_placeholder"]:
                    player = next(p for p in team_players if p["id"] == row["player_id"])
                    history_row = {
                        "match_id": f"{match_id}-H{index + 1}", "match_index": index + 1,
                        "date_offset_days": -7 * (7 - index), "opponent": opponent,
                        "venue": "home" if at_home else "away", "result": result,
                        "team_score": goals_for, "opponent_score": goals_against,
                        "minutes_played": mins, "started": True, "stats": stats,
                    }
                    player_rows.setdefault(player["id"], {"player_id": player["id"], "player_name": player["name"], "team": team, "role": player["role"], "matches": []})["matches"].append(history_row)

            team_stats = {key: round(sum(row["stats"][key] for row in appearances), 2) for key in ("xg", "xa", "shots", "passes", "accurate_passes", "crosses", "high_speed_efforts")}
            team_stats.update({"goals_for": goals_for, "goals_against": goals_against, "pass_accuracy_pct": round(team_stats["accurate_passes"] / max(1, team_stats["passes"]) * 100, 1), "possession_pct": round(rng.uniform(42, 58), 1), "corners_for": rng.randint(2, 9), "corners_against": rng.randint(2, 9), "corner_goals_for": corner_for, "corner_goals_against": corner_against, "direct_free_kick_goals_for": free_kick_for, "direct_free_kick_goals_against": free_kick_against})
            matches.append({
                "match_id": f"{match_id}-H{index + 1}", "match_index": index + 1,
                "date_offset_days": -7 * (7 - index), "opponent": opponent,
                "venue": "home" if at_home else "away", "score_for": goals_for,
                "score_against": goals_against, "result": result,
                "formation": rng.choice(["4-3-3", "4-2-3-1", "4-4-2", "3-4-2-1"]),
                "tactical_style": {"tagged_attacks": 24, "cross_attacks": rng.randint(1, 7), "left_to_right_switches": rng.randint(0, 5), "high_press_regains": rng.randint(2, 11), "average_defensive_line_m": round(rng.uniform(35, 49), 1)},
                "team_metrics": team_stats, "players": appearances,
                "provenance": "synthetic generated historical fixture",
            })
        match_rows = [p for m in matches for p in m["players"] if not p["is_synthetic_placeholder"]]
        team_history["teams"][team] = {
            "team_id": "HOME" if team_index == 0 else "AWAY", "recent_matches": len(matches),
            "summary": {
                "wins": sum(m["result"] == "win" for m in matches),
                "draws": sum(m["result"] == "draw" for m in matches),
                "losses": sum(m["result"] == "loss" for m in matches),
                "goals_for": sum(m["score_for"] for m in matches),
                "goals_against": sum(m["score_against"] for m in matches),
                "corner_scoring_matches": sum(m["team_metrics"]["corner_goals_for"] > 0 for m in matches),
                "corner_conceding_matches": sum(m["team_metrics"]["corner_goals_against"] > 0 for m in matches),
                "mean_xg": round(mean(m["team_metrics"]["xg"] for m in matches), 2),
                "mean_possession_pct": round(mean(m["team_metrics"]["possession_pct"] for m in matches), 1),
            },
            "matches": matches,
        }

    for rows in player_rows.values():
        active = [row for row in rows["matches"] if row["minutes_played"] > 0]
        stat_keys = ("goals", "assists", "xg", "xa", "shots", "passes", "accurate_passes", "touches", "key_passes", "crosses", "ground_duels", "ground_duels_won", "aerial_duels", "aerial_duels_won", "high_speed_efforts", "high_speed_distance_m")
        rows["last5_average"] = _mean_stats([row["stats"] for row in active[-5:]], stat_keys)
        rows["season_average"] = _mean_stats([row["stats"] for row in active], stat_keys)
        rows["matches_played"] = len(active)
        rows["provenance"] = "synthetic generated player appearance history"
    player_history = {"schema_version": "1.0", "data_mode": "synthetic", "game_id": match_id, "players": player_rows}
    return team_history, player_history


def build_live_feed_files(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Project the synthetic catalog into domain feed files with stable IDs."""
    team_history = {"schema_version": "1.0", "data_mode": "synthetic", "games": {}}
    player_history = {"schema_version": "1.0", "data_mode": "synthetic", "games": {}}
    live_events = {"schema_version": "1.0", "data_mode": "synthetic", "games": {}}
    live_tactical = {"schema_version": "1.0", "data_mode": "synthetic", "games": {}}
    live_wearables = {"schema_version": "1.0", "data_mode": "synthetic", "games": {}}

    for game in catalog["games"]:
        game_id = game["match"]["game_id"]
        team_feed, player_feed = build_historical_feeds(game)
        team_history["games"][game_id] = team_feed
        player_history["games"][game_id] = player_feed
        events = sorted(game["events"], key=lambda event: (event["minute"], event["id"]))
        live_events["games"][game_id] = {"match": game["match"], "events": events, "attacks": game["attacks"], "provenance": "synthetic generated event stream"}

        frames = []
        for snapshot in game["tracking_snapshots"]:
            positions = snapshot["positions"]
            ball = snapshot.get("ball", {"x": 52.5 + 30 * math.sin(snapshot["minute"] / 8), "y": 34 + 20 * math.sin(snapshot["minute"] / 5.5)})
            team_shapes = {}
            for team in (game["match"]["home"], game["match"]["away"]):
                group = [point for point in positions if point["team"] == team]
                x_values = [point["x"] for point in group]
                y_values = [point["y"] for point in group]
                team_shapes[team] = {"line_height_m": round(mean(x_values), 1), "team_width_m": round(max(y_values) - min(y_values), 1), "centroid": {"x": round(mean(x_values), 1), "y": round(mean(y_values), 1)}}
            pressure = {}
            for team in (game["match"]["home"], game["match"]["away"]):
                pressure[team] = sum(math.hypot(point["x"] - ball["x"], point["y"] - ball["y"]) <= 12 for point in positions if point["team"] != team)
            frames.append({"minute": snapshot["minute"], "ball": ball, "players": positions, "team_shapes": team_shapes, "opposition_players_within_12m_of_ball": pressure})

        # A one-second replay cursor makes the ball path explorable. The source
        # player frames remain one-minute samples; the ball path is an explicit
        # synthetic interpolation, not observed or broadcast tracking.
        duration_seconds = int(game["match"]["minute"] * 60 + game["match"].get("second", 0))
        # Event anchors override the illustrative minute path at tagged moments.
        # This is a synthetic reconstruction, not measured ball tracking.
        anchor_map = {round(f["minute"]*60):(0,f["ball"]) for f in frames}
        priorities={"corner":10,"direct_free_kick":9,"shot":8,"pass":7,"key_pass":7,"cross":7,"dribble":6}
        for event in events:
            if event.get("x") is None or event.get("y") is None:
                continue
            second=round(event["minute"]*60)
            if 0 <= second <= duration_seconds:
                priority=priorities.get(event["type"],1)
                if second not in anchor_map or priority>=anchor_map[second][0]:
                    anchor_map[second]=(priority,{"x":event["x"],"y":event["y"]})
        anchor_map[duration_seconds]=anchor_map.get(duration_seconds,(0,frames[-1]["ball"]))
        anchors=sorted((t,p[1]) for t,p in anchor_map.items())
        cursor=0
        ball_track=[]
        for second in range(duration_seconds+1):
            while cursor+1<len(anchors) and anchors[cursor+1][0]<=second:
                cursor+=1
            lt,left=anchors[cursor]
            rt,right=anchors[min(cursor+1,len(anchors)-1)]
            fraction=(second-lt)/(rt-lt) if rt>lt else 0
            x=left["x"]+(right["x"]-left["x"])*fraction
            y=left["y"]+(right["y"]-left["y"])*fraction
            ball_track.append({"second":second,"x":round(max(0,min(105,x)),2),"y":round(max(0,min(68,y)),2)})

        event_options = []
        for event in events:
            if event["type"] not in {"pass", "key_pass", "dribble", "shot", "cross"} or not event.get("player_id"):
                continue
            frame = max((f for f in frames if f["minute"] <= event["minute"]), key=lambda item: item["minute"])
            player = next((p for p in frame["players"] if p["player_id"] == event["player_id"]), None)
            if player is None:
                continue
            teammate_options = []
            opponents = [p for p in frame["players"] if p["team"] != event["team"]]
            for teammate in frame["players"]:
                if teammate["team"] != event["team"] or teammate["player_id"] == player["player_id"]:
                    continue
                distance = math.hypot(teammate["x"] - event.get("x", player["x"]), teammate["y"] - event.get("y", player["y"]))
                if distance > 32:
                    continue
                pressure_distance = min((math.hypot(teammate["x"] - defender["x"], teammate["y"] - defender["y"]) for defender in opponents), default=0)
                teammate_options.append({"player_id": teammate["player_id"], "distance_m": round(distance, 1), "nearest_opponent_m": round(pressure_distance, 1), "space_label": "open" if pressure_distance >= 8 else "pressured"})
            teammate_options.sort(key=lambda option: (-option["nearest_opponent_m"], option["distance_m"]))
            event_options.append({"event_id": event["id"], "minute": event["minute"], "player_id": event["player_id"], "event_type": event["type"], "outcome": event.get("outcome"), "ball_location": {"x": event.get("x"), "y": event.get("y")}, "nearest_pressure_m": round(min((math.hypot(player["x"] - defender["x"], player["y"] - defender["y"]) for defender in opponents), default=0), 1), "passing_options": teammate_options[:4]})
        live_tactical["games"][game_id] = {"match": game["match"], "coordinate_system": "105x68m; home attack direction normalized to increasing x", "frames": frames, "ball_track_resolution_seconds": 1, "ball_track_method": "event-constrained interpolation between synthetic ball anchors and minute snapshots; this is not observed tracking", "ball_track": ball_track, "event_options": event_options, "provenance": "synthetic one-minute player tracking, one-second interpolated ball path, and derived spatial options"}

        wearable_players = {}
        for player in game["players"]:
            points = []
            previous_speed = None
            for snapshot in game["tracking_snapshots"]:
                position = next((item for item in snapshot["positions"] if item["player_id"] == player["id"]), None)
                if position is None:
                    continue
                rng = random.Random(_seed(game_id, player["id"], "wearable", snapshot["minute"]))
                speed = float(position.get("speed_kmh", 0))
                base = 110 if player["role"] in {"GK", "CB"} else 116
                heart_rate = max(100, min(190, round(base + speed * 1.45 + snapshot["minute"] * .12 + rng.uniform(-4, 4))))
                accel = round(max(-3.2, min(3.2, rng.gauss((speed - (previous_speed or speed)) / 12, .55))), 2)
                points.append({"minute": snapshot["minute"], "player_id": player["id"], "speed_kmh": round(speed, 1), "heart_rate_bpm": heart_rate, "acceleration_mps2": accel, "effort_zone": "sprint" if speed >= 24 else "high" if speed >= 20 else "moderate" if speed >= 12 else "low", "provenance": "synthetic wearable sample"})
                previous_speed = speed
            early = [point for point in points if 20 <= point["minute"] < 30]
            late = [point for point in points if 60 <= point["minute"] < 70]
            wearable_players[player["id"]] = {"player_id": player["id"], "player_name": player["name"], "role": player["role"], "samples": points, "summary": {"mean_heart_rate_bpm": round(mean(point["heart_rate_bpm"] for point in points), 1) if points else None, "peak_speed_kmh": max((point["speed_kmh"] for point in points), default=0), "high_efforts_20_30": sum(point["effort_zone"] in {"high", "sprint"} for point in early), "high_efforts_60_70": sum(point["effort_zone"] in {"high", "sprint"} for point in late)}}
        live_wearables["games"][game_id] = {"match": game["match"], "sampling_interval_minutes": 1, "metrics_note": "Synthetic workload signals for demo interaction; not medical, clinical, or verified wearable measurements.", "players": wearable_players}

    return {
        "team_history.json": team_history,
        "player_history.json": player_history,
        "live_events.json": live_events,
        "live_tactical_metrics.json": live_tactical,
        "live_wearables.json": live_wearables,
    }
