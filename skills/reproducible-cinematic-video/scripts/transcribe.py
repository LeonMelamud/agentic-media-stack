#!/usr/bin/env python3
"""Transcribe a source movie with per-segment language detection.

Speakers code-switch (e.g. Hebrew talk that reads English slide titles). Forcing
one language garbles the other span, so this script:
  1. runs a VAD-segmented pass in the primary language with word timestamps,
  2. re-detects the language of every segment on its own audio with a GENERAL
     multilingual model (language fine-tunes such as ivrit-ai always report their
     own language with p=1.0, so they cannot be used for detection),
  3. re-transcribes segments whose detected language differs from the primary,
  4. flags segments where most words are low-confidence (`suspect`), which is the
     usual symptom of a wrong-language pass.

Output: transcript.json = {"source", "primary_language", "model", "segments": [
  {"start", "end", "language", "language_probability", "text", "low_confidence",
   "words": [{"w", "s", "e", "p"}]}]}

Requires: ffmpeg on PATH, `pip install faster-whisper`.
Hebrew default model: ivrit-ai/whisper-large-v3-turbo-ct2 (Hebrew fine-tune).

Usage:
  python transcribe.py SOURCE.mp4 OUT/transcript.json --language he
  python transcribe.py SOURCE.mp4 OUT/transcript.json --language ar --model large-v3
  # detection missed a switch (segment straddles it): force a span, edges at pauses
  python transcribe.py SOURCE.mp4 OUT/transcript.json --language he --span 0-6.6:en
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

DEFAULT_MODELS = {"he": "ivrit-ai/whisper-large-v3-turbo-ct2"}
LOW_CONFIDENCE = 0.80
SWITCH_CONFIDENCE = 0.60  # detector must be at least this sure before a span is treated as foreign


def extract_wav(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1",
                    "-ar", "16000", str(dst)], check=True)


def words_of(seg, offset=0.0):
    # Keep Whisper's leading spaces: sub-word tokens ("e", "-mail") must be joined with "".
    return [{"w": w.word, "s": round(w.start + offset, 3), "e": round(w.end + offset, 3),
             "p": round(w.probability, 3)} for w in (seg.words or [])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("out")
    ap.add_argument("--language", required=True, help="primary spoken language, e.g. he")
    ap.add_argument("--model", help="faster-whisper model id (default per language)")
    ap.add_argument("--detect-model", default="small",
                    help="general multilingual model used only for per-segment language ID")
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--span", action="append", default=[], metavar="START-END:LANG",
                    help="force a time span to a language (repeatable); replaces segments centred in it")
    args = ap.parse_args()

    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio

    model_id = args.model or DEFAULT_MODELS.get(args.language, "large-v3")
    model = WhisperModel(model_id, device="cpu", compute_type=args.compute_type)
    detector = WhisperModel(args.detect_model, device="cpu", compute_type=args.compute_type)

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio16k.wav"
        extract_wav(args.source, wav)
        audio = decode_audio(str(wav), sampling_rate=16000)
        segs, _ = model.transcribe(str(wav), language=args.language, word_timestamps=True,
                                   vad_filter=True, beam_size=5)
        segs = list(segs)

        out = []
        for seg in segs:
            a, b = int(seg.start * 16000), int(seg.end * 16000)
            clip = audio[a:b]
            detected, prob = args.language, 1.0
            if len(clip) > 16000 * 0.5:
                detected, prob, _ = detector.detect_language(clip)
            lang = detected if prob >= SWITCH_CONFIDENCE else args.language
            entry = {"start": round(seg.start, 3), "end": round(seg.end, 3), "language": lang,
                     "detected_language": detected, "language_probability": round(prob, 3),
                     "text": seg.text.strip(), "words": words_of(seg)}
            if lang != args.language:
                # Re-transcribe the foreign span in its own language.
                sub, _ = model.transcribe(clip, language=lang, word_timestamps=True, beam_size=5,
                                          condition_on_previous_text=False)
                sub = list(sub)
                entry["text"] = " ".join(x.text.strip() for x in sub)
                entry["words"] = [w for s in sub for w in words_of(s, offset=seg.start)]
            entry["low_confidence"] = [w["w"].strip() for w in entry["words"] if w["p"] < LOW_CONFIDENCE]
            entry["suspect"] = len(entry["low_confidence"]) > 0.5 * max(1, len(entry["words"]))
            out.append(entry)

        for spec in args.span:
            times, lang = spec.rsplit(":", 1)
            a, b = (float(x) for x in times.split("-"))
            out = [e for e in out if not a <= (e["start"] + e["end"]) / 2 <= b]
            sub, _ = model.transcribe(audio[int(a * 16000):int(b * 16000)], language=lang, word_timestamps=True,
                                      beam_size=5, condition_on_previous_text=False)
            for x in sub:
                words = words_of(x, offset=a)
                low = [w["w"].strip() for w in words if w["p"] < LOW_CONFIDENCE]
                out.append({"start": round(x.start + a, 3), "end": round(x.end + a, 3), "language": lang,
                            "detected_language": "forced", "language_probability": 1.0,
                            "text": x.text.strip(), "words": words, "low_confidence": low,
                            "suspect": len(low) > 0.5 * max(1, len(words))})
        out.sort(key=lambda e: e["start"])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"source": str(args.source), "primary_language": args.language,
                                          "model": model_id, "segments": out},
                                         ensure_ascii=False, indent=1))
    for e in out:
        flag = "  <-- SUSPECT (mostly low confidence)" if e["suspect"] else (
            f"  <-- check: {' '.join(e['low_confidence'])}" if e["low_confidence"] else "")
        print(f"[{e['start']:6.2f}-{e['end']:6.2f}] ({e['language']}; detector {e['detected_language']} "
              f"{e['language_probability']:.2f}) {e['text']}{flag}")


if __name__ == "__main__":
    main()
