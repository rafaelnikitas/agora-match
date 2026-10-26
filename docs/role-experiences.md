# Agora Match: three experiences over shared evidence

## Product contract

One synthetic match catalog powers three different workspaces. Choosing a role changes the default screen, layout, navigation, guided steps, question suggestions, player summary, and assistant's purpose. It does not change the underlying measurements.

### Fan — watch and understand

**Start:** Matchday. The pitch and question panel come first. Play continuously, change speed, or jump to a key moment. Full play-by-play stays closed until requested.

**Plan:** Follow the action → understand a moment → follow a player.

**Messages:** A direct takeaway in everyday language. Facts and source limits expand on demand. The selected player has a simple spotlight and fewer position metrics. Commentary and browser speech are optional.

### Analyst — ask and verify

**Start:** Analysis desk. Four investigation presets lead to fullback/winger cases, attack sequences, set-piece history, and player form. A persistent chat sits beside the evidence.

**Plan:** Choose a question → inspect cases and replay → export the finding.

**Messages:** Finding, observed denominator, source IDs, and coverage. The fullback/winger board maps the selected tagged encounter to the nearest player snapshot. Attack tiles jump to their replay time. A Markdown evidence brief includes the latest investigation and its sources.

### Coach — prioritize and review

**Start:** Review board. Select a team and inspect a short queue of spacing, pass-retention, or running-output cues. Each card identifies its player, measurement, observed window, and review step.

**Plan:** Scan the priorities → check a player → prepare a review conversation.

**Messages:** Observation, cautious review question, and limit. Cues are not a diagnosis, tactical-error verdict, or substitution recommendation. Pass-retention priorities require at least four tagged passes. Running-output priorities require at least two early efforts and a decline greater than 25%; the actual counts stay visible. Spacing cues compare the supplied 55′ and 70′ paired snapshots. These are transparent demo thresholds, not calibrated professional thresholds.

## Shared interaction standards

- Light and dark mode use the same information architecture. Role color is a secondary cue; labels, numbers, and icons also identify state.
- Role and theme preferences are saved on the device. Conversation state is isolated by match and role for the current page session.
- Plain language changes vocabulary without converting Analyst or Coach to Fan.
- Keyboard focus is visible. Form controls retain keyboard access. Reduced-motion preferences disable decorative transitions.
- Every assistant states the available data minute. Scrubbing the replay does not time-travel all statistics or historical retrieval: those still cover the full available synthetic snapshot.
- No referee section, real club footage, or real Premier League data is used.

## Foundry boundary

The public static demo uses deterministic evidence templates and says so. The Python server supports a configured Foundry analyst → audience narrator → evidence reviewer pipeline, with role-specific response goals and deterministic fallback. The UI does not claim the cloud model is connected until the API reports it.

## Acceptance checks

1. Enter each role: the default screen and assistant location match the contracts above.
2. Ask the same question in all roles: preserve the same facts while changing the answer's purpose. Repeat with plain language enabled.
3. Switch matches and roles: conversation history is isolated; player/team labels and sources update.
4. In Analyst, open every fullback/winger case, search attack patterns, jump from a tile to replay, and export the current evidence brief.
5. In Coach, inspect a cue: select that player, use their evidence, and preserve the cue's limit. Switch teams and confirm the priority queue changes.
6. In Fan, play and pause the pitch, cycle speed, jump to the next moment, and open play-by-play explicitly.
7. Verify light/dark presentation and a visible focus outline. Responsive CSS stacks the assistant and evidence panels on smaller screens; mobile viewport QA should be repeated on the target device before submission.

## Next delivery priorities

1. Configure and measure the real Foundry deployments; compare supported claims, latency, and fallback rate with the static template mode.
2. Run short usability sessions with one fan, analyst, and coach. Measure time to a first useful answer and time to locate its source.
3. Validate higher-frequency tracking, complete pass coverage, and role baselines before extending coaching conclusions.
4. Record a focused demonstration of question → visual evidence → role-specific explanation, then finish public-repository and video submission requirements.

## Validation record — 26 October 2026

- 39 Python tests pass, including persona preservation in plain language and team-history routing with a selected player.
- Both JavaScript files pass `node --check`; the static site builds successfully.
- Desktop browser checks cover the three landing screens, fan set-piece answer, analyst pattern search and encounter selection, coach-to-player selection, team switching, light/dark text contrast, and smart replay controls.
- Browser layout inspection found no horizontal overflow at the tested desktop viewport.
- The brief export click was exercised, but the cloud browser did not expose a download event. Download delivery remains a target-browser acceptance check.
- Screenshots: [Fan](images/agora-fan-workspace.jpg), [Analyst](images/agora-analyst-workspace.jpg), [Coach](images/agora-coach-workspace.jpg).
- No claim of mobile viewport certification, WCAG certification, or live Foundry deployment is made.
