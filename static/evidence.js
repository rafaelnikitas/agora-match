/* Pure browser fallback. Every input is an already time-filtered match view. */
const AgoraEvidence = (() => {
  function answer(game,question,persona,playerId,simplify=false,conversation=[]) {
    const activeGame=game, sourceGame=game, playerSelect={value:playerId};
    const playerFor=id=>game.players.find(p=>p.id===id);
    const profileFor=id=>game.player_profiles.find(p=>p.player_id===id);
function chatEvidence(question) {
  const q = question.toLowerCase();
  const has = (...terms) => terms.some((term) => new RegExp("\\b" + term.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&") + "\\w*").test(q));
  const person = activeGame.players.find((p) => q.includes(p.name.toLowerCase())) || playerFor(playerSelect.value);
  const unavailable=has("referee","predict","bet","injury","medical","weather","stock","yellow card","calories") || (q.includes("distance") && !has("spacing","gap","paired"));
  const subject=q.match(/how is (.+?) (?:playing|doing)/);
  if(unavailable || (subject && !["this player","the player","he","she"].includes(subject[1]) && !activeGame.players.some(p=>subject[1].includes(p.name.toLowerCase())))) return {topic:"unsupported",summary:"That player or measurement is not supported by this sample. Try a listed player, attack patterns, set-piece history, or tagged matchups.",facts:[],caveat:"No unsupported measurement or prediction is inferred."};
  const facts = [];
  let summary = ""; let caveat = ""; let topic = "match";
  const historical = /histor|last\s*(5|five|7|seven)|season|average|compar|versus|\bvs\b/i.test(q);
  const namedPerson = activeGame.players.find((p) => q.includes(p.name.toLowerCase()));
  const playerMetric = /player|form|performance|touch|pass|goal|assist|\bxg\b|\bxa\b|cross|duel|speed|sprint|workload/i.test(q);
  if (historical && !has("corner", "free kick", "set piece", "set-piece") && (namedPerson || playerMetric)) {
    const historicalPlayer = namedPerson || (playerMetric && /\b(this player|his|her|their)\b/i.test(q) ? person : null);
    if (historicalPlayer) {
      topic = "player_history";
      const profile = profileFor(historicalPlayer.id);
      const keys = [["xg","xG"],["xa","xA"],["touches","Touches"],["passes","Passes"],["goals","Goals"],["assists","Assists"],["crosses","Crosses"],["high_speed_efforts","High-speed samples"]];
      const metric = keys.find(([key,label]) => q.includes(key) || q.includes(label.toLowerCase()));
      const chosen = metric ? [metric] : keys.slice(0,4);
      const fmt = (key,value) => ["xg","xa"].includes(key) ? Number(value).toFixed(2).replace(/0+$/," ").trim().replace(/\.$/,"") : Math.round(value).toString();
      for (const [key,label] of chosen) {
        const current = profile.stats[key], recent = profile.last5_average[key], season = profile.season_average[key];
        if ([current,recent,season].some((v)=>v === undefined || v === null)) continue;
        facts.push({label:`${label} · current match`,value:fmt(key,current),source:"selected synthetic live match"},{label:`${label} · last 5 average`,value:fmt(key,recent),source:"five synthetic prior appearances"},{label:`${label} · season sample average`,value:fmt(key,season),source:`${profile.history_matches?.length || 7} synthetic prior appearances`});
      }
      if(metric?.[0]==="xg") {
        const rates=profile.comparable_rates?.xg_per_shot;
        if(rates?.current !== null && rates?.current !== undefined) facts.push({label:"Current xG per tagged shot",value:rates.current,source:`synthetic shot sample; denominator ${rates.current_denominator} shots`});
        if(rates?.last5 !== null && rates?.last5 !== undefined) facts.push({label:"Last-five xG per shot",value:rates.last5,source:`synthetic shot sample; denominator ${rates.history_denominator} shots`});
      }
      const label = facts[0]?.label.split(" · ")[0].toLowerCase() || "match output";
      summary = `${historicalPlayer.name}'s current-match ${label} is ${facts[0]?.value ?? "unavailable"}, compared with ${facts[1]?.value ?? "unavailable"} per match across the last five synthetic appearances.`;
      caveat = "Historical values are synthetic per-appearance averages. Current tagged totals and full historical appearances have different coverage. Compare per-shot rates where available; this is not a forecast.";
    } else {
      const teams = [activeGame.match.home,activeGame.match.away].filter((team)=>q.includes(team.toLowerCase()));
      const targetTeams = teams.length ? teams : [activeGame.match.home,activeGame.match.away];
      const context = activeGame.team_history_context || {};
      const tactical = /cross|wide|switch|pattern|tactic/i.test(q);
      topic = "team_history";
      if (tactical) {
        const metric = /cross|wide/i.test(q) ? "cross_attacks" : "left_to_right_switches";
        const live = activeGame.attacks.slice(-8);
        for (const team of targetTeams) {
          const rows = live.filter((a)=>a.team === team);
          if (!rows.length) continue;
          const count = rows.filter((a)=>metric === "cross_attacks" ? a.end_type === "cross" : a.switched_left_to_right).length;
          const matches = context[team]?.matches || [];
          const avg = matches.length ? matches.reduce((sum,m)=>sum+(m.tactical_style?.[metric] || 0),0)/matches.length : 0;
          facts.push({label:`${team} · live tagged ${metric === "cross_attacks" ? "cross attacks" : "switches"}`,value:`${count}/${rows.length}`,source:rows.map((a)=>a.id).join(", ") || "no tagged attacks"},{label:`${team} · historical per-match average`,value:avg.toFixed(1),source:`${matches.length} synthetic prior matches`});
        }
        for(const team of targetTeams) {
          const rows=live.filter(a=>a.team===team), matches=context[team]?.matches || [];
          const n=matches.reduce((sum,m)=>sum+(m.tactical_style?.[metric]||0),0), d=matches.reduce((sum,m)=>sum+(m.tactical_style?.tagged_attacks||0),0);
          if(rows.length && d) { const c=rows.filter(a=>metric === "cross_attacks" ? a.end_type === "cross" : a.switched_left_to_right).length;
            facts.push({label:`${team} · current tagged attack share`,value:`${c}/${rows.length} (${(c/rows.length*100).toFixed(1)}%)`,source:rows.map(a=>a.id).join(", ")},{label:`${team} · historical tagged attack share`,value:`${n}/${d} (${(n/d*100).toFixed(1)}%)`,source:"seven synthetic prior-match attack samples"}); }
        }
        summary = "Compare tagged attack shares; raw counts are shown only as context.";
        caveat = "The live window is the latest tagged attack sample; historical values are per-match averages from synthetic records. Use shares for comparison; raw window totals are not comparable. Synthetic records do not establish a stable tactic.";
      } else {
        facts.push({label:"Current score",value:`${activeGame.match.home_score}–${activeGame.match.away_score}`,source:`synthetic live match at ${activeGame.match.minute}′`});
        for (const team of targetTeams) {
          const baseline = context[team]?.summary;
          if (!baseline) continue;
          facts.push({label:`${team} · prior record`,value:`${baseline.wins}W–${baseline.draws}D–${baseline.losses}L`,source:"seven synthetic prior matches"},{label:`${team} · average xG`,value:baseline.mean_xg,source:"synthetic prior-match team records"},{label:`${team} · matches scoring from corners`,value:`${baseline.corner_scoring_matches}/7`,source:"synthetic prior-match set-piece records"});
        }
        summary = "The live score is paired with recent synthetic form and set-piece context.";
        caveat = "The historical sample is fictional and descriptive. It gives context for this match, not a prediction.";
      }
    }
  } else if (has("fullback", "full-back", "winger", "wingers")) {
    topic = "fullback_winger";
    const byId = Object.fromEntries(activeGame.players.map((p) => [p.id, p]));
    const cases = activeGame.match_intelligence.matchups.flatMap((item) => {
      const attacker = byId[item.player_id], defender = byId[item.opponent_id];
      if (!attacker || !defender || new Set([attacker.role, defender.role]).size !== 2 || ![attacker.role, defender.role].includes("W") || ![attacker.role, defender.role].includes("FB")) return [];
      const winger = attacker.role === "W" ? attacker : defender; const fullback = attacker.role === "FB" ? attacker : defender;
      return item.events.map((e) => ({event_id:e.event_id,minute:e.minute,action:e.action,result:e.result,player_id:winger.id,player_name:winger.name,opponent_id:fullback.id,opponent_name:fullback.name}));
    }).sort((a,b)=>a.minute-b.minute);
    const wins = cases.filter((c)=>c.result === "won").length;
    summary = `Found ${cases.length} tagged winger-versus-fullback encounter${cases.length===1 ? "" : "s"} across ${new Set(cases.map((c)=>c.player_id+":"+c.opponent_id)).size} pairing${new Set(cases.map(c=>c.player_id+":"+c.opponent_id)).size===1 ? "" : "s"}. Select a case to inspect the prior sampled shape.`;
    facts.push({label:"Tagged encounters",value:cases.length,source:cases.map((c)=>c.event_id).join(", ")},{label:"Winger beat defender",value:cases.length ? `${wins}/${cases.length}` : "Unavailable: no tagged encounters",source:"synthetic matchup event outcomes"},{label:"Distinct pairings",value:new Set(cases.map((c)=>c.player_id+":"+c.opponent_id)).size,source:"synthetic matchup ledger"});
    caveat = "This is the complete tagged synthetic matchup sample, not all moments from the match. The player map uses the prior minute-level snapshot.";
    return {topic,summary,facts,caveat,visualization:{type:"fullback_winger_cases",cases}};
  } else if (has("corner", "free kick", "set piece", "set-piece", "histor", "last 7", "last seven")) {
    topic = "history"; const ev = [...activeGame.events].reverse().find(e=>has("free kick") ? e.type==="direct_free_kick" : has("corner") ? e.type==="corner" : ["corner","direct_free_kick"].includes(e.type)); const h = activeGame.history;
    if (ev && ["corner", "direct_free_kick"].includes(ev.type)) {
      const type = ev.type; const attacking = h[ev.team]; const defendingName = ev.team === activeGame.match.home ? activeGame.match.away : activeGame.match.home; const defending = h[defendingName];
      const scored = attacking[`scored_from_${type}`].reduce((a,b)=>a+b,0); const conceded = defending[`conceded_from_${type}`].reduce((a,b)=>a+b,0);
      summary = `${ev.team} scored from ${type.replaceAll("_"," ")}s in ${scored} of their last ${attacking.matches} synthetic matches. ${defendingName} conceded from one in ${conceded} of their last ${defending.matches}.`;
      facts.push({label:`${ev.team} scored from ${type.replaceAll("_"," ")}`,value:`${scored}/${attacking.matches} matches`,source:"synthetic recent-match aggregate"},{label:`${defendingName} conceded from ${type.replaceAll("_"," ")}`,value:`${conceded}/${defending.matches} matches`,source:"synthetic recent-match aggregate"},{label:"Current event",value:`${type.replaceAll("_"," ")} at ${ev.minute}′`,source:`event ${ev.id}`});
      caveat = `Only ${attacking.matches} fictional matches are represented. This is context, not a prediction.`;
    } else { summary = "Recent synthetic set-piece aggregates are available, but the current event is not a matching set piece."; caveat = "No event-specific comparison is available."; }
  } else if (has("attack", "cross", "switch", "wide", "pattern", "tactic", "tactical", "left", "right", "build")) {
    topic = "tactics"; const recent = activeGame.attacks.slice(-8); if(!recent.length) return {topic:"tactics",summary:"No completed tagged attacks are available at this moment.",facts:[{label:"Completed tagged attacks",value:0,source:"synthetic event prefix"}],caveat:"An empty sample has no crossing or switching rate."}; const crosses = recent.filter((a)=>a.end_type === "cross").length; const switches = recent.filter((a)=>a.switched_left_to_right).length;
    summary = `In the last ${recent.length} tagged attacks, ${crosses} ended with a cross and ${switches} switched left to right.`;
    facts.push({label:"Attacks ending in a cross",value:`${crosses}/${recent.length}`,source:recent.filter((a)=>a.end_type === "cross").map((a)=>a.id).join(", ") || "no tagged attacks"},{label:"Left-to-right switches",value:`${switches}/${recent.length}`,source:recent.filter((a)=>a.switched_left_to_right).map((a)=>a.id).join(", ") || "no tagged attacks"});
    caveat = "This describes a short synthetic sequence; it does not establish a stable tactic or predict the next attack.";
  } else if (has("spacing", "gap", "marking", "shape", "defensive")) {
    topic = "spacing"; const named = activeGame.players.find((p)=>q.includes(p.name.toLowerCase())); const rows = activeGame.match_intelligence.coach_board.players.filter((r)=>r.paired_spacing && (!named || r.player_id === named.id)); const row = rows.find((r)=>r.paired_spacing.status === "widened") || rows[0];
    if (row) { const pair = row.paired_spacing; const opponent = playerFor(pair.opponent_id); const word = pair.status === "widened" ? "widened" : "changed"; summary = `The sampled gap between ${row.name} and ${opponent?.name || "their paired opponent"} ${word} from ${pair.distance_before_m} m to ${pair.distance_after_m} m by 70′.`; facts.push({label:"Paired gap at 55′",value:`${pair.distance_before_m} m`,source:"synthetic tracking-derived paired positions"},{label:"Paired gap at 70′",value:`${pair.distance_after_m} m`,source:"synthetic tracking-derived paired positions"},{label:"Tracked pair",value:`${row.name} · ${opponent?.name || pair.opponent_id}`,source:"synthetic marking-pair scenario"}); }
    else summary = "No paired-player spacing sample is available for the selected player.";
    caveat = "This is a tracking review cue, not proof of a marking assignment or a tactical error.";
  } else if (has("fatigue", "tired", "sprint", "running", "speed", "load", "effort")) {
    topic = "load"; const row = activeGame.match_intelligence.coach_board.players.find((r)=>r.player_id === person?.id) || activeGame.match_intelligence.coach_board.players.find((r)=>r.high_speed_sample_change_pct !== null);
    if (row && row.high_speed_efforts_20_30 !== null && row.high_speed_efforts_60_70 !== null) { summary = `${row.name} recorded ${row.high_speed_efforts_20_30} high-speed samples at 20–30′ and ${row.high_speed_efforts_60_70} at 60–70′.`; facts.push({label:"High-speed samples, 20–30′",value:row.high_speed_efforts_20_30,source:"minute-sampled synthetic tracking"},{label:"High-speed samples, 60–70′",value:row.high_speed_efforts_60_70,source:"minute-sampled synthetic tracking"},{label:"Peak speed vs same-role peers",value:`${row.max_speed_kmh} km/h vs ${row.role_peer_max_speed_kmh} km/h`,source:"synthetic tracking and role labels"}); }
    else summary = "Both complete time windows are not available yet.";
    caveat = "A change in sampled running output is not a fatigue diagnosis; role, possession, and opportunity also affect it.";
  } else if (has("matchup", "battle", "duel", "against", "beat", "beating", "opponent")) {
    topic = "matchup"; const item = activeGame.match_intelligence.matchups.find((m)=>!person || m.player_id === person.id || m.opponent_id === person.id);
    if (item) { const reversed = person && item.opponent_id === person.id; const subject = reversed ? item.opponent_name : item.player_name; const other = reversed ? item.player_name : item.opponent_name; const stopped = reversed ? item.won : item.stopped; summary = `${subject} had ${stopped} stopped actions in ${item.attempts} tagged encounters with ${other}.`; facts.push({label:"Tagged encounters",value:item.attempts,source:item.events.map((e)=>e.event_id).join(", ")},{label:"Stopped / won actions",value:`${stopped}/${item.attempts}`,source:"synthetic matchup ledger"}); }
    else summary = "No tagged one-v-one encounters are available for this player in the selected sample.";
    caveat = "This is a small tagged synthetic sample, not a complete duel record.";
  } else if (person && (q.includes(person.name.toLowerCase()) || has("player", "he ", "his ", "him ", "form", "performance", "playing", "doing"))) {
    topic = "player"; const profile = profileFor(person.id); const stats = profile.stats; const timeline = activeGame.match_intelligence.rating_timelines[person.id] || []; const rating = timeline.length ? timeline[timeline.length-1].rating : 6;
    summary = `${person.name} (${person.role}) has ${stats.goals} goals, ${stats.xg} xG, and ${stats.touches} touches in this synthetic match.`;
    facts.push({label:"Goals",value:stats.goals,source:"derived from synthetic shot events"},{label:"xG",value:stats.xg,source:"synthetic shot events"},{label:"Touches",value:`${stats.touches} · rank #${profile.ranks.touches}`,source:"synthetic event feed"},{label:"Demo rating",value:`${rating}/10`,source:"tagged-action demo model"});
    caveat = "The rating is a transparent demo score, not an official game rating. Sparse event coverage may miss contributions.";
  } else if (!has("story","summary","recap","commentary","happened","match","moment") || has("referee","bet","predict","injury","medical","weather","stock")) {
    topic="unsupported"; summary="I cannot answer that from this sample. Try a player, attack patterns, set-piece history, or tagged matchups."; caveat="No supporting query is available for this request.";
  } else {
    topic = "match"; summary = activeGame.recap.summary; facts.push(...activeGame.insights.slice(0,3).map((item)=>({label:item.title,value:item.fan_summary,source:item.evidence.slice(0,2).map((e)=>e.event_id || e.metric).join(", ")}))); caveat = "This answer uses the selected synthetic match only. Ask about a named player, recent pattern, set piece, running output, or matchup for a focused answer.";
  }
  return {topic,summary,facts,caveat};
}

function localChatAnswer(question, persona, simplify = false, conversation = []) {
  const effectivePersona = persona;
  const priorUser = [...conversation].reverse().find((turn)=>turn.role === "user" && turn.content);
  const followUp = /\b(that|those|it|they|them|same|compare|compared|what about|and their|and his|and her|how about|what changed)\b/i.test(question);
  const retrievalQuestion = followUp && priorUser ? `${priorUser.content} ${question}` : question;
  const evidence = chatEvidence(retrievalQuestion); const detail = evidence.facts.slice(0, effectivePersona === "analyst" ? 4 : 3).map((f)=>`${f.label}: ${f.value}`).join("; ");
  let text;
  if (effectivePersona === "fan") text = evidence.summary;
  else if (effectivePersona === "analyst") text = evidence.summary + (simplify ? " Check the supporting sample and its coverage below." : (detail ? ` Evidence: ${detail}.` : "") + ` Coverage note: ${evidence.caveat}`);
  else text = evidence.summary + (simplify ? " Review cue: confirm this in the replay and discuss the context with the player." : (detail ? ` Review cue: inspect ${detail}.` : " Review cue: confirm feed coverage before drawing a conclusion.") + ` Limit: ${evidence.caveat}`);
  const facts=evidence.facts.map((f,i)=>({...f,fact_id:"F"+String.fromCharCode(65+i),analysis_seconds:activeGame.analysis_context.seconds,event_ids:sourceGame.events.filter(e=>(String(f.source||"").includes(e.id) || (e.attack_id && String(f.source||"").includes(e.attack_id))) && Math.round(e.minute*60)<=activeGame.analysis_context.seconds).map(e=>e.id)}));
  return {analysis_context:activeGame.analysis_context,supported:!!facts.length,text,summary:evidence.summary,topic:evidence.topic,facts,caveat:evidence.caveat,visualization:evidence.visualization,model_used:false,reason:"evidence-based local demo"};
}

    return localChatAnswer(question,persona,simplify,conversation);
  }
  function projectView(source,patch) {
    const seconds=patch.analysis_context.seconds;
    return {...source,...patch,
      tracking_snapshots:source.tracking_snapshots.filter(s=>Math.round(s.minute*60)<=seconds),
      matchup_events:(source.matchup_events || []).filter(e=>Math.round(e.minute*60)<=seconds)};
  }
  return {answer,projectView};
})();
if(typeof module !== "undefined") module.exports=AgoraEvidence;
