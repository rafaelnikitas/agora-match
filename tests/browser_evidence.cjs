// Data-contract tests for the pure browser fallback; no browser automation.
const fs=require('node:fs');
const assert=require('node:assert/strict');
const {answer,projectView}=require('../static/evidence.js');
const catalog=JSON.parse(fs.readFileSync('static/data/games.json','utf8'));
let checks=0;
function check(value,message){assert.ok(value,message);checks++;}
for(const full of catalog.games){
  for(const second of [0,1200,1800,full.available_through_seconds]){
    const boundaries=JSON.parse(fs.readFileSync('static/data/analysis-index.json')).games[full.match.game_id];
    const boundary=boundaries.filter(t=>t<=second).at(-1);
    const game=projectView(full,JSON.parse(fs.readFileSync(`static/data/analysis/${full.match.game_id}-${boundary}.json`)));
    check([...game.tracking_snapshots,...game.matchup_events].every(e=>Math.round(e.minute*60)<=second),"all retained raw frames and matchup rows respect cutoff");
    const a=answer(game,'Show every fullback vs winger case on the pitch','analyst','N8',true);
    check(a.topic==='fullback_winger','wide query routes to cases');
    check(a.visualization.cases.every(e=>Math.round(e.minute*60)<=second),'no later visual cases');
    check(a.facts.every(f=>f.analysis_seconds<=second),'facts carry cutoff');
    const tactics=answer(game,"How many attacks ended in crosses?","fan","N8");
    check(tactics.facts.every(f=>f.value!=="0/0"),"empty attack rates stay unavailable");
    const player=answer(game,'How is Luca Gray playing?','fan','N8');
    check(player.text.includes('Luca Gray'),'named player overrides selection');
    const load=answer(game,'Show Milo Vale running output','coach','N8');
    if(second<4200) check(load.facts.length===0,'incomplete paired windows withheld');
    check(answer(game,'Predict the winner','fan','N8').topic==='unsupported','prediction rejected');
    check(answer(game,'How is Mystery Striker playing?','fan','N8').topic==='unsupported','unknown player rejected');
  }
  const history=answer(full,'Compare Luca Gray xG with last five matches','analyst','N8');
  check(history.facts.length>=3,'history uses canonical current and prior facts');
}
console.log(JSON.stringify({browser_fallback_checks:checks,passed:checks,scope:'Deterministic data contract, not live LLM quality'}));
