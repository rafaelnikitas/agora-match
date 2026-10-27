/* Role-specific presentation. All numbers come from the shared synthetic catalog. */
const AgoraExperience = (() => {
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const icons = {
    play:'<path d="m9 5 11 7-11 7V5Z"/>',
    spark:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/>',
    chart:'<path d="M4 4v16h16M8 15l4-5 4 2 4-7"/>',
    search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    people:'<circle cx="9" cy="8" r="3"/><path d="M3 20v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6m3 9v-3a6 6 0 0 0-2-4"/>',
    board:'<rect x="3" y="3" width="18" height="14" rx="2"/><path d="m8 21 4-4 4 4M7 12l4-4 3 3 3-4"/>',
    file:'<path d="M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8m-8 4h6"/>',
    arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>'
  };
  const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.spark}</svg>`;
  const config = {
    fan: {
      title:"Your matchday, with more insight.", subtitle:"Follow the action. Find your player. Ask why it matters.", home:"match", label:"Fan workspace", chat:"Ask the match", placeholder:"Why did that moment matter?", chatLead:"A little context can change how you see the game.",
      journey:[{label:"Follow the action",icon:"play",screen:"match"},{label:"Understand a moment",icon:"spark",question:"What is the story of this match?"},{label:"Follow a player",icon:"people",screen:"players"}]
    },
    analyst: {
      title:"Follow the question. Find the proof.", subtitle:"Search the match, inspect the cases, and compare the history.", home:"stories", label:"Analyst workspace", chat:"Ask your analyst", placeholder:"Find every fullback vs winger encounter…", chatLead:"Ask a question. Keep the supporting sample in view.",
      journey:[{label:"Choose a question",icon:"search",screen:"stories"},{label:"Inspect the replay",icon:"play",screen:"match"},{label:"Export your brief",icon:"file",export:true}]
    },
    coach: {
      title:"A clearer view from the touchline.", subtitle:"Review the signal. Check the context. Decide what to discuss.", home:"coach", label:"Coach workspace", chat:"Ask your assistant", placeholder:"What should I review about our spacing?", chatLead:"Evidence first. Review options you can discuss with your team.",
      journey:[{label:"Scan the priorities",icon:"board",screen:"coach"},{label:"Check a player",icon:"people",screen:"players"},{label:"Prepare a review",icon:"file",question:"What should I review about defensive spacing?"}]
    }
  };
  function mountChat(role) {
    const chat = document.querySelector(".live-chat-panel");
    const target = document.querySelector(role === "analyst" ? "#analyst-assistant-slot" : role === "coach" ? "#coach-assistant-slot" : "#match-assistant-slot");
    if (chat && chat.parentElement !== target) target.append(chat);
  }
  function configure(role) {
    const c = config[role];
    document.querySelector("#workspace-title").textContent = c.title;
    document.querySelector("#workspace-subtitle").textContent = c.subtitle;
    document.querySelector("#workspace-role-label").textContent = `Change perspective · ${role[0].toUpperCase() + role.slice(1)}`;
    document.querySelector("#match-chat-title").textContent = c.chat;
    document.querySelector(".chat-intro").textContent = c.chatLead;
    document.querySelector("#chat-input").placeholder = c.placeholder;
    const guide = document.querySelector("#role-guide");
    guide.hidden = false;
    guide.innerHTML = `<span class="journey-label">${role === "fan" ? "Your matchday" : role === "analyst" ? "Your workflow" : "Your review"}</span><div class="journey-steps">${c.journey.map((step,i)=>`<button type="button" ${step.screen ? `data-go-screen="${step.screen}"` : step.export ? 'id="download-report"' : `data-workspace-question="${escape(step.question)}"`}><span class="journey-number">0${i+1}</span>${icon(step.icon)}<span>${step.label}</span>${icon("arrow")}</button>`).join("")}</div>`;
    document.querySelector("#stories-title").textContent = role === "analyst" ? "Your analysis desk" : role === "coach" ? "Patterns behind the priorities" : "The stories behind the score";
    document.querySelector("#stories-kicker").textContent = role === "analyst" ? "Question → evidence → brief" : "Match intelligence";
    mountChat(role);
    const fanHighlights = document.querySelector("#fan-matchday");
    if (fanHighlights.parentElement.id === "screen-match" && fanHighlights.previousElementSibling === null) document.querySelector("#screen-match").append(fanHighlights);
  }
  function renderFan(game, player) {
    const root = document.querySelector("#fan-matchday");
    const focal = game.insights[0];
    const profile = game.player_profiles.find(p=>p.player_id === player.id);
    const rating = game.match_intelligence.rating_timelines[player.id]?.at(-1)?.rating ?? 6;
    root.innerHTML = `<article class="matchday-story"><span class="feature-icon">${icon("spark")}</span><div><p class="eyebrow">Worth watching</p><h3>${escape(focal.title)}</h3><p>${escape(focal.fan_summary)}</p></div><button class="text-action" type="button" data-workspace-question="${focal.kind==='history' ? 'Why is this set piece interesting?' : focal.kind==='pattern' ? 'How many attacks ended in crosses?' : 'What is the story of this match?'}">Tell me why ${icon("arrow")}</button></article><button class="fan-player-card" type="button" data-go-screen="players"><span class="shirt-number">${escape(player.number)}</span><span><small>Your player · ${escape(player.team)}</small><strong>${escape(player.name)}</strong><span>${profile?.stats.touches ?? 0} touches · #${profile?.ranks.touches ?? "—"} in match</span></span><span class="fan-rating"><strong>${Number(rating).toFixed(1)}</strong><small>demo rating</small></span></button>`;
  }
  function renderAnalyst(game, feeds) {
    const root = document.querySelector("#analyst-tools");
    const track = feeds.tactical?.games?.[game.match.game_id];
    const recent = game.attacks.slice(-8);
    const questions = [
      ["matchups","people","Fullback vs winger","Open each tagged encounter","Show every fullback vs winger case on the pitch"],
      ["attacks","chart","Attacking patterns",recent.length ? `${recent.filter(a=>a.end_type === "cross").length}/${recent.length} recent attacks end in a cross` : "No completed tagged attacks yet","How many of the last attacks ended in crosses?"],
      ["history","file","Set-piece history","Compare both teams' last 7 games","How does this set piece compare with their recent matches?"],
      ["form","search","Player form","Today, last five, season sample","Compare this player's xG with his last five matches"]
    ];
    root.innerHTML = `<div class="analysis-metrics"><div><strong>${game.events.length}</strong><span>Tagged events</span></div><div><strong>${(track?.frames || []).filter(f=>f.minute*60<=game.analysis_context.seconds).length}</strong><span>Player snapshots · 1/min</span></div><div><strong>7</strong><span>Historical games / team</span></div><div><strong>${game.match.minute}′</strong><span>Latest available minute</span></div></div><div class="analysis-tool-heading"><h3>Start an investigation</h3><span>Choose a question, or write your own →</span></div><div class="investigation-cards">${questions.map(([id,ic,title,detail,q])=>`<button type="button" data-investigation="${id}" data-workspace-question="${escape(q)}"><span class="tool-icon">${icon(ic)}</span><strong>${title}</strong><small>${escape(detail)}</small>${icon("arrow")}</button>`).join("")}</div>`;
  }
  function coachPriorities(game, team) {
    const rows = game.match_intelligence.coach_board.players.filter(p=>p.team === team);
    const cues = [];
    for (const row of rows) {
      const r = row.paired_spacing;
      if (r?.status === "widened") cues.push({id:`gap-${row.player_id}`,player:row,priority:100 + r.distance_after_m - r.distance_before_m,label:"Spacing",title:`Check ${row.name.split(" ")[0]}'s paired gap`,value:`${r.distance_before_m} → ${r.distance_after_m}m`,context:"Distance to the paired opponent · 55′ vs 70′",action:"Compare the two frames and check the team shape before changing an assignment.",question:`What should I review about ${row.name}'s defensive spacing?`});
      if (row.passes >= 4 && row.pass_accuracy < 75) cues.push({id:`pass-${row.player_id}`,player:row,priority:60 + (75-row.pass_accuracy),label:"Ball retention",title:`Review ${row.name.split(" ")[0]}'s passing`,value:`${row.accurate_passes}/${row.passes}`,context:`Completed passes · ${row.pass_accuracy}% in the tagged sample`,action:"Review the pass locations and nearby support. The sample alone cannot show why a pass failed.",question:`How is ${row.name} playing?`});
      if (row.high_speed_sample_change_pct !== null && row.high_speed_sample_change_pct < -25 && row.high_speed_efforts_20_30 >= 2) cues.push({id:`load-${row.player_id}`,player:row,priority:50,label:"Running output",title:`Monitor ${row.name.split(" ")[0]}'s effort count`,value:`${row.high_speed_efforts_20_30} → ${row.high_speed_efforts_60_70}`,context:"High-speed samples · 20–30′ vs 60–70′",action:"Check opportunity, role, and how the player feels. Lower running output is not a fatigue diagnosis.",question:`Show ${row.name}'s running output in this match`});
    }
    return cues.sort((a,b)=>b.priority-a.priority).slice(0,3);
  }
  function renderCoach(game, player) {
    const team = player.team;
    const priorities = coachPriorities(game, team);
    document.querySelector("#coach-team-switch").innerHTML = [game.match.home,game.match.away].map(name=>`<button type="button" data-coach-team="${escape(name)}" aria-pressed="${name===team}">${escape(name)}</button>`).join("");
    document.querySelector("#coach-priority-board").innerHTML = `<div class="priority-label"><span class="eyebrow">${escape(team)} · review queue</span><span>${priorities.length} ${priorities.length === 1 ? "cue" : "cues"} to inspect</span></div>${priorities.length ? priorities.map((cue,i)=>`<article class="priority-card"><span class="priority-index">0${i+1}</span><div class="priority-copy"><span class="cue-label">${escape(cue.label)} · review cue</span><h3>${escape(cue.title)}</h3><strong class="cue-value">${escape(cue.value)}</strong><p>${escape(cue.context)}</p><details><summary>Review next</summary><p>${escape(cue.action)}</p></details></div><button type="button" class="priority-focus" data-review-player="${escape(cue.player.player_id)}" data-workspace-question="${escape(cue.question)}" aria-label="Inspect ${escape(cue.player.name)}">Inspect ${icon("arrow")}</button></article>`).join("") : '<div class="empty-state">No cue meets this demo’s review thresholds. You can still inspect any player below.</div>'}`;
    const primary = priorities[0];
    document.querySelector("#coach-review-plan").innerHTML = `<div class="panel-head"><div><p class="eyebrow">A simple plan for this review</p><h2>Observe. Confirm. Discuss.</h2></div>${icon("board")}</div><ol class="review-plan"><li><span>01</span><div><strong>Start with the clearest cue</strong><p>${primary ? escape(primary.title) + ". Open its evidence before drawing a conclusion." : "Select a player to review their tagged actions."}</p></div></li><li><span>02</span><div><strong>Check the wider picture</strong><p>Use the player view and replay to compare role, position, and nearby support.</p></div></li><li><span>03</span><div><strong>Prepare the conversation</strong><p>Use your assistant for a short evidence summary. Confirm it with the team.</p></div></li></ol><button class="text-action" type="button" data-workspace-question="${escape(primary?.question || `How is ${player.name} playing?`)}">Prepare this review ${icon("arrow")}</button>`;
  }
  function result(answer, question, game) {
    const root = document.querySelector("#analysis-result");
    root.hidden = answer.topic === "fullback_winger";
    const heading = ({fullback_winger:"Encounter search",tactics:"Attack sequence",team_history:"Historical comparison",history:"Set-piece context",player_history:"Player form comparison",player:"Player evidence",load:"Running output",spacing:"Paired spacing",matchup:"Direct matchup"})[answer.topic] || "Match evidence";
    let graphic = "";
    if (answer.topic === "tactics") {
      graphic = `<div class="attack-sequence" aria-label="Last eight tagged attacks">${game.attacks.slice(-8).map(a=>`<button type="button" data-jump-minute="${a.minute}" title="${escape(a.team)} · ${a.minute} minutes · ${escape(a.end_type)}"><time>${a.minute}′</time><span>${a.end_type === "cross" ? "↗" : "→"}</span><strong>${escape(a.end_type)}</strong><small>${a.switched_left_to_right ? "Switched side" : "Same side"}</small></button>`).join("")}</div>`;
    }
    root.innerHTML = `<div class="panel-head"><div><p class="eyebrow">Current investigation</p><h2>${heading}</h2></div><span class="sample-tag">${answer.facts?.length || 0} EVIDENCE ITEMS</span></div><p class="investigation-question">${escape(question)}</p><p class="result-summary">${escape(answer.summary || answer.text)}</p>${graphic}<div class="result-facts">${(answer.facts || []).slice(0,6).map(f=>`<div><span>${escape(f.label)}</span><strong>${escape(f.value)}</strong><details><summary>Source</summary><small>${escape(f.source)}</small></details></div>`).join("")}</div><p class="coverage-note"><strong>Coverage</strong> ${escape(answer.caveat)}</p>`;
  }
  return {config,configure,renderFan,renderAnalyst,renderCoach,result,icon};
})();
