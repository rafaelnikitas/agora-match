"""Executable acceptance examples with independent expected results.

These verify the synthetic intelligence and claim contract, not live LLM quality.
"""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
import json

from .catalog import build_catalog
from .projection import project_game, event_second
from .player_profiles import in_attacking_box, _aggregate_stats, build_player_profiles
from .chat import answer_question
from .grounding import assemble_draft


def run_checks():
    rows=[]
    def check(name,actual,expected=True):
        rows.append({"check":name,"passed":actual==expected})
    p={"id":"P","team":"Home","role":"W"}
    for name,e,want in [
        ("home box centre",{"x":95,"y":34},True),
        ("corner outside box width",{"x":100,"y":2},False),
        ("box width boundary",{"x":88.5,"y":13.84},True),
        ("outside box length",{"x":88.49,"y":34},False),
        ("missing y is unavailable",{"x":95},False),
        ("explicit reverse direction",{"x":10,"y":34,"attack_direction":-1},True),
    ]: check(name,in_attacking_box(e,p,"Home"),want)
    check("away attacking box",in_attacking_box({"x":12,"y":34},{**p,"team":"Away"},"Home"))
    events=[{"id":"a","player_id":"P","type":"dribble","outcome":"won"},
            {"id":"b","player_id":"P","type":"dribble","outcome":"complete"},
            {"id":"c","player_id":"P","type":"dribble","outcome":"lost"},
            {"id":"d","player_id":"OTHER","receiver_id":"P","type":"pass","outcome":"incomplete"}]
    stats=_aggregate_stats(p,events,[],"Home")
    check("successful dribble outcome vocabulary",stats["successful_dribbles"],2)
    check("failed receiver pass adds no touch",stats["touches"],3)
    check("unsupported physical totals omitted",not ({"sprints","high_speed_distance_m","progressive_carries"}&stats.keys()))
    games=build_catalog()["games"]
    for g in games:
        gid=g["match"]["game_id"]
        for second in [0,1200,1800,min(3600,g["available_through_seconds"]),g["available_through_seconds"]]:
            view=project_game(g,second)
            check(f"{gid} {second}s: no later event",all(event_second(e)<=second for e in view["events"]))
            check(f"{gid} {second}s: no later frame",all(event_second(e)<=second for e in view["tracking_snapshots"]))
            check(f"{gid} {second}s: no later rating",all(event_second(e)<=second for trace in view["match_intelligence"]["rating_timelines"].values() for e in trace))
            answer=answer_question(view,"Show all fullback vs winger cases","analyst")
            check(f"{gid} {second}s: no later visual case",all(event_second(e)<=second for e in answer.get("visualization",{}).get("cases",[])))
            check(f"{gid} {second}s: source cutoff retained",all(f["analysis_seconds"]==second for f in answer["facts"]))
        check(f"{gid}: canonical player history",all(pr["last5_average"]==g["player_history_context"][pr["player_id"]]["last5_average"] for pr in g["player_profiles"]))
        check(f"{gid}: no events beyond fixture",all(event_second(e)<=g["available_through_seconds"] for e in g["events"]))
    g=games[0]
    check("empty attack sample has no invalid fraction", all(f["value"] != "0/0" for f in answer_question(project_game(g,0),"How many attacks ended in crosses?","fan")["facts"]))
    check("kickoff has no goals",project_game(g,0)["match"]["home_score"],0)
    check("before seeded goal has no goal",project_game(g,3066)["match"]["home_score"],0)
    check("goal available at rounded event second",project_game(g,3067)["match"]["home_score"],1)
    check("only one wide case by twenty minutes",len(answer_question(project_game(g,1200),"Show fullback vs winger cases","analyst")["visualization"]["cases"]),1)
    late=deepcopy(g)
    late["events"].append({"id":"ADVERSARIAL_FUTURE","minute":71,"team":g["match"]["home"],"player_id":"N11","type":"shot","outcome":"goal","xg":99})
    check("future mutation cannot alter earlier KPIs",project_game(g,1200)["player_profiles"],project_game(late,1200)["player_profiles"])
    early=project_game(g,3600)
    check("incomplete physical window suppressed",all(r["high_speed_sample_change_pct"] is None for r in early["match_intelligence"]["coach_board"]["players"]))
    check("future paired geometry suppressed",all(r["paired_spacing"] is None for r in early["match_intelligence"]["coach_board"]["players"]))
    for q in ["How is Mystery Striker playing?","Predict the winner","How far did Milo Vale run? distance", "How busy is the referee?"]:
        check("unsupported: "+q,answer_question(g,q,"fan","N8")["topic"],"unsupported")
    facts={"facts":[{"fact_id":"FA","label":"Northbridge corner record","value":"3/7"}],"entities":["Luca Gray"],"caveat":"Small synthetic sample"}
    rendered,ids=assemble_draft('{"lead":"The record adds context.","fact_ids":["FA"]}',facts,600)
    check("canonical fact rendered verbatim",rendered.endswith("Northbridge corner record: 3/7"))
    for name,raw in [
        ("unknown fact ID",'{"lead":"Context.","fact_ids":["UNKNOWN"]}'),
        ("invented numeric prose",'{"lead":"There were 99 goals.","fact_ids":["FA"]}'),
        ("swapped fact value",'{"lead":"Context.","fact_ids":["FA"],"value":"7/3"}'),
        ("wrong retrieved participant",'{"lead":"Luca Gray dominated.","fact_ids":["FA"]}'),
        ("malformed response",'not JSON'),
    ]:
        try: assemble_draft(raw,facts,600); rejected=False
        except ValueError: rejected=True
        check("reject "+name,rejected)
    return {"generated_at":datetime.now(ZoneInfo("Europe/Athens")).isoformat(),"passed":sum(r["passed"] for r in rows),"total":len(rows),
        "scope":"Deterministic synthetic acceptance examples: KPI boundaries, time isolation, historical consistency and claim-format rejection. These do not measure qualitative LLM accuracy.",
        "live_llm_evaluation":"not run; authenticated Foundry access required","checks":rows}
