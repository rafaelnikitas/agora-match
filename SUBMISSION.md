# Agora Match — submission materials

## Elevator pitch

Football has more to say than the score. Agora Match turns synthetic match events, player positions, wearable samples, and fictional team history into evidence-linked explanations for fans, analysts, and coaches. Follow the ball, ask why a moment matters, inspect a player or matchup, and turn a finding into a timed broadcast card. The same evidence becomes three focused experiences, with sample sizes, source links, and uncertainty kept visible.

## Why Agora? · Αγορά

The ancient Greek agora was a public gathering place for conversation, ideas, and different viewpoints. Agora Match brings that spirit to football: the match brings us together, while each person's perspective shapes the experience. Anyone can follow the story as a fan, investigate the evidence as an analyst, or consider the choices as a coach—and switch perspectives at any time. One match. Many perspectives.

## Links

- Working Azure app: https://agora-demo-d3ysdvzmwpuoi.orangewater-9594c3f1.swedencentral.azurecontainerapps.io/
- Static fallback demo: https://agoramatch.russettitan64.chatgpt.site/
- Public source: https://github.com/rafaelnikitas/agora-match
- Narrated walkthrough: https://agoramatch.russettitan64.chatgpt.site/showcase.html
- **Required video platform URL: pending upload to YouTube, Vimeo, Facebook Video, or Youku.** The self-hosted walkthrough above is a review copy; it does not replace that submission requirement.

## Problem and users

An isolated statistic rarely explains why a moment matters. Fans need a concise story, analysts need inspectable cases, and coaches need a qualified review cue. Agora uses a shared evidence cutoff and role-specific workflows to connect current actions with historical context without presenting a small synthetic sample as a prediction.

## What the prototype demonstrates

1. A corner can surface both teams' seven-match set-piece record, with denominators and source events.
2. Analysts can inspect eight tagged winger/fullback encounters on a pitch. At 20:00, only the one encounter that has occurred remains visible.
3. Player pages combine positional KPIs, a synthetic movement heatmap, historical rates, a rating trace, and tagged opponent encounters.
4. Coach review combines sampled output and spacing cues, while declining unsupported fatigue diagnoses and inferred marking assignments.
5. A broadcast JSON card includes evidence, match timing, and expiry for a possible studio integration.

## Microsoft technology and actual execution status

The optional Python service integrates Microsoft Foundry model deployments through Azure Identity. Three bounded roles perform analysis, audience narration, and evidence review. Deterministic code supplies canonical fact values and source IDs; rejected or unavailable model output falls back to an evidence-based response. Azure Container Apps infrastructure is defined in Bicep, with managed identity, monitoring, health checks, and deployment scripts.

**The Azure app is deployed and actual Foundry model calls have been verified with managed identity.** The separate public static demo uses deterministic responses. Live acceptance evaluation measures routing, execution/fallback rate and latency; it does not establish semantic accuracy. A single-versus-three-role quality comparison and independent human review remain separate work.

[Live Azure verification results and remaining tasks](docs/azure-live-verification.md). The latest fixed suite completed 21 fresh AI answers, including five bounded corrections; qualitative review remains pending.

## Data statement

All teams, players, matches, histories, events, positions, ratings, and telemetry are invented. The source includes deterministic generators for two fixtures, seven-match team histories, individual appearance records, tagged events, minute-sampled player positions, event-constrained illustrative ball positions, and wearable samples. No Premier League match data or footage is redistributed. See [dataset requirements](docs/dataset-requirements.md).

## Verification

Local release checks: 67 unit/API tests, 82 synthetic acceptance examples, and 73 browser-fallback assertions passed. These are regression checks over synthetic fixtures and mocked model failures; they do not measure live LLM accuracy. See [evaluation details](docs/accuracy-and-evaluation.md).

## Practical adoption path

The initial user is a digital match-content producer who needs concise, sourced copy and a machine-readable overlay. A pilot would ingest a permitted provider feed, validate event identity and timing, and measure editor acceptance, correction rate, latency, and cost per accepted card. The fan and coach views reuse the evidence service. Real tracking, xG models, and performance conclusions would require compatible licensed data and independent validation.

## Remaining entry steps

1. Upload the updated 1:54 MP4 to an accepted video platform and paste its public URL into the entry.
2. Use the Azure app and its retained live verification evidence when describing demonstrated Microsoft AI execution; review the documented limitations.
3. Paste the pitch, app URL, public source URL, technology description, and video URL into the hackathon project page.
4. The entrant must verify eligibility/team details, answer ownership and rule attestations, and perform the final portal submission.

The updated recording was captured from the Azure app on 27 October 2026. It includes fresh Fan, Analyst, and Coach Foundry answers, visible source facts, and an actual three-stage execution trace. It remains a self-hosted review copy until uploaded to an accepted video platform.

## Video upload copy

**Title:** Agora Match — the story behind the score | Inside the Game

**Description:** A 1-minute-54-second customer walkthrough of Agora Match, a football intelligence prototype for fans, analysts, coaches, and broadcast workflows. Captured from the Azure application on 27 October 2026, the video shows real Microsoft Foundry answers with historical context, supporting facts and execution stages; visual fullback-versus-winger cases; replay-aware evidence; player heatmaps and ratings; qualified coach review; commentary; and timed broadcast export. Azure Container Apps hosts the app, and managed identity provides keyless Foundry access. Three specialist stages share GPT-OSS-120B and use custom Python orchestration. The fixed 21-case live acceptance run verifies expected evidence checks, with human explanation-quality review still pending. All football data and teams are fictional. Narration is synthesized; no match footage or music is used. App and source links are listed above.

Video production and voice credits: [demo assets](docs/demo-assets.md).
