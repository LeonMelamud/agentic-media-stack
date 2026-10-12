# Social delivery reference (Mode B)

Reference material for `scripts/social_render.py` and `scripts/transcribe.py`. Platform specs change; re-check them before a campaign launch.

## Platform presets

| `preset` | Canvas | Use | Caption band centre (`y_center`) |
| --- | --- | --- | --- |
| `ig-reels` | 1080x1920 (9:16) | Instagram Reels; all IG video posts are Reels | 0.66 |
| `ig-story` | 1080x1920 (9:16) | Instagram Stories | 0.66 |
| `ig-feed-4x5` | 1080x1350 (4:5) | Feed-first video, carousel video | 0.80 |
| `ig-square` | 1080x1080 (1:1) | Square feed / ads | 0.80 |
| `yt-shorts` | 1080x1920 (9:16) | YouTube Shorts | 0.66 |
| `tiktok` | 1080x1920 (9:16) | TikTok | 0.64 |
| `landscape-16x9` | 1920x1080 | YouTube / LinkedIn landscape | 0.86 |

Platform aliases resolve to these canvases: `fb-reels`, `fb-story`, `fb-feed-4x5`, `linkedin-feed` (4:5), `linkedin-vertical`, `linkedin-landscape`, `x-vertical`, `x-square`, `x-landscape`. Any other size: omit `preset`, set `width` and `height`.

## Which file for which platform

Checked 2026-10-11 against vendor guides (postiz, postfa.st, sendshort, quso, shootsta, async, moda, heyorca, posteverywhere), not the platforms' own help pages. The guides disagree on every limit. Re-verify before a paid campaign, and tell the user which figures are uncertain.

**One 9:16 master serves most platforms. Make a 4:5 only for feeds that crop 9:16.**

| Platform / placement | Upload | Preset / reel layout | Notes |
| --- | --- | --- | --- |
| Instagram Reels, Stories | 9:16 master | `ig-reels` / `reel` | Keep the bottom ~20%, top ~10% and right ~12% clear (UI). |
| Facebook Reels (default for a vertical clip) | the same 9:16 file | `fb-reels` / `reel` | Organic overlay is close to Instagram's. As an ad, Meta advises keeping the top 14%, bottom 35% and sides 6% clear. Two-line captions in the `reel` layout end at y ≈ 0.69, so for an ad cut use `"cue_top": 1050` (pill bottom ≈ 0.64). |
| Facebook feed post | 4:5 | `fb-feed-4x5` / `feed-4x5` | Taller video is cropped to 4:5 in the feed. |
| LinkedIn feed | 4:5 | `linkedin-feed` / `feed-4x5` | 9:16 is cropped in the main feed and the top title band disappears; 4:5 shows whole. Most viewing is muted, so burned captions matter. Reported limits: 5 GB and 10-15 min for native posts, 200 MB for ads. |
| LinkedIn vertical video tab | the 9:16 master | `linkedin-vertical` / `reel` | |
| X | 9:16 master; 4:5 for a desktop-heavy audience | `x-vertical` / `reel`, or the 4:5 file | Supports 16:9, 1:1 and 9:16. The free tier allows 2:20 and 512 MB. Sources disagree on max resolution (1080x1920 vs 1920x1200); if needed X downscales, it does not crop. |
| YouTube Shorts, TikTok | 9:16 master | `yt-shorts`, `tiktok` / `reel` | |
| YouTube / LinkedIn landscape | 16:9 | `landscape-16x9` | The HyperFrames reel template has no tuned 16:9 layout yet. |

- **Captions:** when captions are burned in, do not upload the SRT, and turn off the platform's auto-captions (Facebook, LinkedIn). Otherwise viewers who switch CC on see two sets. Upload the SRT only with an uncaptioned cut.
- **Length:** reported limits are FB Reels 60 s, 90 s or unlimited (sources conflict; one cites a June 2025 change), LinkedIn 10-15 min, X free 2:20. Short pieces (under 60 s) clear all of them.
- **Deliverable names:** `<name>-reel.mp4` (9:16), `<name>-4x5.mp4`, each with its own `-cover.jpg`. The HyperFrames route builds both from one `captions.json` (`references/hyperframes-polish.md`).

Encode defaults: H.264 High, yuv420p, BT.709 tags, limited range, GOP 2 s, CRF 18, maxrate 12M, `+faststart`, audio stream copied. When `fps` is omitted, the source rate is kept up to 30 (25 stays 25, 29.97 stays 29.97) and 50/60 is halved to 25/30. Forcing 30 on a 25 fps source adds judder. Set `"fps": 60` only if the user asks for 60.

### 9:16 safe zones (Reels / Stories / Shorts / TikTok)

- Bottom ~20% (y > 0.80): username, caption text and audio row cover it. Keep captions and faces out of it.
- Top ~10%: progress bar, header.
- Right ~12%: like/comment/share icon column. Caption side margins default to 12% of width on 9:16 (6% otherwise), so centred captions clear it.
- The profile grid shows a centre crop (3:4 / 4:5) of a Reel. Keep the subject near the vertical centre if the grid thumbnail matters, and pick `cover_time` on a frame where face and screen are both visible.

## Reframe math

For source `W x H` and target aspect `a = tw/th`:

```text
base = largest a-aspect window inside the source (full height if W/H > a, else full width)
crop = base / zoom                                # zoom 1.0 = widest possible
x    = anchor_x * (W - crop_w)                    # left=0, center=0.5, right=1
y    = anchor_y * (H - crop_h)                    # top=0,  center=0.5, bottom=1
then scale to tw x th (lanczos)
```

- A source that already has the target aspect gets **no crop at zoom 1.0**. "Take the left side" then means `anchor_x: left` with `zoom` 1.15-1.3.
- `zoom` must be at least 1.0. Below 1 the crop would need pixels outside the frame, and the script refuses it.
- Upscale factor = `tw / crop_w`. Keep it at or below about 1.7. 810-wide phone exports are already 1.33x at zoom 1.0. A 1080p 16:9 source cropped to 9:16 is 1.78x even at zoom 1.0: acceptable for a talking head, soft for slides and text. Offer `blur-pad` or a 4K source.
- `preview --times ... --zooms ...` renders a source row plus one row per zoom into `review/preview.jpg`. Compare at several timestamps, because handheld footage pans.
- A moving subject needs keyframes (crop mode only: blur-pad ignores them, and `zoom` is not keyframed). They are linear between keys and held outside them:

```json
"reframe": {"zoom": 1.2, "anchor_y": "top",
            "keyframes": [{"t": 0, "anchor_x": 0.0}, {"t": 9.5, "anchor_x": 0.0}, {"t": 11.0, "anchor_x": 0.6}]}
```

  Hold, then move over 1-2 s. Fast moves read as camera shake. A camera that whips between two subjects is not a reframe problem: see the steady screen recipe in `references/hyperframes-polish.md`.

### `"fit": "blur-pad"`

The whole source frame is scaled to fit the canvas and laid over a blurred, slightly darkened fill of itself (`blur` sigma 40, `bg_brightness` -0.08, `pad_anchor_y` center). Nothing is cropped or stretched. Use it for 16:9 panels and slides with text near the edges, or whenever the crop would lose the subject or exceed about 1.7x. Captions then usually sit on the blurred band, which keeps them off faces.

## Transcription

- `transcribe.py` uses VAD segments, then a per-segment language check with a general model (`--detect-model small`), then re-transcribes foreign spans.
- Hebrew: `ivrit-ai/whisper-large-v3-turbo-ct2` (default for `--language he`) clearly beats stock large-v3-turbo. Stock mlx/whisper with forced `he` can loop ("תגיד את תגיד את ...") on English audio.
- Other languages default to `large-v3`. For Arabic, the ASR output is usually MSA-leaning even for dialect speech; tell the user and keep dialect words they correct.
- `--span START-END:LANG` (repeatable) forces a span when detection misses a switch inside one VAD segment. It replaces segments centred in the span, so put the span edges at pauses.
- Language fine-tunes always report their own language with p=1.0. Use them only for transcription.
- A detector result below 0.60 keeps the primary language. Short or noisy Hebrew segments often get labelled `ar` or `en` at p 0.3-0.45, which is noise.
- Segment edges are more reliable than word edges (word times drift ~0.2-0.3 s). `cues` snaps each segment's first and last cue to the segment edges.
- `suspect: true` (more than half the words below p 0.80) almost always means a wrong-language span or overlapping speech.

## Cue rules

- 1-2 lines, at most about 7 words, at least 0.8 s on screen. Gaps under 0.35 s are bridged so captions do not flicker.
- Break at punctuation first. Never end a cue on a short function word (את, של, ה-, a, the, of). The `cues` command moves it to the next cue.
- Line wrapping is balanced (most even line widths), not greedy.
- **Translated spans:** when the caption language differs from what was said (an English slide read aloud in a Hebrew talk), translate the cue, delete its `needs_translation` key and add a `note`. Tell the user which spans were translated, because some prefer the original language there. In that case keep the original text, set `"language"` on the cue for your own records, and render with `--allow-untranslated`.
- When the audio reads on-screen text (slides, a promo playing on a TV), read the frames: the visible text is a stronger source than ASR for clipped or blurred words.
- Keep the speaker's register (colloquial הזאתי, slang). Fix recognition errors only.
- Brand names: keep what was said (קלוד) unless the user wants Latin (Claude). Mixed scripts render correctly with RAQM. Avoid placing a Latin word next to digits ("Claude, 3"): bidi groups them into one LTR run.

## RTL captions without libass

Homebrew/static FFmpeg builds often lack `subtitles`, `ass` and `drawtext`. Check with `ffmpeg -filters | grep -E "subtitles|drawtext"`. The script does not depend on them:

1. Pillow with `ImageFont.Layout.RAQM`. `features.check('raqm')` must be True, because RAQM does the bidi reordering and shaping. Draw with `direction="rtl", language="he"`. Never reverse strings by hand or use python-bidi visual reordering on top of RAQM: that double-reverses.
2. Each cue becomes one transparent PNG band (`band_height` ≈ 16% of canvas). A `blank.png` fills gaps.
3. An ffconcat list with per-image `duration` gives one caption stream, resampled with `fps=` and overlaid once with `overlay=0:Y:eof_action=pass`. This scales to hundreds of cues, unlike N overlay inputs with `enable=between(...)`.
4. The SRT sidecar prefixes each RTL line with U+200F (RLM) so players keep RTL paragraph direction when a line starts with a Latin word.

Style defaults: Heebo ExtraBold (800) at 6.6% of canvas width, white, rounded black box at about 65% opacity. Phone footage of bright walls needs the box; a stroke alone is not enough. Override any key under `captions` in the manifest (`size`, `weight`, `font`, `box`, `box_rgba`, `color_rgba`, `stroke_width`, `y_center`, `side_margin`, `max_lines`).

Fonts: the bundled `assets/fonts/Heebo[wght].ttf` (OFL) covers Hebrew and Latin only. For Arabic, download an OFL Arabic font (Noto Naskh Arabic, Noto Kufi Arabic or Cairo, from github.com/google/fonts) next to the manifest and set `captions.font`. A relative `font` path resolves from the manifest folder first, then the skill folder.
- `weight` applies only to variable fonts with a `wght` axis. For a static font, pick the Bold/ExtraBold file itself.
- `render` checks glyph coverage before encoding and exits listing missing codepoints. Missing glyphs would otherwise render as boxes and still pass every encode check.
- Do not bundle OS fonts (Arial Hebrew, SF Hebrew) in a shared skill.

## Sharpen

`"video": {"sharpen": 0.3-0.8}` adds a luma-only `unsharp` after scaling. Use about 0.5 for soft phone footage or upscales of 1.4x and above. Skip it for screen recordings, where it rings around text. Use it for clean bases handed to HyperFrames (CRF 12), because the realtime grading shader has no sharpen control.

## Audio

- Default `"audio": {"mode": "copy"}`: the bitstream is identical to the source and validation checks it by MD5.
- `"aac"` re-encodes to 48 kHz/192k. `"loudnorm"` (`lufs`, default -14) normalises for platforms. Use either only when the user asks or the source is badly quiet (integrated loudness below -20 LUFS). Measure with `ffmpeg -i SRC -af ebur128 -f null -`.

## Validation (automatic in `render`, rerun with `validate`)

`dimensions`, `fps`, `pix_fmt_yuv420p`, `h264_high`, `duration_matches_source` (within 2 frames), `faststart_moov_before_mdat`, `full_decode_clean`, `audio_present`, and in copy mode `audio_bitstream_identical_to_source`. Then look at the contact sheet and at least three full-resolution frames from the encoded file. A Pillow preview is not evidence.

## Deliverables

```text
delivery/
  <name>.mp4            # upload this
  <name>.<lang>.srt     # editable caption text/timing (also for platforms that accept SRT)
  <name>-cover.jpg      # cover/thumbnail candidate, no captions
work/
  transcript.json  cues.json  delivery.json  review/{validation.json, contact-sheet.jpg, ffmpeg-command.txt}
```

To fix a caption, edit `cues.json` and rerun `render`. For another ratio, copy the manifest and give it a new `name` and `review_dir` (for example `<name>-4x5`). Rerunning with only `preset` changed overwrites the first file's MP4, SRT, cover and validation. A 9:16 source in a 16:9 `blur-pad` frame puts the blurred bands at the sides, so captions sit on the picture. Check that two-line captions fit `captions.band_height` (default 16% of the canvas height) and raise it if they are clipped.
