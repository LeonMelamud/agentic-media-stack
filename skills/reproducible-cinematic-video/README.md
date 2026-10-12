# Reproducible Cinematic Video Skill

A reusable agent skill for re-delivering an **approved source movie** without changing its timing or soundtrack.

## What it does

**Mode A - Generative hybrid** (distilled from the supplied **Three.js × fal** production concept). It preserves an approved source film's:

- shot structure and cut timing
- camera choreography
- geometry/silhouettes/openings
- typography and logo pixels
- soundtrack and word timing

while selectively introducing photorealistic generated appearances with fal image/video models.

**Mode B - Social delivery** (fully local: FFmpeg + Pillow/RAQM + faster-whisper). It turns approved footage into a platform deliverable:

- Instagram Reels/Stories (9:16), feed 4:5, square, Shorts, TikTok, 16:9 presets, plus Facebook, LinkedIn and X aliases and a "which file for which platform" table
- reframe with a crop anchor (left/center/right, top/center/bottom), punch-in zoom, keyframed pans
- per-segment-language transcription (handles Hebrew speech that reads English slides)
- burned-in captions, including correct right-to-left Hebrew/Arabic, without needing libass
- platform-safe H.264 encode with source audio copied, an SRT sidecar, a cover frame and automatic validation
- optional designed polish through HyperFrames: karaoke captions, hook, brand tag, punch-ins, grade and a closing question, from one config, in 9:16 and 4:5 at once

## Included

```text
SKILL.md
references/
  workflow-notes.md
  example-timeline.md
  appearance-briefs.md
  social-delivery.md        # Mode B: presets, platform table, safe zones, reframe math, RTL captions
  hyperframes-polish.md     # B6: reel template, captions.json/reel.json, layouts, recipes
  examples/                 # steady screen recipe as used once (worked examples, not tools)
templates/
  shot-manifest.json
  job-record.json
  delivery-manifest.json    # Mode B manifest
  hyperframes-reel/         # build_reel.py + reel.example.json
scripts/
  transcribe.py             # pip install faster-whisper
  social_render.py          # cues | render | validate
  captions_from_cues.py     # word-timed captions.json for karaoke
  check_delivery.py         # verify any final MP4 against its source
assets/fonts/
  Heebo[wght].ttf, OFL.txt  # OFL Hebrew+Latin font
```

## Mode B quick start

```bash
cp templates/delivery-manifest.json work/delivery.json   # set source, name, preset
python -I scripts/social_render.py preview work/delivery.json --times 3,10,20 --zooms 1.0,1.15,1.3
python -I scripts/transcribe.py source.mp4 work/transcript.json --language he
python -I scripts/social_render.py cues work/transcript.json work/cues.json --caption-language he
# edit work/cues.json: translate [TRANSLATE] cues, check [REVIEW] cues
python -I scripts/social_render.py render work/delivery.json
```

Designed version (HyperFrames, see `references/hyperframes-polish.md`):

```bash
python -I scripts/captions_from_cues.py work/cues.json work/transcript.json <project>/prep/captions.json
python3 -I <project>/prep/build_reel.py <project>/prep/reel.json reel       # 9:16
python3 -I <project>/prep/build_reel.py <project>/prep/reel.json feed-4x5   # 4:5 sibling project
python -I scripts/check_delivery.py <render>.mp4 --source source.mp4 --size 1080x1920
```

## Changes

- **v3 (2026-10-11):**
  - Facebook, LinkedIn and X presets, and a platform routing table.
  - Config-driven HyperFrames reel template with 9:16 and 4:5 layouts, plus an SRT sidecar. It is pixel-identical to a hand-built project at sampled frames (0.9-29.5 s; the brand dot's pulse count now follows the clip length).
  - `captions_from_cues.py` and `check_delivery.py`.
  - B6 corrected: mount native footage as a card; a clean base only when cropping.
  - Recipes for emoji captions, steady screen replacement and the BT.709 round trip.
- **v2 (2026-10-10):** Mode B social delivery, per-span language transcription, RTL captions without libass.

## Key design choice

Mode A is intentionally a **thin specialized layer** rather than a copy of a general fal integration skill. It focuses on the part that is unique to the supplied concept: reproducible shot preservation, guide extraction, geometry-locked appearance generation, local retiming, typography masking, audio preservation, resumability, and validation. It can be combined with a general fal/GenMedia skill that handles model discovery and provider-specific API details.

Mode B keeps the same authority rule (the source owns timing and sound) and moves every creative decision (ratio, crop, captions) into a manifest, so a re-cut is a one-field edit plus a rerun.

## Important

The example timeline, appearance prompts, endpoint examples, and 4K60 output settings are derived from one specific production. Use them as reference templates, not assumptions for every project. Platform specs and safe zones in `social-delivery.md` change over time; re-check them before a campaign.
