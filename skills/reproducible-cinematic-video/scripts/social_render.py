#!/usr/bin/env python3
"""Mode B: approved footage -> platform delivery (reframe, burned captions, encode, validate).

Works with an ffmpeg that has NO libass / drawtext / freetype: captions are rendered
by Pillow (RAQM layout = real bidi + shaping, so Hebrew/Arabic RTL is correct) into
transparent PNGs, sequenced with the concat demuxer, and overlaid in one pass.

Subcommands:
  preview   delivery manifest -> review/preview.jpg (source row + one row per zoom) to choose the reframe
  cues      transcript.json -> draft cues.json (split by word timestamps, flags foreign spans)
  render    delivery manifest -> <name>.mp4, <name>.<lang>.srt, <name>-cover.jpg, review/, validation.json
  validate  re-run validation on an existing render

Usage:
  python social_render.py preview delivery.json --times 3,8,13 --zooms 1.0,1.15,1.25
  python social_render.py cues transcript.json cues.json --caption-language he
  python social_render.py render delivery.json
  python social_render.py validate delivery.json

Paths inside the manifest resolve relative to the manifest file; `captions.font` falls back
to the skill directory (so the bundled "assets/fonts/Heebo[wght].ttf" works from anywhere).

Requires: ffmpeg/ffprobe on PATH, Pillow with RAQM (python -c "from PIL import features;
print(features.check('raqm'))" must print True for RTL scripts).
"""
import argparse
import hashlib
import json
import math
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

PRESETS = {
    # name: (width, height, safe-zone notes used for caption defaults)
    "ig-reels": (1080, 1920),      # 9:16 Reels / Stories
    "ig-story": (1080, 1920),
    "ig-feed-4x5": (1080, 1350),   # 4:5 feed video
    "ig-square": (1080, 1080),     # 1:1
    "yt-shorts": (1080, 1920),
    "tiktok": (1080, 1920),
    "landscape-16x9": (1920, 1080),
}
# Caption band centre (fraction of height) that clears platform UI.
# 9:16: bottom ~20% is caption/handle UI, right ~12% is the action-icon column.
DEFAULT_CAPTION_Y = {"ig-reels": 0.66, "ig-story": 0.66, "yt-shorts": 0.66, "tiktok": 0.64,
                     "ig-feed-4x5": 0.80, "ig-square": 0.80, "landscape-16x9": 0.86}
# Platform names map onto the canvases above (see references/social-delivery.md, "Which file for which
# platform"). One 9:16 master serves most of them; LinkedIn's main feed and desktop-heavy X want 4:5.
PRESET_ALIASES = {
    "fb-reels": "ig-reels", "fb-story": "ig-story", "fb-feed-4x5": "ig-feed-4x5",
    "linkedin-feed": "ig-feed-4x5", "linkedin-vertical": "ig-reels", "linkedin-landscape": "landscape-16x9",
    "x-vertical": "ig-reels", "x-square": "ig-square", "x-landscape": "landscape-16x9",
}
ANCHORS = {"left": 0.0, "top": 0.0, "center": 0.5, "middle": 0.5, "right": 1.0, "bottom": 1.0}
RTL_LANGS = {"he", "iw", "ar", "fa", "ur", "yi"}


# ----------------------------------------------------------------------------- helpers
def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw)


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "format=duration:stream=index,codec_type,codec_name,profile,width,height,"
               "r_frame_rate,pix_fmt,sample_rate,channels,nb_frames,color_transfer",
               "-of", "json", str(path)]).stdout
    return json.loads(out)


def vstream(info):
    return next(s for s in info["streams"] if s["codec_type"] == "video")


def astream(info):
    return next((s for s in info["streams"] if s["codec_type"] == "audio"), None)


def even(x):
    return max(2, int(round(x / 2.0)) * 2)


def anchor_value(v):
    return ANCHORS[v] if isinstance(v, str) else float(v)


def resolve_path(p, base):
    p = Path(p).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


# ----------------------------------------------------------------------------- cues
def cmd_cues(args):
    data = json.loads(Path(args.transcript).read_text())
    cues = []
    for seg in data["segments"]:
        words = seg.get("words") or []
        seg_cues, chunk = [], []
        for i, w in enumerate(words):
            chunk.append(w)
            punct = w["w"].strip().endswith((",", ".", "?", "!", ":", ";"))
            if i == len(words) - 1 or (punct and len(chunk) >= 2):
                pass
            elif len(chunk) >= args.max_words:
                # Do not strand a short function word ("את", "של", "a", "the") at a cue end.
                if len(chunk) > 2 and len(chunk[-1]["w"].strip()) <= 3:
                    chunk.pop()
                    seg_cues.append(chunk)
                    chunk = [w]
                    continue
            else:
                continue
            seg_cues.append(chunk)
            chunk = []
        if chunk:
            seg_cues.append(chunk)
        seg_cues = [{"start": c[0]["s"], "end": c[-1]["e"], "text": "".join(x["w"] for x in c).strip()}
                    for c in seg_cues]
        if not seg_cues:
            seg_cues = [{"start": seg["start"], "end": seg["end"], "text": seg["text"]}]
        # Segment edges are more reliable than word edges: snap the outer cue bounds to them.
        seg_cues[0]["start"], seg_cues[-1]["end"] = seg["start"], seg["end"]
        for c in seg_cues:
            c["source_language"] = seg.get("language")
            if seg.get("language", args.caption_language) != args.caption_language:
                c["needs_translation"] = True
            if seg.get("suspect") or any(x in c["text"].split() for x in seg.get("low_confidence", [])):
                c["review"] = True
        cues += seg_cues
    # Close small gaps so captions do not flicker; enforce a readable minimum.
    for a, b in zip(cues, cues[1:]):
        if b["start"] - a["end"] < args.bridge_gap:
            a["end"] = b["start"]
    for c in cues:
        c["start"], c["end"] = round(c["start"], 3), round(max(c["end"], c["start"] + args.min_duration), 3)
    for a, b in zip(cues, cues[1:]):
        a["end"] = min(a["end"], b["start"])
    lang = args.caption_language
    doc = {"language": lang, "direction": "rtl" if lang in RTL_LANGS else "ltr", "cues": cues}
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    for c in cues:
        tags = "".join([" [TRANSLATE]" if c.get("needs_translation") else "", " [REVIEW]" if c.get("review") else ""])
        print(f"{c['start']:6.2f}-{c['end']:6.2f} {c['text']}{tags}")


# ----------------------------------------------------------------------------- captions
def load_font(cfg):
    from PIL import ImageFont, features
    if not features.check("raqm"):
        sys.exit("Pillow lacks RAQM: RTL/complex-script captions would render in wrong order. "
                 "Install libraqm (brew install libraqm) and reinstall Pillow.")
    font = ImageFont.truetype(cfg["_font_path"], cfg["size"], layout_engine=ImageFont.Layout.RAQM)
    try:
        axes = font.get_variation_axes()
    except OSError:
        axes = None  # static font: `weight` does not apply, pick the right file instead
    if axes and cfg.get("weight"):
        font.set_variation_by_axes([cfg["weight"] if a["name"] in (b"Weight", "Weight") else a["default"]
                                    for a in axes])
    return font


IGNORABLE = set(" \t\n\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u00a0")


def check_glyphs(cues, cfg):
    """Exit if the caption font lacks any glyph used in the cues (they would render as boxes)."""
    font = load_font(cfg)
    def signature(ch):
        mask = font.getmask(ch)
        return mask.size, bytes(mask)

    notdef = signature("\uffff")  # noncharacter: always rendered with the .notdef glyph
    used = {ch for c in cues for ch in c["text"]} - IGNORABLE
    missing = sorted(ch for ch in used if signature(ch) == notdef)
    if missing:
        sys.exit(f"Font {cfg['_font_path']} has no glyph for: {' '.join(missing)} "
                 f"({', '.join(f'U+{ord(ch):04X}' for ch in missing)}). Set captions.font to a font "
                 f"that covers the caption language.")


def wrap(draw, text, font, max_w, direction, lang, max_lines):
    """Fewest lines that fit max_w; within that count, the most even line widths."""
    words = text.split()
    width = lambda ws: draw.textlength(" ".join(ws), font=font, direction=direction, language=lang)
    if width(words) <= max_w or len(words) == 1:
        return [text]
    if max_lines >= 2:
        best = None
        for i in range(1, len(words)):
            a, b = words[:i], words[i:]
            wa, wb = width(a), width(b)
            if wa <= max_w and wb <= max_w and (best is None or max(wa, wb) < best[0]):
                best = (max(wa, wb), [" ".join(a), " ".join(b)])
        if best:
            return best[1]
    lines, cur = [], []  # greedy fallback for 3+ lines
    for word in words:
        if cur and width(cur + [word]) > max_w:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    return lines + [" ".join(cur)] if cur else lines


def render_cue_png(text, cfg, band_w, band_h, direction, lang, path):
    from PIL import Image, ImageDraw
    size = cfg["size"]
    max_w = band_w - 2 * cfg["side_margin"] - 2 * cfg["pad_x"]
    probe_img = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    while True:  # shrink (to 75%) until it fits max_lines
        font = load_font({**cfg, "size": size})
        lines = wrap(probe_img, text, font, max_w, direction, lang, cfg["max_lines"])
        if len(lines) <= cfg["max_lines"] or size <= cfg["size"] * 0.75:
            break
        size -= 2
    if len(lines) > cfg["max_lines"]:
        print(f"WARNING: cue does not fit {cfg['max_lines']} lines, split it: {text}", file=sys.stderr)
    img = Image.new("RGBA", (band_w, band_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    line_h = int(size * cfg["line_height"])
    total_h = line_h * len(lines) + cfg["line_gap"] * (len(lines) - 1)
    y = (band_h - total_h) // 2
    box = tuple(cfg["box_rgba"]) if cfg.get("box") else None
    for line in lines:
        w = d.textlength(line, font=font, direction=direction, language=lang)
        cx, cy = band_w / 2, y + line_h / 2
        if box:
            d.rounded_rectangle([cx - w / 2 - cfg["pad_x"], y - cfg["pad_y"],
                                 cx + w / 2 + cfg["pad_x"], y + line_h + cfg["pad_y"]],
                                radius=cfg["radius"], fill=box)
        d.text((cx, cy), line, font=font, fill=tuple(cfg["color_rgba"]), anchor="mm",
               direction=direction, language=lang, stroke_width=cfg["stroke_width"],
               stroke_fill=tuple(cfg["stroke_rgba"]))
        y += line_h + cfg["line_gap"]
    img.save(path)


def caption_defaults(preset, tw, th):
    return {"font": "assets/fonts/Heebo[wght].ttf", "weight": 800, "size": round(tw * 0.066),
            "line_height": 1.3, "line_gap": 14, "max_lines": 2,
            "side_margin": round(tw * (0.12 if th / tw > 1.5 else 0.06)), "pad_x": 26, "pad_y": 8, "radius": 18,
            "box": True, "box_rgba": [0, 0, 0, 165], "color_rgba": [255, 255, 255, 255],
            "stroke_width": 0, "stroke_rgba": [0, 0, 0, 255],
            "y_center": DEFAULT_CAPTION_Y.get(preset, 0.66), "band_height": round(th * 0.16)}


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def write_srt(cues, direction, path):
    rlm = "‏" if direction == "rtl" else ""  # keeps RTL paragraph direction in players
    blocks = [f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{rlm}{c['text']}\n"
              for i, c in enumerate(cues, 1)]
    Path(path).write_text("\n".join(blocks), encoding="utf-8")


# ----------------------------------------------------------------------------- reframe
def lerp_expr(keys, field, span):
    """Piecewise-linear ffmpeg expression in t for crop x/y from anchor keyframes."""
    pts = [(k["t"], anchor_value(k[field]) * span) for k in keys if field in k]
    if not pts:
        return None
    expr = f"{pts[-1][1]:.3f}"
    for (t0, v0), (t1, v1) in reversed(list(zip(pts, pts[1:]))):
        seg = f"{v0:.3f}+({v1 - v0:.3f})*(t-{t0:.3f})/{max(t1 - t0, 1e-3):.3f}"
        expr = f"if(lt(t,{t1:.3f}),{seg},{expr})"
    return f"if(lt(t,{pts[0][0]:.3f}),{pts[0][1]:.3f},{expr})"


def crop_filter(src_w, src_h, tw, th, rf):
    aspect = tw / th
    base_w, base_h = (src_h * aspect, src_h) if src_w / src_h > aspect else (src_w, src_w / aspect)
    zoom = float(rf.get("zoom", 1.0))
    if zoom < 1.0:
        sys.exit("reframe.zoom < 1 cannot be cropped (it would stretch the picture). "
                 "To keep the whole source frame use \"fit\": \"blur-pad\".")
    cw, ch = even(base_w / zoom), even(base_h / zoom)
    span_x, span_y = src_w - cw, src_h - ch
    keys = rf.get("keyframes") or []
    x = lerp_expr(keys, "anchor_x", span_x) or f"{anchor_value(rf.get('anchor_x', 'center')) * span_x:.3f}"
    y = lerp_expr(keys, "anchor_y", span_y) or f"{anchor_value(rf.get('anchor_y', 'center')) * span_y:.3f}"
    return f"crop={cw}:{ch}:'{x}':'{y}'", (cw, ch)


def video_graph(v, tw, th, fps, rf):
    """Filter chain from [0:v] to the reframed canvas (no output label). Returns (chain, upscale, desc)."""
    W, H = v["width"], v["height"]
    fit = rf.get("fit", "crop")
    if fit == "crop":
        crop, (cw, ch) = crop_filter(W, H, tw, th, rf)
        chain = f"[0:v]fps={fps},{crop},scale={tw}:{th}:flags=lanczos,setsar=1"
        return chain, tw / cw, f"crop {cw}x{ch}"
    if fit == "blur-pad":
        # Whole source frame, scaled to fit, over a blurred fill of itself (no stretch, no loss).
        s = min(tw / W, th / H)
        fw, fh = even(W * s), even(H * s)
        fy = f"(H-h)*{anchor_value(rf.get('pad_anchor_y', 'center')):.3f}"
        chain = (f"[0:v]fps={fps},split[bgsrc][fgsrc];"
                 f"[bgsrc]scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},"
                 f"gblur=sigma={rf.get('blur', 40)},eq=brightness={rf.get('bg_brightness', -0.08)}[bg];"
                 f"[fgsrc]scale={fw}:{fh}:flags=lanczos,setsar=1[fg];[bg][fg]overlay=(W-w)/2:{fy}")
        return chain, s, f"blur-pad fit {fw}x{fh}"
    sys.exit(f"unknown reframe.fit {fit!r} (use 'crop' or 'blur-pad')")


def resolve_fps(m, v):
    """Manifest fps, else the source rate when <= 30, else half of it (60 -> 30, 59.94 -> 29.97)."""
    if m.get("fps"):
        return str(m["fps"]), float(m["fps"])
    num, den = map(int, v["r_frame_rate"].split("/"))
    src = num / den
    if src <= 30.5:
        return f"{num}/{den}", src
    if src >= 47:
        return f"{num}/{den * 2}", src / 2
    return "30", 30.0


def grab_frame(src, chain, t, out, keyframed, extra_vf=""):
    """One frame through the reframe chain. Output-side seek when crop depends on t."""
    graph = f"{chain}{',' + extra_vf if extra_vf else ''}[v]"
    seek_in, seek_out = ([], ["-ss", f"{t:.3f}"]) if keyframed else (["-ss", f"{t:.3f}"], [])
    subprocess.run(["ffmpeg", "-v", "error", "-y", *seek_in, "-i", src, *seek_out, "-filter_complex", graph,
                    "-map", "[v]", "-frames:v", "1", "-q:v", "2", str(out)], check=True)


# ----------------------------------------------------------------------------- render
def load_manifest(path):
    path = Path(path).resolve()
    m = json.loads(path.read_text())
    base = path.parent
    m["_base"] = base
    m["source"] = str(resolve_path(m["source"], base))
    m["output_dir"] = str(resolve_path(m.get("output_dir", "delivery"), base))
    # Review artefacts stay out of the clean delivery folder.
    m["review_dir"] = str(resolve_path(m.get("review_dir", "work/review"), base))
    if m.get("preset"):
        m["preset"] = PRESET_ALIASES.get(m["preset"], m["preset"])
        if m["preset"] not in PRESETS:
            sys.exit(f"unknown preset {m['preset']!r}. Known: {', '.join([*PRESETS, *PRESET_ALIASES])}. "
                     "Or omit preset and set width/height.")
        tw, th = PRESETS[m["preset"]]
    elif "width" in m and "height" in m:
        tw, th = m["width"], m["height"]
    else:
        sys.exit("delivery manifest needs a preset or width/height")
    m["_size"] = (tw, th)
    if m.get("captions"):
        m["captions"] = {**caption_defaults(m.get("preset"), tw, th), **m["captions"]}
        m["captions"]["cues"] = str(resolve_path(m["captions"]["cues"], base))
        font = Path(m["captions"]["font"]).expanduser()
        candidates = [font] if font.is_absolute() else [base / font, SKILL_DIR / font]
        found = next((c for c in candidates if c.exists()), None)
        if not found:
            sys.exit(f"caption font not found: {m['captions']['font']} (looked in {base} and {SKILL_DIR})")
        m["captions"]["_font_path"] = str(found.resolve())
    return m


def cmd_render(args):
    m = load_manifest(args.manifest)
    src = m["source"]
    tw, th = m["_size"]
    out_dir = Path(m["output_dir"])
    review = Path(m["review_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    review.mkdir(parents=True, exist_ok=True)
    name = m["name"]
    out_mp4 = out_dir / f"{name}.mp4"

    info = probe(src)
    v = vstream(info)
    if v.get("color_transfer") in ("smpte2084", "arib-std-b67"):
        sys.exit("HDR source (PQ/HLG): add a tonemap stage before reframing; not handled here.")
    duration = float(info["format"]["duration"])
    fps, fps_f = resolve_fps(m, v)
    rf = m.get("reframe", {})
    vchain, upscale, desc = video_graph(v, tw, th, fps, rf)
    print(f"source {v['width']}x{v['height']} @ {v['r_frame_rate']} -> {desc} -> {tw}x{th} @ {fps} "
          f"(scale x{upscale:.2f})")
    enc = m.get("video", {})
    if enc.get("sharpen"):
        # Luma-only unsharp after scaling: offsets phone softness and upscale blur. 0.3-0.8 is sane.
        vchain += f",unsharp=5:5:{float(enc['sharpen']):.2f}:5:5:0.0"
    if upscale > 1.7:
        print(f"WARNING: x{upscale:.2f} upscale will look soft. Options: a higher-resolution source, "
              f"zoom closer to 1.0, or \"fit\": \"blur-pad\". (1080p 16:9 -> 9:16 crop is x1.78 at best.)",
              file=sys.stderr)
    inputs = ["-i", src]
    tmp = Path(tempfile.mkdtemp(prefix="captions-"))
    cap = m.get("captions")
    if cap:
        doc = json.loads(Path(cap["cues"]).read_text())
        lang = doc.get("language", "he")
        direction = doc.get("direction", "rtl" if lang in RTL_LANGS else "ltr")
        cues = sorted(doc["cues"], key=lambda c: c["start"])
        check_glyphs(cues, cap)
        pending = [c for c in cues if c.get("needs_translation")]
        if pending and not args.allow_untranslated:
            sys.exit(f"{len(pending)} cue(s) still need translation into '{lang}' "
                     f"(first: {pending[0]['text']!r}). Edit cues.json or pass --allow-untranslated.")
        band_w, band_h = tw, cap["band_height"]
        from PIL import Image
        Image.new("RGBA", (band_w, band_h), (0, 0, 0, 0)).save(tmp / "blank.png")
        lines, t = ["ffconcat version 1.0"], 0.0
        for i, c in enumerate(cues):
            png = tmp / f"cue_{i:03}.png"
            render_cue_png(c["text"], cap, band_w, band_h, direction, lang, png)
            if c["start"] > t:
                lines += ["file 'blank.png'", f"duration {c['start'] - t:.3f}"]
            lines += [f"file '{png.name}'", f"duration {c['end'] - c['start']:.3f}"]
            t = c["end"]
        lines += ["file 'blank.png'", f"duration {max(duration - t, 0.1) + 1:.3f}", "file 'blank.png'"]
        (tmp / "captions.ffconcat").write_text("\n".join(lines) + "\n")
        inputs += ["-f", "concat", "-safe", "0", "-i", str(tmp / "captions.ffconcat")]
        band_y = int(round(cap["y_center"] * th - band_h / 2))
        graph = (f"{vchain}[base];[1:v]fps={fps},format=rgba[cap];"
                 f"[base][cap]overlay=0:{band_y}:eof_action=pass:format=auto,format=yuv420p[v]")
        write_srt(cues, direction, out_dir / f"{name}.{lang}.srt")
    else:
        graph = f"{vchain},format=yuv420p[v]"

    audio = m.get("audio", {"mode": "copy"})
    if audio["mode"] == "copy":
        acodec = ["-c:a", "copy"]
    elif audio["mode"] == "loudnorm":
        acodec = ["-af", f"loudnorm=I={audio.get('lufs', -14)}:TP=-1.5:LRA=11", "-c:a", "aac",
                  "-b:a", "192k", "-ar", "48000"]
    else:
        acodec = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]

    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", *inputs, "-filter_complex", graph,
           "-map", "[v]", "-map", "0:a:0?", "-t", f"{duration:.3f}",
           "-c:v", "libx264", "-profile:v", "high", "-preset", enc.get("preset", "slow"),
           "-crf", str(enc.get("crf", 18)), "-maxrate", enc.get("maxrate", "12M"),
           "-bufsize", enc.get("bufsize", "24M"), "-g", str(round(fps_f * 2)), "-pix_fmt", "yuv420p",
           "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", *acodec, "-movflags", "+faststart", str(out_mp4)]
    (review / "ffmpeg-command.txt").write_text(" ".join(cmd))
    subprocess.run(cmd, check=True)

    if m.get("cover_time") is not None:
        grab_frame(src, vchain, float(m["cover_time"]), out_dir / f"{name}-cover.jpg",
                   keyframed=bool(rf.get("keyframes")))
    cmd_validate(args, m)


# ----------------------------------------------------------------------------- validate
def top_level_boxes(path):
    boxes = []
    with open(path, "rb") as f:
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            size, kind = struct.unpack(">I4s", hdr)
            if size == 1:
                size = struct.unpack(">Q", f.read(8))[0]
                f.seek(size - 16, 1)
            elif size == 0:
                boxes.append(kind.decode())
                break
            else:
                f.seek(size - 8, 1)
            boxes.append(kind.decode())
    return boxes


def audio_md5(path):
    return run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-c", "copy",
                "-f", "md5", "-"]).stdout.strip()


def cmd_validate(args, m=None):
    m = m or load_manifest(args.manifest)
    tw, th = m["_size"]
    _, fps = resolve_fps(m, vstream(probe(m["source"])))
    out_dir, review = Path(m["output_dir"]), Path(m["review_dir"])
    review.mkdir(parents=True, exist_ok=True)
    out_mp4 = out_dir / f"{m['name']}.mp4"
    src_info, out_info = probe(m["source"]), probe(out_mp4)
    ov, oa = vstream(out_info), astream(out_info)
    num, den = map(int, ov["r_frame_rate"].split("/"))
    sd, od = float(src_info["format"]["duration"]), float(out_info["format"]["duration"])
    boxes = top_level_boxes(out_mp4)
    decode_err = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out_mp4), "-f", "null", "-"],
                                capture_output=True, text=True).stderr.strip()
    checks = {
        "dimensions": [ov["width"], ov["height"]] == [tw, th],
        "fps": abs(num / den - fps) < 0.01,
        "pix_fmt_yuv420p": ov.get("pix_fmt") == "yuv420p",
        "h264_high": ov.get("codec_name") == "h264" and ov.get("profile") == "High",
        "duration_matches_source": abs(od - sd) <= 2.0 / fps + 0.05,
        "faststart_moov_before_mdat": "moov" in boxes and "mdat" in boxes and boxes.index("moov") < boxes.index("mdat"),
        "full_decode_clean": decode_err == "",
        "audio_present": oa is not None,
    }
    if m.get("audio", {"mode": "copy"})["mode"] == "copy" and oa:
        checks["audio_bitstream_identical_to_source"] = audio_md5(m["source"]) == audio_md5(out_mp4)
    report = {"output": str(out_mp4), "size_mb": round(out_mp4.stat().st_size / 1e6, 2),
              "source_duration": sd, "output_duration": od, "video": ov, "audio": oa,
              "top_level_boxes": boxes, "decode_errors": decode_err[:2000], "checks": checks}
    (review / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))

    # Review sheet: frames at cue midpoints (or evenly spaced) from the ENCODED file.
    times = []
    if m.get("captions"):
        cues = json.loads(Path(m["captions"]["cues"]).read_text())["cues"]
        times = [(c["start"] + c["end"]) / 2 for c in cues]
    if not times:
        times = [od * (i + 0.5) / 8 for i in range(8)]
    step = max(1, math.ceil(len(times) / 12))
    times = times[::step][:12]
    with tempfile.TemporaryDirectory() as tmp:
        for i, t in enumerate(times):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(out_mp4),
                            "-frames:v", "1", "-vf", f"scale={tw // 3}:-2", f"{tmp}/r_{i:02}.png"],
                           check=True)
        cols = min(6, len(times))
        rows = math.ceil(len(times) / cols)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", f"{tmp}/r_*.png",
                        "-vf", f"tile={cols}x{rows}", "-frames:v", "1",
                        str(review / "contact-sheet.jpg")], check=True)
    for k, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {k}")
    print(f"review sheet: {review / 'contact-sheet.jpg'}")
    if not all(checks.values()):
        sys.exit(1)


def cmd_preview(args):
    m = load_manifest(args.manifest)
    tw, th = m["_size"]
    v = vstream(probe(m["source"]))
    rf = m.get("reframe", {})
    times = [float(t) for t in args.times.split(",")]
    zooms = [float(z) for z in args.zooms.split(",")] if args.zooms else [float(rf.get("zoom", 1.0))]
    tile_w, tile_h = even(tw / 4), even(th / 4)
    review = Path(m["review_dir"])
    review.mkdir(parents=True, exist_ok=True)
    keyframed = bool(rf.get("keyframes"))
    rows = [("source", f"[0:v]scale={tile_w}:{tile_h}:force_original_aspect_ratio=decrease,"
                       f"pad={tile_w}:{tile_h}:(ow-iw)/2:(oh-ih)/2")]
    if rf.get("fit", "crop") == "crop":
        rows += [(f"zoom {z}", video_graph(v, tw, th, 30, {**rf, "zoom": z})[0]) for z in zooms]
    else:
        rows += [(rf["fit"], video_graph(v, tw, th, 30, rf)[0])]
    with tempfile.TemporaryDirectory() as tmp:
        for r, (label, chain) in enumerate(rows):
            for c, t in enumerate(times):
                grab_frame(m["source"], chain, t, f"{tmp}/p_{r:02}_{c:02}.png", keyframed and r > 0,
                           extra_vf="" if r == 0 else f"scale={tile_w}:{tile_h}")
        out = review / "preview.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", f"{tmp}/p_*.png",
                        "-vf", f"tile={len(times)}x{len(rows)}", "-frames:v", "1", str(out)], check=True)
    print("rows: " + " | ".join(label for label, _ in rows) + f"\ncolumns: t = {times}\n{out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("preview")
    pv.add_argument("manifest")
    pv.add_argument("--times", required=True, help="comma-separated seconds, e.g. 3,8,13")
    pv.add_argument("--zooms", help="comma-separated zoom values to compare (crop fit only)")
    c = sub.add_parser("cues")
    c.add_argument("transcript")
    c.add_argument("out")
    c.add_argument("--caption-language", required=True)
    c.add_argument("--max-words", type=int, default=7)
    c.add_argument("--bridge-gap", type=float, default=0.35)
    c.add_argument("--min-duration", type=float, default=0.8)
    r = sub.add_parser("render")
    r.add_argument("manifest")
    r.add_argument("--allow-untranslated", action="store_true")
    v = sub.add_parser("validate")
    v.add_argument("manifest")
    args = ap.parse_args()
    {"preview": cmd_preview, "cues": cmd_cues, "render": cmd_render, "validate": cmd_validate}[args.cmd](args)


if __name__ == "__main__":
    main()
