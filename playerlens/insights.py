"""Evidence-first insight workers and relevance ranking."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Any, Protocol


@dataclass
class Candidate:
    id: str
    agent: str
    kind: str
    title: str
    fan_summary: str
    explorer_summary: str
    studio_summary: str
    relevance: int
    evidence: list[dict[str, Any]]
    caveat: str
    minute: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InsightWorker(Protocol):
    name: str

    def detect(self, state: dict[str, Any]) -> list[Candidate]: ...


def _count(values: list[int]) -> int:
    return sum(1 for value in values if value)


class HistoricalContextAgent:
    name = "Historical Context Agent"

    def detect(self, state: dict[str, Any]) -> list[Candidate]:
        event = next((e for e in reversed(state["events"]) if e["type"] in {"corner","direct_free_kick"}), None)
        if not event or event["type"] not in {"corner", "direct_free_kick"}:
            return []
        home, away = state["match"]["home"], state["match"]["away"]
        attacking = state["history"][event["team"]]
        defending_team = away if event["team"] == home else home
        defending = state["history"][defending_team]
        if event["type"] == "corner":
            scored = _count(attacking["scored_from_corner"])
            conceded = _count(defending["conceded_from_corner"])
            free_kick_conceded = _count(defending["conceded_from_direct_free_kick"])
            title = "A recent corner pattern is relevant now"
            fan = f"{event['team']} scored from a corner in {scored} of its last {attacking['matches']} matches. {defending_team} conceded from one in {conceded} of its last {defending['matches']}."
            explorer = f"Corner goals: {event['team']} {scored}/{attacking['matches']} scored; {defending_team} {conceded}/{defending['matches']} conceded. Direct free-kick goals conceded by {defending_team}: {free_kick_conceded}/{defending['matches']}."
            studio = f"Corner · {event['team']} scored in {scored}/{attacking['matches']} recent; {defending_team} conceded in {conceded}/{defending['matches']}."
            ev = [
                {"source": f"{event['team']} last {attacking['matches']} synthetic matches", "metric": "goals scored from corners", "value": f"{scored}/{attacking['matches']}"},
                {"source": f"{defending_team} last {defending['matches']} synthetic matches", "metric": "goals conceded from corners", "value": f"{conceded}/{defending['matches']}"},
                {"source": f"{defending_team} last {defending['matches']} synthetic matches", "metric": "goals conceded from direct free-kicks", "value": f"{free_kick_conceded}/{defending['matches']}"},
                {"source": "live match", "metric": "current event", "value": "corner", "event_id": event["id"], "minute": event["minute"]},
            ]
        else:
            conceded = _count(defending["conceded_from_corner"])
            scored_fk = _count(attacking["scored_from_direct_free_kick"])
            conceded_fk = _count(defending["conceded_from_direct_free_kick"])
            title = "Recent free-kick outcomes add context to this chance"
            fan = f"{defending_team} conceded a direct free-kick goal in {conceded_fk} of its last {defending['matches']} matches. {event['team']} scored from one in {scored_fk} of its last {attacking['matches']}."
            explorer = f"Direct free-kick goals: {event['team']} {scored_fk}/{attacking['matches']} scored; {defending_team} {conceded_fk}/{defending['matches']} conceded. Corner goals conceded by {defending_team}: {conceded}/{defending['matches']}."
            studio = f"Direct free-kick · {event['team']} scored in {scored_fk}/{attacking['matches']}; {defending_team} conceded in {conceded_fk}/{defending['matches']}."
            ev = [
                {"source": f"{event['team']} last {attacking['matches']} synthetic matches", "metric": "goals scored from direct free-kicks", "value": f"{scored_fk}/{attacking['matches']}"},
                {"source": f"{defending_team} last {defending['matches']} synthetic matches", "metric": "goals conceded from direct free-kicks", "value": f"{conceded_fk}/{defending['matches']}"},
                {"source": f"{defending_team} last {defending['matches']} synthetic matches", "metric": "goals conceded from corners", "value": f"{conceded}/{defending['matches']}"},
                {"source": "live match", "metric": "current event", "value": "direct free-kick", "event_id": event["id"], "minute": event["minute"]},
            ]
        return [Candidate(
            id="history-set-piece", agent=self.name, kind="history", title=title,
            fan_summary=fan,
            explorer_summary=explorer,
            studio_summary=studio,
            relevance=100, evidence=ev, caveat="Seven fictional matches are a small sample; these counts are context, not a prediction.", minute=float(event["minute"]),
        )]


class LivePatternAgent:
    name = "Live Pattern Agent"

    def detect(self, state: dict[str, Any]) -> list[Candidate]:
        attacks = state["attacks"]
        recent8 = attacks[-8:]
        last6 = attacks[-6:]
        findings = []
        crosses = sum(a["end_type"] == "cross" for a in recent8)
        caught = sum(a["reached_teammate"] for a in recent8)
        shots = sum(a["led_to_shot"] for a in recent8)
        if crosses >= 6:
            findings.append(Candidate(
                id="pattern-crosses", agent=self.name, kind="pattern", title=f"{crosses} of the last {len(recent8)} attacks ended in a cross",
                fan_summary=f"{state['match']['home']} have repeatedly gone wide: {crosses} of their last {len(recent8)} attacks ended with a cross.",
                explorer_summary=f"Recent {len(recent8)} attacks: {crosses} ended in crosses; {caught} reached a teammate; {shots} led to a shot.",
                studio_summary=f"{crosses}/{len(recent8)} recent attacks ended with a cross.", relevance=82,
                evidence=[{"source": "current synthetic match", "metric": "cross-ending attacks", "value": f"{crosses}/{len(recent8)}", "event_ids": [a["id"] for a in recent8]},
                          {"source": "current synthetic match", "metric": "crosses reaching teammate", "value": str(caught)},
                          {"source": "current synthetic match", "metric": "crosses leading to shot", "value": str(shots)}],
                caveat="This describes the recent attack sequence; it does not prove the team will continue crossing.", minute=float(recent8[-1]["minute"]),
            ))
        central = sum(a.get("build_side") == "middle" for a in recent8)
        if central >= 4:
            home = state["match"]["home"]
            findings.append(Candidate(
                id="pattern-central-build", agent=self.name, kind="pattern", title=f"{home} are building through central lanes",
                fan_summary=f"{home} built through the middle in {central} of their last {len(recent8)} attacks, looking for a route through the centre.",
                explorer_summary=f"Central build-up: {central}/{len(recent8)} recent attacks; {shots} of those eight attacks led to a shot.",
                studio_summary=f"{home} built centrally in {central}/{len(recent8)} recent attacks.", relevance=78,
                evidence=[{"source": "current synthetic match", "metric": "attacks built through middle", "value": f"{central}/{len(recent8)}", "event_ids": [a["id"] for a in recent8 if a.get("build_side") == "middle"]}],
                caveat="This describes the recent attack sequence; it does not establish a permanent team tactic.", minute=float(recent8[-1]["minute"]),
            ))
        switches = sum(a["switched_left_to_right"] for a in last6)
        switch_shots = sum(a["switched_left_to_right"] and a["led_to_shot"] for a in last6)
        if switches >= 3:
            findings.append(Candidate(
                id="pattern-switch", agent=self.name, kind="pattern", title=f"{state['match']['home']} are switching play from left to right",
                fan_summary=f"{state['match']['home']} switched from left to right in {switches} of their last {len(last6)} attacks. This records the direction of play, not its cause.",
                explorer_summary=f"Left-to-right switches: {switches}/{len(last6)} recent attacks; {switch_shots} of those attacks led to a shot.",
                studio_summary=f"{state['match']['home']} switched left→right in {switches}/{len(last6)} recent attacks.", relevance=76,
                evidence=[{"source": "current synthetic match", "metric": "left-to-right switches", "value": f"{switches}/{len(last6)}", "event_ids": [a["id"] for a in last6 if a["switched_left_to_right"]]},
                          {"source": "current synthetic match", "metric": "switched attacks leading to shot", "value": str(switch_shots)}],
                caveat="A pattern in six attacks is descriptive and may reflect the opponent's shape or the match situation.", minute=float(last6[-1]["minute"]),
            ))
        return findings


class PlayerLoadAgent:
    name = "Player Load Agent"

    def detect(self, state: dict[str, Any]) -> list[Candidate]:
        if state["match"]["minute"] < 70:
            return []
        player = next(p for p in state["players"] if p["id"] == "N8")
        if state.get("analysis_context"):
            for peer in (p for p in state["players"] if p["role"] == player["role"]):
                for start,end in [(20,30),(60,70)]:
                    covered={snap["minute"] for snap in state["tracking_snapshots"] if start <= snap["minute"] < end for point in snap["positions"] if point["player_id"] == peer["id"] and "speed_kmh" in point}
                    if covered != set(range(start,end)):
                        return []

        if state.get("load_windows"):
            data = state["load_windows"][player["id"]]
            effort_counts = {p["id"]: {"early": state["load_windows"].get(p["id"], {}).get("efforts_20_30", 0), "late": state["load_windows"].get(p["id"], {}).get("efforts_60_70", 0)} for p in state["players"]}
        else:
            data = None
            effort_counts = {}
            for p in state["players"]:
                effort_counts[p["id"]] = {
                    "early": sum(point["speed_kmh"] >= 20 for snap in state["tracking_snapshots"] if 20 <= snap["minute"] < 30 for point in snap["positions"] if point["player_id"] == p["id"]),
                    "late": sum(point["speed_kmh"] >= 20 for snap in state["tracking_snapshots"] if 60 <= snap["minute"] < 70 for point in snap["positions"] if point["player_id"] == p["id"]),
                }
        role_peers = data["role_peer_efforts_60_70"] if data else [effort_counts[p["id"]]["late"] for p in state["players"] if p["role"] == player["role"] and p["id"] != player["id"]]
        peer_mid = median(role_peers) if role_peers else 0
        early, recent = effort_counts[player["id"]]["early"], effort_counts[player["id"]]["late"]
        if early == 0 or recent / early > 0.7 or recent >= peer_mid:
            return []
        drop_pct = round((1 - recent / early) * 100)
        return [Candidate(
            id="load-output-drop", agent=self.name, kind="load", title=f"{player['name']}'s high-speed output has dropped",
            fan_summary=f"{player['name']} made fewer high-speed samples later in the match: {recent} versus {early} earlier. The samples alone cannot explain the change.",
            explorer_summary=f"High-speed samples per 10-minute window fell {drop_pct}% ({early} at 20–30′ to {recent} at 60–70′). Same-role peers had a median of {peer_mid} in the later window.",
            studio_summary=f"{player['name']} high-speed samples: {early} early → {recent} late; same-role median {peer_mid}. Possible output drop.", relevance=64,
            evidence=[{"source": "minute-by-minute synthetic tracking", "metric": "high-speed samples, 20–30′ (speed ≥20 km/h)", "value": str(early), "player_id": player["id"]},
                      {"source": "minute-by-minute synthetic tracking", "metric": "high-speed samples, 60–70′ (speed ≥20 km/h)", "value": str(recent), "player_id": player["id"]},
                      {"source": "same-role synthetic tracking", "metric": "median high-speed samples, 60–70′", "value": str(peer_mid), "role": player["role"]}],
            caveat="Sampled output change, not a diagnosis of fatigue. Role, possession, score, and sprint opportunities also affect running output; maximum speed alone is not enough.", minute=70.0,
        )]


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


class ShapeAgent:
    name = "Defensive Shape Agent"

    def detect(self, state: dict[str, Any]) -> list[Candidate]:
        if state.get("analysis_context") and not {55,70}.issubset({s["minute"] for s in state["tracking_snapshots"]}):
            return []
        if len(state["tracking_snapshots"]) > 10:
            before = min(state["tracking_snapshots"], key=lambda snap: abs(snap["minute"] - 55))
            after = min(state["tracking_snapshots"], key=lambda snap: abs(snap["minute"] - 70))
        else:
            before, after = state["tracking_snapshots"]
        def by_id(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
            return {p["player_id"]: p for p in snapshot["positions"]}
        b, a = by_id(before), by_id(after)
        gap_before = _distance(b["E3"], b["E4"])
        gap_after = _distance(a["E3"], a["E4"])
        attackers = [a["N9"], a["N10"], a["N11"]]
        defenders = [a[f"E{i}"] for i in range(2, 9)]
        uncovered = [attacker for attacker in attackers if min(_distance(attacker, defender) for defender in defenders) > 5]
        if gap_after - gap_before < 6 or not uncovered:
            return []
        return [Candidate(
            id="shape-gap", agent=self.name, kind="shape", title=f"A channel is opening in {state['match']['away']}'s defence",
            fan_summary=f"{state['match']['away']}'s back line is stretching out. An opponent moved into the space between defenders, with no nearby defender within 5 metres in the latest frame.",
            explorer_summary=f"Gap between synthetic tracking points E3 and E4 grew from {gap_before:.0f}m to {gap_after:.0f}m across the two snapshots. {len(uncovered)} of 3 {state['match']['home']} attackers were more than 5m from the nearest defender in the later frame.",
            studio_summary=f"{state['match']['away']} defensive gap widened {gap_before:.0f}m→{gap_after:.0f}m; runner in channel. Shape alert.", relevance=88,
            evidence=[{"source": "synthetic tracking snapshot", "metric": "E3–E4 spacing before / after", "value": f"{gap_before:.1f}m / {gap_after:.1f}m", "minutes": [before["minute"], after["minute"]]},
                      {"source": "synthetic tracking snapshot", "metric": "attackers >5m from nearest defender", "value": f"{len(uncovered)}/3", "minutes": after["minute"]}],
            caveat="This identifies open space in sampled synthetic tracking, not individual marking responsibility.", minute=after["minute"],
        )]


class InsightCoordinator:
    """Runs specialized workers against shared state and ranks evidence-backed findings."""

    def __init__(self, workers: list[InsightWorker] | None = None):
        self.workers = workers or [HistoricalContextAgent(), LivePatternAgent(), PlayerLoadAgent(), ShapeAgent()]

    def collect(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = [candidate for worker in self.workers for candidate in worker.detect(state)]
        # Ranking is transparent: current event relevance first, then repeated live pattern,
        # geometry/load alerts, with evidence kept visible for every item.
        candidates.sort(key=lambda item: (-item.relevance, -len(item.evidence), item.id))
        return [candidate.to_dict() | {"rank": i + 1} for i, candidate in enumerate(candidates)]
