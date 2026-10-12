#!/usr/bin/env python3
"""Check a finished delivery MP4 (from social_render.py or a HyperFrames render) against its source.

Usage:
    python -I check_delivery.py FINAL.mp4 --source SOURCE.mp4 [--size 1080x1920] [--fps 30] [--extra 1.5]
                                [--motion 0-5.5] [--frames 1.6,12,30] [--out review/] [--cover 1.6]

Checks: size, frame rate, duration (source + --extra seconds, e.g. a held closing frame), H.264 High,
yuv420p, BT.709 tag (untagged = WARN), faststart (moov before mdat), full decode, audio present, and audio
sync against the source by cross-correlation over the whole overlap (works when the audio was re-encoded,
e.g. by HyperFrames, where an MD5 check cannot). --motion reports the mean/max camera shift per frame in a
window (phase correlation on the downscaled picture); a steady shot is about 0.1 px. --frames writes
full-resolution frames from the encoded file to --out: look at them, a passing check is not a review.
--cover T writes <final>-cover.jpg next to the final file. Exit code 1 on any FAIL.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,profile,width,height,pix_fmt,color_primaries,r_frame_rate,sample_rate"
                          ":format=duration,bit_rate,size", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def mono(path, seconds, rate=8000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-t", str(seconds), "-ac", "1", "-ar", str(rate),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def audio_offset(final, source, seconds, rate=8000):
    a, b = mono(source, seconds, rate), mono(final, seconds, rate)
    n = min(len(a), len(b))
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    size = 1 << int(np.ceil(np.log2(2 * n)))
    c = np.fft.irfft(np.fft.rfft(a, size) * np.conj(np.fft.rfft(b, size)), size)
    lag = int(np.argmax(c))
    lag = lag - size if lag > size // 2 else lag
    corr = float(np.dot(a, b) / np.sqrt(np.dot(a, a) * np.dot(b, b)))
    return lag * 1000.0 / rate, corr


def motion(final, t0, t1, width, height):
    import cv2
    w = 270
    h = int(round(w * height / width / 2)) * 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-i", str(final), "-t", str(t1 - t0),
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    shifts = np.array([np.hypot(*cv2.phaseCorrelate(f[i], f[i + 1])[0]) for i in range(len(f) - 1)])
    return float(shifts.mean()), float(shifts.max())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("final")
    ap.add_argument("--source", required=True)
    ap.add_argument("--size", help="expected WxH, e.g. 1080x1920")
    ap.add_argument("--fps", help="expected frame rate, e.g. 30")
    ap.add_argument("--extra", type=float, default=0.0, help="seconds the final may run past the source (held end frame)")
    ap.add_argument("--cover", help="time of the cover frame; writes <final>-cover.jpg")
    ap.add_argument("--motion", help="window START-END in seconds to measure camera motion")
    ap.add_argument("--frames", help="comma-separated times to export as PNG")
    ap.add_argument("--out", default="review")
    a = ap.parse_args()
    final = Path(a.final)
    info = probe(final)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    aud = [s for s in info["streams"] if s["codec_type"] == "audio"]
    results = []

    def check(name, ok, detail="", warn=False):
        results.append({"check": name, "ok": bool(ok), "warn": warn, "detail": str(detail)})

    src = probe(a.source)
    src_dur = float(src["format"]["duration"])
    dur = float(info["format"]["duration"])
    num, den = (int(x) for x in v["r_frame_rate"].split("/"))
    fps = num / den

    if a.size:
        check("size", f'{v["width"]}x{v["height"]}' == a.size, f'{v["width"]}x{v["height"]}')
    if a.fps:
        check("fps", abs(fps - float(a.fps)) < 0.01, f"{fps:.3f}")
    want = src_dur + a.extra
    check("duration", abs(dur - want) <= 2 / fps, f"{dur:.3f}s, expected {want:.3f}s (source {src_dur:.3f} + {a.extra})")
    check("h264_high", v["codec_name"] == "h264" and v.get("profile") == "High", f'{v["codec_name"]} {v.get("profile")}')
    check("yuv420p", v.get("pix_fmt") == "yuv420p", v.get("pix_fmt"))
    prim = v.get("color_primaries")
    if prim is None:
        check("bt709", True, "untagged: players will guess; tag bt709 when encoding", warn=True)
    else:
        check("bt709", prim == "bt709", prim)
    head = final.read_bytes()
    check("faststart_moov_before_mdat", 0 <= head.find(b"moov") < head.find(b"mdat"))
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"], capture_output=True, text=True)
    check("full_decode_clean", dec.returncode == 0 and not dec.stderr.strip(), dec.stderr.strip()[:200])
    check("audio_present", bool(aud), aud[0]["codec_name"] if aud else "none")
    if aud:
        off, corr = audio_offset(final, a.source, min(src_dur, dur, 180))
        check("audio_sync_vs_source", abs(off) <= 20 and corr > 0.9, f"offset {off:.1f} ms, corr {corr:.4f}")
    if a.motion:
        t0, t1 = (float(x) for x in a.motion.split("-"))
        mean, peak = motion(final, t0, t1, v["width"], v["height"])
        check("motion_window", True, f"{t0}-{t1}s: mean {mean:.2f} px/frame, max {peak:.2f} (steady ~0.1)")
    if a.frames:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        for t in a.frames.split(","):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", t, "-i", str(final), "-frames:v", "1",
                            str(out / f"{final.stem}-{float(t):06.2f}s.png")], check=True)
        check("frames_written", True, f"{len(a.frames.split(','))} PNG in {out}")
    if a.cover:
        cover = final.with_name(f"{final.stem}-cover.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", a.cover, "-i", str(final), "-frames:v", "1", "-q:v", "2",
                        str(cover)], check=True)
        check("cover_written", True, cover.name)
    print(f"{final.name}: {v['width']}x{v['height']} {v['r_frame_rate']} fps, {dur:.2f}s, "
          f"{int(info['format']['size']) / 1e6:.1f} MB, {int(info['format']['bit_rate']) / 1e6:.1f} Mbps")
    for r in results:
        status = "FAIL" if not r["ok"] else ("WARN" if r["warn"] else "PASS")
        print(f"  {status}  {r['check']:28s} {r['detail']}")
    sys.exit(0 if all(r["ok"] for r in results) else 1)


if __name__ == "__main__":
    main()
