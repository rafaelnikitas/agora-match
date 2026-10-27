"""Evidence retrieval and persona-aware answers for the match chat."""

from __future__ import annotations

import re
from typing import Any


PERSONAS = {"fan", "analyst", "coach"}
HISTORY_TERMS = ("histor", "last 5", "last five", "last 7", "last seven", "season", "average", "compared", "compare", "versus", "vs ")


def _contains(text: str, *words: str) -> bool:
    return any(re.search(r"(?<!\w)" + re.escape(word.strip()) + r"\w*(?!\w)", text) for word in words)


def _player_for(game: dict[str, Any], question: str, selected_player_id: str | None) -> dict[str, Any] | None:
    lowered = question.casefold()
    return next((p for p in game["players"] if p["name"].casefold() in lowered), None) or next(
        (p for p in game["players"] if p["id"] == selected_player_id), None
    )


def _historical_evidence(game: dict[str, Any], question: str, selected_player_id: str | None) -> dict[str, Any] | None:
    """Compare a current-match signal with generated historical match records."""
    q = question.casefold()
    if not any(term in q for term in HISTORY_TERMS):
        return None

    # Preserve the more specific current set-piece vs recent set-piece answer below.
    if _contains(q, "corner", "free kick", "set piece", "set-piece"):
        return None

    explicit_player = next((p for p in game["players"] if p["name"].casefold() in q), None)
    player_context = any(word in q for word in ("player", "form", "performance", "touch", "pass", "goal", "assist", "xg", "xa", "cross", "duel", "speed", "sprint"))
    selected_reference = re.search(r"\b(this player|selected player|his|her)\b", q)
    player = explicit_player or (_player_for(game, question, selected_player_id) if player_context and selected_reference else None)
    if player:
        profile = next((p for p in game["player_profiles"] if p["player_id"] == player["id"]), None)
        if not profile:
            return None
        keys = (
            ("xg", "xG"), ("xa", "xA"), ("touches", "Touches"), ("passes", "Passes"),
            ("goals", "Goals"), ("assists", "Assists"), ("crosses", "Crosses"),
            ("high_speed_efforts", "High-speed samples"), ("high_speed_distance_m", "High-speed distance"),
            ("ground_duels_won", "Ground duels won"), ("aerial_duels_won", "Aerial duels won"),
        )
        selected = next(((key, label) for key, label in keys if key in q or (key == "xg" and "expected goals" in q)), None)
        metrics = [selected] if selected else [(key, label) for key, label in keys[:4]]
        facts = []
        for key, label in metrics:
            current = profile["stats"].get(key)
            recent = profile["last5_average"].get(key)
            season = profile["season_average"].get(key)
            if current is None or recent is None or season is None:
                continue
            digits = 2 if key in {"xg", "xa"} else 1 if key.endswith("_m") else 0
            render = lambda value: f"{value:.{digits}f}".rstrip("0").rstrip(".") if digits else str(round(value))
            facts.extend([
                {"label": f"{label} · current match", "value": render(current), "source": "selected synthetic live match"},
                {"label": f"{label} · last 5 average", "value": render(recent), "source": "five synthetic prior appearances"},
                {"label": f"{label} · season sample average", "value": render(season), "source": f"{profile.get('matches_played', 7)} synthetic prior appearances"},
            ])
        if selected and selected[0] == "xg":
            rate=profile.get("comparable_rates",{}).get("xg_per_shot",{})
            for field,label,denominator in [("current","Current xG per tagged shot","current_denominator"),("last5","Last-five xG per shot","history_denominator")]:
                if rate.get(field) is not None:
                    facts.append({"label":label,"value":rate[field],"source":f"synthetic shot sample; denominator {rate[denominator]} shots"})
        if not facts:
            return None
        first_current, first_recent = facts[0]["value"], facts[1]["value"]
        summary = f"{player['name']}'s current-match {facts[0]['label'].split(' · ')[0].lower()} is {first_current}, compared with {first_recent} per match across the last five synthetic appearances."
        if selected:
            summary += f" The season-sample average is {facts[2]['value']}."
        return {
            "topic": "player_history",
            "player_id": player["id"],
            "summary": summary,
            "facts": facts,
            "caveat": "Historical values are synthetic per-appearance averages. Current totals cover sparse tagged events and are not directly comparable with full historical appearances. Compare per-shot rates where available; no forecast is implied.",
        }

    names = (game["match"]["home"], game["match"]["away"])
    target_teams = [name for name in names if name.casefold() in q]
    if not target_teams:
        target_teams = list(names)
    history_context = game.get("team_history_context", {})
    attacks = game.get("attacks", [])[-8:]
    if any(word in q for word in ("cross", "switch", "wide", "pattern", "tactic")):
        metric_key = "cross_attacks" if any(word in q for word in ("cross", "wide")) else "left_to_right_switches"
        label = "Cross attacks per prior match" if metric_key == "cross_attacks" else "Left-to-right switches per prior match"
        live_label = "Cross-ending attacks in last 8" if metric_key == "cross_attacks" else "Left-to-right switches in last 8"
        facts = []
        for team in target_teams:
            team_attacks = [attack for attack in attacks if attack.get("team") == team]
            if not team_attacks:
                continue
            live_count = sum(
                attack.get("end_type") == "cross" if metric_key == "cross_attacks"
                else bool(attack.get("switched_left_to_right"))
                for attack in team_attacks
            )
            records = history_context.get(team, {}).get("matches", [])
            historical_values = [row.get("tactical_style", {}).get(metric_key, 0) for row in records]
            historical_avg = sum(historical_values) / len(historical_values) if historical_values else 0
            facts.extend([
                {"label": f"{team} · {live_label}", "value": f"{live_count}/{len(team_attacks)}", "source": ", ".join(a["id"] for a in team_attacks) or "no tagged attacks in latest sample"},
                {"label": f"{team} · {label}", "value": f"{historical_avg:.1f}", "source": f"{len(historical_values)} synthetic prior matches"},
            ])
        for team in target_teams:
            attacks_for = [a for a in attacks if a.get("team") == team]
            records = history_context.get(team,{}).get("matches",[])
            denominator = sum(r.get("tactical_style",{}).get("tagged_attacks",0) for r in records)
            numerator = sum(r.get("tactical_style",{}).get(metric_key,0) for r in records)
            if attacks_for and denominator:
                current = sum(a.get("end_type") == "cross" if metric_key == "cross_attacks" else bool(a.get("switched_left_to_right")) for a in attacks_for)
                facts.extend([{"label":f"{team} · current tagged attack share","value":f"{current}/{len(attacks_for)} ({current/len(attacks_for)*100:.1f}%)","source":", ".join(a["id"] for a in attacks_for)},
                    {"label":f"{team} · historical tagged attack share","value":f"{numerator}/{denominator} ({numerator/denominator*100:.1f}%)","source":"seven synthetic prior-match attack samples"}])
        summary = "Compare the tagged attack shares below; raw window counts are included as context."
        caveat = "The live window is the latest tagged attack sample; historical figures are per-match averages from synthetic records. Use attack shares for comparison; raw window totals are not comparable. Synthetic records do not establish a stable tactic."
        return {"topic": "team_history", "summary": summary, "facts": facts, "caveat": caveat}

    facts = [{"label": "Current score", "value": f"{game['match']['home_score']}–{game['match']['away_score']}", "source": f"synthetic live match at {game['match'].get('minute', 0)}′"}]
    for team in target_teams:
        baseline = history_context.get(team, {}).get("summary", {})
        if not baseline:
            continue
        facts.extend([
            {"label": f"{team} · prior record", "value": f"{baseline.get('wins', 0)}W–{baseline.get('draws', 0)}D–{baseline.get('losses', 0)}L", "source": "seven synthetic prior matches"},
            {"label": f"{team} · average xG", "value": baseline.get("mean_xg", "unavailable"), "source": "synthetic prior-match team records"},
            {"label": f"{team} · matches scoring from corners", "value": f"{baseline.get('corner_scoring_matches', 0)}/7", "source": "synthetic prior-match set-piece records"},
        ])
    return {
        "topic": "team_history",
        "summary": "The current score is paired with both teams' recent synthetic form and set-piece context.",
        "facts": facts,
        "caveat": "The historical sample is fictional and descriptive. It gives context for this match, not a prediction.",
    }


def retrieve_evidence(game: dict[str, Any], question: str, selected_player_id: str | None = None) -> dict[str, Any]:
    """Select a small, typed evidence bundle; never let the model query raw data."""
    q = question.casefold()
    match = game["match"]
    unsupported = _contains(q,"referee","predict","bet","injury","medical","weather","stock","yellow card","calories") or ("distance" in q and not _contains(q,"spacing","gap","paired"))
    subject = re.search(r"how is (.+?) (?:playing|doing)",q)
    if subject and subject.group(1) not in {"this player","the player","he","she"} and not any(p["name"].casefold() in subject.group(1) for p in game["players"]):
        unsupported = True
    if unsupported:
        return {"topic":"unsupported","summary":"That player or measurement is not supported by this sample. Try a listed player, attack patterns, set-piece history, or tagged matchups.","facts":[],"caveat":"No unsupported measurement or prediction is inferred."}
    historical = None if _contains(q,"fullback","full-back","winger") else _historical_evidence(game, question, selected_player_id)
    if historical:
        return historical
    if _contains(q, "corner", "free kick", "set piece", "set-piece", "histor", "last 7", "last seven"):
        requested_type = "direct_free_kick" if _contains(q,"free kick") else "corner" if _contains(q,"corner") else None
        event = next((e for e in reversed(game["events"]) if e["type"] in ({requested_type} if requested_type else {"corner","direct_free_kick"})), None)
        history = game.get("history", {})
        if event and event["type"] in {"corner", "direct_free_kick"}:
            attacking = history[event["team"]]
            defending_name = match["away"] if event["team"] == match["home"] else match["home"]
            defending = history[defending_name]
            kind = "corner" if event["type"] == "corner" else "direct_free_kick"
            scored_key, conceded_key = f"scored_from_{kind}", f"conceded_from_{kind}"
            scored = sum(attacking[scored_key]); conceded = sum(defending[conceded_key])
            facts = [
                {"label": f"{event['team']} scored from {kind.replace('_', ' ')}", "value": f"{scored}/{attacking['matches']} matches", "source": "synthetic recent-match aggregate"},
                {"label": f"{defending_name} conceded from {kind.replace('_', ' ')}", "value": f"{conceded}/{defending['matches']} matches", "source": "synthetic recent-match aggregate"},
                {"label": "Latest tagged set piece", "value": f"{event['type'].replace('_', ' ')} at {event['minute']}′", "source": f"event {event['id']}"},
            ]
            summary = (f"{event['team']} scored from {kind.replace('_', ' ')}s in {scored} of their last {attacking['matches']} synthetic matches. "
                       f"{defending_name} conceded from one in {conceded} of their last {defending['matches']}.")
            return {"topic": "history", "summary": summary, "facts": facts, "caveat": f"Only {attacking['matches']} fictional matches are represented. This is context, not a prediction."}
        return {"topic": "history", "summary": "The selected match has synthetic recent-match set-piece aggregates.", "facts": [], "caveat": "The current sample does not match that set-piece situation, so no event-specific comparison is available."}

    if _contains(q, "attack", "cross", "switch", "wide", "pattern", "tactic", "tactical", "left", "right", "build"):
        recent = game.get("attacks", [])[-8:]
        count = len(recent)
        if not count:
            return {"topic":"tactics","summary":"No completed tagged attacks are available at this moment.","facts":[{"label":"Completed tagged attacks","value":0,"source":"synthetic event prefix"}],"caveat":"An empty sample has no crossing or switching rate."}
        crosses = sum(a.get("end_type") == "cross" for a in recent)
        switches = sum(a.get("switched_left_to_right") for a in recent)
        facts = [
            {"label": "Attacks ending in a cross", "value": f"{crosses}/{count}", "source": ", ".join(a["id"] for a in recent if a.get("end_type") == "cross") or "no tagged attacks"},
            {"label": "Left-to-right switches", "value": f"{switches}/{count}", "source": ", ".join(a["id"] for a in recent if a.get("switched_left_to_right")) or "no tagged attacks"},
        ]
        return {"topic": "tactics", "summary": f"In the last {count} tagged attacks, {crosses} ended with a cross and {switches} switched left to right.", "facts": facts, "caveat": "This describes a short synthetic sequence; it does not establish a stable tactic or predict the next attack."}

    if _contains(q, "spacing", "gap", "marking", "shape", "defensive"):
        players = {p["id"]: p for p in game["players"]}
        rows = game["match_intelligence"]["coach_board"]["players"]
        player = next((p for p in game["players"] if p["name"].casefold() in q), None)
        candidates = [row for row in rows if row.get("paired_spacing") and (not player or row["player_id"] == player["id"])]
        row = next((item for item in candidates if item["paired_spacing"]["status"] == "widened"), candidates[0] if candidates else None)
        if row:
            pair = row["paired_spacing"]
            opponent = players[pair["opponent_id"]]
            facts = [
                {"label": "Paired gap at 55′", "value": f"{pair['distance_before_m']} m", "source": "synthetic tracking-derived paired positions"},
                {"label": "Paired gap at 70′", "value": f"{pair['distance_after_m']} m", "source": "synthetic tracking-derived paired positions"},
                {"label": "Tracked pair", "value": f"{row['name']} · {opponent['name']}", "source": "synthetic marking-pair scenario"},
            ]
            wording = "widened" if pair["status"] == "widened" else "changed"
            return {"topic": "spacing", "player_id": row["player_id"], "summary": f"The sampled gap between {row['name']} and {opponent['name']} {wording} from {pair['distance_before_m']} m to {pair['distance_after_m']} m by 70′.", "facts": facts, "caveat": "This is a tracking review cue, not proof of a marking assignment or a tactical error."}
        return {"topic": "spacing", "summary": "No paired-player spacing sample is available for the selected player.", "facts": [], "caveat": "The tracking ledger includes only selected synthetic player pairs."}

    if _contains(q, "fatigue", "tired", "sprint", "running", "speed", "load", "effort"):
        rows = game["match_intelligence"]["coach_board"]["players"]
        player = _player_for(game, question, selected_player_id)
        row = next((r for r in rows if player and r["player_id"] == player["id"]), None)
        if row is None:
            row = next((r for r in rows if r.get("high_speed_sample_change_pct") is not None), None)
        if row and row["high_speed_efforts_20_30"] is not None and row["high_speed_efforts_60_70"] is not None:
            facts = [
                {"label": "High-speed samples, 20–30′", "value": row["high_speed_efforts_20_30"], "source": "minute-sampled synthetic tracking"},
                {"label": "High-speed samples, 60–70′", "value": row["high_speed_efforts_60_70"], "source": "minute-sampled synthetic tracking"},
                {"label": "Maximum sampled speed vs other same-role players", "value": f"{row['max_speed_kmh']} km/h vs {row['role_peer_max_speed_kmh']} km/h", "source": "synthetic tracking and role labels"},
            ]
            return {"topic": "load", "player_id": row["player_id"], "summary": f"{row['name']} recorded {row['high_speed_efforts_20_30']} high-speed samples at 20–30′ and {row['high_speed_efforts_60_70']} at 60–70′.", "facts": facts, "caveat": "A change in sampled running output is not a fatigue diagnosis; role, possession, and opportunity also affect it."}
        return {"topic": "load", "summary": "The paired 20–30′ and 60–70′ windows are not both available yet.", "facts": [], "caveat": "This demo contains sparse synthetic tracking samples."}

    if _contains(q, "fullback", "full-back", "winger", "wingers"):
        players = {p["id"]: p for p in game["players"]}
        rows = []
        for item in game["match_intelligence"]["matchups"]:
            attacker, defender = players[item["player_id"]], players[item["opponent_id"]]
            if {attacker["role"], defender["role"]} != {"W", "FB"}:
                continue
            winger = attacker if attacker["role"] == "W" else defender
            fullback = defender if defender["role"] == "FB" else attacker
            for event in item["events"]:
                rows.append({"event_id": event["event_id"], "minute": event["minute"], "action": event["action"], "result": event["result"], "player_id": winger["id"], "player_name": winger["name"], "opponent_id": fullback["id"], "opponent_name": fullback["name"]})
        rows.sort(key=lambda row: (row["minute"], row["event_id"]))
        wins = sum(row["result"] == "won" for row in rows)
        facts = [
            {"label": "Tagged winger vs fullback cases", "value": len(rows), "source": ", ".join(row["event_id"] for row in rows)},
            {"label": "Winger beat defender", "value": f"{wins}/{len(rows)}" if rows else "Unavailable: no tagged encounters", "source": "synthetic matchup event outcomes"},
            {"label": "Distinct pairings", "value": len({(row["player_id"], row["opponent_id"]) for row in rows}), "source": "synthetic matchup ledger"},
        ]
        return {"topic": "fullback_winger", "summary": f"Found {len(rows)} tagged winger-versus-fullback encounter{'s' if len(rows)!=1 else ''} across {len({(row['player_id'], row['opponent_id']) for row in rows})} pairing{'s' if len({(row['player_id'],row['opponent_id']) for row in rows})!=1 else ''}. Select a case to inspect the prior sampled shape.", "facts": facts, "caveat": "This is the complete tagged synthetic matchup sample, not all moments from the match. The player map uses the prior minute-level snapshot.", "visualization": {"type": "fullback_winger_cases", "cases": rows}}

    if _contains(q, "matchup", "battle", "duel", "against", "beat", "beating", "opponent"):
        player = _player_for(game, question, selected_player_id)
        matchups = game["match_intelligence"]["matchups"]
        rows = [m for m in matchups if not player or m["player_id"] == player["id"] or m["opponent_id"] == player["id"]]
        row = rows[0] if rows else None
        if row:
            reversed_view = bool(player and row["opponent_id"] == player["id"])
            subject = row["opponent_name"] if reversed_view else row["player_name"]
            other = row["player_name"] if reversed_view else row["opponent_name"]
            stopped = row["won"] if reversed_view else row["stopped"]
            facts = [{"label": "Tagged encounters", "value": row["attempts"], "source": ", ".join(e["event_id"] for e in row["events"])}, {"label": "Stopped / won actions", "value": f"{stopped}/{row['attempts']}", "source": "synthetic matchup ledger"}]
            return {"topic": "matchup", "player_id": player["id"] if player else row["player_id"], "summary": f"{subject} had {stopped} stopped actions in {row['attempts']} tagged encounters with {other}.", "facts": facts, "caveat": "This is a small tagged synthetic sample, not a complete duel record."}
        return {"topic": "matchup", "summary": "No tagged one-v-one encounters are available for this player in the selected sample.", "facts": [], "caveat": "No matchup conclusion can be made from missing observations."}

    explicit_player = next((p for p in game["players"] if p["name"].casefold() in q), None)
    asks_player = explicit_player or (_player_for(game, question, selected_player_id) if _contains(q, "player", "he ", "his ", "him ", "form", "performance", "playing", "doing") else None)
    if asks_player:
        player = asks_player
        profile = next(p for p in game["player_profiles"] if p["player_id"] == player["id"])
        stats = profile["stats"]
        timeline = game["match_intelligence"]["rating_timelines"].get(player["id"], [])
        rating = timeline[-1]["rating"] if timeline else 6.0
        facts = [
            {"label": "Goals", "value": stats["goals"], "source": "derived from synthetic shot events"},
            {"label": "xG", "value": stats["xg"], "source": "synthetic shot events"},
            {"label": "Touches", "value": f"{stats['touches']} · rank #{profile['ranks']['touches']}", "source": "synthetic event feed"},
            {"label": "Demo rating", "value": f"{rating}/10", "source": "tagged-action demo model"},
        ]
        return {"topic": "player", "player_id": player["id"], "summary": f"{player['name']} ({player['role']}) has {stats['goals']} goals, {stats['xg']} xG, and {stats['touches']} touches in this synthetic match.", "facts": facts, "caveat": "The rating is a transparent demo score, not an official game rating. Sparse event coverage may miss contributions."}

    if not _contains(q,"story","summary","recap","commentary","happened","match","moment") or _contains(q,"referee","bet","predict","injury","medical","weather","stock"):
        return {"topic":"unsupported","summary":"I cannot answer that from this match sample. Try a player, set-piece history, attack patterns, or tagged matchups.","facts":[],"caveat":"No supporting metric or event query is available for this request."}
    insights = game.get("insights", [])[:3]
    facts = [{"label": item["title"], "value": item["fan_summary"], "source": ", ".join(f.get("event_id", f.get("metric", "match evidence")) for f in item.get("evidence", [])[:3])} for item in insights]
    summary = game.get("recap", {}).get("summary", "No current synthetic match summary is available.")
    return {"topic": "match", "summary": summary, "facts": facts, "caveat": "This answer uses the selected synthetic match only. Ask about a named player, recent pattern, set piece, running output, or matchup for a focused answer."}


def answer_question(game: dict[str, Any], question: str, persona: str, selected_player_id: str | None = None, simplify: bool = False, conversation: list[dict[str, str]] | None = None) -> dict[str, Any]:
    if persona not in PERSONAS:
        raise ValueError("persona must be fan, analyst, or coach")
    retrieval_question = question
    follow_up = re.search(r"\b(that|those|it|they|them|same|compare|compared|what about|and their|and his|and her|how about|what changed)\b", question.casefold())
    if follow_up and conversation:
        previous = next((item.get("content", "") for item in reversed(conversation) if item.get("role") == "user" and item.get("content")), "")
        if previous:
            # Keep the subject and requested historical window together, while avoiding
            # carrying unrelated assistant prose into the evidence-routing query.
            retrieval_question = f"{previous} {question}"
    evidence = retrieve_evidence(game, retrieval_question, selected_player_id)
    summary = evidence["summary"]
    facts = []
    for i, fact in enumerate(evidence["facts"]):
        f = dict(fact, fact_id="F"+chr(65+i))
        f["event_ids"] = [e["id"] for e in game["events"] if e["id"] in f.get("source","") or (e.get("attack_id") and e["attack_id"] in f.get("source",""))]
        f["analysis_seconds"] = game.get("analysis_context",{}).get("seconds",game["match"]["minute"]*60)
        facts.append(f)
    caveat = evidence["caveat"]
    if persona == "fan":
        text = summary
    elif persona == "analyst":
        detail = "; ".join(f"{f['label']}: {f['value']}" for f in facts[:4])
        text = summary + (" Check the supporting sample and its coverage below." if simplify else
                          (f" Evidence: {detail}." if detail else "") + f" Coverage note: {caveat}")
    else:
        detail = "; ".join(f"{f['label']}: {f['value']}" for f in facts[:3])
        text = summary + (" Review cue: confirm this in the replay and discuss the context with the player." if simplify else
                          (f" Review cue: inspect {detail}." if detail else " Review cue: confirm the relevant feed coverage before drawing a conclusion.") + f" Limit: {caveat}")
    result = {
        "text": text,
        "summary": summary,
        "topic": evidence["topic"],
        "facts": facts,
        "caveat": caveat,
        "persona": persona,
        "analysis_context":game.get("analysis_context",{}),
        "entities":[p["name"] for p in game["players"]]+[game["match"]["home"],game["match"]["away"]],
        "supported":bool(facts),
        "model_used": False,
        "reason": "evidence-based deterministic answer",
    }
    if "player_id" in evidence:
        result["player_id"] = evidence["player_id"]
    if "visualization" in evidence:
        result["visualization"] = evidence["visualization"]
    return result
