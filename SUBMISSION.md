# Agora Match — submission materials

Updated **27 October 2026**. Use the sections below for the hackathon project-page fields.

## Project title

**Agora Match — The story behind the score**

## Elevator pitch

One match. Many perspectives. Agora Match turns synthetic football events, player positions, wearable samples, and fictional histories into evidence-linked intelligence for fans, analysts, coaches, and broadcast teams. Follow the ball, ask why a moment matters, inspect a player or matchup, and export a timed insight card. Azure Container Apps hosts the working application; Microsoft Foundry powers three specialist AI stages that select facts, explain them for the chosen audience, and review the draft.

## Project description

Football audiences need different explanations of the same match. A fan wants to understand a moment, an analyst wants to inspect the supporting cases, and a coach wants a focused review cue. Agora Match combines one shared evidence service with three purpose-built workspaces.

- **Fan:** follow the synthetic ball replay, jump to key moments, generate commentary, listen through browser text-to-speech, and ask questions combining current events with recent team history. A corner can surface both teams’ seven-match set-piece records, with denominators and source events.
- **Analyst:** request fullback-versus-winger encounters and open linked visual cases. Inspect tagged outcomes and prior sampled positions, compare attacking patterns and historical baselines, and export a timed broadcast card.
- **Coach:** scan prioritized passing, spacing, and running-output cues; inspect a player; and ask for a short evidence summary to prepare a review conversation.

Player pages add movement heatmaps, position-adjusted KPIs, a transparent demo rating trace, tagged opponent encounters, and comparisons with recent synthetic appearances. The replay clock governs chat, statistics, recaps, heatmaps, ratings, and exports. At 20:00, later events disappear: the score is 0–0 and the available matchup sample falls from eight cases to one.

The prototype connects current action, historical context, audience-specific explanation, and an inspectable on-screen output. Its broadcast JSON carries source facts, match timing, audience copy, and expiry for a possible studio integration.

## How AI adds value

The Azure application invokes **GPT-OSS-120B, version 1**, deployed in **Microsoft Foundry**. Three bounded specialist roles share that model:

1. **Match analyst:** selects and orders relevant, known fact IDs from the evidence bundle.
2. **Audience narrator:** explains the selected evidence for a Fan, Analyst, or Coach.
3. **Evidence reviewer:** checks the draft against the supplied evidence.

Application code calculates statistics, inserts canonical fact values, validates references and numeric claims, and coordinates the handoffs. A rejected draft receives at most one controlled narration correction and must pass the checks again. If the process cannot finish successfully, the app returns a clearly labeled evidence template.

The LLM connects a live-style moment to historical context and explains it at the chosen level of detail. Users can open supporting facts, source events, and the actual execution trace. Commentary uses the available match evidence; speech playback uses the visitor’s browser.

Orchestration runs in custom Python. The deployment uses Foundry Models; Foundry Agent Service and Microsoft Agent Framework are not part of this implementation.

## Microsoft and Azure technologies

| Technology | Implemented role |
|---|---|
| Microsoft Foundry | Hosts the model used for evidence selection, narration, and review |
| Azure Container Apps | Hosts the browser UI and Python API together over HTTPS |
| Managed identity and Azure Identity | Provide keyless access to the deployed model |
| Azure Container Registry | Stores the deployed container image |
| Application Insights and Log Analytics | Provide the configured monitoring foundation; request-metric ingestion has been observed |
| Bicep and GitHub Actions | Define Azure infrastructure and validate the repository; cloud automation setup is documented separately |

## Verification results

A retained live run exercised **seven fixed scenarios for each of three audiences**, covering both synthetic fixtures:

- **21/21** expected topic and evidence-value checks passed.
- **21/21** responses used fresh AI calls, without cached answers.
- **Five** answers recovered through bounded correction; **zero** final fallbacks occurred in that run.
- Median API response time was **9.6 seconds**; p95 was **13.0 seconds**, excluding cold starts.

These are fixed development acceptance cases used during hardening. Independent human explanation-quality review and a single-versus-three-role comparison remain pending. The results establish execution and the tested evidence checks; they do not establish an overall semantic-accuracy percentage or measured multi-agent superiority.

Recorded regression checks also passed: **67 unit/API tests**, **82 synthetic acceptance examples**, and **73 browser-fallback assertions**. The [live verification report](docs/azure-live-verification.md) links the per-request results, deployment provenance, and remaining evaluation work.

## Synthetic data and reproducibility

All clubs, players, matches, histories, events, coordinates, and telemetry are fictional. Deterministic generators produce **two fixtures**, seven-match team histories, player appearance/minute records, tagged events, minute-sampled player positions, illustrative event-constrained ball paths, and synthetic wearable readings.

The documented inputs include `team_history.json`, `player_history.json`, `live_events.json`, `live_tactical_metrics.json`, and `live_wearables.json`. No Premier League match data or broadcast footage is redistributed. The static experience can be regenerated with Python and run without API keys; container and Azure configurations are included.

Tracking is minute-sampled, and the second-by-second ball path is illustrative interpolation. The event feed is a sparse tagged sample. Player ratings are transparent demo scores. Running-output and paired-gap signals require football context and do not diagnose fatigue or establish marking responsibility.

See [dataset requirements](docs/dataset-requirements.md), [local setup](README.md#run-it-locally), and [Azure deployment guidance](docs/azure-readiness.md).

## Practical impact and adoption

The initial business user is a digital match-content producer who needs concise, sourced audience copy and a machine-readable on-screen card. Fan and coach experiences reuse the same evidence service.

A pilot would integrate a permitted provider feed, validate timing and identifiers, and measure editor acceptance, time to an approved insight, correction rate, latency, and cost per accepted card. Real tracking and performance conclusions require suitable licensed data and independent validation. Detailed operational trace exports, cost review, and production hardening remain documented follow-up work.

## Submission links

| Portal field | URL |
|---|---|
| Working Azure application | https://agora-demo-d3ysdvzmwpuoi.orangewater-9594c3f1.swedencentral.azurecontainerapps.io/ |
| YouTube demonstration | https://youtu.be/nxC-Q8esbOQ |
| Public GitHub repository | https://github.com/rafaelnikitas/agora-match |
| Alternate video player and MP4 download | https://agoramatch.russettitan64.chatgpt.site/showcase |
| Static fallback experience | https://agoramatch.russettitan64.chatgpt.site/ |

Use the Azure link for the AI-backed experience and the YouTube URL for the portal’s video field. The separate static fallback provides deterministic answers.

The entrant reports completing YouTube publication. The URL above is the one assigned to the uploaded draft; signed-out playback has not been independently verified here. If a separate upload was published, replace it with that video’s public URL before submitting.

## Judge testing instructions

1. Open the **Azure application**; visitors need no account or API key. Select **Fan** and **Northbridge vs Eastport**.
2. Ask **“Why is this set piece interesting?”** Open the supporting facts and **“How this answer was checked.”** The label distinguishes fresh or cached Foundry output from an evidence fallback.
3. Switch to **Analyst**, ask **“Show every fullback vs winger case on the pitch,”** and open the visual cases. Compare the late snapshot with **20:00** on the replay.
4. Open a player for KPIs, heatmap, history, and rating evolution. Switch to **Coach** and use **“Prepare this review.”**
5. Preview a broadcast card in the analyst desk and inspect its JSON export. Try **Harbor City vs Redvale** for the second fixture.

The demo may need time to start after inactivity; AI requests can take several seconds. The app displays a clearly labeled fallback if a model request cannot finish. See the verification report for measured response times and their scope.

## Demonstration video

**Title:** Agora Match — AI Football Intelligence | Inside the Game

**Video:** https://youtu.be/nxC-Q8esbOQ

The 114-second narrated, captioned walkthrough was captured from the Azure app on 27 October 2026. It shows all three customer journeys, fresh Foundry answers, supporting facts, an actual three-stage trace, visual matchups, replay-aware evidence, player analysis, commentary, and broadcast export. App panels are genuine captures edited for clarity; the replay uses successive captured frames.

Narration is synthesized; no music or match broadcasts are used. [Production credits and video release identity](docs/demo-assets.md).

## Why Agora? · Αγορά

The ancient Greek agora was a public gathering place for conversation and different viewpoints. Agora Match brings that spirit to football: a shared game, shared evidence, and the freedom to explore it through different eyes. **The match brings us together. Your perspective shapes the experience.**

## Entrant’s final portal checklist

- Check the YouTube URL while signed out and add it to the portal’s video field.
- Enter the pitch, description, Microsoft technologies, public repository URL, Azure app URL, and testing instructions. Complete the category and team fields.
- Review eligibility, registration, ownership, licensing, and rule declarations personally; retain the supplied asset credits.
- Complete the final portal submission and retain confirmation. This document does not establish that the portal entry has been submitted.
- Keep the submitted demo accessible through judging and review Azure credit, spending protection, and availability.
