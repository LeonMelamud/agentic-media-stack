---
name: hebrew-media-rules
description: >
  Production rules for Hebrew, Arabic, and other RTL content in video and web output. Use whenever
  the content language is Hebrew or RTL and the task involves captions, subtitles, transcription,
  a landing page, a deck, or any rendered video. Trigger phrases include "עברית", "כתוביות בעברית",
  "RTL", "אתר בעברית", "תמלול בעברית", "Hebrew captions", "Hebrew subtitles", "right to left".
  Read this before rendering, not after.
---

# Hebrew and RTL Media Rules

RTL failures surface at render time, not at author time. By then a full render cycle is wasted. Apply these before producing.

## Transcription

Word-level transcription quality in Hebrew is materially worse than in English across every engine, including ElevenLabs Scribe and Whisper. Never render burned captions from a raw Hebrew transcript.

For **AI-generated Hebrew speech** (native-voice video models, lip-sync), run the
`generated-video-qa` transcribe-and-diff loop first — `whisper-large-v3-turbo`
handles Hebrew — then apply the corrections pass below to the transcript before
trusting any word of it.

Required sequence:

1. Transcribe (Scribe for word-level timestamps and diarization, or faster-whisper `large-v3` locally)
2. Apply a corrections pass. The `video-edit` skill in ai-agents-skills ships `corrections-hebrew.md` — a dictionary of common Hebrew mistranscriptions. Use it.
3. **Present the transcript for human approval before rendering.** The `video-edit` skill provides an interactive browser transcript editor for exactly this. It runs a local model over WebGPU, so it works offline after first cache and no audio leaves the machine.
4. Only then render

Step 3 is not optional for Hebrew. Burned captions cannot be fixed after the render.

Local Whisper notes, verified on Hebrew talks:

- **Model:** `ivrit-ai/whisper-large-v3-turbo-ct2` (faster-whisper) clearly beats stock `large-v3` / turbo on Hebrew speech. Stock models forced to `he` can loop on English audio.
- **English inside Hebrew** (slides read aloud, a promo playing in the room): a single forced-language pass turns it into confident-looking garbage.
  - Detect the language per segment with a general multilingual model. A Hebrew fine-tune reports Hebrew at p=1.0 for everything, so never use it for language ID.
  - Re-transcribe the foreign spans in their own language. `reproducible-cinematic-video` → `scripts/transcribe.py` does this, with `--span` for a switch inside one segment.
- **Laughter and applause:** ASR inserts a short filler word at the end of a phrase where the room laughs ("זה."). Flag cue-final short words in the approval step. The user may prefer an emoji in its place.

## Text rendering in ffmpeg

Hebrew inside ffmpeg filter layers requires bidirectional reordering. Without it, text renders reversed or with punctuation on the wrong side.

Use `python-bidi` to reorder strings before passing them to `drawtext` or ASS subtitle files. Verify a rendered still frame before committing to a full render — a single frame costs seconds, a full render costs minutes.

Reorder only for a renderer that has no bidi of its own. Some renderers already reorder and shape: Pillow with RAQM (`features.check('raqm')`), browsers (HyperFrames compositions), and libass/drawtext builds with FriBidi. Given a pre-reordered string, they reverse it a second time. With Pillow, draw the logical string with `direction="rtl", language="he"`.

Static ffmpeg builds often have no `drawtext` or `subtitles` filter at all. Then render each caption as a PNG with Pillow RAQM and overlay it; `reproducible-cinematic-video` does this.

Mixed Hebrew and English in one line is the most common failure. Test that case explicitly.

## Typography

Do not fall back to a default sans-serif. Hebrew has poor coverage in most Latin-first families and the result looks broken to native readers.

| Role | Family |
| --- | --- |
| Body and UI | Rubik, Assistant |
| Display and headlines | Suez One |
| Heavy display in video | Rubik Black |

Also verified in rendered Reels, both OFL variable fonts: **Heebo** ExtraBold (800) for captions and **Frank Ruhl Libre** Black (900) for a serif title or closing line.

Confirm the font file actually contains Hebrew glyphs before rendering. Headless Chrome silently substitutes a fallback and produces tofu boxes or Latin-shaped Hebrew.

## RTL layout — what must mirror

When a page or composition flips to RTL, mirror all of these. Missing one is the usual cause of a layout that feels subtly wrong:

- Hero panel side
- Cursor-hint and scroll-hint side
- Scroll-to-top button position
- Arrow and chevron direction
- Progress bar fill direction
- Caption alignment
- Timeline scrub direction, if the UI exposes one

Numbers, code, and Latin brand names stay LTR inside RTL text. Do not mirror them.

## Video composition specifics

- Captions align right by default in Hebrew
- Karaoke-style caption scaling uses ASS override tags; verify the reordered string survives the tag insertion
- HTML karaoke (HyperFrames):
  - Use one span per word inside a `dir="rtl"` line, with no reordering.
  - Balance line breaks by measuring each word with the real font (Pillow RAQM) instead of relying on flex-wrap, which leaves orphans.
  - Keep the word gap at least 0.34em, so a lifted highlighted word does not touch its neighbours.
- Centered caption pills are the norm for social video. Right alignment applies to left-anchored caption blocks.
- Never cover the speaker's face with a caption card — this holds in every language, and Hebrew cards run wider for the same word count, so the risk is higher

## Verification before declaring done

Render a still frame and check each of these before a full render:

1. Hebrew text reads in the correct direction
2. Punctuation sits on the correct side
3. Mixed Hebrew and Latin in one line is correct
4. No tofu boxes or fallback glyphs
5. Captions do not cover the subject's face
6. Every mirrored element listed above actually flipped
7. Numbers remain LTR

Report which checks passed. Do not claim completion without running them.
