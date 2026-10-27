"""One event-time boundary for every answer, KPI, insight and export."""
from __future__ import annotations

from .insights import InsightCoordinator
from .player_profiles import build_player_profiles
from .intelligence import build_match_intelligence
from .recap import compose_live_recap


def event_second(row):
    return int(round(float(row["minute"]) * 60))


def project_game(source: dict, seconds: int | None = None) -> dict:
    latest = source.get("available_through_seconds", source["match"]["minute"] * 60 + source["match"].get("second", 0))
    seconds = int(latest if seconds is None else seconds)
    if not 0 <= seconds <= latest:
        raise ValueError("analysis_time_seconds is outside the available match")
    game = {k:v for k,v in source.items() if k not in {"player_profiles","match_intelligence","insights","recap"}}
    game["match"] = dict(source["match"], minute=seconds//60, second=seconds%60)
    game["available_through_seconds"] = latest
    for key in ("events","attacks","tracking_snapshots","matchup_events"):
        game[key] = [r for r in source.get(key,[]) if event_second(r) <= seconds]
    game["attacks"] = [a for a in game["attacks"] if a.get("available_second",event_second(a)) <= seconds]
    game["current_event_id"] = game["events"][-1]["id"] if game["events"] else None
    goals = [e for e in game["events"] if e["type"] == "shot" and e.get("outcome") == "goal"]
    for side in ("home","away"):
        game["match"][side+"_score"] = sum(e["team"] == game["match"][side] for e in goals)
    game.pop("defensive_responsibilities",None)
    game["load_windows"] = {}
    game["analysis_context"] = {"seconds":seconds,"clock":f"{seconds//60:02}:{seconds%60:02}",
        "coverage":"Tagged event sample; player and speed samples once per minute. Not complete match totals.",
        "event_count":len(game["events"]),"future_evidence_excluded":True}
    game["player_profiles"] = build_player_profiles(game)
    game["match_intelligence"] = build_match_intelligence(game)
    game["insights"] = InsightCoordinator().collect(game)
    if not game["insights"]:
        game["insights"] = [{"id":"context-sample","agent":"Evidence coordinator","kind":"context","rank":1,
            "title":"Follow the next moment", "fan_summary":"No pattern meets the review threshold yet.",
            "explorer_summary":"Inspect the available tagged actions; no pattern meets the current threshold.",
            "studio_summary":"Gather more evidence before drawing a tactical conclusion.","relevance":20,
            "evidence":[{"source":"synthetic event prefix","metric":"tagged actions","value":str(len(game["events"]))}],
            "caveat":"An empty or sparse sample cannot establish a trend.","minute":seconds/60}]
    game["recap"] = compose_live_recap(game,game["insights"])
    return game


def view_patch(game):
    """Static projection without repeated immutable historical ledgers."""
    keys = ("match","analysis_context","events","attacks","tracking_snapshots","current_event_id",
            "insights","recap","player_profiles","match_intelligence")
    patch = {k:game[k] for k in keys}
    patch["player_profiles"] = [{k:v for k,v in p.items() if k not in {"history_matches"}} for p in game["player_profiles"]]
    return patch
