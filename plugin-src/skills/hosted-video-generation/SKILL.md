---
name: hosted-video-generation
description: >
  Use when generating video with a hosted model through the magnific MCP — "animate this image",
  "make a video from this poster", "turn this into a clip", "תעשה מזה סרטון", "תנפיש את התמונה".
  Also use when choosing between Seedance, FLUX 3, Veo and Kling, when a clip needs to preserve
  a finished image exactly, when directing motion that must stay smooth, or before spending
  credits on any video render.
---

# Hosted Video Generation

A video render costs one to two orders of magnitude more than an image — thousands of credits
against tens. Every decision below is about getting it right on the first render, because there
is no cheap retry.

## Cost discipline

**One video per request. Never batch variants.** Two images for review is good practice; two
videos is a large chunk of the plan balance spent before any feedback. Generate one, show it,
iterate on direction.

Before spending: `simulate_cost` for the exact figure, `account_balance` for what's left, then
state both to the user and wait. Never start a render off an ambiguous brief.

**`simulate_cost` takes FLAT arguments**, not the nested shape `video_generate` uses. Passing
`{video:{clips:[{slug,...}]}}` fails with "The api field is required when slug is not present"
even though the slug is right there. Pass the clip fields at the top level instead, using `api`
and `mode` from the model's `video_models_list` entry:

```
{ tool: "video_generate",
  arguments: { api: "bfl", mode: "standard", duration: 12,
               aspectRatio: "16:9", resolution: "1080p", prompt: "test" } }
```

Observed reference points (16:9, 1080p, exact): FLUX 3 10s ≈ 4,400 · FLUX 3 12s ≈ 5,280 ·
Seedance 2.0 10s ≈ 7,000. Dropping to 720p roughly halves it — use that for a look-test.

## Choosing the model

| Need | Model | Why |
| --- | --- | --- |
| One continuous flowing take, up to 20s | `bfl-flux-3` | Longest single take; start **and** end keyframes; no references, no multishot, no cameraMotion |
| Discrete directed shots, camera-move control | `bytedance-seedance-pro-2.0` | `multishot` up to 6 shots, 52 named `cameraMotion` values, rich reference types, native audio |
| Cheap iteration with the same controls | `bytedance-seedance-mini-2.0` | Best quality/price; 480p/720p |
| Native audio and lip sync | Seedance 2.0 (`references[].type:"audio"`) or Veo 3.1 | Note: **not** `audioUrl` for Seedance |
| Silent action, start/end frame control | `kling-25` | 5s or 10s only |

Never infer a slug from the product name — read it from `video_models_list`. "Flex 3" is
**FLUX 3** (`bfl-flux-3`), a video model, and is unrelated to `flux-2-flex`, an image model.

## Keyframes vs references

They are **mutually exclusive** on Seedance: any `keyframes.start` prohibits every visual
`references[]` entry, and vice versa. Two consequences worth knowing before you build the call:

- **To preserve a finished image exactly, use `keyframes.start`, not a reference.** Frame one then
  *is* the image, so faces and composition cannot drift. This is the correct choice when animating
  an approved poster or thumbnail.
- Seedance audio references need a *visual* reference in the same array, and a start frame does
  not satisfy that requirement — so "start frame + audio" is rejected. Pick one path.

Pass a creation `identifier` or asset URL. Never `webUrl`.

## Directing motion

"Make it impressive with no dead time" and "keep it smooth" pull against each other. Cuts are
what break smoothness, so the resolution is **one unbroken camera move whose action escalates**,
not a sequence of shots.

- State it explicitly: "one continuous unbroken take, no cuts, no jump cuts, no whip pans, no
  strobing, no camera shake, steady constant camera velocity."
- **Overlap the beats.** The next event begins while the previous is still running — a storm that
  builds in the background *during* the action never reads as a scene change. Sequential beats
  create the dead hand-off moments the user is objecting to.
- Give per-second timings (`0-2s:`, `2-4s:`) — long-form models follow them.
- Say environment changes happen "as a gradual flowing transition, never as a hard cut".
- Start the motion inside the first second. A held opening frame is the most common dead time.

For a still image being animated, keep the people almost motionless and let secondary
elements — animals, particles, light — carry the movement. Faces drift the moment they move.

## Audio arrives whether or not you ask

Seedance returned a populated AAC track on a clip generated with no `withSoundEffects`. Always
probe the output rather than assuming silence, and offer a stripped version when the user is
laying their own music:

```bash
ffmpeg -v error -i in.mp4 -af volumedetect -f null /dev/null 2>&1 | grep mean_volume
ffmpeg -i in.mp4 -c copy -an final_promo_V2.mp4
```

## Verify before showing

Never present a clip you have only received a URL for.

1. `ffprobe` the specs — expect `yuv420p`; **`yuv444p` stutters or refuses to play** in QuickTime,
   Safari and embedded PowerPoint. **Check the height too**: a "1080p" request can come back
   **1920×1088** (FLUX 3 pads to a multiple of 16), which editors and platforms reject or letterbox.
   Crop it back, then re-probe:

   ```bash
   ffmpeg -i in.mp4 -vf "crop=1920:1080:0:4" -c:v libx264 -crf 17 -pix_fmt yuv420p -c:a copy out.mp4
   ```
2. Decode test: `ffmpeg -v error -i out.mp4 -f null -` returns nothing.
3. Extract 6 evenly spaced frames into a contact sheet and **look at it** — check identity holds,
   subjects stay in frame, and no beat collapsed into stillness.
4. If a start frame was used, diff frame 0 against the source image to confirm the composition
   survived.
5. Never overwrite: write `final_*_V<N>.mp4`.

## Common mistakes

| Mistake | Reality |
| --- | --- |
| Generating two video variants to compare | One render, then iterate on direction. Images are the exempt case. |
| Nesting `simulate_cost` args like `video_generate` | It takes flat args; the error message misleadingly blames a missing `api`. |
| Passing a finished image as a reference to preserve it | Use `keyframes.start`. A reference lets the model redraw it. |
| Combining a Seedance start frame with references | Mutually exclusive; the call is rejected. |
| Asking for many shots to avoid dead time | Cuts are what feel abrupt. One escalating take with overlapping beats. |
| Assuming the clip is silent | Probe it. Models return audio unrequested. |
| Reporting a render from its URL | Probe and view it first. |
