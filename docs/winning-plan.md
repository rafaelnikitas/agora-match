# Agora Match: submission and winning plan

**Checked:** 26 October 2026  
**Submission deadline:** 27 October 2026, 11:59 p.m. Pacific Time. Confirm the timestamp on the submission page before uploading.

## Positioning

**Agora Match turns synthetic football events into clear, evidence-linked match stories for fans, analysts, coaches, and broadcast teams.** The signature idea is a player-first “what happened, why it matters, show me the evidence” loop: follow the ball, ask a question, inspect a visual case, and turn a finding into a timed broadcast card.

The product should be presented as a broadcaster and streaming companion that also works for individual fans. A viewer can follow one player or ask a question in plain language; a studio user can inspect tagged cases and export a structured overlay. The business hypothesis is that concise, sourced explanations can make a stream more interactive while reducing the time needed to find and package a useful match story. These are hypotheses to validate with broadcasters, not measured results.

## Where the project stands

Agora already has two fictional matches, player and team histories, event and tracking samples, role-based Fan/Analyst/Coach screens, a second-by-second illustrative ball path, a collapsed play-by-play timeline, a match Q&A, player metrics, coach review cues, ranked insights, and timed JSON overlay output. Every fixture is synthetic.

The new playback uses 1×/2×/4× speed and a jump to the next tagged moment. The interface keeps secondary controls behind clear labels and a collapsed timeline. The Foundry-backed server can use three model roles—Match Analyst, Role Narrator, Evidence Reviewer—with one shared evidence bundle and deterministic fallback. Automated tests cover numeric-claim rejection and reviewer rejection.

**Limits to state plainly:** the public hosted demo is static and uses deterministic answers; Foundry needs configured model deployments in a server-backed run. The ball path is interpolated between synthetic samples, and player locations are minute-sampled. This is a working prototype, not a live licensed Premier League data service.

## Submission-critical actions

Complete these first because they gate eligibility or can erase the value of the product:

1. **Use a public GitHub repository for the competition entry.** A private personal copy is useful for development, but the rules require a public repository. Keep the existing private copy if desired and publish a separate competition copy only after checking for secrets and verifying that every match/player record is synthetic.
2. **Record a sub-two-minute demo** that shows the app operating, not slides. Use original narration and no unlicensed marks, footage, music, or other copyrighted material.
3. **Put the public app URL, public repository URL, concise pitch, and video URL on the entry page.** Check every link from a signed-out browser.
4. **Make the synthetic-data boundary obvious** in the pitch, UI, README, dataset guide, and video. Never imply that fictional records are official Premier League statistics.

These deliverables are required by the [official rules](https://aka.ms/insidethegame/rules). The hackathon asks for synthetic, football-realistic data and judges five criteria at equal 20% weight.

## Build order for the remaining time

### 1. Verify the Azure and Foundry path

The [Azure readiness package](azure-readiness.md) now includes keyless infrastructure, the production API, actual stage traces, controlled failure recovery, and smoke/evaluation scripts. Local tests and Bicep compilation pass. Provisioning, live model execution, cloud telemetry, and GitHub CI still need verification in the target accounts.

- Configure the three checked model roles in the server-backed build: a match reader, audience narrator, and cautious evidence reviewer. They can share a deployment; compare different deployments only when they improve measured quality or latency. Keep deterministic retrieval and calculations in code.
- Show the handoff in the UI and demo: **verified facts → match analyst → role narrator → evidence reviewer**. Show the source facts beside the final text.
- Log stage name, model deployment, duration, success/fallback, and evidence IDs. Do not log API keys or full user secrets.
- Set per-call timeouts. If a stage fails, returns an unsupported number, or the reviewer rejects the answer, return the deterministic answer. Never block the match clock on model calls.
- Test whether the extra model roles improve grounded-answer quality over a single narrator. If they add delay without measurable quality improvement, keep the roles for analyst/high-impact questions and use one model for simple fan questions.

Microsoft describes Foundry as a model and agent platform; its Agent Service and Agent Framework support sequential and concurrent workflows, observability, evaluation, and managed agents. Agora's current POC orchestrates Foundry model deployments in its Python service; claiming a Foundry-managed workflow would be inaccurate until one is configured. A credible next step is to move the tested handoff into an Agent Framework workflow and show its trace in Foundry.

### 2. Rehearse one memorable end-to-end story

Use a prepared match and a repeatable question rather than wandering through every tab:

1. Start the key-moment replay and use **Next moment** to show the pitch, clock, and event moving together.
2. Ask: **“Show every winger versus fullback encounter and who came out ahead.”** Open the visual case board; point to the event time, players, outcome, and sampled-position caveat.
3. Follow a player and show a position-aware metric with its match rank and recent synthetic comparison.
4. Ask about a set piece or recent attack pattern. Show the historical evidence and the answer tailored to the selected role.
5. Preview and download the timed broadcast card. Point out its source evidence and synthetic provenance.
6. Close on the three Foundry roles and the reviewer/fallback path.

Aim for 90–105 seconds. Let the visual answer carry the story; keep spoken explanations short. Nielsen Norman Group’s guidance supports showing the most useful action first, keeping controls recognizable, and revealing advanced details when requested. Agora applies that through one main replay action, speed choices, next-moment navigation, and a collapsed timeline.

### 3. Run a small, honest quality gate

- Maintain 20–30 representative questions with expected evidence IDs and acceptable caveats: historical set pieces, switches/crosses, player form, workload, and matchups.
- Measure retrieval coverage, supported-claim rate, numeric-claim rejection, p50/p95 response time, model-stage failures, and deterministic fallback rate.
- Compare the single-model and three-role modes on the same questions. Report measured results only; do not invent an accuracy percentage for the pitch.
- Re-run the unit suite and local build after the last content change. Verify both matches, Fan/Analyst/Coach, keyboard access, dark/light themes, event replay, chat follow-ups, overlay JSON, and no model-key exposure.

### 4. Show a practical business path

| User | Job to be done | Demonstrated value | Business measure to validate |
|---|---|---|---|
| Streaming or broadcast producer | Find a useful story and package it quickly | Ranked, timed overlay with source evidence | Time from event to approved graphic; overlays used per match |
| Analyst | Find repeated tactical or player matchups | Natural-language query opens tagged visual cases | Time to answer a scouting question; analyst edit rate |
| Fan | Understand a moment and follow a player | Plain-language Q&A, commentary, player view | Questions per session; return visits; self-reported understanding |
| Coach or performance staff | Review a possible workload or shape issue | Role-adjusted comparisons with explicit caveats | Review time; staff usefulness rating; false-alert rate |

Start with a **studio/streaming pilot** as the buyer and fans as the audience. The pitch is not “AI replaces commentators”; it is “a verified intelligence layer gives producers more explainable, customizable moments.” To validate it, interview a small group of producers/analysts, ask them to rank the generated cards, and compare generation/edit time with their current workflow. Provider licensing and rights to any real feed must be resolved before a commercial pilot.

## Rubric map

| 20% judging area | What judges should see | Remaining proof |
|---|---|---|
| Technological implementation | Reproducible synthetic fixtures, modular detectors, tests, API, Foundry model integration | Public repo, setup walkthrough, deployment/secret instructions, full test result |
| Agentic design and innovation | Distinct reader, narrator, reviewer; shared evidence; handoffs; rejection and fallback | Run a configured pipeline on camera and show stage trace/timing |
| Real-world impact | Broadcast JSON, role-specific value, production path, measurable pilot hypotheses | One buyer story and a credible integration boundary |
| User experience and presentation | Simple role onboarding, match-first replay, prompt Q&A, visual evidence cases | Tight video, large readable UI, no feature-tour sprawl |
| Category adherence | Synthetic-only football data; meaningful Microsoft AI platform use | Explicit submission category and proof that Foundry was actually used |

The best-aligned category is **Best Multi-Agent Orchestration**, with a credible **Grand Prize** case if the live Foundry path, video, repo, and business story are all complete. Do not claim Best Azure Cloud Native Integration unless the deployed app actually uses Azure services. The rules score category adherence as its own equal-weight pillar, so clearly name the category in the submission.

## 24-hour checklist

- [ ] Provision and verify the three Foundry roles using the Azure smoke/evaluation gates, or record the deterministic demo honestly if Azure access is unavailable.
- [ ] Record one clean 90–105 second walkthrough; inspect it once for timing, legibility, and unsupported claims.
- [ ] Publish the competition repository publicly after secret scan and synthetic-data audit; retain the personal private copy separately if preferred.
- [ ] Add a concise project pitch, demo URL, repository URL, video URL, and chosen category to the entry.
- [ ] Test the links while signed out and submit before the posted Pacific-time cutoff.

## Research notes

- [Microsoft Foundry Agent Service overview](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview): model choice, agent hosting, traces, evaluation, and deployment lifecycle.
- [Foundry workflows](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/workflow): repeatable sequential workflows and multi-agent handoffs.
- [Agent Framework orchestration patterns](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/): sequential, concurrent, handoff, group-chat, and Magentic patterns.
- [Microsoft guidance on agent design patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns/): use the lowest orchestration complexity that meets the need; multi-agent designs add latency, cost, and failure modes.
- [Nielsen Norman Group: Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) and [10 Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/): keep primary actions visible, reveal advanced controls on request, and make system state clear.
