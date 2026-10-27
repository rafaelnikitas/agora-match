const $ = (selector) => document.querySelector(selector);
const insightRoot = $("#insights");
const gameSelect = $("#game-select");
const viewSelect = $("#view-select");
const playerSelect = $("#player-select");
const viewNames = {fan: "Fan view", analyst: "Analyst view", coach: "Coach view"};
const screenNames = ["match", "players", "stories", "coach"];
const roleScreens = {
  fan: {match:"Matchday",players:"My player",stories:"Match stories",coach:null},
  analyst: {match:"Live replay",players:"Player data",stories:"Analysis desk",coach:"Squad signals"},
  coach: {match:"Live pitch",players:"Player review",stories:"Team patterns",coach:"Review board"}
};
const statLabels = {
  goals: "Goals", assists: "Assists", xg: "xG", xa: "xA", passes: "Passes",
  accurate_passes: "Accurate passes", touches: "Touches", big_chances_created: "Big chances created",
  long_passes: "Long passes", accurate_long_passes: "Accurate long passes", ground_duels: "Ground duels",
  ground_duels_won: "Ground duels won", aerial_duels: "Aerial duels", aerial_duels_won: "Aerial duels won",
  penalty_area_touches: "Penalty-area touches", successful_dribbles: "Successful tagged dribbles", pressures: "Pressures",
  recoveries: "Recoveries", high_speed_samples: "High-speed samples",
  interceptions: "Interceptions", clearances: "Clearances", saves: "Saves", crosses: "Crosses", max_speed_kmh: "Max sampled speed"
};
const eventNames = {key_pass: "Key pass", duel: "Ground duel", shot: "Shot", tackle: "Tackle", direct_free_kick: "Direct free kick", turnover: "Possession lost", cross: "Cross", pass: "Pass", corner: "Corner", dribble: "Dribble"};
let catalog;
let activeGame;
let sourceGame;
let analysisIndex;
let analysisKey = "";
let analysisPending = false;
let analysisTask = Promise.resolve();
const analysisCache = new Map();
let answerLanguage = localStorage.getItem("agora-language") || "en";
function analysisBase() { return `${activeGame.match.game_id}:${activeGame.analysis_context?.seconds ?? activeGame.available_through_seconds}`; }
function sessionKeyFor(role=viewSelect.value) { return `${analysisBase()}:${role}:${answerLanguage}`; }
function evidenceLinks(fact) {
  const ids = fact.event_ids?.length ? fact.event_ids : sourceGame.events.filter(e=>String(fact.source||"").includes(e.id) || fact.event_id===e.id || (e.attack_id && String(fact.source||"").includes(e.attack_id))).map(e=>e.id);
  return ids.slice(0,3).map(id=>`<button type="button" class="evidence-jump" data-evidence-event="${esc(id)}">Open ${esc(id)} ↗</button>`).join("");
}
function setAnalysisStatus(text) {
  const label=document.querySelector("#analysis-clock-status"); if(label) label.textContent=text;
  document.body.dataset.analysisPending=String(analysisPending);
  const submit=document.querySelector("#chat-submit"); if(submit) submit.disabled=analysisPending || chatBusy.has(sessionKeyFor());
}
async function synchronizeAnalysis() {
  if(!analysisIndex || !sourceGame) return;
  const gid=sourceGame.match.game_id, second=ballSecond;
  const boundaries=analysisIndex.games[gid];
  const boundary=[...boundaries].reverse().find(t=>t<=second) ?? 0;
  const key=`${gid}-${boundary}`;
  if(analysisKey===key) return;
  analysisKey=key; $("#commentary-output").hidden=true; $("#commentary-output").textContent=""; if("speechSynthesis" in window) speechSynthesis.cancel(); analysisPending=true; setAnalysisStatus("Updating the evidence to this match moment…");
  if(currentOverlayPayload) { currentOverlayPayload=null; $("#broadcast-overlay").hidden=true; }
  let patch=analysisCache.get(key);
  try {
    if(!patch) { const r=await fetch(`/data/analysis/${key}.json`); if(!r.ok) throw new Error("context unavailable"); patch=await r.json(); analysisCache.set(key,patch); while(analysisCache.size>32) analysisCache.delete(analysisCache.keys().next().value); }
    if(analysisKey!==key || sourceGame.match.game_id!==gid) return;
    activeGame=AgoraEvidence.projectView(sourceGame,patch); analysisPending=false;
    renderAnalysisPanels(); syncUrl();
    setAnalysisStatus(`Evidence through ${patch.analysis_context.clock} · future events excluded · tagged sample`);
  } catch (_error) {
    if(analysisKey!==key) return;
    analysisPending=true; setAnalysisStatus("This moment could not load. Choose another moment or reload.");
  }
}
function queueAnalysis() { analysisTask=synchronizeAnalysis(); }

let foundryConfigured = false;
let foundryMode = "demo";
let foundryConnection = "unconfigured";
let serverAvailable = false;
let requestedPlayer = "";
let activeScreen = "match";
let replayIndex = null;
let replayTimer = null;
let replayGameId = "";
let hasSelectedEvent = false;
let ballSecond = null;
let requestedSecond = null;
let ballGameId = "";
let ballTimer = null;
let playbackSpeed = 2;
let replayKeyMomentsOnly = false;
const keyMomentTypes = new Set(["shot", "key_pass", "dribble", "cross", "corner", "direct_free_kick", "interception"]);
let chatMessages = [];
const chatSessions = new Map();
const chatBusy = new Set();
const investigations = new Map();
let toastTimer;
let currentOverlayPayload = null;
let chatGameId = "";
let dataFeeds = {};
let visualFlavor = localStorage.getItem("agora-match-flavor") || "modern";
const storedTextScale = Number(localStorage.getItem("agora-match-text-scale") || "1");
let textScale = [1, 1.1, 1.2].includes(storedTextScale) ? storedTextScale : 1;
let simpleLanguage = localStorage.getItem("agora-match-simple") === null ? true : localStorage.getItem("agora-match-simple") === "true";
let commentaryStyle = localStorage.getItem("agora-match-commentary") || "Tactical explainer";

function applyFlavor() {
  if (!["classical", "modern"].includes(visualFlavor)) visualFlavor = "modern";
  document.body.dataset.flavor = visualFlavor;
  document.body.dataset.simpleText = String(simpleLanguage);
  document.documentElement.style.setProperty("--ui-zoom", String(Math.max(1, Math.min(1.2, textScale))));
  document.documentElement.style.zoom = String(Math.max(1, Math.min(1.2, textScale)));
  document.querySelectorAll("#game-select,#player-select,#replay-range").forEach((control) => { control.tabIndex = 0; });
  $("meta[name='theme-color']").content = visualFlavor === "classical" ? "#0F141C" : "#FFFFFF";
  document.querySelectorAll("[data-flavor-choice]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.flavorChoice === visualFlavor)));
}

function setFlavor(flavor) {
  visualFlavor = flavor;
  localStorage.setItem("agora-match-flavor", flavor);
  applyFlavor();
  if (catalog && $("#onboarding").hidden) render();
}

function setSimpleLanguage(enabled) {
  simpleLanguage = enabled;
  localStorage.setItem("agora-match-simple", String(enabled));
  applyFlavor();
  if (catalog) render();
}

function setTextScale(value) {
  textScale = Math.max(1, Math.min(1.2, Number(value)));
  localStorage.setItem("agora-match-text-scale", String(textScale));
  applyFlavor();
  if (catalog) { renderPersonalControls(); syncUrl(); }
}

applyFlavor();

function enterRole(role, keepScreen = false) {
  if (!["fan", "analyst", "coach"].includes(role)) role = "fan";
  viewSelect.value = role;
  localStorage.setItem("agora-match-role", role);
  $("#onboarding").hidden = true;
  $(".page").hidden = false;
  $("#screen-nav").hidden = false;
  $("#change-role").hidden = false;
  $("#theme-switcher").hidden = false;
  if (!keepScreen) activeScreen = AgoraExperience.config[role].home;
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  render();
  window.scrollTo({top:0,behavior:"instant"});
}

function configureWorkspace() {
  const role = viewSelect.value;
  document.body.dataset.audience = role;
  document.querySelectorAll("[data-screen-target]").forEach((button) => {
    const label = roleScreens[role][button.dataset.screenTarget];
    button.hidden = !label;
    if (label) button.textContent = label;
  });
  AgoraExperience.configure(role);
  renderPersonalControls();
  renderMatchChoices();
  $("#view-label").textContent = viewNames[role];
  $("#audience-help").textContent = AgoraExperience.config[role].subtitle;
}

function renderPersonalControls() {
  const root = $("#personal-controls");
  root.hidden = false;
  const scaleLabel = textScale >= 1.19 ? "Largest" : textScale >= 1.09 ? "Large" : "Standard";
  const voiceSupported = "SpeechRecognition" in window || "webkitSpeechRecognition" in window;
  root.innerHTML = `<details class="accessibility-details"><summary>Display &amp; voice settings</summary><div class="accessibility-options"><div class="text-scale-control" role="group" aria-label="Text size"><strong>Text size: ${scaleLabel}</strong><button type="button" data-text-scale="1" aria-pressed="${textScale < 1.05}">A</button><button type="button" data-text-scale="1.1" aria-pressed="${textScale >= 1.05 && textScale < 1.15}">A+</button><button type="button" data-text-scale="1.2" aria-pressed="${textScale >= 1.15}">A++</button></div><button class="simple-toggle" id="simple-toggle" type="button" aria-pressed="${simpleLanguage}"><span>${simpleLanguage ? "✓" : "○"}</span> Plain-language explanations ${simpleLanguage ? "On" : "Off"}</button>${voiceSupported ? '<button class="simple-toggle" id="voice-command" type="button">🎙 Voice command</button>' : ""}<span id="voice-status" class="accessibility-hint" role="status">${voiceSupported ? "Try: ‘Agora, read recap’ or ‘Agora, coach view’." : "Keyboard friendly · text is announced as it updates."}</span></div></details>`;
  root.querySelector(".accessibility-options").insertAdjacentHTML("beforeend", `<div class="commentary-settings"><strong>AI explanation language</strong><div role="group" aria-label="AI explanation language"><button type="button" data-answer-language="en" aria-pressed="${answerLanguage==='en'}">English</button><button type="button" data-answer-language="el" aria-pressed="${answerLanguage==='el'}">Ελληνικά</button></div><small>Questions and sources stay in English. Greek explanations require a live AI connection.</small></div>`);
  if (viewSelect.value === "fan") root.querySelector(".accessibility-options").insertAdjacentHTML("beforeend", `<div class="commentary-settings"><strong>Commentary style</strong><div class="commentary-style-group" role="group" aria-label="Commentary style">${["Tactical explainer","Casual companion","Youth-friendly"].map(style=>`<button type="button" data-commentary-style="${esc(style)}" aria-pressed="${commentaryStyle===style}">${esc(style)}</button>`).join("")}</div></div>`);
}

function startVoiceCommand() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) return;
  const recognition = new Recognition();
  recognition.lang = navigator.language || "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  $("#voice-status").textContent = "Listening for one command…";
  recognition.onresult = (event) => {
    const command = event.results[0][0].transcript.toLowerCase().replace(/^\s*agora[,:]?\s*/, "").trim();
    if (/read|speak|recap/.test(command)) {
      const text = $("#recap-headline").textContent + ". " + $("#recap-summary").textContent;
      if ("speechSynthesis" in window) speechSynthesis.speak(new SpeechSynthesisUtterance(text));
      $("#voice-status").textContent = "Reading the latest recap.";
    } else {
      const role = command.includes("coach") ? "coach" : command.includes("analyst") ? "analyst" : command.includes("fan") ? "fan" : null;
      if (role) { enterRole(role); $("#voice-status").textContent = `Switched to ${role} view.`; }
      else if (command.includes("player")) { setScreen("players"); $("#voice-status").textContent = "Opened player view."; }
      else if (command.includes("match")) { setScreen("match"); $("#voice-status").textContent = "Opened match view."; }
      else if (command.includes("ask") || command.includes("insight")) { setScreen("stories"); $("#voice-status").textContent = "Opened match questions."; }
      else $("#voice-status").textContent = `Command not recognized: ${command}`;
    }
  };
  recognition.onerror = () => { const status = $("#voice-status"); if (status) status.textContent = "Voice input unavailable. Use the buttons or keyboard instead."; };
  recognition.start();
}

function renderMatchChoices() {
  const root = $("#match-buttons");
  if (!catalog) return;
  root.innerHTML = catalog.games.map((game) => `<button type="button" data-match-choice="${esc(game.match.game_id)}" aria-pressed="${game.match.game_id === gameSelect.value}">${esc(game.match.label)}</button>`).join("");
}

function renderPlayerChoices() {
  const root = $("#player-choice-buttons");
  if (!activeGame) return;
  root.innerHTML = activeGame.players.map((player) => `<button type="button" data-player-choice="${esc(player.id)}" aria-pressed="${player.id === playerSelect.value}"><strong>${esc(player.name)}</strong><small>${esc(player.team)} · ${esc(player.role)} · #${player.number}</small></button>`).join("");
}

function renderHistory() {
  const payload = dataFeeds.teamHistory?.games?.[activeGame.match.game_id];
  if (!payload) { $("#history-panel").innerHTML = ""; return; }
  const teams = Object.entries(payload.teams);
  $("#history-panel").innerHTML = `<div class="panel-head"><div><p class="eyebrow">Seven-match team baseline</p><h2>Recent context for both sides</h2></div><span class="sample-tag">SYNTHETIC HISTORY</span></div><div class="history-teams">${teams.map(([name, team]) => `<article class="history-team"><div class="history-team-head"><strong>${esc(name)}</strong><span>${team.summary.wins}W · ${team.summary.draws}D · ${team.summary.losses}L</span></div><p>${team.summary.goals_for} scored · ${team.summary.goals_against} conceded · ${fmt(team.summary.mean_xg)} avg xG</p><div class="history-signal"><b>${team.summary.corner_scoring_matches}/7</b><span>matches with a corner goal</span></div><div class="history-signal"><b>${team.summary.corner_conceding_matches}/7</b><span>matches conceding from a corner</span></div></article>`).join("")}</div><p class="caveat-note">Illustrative history generated for this demo. Counts are match-level and do not imply the same pattern will repeat.</p>`;
}

function renderWorkload() {
  const feed = dataFeeds.wearables?.games?.[activeGame.match.game_id];
  const series = (feed?.players?.[playerSelect.value]?.samples || []).filter(s=>s.minute*60 <= activeGame.analysis_context.seconds);
  if (!series.length) { $("#workload-chart").innerHTML = '<p class="empty-state">No wearable samples for this player.</p>'; return; }
  const buckets = Array.from({length: 8}, (_, i) => {
    const start = i * 10, rows = series.filter((sample) => sample.minute >= start && sample.minute < start + 10);
    const effort = rows.filter((sample) => sample.effort_zone === "high" || sample.effort_zone === "sprint").length;
    return {label:`${start}–${start+10}′`, value:rows.length ? Math.round(effort / rows.length * 100) : null};
  });
  $("#workload-chart").innerHTML = `<div class="workload-title">${esc(currentPlayer().name)} · high-effort samples per 10 min</div><div class="workload-bars">${buckets.map((b) => `<div class="workload-bar-wrap"><div class="workload-bar" style="--bar:${Math.max(5,b.value||0)}%" title="${b.value}%"></div><small>${b.label}</small><b>${b.value === null ? "—" : b.value+"%"}</b></div>`).join("")}</div>`;
  $("#workload-note").textContent = "Share of synthetic samples in a high-effort zone. The final window is incomplete. This measures running output, not fatigue.";
}

function downloadBrief() {
  const payload = dataFeeds.teamHistory?.games?.[activeGame.match.game_id];
  const events = dataFeeds.liveEvents?.games?.[activeGame.match.game_id]?.events || [];
  if (!payload) return;
  const lines = [`# Evidence brief — ${activeGame.match.label}`, "", "Synthetic-only demonstration data.", "", `Tagged live events: ${events.length}`, "", "## Recent team context"];
  Object.entries(payload.teams).forEach(([team, item]) => lines.push(`- **${team}:** ${item.summary.wins}W ${item.summary.draws}D ${item.summary.losses}L; ${item.summary.goals_for} goals for, ${item.summary.goals_against} against; corner goals in ${item.summary.corner_scoring_matches}/7 matches.`));
  const investigation = investigations.get(analysisBase());
  if (investigation) {
    lines.push("", "## Current investigation", investigation.question, "", investigation.answer.text, "", "### Evidence");
    (investigation.answer.facts || []).forEach(f => lines.push(`- **${f.label}:** ${f.value} — ${f.source}`));
    lines.push("", "### Coverage", investigation.answer.caveat || "");
  }
  lines.push("", "## Data limits", "History, event tags, tracking, and wearable readings are fictional synthetic examples. Review denominators and event coverage before interpreting a pattern.");
  const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([lines.join("\n")], {type:"text/markdown"})); link.download = `${activeGame.match.game_id}-evidence-brief.md`; document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(link.href),1000);
  announce("Evidence brief downloaded.");
}

function announce(message) {
  const root = $("#workspace-status"); root.textContent = message; root.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { root.hidden = true; }, 3500);
}

function focusAssistant() {
  setScreen(AgoraExperience.config[viewSelect.value].home);
  requestAnimationFrame(() => { $(".live-chat-panel").scrollIntoView({behavior:"smooth",block:"nearest"}); $("#chat-input").focus({preventScroll:true}); });
}

function renderRolePanels() {
  const role = viewSelect.value;
  $("#fan-matchday").hidden = role !== "fan";
  $("#analyst-tools").hidden = role !== "analyst";
  if (role !== "analyst") { $("#analysis-result").hidden = true; $("#matchup-explorer").hidden = true; }
  AgoraExperience.renderFan(activeGame, currentPlayer());
  AgoraExperience.renderAnalyst(activeGame, dataFeeds);
  AgoraExperience.renderCoach(activeGame, currentPlayer());
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
}
function playerFor(id) { return activeGame.players.find((p) => p.id === id); }
function profileFor(id) { return activeGame.player_profiles.find((p) => p.player_id === id); }
function currentPlayer() { return playerFor(playerSelect.value) || playerFor("N8") || activeGame.players[0]; }
function fmt(value) { return Number.isInteger(value) ? String(value) : Number(value).toFixed(2).replace(/0+$/, "").replace(/\.$/, ""); }

function chatSuggestions() {
  const setPiece=[...activeGame.events].reverse().find(e=>["corner","direct_free_kick"].includes(e.type));
  const items = viewSelect.value === "fan"
    ? ["What is the story of this match?", setPiece ? "Why is this set piece interesting?" : "Show every fullback vs winger case on the pitch", `How is ${currentPlayer().name} playing?`]
    : viewSelect.value === "analyst"
      ? ["Compare the last 8 crosses with their historical average", setPiece ? `What is the recent ${setPiece.type === "direct_free_kick" ? "free kick" : "corner"} record?` : "How many attacks ended in crosses?", "Show every fullback vs winger case on the pitch"]
      : [`Show ${currentPlayer().name}'s running output in this match`, "Show me the latest player matchup", "What should I review about defensive spacing?"];
  const root = $("#live-suggestions");
  if (root) root.innerHTML = items.map((item) => `<button type="button" data-chat-question="${esc(item)}">${esc(item)}</button>`).join("");
}

function localChatAnswer(question,persona,simplify=false,conversation=[]) {
  return AgoraEvidence.answer(activeGame,question,persona,playerSelect.value,simplify,conversation);
}
function chatEvidence(question) { return localChatAnswer(question,viewSelect.value,true); }

function aiTraceMarkup(message) {
  if (!message.agent_trace?.length) return "";
  const labels = {match_analyst:"Match analyst",audience_narrator:"Your narrator",evidence_reviewer:"Evidence checker"};
  return `<details class="answer-sources ai-trace"><summary>How this answer was checked</summary>${message.agent_trace.map(row=>`<div><strong>${esc(labels[row.stage] || row.stage)}</strong><span>${esc(row.status === "completed" ? "Completed" : "Fallback")} · ${esc(row.duration_ms)} ms</span></div>`).join("")}${!message.model_used ? '<p class="answer-limit">AI could not complete the checks. You are seeing the evidence template.</p>' : ""}</details>`;
}

function renderChat() {
  const sessionKey = sessionKeyFor();
  if (chatGameId !== sessionKey) { if (chatGameId) chatSessions.set(chatGameId, chatMessages); chatGameId = sessionKey; chatMessages = chatSessions.get(sessionKey) || []; chatSessions.set(sessionKey, chatMessages); }
  chatSuggestions();
  $("#chat-mode").textContent = foundryConnection === "verified" ? "FOUNDRY" : foundryConnection === "degraded" ? "AI FALLBACK" : foundryConfigured ? "AI CONFIGURED" : "DEMO";
  const connectionLabel = foundryConnection === "verified" ? "CONNECTED" : foundryConnection === "degraded" ? "FALLBACK" : "CONFIGURED";
  $("#foundry-pipeline-status").textContent = foundryConfigured ? `${foundryMode === "three-role" ? "3 ROLES" : "1 ROLE"} · ${connectionLabel}` : "DEMO · AI NOT CONNECTED";
  $("#chat-submit").disabled = analysisPending || chatBusy.has(sessionKey);
  $("#chat-submit").setAttribute("aria-label", chatBusy.has(sessionKey) ? "Preparing answer" : "Send message");
  $("#chat-footnote").textContent = `Answers through ${activeGame.analysis_context.clock} · synthetic match & history · ${foundryConnection === "verified" ? "Foundry reachable" : foundryConnection === "degraded" ? "AI unavailable · demo fallback" : foundryConfigured ? "AI connection not yet verified" : "demo answers"}`;
  const empty = {fan:["Curious about that moment?","Ask why it mattered, or follow a player beyond the score."],analyst:["What would you like to investigate?","Choose a search above, or ask your own question. Sources and visual cases stay alongside the answer."],coach:["A second pair of eyes.","Ask about a player's output, a matchup, or the context behind a review cue."]}[viewSelect.value];
  $("#chat-messages").innerHTML = chatMessages.length ? chatMessages.map((message) => message.role === "user"
    ? `<article class="chat-message user"><p>${esc(message.text)}</p></article>`
    : `<article class="chat-message assistant"><div class="answer-label">${AgoraExperience.icon("spark")}${({fan:"The takeaway",analyst:"Finding",coach:"Review cue"})[message.persona]}</div><p>${esc(message.text)}</p>${message.facts?.length ? `<details class="answer-sources" ${message.persona === "analyst" ? "open" : ""}><summary>${message.facts.length} supporting facts · sources & limits</summary><div class="chat-citations">${message.facts.map((fact)=>`<span><strong>${esc(fact.label)}</strong>${esc(fact.value)}<small>${esc(fact.source)}</small>${evidenceLinks(fact)}</span>`).join("")}</div>${message.caveat ? `<p class="answer-limit">${esc(message.caveat)}</p>` : ""}</details>` : ""}${message.visualization?.type === "fullback_winger_cases" ? `<button type="button" class="open-matchup-cases" data-open-matchups="${esc(chatMessages.indexOf(message))}">Open visual cases →</button>` : ""}${aiTraceMarkup(message)}<span class="chat-meta">${esc(message.analysis_context?.clock || "")} · ${esc(viewNames[message.persona])} · ${!message.model_used && answerLanguage === "el" ? "English fallback · " : ""}${message.model_used ? (message.cache_hit ? "cached AI answer" : "Foundry answer") : "synthetic evidence template"}</span></article>`).join("") : `<div class="chat-empty"><span class="empty-icon">${AgoraExperience.icon(viewSelect.value === "coach" ? "board" : viewSelect.value === "analyst" ? "search" : "spark")}</span><strong>${empty[0]}</strong><p>${empty[1]}</p></div>`;
  if (chatBusy.has(sessionKey)) $("#chat-messages").insertAdjacentHTML("beforeend", '<div class="chat-pending" role="status">Checking the match evidence</div>');
  if (viewSelect.value === "analyst") {
    const investigation = investigations.get(analysisBase());
    if (investigation) { AgoraExperience.result(investigation.answer, investigation.question, activeGame); renderMatchupExplorer(investigation.answer.visualization); }
    else {
      const question = "Show every fullback vs winger case on the pitch";
      const answer = localChatAnswer(question,"analyst",true);
      AgoraExperience.result(answer,question,activeGame); renderMatchupExplorer(answer.visualization);
    }
    const topic = investigation?.answer.topic || "fullback_winger";
    const selectedTool = ({fullback_winger:"matchups",tactics:"attacks",history:"history",team_history:"history",player_history:"form",player:"form"})[topic];
    document.querySelectorAll("[data-investigation]").forEach(button=>{ const selected = button.dataset.investigation === selectedTool; button.classList.toggle("selected",selected); button.setAttribute("aria-pressed",String(selected)); });
  }
  const root = $("#chat-messages"); root.scrollTop = root.scrollHeight;
}

function setScreen(name, writeUrl = true) {
  if (!screenNames.includes(name)) name = "match";
  if (!roleScreens[viewSelect.value]?.[name]) name = "match";
  activeScreen = name;
  document.querySelectorAll(".screen").forEach((screen) => {
    const on = screen.id === "screen-" + name;
    screen.hidden = !on;
    screen.classList.toggle("active", on);
  });
  document.querySelectorAll("[data-screen-target]").forEach((button) => { const active = button.dataset.screenTarget === name; button.classList.toggle("active", active); if (active) button.setAttribute("aria-current","page"); else button.removeAttribute("aria-current"); });
  if (writeUrl) syncUrl();
}

function renderInsight(item, view) {
  const extra = view === "fan"
    ? "<p>" + esc(item.fan_summary) + "</p>"
    : view === "analyst"
      ? "<p>" + esc(item.explorer_summary) + "</p><div class=\"facts\">" + item.evidence.slice(0, 3).map((fact) => "<div class=\"fact\"><strong>" + esc(fact.value) + "</strong><span>" + esc(fact.metric) + "</span></div>").join("") + "</div><p class=\"evidence\">Evidence: " + item.evidence.map((fact) => esc(fact.source)).join(" · ") + "</p><p class=\"caveat\">" + esc(item.caveat) + "</p>"
      : "<p>" + esc(item.studio_summary) + "</p><p class=\"evidence\">" + esc(item.minute) + "′ · " + esc(item.agent) + " · source " + item.evidence.map((fact) => esc(fact.event_id || fact.metric)).slice(0, 2).join(" / ") + "</p>";
  const aiAction = foundryConfigured
    ? "<button class=\"narrate\" type=\"button\" data-insight-id=\"" + esc(item.id) + "\">Narrate with Microsoft Foundry</button><p class=\"narration\" id=\"narration-" + esc(item.id) + "\" aria-live=\"polite\"></p>"
    : "";
  return "<article class=\"insight\"><div class=\"insight-top\"><span class=\"agent\">" + esc(item.kind || "Match story") + "</span><span class=\"rank\">#" + item.rank + " · " + (item.relevance >= 85 ? "WORTH A LOOK" : "MATCH CONTEXT") + "</span></div><h3>" + esc(item.title) + "</h3>" + extra + (view === "analyst" ? "<button class=\"overlay-action\" type=\"button\" data-overlay-id=\"" + esc(item.id) + "\">Preview broadcast card</button>" : "") + aiAction + "</article>";
}

function renderEvents() {
  const playerNames = Object.fromEntries(activeGame.players.map((p) => [p.id, p.name]));
  const ordered = [...sourceGame.events].sort((a, b) => a.minute - b.minute || a.id.localeCompare(b.id));
  if (replayGameId !== activeGame.match.game_id || replayIndex === null) { replayGameId = activeGame.match.game_id; replayIndex = ordered.length - 1; }
  replayIndex = Math.max(0, Math.min(replayIndex, ordered.length - 1));
  const events = ordered.filter(e=>Math.round(e.minute*60)<=ballSecond).slice(-36).reverse();
  const activeEvent = ordered.filter(e=>Math.round(e.minute*60)<=ballSecond).at(-1) || {minute:0,team:"Match",type:"kick_off",id:"",player_id:null};
  replayIndex = Math.max(0,ordered.findIndex(e=>e.id===activeEvent.id));
  const range = $("#replay-range"); range.max = Math.max(0, ordered.length - 1); range.value = replayIndex;
  $("#replay-position").textContent = `${fmt(activeEvent.minute)}′ · ${replayIndex + 1}/${ordered.length}`;
  $("#timeline-caption").textContent = `Through ${fmt(activeEvent.minute)}′ · newest first`;
  $("#timeline-count").textContent = `${ordered.filter(e=>Math.round(e.minute*60)<=ballSecond).length} events through replay time`;
  const eventLabel = ({whistle:"Play stopped",restart:"Play resumes"})[activeEvent.type] || eventNames[activeEvent.type] || activeEvent.type.replaceAll("_", " ");
  const eventPlayer = playerNames[activeEvent.player_id] || "Team action";
  $("#live-event-title").textContent = `${activeEvent.team} · ${eventLabel}`;
  $("#live-event-detail").textContent = `${eventPlayer} · ${activeEvent.team}${activeEvent.outcome && activeEvent.outcome !== "complete" ? ` · ${activeEvent.outcome.replaceAll("_", " ")}` : ""}`;
  $("#live-event-time").textContent = `${fmt(activeEvent.minute)}′`;
  $("#stream-events").textContent = replayTimer ? "❚❚ Pause" : "▶ Play key moments";
  const goals = ordered.filter(e=>Math.round(e.minute*60)<=ballSecond).filter((event) => event.type === "shot" && event.outcome === "goal");
  const homeScore = goals.filter((event) => event.team === activeGame.match.home).length;
  const awayScore = goals.filter((event) => event.team === activeGame.match.away).length;
  $("#score").textContent = `${homeScore} — ${awayScore}`;
  $("#replay-toggle").textContent = replayTimer ? "❚❚ Pause" : (replayIndex >= ordered.length - 1 ? "▶ Replay" : "▶ Play");
  $("#play-by-play").innerHTML = events.map((event) => {
    const active = event.id === activeEvent.id; const type = ({whistle:"Play stopped",restart:"Play resumes"})[event.type] || eventNames[event.type] || event.type.replaceAll("_", " ");
    const player = playerNames[event.player_id] || "Team action";
    const status = event.outcome && event.outcome !== "complete" ? " · " + event.outcome.replaceAll("_", " ") : "";
    const team = event.team === "Officials" ? "Match" : event.team;
    const label = hasSelectedEvent ? "SELECTED" : "LATEST";
    return `<button type="button" class="event-row ${active ? "current" : ""}" data-event-id="${esc(event.id)}"><time>${fmt(event.minute)}′</time><span class="event-mark"></span><span class="event-copy"><strong>${esc(type)}${active ? ` <span class="live-tag">${label}</span>` : ""}</strong><small>${esc(player)} · ${esc(team)}${esc(status)}</small></span></button>`;
  }).join("");
}

function renderPitch() {
  queueAnalysis();
  const tactical = dataFeeds.tactical?.games?.[sourceGame.match.game_id];
  const track = tactical?.ball_track || [];
  if (!track.length) return;
  const maxSecond = track.length - 1;
  ballSecond = Math.max(0, Math.min(maxSecond, Math.round(ballSecond ?? maxSecond)));
  const point = track[ballSecond];
  const minute = ballSecond / 60;
  const frame = [...(tactical.frames || [])].reverse().find((item) => item.minute <= minute) || tactical.frames?.[0];
  const positions = frame?.players || [];
  const trail = track.slice(Math.max(0, ballSecond - 20), ballSecond + 1);
  const polyline = trail.map((item) => `${item.x},${item.y}`).join(" ");
  const dots = positions.map((p) => `<span class="dot ${p.team === activeGame.match.home ? "home" : "away"}" style="left:${(p.x / 105 * 100).toFixed(2)}%;top:${(p.y / 68 * 100).toFixed(2)}%" title="${esc(p.name || p.player_id)} · #${esc(p.number)}">${esc(p.number)}</span>`).join("");
  const pitch = $("#live-pitch");
  pitch.innerHTML = `<span class="pitch-mid"></span><span class="pitch-circle"></span><span class="pitch-box"></span><svg class="ball-trail" viewBox="0 0 105 68" preserveAspectRatio="none" aria-hidden="true"><polyline points="${polyline}"/></svg>${dots}<span class="ball-marker" style="left:${(point.x / 105 * 100).toFixed(2)}%;top:${(point.y / 68 * 100).toFixed(2)}%" aria-hidden="true"></span>`;
  pitch.setAttribute("aria-label", `Synthetic ball at ${fmt(minute)} minutes, coordinates ${fmt(point.x)} by ${fmt(point.y)} metres; 22 players shown at the ${frame?.minute || 0} minute snapshot.`);
  const sec = Math.floor(ballSecond % 60); const min = Math.floor(ballSecond / 60);
  $("#tactical-minute").textContent = `${String(min).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
  $("#ball-clock").textContent = `${String(min).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
  $(".minute").textContent = `${String(min).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
  const goals = sourceGame.events.filter((item) => item.type === "shot" && item.outcome === "goal" && Math.round(item.minute * 60) <= ballSecond);
  $("#score").textContent = `${goals.filter((item) => item.team === activeGame.match.home).length} — ${goals.filter((item) => item.team === activeGame.match.away).length}`;
  const slider = $("#ball-range"); slider.max = maxSecond; slider.value = ballSecond;
  $("#ball-play").textContent = ballTimer ? "❚❚ Pause" : ballSecond >= maxSecond ? "▶ Replay" : "▶ Play";
  $("#ball-play").setAttribute("aria-label", ballTimer ? "Pause ball replay" : ballSecond >= maxSecond ? "Replay the match" : "Play ball replay");
  $("#ball-play").setAttribute("aria-pressed", String(Boolean(ballTimer)));
  $("#pitch-caption").textContent = `Ball at ${fmt(point.x)}m × ${fmt(point.y)}m · trailing 20 seconds · player frame ${String(frame?.minute || 0).padStart(2,"0")}:00`;
  const event = sourceGame.events.filter(e=>Math.round(e.minute*60)<=ballSecond).reduce((closest, item) => Math.abs(item.minute * 60 - ballSecond) < Math.abs((closest?.minute ?? 1e9) * 60 - ballSecond) ? item : closest, null);
  const delta = event ? Math.abs(event.minute * 60 - ballSecond) : Infinity;
  $("#ball-event").textContent = event && delta <= 2 ? `${fmt(event.minute)}′ · ${eventNames[event.type] || event.type.replaceAll("_", " ")} · ${playerFor(event.player_id)?.name || event.team}` : `Ball coordinates · ${fmt(point.x)}m, ${fmt(point.y)}m`;
  $("#shape-label").textContent = "The match, from above";
  const previousEvent = [...sourceGame.events].sort((a,b)=>b.minute-a.minute).find(item=>Math.round(item.minute * 60) <= ballSecond);
  if (previousEvent) {
    $("#live-event-title").textContent = `${previousEvent.team} · ${eventNames[previousEvent.type] || previousEvent.type.replaceAll("_"," ")}`;
    $("#live-event-detail").textContent = `${playerFor(previousEvent.player_id)?.name || "Team action"}${previousEvent.outcome ? " · " + previousEvent.outcome.replaceAll("_"," ") : ""}`;
    $("#live-event-time").textContent = `${fmt(previousEvent.minute)}′`;
  } else { $("#live-event-title").textContent = "Ready for kick-off"; $("#live-event-detail").textContent = "Press play or jump to a key moment."; $("#live-event-time").textContent = "00:00"; }
  renderAttackPulse();

  const selected = [...sourceGame.events].sort((a,b)=>a.minute-b.minute||a.id.localeCompare(b.id))[replayIndex || 0];
  const decision = (tactical.event_options || []).filter(e=>Math.round(e.minute*60)<=ballSecond).reduce((closest, item) => !closest || Math.abs(item.minute - (selected?.minute || 0)) < Math.abs(closest.minute - (selected?.minute || 0)) ? item : closest, null);
  const decisionPanel = $("#decision-panel");
  if (!hasSelectedEvent || !decision || Math.abs(decision.minute - (selected?.minute || 0)) > 1.2 || Math.abs(decision.minute-minute) > 1.2) decisionPanel.hidden = true;
  else {
    decisionPanel.hidden = false; const actor = playerFor(decision.player_id)?.name || "Player";
    $("#decision-heading").textContent = `${actor} · ${eventNames[decision.event_type] || decision.event_type.replaceAll("_", " ")} · ${fmt(decision.minute)}′`;
    $("#decision-options").innerHTML = decision.passing_options.length ? decision.passing_options.map((option, index) => `<div class="decision-option"><span class="option-rank">${index + 1}</span><strong>${esc(playerFor(option.player_id)?.name || option.player_id)}</strong><span>${esc(option.space_label)} lane</span><span>${fmt(option.distance_m)}m away</span><small>Nearest opponent ${fmt(option.nearest_opponent_m)}m</small></div>`).join("") : '<div class="empty-state">No nearby teammate option in this sampled frame.</div>';
    const decisionFrame = (tactical.frames || []).filter(f=>f.minute<=decision.minute && f.minute*60<=ballSecond).at(-1);
    $("#decision-note").textContent = `Event ${decision.event_id} · nearest pressure ${fmt(decision.nearest_pressure_m)}m. Options use the closest synthetic player frame (${decisionFrame?.minute || 0}′); they are not verified video or exact event-time choices.`;
  }
}

function updatePlaybackSpeed() {
  $("#ball-speed").textContent = `${playbackSpeed}×`;
  $("#ball-speed").setAttribute("aria-label", `Playback speed ${playbackSpeed} times`);
  $("#replay-speed").textContent = `${playbackSpeed}×`;
  $("#replay-speed").setAttribute("aria-label", `Event speed ${playbackSpeed} times`);
}

function cyclePlaybackSpeed() {
  playbackSpeed = playbackSpeed === 1 ? 2 : playbackSpeed === 2 ? 4 : 1;
  updatePlaybackSpeed();
  if (ballTimer) { clearInterval(ballTimer); ballTimer = null; startBallReplay(); }
  if (replayTimer) { clearInterval(replayTimer); replayTimer = null; startEventReplay(); }
}

function startBallReplay() {
  const max = dataFeeds.tactical.games[activeGame.match.game_id].ball_track.length - 1;
  if (ballSecond >= max) ballSecond = 0;
  $("#ball-play").textContent = "❚❚ Pause";
  $("#ball-play").setAttribute("aria-label","Pause ball replay");
  ballTimer = setInterval(() => {
    if (ballSecond >= max) { clearInterval(ballTimer); ballTimer = null; renderPitch(); return; }
    ballSecond += 1; renderPitch();
  }, Math.max(35, Math.round(1000 / playbackSpeed)));
}

function startEventReplay(keyMomentsOnly = replayKeyMomentsOnly) {
  replayKeyMomentsOnly = keyMomentsOnly;
  const ordered = [...sourceGame.events].sort((a, b) => a.minute - b.minute || a.id.localeCompare(b.id));
  const queue = keyMomentsOnly ? ordered.map((event, index) => ({event, index})).filter(({event}) => keyMomentTypes.has(event.type)).map(({index}) => index) : ordered.map((_, index) => index);
  const nextQueuePosition = queue.findIndex((index) => index > replayIndex);
  let queuePosition = nextQueuePosition < 0 ? -1 : nextQueuePosition - 1;
  if (nextQueuePosition < 0) replayIndex = 0;
  $("#replay-toggle").textContent = "❚❚ Pause";
  replayTimer = setInterval(() => {
    queuePosition += 1;
    if (queuePosition >= queue.length) { clearInterval(replayTimer); replayTimer = null; renderEvents(); return; }
    replayIndex = queue[queuePosition];
    const e = ordered[replayIndex];
    if (e) ballSecond = Math.round(e.minute * 60);
    renderEvents(); renderPitch();
  }, Math.max(140, Math.round(900 / playbackSpeed)));
  renderEvents();
}

function renderAttackPulse() {
  const root = $("#attack-pulse"); if (!root || !activeGame) return;
  const duration = Math.ceil(activeGame.match.minute); const counts = Array(duration + 1).fill(0);
  const actionTypes = new Set(["shot","cross","key_pass","dribble","duel","tackle","interception","corner"]);
  activeGame.events.filter((event) => actionTypes.has(event.type)).forEach((event) => { const minute = Math.min(duration, Math.floor(event.minute)); counts[minute] += 1; });
  const max = Math.max(1, ...counts); const current = Math.floor((ballSecond || 0) / 60);
  const priorMinute = Number(root.dataset.minute ?? -1); const oldScroll = root.scrollLeft;
  root.innerHTML = counts.map((count, minute) => `<button type="button" class="pulse-bar ${minute === current ? "selected" : ""} ${count ? "has-actions" : ""}" style="--pulse:${Math.max(5, count / max * 100)}%" data-pulse-minute="${minute}" title="${minute}′ · ${count} tagged actions" aria-label="${minute} minutes, ${count} tagged key actions"><i></i><small>${minute % 10 === 0 ? minute : ""}</small></button>`).join("");
  root.dataset.minute = String(current);
  if (priorMinute !== current) { const selected = root.querySelector(".pulse-bar.selected"); if (selected) root.scrollLeft = Math.max(0, selected.offsetLeft - root.offsetLeft - root.clientWidth / 2); }
  else root.scrollLeft = oldScroll;
}

function renderMatchupExplorer(visualization) {
  if (visualization?.type !== "fullback_winger_cases") { $("#matchup-explorer").hidden = true; return; }
  const cases = visualization?.cases || []; const panel = $("#matchup-explorer");
  panel.hidden = false; $("#matchup-case-count").textContent = `${cases.length} TAGGED CASE${cases.length===1 ? "" : "S"} · ${new Set(cases.map((c)=>c.player_id+":"+c.opponent_id)).size} PAIRING${new Set(cases.map(c=>c.player_id+":"+c.opponent_id)).size===1 ? "" : "S"}`;
  $("#matchup-case-list").innerHTML = cases.map((item,index) => `<button type="button" class="matchup-case ${index === 0 ? "selected" : ""}" data-case-index="${index}"><strong>${fmt(item.minute)}′ · ${esc(item.player_name)} vs ${esc(item.opponent_name)}</strong><span>${esc(item.action.replaceAll("_"," "))} · ${esc(item.result)}</span><small>${esc(item.event_id)}</small></button>`).join("");
  if(!cases.length) { $("#matchup-pitch").innerHTML=""; $("#matchup-case-detail").textContent="No tagged winger-versus-fullback case is available at this moment."; return; }
  showMatchupCase(cases,0);
}

function showMatchupCase(cases,index) {
  const item = cases[index]; if (!item) return;
  document.querySelectorAll(".matchup-case").forEach((node) => node.classList.toggle("selected", Number(node.dataset.caseIndex) === index));
  const tactical = dataFeeds.tactical?.games?.[activeGame.match.game_id];
  const frame = (tactical?.frames || []).filter(row=>row.minute<=item.minute && row.minute*60<=activeGame.analysis_context.seconds).at(-1);
  const a = frame?.players.find((p)=>p.player_id===item.player_id), b = frame?.players.find((p)=>p.player_id===item.opponent_id);
  const pitch = $("#matchup-pitch");
  const connector = a && b ? `<svg viewBox="0 0 105 68" preserveAspectRatio="none"><line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"/></svg>` : "";
  pitch.innerHTML = `<span class="pitch-mid"></span><span class="pitch-circle"></span><span class="pitch-box"></span>${connector}${a ? `<span class="dot home matchup-attacker" style="left:${a.x/105*100}%;top:${a.y/68*100}%" title="Winger · ${esc(item.player_name)}">W</span>` : ""}${b ? `<span class="dot away matchup-defender" style="left:${b.x/105*100}%;top:${b.y/68*100}%" title="Fullback · ${esc(item.opponent_name)}">FB</span>` : ""}`;
  $("#matchup-case-detail").textContent = `${fmt(item.minute)}′ · ${item.player_name} (winger) vs ${item.opponent_name} (fullback) · ${item.result.replaceAll("_"," ")} · prior shape at ${frame?.minute || 0}′ · ${item.event_id}`;
}

function renderPlayer() {
  const player = currentPlayer();
  const profile = profileFor(player.id);
  if (!profile) return;
  const historical = dataFeeds.playerHistory?.games?.[activeGame.match.game_id]?.players?.[player.id];
  const stats = profile.stats;
  const role = viewSelect.value;
  const topStats = role === "fan" ? ["goals", "assists", "xg", "touches"] : role === "coach" ? ["accurate_passes", "ground_duels_won", "aerial_duels_won", "high_speed_samples", "touches"] : ["xg", "xa", "accurate_passes", "touches", "passes"];
  $("#player-screen-title").textContent = role === "fan" ? "A closer look at your player" : role === "coach" ? "Player review" : "Player evidence & form";
  const playerNote = role === "fan" ? `${player.name} has ${stats.goals} goals and ${stats.touches} touches. Follow the moments behind the numbers.` : role === "analyst" ? `Inspect current output, position-adjusted ranks, and ${historical?.matches?.length || 7} prior synthetic appearances. Current figures cover sparse tagged actions; historical totals are per appearance, so raw totals are not directly comparable.` : `Review ${player.name}'s output alongside role peers and tagged opponent encounters. Confirm the context before discussing an adjustment.`;
  $("#player-context").innerHTML = `<p>${esc(playerNote)}</p><button type="button" class="text-action" data-workspace-question="How is ${esc(player.name)} playing?">Ask about ${esc(player.name.split(" ")[0])} ${AgoraExperience.icon("arrow")}</button>`;
  $("#player-name").textContent = player.name;
  $("#player-role").textContent = "· #" + player.number + " · " + player.role;
  $("#player-team-label").textContent = player.team + " · match performance";
  $("#position-label").textContent = player.role + " KPIs";
  $("#player-rank-label").textContent = "Touches rank · " + profile.ranks.touches + " of " + activeGame.players.length;
  $("#player-stats").innerHTML = topStats.map((key) => "<div class=\"stat-chip\"><strong>" + fmt(stats[key]) + (key === "touches" ? " · #" + profile.ranks[key] : "") + "</strong><span>" + esc(statLabels[key]) + (key !== "touches" ? " · rank #" + profile.ranks[key] : "") + "</span></div>").join("");
  const events = activeGame.events.filter((e) => e.player_id === player.id).sort((a, b) => b.minute - a.minute).slice(0, 6);
  $("#player-moment-caption").textContent = events.length + " tagged actions · " + (historical?.matches?.length || 0) + " historical samples";
  $("#player-moments").innerHTML = events.length ? events.map((e) => "<span>" + fmt(e.minute) + "′ · " + esc(eventNames[e.type] || e.type.replaceAll("_", " ")) + "</span>").join("") : "<span>No tagged moments for this player yet</span>";
  const kpis = role === "fan" ? profile.kpis.slice(0,4) : profile.kpis;
  $("#kpi-heading").textContent = player.role === "ST" || player.role === "W" ? "Attacking impact" : player.role === "GK" ? "Goalkeeper impact" : player.role === "CB" || player.role === "FB" ? "Defensive & progression" : "Midfield impact";
  $("#role-kpis").innerHTML = kpis.map((key) => "<div class=\"role-kpi\"><span>" + esc(statLabels[key] || key) + "</span><strong>" + fmt(stats[key]) + "</strong><small>match rank #" + profile.ranks[key] + " of " + activeGame.players.length + "</small></div>").join("");
  const compareKeys = ["goals", "assists", "xg", "xa", "touches", "accurate_passes"];
  const last5 = profile.last5_average;
  const season = profile.season_average;
  $("#player-comparison").innerHTML = "<div class=\"comparison-row comparison-head\"><span>Metric</span><span>Tagged now</span><span>Last 5 / appearance</span><span>7-game / appearance</span></div>" + compareKeys.map((key) => "<div class=\"comparison-row\"><span>" + esc(statLabels[key]) + "</span><strong>" + fmt(stats[key]) + "</strong><span>" + fmt(last5[key]) + "</span><span>" + fmt(season[key]) + "</span></div>").join("");
  const rateRows=Object.entries(profile.comparable_rates || {}).map(([key,r])=>`<div class="comparison-row"><span>${key==="xg_per_shot" ? "xG / tagged shot" : "Pass completion rate"}</span><strong>${r.current===null ? "—" : fmt(r.current)}</strong><span>${r.last5===null ? "—" : fmt(r.last5)}</span><span>${r.current_denominator} / ${r.history_denominator} samples</span></div>`).join("");
  $("#player-comparison").insertAdjacentHTML("beforeend",`<div class="comparison-row comparison-head"><span>Matched rate</span><span>Now</span><span>Last five</span><span>Sample sizes</span></div><p class="caveat-note">Matched metric definitions below; denominators show current / historical sample sizes. Sparse samples remain descriptive.</p>${rateRows}`);
  $("#player-heatmap").innerHTML = renderHeatmap(profile.heat_points, player.team === activeGame.match.home);
  renderRating(player);
  renderMatchups(player);
}

function renderRating(player) {
  const timeline = activeGame.match_intelligence.rating_timelines[player.id] || [];
  const maxMinute = Math.max(1, activeGame.match.minute);
  const points = timeline.map((item) => ({x: 38 + item.minute / maxMinute * 470, y: 176 - (item.rating - 4.5) / 5.3 * 132}));
  const line = points.map((point, index) => (index ? "L" : "M") + point.x.toFixed(1) + " " + point.y.toFixed(1)).join(" ");
  const dots = points.slice(1).map((point, index) => `<circle cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="3.7" fill="${timeline[index + 1].rating >= 6.5 ? "#54d995" : "#ffc876"}"><title>${fmt(timeline[index + 1].minute)}′ · ${fmt(timeline[index + 1].rating)} · ${esc(timeline[index + 1].label)}</title></circle>`).join("");
  const latest = timeline.at(-1) || {rating: 6, minute: 0};
  $("#rating-value").textContent = fmt(latest.rating);
  $("#rating-through").textContent = "through " + fmt(latest.minute) + "′";
  $("#rating-trace").innerHTML = `<svg viewBox="0 0 530 210" role="img" aria-label="Synthetic performance rating by minute from a neutral 6.0 baseline"><line x1="38" y1="126" x2="508" y2="126" class="rating-average"/><line x1="38" y1="44" x2="38" y2="176" class="chart-axis"/><line x1="38" y1="176" x2="508" y2="176" class="chart-axis"/><text x="5" y="48">9</text><text x="5" y="130">6</text><text x="5" y="179">4.5</text><text x="35" y="198">0′</text><text x="245" y="198">${Math.round(maxMinute / 2)}′</text><text x="480" y="198">${maxMinute}′</text><path d="${line}" class="rating-line"/>${dots}<circle cx="${points.at(-1)?.x || 38}" cy="${points.at(-1)?.y || 138}" r="5" class="rating-current"/></svg>`;
  const delta = timeline.length > 1 ? timeline.at(-1).rating - timeline.at(-2).rating : 0;
  $("#rating-note").textContent = timeline.length < 2
    ? "No tagged actions for this player yet; the neutral baseline is shown."
    : viewSelect.value === "fan"
      ? `${timeline.length - 1} tagged actions inform this sample rating.`
      : `${timeline.length - 1} tagged actions · latest change ${delta >= 0 ? "+" : ""}${fmt(delta)} from ${timeline.at(-1).label}.`;
}

function renderMatchups(player) {
  const matches = activeGame.match_intelligence.matchups.filter((item) => item.player_id === player.id || item.opponent_id === player.id);
  const root = $("#player-matchups");
  if (!matches.length) {
    root.innerHTML = '<div class="empty-state">No tagged one-v-one observations for this player in this sample. No matchup conclusion can be made.</div>';
    return;
  }
  root.innerHTML = matches.map((item) => {
    const reversed = item.opponent_id === player.id;
    const other = reversed ? item.player_name : item.opponent_name;
    const adverse = reversed ? item.won : item.stopped;
    const events = item.events.map((event) => {
      let result = event.result;
      if (reversed) result = ({won: "lost", lost: "won", stopped: "progressed", "route blocked": "route open"})[result] || result;
      return viewSelect.value === "fan" ? "" : `<div class="duel-event"><time>${fmt(event.minute)}′</time><span>${esc(event.action)}</span><strong class="${result === "won" ? "positive" : result === "lost" || result === "stopped" || result === "route blocked" ? "negative" : "neutral"}">${esc(result)}</strong></div>`;
    }).join("");
    return `<article class="matchup-card"><div class="matchup-title"><div><strong>vs ${esc(other)}</strong><small>${item.attempts} tagged encounters in this synthetic sample</small></div><b class="${adverse >= 2 ? "negative" : "positive"}">${adverse}/${item.attempts} ${reversed ? "won by player" : "stopped"}</b></div>${events}</article>`;
  }).join("");
}

function renderCoach() {
  const player = currentPlayer();
  const row = activeGame.match_intelligence.coach_board.players.find((item) => item.player_id === player.id);
  const pct = row.max_speed_vs_role_pct;
  const fatigue = row.high_speed_sample_change_pct;
  const responsibility = row.paired_spacing;
  const assignmentPlayer = responsibility ? playerFor(responsibility.opponent_id) : null;
  const signals = [
    ["Passing", row.passes ? `${row.accurate_passes}/${row.passes} · ${row.pass_accuracy}%` : "No pass sample", row.passes ? (row.pass_accuracy < 75 ? "negative" : "positive") : "neutral", "Completed passes divided by attempts in the tagged sample."],
    ["Max sampled speed", `${fmt(row.max_speed_kmh)} km/h`, pct < -5 ? "negative" : "positive", `${Math.abs(pct)}% ${pct < 0 ? "below" : "above"} this match’s ${player.role} peer average (${fmt(row.role_peer_max_speed_kmh)} km/h).`],
    ["Running output", fatigue === null ? "No paired effort windows" : `${row.high_speed_efforts_20_30} → ${row.high_speed_efforts_60_70} high-speed samples`, fatigue === null ? "neutral" : fatigue < -25 ? "negative" : "positive", "20–30′ compared with 60–70′ in sampled tracking. Counts depend on role and opportunity; they do not diagnose fatigue."],
    ["Paired-opponent spacing", responsibility ? (responsibility.status === "widened" ? "Gap widened" : "Gap held") + (assignmentPlayer ? " · " + assignmentPlayer.name : "") : "No paired sample", responsibility?.status === "widened" ? "negative" : responsibility?.status === "stable" ? "positive" : "neutral", responsibility ? `${fmt(responsibility.distance_before_m)}m → ${fmt(responsibility.distance_after_m)}m between sampled positions at 55′ and 70′. This is a review cue, not proof of an assigned marking duty.` : "No paired position sample is provided for this player."],
    ["Decision time", "Not measured", "neutral", "The feed has no ball-receipt and release timestamps, so decision speed cannot be assessed."],
  ];
  $("#coach-player-heading").textContent = player.name + " · " + player.role;
  $("#coach-team-label").textContent = player.name + " selected · click a name to switch";
  $("#coach-indicators").innerHTML = signals.map(([title, value, tone, note]) => `<article class="coach-signal"><div><span>${esc(title)}</span><strong class="${tone}">${esc(value)}</strong></div><p>${esc(note)}</p></article>`).join("");
  const matchup = activeGame.match_intelligence.matchups.filter((item) => item.player_id === player.id || item.opponent_id === player.id).sort((a,b) => b.stopped - a.stopped)[0];
  $("#coach-matchup").innerHTML = matchup
    ? `<strong>${esc(matchup.player_id === player.id ? matchup.player_name : matchup.opponent_name)} vs ${esc(matchup.player_id === player.id ? matchup.opponent_name : matchup.player_name)}</strong><p>${matchup.stopped} of ${matchup.attempts} attacking actions were stopped or had the forward route blocked in the tagged sample.</p><small>Small synthetic sample; use as a review cue.</small>`
    : '<p>No tagged matchup sample for this player.</p>';
  const teamRows = activeGame.match_intelligence.coach_board.players.filter((item) => item.team === player.team).map((item) => {
    const flag = item.paired_spacing?.status === "widened" ? "Gap widened" : item.passes >= 4 && item.pass_accuracy < 75 ? "Review passing" : item.high_speed_sample_change_pct < -25 && item.high_speed_efforts_20_30 >= 2 ? "Lower effort count" : item.max_speed_vs_role_pct < -5 ? "Below role peak speed" : "No flagged sample";
    return `<tr><td><button type="button" class="player-link" data-focus-player="${esc(item.player_id)}">${esc(item.name)}</button></td><td>${esc(item.role)}</td><td>${item.passes ? item.pass_accuracy + "%" : "—"}</td><td>${fmt(item.max_speed_kmh)}</td><td>${esc(flag)}</td></tr>`;
  }).join("");
  $("#coach-team-table").innerHTML = `<div class="table-scroll"><table><thead><tr><th>Player</th><th>Role</th><th>Pass %</th><th>Sampled km/h</th><th>Review cue</th></tr></thead><tbody>${teamRows}</tbody></table></div>`;
}

function renderHeatmap(points, home) {
  const dots = points.map((p) => `<circle cx="${p.x}" cy="${p.y}" r="6" fill="url(#hot)" opacity=".33"/>`).join("");
  const travel = points.filter((_, i) => i % 6 === 0).map((p, i) => `<circle cx="${p.x}" cy="${p.y}" r="1.1" fill="${home ? "#f3fff5" : "#ffd0cd"}" opacity="${.45 + (i % 3) * .15}"/>`).join("");
  return `<svg viewBox="0 0 105 68" preserveAspectRatio="none" aria-hidden="true"><defs><radialGradient id="hot"><stop offset="0" stop-color="#ffd475" stop-opacity=".95"/><stop offset=".55" stop-color="#ff9a50" stop-opacity=".45"/><stop offset="1" stop-color="#f56b55" stop-opacity="0"/></radialGradient></defs><rect x="0" y="0" width="105" height="68" fill="#205b3b"/><rect x="1" y="1" width="103" height="66" fill="none" stroke="#ffffffaa" stroke-width=".5"/><path d="M52.5 1v66M52.5 18a16 16 0 1 0 0 32a16 16 0 1 0 0-32M1 16h16v36H1M104 16H88v36h16" fill="none" stroke="#ffffff88" stroke-width=".5"/>${dots}${travel}</svg>`;
}

function syncUrl() {
  if (!catalog || !activeGame) return;
  const params = new URLSearchParams({match: gameSelect.value, view: viewSelect.value, player: playerSelect.value, screen: activeScreen, flavor: visualFlavor, size: String(textScale)});
  params.set("simple", simpleLanguage ? "1" : "0");
  if(ballSecond !== null) params.set("at",String(ballSecond));
  history.replaceState(null, "", "?" + params);
}

function render() {
  configureWorkspace();
  const selectedSource = catalog.games.find((game) => game.match.game_id === gameSelect.value) || catalog.games[0];
  if(!sourceGame || sourceGame.match.game_id !== selectedSource.match.game_id) { sourceGame=selectedSource; activeGame=sourceGame; analysisKey=""; }
  const match = activeGame.match;
  if (ballGameId !== match.game_id) { ballGameId = match.game_id; ballSecond = requestedSecond !== null && requestedSecond <= activeGame.available_through_seconds ? requestedSecond : Math.floor(match.minute * 60 + (match.second || 0)); requestedSecond=null; hasSelectedEvent = false; if (ballTimer) clearInterval(ballTimer); ballTimer = null; if (replayTimer) clearInterval(replayTimer); replayTimer = null; replayGameId = ""; replayIndex = null; currentOverlayPayload = null; $("#broadcast-overlay").hidden = true; }
  $("#home-name").textContent = match.home;
  $("#away-name").textContent = match.away;
  $("#ball-home-name").textContent = match.home; $("#ball-away-name").textContent = match.away;
  const oldPlayer = playerSelect.value;
  playerSelect.innerHTML = activeGame.players.map((p) => "<option value=\"" + esc(p.id) + "\">" + esc(p.name) + " · " + esc(p.role) + "</option>").join("");
  const desired = requestedPlayer || oldPlayer;
  playerSelect.value = activeGame.players.some((p) => p.id === desired) ? desired : "N8";
  renderPlayerChoices();
  requestedPlayer = "";
  renderEvents(); renderPitch(); renderAttackPulse(); renderPlayer(); renderCoach(); renderHistory(); renderWorkload();
  renderRolePanels();
  renderAnalysisPanels();
  setScreen(activeScreen, false);
  syncUrl();
}

function renderAnalysisPanels() {
  renderEvents(); renderAttackPulse(); renderPlayer(); renderCoach(); renderHistory(); renderWorkload(); renderRolePanels();
  const insights = activeGame.insights
    .filter((item) => item.id !== "load-output-drop" || item.evidence.some((fact) => fact.player_id === playerSelect.value))
    .map((item, index) => ({...item, rank: index + 1}));
  const top=insights.slice(0,2), rest=insights.slice(2);
  insightRoot.innerHTML = top.map(item=>renderInsight(item,viewSelect.value)).join("") + (rest.length ? `<details class="more-insights"><summary>${rest.length} more observations</summary>${rest.map(item=>renderInsight(item,viewSelect.value)).join("")}</details>` : "");
  const focal=insights[0];
  $("#moment-context").innerHTML = focal ? `<p class="eyebrow">Why this moment matters</p><h3>${esc(focal.title)}</h3><p>${esc(focal.fan_summary)}</p><div class="moment-facts">${focal.evidence.slice(0,2).map(f=>`<span><strong>${esc(f.value)}</strong><small>${esc(f.metric)}</small></span>`).join("")}</div><small>Triggered ${Math.floor(focal.minute)}:${String(Math.round(focal.minute%1*60)).padStart(2,"0")} · evidence through ${esc(activeGame.analysis_context.clock)}</small>${focal.evidence.flatMap(f=>[f.event_id,...(f.event_ids||[])]).filter(Boolean).slice(0,2).map(id=>`<button type="button" class="evidence-jump" data-evidence-event="${esc(id)}">Inspect moment ↗</button>`).join("")}` : "";
  $("#live-insights").innerHTML = insights.slice(0, 2).map((item) => renderInsight(item, viewSelect.value)).join("");
  $("#recap-headline").textContent = activeGame.recap.headline;
  $("#recap-summary").textContent = activeGame.recap.summary;
  $("#recap-facts").innerHTML = activeGame.recap.evidence.map((fact) => "<span class=\"recap-fact\"><strong>" + esc(fact.value) + "</strong><small>" + esc(fact.metric) + "</small></span>").join("");
  $("#recap-label").textContent = activeGame.recap.label;
  renderChat();
  $("#ai-status").textContent = foundryConfigured
    ? foundryConnection === "verified" ? "Foundry connection verified" : foundryConnection === "degraded" ? "Foundry unavailable · evidence fallback active" : "Foundry configured · connection awaiting verification"
    : serverAvailable
      ? "Evidence narrative · synthetic data, Foundry model not configured"
      : "Evidence narrative · local synthetic-data demo; Foundry model not connected";
  $("#commentary-model").textContent = foundryConnection === "verified" ? "Foundry available" : foundryConnection === "degraded" ? "Evidence fallback" : foundryConfigured ? "AI configured" : "Demo commentary";
  $("#game-heading").textContent = activeGame.match.label;

}

async function narrate(insightId, button) {
  const result = document.getElementById("narration-" + insightId);
  button.disabled = true; button.textContent = "Preparing narration…";
  try {
    const narratorView = ({analyst: "explorer", coach: "studio"})[viewSelect.value] || viewSelect.value;
    const response = await fetch("/api/narrate", {signal:AbortSignal.timeout(35000),method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({insight_id: insightId, analysis_time_seconds:activeGame.analysis_context.seconds,language:answerLanguage,game_id: gameSelect.value, view: narratorView, simplify: simpleLanguage})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Narration unavailable");
    result.innerHTML = esc(data.text) + " <span class=\"narration-source\">" + (data.model_used ? "Microsoft Foundry" : "Evidence-based fallback") + "</span>";
    button.textContent = "Refresh narration";
  } catch (error) { result.textContent = error.message; button.textContent = "Try narration again"; }
  finally { button.disabled = false; }
}

document.addEventListener("click", (event) => {
  const language=event.target.closest("[data-answer-language]");
  if(language) { answerLanguage=language.dataset.answerLanguage; localStorage.setItem("agora-language",answerLanguage); renderPersonalControls(); renderChat(); return; }
  const link=event.target.closest("[data-evidence-event]");
  if(link) {
    const row=[...sourceGame.events,...sourceGame.attacks].find(e=>e.id===link.dataset.evidenceEvent);
    if(!row) return;
    if(ballTimer) clearInterval(ballTimer); ballTimer=null;
    if(replayTimer) clearInterval(replayTimer); replayTimer=null;
    ballSecond=row.available_second ?? Math.round(row.minute*60); hasSelectedEvent=true; renderPitch(); renderEvents(); setScreen("match");
    $("#live-pitch").scrollIntoView({behavior:"smooth",block:"center"});
  }
});

document.addEventListener("click", (event) => {
  const overlayButton = event.target.closest("button[data-overlay-id]");
  if (overlayButton) {
    const item = activeGame.insights.find((insight) => insight.id === overlayButton.dataset.overlayId);
    if (!item) return;
    const audience = viewSelect.value;
    const summary = audience === "fan" || (simpleLanguage) ? item.fan_summary : audience === "analyst" ? item.explorer_summary : item.studio_summary;
    currentOverlayPayload = {
      schema_version: "agora.broadcast.overlay.v1",
      data_mode: "synthetic",
      match: {game_id:activeGame.match.game_id,home:activeGame.match.home,away:activeGame.match.away},
      timing: {period:item.minute >= 45 ? 2 : 1,match_minute:Math.floor(item.minute),period_minute:item.minute >= 45 ? Math.floor(item.minute-45) : Math.floor(item.minute),second:Math.round((item.minute%1)*60),offset_seconds:Math.round(item.minute*60)},
      audience,
      analysis_context:activeGame.analysis_context,
      expires_at_match_seconds:activeGame.analysis_context.seconds+15,
      insight: {id:item.id,rank:item.rank,headline:item.title,summary,evidence:item.evidence.map((fact)=>({source:fact.source,metric:fact.metric,value:fact.value,event_id:fact.event_id || null,event_ids:fact.event_ids || []})),caveat:item.caveat},
    };
    $("#overlay-title").textContent = item.title;
    $("#overlay-summary").textContent = summary;
    $("#overlay-meta").textContent = `${activeGame.match.home} vs ${activeGame.match.away} · ${fmt(item.minute)}′ · ${audience} · ${item.evidence.length} evidence records`;
    setScreen("match");
    $("#broadcast-overlay").hidden = false;
    $("#broadcast-overlay").scrollIntoView({behavior:"smooth",block:"nearest"});
    return;
  }
  const insightButton = event.target.closest("button[data-insight-id]");
  if (insightButton) { narrate(insightButton.dataset.insightId, insightButton); return; }
  const suggestion = event.target.closest("button[data-chat-question]");
  if (suggestion) { focusAssistant(); $("#chat-input").value = suggestion.dataset.chatQuestion; $("#chat-form").requestSubmit(); }
});

$("#stream-events").addEventListener("click", () => {
  const explorer = $("#event-explorer");
  explorer.open = true;
  hasSelectedEvent = true;
  if (replayTimer) { $("#replay-toggle").click(); return; }
  if (ballTimer) { clearInterval(ballTimer); ballTimer = null; $("#ball-play").textContent = "▶ Play"; }
  replayIndex = 0; ballSecond = 0;
  renderEvents(); renderPitch(); startEventReplay(true);
});

$("#download-overlay").addEventListener("click", () => {
  if (!currentOverlayPayload) return;
  const blob = new Blob([JSON.stringify(currentOverlayPayload,null,2)],{type:"application/json"});
  const url = URL.createObjectURL(blob); const link = document.createElement("a");
  link.href = url; link.download = `${activeGame.match.game_id}-${currentOverlayPayload.insight.id}-overlay.json`;
  document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
});

async function createCommentary(speak = false) {
  if(ballTimer) { clearInterval(ballTimer); ballTimer=null; }
  if(replayTimer) { clearInterval(replayTimer); replayTimer=null; }
  const button = $(speak ? "#speak-commentary" : "#generate-commentary");
  const output = $("#commentary-output");
  const label = $("#commentary-model");
  const commentaryContext = analysisBase();
  const match = activeGame.match;
  const minute = Math.floor((ballSecond || 0) / 60);
  const second = (ballSecond || 0) % 60;
  await analysisTask; if(analysisPending) return;
  const prompt = `Give short football commentary in a ${commentaryStyle} style for ${match.home} vs ${match.away}. Replay clock ${minute}:${String(second).padStart(2, "0")}; full available evidence through ${match.minute} minutes. Use only the selected synthetic match evidence and keep replay timing distinct from the data snapshot.`;
  button.disabled = true;
  label.textContent = "Preparing evidence-based commentary…";
  output.hidden = false;
  output.textContent = "Reading the synthetic match feed…";
  let answer;
  if (serverAvailable) {
    try {
      const response = await fetch("/api/ask", {signal:AbortSignal.timeout(35000),method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({analysis_time_seconds:activeGame.analysis_context.seconds,language:answerLanguage,game_id:gameSelect.value,persona:viewSelect.value,player_id:playerSelect.value,question:prompt,simplify:simpleLanguage})});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Narration endpoint unavailable");
      answer = payload.text;
      if (payload.foundry_status) foundryConnection = payload.foundry_status.connection;
      label.textContent = payload.model_used ? "Microsoft Foundry · synthetic match evidence" : "Evidence-based synthetic commentary · demo mode";
    } catch (_error) { answer = localChatAnswer(prompt, viewSelect.value, simpleLanguage).text; label.textContent = "Synthetic-data commentary · local demo mode"; }
  } else {
    answer = localChatAnswer(prompt, viewSelect.value, simpleLanguage).text;
    label.textContent = "Synthetic-data commentary · connect Foundry for model narration";
  }
  if(commentaryContext !== analysisBase()) { button.disabled=false; output.hidden=true; return; }
  output.textContent = answer;
  if (speak && "speechSynthesis" in window) {
    const utterance = new SpeechSynthesisUtterance(answer);
    utterance.lang=answerLanguage === "el" && label.textContent.includes("Foundry") ? "el-GR" : "en-GB";
    utterance.rate = commentaryStyle === "Youth-friendly" ? 0.88 : commentaryStyle === "Casual companion" ? 1.04 : 0.96;
    utterance.pitch = commentaryStyle === "Youth-friendly" ? 1.12 : 1;
    speechSynthesis.cancel(); speechSynthesis.speak(utterance);
    label.textContent += " · speaking";
  } else if (speak) label.textContent += " · speech playback is not supported by this browser";
  button.disabled = false;
}

$("#generate-commentary").addEventListener("click", () => createCommentary(false));
$("#speak-commentary").addEventListener("click", () => createCommentary(true));
$("#chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#chat-input"); const question = input.value.trim();
  if (!question || question.length > 1000) return;
  const persona = viewSelect.value;
  await analysisTask;
  if(analysisPending) return;
  const requestGameId = gameSelect.value;
  const requestKey = sessionKeyFor(persona);
  const requestBase = analysisBase();
  if (chatBusy.has(requestKey)) return;
  const requestMessages = chatMessages;
  chatBusy.add(requestKey);
  chatMessages.push({role:"user",text:question});
  const conversation = chatMessages.slice(0,-1).slice(-6).map((message)=>({role:message.role,content:String(message.text || "").slice(0,1000)}));
  input.value = ""; $("#chat-submit").disabled = true; $("#chat-submit").setAttribute("aria-label", "Preparing answer"); renderChat();
  const fallbackAnswer = localChatAnswer(question, persona, simpleLanguage, conversation);
  let result;
  if (serverAvailable) {
    try {
      const response = await fetch("/api/ask", {signal:AbortSignal.timeout(35000),method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({analysis_time_seconds:activeGame.analysis_context.seconds,language:answerLanguage,game_id:requestGameId,persona,player_id:playerSelect.value,question,conversation,simplify:simpleLanguage})});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Chat endpoint unavailable");
      result = payload;
      if (payload.foundry_status) foundryConnection = payload.foundry_status.connection;
    } catch (_error) { result = {...fallbackAnswer, reason:"local synthetic-data fallback"}; }
  } else result = fallbackAnswer;
  requestMessages.push({...result,role:"assistant",persona});
  chatSessions.set(requestKey, requestMessages); chatBusy.delete(requestKey);
  if (persona === "analyst") investigations.set(requestBase,{answer:result,question});
  if (chatGameId === requestKey) { renderChat(); input.focus({preventScroll:true}); }
});
$("#chat-input").addEventListener("focus",()=>{
  if(ballTimer) { clearInterval(ballTimer); ballTimer=null; }
  if(replayTimer) { clearInterval(replayTimer); replayTimer=null; }
  renderEvents(); renderPitch();
});
$("#chat-input").addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("#chat-form").requestSubmit(); } });
document.querySelectorAll("[data-screen-target]").forEach((button) => button.addEventListener("click", () => setScreen(button.dataset.screenTarget)));
document.querySelectorAll("[data-enter-role]").forEach((button) => button.addEventListener("click", () => enterRole(button.dataset.enterRole)));
$("#change-role").addEventListener("click", () => { $("#onboarding").hidden = false; $(".page").hidden = true; $("#screen-nav").hidden = true; $("#change-role").hidden = true; $("#theme-switcher").hidden = true; window.scrollTo({top:0,behavior:"instant"}); });
document.addEventListener("click", (event) => {
  const workspaceQuestion = event.target.closest("[data-workspace-question]");
  if (workspaceQuestion) {
    const playerId = workspaceQuestion.dataset.reviewPlayer;
    if (playerId) { playerSelect.value = playerId; renderPlayer(); renderCoach(); renderWorkload(); renderRolePanels(); chatSuggestions(); syncUrl(); }
    focusAssistant();
    $("#chat-input").value = workspaceQuestion.dataset.workspaceQuestion;
    $("#chat-form").requestSubmit();
    return;
  }
  const teamButton = event.target.closest("[data-coach-team]");
  if (teamButton) {
    const next = activeGame.players.find(p=>p.team===teamButton.dataset.coachTeam && p.role==="CM") || activeGame.players.find(p=>p.team===teamButton.dataset.coachTeam);
    playerSelect.value = next.id; playerSelect.dispatchEvent(new Event("change")); announce(`${next.team} selected.`); return;
  }
  const jump = event.target.closest("[data-jump-minute]");
  if (jump) { ballSecond = Math.round(Number(jump.dataset.jumpMinute)*60); setScreen("match"); renderPitch(); announce(`Replay opened at ${jump.dataset.jumpMinute}′.`); return; }
  const go = event.target.closest("[data-go-screen]"); if (go) setScreen(go.dataset.goScreen);
  if (event.target.closest("#download-report")) downloadBrief();
  if (event.target.closest("#read-latest") && "speechSynthesis" in window) {
    const text = $("#recap-headline").textContent + ". " + $("#recap-summary").textContent;
    const style = commentaryStyle;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = style === "Youth-friendly" ? 0.88 : style === "Casual companion" ? 1.04 : 0.96;
    utterance.pitch = style === "Youth-friendly" ? 1.12 : 1;
    speechSynthesis.cancel(); speechSynthesis.speak(utterance);
  }
});
gameSelect.addEventListener("change", render); viewSelect.addEventListener("change", () => enterRole(viewSelect.value)); playerSelect.addEventListener("change", () => { renderPlayerChoices(); renderPlayer(); renderCoach(); renderWorkload(); renderRolePanels(); chatSuggestions(); syncUrl(); });
document.addEventListener("click", (event) => {
  const flavorButton = event.target.closest("[data-flavor-choice]");
  if (flavorButton) { setFlavor(flavorButton.dataset.flavorChoice); return; }
  const matchButton = event.target.closest("[data-match-choice]");
  if (matchButton) { gameSelect.value = matchButton.dataset.matchChoice; gameSelect.dispatchEvent(new Event("change", {bubbles:true})); return; }
  const playerButton = event.target.closest("[data-player-choice]");
  if (playerButton) { playerSelect.value = playerButton.dataset.playerChoice; playerSelect.dispatchEvent(new Event("change", {bubbles:true})); return; }
  const styleButton = event.target.closest("[data-commentary-style]");
  if (styleButton) { commentaryStyle = styleButton.dataset.commentaryStyle; localStorage.setItem("agora-match-commentary", commentaryStyle); configureWorkspace(); return; }
  const scaleButton = event.target.closest("[data-text-scale]");
  if (scaleButton) { setTextScale(scaleButton.dataset.textScale); return; }
  if (event.target.closest("#simple-toggle")) setSimpleLanguage(!simpleLanguage);
  if (event.target.closest("#voice-command")) startVoiceCommand();
  const eventRow = event.target.closest("[data-event-id]");
  if (eventRow) {
    hasSelectedEvent = true;
    const ordered = [...sourceGame.events].sort((a,b)=>a.minute-b.minute||a.id.localeCompare(b.id));
    replayIndex = ordered.findIndex((item)=>item.id===eventRow.dataset.eventId);
    const selected = ordered[replayIndex]; if (selected) ballSecond = Math.round(selected.minute*60);
    if (replayTimer) { clearInterval(replayTimer); replayTimer = null; }
    renderEvents(); renderPitch(); return;
  }
  const pulse = event.target.closest("[data-pulse-minute]");
  if (pulse) { ballSecond = Number(pulse.dataset.pulseMinute)*60; renderPitch(); return; }
  const matchupCase = event.target.closest("[data-case-index]");
  if (matchupCase) { const cases = investigations.get(analysisBase())?.answer.visualization?.cases || [...chatMessages].reverse().find((item)=>item.visualization?.type === "fullback_winger_cases")?.visualization.cases || chatEvidence("Show every fullback vs winger case on the pitch").visualization?.cases; if (cases) showMatchupCase(cases,Number(matchupCase.dataset.caseIndex)); return; }
  const openCases = event.target.closest("[data-open-matchups]");
  if (openCases) { const message = chatMessages[Number(openCases.dataset.openMatchups)]; renderMatchupExplorer(message?.visualization); setScreen("stories"); requestAnimationFrame(()=>$("#matchup-explorer").scrollIntoView({behavior:"smooth",block:"start"})); return; }
});
$("#replay-range").addEventListener("input", (event) => {
  hasSelectedEvent = true;
  replayIndex = Number(event.target.value);
  const selected = [...sourceGame.events].sort((a,b)=>a.minute-b.minute||a.id.localeCompare(b.id))[replayIndex];
  if (selected) ballSecond = Math.round(selected.minute*60);
  renderEvents(); renderPitch();
});
$("#ball-range").addEventListener("input", (event) => { ballSecond = Number(event.target.value); renderPitch(); });
$("#ball-play").addEventListener("click", () => {
  if (ballTimer) { clearInterval(ballTimer); ballTimer=null; renderPitch(); return; }
  if (replayTimer) { clearInterval(replayTimer); replayTimer=null; renderEvents(); }
  startBallReplay();
});
$("#ball-speed").addEventListener("click", cyclePlaybackSpeed);
$("#replay-speed").addEventListener("click", cyclePlaybackSpeed);
$("#ball-next-moment").addEventListener("click", () => {
  const ordered = [...sourceGame.events].sort((a,b)=>a.minute-b.minute||a.id.localeCompare(b.id));
  const keyMoments = ordered.map((event, index) => ({event,index})).filter(({event}) => keyMomentTypes.has(event.type));
  const next = keyMoments.find(({event}) => event.minute * 60 > ballSecond + 1) || keyMoments[0];
  if (!next) return;
  if (ballTimer) { clearInterval(ballTimer); ballTimer = null; $("#ball-play").textContent = "▶ Play"; }
  if (replayTimer) { clearInterval(replayTimer); replayTimer = null; }
  hasSelectedEvent = true; replayIndex = next.index; ballSecond = Math.round(next.event.minute * 60);
  renderEvents(); renderPitch();
});
$("#replay-back").addEventListener("click", () => { hasSelectedEvent=true; clearInterval(replayTimer); replayTimer = null; replayIndex = Math.max(0, (replayIndex ?? 0) - 1); const e=[...sourceGame.events].sort((a,b)=>a.minute-b.minute||a.id.localeCompare(b.id))[replayIndex]; if(e)ballSecond=Math.round(e.minute*60); renderEvents(); renderPitch(); });
$("#replay-forward").addEventListener("click", () => { hasSelectedEvent=true; clearInterval(replayTimer); replayTimer = null; replayIndex = Math.min(sourceGame.events.length - 1, (replayIndex ?? 0) + 1); const e=[...sourceGame.events].sort((a,b)=>a.minute-b.minute||a.id.localeCompare(b.id))[replayIndex]; if(e)ballSecond=Math.round(e.minute*60); renderEvents(); renderPitch(); });
$("#replay-start").addEventListener("click", () => { hasSelectedEvent=true; clearInterval(replayTimer); replayTimer = null; replayIndex = 0; ballSecond=0; renderEvents(); renderPitch(); });
$("#replay-toggle").addEventListener("click", () => {
  hasSelectedEvent = true;
  if (replayTimer) { clearInterval(replayTimer); replayTimer = null; renderEvents(); return; }
  if (ballTimer) { clearInterval(ballTimer); ballTimer = null; $("#ball-play").textContent = "▶ Play"; }
  startEventReplay();
});
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-focus-player]");
  if (!button) return;
  playerSelect.value = button.dataset.focusPlayer;
  renderPlayer(); renderCoach(); renderWorkload(); renderRolePanels(); chatSuggestions(); syncUrl();
});

async function init() {
  try {
    updatePlaybackSpeed();
    fetch("/data/verification.json").then(r=>r.ok?r.json():null).then(report=>{ if(report) $("#accuracy-summary").innerHTML=`<p><strong>${report.passed}/${report.total} synthetic acceptance checks passed.</strong></p><p>${esc(report.scope)}</p><p>Live LLM evaluation: ${esc(report.live_llm_evaluation)}. Connection status does not certify answer quality.</p>`; else $("#accuracy-summary").textContent="Verification report unavailable. All match data is synthetic; live LLM quality is not certified."; }).catch(()=>{$("#accuracy-summary").textContent="Report unavailable. Live LLM quality is not certified.";});
    const indexResponse=await fetch("/data/analysis-index.json"); if(!indexResponse.ok) throw new Error("analysis index missing"); analysisIndex=await indexResponse.json();
    const [response, teamHistory, playerHistory, liveEvents, tactical, wearables] = await Promise.all([
      fetch("/data/games.json"), fetch("/data/team_history.json"), fetch("/data/player_history.json"),
      fetch("/data/live_events.json"), fetch("/data/live_tactical_metrics.json"), fetch("/data/live_wearables.json")
    ]);
    catalog = await response.json();
    const [th, ph, le, tm, we] = await Promise.all([teamHistory.json(), playerHistory.json(), liveEvents.json(), tactical.json(), wearables.json()]);
    dataFeeds = {teamHistory:th, playerHistory:ph, liveEvents:le, tactical:tm, wearables:we};
    if (!response.ok || !catalog.synthetic || catalog.games.length < 2) throw new Error("Synthetic match catalog is incomplete");
    const params = new URLSearchParams(location.search);
    const requestedFlavor = params.get("flavor");
    if (["classical", "modern"].includes(requestedFlavor)) visualFlavor = requestedFlavor;
    const requestedScale = Number(params.get("size"));
    if ([1, 1.1, 1.2].includes(requestedScale)) textScale = requestedScale;
    if (params.has("simple")) simpleLanguage = params.get("simple") === "1";
    applyFlavor();
    gameSelect.innerHTML = catalog.games.map((game) => "<option value=\"" + esc(game.match.game_id) + "\">" + esc(game.match.label) + "</option>").join("");
    if (catalog.games.some((g) => g.match.game_id === params.get("match"))) gameSelect.value = params.get("match");
    const requestedView = params.get("view");
    if (["fan", "analyst", "coach"].includes(requestedView)) viewSelect.value = requestedView;
    else if (requestedView === "explorer" || requestedView === "studio") viewSelect.value = requestedView === "explorer" ? "analyst" : "coach";
    else if (["fan", "analyst", "coach"].includes(localStorage.getItem("agora-match-role"))) viewSelect.value = localStorage.getItem("agora-match-role");
    requestedPlayer = params.get("player") || "";
    if(params.has("at") && /^\d+$/.test(params.get("at"))) requestedSecond=Number(params.get("at"));
    activeScreen = screenNames.includes(params.get("screen")) ? params.get("screen") : AgoraExperience.config[viewSelect.value].home;
    try {
      const health = await fetch("/api/health");
      if (health.ok) {
        const state = await fetch("/api/state?game_id=" + encodeURIComponent(gameSelect.value) + "&view=" + encodeURIComponent(viewSelect.value));
        const payload = await state.json();
        if (state.ok && typeof payload.foundry_configured === "boolean" && payload.match) { serverAvailable = true; foundryConfigured = payload.foundry_configured; foundryMode = payload.foundry_mode || (foundryConfigured ? "single-model" : "demo"); foundryConnection = payload.foundry_status?.connection || (foundryConfigured ? "unverified" : "unconfigured"); }
      }
    } catch (_error) { /* Public static preview has no server-side Foundry proxy. */ }
    document.querySelectorAll("[data-enter-role]").forEach(button=>{ button.disabled = false; });
    $("#onboarding-status").textContent = "Two synthetic matches ready.";
    const hasRole = ["fan", "analyst", "coach", "explorer", "studio"].includes(requestedView) || ["fan", "analyst", "coach"].includes(localStorage.getItem("agora-match-role"));
    if (hasRole) enterRole(viewSelect.value, true);
    else { $(".page").hidden = true; $("#screen-nav").hidden = true; $("#change-role").hidden = true; $("#onboarding").hidden = false; }
  } catch (error) { $(".page").hidden = true; $("#onboarding").hidden = false; $("#onboarding-status").textContent = "The match data could not load. Reload to try again."; $("#reload-data").hidden = false; }
}
$("#reload-data").addEventListener("click",()=>location.reload());
init();
