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

## Text rendering in ffmpeg

Hebrew inside ffmpeg filter layers requires bidirectional reordering. Without it, text renders reversed or with punctuation on the wrong side.

Use `python-bidi` to reorder strings before passing them to `drawtext` or ASS subtitle files. Verify a rendered still frame before committing to a full render — a single frame costs seconds, a full render costs minutes.

Mixed Hebrew and English in one line is the most common failure. Test that case explicitly.

## Typography

Do not fall back to a default sans-serif. Hebrew has poor coverage in most Latin-first families and the result looks broken to native readers.

| Role | Family |
| --- | --- |
| Body and UI | Rubik, Assistant |
| Display and headlines | Suez One |
| Heavy display in video | Rubik Black |

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
