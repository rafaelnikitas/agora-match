"""Small deterministic fictional fixture used by the demo and tests."""

from __future__ import annotations

import random
from copy import deepcopy
from typing import Any


def build_demo_state(seed: int = 17) -> dict[str, Any]:
    """Return a reproducible match state containing only synthetic data."""
    rng = random.Random(seed)
    north = "Northbridge"
    east = "Eastport"
    roles = ["GK", "FB", "CB", "CB", "FB", "DM", "CM", "CM", "W", "ST", "W"]
    north_players = [
        {"id": f"N{i + 1}", "team": north, "number": i + 1, "name": name, "role": roles[i]}
        for i, name in enumerate([
            "Ari Moss", "Ivo Lane", "Noah Reed", "Eli Voss", "Rafi Cole", "Theo Wynn",
            "Jude North", "Milo Vale", "Kai Mercer", "Owen Hart", "Luca Gray",
        ])
    ]
    east_roles = ["GK", "FB", "CB", "CB", "FB", "DM", "CM", "CM", "W", "ST", "W"]
    east_players = [
        {"id": f"E{i + 1}", "team": east, "number": i + 1, "name": name, "role": east_roles[i]}
        for i, name in enumerate([
            "Sam Pike", "Leo Frost", "Ben Alder", "Finn Shore", "Max Field", "Ezra Bell",
            "Remy Stone", "Alex Brook", "Nico Vale", "Cory Lake", "Toby West",
        ])
    ]

    events: list[dict[str, Any]] = []
    attacks: list[dict[str, Any]] = []
    for i in range(1, 25):
        minute = 6 + i * 2.5
        side = "left" if i % 2 else "right"
        switched = i in {19, 20, 21, 22}
        end_type = "cross" if i >= 17 else rng.choice(["pass", "turnover", "shot", "cross"])
        shot = i in {8, 13, 18, 21, 23}
        attacks.append({
            "id": f"A{i:02d}",
            "minute": round(minute, 1),
            "team": north,
            "build_side": side,
            "switched_left_to_right": switched,
            "end_type": end_type,
            "reached_teammate": i in {17, 18, 19, 20, 21},
            "led_to_shot": shot,
        })
        events.append({
            "id": f"EV{i:03d}", "minute": round(minute, 1), "team": north,
            "player_id": f"N{rng.choice([6, 7, 8, 9, 10, 11])}",
            "type": end_type, "outcome": "complete" if end_type != "turnover" else "lost",
            "possession_id": f"POS{i:02d}", "x": round(rng.uniform(20, 84), 1),
            "y": round(rng.uniform(12, 58), 1), "attack_id": f"A{i:02d}",
        })

    events.extend([
        {"id": "EV_CORNER_1", "minute": 67.7, "team": north, "player_id": "N5", "type": "corner", "outcome": "in_play", "possession_id": "POS_CORNER", "x": 105, "y": 0, "attack_id": "A25"},
        {"id": "EV_DUEL_1", "minute": 31.2, "team": north, "player_id": "N8", "type": "duel", "outcome": "won", "possession_id": "POS09", "x": 52, "y": 36},
        {"id": "EV_PASS_1", "minute": 63.2, "team": north, "player_id": "N8", "type": "key_pass", "outcome": "complete", "possession_id": "POS22", "x": 69, "y": 33, "end_x": 87, "end_y": 21},
        {"id": "EV_SHOT_1", "minute": 63.3, "team": north, "player_id": "N9", "type": "shot", "outcome": "saved", "possession_id": "POS22", "x": 88, "y": 21},
    ])

    # Fictional, explicitly tagged one-v-one observations used by the matchup
    # and coaching views. These remain synthetic event records, not LLM guesses.
    matchup_events = [
        {"id": "MX_N8_1", "minute": 31.2, "player_id": "N8", "opponent_id": "E6", "action": "ground duel", "result": "won"},
        {"id": "MX_N8_2", "minute": 48.6, "player_id": "N8", "opponent_id": "E6", "action": "dribble attempt", "result": "stopped"},
        {"id": "MX_N8_3", "minute": 61.1, "player_id": "N8", "opponent_id": "E6", "action": "forward pass", "result": "route blocked"},
        {"id": "MX_N9_1", "minute": 39.4, "player_id": "N9", "opponent_id": "E3", "action": "ground duel", "result": "lost"},
        {"id": "MX_N9_2", "minute": 55.8, "player_id": "N9", "opponent_id": "E3", "action": "dribble attempt", "result": "stopped"},
        {"id": "MX_N9_3", "minute": 63.3, "player_id": "N9", "opponent_id": "E3", "action": "aerial duel", "result": "won"},
        {"id": "MX_E8_1", "minute": 42.0, "player_id": "E8", "opponent_id": "N6", "action": "ground duel", "result": "won"},
        {"id": "MX_E8_2", "minute": 57.6, "player_id": "E8", "opponent_id": "N6", "action": "dribble attempt", "result": "stopped"},
        {"id": "MX_E8_3", "minute": 68.1, "player_id": "E8", "opponent_id": "N6", "action": "forward pass", "result": "route blocked"},
        # Wide one-v-ones: the winger is the ball carrier, the fullback is the defender.
        {"id": "MX_WFB_N9_E2_1", "minute": 21.4, "player_id": "N9", "opponent_id": "E2", "action": "dribble attempt", "result": "stopped", "x": 79, "y": 10},
        {"id": "MX_WFB_N9_E2_2", "minute": 54.2, "player_id": "N9", "opponent_id": "E2", "action": "dribble attempt", "result": "beat defender", "x": 86, "y": 13},
        {"id": "MX_WFB_N11_E5_1", "minute": 28.1, "player_id": "N11", "opponent_id": "E5", "action": "dribble attempt", "result": "beat defender", "x": 77, "y": 58},
        {"id": "MX_WFB_N11_E5_2", "minute": 66.2, "player_id": "N11", "opponent_id": "E5", "action": "forward pass", "result": "route blocked", "x": 83, "y": 56},
        {"id": "MX_WFB_E9_N2_1", "minute": 18.9, "player_id": "E9", "opponent_id": "N2", "action": "dribble attempt", "result": "stopped", "x": 76, "y": 11},
        {"id": "MX_WFB_E9_N2_2", "minute": 50.5, "player_id": "E9", "opponent_id": "N2", "action": "dribble attempt", "result": "beat defender", "x": 86, "y": 14},
        {"id": "MX_WFB_E11_N5_1", "minute": 32.7, "player_id": "E11", "opponent_id": "N5", "action": "dribble attempt", "result": "beat defender", "x": 78, "y": 57},
        {"id": "MX_WFB_E11_N5_2", "minute": 62.4, "player_id": "E11", "opponent_id": "N5", "action": "dribble attempt", "result": "stopped", "x": 84, "y": 54},
    ]

    defensive_responsibilities = [
        {"defender_id": "N3", "opponent_id": "E10", "status": "lost", "minute": 71.9, "evidence": "synthetic assignment ledger"},
        {"defender_id": "N4", "opponent_id": "E11", "status": "held", "minute": 71.9, "evidence": "synthetic assignment ledger"},
        {"defender_id": "N2", "opponent_id": "E9", "status": "late_recovery", "minute": 71.9, "evidence": "synthetic assignment ledger"},
    ]

    history = {
        north: {
            "matches": 7,
            "scored_from_corner": [1, 0, 1, 0, 0, 1, 0],
            "scored_from_direct_free_kick": [0, 0, 0, 0, 0, 0, 0],
            "conceded_from_corner": [0, 0, 0, 1, 0, 0, 0],
            "conceded_from_direct_free_kick": [0, 0, 0, 0, 0, 0, 0],
        },
        east: {
            "matches": 7,
            "scored_from_corner": [0, 1, 0, 0, 0, 0, 1],
            "scored_from_direct_free_kick": [0, 0, 0, 1, 0, 0, 0],
            "conceded_from_corner": [1, 0, 0, 1, 0, 0, 0],
            "conceded_from_direct_free_kick": [0, 0, 1, 0, 0, 0, 0],
        },
    }

    load_windows = {
        "N8": {"role": "CM", "minutes_played": 72, "efforts_20_30": 9, "efforts_60_70": 4, "role_peer_efforts_60_70": [5, 6, 7], "high_speed_distance_20_30_m": 182, "high_speed_distance_60_70_m": 91},
        "N7": {"role": "CM", "minutes_played": 72, "efforts_20_30": 5, "efforts_60_70": 6, "role_peer_efforts_60_70": [5, 6, 7], "high_speed_distance_20_30_m": 110, "high_speed_distance_60_70_m": 123},
    }

    # A pair of all-player position snapshots around a synthetic transition.
    # Coordinates use metres on a 105 x 68 pitch. Player assignments are fictional.
    before = [
        ("N1", 4, 34), ("N2", 54, 12), ("N3", 59, 27), ("N4", 59, 41), ("N5", 54, 56), ("N6", 61, 34),
        ("N7", 68, 24), ("N8", 69, 40), ("N9", 79, 25), ("N10", 82, 34), ("N11", 78, 48),
        ("E1", 102, 34), ("E2", 78, 15), ("E3", 78, 28), ("E4", 78, 41), ("E5", 78, 55), ("E6", 70, 34),
        ("E7", 63, 23), ("E8", 62, 45), ("E9", 85, 21), ("E10", 88, 36), ("E11", 85, 50),
    ]
    after = [
        ("N1", 4, 34), ("N2", 57, 13), ("N3", 63, 24), ("N4", 63, 48), ("N5", 56, 55), ("N6", 65, 32),
        ("N7", 71, 22), ("N8", 72, 42), ("N9", 85, 24), ("N10", 89, 36), ("N11", 84, 51),
        ("E1", 102, 34), ("E2", 76, 16), ("E3", 77, 22), ("E4", 77, 46), ("E5", 77, 56), ("E6", 70, 34),
        ("E7", 64, 21), ("E8", 63, 47), ("E9", 88, 21), ("E10", 91, 34), ("E11", 89, 53),
    ]
    players_by_id = {p["id"]: p for p in north_players + east_players}
    snapshots = []
    for timestamp, points in [(71.9, before), (72.0, after)]:
        snapshots.append({
            "minute": timestamp,
            "positions": [
                {"player_id": pid, "team": players_by_id[pid]["team"], "role": players_by_id[pid]["role"], "number": players_by_id[pid]["number"], "x": x, "y": y}
                for pid, x, y in points
            ],
        })

    return {
        "match": {"id": "SYNTH-008", "home": north, "away": east, "home_score": 1, "away_score": 0, "minute": 72, "second": 18, "is_synthetic": True},
        "players": north_players + east_players,
        "events": sorted(events, key=lambda e: e["minute"]),
        "matchup_events": matchup_events,
        "defensive_responsibilities": defensive_responsibilities,
        "attacks": attacks,
        "history": history,
        "load_windows": load_windows,
        "tracking_snapshots": snapshots,
        "current_event_id": "EV_CORNER_1",
    }


def build_demo_games() -> list[dict[str, Any]]:
    """Return two deterministic, fictional matches with different live situations."""
    first = build_demo_state()
    first["match"]["game_id"] = "northbridge-eastport"
    first["match"]["label"] = "Northbridge vs Eastport"

    second = deepcopy(first)
    def rename(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace("Northbridge", "Harbor City").replace("Eastport", "Redvale").replace("Milo Vale", "Milo Varga")
        if isinstance(value, list):
            return [rename(item) for item in value]
        if isinstance(value, dict):
            return {rename(key): rename(item) for key, item in value.items()}
        return value

    second = rename(second)
    second["match"].update({
        "id": "SYNTH-014", "game_id": "harbor-redvale", "label": "Harbor City vs Redvale",
        "home_score": 0, "away_score": 0, "minute": 59, "second": 42,
    })
    second["current_event_id"] = "EV_FREEKICK_1"
    second["events"].append({
        "id": "EV_FREEKICK_1", "minute": 59.4, "team": "Harbor City", "player_id": "N6",
        "type": "direct_free_kick", "outcome": "awarded", "possession_id": "POS_FREEKICK",
        "x": 83, "y": 32, "attack_id": "A25",
    })
    second["events"].sort(key=lambda event: event["minute"])
    second["matchup_events"] = [
        {**event, "player_id": event["player_id"].replace("N", "N"), "opponent_id": event["opponent_id"].replace("E", "E")}
        for event in second["matchup_events"]
    ]
    second["history"]["Harbor City"]["scored_from_direct_free_kick"] = [1, 0, 0, 0, 1, 0, 0]
    second["history"]["Redvale"]["conceded_from_direct_free_kick"] = [0, 1, 0, 0, 0, 0, 1]

    recent_types = ["pass", "cross", "turnover", "shot", "pass", "pass", "shot", "cross"]
    recent_sides = ["middle", "right", "middle", "left", "middle", "right", "middle", "left"]
    for offset, attack in enumerate(second["attacks"][-8:]):
        attack["end_type"] = recent_types[offset]
        attack["build_side"] = recent_sides[offset]
        attack["switched_left_to_right"] = offset in {1, 5}
    attack_types = {attack["id"]: attack["end_type"] for attack in second["attacks"]}
    for event in second["events"]:
        if event.get("attack_id") in attack_types:
            event["type"] = attack_types[event["attack_id"]]
    return [first, second]
