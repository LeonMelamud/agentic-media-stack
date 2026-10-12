#!/usr/bin/env python3
"""Build a HyperFrames reel (karaoke captions, hook, tag, CTA, punch-ins) from reel.json + captions.json.

Usage (from the master HyperFrames project root):
    python3 -I prep/build_reel.py prep/reel.json [layout] [--no-grade]

layout   a key of reel.json "layouts" (default "reel"). A layout with "out" writes a sibling project
         (scaffolded on first use: config copied, media hard-linked) so one captions.json feeds every ratio.
--no-grade  skip the canonical grades (npx hyperframes media-treatment), e.g. for a quick lint.

The card shows the whole source frame, never upscaled: card w/h keep the source aspect and card w <= source
width. Built-in layouts "reel" (1080x1920) and "feed-4x5" (1080x1350) assume a 9:16 source; override any key
per layout in reel.json. See references/hyperframes-polish.md for the format and the reasons behind each value.
"""
import html
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import ImageFont, features

LAYOUT_DEFAULTS = {
    # 9:16 Reels / Shorts / TikTok / FB Reels / X vertical: the source at native size on a blurred fill
    "reel": {"canvas": [1080, 1920], "card": {"x": 135, "y": 380, "w": 810, "h": 1440}, "radius": 40,
             "shadow": "0 30px 90px", "hook_top": 132, "hook_font": 76, "chip_top": 226,
             "cta_top": 860, "cta_side": 135, "cue_top": 1150, "cue_side": 135},
    # 4:5 LinkedIn feed / FB feed / desktop-heavy X: the same card at 0.77, title and tag in the band above
    "feed-4x5": {"canvas": [1080, 1350], "card": {"x": 228, "y": 197, "w": 624, "h": 1109}, "radius": 31,
                 "shadow": "0 24px 70px", "hook_top": 26, "hook_font": 64, "chip_top": 72,
                 "cta_top": 533, "cta_side": 110, "cue_top": 905, "cue_side": 150},
}
RTL = {"he", "iw", "ar", "fa", "ur", "yi"}
SIZE = {"rtl": 62, "ltr": 56}     # caption px on a 1080-wide canvas; same in every layout
GAP_EM = 0.34                     # word gap; below this the karaoke lift makes neighbours touch
EMOJI_EM = 1.15
PILL_MAX = 740                    # same caption width and line breaks in every layout
LINE_MAX = PILL_MAX - 2 * 32 - 24
PANEL = "background: rgba(16, 20, 29, 0.88); box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);"
PROJECT_FILES = ["hyperframes.json", "package.json", "meta.json", "CLAUDE.md", "AGENTS.md"]


def load(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    cfg_path = Path(args[0]).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    master = cfg_path.parent.parent if cfg_path.parent.name == "prep" else cfg_path.parent
    layout_name = args[1] if len(args) > 1 else "reel"
    layouts = cfg.get("layouts", {"reel": {}})
    if layout_name not in layouts:
        sys.exit(f"unknown layout {layout_name!r}; reel.json has: {', '.join(layouts)}")
    spec = layouts[layout_name]
    base = spec.get("base", layout_name)
    if base not in LAYOUT_DEFAULTS:
        sys.exit(f"layout {layout_name!r} needs \"base\": one of {', '.join(LAYOUT_DEFAULTS)} (then override keys)")
    L = {**LAYOUT_DEFAULTS[base], **spec}
    out = (master / spec["out"]).resolve() if spec.get("out") else master
    return cfg, master, layout_name, L, out, "--no-grade" in argv


cfg, MASTER, LAYOUT_NAME, L, OUT, NO_GRADE = load(sys.argv)
CW, CH = L["canvas"]
CARD = L["card"]
M = cfg["media"]
VIDEO_D = cfg["video_duration"]
HOLD_D = cfg.get("hold", 0)
DURATION = round(VIDEO_D + HOLD_D, 3)
BRAND = set(cfg.get("brand_words", []))
FONT_SANS, FONT_SERIF = cfg["fonts"]["sans"], cfg["fonts"]["serif"]
# CSS uses each file's real family name: `hyperframes check` measures text by family name, and a made-up alias
# makes it report false text overflows
SANS, SERIF = (ImageFont.truetype(str(MASTER / f), 20).getname()[0] for f in (FONT_SANS, FONT_SERIF))
FONTS = f"""
      @font-face {{ font-family: "{SANS}"; src: url("{FONT_SANS}") format("truetype"); font-weight: 100 900; }}
      @font-face {{ font-family: "{SERIF}"; src: url("{FONT_SERIF}") format("truetype"); font-weight: 300 900; }}"""
cues = json.loads((MASTER / cfg["captions"]).read_text(encoding="utf-8"))

# ----------------------------------------------------------------------------- caption line balancing
assert features.check("raqm"), "Pillow needs RAQM to measure RTL text"
_fonts = {}


def direction(lang):
    return "rtl" if lang in RTL else "ltr"


def measure(words, lang):
    d = direction(lang)
    if d not in _fonts:
        f = ImageFont.truetype(str(MASTER / FONT_SANS), SIZE[d], layout_engine=ImageFont.Layout.RAQM)
        try:
            f.set_variation_by_axes([800])
        except OSError:
            pass  # static font: pick the ExtraBold file itself
        _fonts[d] = f
    width = lambda w: EMOJI_EM * SIZE[d] if "emoji" in w else _fonts[d].getlength(w["t"], direction=d, language=lang)
    return sum(width(w) for w in words) + GAP_EM * SIZE[d] * (len(words) - 1)


def split_lines(words, lang):
    """One line if it fits, else the two-line split with the most even widths (no orphans)."""
    if measure(words, lang) <= LINE_MAX or len(words) < 2:
        return [words]
    best = min(range(1, len(words)), key=lambda i: max(measure(words[:i], lang), measure(words[i:], lang)))
    return [words[:best], words[best:]]


def sub(comp_id, duration, style, body, script, lang="he"):
    return f"""<!doctype html>
<html lang="{lang}">
  <head><meta charset="UTF-8" /></head>
  <body>
    <template>
      <style>{FONTS}
{style}
      </style>
      <div id="root" data-composition-id="{comp_id}" data-width="{CW}" data-height="{CH}" data-duration="{duration:.2f}">
{body}
      </div>
      <script>
        const tl = gsap.timeline({{ paused: true }});
{script}
        window.__timelines["{comp_id}"] = tl;
      </script>
    </template>
  </body>
</html>
"""


def rich(text):
    """*word* -> accent span (brand name in the hook)."""
    parts = html.escape(text).split("*")
    return "".join(f'<span class="accent">{p}</span>' if i % 2 else p for i, p in enumerate(parts))


UI_LANG = cfg.get("language", "he")
UI_DIR = direction(UI_LANG)
SIDE = "right" if UI_DIR == "rtl" else "left"     # title and tag align to the card's reading-start edge
files, hosts = {}, []

# ----------------------------------------------------------------------------- hook (top band, vertical motion only)
if cfg.get("hook"):
    H = cfg["hook"]
    lines = "\n".join(f'          <span class="hook-line"><span class="hook-text" id="hook-{i + 1}">{rich(t)}</span></span>'
                      for i, t in enumerate(H["lines"]))
    rises = "\n".join(f'        tl.fromTo("#hook-{i + 1}", {{ yPercent: 105 }}, {{ yPercent: 0, duration: 0.6, ease: "expo.out" }}, {0.15 * (i + 1):.2f});'
                      for i in range(len(H["lines"])))
    files["hook"] = sub("hook", H["duration"], f"""
      #root {{ position: absolute; inset: 0; }}
      #hook-panel {{ position: absolute; top: {L["hook_top"]}px; {SIDE}: {CARD["x"]}px; direction: {UI_DIR}; padding: 26px 40px 30px;
        border-radius: 26px; {PANEL} }}
      .hook-line {{ display: block; overflow: hidden; padding-bottom: 4px; }}
      .hook-text {{ display: block; font-family: "{SERIF}", serif; font-weight: 900; font-size: {L["hook_font"]}px; line-height: 1.06; color: #fbf6f1; }}
      .accent {{ color: #f2876b; font-family: "{SANS}", sans-serif; font-weight: 800; }}
      #hook-rule {{ display: block; width: 100%; height: 5px; margin-top: 14px; border-radius: 3px; background: #f2876b; }}""",
f"""        <div id="hook-panel" dir="{UI_DIR}" lang="{UI_LANG}">
{lines}
          <span id="hook-rule"></span>
        </div>""",
f"""        tl.fromTo("#hook-panel", {{ y: -24, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.5, ease: "power3.out" }}, 0.05);
{rises}
        tl.fromTo("#hook-rule", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4, ease: "power1.out" }}, 0.6);
        tl.to("#hook-panel", {{ y: -18, opacity: 0, duration: 0.35, ease: "power2.in" }}, {H["duration"] - 0.4:.2f});""", UI_LANG)
    hosts.append(("hook", H["start"], H["duration"], 2, ""))

# ----------------------------------------------------------------------------- tag (fade only, takes the band after the hook)
if cfg.get("chip"):
    C = cfg["chip"]
    chip_d = round(DURATION - C["start"], 3)
    repeats = max(int((chip_d - 0.5) / 1.2) - 1, 0)
    files["chip"] = sub("chip", chip_d, f"""
      #root {{ position: absolute; inset: 0; font-family: "{SANS}", sans-serif; }}
      #chip-box {{ position: absolute; top: {L["chip_top"]}px; {SIDE}: {CARD["x"]}px; display: flex; align-items: center; gap: 16px; direction: {UI_DIR};
        padding: 14px 26px 14px 30px; border-radius: 999px; background: rgba(16, 20, 29, 0.82); color: #fbf6f1;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28); }}
      #chip-dot {{ display: block; width: 16px; height: 16px; border-radius: 50%; background: #f2876b; }}
      #chip-label {{ font-weight: 600; font-size: 28px; }}
      #chip-sep {{ display: block; width: 2px; height: 26px; background: rgba(251, 246, 241, 0.35); }}
      #chip-brand {{ font-weight: 800; font-size: 25px; letter-spacing: 0.14em; direction: ltr; }}""",
f"""        <div id="chip-box" dir="{UI_DIR}" lang="{UI_LANG}">
          <span id="chip-dot"></span>
          <span id="chip-label">{html.escape(C["label"])}</span>
          <span id="chip-sep"></span>
          <span id="chip-brand">{html.escape(C["brand"])}</span>
        </div>""",
f"""        tl.fromTo("#chip-box", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5, ease: "power1.out" }}, 0.0);
        tl.fromTo("#chip-dot", {{ scale: 1 }}, {{ scale: 1.35, duration: 1.2, ease: "sine.inOut", yoyo: true, repeat: {repeats} }}, 0.5);""", UI_LANG)
    hosts.append(("chip", C["start"], chip_d, 1, ""))

# ----------------------------------------------------------------------------- CTA (closing line over the dimmed card)
if cfg.get("cta"):
    T = cfg["cta"]
    cta_d = round(DURATION - T["start"], 3)
    lines = "\n".join(f'            <span class="cta-line"><span class="cta-text" id="cta-{i + 1}">{html.escape(t)}</span></span>'
                      for i, t in enumerate(T["lines"]))
    rises = "\n".join(f'        tl.fromTo("#cta-{i + 1}", {{ yPercent: 105 }}, {{ yPercent: 0, duration: 0.6, ease: "expo.out" }}, {0.15 * (i + 1):.2f});'
                      for i in range(len(T["lines"])))
    files["cta"] = sub("cta", cta_d, f"""
      #root {{ position: absolute; inset: 0; }}
      #cta-wrap {{ position: absolute; left: {L["cta_side"]}px; right: {L["cta_side"]}px; top: {L["cta_top"]}px; display: flex; justify-content: center; }}
      #cta-panel {{ direction: {UI_DIR}; padding: 34px 46px 38px; border-radius: 30px; {PANEL} text-align: center; }}
      .cta-line {{ display: block; overflow: hidden; padding-bottom: 4px; }}
      .cta-text {{ display: block; font-family: "{SERIF}", serif; font-weight: 900; font-size: 84px; line-height: 1.08; color: #fbf6f1; }}
      #cta-rule {{ display: block; width: 46%; height: 6px; margin: 18px auto 0; border-radius: 3px; background: #f2876b; transform-origin: 50% 50%; }}""",
f"""        <div id="cta-wrap">
          <div id="cta-panel" dir="{UI_DIR}" lang="{UI_LANG}">
{lines}
            <span id="cta-rule"></span>
          </div>
        </div>""",
f"""        tl.fromTo("#cta-panel", {{ y: 30, scale: 0.95, opacity: 0 }}, {{ y: 0, scale: 1, opacity: 1, duration: 0.5, ease: "power3.out" }}, 0.05);
{rises}
        tl.fromTo("#cta-rule", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.5, ease: "power2.out" }}, {0.15 * len(T["lines"]) + 0.4:.2f});""", UI_LANG)
    hosts.append(("cta", T["start"], cta_d, 4, ""))

# ----------------------------------------------------------------------------- captions
CAPTION_STYLE = f"""
      #root {{ position: absolute; inset: 0; font-family: "{SANS}", sans-serif; }}
      .cue {{ position: absolute; left: {L["cue_side"]}px; right: {L["cue_side"]}px; top: {L["cue_top"]}px; display: flex; justify-content: center; }}
      .pill {{ display: flex; flex-direction: column; align-items: center; row-gap: 2px;
        max-width: {PILL_MAX}px; padding: 16px 32px 20px; border-radius: 26px; background: rgba(16, 20, 29, 0.82);
        box-shadow: 0 14px 40px rgba(0, 0, 0, 0.32); font-weight: 800; font-size: {SIZE["rtl"]}px; line-height: 1.2; color: #bdb6b0; }}
      .pill[dir="ltr"] {{ font-size: {SIZE["ltr"]}px; }}
      .line {{ display: flex; flex-wrap: nowrap; justify-content: center; align-items: baseline; column-gap: {GAP_EM}em; }}
      .w {{ display: inline-block; transform-origin: 50% 80%; }}
      .emoji {{ display: block; width: {EMOJI_EM}em; height: {EMOJI_EM}em; margin-bottom: -0.2em; transform-origin: 50% 60%; }}"""

CAPTION_SCRIPT = """        const CUES = __CUES__;
        CUES.forEach(([s, e], i) => {
          const pill = `#__ID__-cue${i} .pill`;
          tl.fromTo(pill, { y: 24, scale: 0.95, opacity: 0 }, { y: 0, scale: 1, opacity: 1, duration: 0.26, ease: "back.out(1.6)" }, s);
          const out = Math.max(s + 0.3, e - 0.12);
          tl.to(pill, { y: -10, opacity: 0, duration: 0.12, ease: "power2.in" }, out);
          tl.set(pill, { opacity: 0, visibility: "hidden" }, out + 0.12);  // hard kill
        });
        // emoji words pop in when spoken, then shake like a laugh
        document.querySelectorAll(".__ID__-emoji").forEach((el) => {
          const s = parseFloat(el.parentElement.dataset.s);
          tl.fromTo(el, { scale: 0, rotation: -30 }, { scale: 1, rotation: 0, duration: 0.32, ease: "back.out(2.6)" }, s);
          tl.to(el, { rotation: 9, duration: 0.07, ease: "sine.inOut", yoyo: true, repeat: 5 }, s + 0.3);
        });
        // karaoke: one linear driver; upcoming = dim, spoken now = coral + lift, spoken = paper (brand words stay coral)
        const DIM = [189, 182, 176], PAPER = [251, 246, 241], CORAL = [242, 135, 107];
        const ATTACK = 0.08, RELEASE = 0.35;
        const words = Array.from(document.querySelectorAll(".__ID__-w")).map((el) => ({
          el, s: parseFloat(el.dataset.s), e: parseFloat(el.dataset.e), brand: el.classList.contains("brand"),
        }));
        const mix = (a, b, t) => a.map((v, k) => Math.round(v + (b[k] - v) * t));
        const driver = { t: 0 };
        tl.to(driver, {
          t: __D__, duration: __D__, ease: "none",
          onUpdate: () => {
            const t = driver.t;
            for (const w of words) {
              let c, lift;
              if (t < w.s) { c = DIM; lift = 0; }
              else if (t < w.e) { const a = Math.min((t - w.s) / ATTACK, 1); c = mix(DIM, CORAL, a); lift = a; }
              else { const r = Math.min((t - w.e) / RELEASE, 1); c = w.brand ? CORAL : mix(CORAL, PAPER, r); lift = 1 - r; }
              w.el.style.color = `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
              w.el.style.transform = `translateY(${-5 * lift}px) scale(${1 + 0.06 * lift})`;
            }
          },
        }, 0);"""


def caption_comp(comp_id, group, t0, duration):
    body, windows = [], []
    for ci, c in enumerate(group):
        d = direction(c["lang"])
        lines = []
        for line in split_lines(c["words"], c["lang"]):
            spans = []
            for w in line:
                bare = w["t"].strip(".,!?:;")
                cls = f"w {comp_id}-w" + (" brand" if bare in BRAND else "")
                inner = (f'<img class="emoji {comp_id}-emoji" src="{w["emoji"]}" alt="{w["t"]}" />' if "emoji" in w
                         else html.escape(w["t"]))
                spans.append(f'<span class="{cls}" data-s="{w["s"] - t0:.2f}" data-e="{w["e"] - t0:.2f}">{inner}</span>')
            lines.append(f'<div class="line">{"".join(spans)}</div>')
        s, e = c["start"] - t0, c["end"] - t0
        windows.append([round(s, 2), round(e, 2)])
        body.append(
            f'        <div id="{comp_id}-cue{ci}" class="clip cue" data-start="{s:.2f}" data-duration="{e - s:.2f}" '
            f'data-track-index="{ci % 2}">\n'
            f'          <div class="pill" dir="{d}" lang="{c["lang"]}">{"".join(lines)}</div>\n'
            f"        </div>")
    script = (CAPTION_SCRIPT.replace("__CUES__", json.dumps(windows)).replace("__ID__", comp_id)
              .replace("__D__", f"{duration:.2f}"))
    return sub(comp_id, duration, CAPTION_STYLE, "\n".join(body), script)


# about 6 cues per sub-composition keeps each caption track readable in Studio (lint: track density)
groups = cfg.get("caption_groups") or [[f"captions-{i // 6 + 1}", i, i + 6 if i + 6 < len(cues) else None]
                                       for i in range(0, len(cues), 6)]
for comp_id, a, b in groups:
    group = cues[a:b]
    t0 = group[0]["start"]
    dur = round(group[-1]["end"] - t0 + 0.05, 2)
    files[comp_id] = caption_comp(comp_id, group, t0, dur)
    hosts.append((comp_id, t0, dur, 3, ' data-track-kind="captions"'))
host_html = "\n".join(
    f'      <div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html"{extra}\n'
    f'           data-start="{start:.2f}" data-duration="{dur:.2f}" data-track-index="{track}" data-width="{CW}" data-height="{CH}"></div>'
    for cid, start, dur, track, extra in hosts)

# ----------------------------------------------------------------------------- camera moves on the untimed #cam wrapper
cam_origin = cfg.get("cam_origin", "50% 50%")
moves = []
push = cfg.get("opening_push")
if push:  # slow push toward the subject, released on a cut (e.g. a replaced steady opening)
    moves += [f'      tl.set("#cam", {{ transformOrigin: "{push["origin"]}" }}, 0);',
              f'      tl.fromTo("#cam", {{ scale: 1 }}, {{ scale: {push["scale"]}, duration: {push["until"]:.3f}, ease: "none" }}, 0);',
              f'      tl.set("#cam", {{ scale: 1, transformOrigin: "{cam_origin}" }}, {push["until"]:.3f});']
for p in cfg.get("punch_ins", []):  # move "origin" only while scale is 1
    note = f'   // {p["note"]}' if p.get("note") else ""
    if "origin" in p:
        moves.append(f'      tl.set("#cam", {{ transformOrigin: "{p["origin"]}" }}, {p["t"]});{note}')
    else:
        moves.append(f'      tl.to("#cam", {{ scale: {p["scale"]}, duration: {p["dur"]}, ease: "{p.get("ease", "sine.inOut")}" }}, {p["t"]});{note}')
if cfg.get("cta") and cfg["cta"].get("dim_exposure") is not None:
    moves.append(f'      tl.to("#base", {{ "--hf-color-grading-exposure": {cfg["cta"]["dim_exposure"]}, duration: 0.6, ease: "power1.inOut" }}, {cfg["cta"]["start"]});')
base_exposure = cfg.get("base_exposure", 0)

if HOLD_D:
    hold_html = (f'\n      <img id="bg-hold" class="clip" src="{M["bg_hold"]}" alt="" data-start="{VIDEO_D}" data-duration="{HOLD_D}" data-track-index="5" />',
                 f'\n          <img id="base-hold" class="clip" src="{M["hold"]}" alt="" data-start="{VIDEO_D}" data-duration="{HOLD_D}" data-track-index="0" />')
else:
    hold_html = ("", "")

page = f"""<!doctype html>
<html lang="{UI_LANG}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={CW}, height={CH}" />
    <title>{html.escape(cfg.get("title", "Reel"))}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>{FONTS}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {CW}px; height: {CH}px; overflow: hidden; background: #10141d; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
      /* background: the same footage, blurred and darkened by the canonical grade (media-treatment) */
      #bg, #bg-hold {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
      /* card: the full source frame, never upscaled */
      #card {{ position: absolute; left: {CARD["x"]}px; top: {CARD["y"]}px; width: {CARD["w"]}px; height: {CARD["h"]}px;
        border-radius: {L["radius"]}px; overflow: hidden; box-shadow: {L["shadow"]} rgba(0, 0, 0, 0.55); }}
      #cam {{ position: absolute; inset: 0; transform-origin: {cam_origin}; }}
      #base, #base-hold {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DURATION}" data-width="{CW}" data-height="{CH}">
      <video id="bg" class="clip" src="{M["bg"]}" muted playsinline
             data-start="0" data-duration="{VIDEO_D}" data-track-index="5"></video>{hold_html[0]}
      <div id="card">
        <div id="cam">
          <video id="base" class="clip" src="{M["base"]}" playsinline data-has-audio="true"
                 style="--hf-color-grading-exposure: {base_exposure}"
                 data-start="0" data-duration="{VIDEO_D}" data-track-index="0" data-volume="1"></video>{hold_html[1]}
        </div>
      </div>
{host_html}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(moves)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


# ----------------------------------------------------------------------------- write (scaffold a sibling layout project)
def scaffold(out):
    """Sibling project for another ratio: copy the project config, hard-link every referenced asset.
    No node_modules needed: package.json scripts run a pinned `npx --yes hyperframes@x.y.z`."""
    out.mkdir(parents=True, exist_ok=True)
    for name in PROJECT_FILES:
        src = MASTER / name
        if src.exists() and not (out / name).exists():
            if name in ("package.json", "meta.json"):
                data = json.loads(src.read_text())
                data["name"] = out.name
                if name == "meta.json":
                    data["id"] = out.name
                (out / name).write_text(json.dumps(data, indent=2) + "\n")
            else:
                shutil.copy2(src, out / name)
    assets = [M["base"], M["bg"], FONT_SANS, FONT_SERIF] + ([M["hold"], M["bg_hold"]] if HOLD_D else [])
    assets += [w["emoji"] for c in cues for w in c["words"] if "emoji" in w]
    for rel in dict.fromkeys(assets):
        src, dst = MASTER / rel, out / rel
        if dst.exists() and os.path.samefile(src, dst):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.unlink()
        try:
            os.link(src, dst)  # same file, no extra disk space; re-linked if the master asset was rebuilt
        except OSError:        # another volume: copy (rerun after rebuilding a master asset)
            shutil.copy2(src, dst)


if OUT != MASTER:
    scaffold(OUT)
(OUT / "index.html").write_text(page, encoding="utf-8")
comp_dir = OUT / "compositions"
comp_dir.mkdir(exist_ok=True)
for old in comp_dir.glob("*.html"):
    old.unlink()
for name, doc in files.items():
    (comp_dir / f"{name}.html").write_text(doc, encoding="utf-8")


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# SRT sidecar from the same captions (RTL lines start with RLM so players keep the paragraph direction).
# Upload it only with an uncaptioned cut: these captions are already burned in.
RLM = chr(0x200F)
srt = "\n".join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n"
                f"{RLM if direction(c['lang']) == 'rtl' else ''}{' '.join(w['t'] for w in c['words'])}\n"
                for i, c in enumerate(cues, 1))
(OUT / "captions.srt").write_text(srt, encoding="utf-8")
print(f"[{LAYOUT_NAME}] wrote {OUT.name}/index.html + {len(files)} sub-compositions ({len(cues)} cues), {CW}x{CH}, {DURATION}s, captions.srt")

# ----------------------------------------------------------------------------- canonical grades (persisted into index.html)
if not NO_GRADE:
    for selector, grading in cfg.get("grades", {}).items():
        subprocess.run(["npx", "hyperframes", "media-treatment", "--project", ".", "--file", "index.html", "--selector", selector,
                        "--grading", json.dumps(grading), "--apply", "--json"], cwd=OUT, check=True, capture_output=True)
        print(f"graded {selector}")
