"""Small evidence-linked, deterministic live recap composer."""

from typing import Any


def compose_live_recap(state: dict[str, Any], insights: list[dict[str, Any]]) -> dict[str, Any]:
    match = state["match"]
    current = next((e for e in state["events"] if e["id"] == state["current_event_id"]), None)
    scoreline = f"{match['home']} {match['home_score']}–{match['away_score']} {match['away']}"
    current_label = current["type"].replace("_", " ") if current else "live play"
    pattern = next((item for item in insights if item["kind"] == "pattern"), None)
    load = next((item for item in insights if item["kind"] == "load"), None)
    key_lines = [item["title"] for item in (pattern, load) if item]
    focus = ". ".join(line.rstrip(".") for line in key_lines) + "." if key_lines else f"The current moment is a {current_label} for {current['team'] if current else match['home']}."
    return {
        "label": f"Match snapshot · through {match['minute']}′",
        "headline": f"{scoreline} · {match['minute']}′",
        "summary": (f"{match['home']} vs {match['away']}. The latest tagged {current_label} for {current['team']} was at {current['minute']}′. " if current else "") + f"{focus} This summarizes the available synthetic snapshot, not a prediction of the final result.",
        "evidence": [
            {"source": "synthetic match state", "metric": "scoreline", "value": f"{match['home_score']}–{match['away_score']}", "minute": match["minute"]},
            {"source": "synthetic event feed", "metric": "current event", "value": current_label, "event_id": current["id"] if current else None, "minute": current["minute"] if current else match["minute"]},
            *([{"source": "ranked insight feed", "metric": "key live pattern", "value": pattern["title"], "insight_id": pattern["id"]}] if pattern else []),
        ],
    }
