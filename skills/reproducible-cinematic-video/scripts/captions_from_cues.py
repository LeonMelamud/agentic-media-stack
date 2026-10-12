#!/usr/bin/env python3
"""Word-timed captions (captions.json) from cue text + transcript word times.

Usage:
    python -I captions_from_cues.py work/cues.json work/transcript.json out/captions.json [--force]

Run it once to create captions.json. From then on captions.json is the master: edit it by hand (word fixes,
timing, emoji). Re-running this script overwrites those edits, so it refuses an existing output without --force.

cues        social_render.py cues.json ({"cues": [{start, end, text}]}) or a plain list of {start, end, text}.
transcript  transcribe.py transcript.json (segments[].words[] = {w, s, e, p}).

Each cue's tokens are aligned to the transcript words inside the cue window (difflib on normalised
tokens). Matched tokens take the word times. Tokens edited by hand (a corrected ASR word, slide text read
aloud, a translation) have no word to match. They get times by character length: within the span of the
transcript words they replace, else between their matched neighbours, else across the cue window.
Cues with such tokens are reported as "estimated": check them against the audio.

Output: [{"start", "end", "lang", "words": [{"t", "s", "e"}]}], the format the HyperFrames reel template
reads (templates/hyperframes-reel). To show a word as an emoji image, add "emoji": "<asset path>" to it.
"""
import difflib
import json
import os
import sys
import unicodedata

PAD = 0.25        # transcript words whose midpoint is this close to the cue window are candidates
GAP = 0.01        # gap kept between consecutive words
MIN_WORD = 0.06   # shortest word duration written


def norm(tok):
    """Compare words without punctuation, case, niqqud or joiners ("e -mail" vs "email")."""
    tok = unicodedata.normalize("NFKC", tok).lower()
    return "".join(ch for ch in tok if not unicodedata.category(ch).startswith(("P", "M", "Z", "S")))


RTL = {"he", "iw", "ar", "fa", "ur", "yi"}


def cue_lang(cue, segments, default):
    """The caption's own script decides; for Latin text, the spoken language of the transcript segment."""
    for ch in cue["text"]:
        if 0x0590 <= ord(ch) <= 0x05FF:
            return "he"
        if 0x0600 <= ord(ch) <= 0x06FF:
            return cue.get("language", "ar")
    mid = (cue["start"] + cue["end"]) / 2
    seg = min(segments, key=lambda g: 0 if g["start"] <= mid <= g["end"]
              else min(abs(g["start"] - mid), abs(g["end"] - mid)))
    spoken = seg.get("language", default)
    return cue.get("language") or (spoken if spoken not in RTL else "en")


def spread(tokens, t0, t1):
    """Times for tokens laid end to end over [t0, t1], proportional to character length."""
    weights = [max(len(norm(t)), 1) + 1 for t in tokens]
    total, out, cur = sum(weights), [], t0
    for t, w in zip(tokens, weights):
        nxt = cur + (t1 - t0) * w / total
        out.append({"t": t, "s": round(cur, 2), "e": round(nxt - GAP, 2)})
        cur = nxt
    return out


def align_cue(cue, words):
    tokens = cue["text"].split()
    mid = lambda w: (w["s"] + w["e"]) / 2
    cand = [w for w in words if cue["start"] - PAD <= mid(w) <= cue["end"] + PAD]
    sm = difflib.SequenceMatcher(None, [norm(t) for t in tokens], [norm(w["w"]) for w in cand], autojunk=False)
    timed, estimated = [None] * len(tokens), []
    ops = sm.get_opcodes()
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            for k in range(i2 - i1):
                w = cand[j1 + k]
                timed[i1 + k] = {"t": tokens[i1 + k], "s": round(w["s"], 2), "e": round(w["e"], 2)}
        elif tag == "replace":
            # the transcript words this edited text replaces, kept inside the cue window
            inside = [w for w in cand[j1:j2] if cue["start"] <= mid(w) <= cue["end"]] or cand[j1:j2]
            t0, t1 = max(inside[0]["s"], cue["start"]), min(inside[-1]["e"], cue["end"])
            if t1 - t0 < MIN_WORD * (i2 - i1):
                t0, t1 = cue["start"], cue["end"]
            timed[i1:i2] = spread(tokens[i1:i2], t0, t1)
            estimated += tokens[i1:i2]
    # inserts: tokens with no transcript counterpart, placed between their neighbours
    i = 0
    while i < len(tokens):
        if timed[i] is not None:
            i += 1
            continue
        j = i
        while j < len(tokens) and timed[j] is None:
            j += 1
        t0 = timed[i - 1]["e"] + GAP if i > 0 else cue["start"]
        t1 = timed[j]["s"] - GAP if j < len(tokens) else cue["end"]
        if t1 - t0 < MIN_WORD * (j - i):          # no room between neighbours: use the cue window
            t0, t1 = cue["start"], cue["end"]
        timed[i:j] = spread(tokens[i:j], t0, t1)
        estimated += tokens[i:j]
        i = j
    # monotonic, non-overlapping, each word at least MIN_WORD long
    for k, w in enumerate(timed):
        if k:
            w["s"] = max(w["s"], round(timed[k - 1]["e"] + GAP, 2))
        w["e"] = max(w["e"], round(w["s"] + MIN_WORD, 2))
        if k + 1 < len(timed):
            w["e"] = min(w["e"], round(max(timed[k + 1]["s"] - GAP, w["s"] + MIN_WORD), 2))
    return timed, estimated


def main():
    args = [a for a in sys.argv[1:] if a != "--force"]
    if len(args) != 3:
        sys.exit(__doc__)
    cues_path, transcript_path, out_path = args
    if os.path.exists(out_path) and "--force" not in sys.argv:
        sys.exit(f"{out_path} exists and is the master caption file (hand edits, emoji). "
                 "Edit it directly, or pass --force to regenerate it from the cues.")
    cues_in = json.load(open(cues_path, encoding="utf-8"))
    transcript = json.load(open(transcript_path, encoding="utf-8"))
    cues = cues_in["cues"] if isinstance(cues_in, dict) else cues_in
    default_lang = cues_in.get("language", "en") if isinstance(cues_in, dict) else "en"
    words = [w for seg in transcript["segments"] for w in seg.get("words", [])]
    out, report = [], []
    for c in cues:
        timed, estimated = align_cue(c, words)
        out.append({"start": round(min(c["start"], timed[0]["s"]), 2), "end": round(max(c["end"], timed[-1]["e"]), 2),
                    "lang": cue_lang(c, transcript["segments"], default_lang), "words": timed})
        if estimated:
            report.append(f"  {c['start']:7.2f}s  estimated: {' '.join(estimated)}")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {len(out)} cues to {out_path}")
    if report:
        print("check these against the audio (hand-edited text, timed by character length):")
        print("\n".join(report))


if __name__ == "__main__":
    main()
