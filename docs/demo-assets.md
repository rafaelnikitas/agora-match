# Updated demo assets and production notes

The current walkthrough is **114.021 seconds (1:54)**, **1920×1080**, 5 fps, H.264 video with AAC narration. It was captured from the public Azure application on **27 October 2026**. English subtitles are burned into the video; a separate WebVTT caption track is provided.

- [YouTube demonstration](https://youtu.be/nxC-Q8esbOQ)
- [Alternate player](https://agoramatch.russettitan64.chatgpt.site/showcase)
- [Download the MP4](https://agoramatch.russettitan64.chatgpt.site/media/agora-match-azure-demo.mp4)
- [Caption transcript](demo-transcript.vtt)
- [Storyboard and narration](demo-script.md)

## Authentic capture and AI execution

App panels are genuine screenshots from the functioning Azure app, cropped and edited for readability. The ball replay uses successive captured frames. This is an edited screen-capture walkthrough. Presentation headings, callouts, and the acceptance-results card are editorial graphics.

The recording includes freshly requested Foundry answers in Fan, Analyst, and Coach views and actual stage timings visible in the app. The trace shown in the fan segment reports match analyst 1,288ms, narrator 1,068ms, and reviewer 374ms. The analyst example opens tagged fullback/winger cases; the coach example reviews Noah Reed’s paired gap of 8m at 55′ and 23m at 70′. The commentary was also generated in the live app. The Speak control is shown; browser speech is not mixed into the soundtrack.

The Azure runtime source remains `30990917600ac7f02029596743892bd4f5d78a61`. Microsoft Foundry provides GPT-OSS-120B to three specialist roles through custom Python orchestration. The code preserves canonical facts and supports one bounded correction before fallback. The video’s 21-case results come from the retained [live acceptance report](azure-live-verification.md); that fixed development suite does not establish semantic accuracy. Human quality review remains pending.

All match data and history are synthetic. Player positions are minute-sampled; the second-by-second ball path is illustrative interpolation constrained by event locations. The player rating is a transparent demo score. Coach cues do not diagnose fatigue or establish marking responsibility.

## Production credits

Narration, script, and editorial graphics were created for Agora Match. Voice synthesis uses [Piper](https://github.com/OHF-Voice/piper1-gpl), version 1.3.0, and [en_US-ljspeech-high](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/high/MODEL_CARD). The model card identifies the [LJ Speech](https://keithito.com/LJ-Speech-Dataset/) source dataset as public domain. The model repository supplies its own license. Voice weights and the Piper runtime are not distributed in the application. No music, match broadcasts, real player images, or club badges are included.

## Release identity

- Video: `agora-match-azure-demo.mp4`
- SHA-256: `3fd6192aefd3ffd3cdaf62ee0bb56fefcb42f99882f06698015032baf9dbb63e`
- Size: 7,680,606 bytes
- Runtime: 114.021333 seconds
- Chapters and narration: [demo-storyboard.json](demo-storyboard.json)

Large media files are hosted on the public demo site, rather than committed to the GitHub source repository. The viewer references those hosted assets. The entrant reports completing YouTube publication. Use the YouTube URL in the submission, and perform a final signed-out playback check. The self-hosted player remains an alternate review copy.
