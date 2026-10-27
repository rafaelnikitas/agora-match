"""Player metrics derived from the synthetic event and tracking records."""

from __future__ import annotations

import random
from typing import Any


ROLE_KPIS = {
    "GK": ["saves", "accurate_passes", "long_passes", "recoveries", "max_speed_kmh"],
    "CB": ["aerial_duels_won", "interceptions", "clearances", "accurate_passes", "long_passes"],
    "FB": ["successful_dribbles", "accurate_long_passes", "ground_duels_won", "crosses", "high_speed_samples"],
    "DM": ["recoveries", "interceptions", "accurate_passes", "ground_duels_won", "pressures"],
    "CM": ["accurate_passes", "successful_dribbles", "ground_duels_won", "pressures", "high_speed_samples"],
    "W": ["penalty_area_touches", "xg", "xa", "successful_dribbles", "high_speed_samples"],
    "ST": ["goals", "xg", "penalty_area_touches", "aerial_duels_won", "big_chances_created"],
}

STAT_KEYS = (
    "shots", "goals", "assists", "xg", "xa", "passes", "accurate_passes", "touches", "big_chances_created",
    "long_passes", "accurate_long_passes", "ground_duels", "ground_duels_won", "aerial_duels",
    "aerial_duels_won", "penalty_area_touches", "successful_dribbles", "pressures", "recoveries",
    "high_speed_samples", "max_speed_kmh", "interceptions", "clearances", "saves", "crosses",
)


def _seed(*parts: object) -> int:
    value = ":".join(map(str, parts)).encode()
    return sum((index + 1) * byte for index, byte in enumerate(value))


def in_attacking_box(event, player, home):
    """105×68m coordinates normalized by attack direction for both periods."""
    direction = event.get("attack_direction", 1 if player["team"] == home else -1)
    x, y = event.get("x"), event.get("y")
    return (isinstance(x,(int,float)) and isinstance(y,(int,float)) and 13.84 <= y <= 54.16
            and (88.5 <= x <= 105 if direction == 1 else 0 <= x <= 16.5))


def _aggregate_stats(player: dict[str, Any], events: list[dict[str, Any]], tracking: list[dict[str, Any]], home: str) -> dict[str, float | int]:
    own = [event for event in events if event.get("player_id") == player["id"]]
    stats: dict[str, float | int] = {key: 0 for key in STAT_KEYS}
    passes = [event for event in own if event["type"] == "pass"]
    stats["passes"] = len(passes)
    stats["accurate_passes"] = sum(event.get("outcome") == "complete" for event in passes)
    stats["long_passes"] = sum(event.get("pass_distance_m", 0) >= 25 for event in passes)
    stats["accurate_long_passes"] = sum(event.get("pass_distance_m", 0) >= 25 and event.get("outcome") == "complete" for event in passes)
    stats["shots"] = sum(event["type"] == "shot" for event in own)
    stats["goals"] = sum(event["type"] == "shot" and event.get("outcome") == "goal" for event in own)
    stats["assists"] = sum(event.get("assist_player_id") == player["id"] for event in events)
    stats["xg"] = round(sum(event.get("xg", 0) for event in own if event["type"] == "shot"), 2)
    stats["xa"] = round(sum(event.get("xa", 0) for event in own), 2)
    stats["big_chances_created"] = sum(event.get("big_chance_created", False) for event in own)
    stats["touches"] = sum(event.get("touches", 1) for event in own if event["type"] not in {"whistle", "restart"})
    # Pass receivers also receive a touch; goals/assists are already represented by shot actions.
    stats["touches"] += sum(event.get("receiver_id") == player["id"] and event.get("outcome") == "complete" for event in events)
    stats["ground_duels"] = sum(event["type"] == "duel" and event.get("duel_type") != "aerial" for event in own)
    stats["ground_duels_won"] = sum(event["type"] == "duel" and event.get("duel_type") != "aerial" and event.get("outcome") == "won" for event in own)
    stats["aerial_duels"] = sum(event["type"] == "duel" and event.get("duel_type") == "aerial" for event in own)
    stats["aerial_duels_won"] = sum(event["type"] == "duel" and event.get("duel_type") == "aerial" and event.get("outcome") == "won" for event in own)
    stats["crosses"] = sum(event["type"] == "cross" for event in own)
    stats["successful_dribbles"] = sum(event["type"] == "dribble" and event.get("outcome") in {"won", "complete"} for event in own)
    stats["pressures"] = sum(event["type"] == "pressure" for event in own)
    stats["recoveries"] = sum(event["type"] == "recovery" for event in own)
    stats["interceptions"] = sum(event["type"] == "interception" for event in own)
    stats["clearances"] = sum(event["type"] == "clearance" for event in own)
    stats["saves"] = sum(event["type"] == "save" for event in own)
    stats["penalty_area_touches"] = sum(
        event.get("touches", 1) > 0 and in_attacking_box(event,player,home)
        for event in own if event["type"] not in {"whistle", "restart"}
    )
    speeds = [point.get("speed_kmh", 0) for snapshot in tracking for point in snapshot["positions"] if point["player_id"] == player["id"]]
    stats["max_speed_kmh"] = round(max(speeds, default=0), 1)
    stats["high_speed_samples"] = sum(speed >= 20 for speed in speeds)
    return stats


def _synthetic_history(player: dict[str, Any], game_id: str) -> list[dict[str, Any]]:
    """Generate prior synthetic match event records, then aggregate them normally."""
    history: list[dict[str, Any]] = []
    role_volume = {"GK": 13, "CB": 38, "FB": 48, "DM": 55, "CM": 62, "W": 39, "ST": 28}.get(player["role"], 40)
    for match_index in range(1, 8):
        rng = random.Random(_seed(game_id, player["id"], "history", match_index))
        events: list[dict[str, Any]] = []
        for action in range(max(8, round(role_volume * rng.uniform(.78, 1.22)))):
            complete = rng.random() < (.84 if player["role"] in {"CB", "DM", "CM", "GK"} else .76)
            events.append({"id": f"H{match_index}_{action}", "player_id": player["id"], "type": "pass", "outcome": "complete" if complete else "incomplete", "pass_distance_m": rng.uniform(4, 42), "minute": rng.uniform(0, 90), "x": rng.uniform(10, 100), "y":rng.uniform(0,68), "attack_direction":1, "touches": 1})
        shot_count = rng.choices([0, 1, 2, 3], weights=[.5, .35, .12, .03])[0] if player["role"] in {"ST", "W", "CM"} else rng.choices([0, 1], weights=[.92, .08])[0]
        for action in range(shot_count):
            xg = round(rng.uniform(.02, .48), 2)
            events.append({"id": f"HS{match_index}_{action}", "player_id": player["id"], "type": "shot", "outcome": "goal" if rng.random() < xg * .8 else "saved", "xg": xg, "minute": rng.uniform(0, 90), "x": rng.uniform(80, 103), "y":rng.uniform(14,54), "attack_direction":1, "touches": 1})
        for action in range(rng.randint(2, 9)):
            aerial = rng.random() < (.55 if player["role"] in {"CB", "ST", "GK"} else .2)
            outcome = "won" if rng.random() < .52 else "lost"
            events.append({"id": f"HD{match_index}_{action}", "player_id": player["id"], "type": "duel", "duel_type": "aerial" if aerial else "ground", "outcome": outcome, "minute": rng.uniform(0, 90), "x": rng.uniform(10, 95), "touches": 1})
        tracking = [{"minute": minute, "positions": [{"player_id": player["id"], "speed_kmh": max(0, rng.gauss(8.5, 5.5))}]} for minute in range(90)]
        history.append({"match_index": match_index, "minutes_played":90, "stats": _aggregate_stats(player, events, tracking, player["team"])})
    return history


def _average(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, float]:
    return {key: round(sum(row["stats"].get(key, 0) for row in rows) / max(1, len(rows)), 2) for key in keys}


def build_player_profiles(game: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive match totals and movement heatmaps from event/tracking samples."""
    profiles = []
    for player in game["players"]:
        stats = _aggregate_stats(player, game["events"], game["tracking_snapshots"], game["match"]["home"])
        canonical = game.get("player_history_context",{}).get(player["id"])
        history = canonical["matches"] if canonical else _synthetic_history(player, game["match"]["game_id"])
        player_points = [point for snapshot in game["tracking_snapshots"] for point in snapshot["positions"] if point["player_id"] == player["id"]]
        if player_points:
            stride = max(1, len(player_points) // 42)
            heat_points = [{"x": point["x"], "y": point["y"]} for point in player_points[::stride][:42]]
        else:
            heat_points = []
        recent_rows=history[-5:]
        def rate(numerator,denominator):
            total=sum(r["stats"].get(denominator,0) for r in recent_rows)
            return {"current":round(stats[numerator]/stats[denominator],3) if stats[denominator] else None,
                "last5":round(sum(r["stats"].get(numerator,0) for r in recent_rows)/total,3) if total else None,
                "current_denominator":stats[denominator],"history_denominator":total}
        profiles.append({
            "comparable_rates":{"xg_per_shot":rate("xg","shots"),"pass_completion":rate("accurate_passes","passes")},
            "player_id": player["id"], "stats": stats,
            "last5_average": canonical["last5_average"] if canonical else _average(history[-5:], STAT_KEYS), "season_average": canonical["season_average"] if canonical else _average(history, STAT_KEYS),
            "matches_played":len(history), "coverage":"Tagged sample, not complete match totals",
            "history_matches": history, "history_is_synthetic": True, "heat_points": heat_points,
            "kpis": ROLE_KPIS.get(player["role"], ROLE_KPIS["CM"]),
        })
    for key in STAT_KEYS:
        ordered = sorted(profiles, key=lambda profile: profile["stats"][key], reverse=True)
        for rank, profile in enumerate(ordered, 1):
            profile.setdefault("ranks", {})[key] = 1 + sum(p["stats"][key] > profile["stats"][key] for p in profiles)
    return profiles
