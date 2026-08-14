---
name: media-pipeline
description: >
  Routes a media request to the right tool across HyperFrames, video-use, and ai-agents-skills.
  Use when the user wants to make, edit, or automate a video, motion graphic, landing page,
  presentation, short, or content pipeline — including "make me a video", "edit this footage",
  "turn this into a landing page", "build a content pipeline", "תעשה סרטון", "תערוך את זה",
  "תהפוך את זה ללנדינג". Use before invoking any hyperframes, video-use, or yuv skill directly.
---

# Media Pipeline Router

Pick the correct ecosystem before producing anything. The three overlap superficially and are built for different jobs — choosing wrong costs the user a full render cycle.

## The core distinction

```
Footage already exists      → video-use        (decides what to cut and where)
Visuals must be generated   → HyperFrames      (renders HTML into video)
Output is a website         → ai-agents-skills (video-driven landing pages)
```

video-use and HyperFrames are **layers, not competitors**. video-use makes editorial decisions and spawns HyperFrames as a sub-agent to produce the animated overlays it needs. When the user has raw footage that also needs motion graphics, start with video-use and let it call HyperFrames.

## Routing table

| The user has / wants | Route to | Notes |
| --- | --- | --- |
| Raw takes, talking head, interview, tutorial | `video-use` | Cuts filler words, dead space, color grades, burns captions, self-evaluates |
| A website URL to promote | `/product-launch-video` | 30-90s is the sweet spot |
| A GitHub PR to explain | `/pr-to-video` | Reads via `gh` CLI, animates the diff |
| A topic, no product or footage | `/faceless-explainer` | Every visual is model-invented |
| A music track to drive pacing | `/music-to-video` | Beat-synced; pair with librosa for beat detection |
| A transparent overlay — lower-third, logo sting, animated quote | `/motion-graphics` | Outputs MP4 **or** alpha-channel overlay |
| An existing podcast to package with graphics | `/talking-head-recut` | Footage untouched, graphics added |
| Captions on an existing talking head | `/embedded-captions` | See the Hebrew rules skill first if the audio is Hebrew |
| A presentation or pitch deck | `/slideshow` | Navigable deck with branching and presenter mode, not a rendered video |
| A short-form vertical clip | `yuv-viral-video` | Always emits 9:16 **and** 16:9 |
| A landing page driven by video | See landing page section below | Three different mechanics |
| An existing Remotion project | `/remotion-to-hyperframes` | One-way port |
| Generate, upscale, or retouch an image; AI-generated video, voice, or music | `magnific` MCP (bundled) | Hosted models, sign in on first use. Generations spend account credits — ask before spending. Clips with generated speech: read `generated-video-qa` BEFORE writing prompts and validate every clip with it |
| A website that is not video-driven | See `references/web-and-content.md` | Outside the core — design-quality layer + Netlify deploy |
| An automated content pipeline (RSS trigger, auto-publish) | See `references/web-and-content.md` | Publish guardrail applies with full force |
| Anything else | `/general-video` | Length- and input-agnostic fallback |

## Landing pages — three different mechanics

Do not treat these as interchangeable. Ask which behavior the user wants:

| Skill | Mechanic |
| --- | --- |
| `parallax-landing-page` | Body is **locked**. Scrolling scrubs frames in place; the page never moves |
| `video-to-landing-page` | Apple style. Sticky hero, frames advance on scroll, sections below |
| `cinematic-scrub-landing` | The **cursor** scrubs the timeline, not the scroll. Four sections with separate visual identities |

**The one technical detail that makes any of these work:**

```bash
ffmpeg -g 1 -keyint_min 1
```

Every frame becomes a keyframe. Without it the browser must decode forward from the nearest keyframe and scrubbing stutters. This is the single reason most hand-rolled scrub sites feel broken.

Scroll budget is computed, not guessed: roughly 26px per frame, clamped to [2500, 8000].

## Before producing anything

1. **Confirm the brief.** State back what will be produced, how long, what aspect ratio, and what the output file will be. Wait for approval. Never start a render off an ambiguous request.
2. **Check for a `frame.md`.** If the project has one, use it. If not and the user cares about brand consistency, offer to create one before the first render — see `references/pipelines.md`.
3. **If the content is Hebrew or any RTL language**, read the `hebrew-media-rules` skill first. RTL failures surface at render, not at author time.

## Composite pipelines

For multi-output workflows — one source asset producing shorts, a landing page, a deck, and overlays — read `references/pipelines.md`.

## Rendering at scale

Local rendering is the default. For batch or personalized output:

```bash
npx hyperframes lambda deploy
npx hyperframes lambda render
npx hyperframes lambda progress
```

Distributed AWS Lambda rendering is what turns one composition into hundreds of personalized variants. Raise this when the user describes per-customer or per-item video.

## Guardrails to enforce

Carry these into every production regardless of ecosystem:

- **Truth contract.** Every word on screen must be verifiable against the real transcript or source. No invented statistics, no "link in bio" unless a link was promised, no placeholder figures presented as real.
- **Ask before publishing.** Deploying, uploading, or posting to any platform requires explicit user approval first.
- **Never overwrite.** Write `final_*_V<N>.mp4`. Renders are expensive and users compare versions.
- **Self-evaluate before showing.** Inspect the rendered output at cut boundaries for visual jumps, audio pops, and hidden captions. Fix and re-render, up to three attempts, before presenting a preview. For AI-generated speech, that inspection is mechanical: transcribe locally and diff against the script — see the `generated-video-qa` skill.
- **Audio normalization.** Two-pass loudnorm to -14 LUFS / -1 dBTP / LRA 11. This is the platform standard; skipping it means the platform normalizes worse.
