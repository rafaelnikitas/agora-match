# Agora Match dataset requirements

## POC boundary

The published hackathon demo uses invented clubs, players, event logs, tracking points, player histories, and wearable records. Referee analysis is deferred in the current application. A future connected-data mode must be separate and must never silently replace the synthetic fixture. No Premier League match data is included. Every record should carry provenance so a viewer can distinguish synthetic, provider-supplied, and derived values.

The LLM is not the source of match data and must not calculate KPIs. A retrieval layer selects bounded records from the chosen match; deterministic code validates and aggregates them; the model may explain those verified results for Fan, Analyst, or Coach.

## Required entities

| Entity | Required fields | Enables |
|---|---|---|
| Match | `game_id`, `label`, `home`, `away`, `period`, `clock_seconds`, score, `data_mode`, `source_id` | Match selection, clock, score, attribution and disclosure |
| Player | `player_id`, `team_id`, shirt number, display name or pseudonym, role, active interval | Player pages, role KPIs, event attribution and peer groups |
| Event | Stable `event_id`, `game_id`, period, clock seconds, sequence, `team_id`, nullable `player_id`, `type`, `outcome`, `possession_id`, start location | Play-by-play, player metrics, matchup and explainable event citations |
| Attack/possession | Stable `attack_id` or `possession_id`, team, start/end time, linked event IDs, outcome | Recent attack patterns, switches, crosses, possession narratives |
| Provenance | `source_kind` (`synthetic`, `licensed_provider`, `public_dataset`, `derived`), source/version, generation or ingestion time, coverage note | Synthetic-only compliance, reproducibility, user trust |

Every event used to support an answer needs an event ID. Use explicit nulls for unavailable values; do not encode missing data as zero. Keep all IDs stable across event revisions, and include a revision/version field if corrections are possible.

## Optional feeds and feature requirements

| Feed | Minimum fields | Features it supports | What cannot be claimed without it |
|---|---|---|---|
| Event detail | Start/end x-y, receiver, pressure, body part, pass length, shot outcome, xG and xA with model version | xG/xA, progressive passes, chance creation, ball-carry choices | Advanced event KPIs are unavailable if event tags or coordinates are missing |
| Player tracking | Timestamp, player ID, x-y in metres, speed, sampling interval, coverage and orientation | Heatmap, speed bands, distance, spacing, pressure and load trend cues | Fatigue is not diagnosable from speed alone; report only observed sample changes |
| Possession/attack labels | Possession ID, team, start/end, phase, build lane, final action, event links | “Last N attacks” and tactical-sequence summaries | Do not infer a sustained tactic from a short or incomplete sequence |
| Recent match aggregates | Team/player ID, match window, metric, numerator, denominator, match IDs, competition scope | Set-piece context, recent form, last-five/season comparisons | Historical context is unavailable when match IDs, denominator, or coverage are unknown |
| Matchup ledger | Two player IDs, action type, attempt/result, time, linked event IDs | One-v-one outcomes and repeated battle summaries | Do not say a player “cannot beat” another from a few attempts |
| Ball replay | Match second, x/y metres, interpolation method, source snapshots | One-second ball cursor and recent path | Current ball path is synthetic interpolation between minute snapshots, not observed tracking |
| Lineups and substitutions | Player IDs, role, on/off times, formation, side/orientation | Minutes played, role-aware normalization, substitution impact | Do not compare raw totals without minutes and role context |

For a “player had these options when receiving the ball” view, include synchronized tracking for all 22 players and the ball near each ball-receipt event, plus event IDs linking receipt, pass/dribble/shot choices and outcomes. Event data without synchronized tracking cannot reliably reconstruct every available option.

## Canonical units and conventions

- Match event time is represented as integer `clock_seconds` from period start, alongside `period`; UI minutes are derived. Added time remains explicit rather than folded into an ambiguous decimal.
- The canonical pitch is 105 m by 68 m. Coordinates are metres from the home team’s attacking-left goal line; the home side attacks toward increasing x and the away side toward decreasing x, with period direction normalized. Explicit event attack_direction overrides this for independently oriented historical records. If the provider uses another orientation, normalize and preserve the original coordinates separately.
- Speed is km/h; distance is metres; stoppage and decision durations are seconds; xG/xA are probabilities in `[0,1]` with a named model/version.
- Roles use a controlled vocabulary (`GK`, `CB`, `FB`, `DM`, `CM`, `W`, `ST`) with optional provider role and formation position stored separately.
- Completed passes require an outcome; unsuccessful actions must remain distinct from missing outcomes. Own goals, penalties, cards, substitutions, stoppages, and restarts need explicit event types.
- Tracking timestamps must be monotonic per match and positions must be within pitch bounds. Sampling rate and missing-player coverage must be retained; do not present interpolated points as observed measurements.

## Checked-in synthetic feed files

The static visitor app ships six generated JSON files under `static/data/`. `python -m agora_match.build_static` regenerates them deterministically from the same scenario seed. Each feed is marked `data_mode: "synthetic"`; team and player identifiers are fictional and scoped to a game.

| File | Shape and key fields | UI use |
|---|---|---|
| `games.json` | Top-level catalog with two synthetic fixtures; match, players, event and attack logs, sampled player tracking, profiles, insight evidence, and provenance. Referee data is not part of the visitor UI. | Match selector, ball replay, expandable play-by-play, player page, insights, and coach review. |
| `team_history.json` | `games[game_id].teams[team_name]` has a seven-match `matches[]` ledger. Each match includes opponent, venue, score/result, formation, tactical counters, team aggregates, and an `players[]` appearance list with starts, minutes, role, stats, and synthetic substitute placeholders. Team `summary` includes W/D/L, goals, mean xG/possession, and number of matches with corner goals for/against. | The Analyst historical context and set-piece examples. |
| `player_history.json` | `games[game_id].players[player_id]` contains seven prior appearance rows, including opponent, venue, result, minutes, start flag, and per-match stats; includes `last5_average`, `season_average`, `matches_played`, position, and provenance. The synthetic season window is explicitly these seven generated matches. | Player form context and comparison table. |
| `live_events.json` | `games[game_id]` contains current match metadata, chronological `events[]` with stable IDs, type/outcome, minute, team/player, location and action-specific fields, plus `attacks[]`. | Narrative generation, play-by-play, match questions, and tactical sequence counts. |
| `live_tactical_metrics.json` | Match coordinate convention plus `frames[]` at sampled times with ball position, 22 player positions/speeds, team centroid/width/line-height, and opposition pressure counts. `event_options[]` links to event IDs and records the nearest pressure distance and up to four nearby passing options with receiver distances and space labels. | Tactical pitch, “what options were available?” replay, shape and pressure review. These are derived from nearest synthetic snapshots, not continuous video tracking. |
| `live_wearables.json` | Per-player `samples[]` include minute, speed, synthetic heart rate, acceleration, estimated metres/minute, effort zone, and provenance; summaries give peak speed and early/late high-effort counts. Feed metadata records the one-minute sampling interval and limits. | Coach workload chart and player trend review. Not clinical, verified device data, or a fatigue diagnosis. |

Historical lineups are made of 11 fictional appearances per team per match, with synthetic substitute stand-ins; the sum of their minutes is 990 team-player minutes. Player histories follow the 22 current fictional player IDs so the visitor can compare one chosen identity across the generated window. Historical score and W/D/L summaries derive from their match ledgers. All event/tactical/telemetry values are reproducible examples, not real match feeds.

## Current POC fields

The checked-in `static/data/games.json` is the runnable synthetic fixture. Its match records include `game_id`, label, teams, clock, score, and synthetic flag. Player records include stable IDs, club, number, fictional name, and role. Events include ID, minute, team/player, type/outcome, possession/attack IDs and coordinates; generated passes/shots also carry fields such as receiver, pass distance, xG/xA, and chance tags. Attacks contain lane, switch, end type, teammate-reach, and shot flags. Tracking snapshots contain player positions, role, team, number, speed, and a ball point. The tactical feed includes a one-second interpolated ball path and event-linked spatial options; player tracking remains minute-sampled. Seven-match fictional team aggregates support the set-piece examples; seven generated prior player match samples support last-five and season averages. The additional five files expose those historical values and the live event, positional-option, and workload feeds as independently consumable POC inputs.

Each game carries `data_provenance` metadata (`source_kind`, generator, schema version, and seed key); the match also carries an explicit synthetic flag. These are deliberately compact examples. Their sparse tagged event feed and low-frequency tracking are suitable for an interaction prototype, not a real performance evaluation or medical/scouting decision.

## Quality gates before enabling a feature

1. Reject records with unknown match/team/player IDs, duplicate IDs, impossible clock order, invalid outcomes, or out-of-bounds coordinates.
2. Validate score against goal events and player summaries against the underlying events; record every derived metric’s formula/version and denominator.
3. Check feed coverage by period, team, player, and event type. Mark low coverage and omit rankings where the comparison population is incomplete.
4. Require the historical match window, scope, and denominator before using phrases such as “in 7 matches” or “last season average.”
5. Ground every chat response in selected facts and include short evidence labels/IDs. The LLM may paraphrase; it cannot add statistics, causes, predictions, diagnoses, or official judgments.
6. Cache the normalized snapshot and generator/provider version so a match can be reproduced and replayed.

## How to extend the synthetic generator

Keep each scenario seed deterministic. Generate a small story first (for example, repeated switches before a corner), then generate event and tracking records that support it. Derive displayed statistics from those records instead of hand-writing the final stat line. Include at least two scenarios with different live situations, player-role diversity, a known historical window, linked event IDs, and intentional missing-data examples. Add tests for score reconciliation, pitch bounds, stable seeded output, denominators, and evidence IDs before adding a new metric to chat.

## Implemented accuracy contract (27 October)

- Every analytical view has an integer-second cutoff. Events, completed attacks, player frames, ratings and answers use that same evidence prefix. Attack records carry available_second so an outcome is not revealed before its final linked action.
- Static analysis files are generated at input-change boundaries; the browser loads the relevant file and suspends sensitive panels while switching. No new evidence exists between those boundaries. The replay second and latest analytical input time can therefore differ slightly.
- Penalty-area touches require both pitch dimensions (16.5m length, 40.32m width), valid coordinates and attacking direction. Successful tagged dribbles normalize won/complete outcomes; they are not labeled progressive carries.
- Current sprint counts and integrated high-speed distances are unavailable from minute samples. The UI uses high_speed_samples and maximum sampled speed. Historical physical aggregates remain explicitly invented records; they are not inferred from the sparse current stream.
- paired_spacing reports widened/stable sampled geometry, without asserting a coaching assignment. high_speed_sample_change_pct is a complete-window sample comparison, not a fatigue score.
- Player table, chat and historical files use one canonical appearance ledger. Per-shot xG and pass-completion rates expose their denominators; raw tagged totals and full-appearance averages are labeled as different coverage.
- LLMs emit qualitative lead text and allowlisted fact IDs. Application code inserts canonical fact labels and values verbatim. A reviewer can reject the assembled result. This protects numerical facts; qualitative truth still needs live evaluation.
