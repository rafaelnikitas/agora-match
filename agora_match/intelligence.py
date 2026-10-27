"""Deterministic, evidence-linked player intelligence for the synthetic demo."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


ACTION_VALUE = {
    "key_pass": 0.34, "shot": 0.18, "cross": 0.10, "pass": 0.06,
    "duel": 0.20, "turnover": -0.25, "tackle": 0.18,
}


def _clamp(value: float, low: float = 4.5, high: float = 9.8) -> float:
    return max(low, min(high, value))


def build_rating_timelines(game: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Build a transparent 5–10 style rating trace from tagged match events.

    The initial value is a neutral 6.0. This is a demo scoring model, not an
    official FIFA/EA rating or a claim that the sparse synthetic feed is complete.
    """
    timelines: dict[str, list[dict[str, Any]]] = {}
    for player in game["players"]:
        events = sorted(
            (event for event in game["events"] if event.get("player_id") == player["id"]),
            key=lambda event: (event["minute"], event["id"]),
        )
        rating = 6.0
        trace = [{"minute": 0, "rating": rating, "label": "Kick-off", "event_id": None}]
        for event in events:
            delta = ACTION_VALUE.get(event["type"], 0)
            outcome = event.get("outcome", "")
            if outcome in {"lost", "incomplete", "failed"}:
                delta = -abs(delta or 0.12)
            elif outcome in {"won", "complete", "saved"} and event["type"] == "duel":
                delta = abs(delta)
            if event["type"] == "shot" and outcome == "goal":
                delta += 0.55
            rating = _clamp(rating + delta)
            trace.append({
                "minute": round(float(event["minute"]), 1), "rating": round(rating, 2),
                "label": event["type"].replace("_", " "), "event_id": event["id"],
            })
        timelines[player["id"]] = trace
    return timelines


def summarize_matchups(game: dict[str, Any]) -> list[dict[str, Any]]:
    players = {player["id"]: player for player in game["players"]}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in game["events"]:
        if event.get("opponent_id") and event.get("player_id") in players and event["opponent_id"] in players:
            grouped[(event["player_id"], event["opponent_id"])].append({
                "id": event["id"], "minute": event["minute"],
                "action": event["type"].replace("_", " "), "result": event.get("outcome", "unrecorded"),
                "event_id": event["id"],
            })
    summaries = []
    for (player_id, opponent_id), observations in grouped.items():
        stopped = sum(item["result"] in {"stopped", "route blocked", "lost", "incomplete"} for item in observations)
        won = sum(item["result"] in {"won", "complete"} for item in observations)
        summaries.append({
            "player_id": player_id, "opponent_id": opponent_id,
            "player_name": players[player_id]["name"], "opponent_name": players[opponent_id]["name"],
            "team": players[player_id]["team"], "opponent_team": players[opponent_id]["team"],
            "attempts": len(observations), "stopped": stopped, "won": won,
            "events": sorted(observations, key=lambda item: item["minute"]),
        })
    return sorted(summaries, key=lambda item: (item["stopped"], item["attempts"]), reverse=True)


def _by_minute(game: dict[str, Any], minute: int) -> dict[str, dict[str, Any]]:
    snapshot = max((s for s in game["tracking_snapshots"] if s["minute"] <= minute), key=lambda item:item["minute"])
    return {point["player_id"]: point for point in snapshot["positions"]}


def _efforts(game: dict[str, Any], player_id: str, start: int, end: int) -> int | None:
    rows = [(snapshot["minute"],point) for snapshot in game["tracking_snapshots"] if start <= snapshot["minute"] < end
            for point in snapshot["positions"] if point["player_id"] == player_id and "speed_kmh" in point]
    if len({minute for minute,_ in rows}) != end-start:
        return None
    return sum(point["speed_kmh"] >= 20 for _,point in rows)


def build_coach_board(game: dict[str, Any]) -> dict[str, Any]:
    players = {player["id"]: player for player in game["players"]}
    profiles = {profile["player_id"]: profile for profile in game["player_profiles"]}
    rows = []
    for player in game["players"]:
        profile = profiles[player["id"]]
        stats = profile["stats"]
        pass_rate = stats.get("accurate_passes", 0) / max(1, stats.get("passes", 0))
        peer_ids = [p["id"] for p in game["players"] if p["role"] == player["role"] and p["id"] != player["id"]]
        peak_peers = [profiles[pid]["stats"]["max_speed_kmh"] for pid in peer_ids]
        peak_avg = sum(peak_peers) / len(peak_peers) if peak_peers else 0
        early, late = _efforts(game, player["id"], 20, 30), _efforts(game, player["id"], 60, 70)
        fatigue = round((late - early) / early * 100) if early and late is not None and game["match"]["minute"] >= 70 else None
        responsibility = None
        pair = next((item for item in game.get("marking_pairs", []) if item["defender_id"] == player["id"]), None)
        if pair and {55,70}.issubset({s["minute"] for s in game["tracking_snapshots"]}):
            before, after = _by_minute(game, 55), _by_minute(game, 70)
            attacker_id = pair["opponent_id"]
            gap_before = ((before[player["id"]]["x"] - before[attacker_id]["x"]) ** 2 + (before[player["id"]]["y"] - before[attacker_id]["y"]) ** 2) ** .5
            gap_after = ((after[player["id"]]["x"] - after[attacker_id]["x"]) ** 2 + (after[player["id"]]["y"] - after[attacker_id]["y"]) ** 2) ** .5
            responsibility = {"defender_id": player["id"], "opponent_id": attacker_id, "status": "widened" if gap_after > max(12, gap_before + 6) else "stable", "minute": 70, "distance_before_m": round(gap_before, 1), "distance_after_m": round(gap_after, 1), "source": "tracking-derived paired positions"}
        # Matchup edges are shared as opposing-player evidence for defensive roles.
        rows.append({
            "player_id": player["id"], "name": player["name"], "team": player["team"], "role": player["role"],
            "pass_accuracy": round(pass_rate * 100), "passes": stats.get("passes", 0), "accurate_passes": stats.get("accurate_passes", 0),
            "high_speed_samples":stats.get("high_speed_samples",0), "peer_count":len(peer_ids),
            "max_speed_kmh": stats.get("max_speed_kmh", 0), "role_peer_max_speed_kmh": round(peak_avg, 2),
            "max_speed_vs_role_pct": round((stats.get("max_speed_kmh", 0) / peak_avg - 1) * 100) if peak_avg else 0,
            "high_speed_sample_change_pct": fatigue,
            "paired_spacing": responsibility, "high_speed_efforts_20_30": early if game["match"]["minute"] >= 30 else None, "high_speed_efforts_60_70": late if game["match"]["minute"] >= 70 else None,
        })
    return {"players": rows, "decision_time_available": False}


def build_match_intelligence(game: dict[str, Any]) -> dict[str, Any]:
    return {
        "rating_timelines": build_rating_timelines(game),
        "matchups": summarize_matchups(game),
        "coach_board": build_coach_board(game),
        "rating_method": "Neutral 6.0 plus small, capped values for tagged events; incomplete synthetic event coverage is shown in the UI.",
    }
