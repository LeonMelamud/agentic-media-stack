---
name: generated-video-qa
description: >
  Use when generating video with AI models where a character speaks (native voice,
  lip-sync, talking mascot/presenter) — before presenting or assembling ANY clip that
  contains generated speech. Also use when a generated voice mispronounces a name or
  brand, invents gibberish audio, or when a character or prop drifts between shots
  or clips ("the wand became a drill").
---

# Generated Video QA

Generated speech and generated characters fail in ways you cannot see in a
thumbnail and often cannot hear on one casual listen. Validate mechanically.

## The QA loop — run on every clip with speech

1. **Transcribe locally, diff against the script.**
   ```bash
   pip install mlx-whisper   # Apple Silicon; use openai-whisper elsewhere
   ffmpeg -i clip.mp4 -ac 1 -ar 16000 a.wav
   python3 -c "import mlx_whisper; print(mlx_whisper.transcribe('a.wav',
     path_or_hf_repo='mlx-community/whisper-large-v3-turbo')['text'])"
   ```
   The ear misses what the transcript catches. Real catches: "Claude" rendered
   as "Claws"; "Hand Claude" rendered as "hand-clawed"; "decks" as "drecks".
2. **Extract and view frames** — mid-shot and the true last frame
   (`ffmpeg -sseof -0.1 -i clip.mp4 -frames:v 1 -update 1 last.png`). The last
   frame matters twice: it is the chain point for the next clip and the end-card
   source.
3. **Silence-map the audio** (`silencedetect`). Speech must fill the clip:
   line length ≈ clip seconds × 2.7 words. Any dead seconds → the model invents
   its own gibberish audio to fill them.

## Writing dialogue the voice can actually say

| Failure seen | Rule |
|---|---|
| "Claude" → "Claws" after adding "she pronounces X as…" | NEVER put pronunciation meta-instructions near dialogue — they bleed onto neighboring words. Fix the spelling inside the quote instead ("Co-Work") |
| "Hand Claude" → "hand-clawed" | No tongue-twisters; pick verbs that don't collide with names ("Give Claude") |
| "decks" → "drecks" | Clipped monosyllable finals mumble; end sentences on multi-syllable words ("presentations") |
| Chopped VO broke lip-sync | Never fix pacing with silenceremove/atempo on a lip-sync source — rewrite the line shorter and regenerate |

## Keeping the character consistent

- **Multishot in ONE generation beats chaining.** One call with multiple shot
  prompts keeps one voice and one character design. Chain by last-frame
  extraction only to continue an already-approved clip — max ONE hop, and pass
  the canonical character image as an extra reference (without it, a magic
  clicker became a power drill).
- **Models take shape words literally.** "Star-shaped bokeh" produced literal
  five-pointed stars everywhere. Name shapes precisely and add the negative:
  "a 12-ray starburst disc — NOT a five-pointed star".

## Assembly rules

- Text and logos are NEVER model-generated — render to transparent PNGs
  (Pillow; Homebrew ffmpeg has no drawtext) and overlay.
- End card = darkened last frame + logo glow (pad the logo canvas BEFORE
  Gaussian-blurring or the glow clips to a square).
- Version filenames (`final_*_V<N>.mp4`), never overwrite; two-pass loudnorm
  I=-14:TP=-1.

Ship only after the transcript diff is clean and the frames pass. One reroll of
a single shot is always cheaper than discovering the flaw after assembly.
