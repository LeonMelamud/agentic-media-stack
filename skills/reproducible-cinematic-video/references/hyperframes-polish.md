# HyperFrames polish (Mode B, step B6)

How to turn approved footage into a designed Reel: karaoke captions, a hook title, a brand tag, punch-ins, a grade and a closing call-to-action. It renders as one master plus one sibling project per extra aspect ratio, all from the same `captions.json`. The HyperFrames skills own composition rules. This file holds what is specific to this pipeline and what was learned delivering it.

## Fast path

```bash
# 0. HyperFrames project for the master (9:16), per the hyperframes skill (route general-video)
npx hyperframes init "<project>" --non-interactive --example=blank --skill=general-video
#    copy into <project>/assets/: the footage, a low-res copy for the backdrop (540x960, no audio),
#    the last frame as hold.png and bg-hold.png (for a CTA hold), and the fonts

# 1. transcript + editable cues (B3, B4)
python -I SKILL/scripts/transcribe.py SOURCE.mp4 work/transcript.json --language he
python -I SKILL/scripts/social_render.py cues work/transcript.json work/cues.json --caption-language he
#    edit work/cues.json (fix ASR, on-screen text beats ASR, translate or keep English spans)

# 2. word-timed captions for the karaoke highlight
python -I SKILL/scripts/captions_from_cues.py work/cues.json work/transcript.json <project>/prep/captions.json
#    it lists hand-edited words it had to time by character length; check those against the audio

# 3. build: copy the template once, write reel.json (hook, tag, CTA, punch-ins, grades, layouts)
cp SKILL/templates/hyperframes-reel/build_reel.py <project>/prep/
cp SKILL/templates/hyperframes-reel/reel.example.json <project>/prep/reel.json
python3 -I prep/build_reel.py prep/reel.json reel        # 9:16 master, in this project
python3 -I prep/build_reel.py prep/reel.json feed-4x5    # 4:5 sibling project, scaffolded on first run
npx hyperframes check            # in each project
npx hyperframes snapshot . --at 1,5,12,20 --no-end --describe false   # look at the frames

# 4. render and verify each ratio (--extra = seconds of held end frame; --cover writes <name>-cover.jpg)
npx hyperframes render . --fps 30 --quality delivery --video-frame-format png -o renders/<name>.mp4
python -I SKILL/scripts/check_delivery.py renders/<name>.mp4 --source SOURCE.mp4 --size 1080x1920 --fps 30 \
    --extra 1.5 --frames 1.6,12,30 --cover 1.6
```

- Each build also writes `captions.srt` in the project root. Deliver it as `<name>.srt` only with an uncaptioned cut: these captions are burned in.
- `reel.example.json` is this pipeline's first reel. Replace its texts, punch-in times and media. Add `opening_push` only together with a steady screen cut, because its release is a visible jump without a cut. Add `caption_groups` only to name the slices; the default (6 cues each) fits any count.
- After step 2, `captions.json` is the master. Edit it by hand (word fixes, timing, emoji). The converter refuses to overwrite it without `--force`.
- Rebuild **and re-render** every layout after a caption change. Each project bakes the captions into its HTML.
- A reel that was hand-built before this template: write a `reel.json` from its values (hook lines, tag, CTA, punch-ins, grades, card geometry). Diff snapshots against the old project before switching; this template reproduced such a project pixel-identically at every sampled frame.

## `captions.json`

```json
[{"start": 26.18, "end": 27.55, "lang": "he",
  "words": [{"t": "ואני", "s": 26.18, "e": 26.69}, {"t": "אהיה", "s": 26.7, "e": 26.93},
            {"t": "😂", "s": 26.94, "e": 27.3, "emoji": "assets/emoji/emoji_u1f602.svg"}]}]
```

- Times are seconds on the source timeline.
- `lang` sets the direction: he, ar, fa, ur and yi are RTL. RTL captions use 62 px, LTR captions 56 px.
- A word with `"emoji"` renders as that image. It pops in at `s` with a short shake.
- Words in `brand_words` stay coral after they are spoken.
- One cue is 1-2 lines. Lines are balanced with the real font through Pillow RAQM, so no orphan words.

## `reel.json`

See `templates/hyperframes-reel/reel.example.json`. Keys:

| Key | Meaning |
| --- | --- |
| `media.base`, `media.bg` | footage (with audio) and the low-res backdrop copy. Keep them as separate files: the same file twice trips duplicate-media lint |
| `media.hold`, `media.bg_hold`, `hold` | last frame held for `hold` seconds after `video_duration`, so the CTA can be read |
| `fonts.sans`, `fonts.serif` | captions/tag, hook/CTA. CSS uses each file's real family name, because `check` measures text by family name |
| `hook` | `lines` (`*word*` = accent colour), `start`, `duration`. Sits in the top band and moves vertically only |
| `chip` | `label` + `brand`. Fades in after the hook, never slides |
| `cta` | closing `lines`, `start`, `dim_exposure` (the card dims under it) |
| `cam_origin`, `punch_ins` | `{t, scale, dur, ease, note}`. `{t, origin}` moves the zoom origin; only move it while scale is 1 |
| `opening_push` | `{until, origin, scale}`: slow push released by a cut (see steady screen below) |
| `grades` | selector → `media-treatment` grading JSON, persisted into `index.html` |
| `caption_groups` | `[name, from, to]` slices. The default is 6 cues per sub-composition, which keeps Studio caption tracks lint-clean |
| `layouts` | `reel`, `feed-4x5` or any name with `base` + overrides; `out` = sibling project folder |

## Layouts

| Layout | Canvas | Card (9:16 source) | Bands |
| --- | --- | --- | --- |
| `reel` | 1080x1920 | 810x1440 at (135, 380), native size for 810-wide phone exports | hook top 132, tag 226, captions 1150, CTA 860 |
| `feed-4x5` | 1080x1350 | 624x1109 at (228, 197), 0.77 | hook top 26 (64 px), tag 72, captions 905, CTA 533 |

- The card always shows the whole frame and is never upscaled. Its w/h keep the source aspect, and its width is at most the source width.
- For a 1080x1920 source, the `reel` card is 0.75 of native and shows the blurred backdrop, which is the zoomed-out look.
- In `feed-4x5` a two-line hook (about 219 px) overlaps the card top by about 45 px. That was fine here, because the card's top showed wall and a camera mount during the hook. If the subject's head or a screen sits in the top ~6% of the card at that moment, set `"hook_font": 54` in that layout, or use a one-line hook.
- Captions keep 740 px pills and the same line breaks in every layout. In 4:5 a pill may overlap the card edge, which reads fine.
- A new ratio is a new `layouts` entry. Look at snapshots before rendering.
- 1:1 and 16:9 have not been tuned yet.

## What this user approved (defaults)

- **Zoom out, don't crop:** show the whole frame at native size on a blurred, darkened copy of itself. Cropping plus upscaling read as a quality drop and hid the second screen.
- **No sideways motion in the opening:** titles rise or fade, they never slide in from the side. Camera swings between screens are the bigger problem: see the steady screen recipe below.
- **Hook in the top band:** never over the subject or the screens.
- **Captions per spoken language:** English captions for English speech, Hebrew for Hebrew, karaoke-highlighted, never an auto-translated mix.
- **Laughter becomes an emoji:** ASR often writes a filler word ("זה.") where the room laughs.
  - Suspects: a short, out-of-context word at a cue end, often low-probability (`p` < 0.8 in `transcript.json`), followed by a pause.
  - Confirm with the user, since only they heard the room.
  - Replace the word with 😂: take the word's `s`, end it just before the next cue (about 0.1 s gap), and extend the cue `end` to match.
- **Closing CTA:** a question in large serif type, over the dimmed final frame, held 1.5 s.

## Lessons (HyperFrames)

- Keep the word gap at least 0.34em. Above about 1.06x lift, neighbouring highlighted words touch.
- Every caption cue needs a hard kill after its exit tween (`tl.set(... visibility: "hidden")`), and caption hosts need `data-track-kind="captions"`.
- `check` warns about caption-pill contrast at the moment a pill pops in (t is about 2 s here). The pill is mid-fade at that instant, so the warning is expected. A contrast warning on a fully visible pill is real.
- `container_overflow #cam inside #card` (info) is the intended punch-in.
- Grades go through `npx hyperframes media-treatment ... --apply`, which writes into `index.html`. Every rebuild regenerates `index.html`, so re-apply the grades each time (`build_reel.py` does).
- Render with `--video-frame-format png` for footage with text or screens.

## Recipe: emoji in captions

Use Noto Color Emoji SVGs, pinned by tag: `https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@v2.047/svg/emoji_u<codepoint>.svg` (😂 is `1f602`). Save the file in the HyperFrames project's assets folder (e.g. `<project>/assets/emoji/`) with the repo's license, and set `"emoji"` on the word. An embedded image renders the same in every renderer. A system emoji font depends on the machine.

## Recipe: steady screen replacement

**When:** the phone swings between screens (a TV playing a promo, slides), and the user has the media that was on the screen. This beats stabilisation: stabilising a whip-pan only blurs and crops it. Search the user's files for the promo or deck (recent videos, matching duration), and ask if it isn't found.

**Without the media:** you cannot invent the screen. Offer instead:
- the longest steady stretch held with a slow push (the content plays, part of it is lost);
- cutting the swing out of the picture only, while the audio continues under a held frame or the hook card;
- leaving it as it is.

The timing and sound of the source stay untouched in every option.

**Which screen:** the one that is fully in frame in the sharpest frame, preferably the one the camera lands on at the cut, so the shot leads into the real footage. Also choose a plate frame with no people in it, because a frozen person reads as a freeze. If no such frame exists, cut earlier.

**Example files:** `references/examples/screen_align.example.py` and `steady_opening.example.py`. They are worked examples pinned to one clip, not tools.

1. **Plate:** take the sharpest frame where one screen is fully in view (variance of the Laplacian). The shot is locked off from frame 0 to a **cut frame** where the real camera has settled. The cut to real footage hides the change of shot.
   - To find the settle point: the mean absolute frame difference on 203x360 grey thumbnails falls from about 10-15 to about 1-2 and stays there.
   - `check_delivery.py --motion` on the source shows the same thing.
2. **Placement:** align promo frames to the screen in the plate with `cv2.findTransformECC(..., MOTION_HOMOGRAPHY)`.
   - Template = the footage, input = the promo, with the mask in promo coordinates. The mask must be the input's size.
   - Seed it with a rough quad.
   - The four promo corners through the result give sub-pixel screen corners.
   - Edge fitting on the bezel fails: the TV's side panel and low bezel contrast fool it.
   - A second, partly visible screen: extrapolate on the wall plane (translate in promo units), then snap the visible edge to the bezel.
3. **Timing:**
   - Find the promo frame shown in the plate by maximising ECC over a window, and cross-check on a second frame.
   - In a room, the TV picture can lead the sound (0.5 s here).
   - **Play the replaced screen locked to the audio** (audio cross-correlation offset), so on-screen text lands with the voice and captions. The picture offset is only for fitting against the plate.
4. **Look:**
   - Denoise the promo (`fastNlMeansDenoisingColored` 5/5/7/21), because the phone smoothed its grain away.
   - Colour by **per-channel quantile matching** over the aligned screen. Least squares flattens contrast and saturation, and a free polynomial bends below black and inverts grain.
   - Add a smooth additive reflection layer: a 2D quadratic of the plate-vs-mapped residual.
   - Blur by sigma 0.9 px to match the optics. Add at most 0.3 luma grain.
   - The promo plays at its own rate: show frame `floor((t + offset) * promo_fps)` at each output frame, as the TV did.
5. **Colour round trip:**
   - ffmpeg's default yuv420p → RGB decode came out about 2 levels darker than its encode, so the opening would not match the rest.
   - Decode raw `yuv420p` and convert with exact BT.709 limited-range maths in numpy. Convert back the same way and pipe raw yuv420p to x264.
   - Concatenate with the untouched remainder in one ffmpeg graph (`trim=start_frame=CUT`), and stream-copy the audio.
   - Encode with x264 `-preset slow -crf 10 -pix_fmt yuv420p`, BT.709 tags and `+faststart`, at the source frame rate.
   - Rebuild the low-res backdrop copy from the new file.
6. **Verify:** `check_delivery.py --motion 0-CUT_S`. Steady is about 0.1 px/frame (the swinging original measured 3.5).

Every corner, offset and frame index in the examples must be re-derived for new footage.
