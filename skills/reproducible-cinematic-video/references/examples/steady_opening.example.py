# WORKED EXAMPLE, not a tool: render step of the steady screen recipe (references/hyperframes-polish.md),
# exactly as used for one 810x1440 60 fps phone clip of a room with two TVs playing the user's promo.
# Every constant below (PLATE_FRAME, CUT_FRAME, offsets, corners) is pinned to that clip. Re-derive them for new
# footage with screen_align.example.py and the measurements described in the recipe, then adapt the paths.
#!/usr/bin/env python3
"""Steady opening: replace the camera swing between the two TVs (0 - 5.53 s) with one locked-off shot.

In the source, the phone swings between two TVs that play the same promo (final_hero_opener_V14) until the
camera settles on the speaker at CUT_FRAME. We keep one sharp frame of the room (PLATE_FRAME, where the right
TV is fully in view) and play the original promo on its screens:
  - placement: screen corners found by ECC alignment of promo frames to the TV picture (frames 204 and 100);
  - timing: in the room the TV picture ran ~0.5 s ahead of the sound (PICTURE_OFFSET, used to fit against the
    plate). The new screen plays at SCREEN_OFFSET, locked to the audio, so the on-screen text lands with the
    voice and the captions;
  - look: denoise, then per-channel distribution matching and softness, fitted from the promo to the TV
    as the phone saw it in the plate frame, plus a smooth reflection layer.
The audio stream is copied untouched. From CUT_FRAME on, the video is the source, re-encoded.

Colour: frames are decoded/encoded with exact BT.709 limited-range math here, because ffmpeg's default
yuv->rgb decode is ~2 levels darker than its encode and would shift the opening against the rest.

Writes assets/source-steady.mp4 and assets/bg-steady.mp4 (the blurred-backdrop feed, rebuilt from it).
assets/source.mp4 stays the untouched original.
"""
import subprocess
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets/source.mp4"
PROMO = ROOT / "assets/promo/final_hero_opener_V14.mp4"
OUT = ROOT / "assets/source-steady.mp4"
BG = ROOT / "assets/bg-steady.mp4"
W, H, FPS = 810, 1440, 60
PW, PH, PFPS = 1280, 720, 24
PLATE_FRAME = 204          # 3.40 s: sharpest frame with the right TV fully in view
CUT_FRAME = 332            # 5.533 s: camera has settled on the speaker
PICTURE_OFFSET = 8.383     # promo time the room TV showed = room time + offset (pinned by frames 100 and 204)
SCREEN_OFFSET = 7.865      # promo time heard in the room audio = room time + offset (audio cross-correlation)
SOFTNESS = 0.9             # px blur so the screen matches the phone's optics
GRAIN = 0.3                # luma grain (8-bit levels) so the locked-off plate does not look frozen
PROMO_RECT = np.float32([[0, 0], [PW, 0], [PW, PH], [0, PH]])
# screen corners (TL, TR, BR, BL) in source pixels, from ECC alignment (frame 100 only pinned PICTURE_OFFSET)
RIGHT_204 = np.float32([[204.85, 149.77], [749.92, 345.75], [757.32, 746.86], [207.39, 710.82]])
RIGHT_100 = np.float32([[314.40, 148.55], [862.24, 344.74], [868.61, 745.65], [319.14, 710.65]])
# left TV: only a strip is in frame; wall-plane extrapolation of the right screen, right edge snapped to the bezel
LEFT_204 = np.float32([[-1257.4, -355.7], [145.0, 129.0], [143.0, 697.0], [-1290.5, 633.8]])


def read_yuv_frames(path, w, h, first, count):
    """Raw yuv420p frames [first, first+count) without any colour conversion."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select='between(n,{first},{first + count - 1})'",
           "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"]
    buf = subprocess.run(cmd, capture_output=True, check=True).stdout
    size = w * h * 3 // 2
    assert len(buf) == size * count, (path, first, count, len(buf))
    return [buf[i * size:(i + 1) * size] for i in range(count)]


def yuv_to_bgr(buf, w, h):
    y = np.frombuffer(buf[:w * h], np.uint8).reshape(h, w).astype(np.float32)
    u = np.frombuffer(buf[w * h:w * h * 5 // 4], np.uint8).reshape(h // 2, w // 2).astype(np.float32)
    v = np.frombuffer(buf[w * h * 5 // 4:], np.uint8).reshape(h // 2, w // 2).astype(np.float32)
    u = (cv2.resize(u, (w, h), interpolation=cv2.INTER_LINEAR) - 128) * (255 / 224)
    v = (cv2.resize(v, (w, h), interpolation=cv2.INTER_LINEAR) - 128) * (255 / 224)
    y = (y - 16) * (255 / 219)
    return np.stack([y + 1.8556 * u, y - 0.1873 * u - 0.4681 * v, y + 1.5748 * v], -1)


def bgr_to_yuv(bgr):
    b, g, r = bgr[..., 0], bgr[..., 1], bgr[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    u = (b - y) / 1.8556
    v = (r - y) / 1.5748
    sub = lambda c: cv2.resize(c, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    Y = np.clip(16 + y * (219 / 255), 0, 255)
    U = np.clip(128 + sub(u) * (224 / 255), 0, 255)
    V = np.clip(128 + sub(v) * (224 / 255), 0, 255)
    return b"".join(np.round(p).astype(np.uint8).tobytes() for p in (Y, U, V))


def promo_index(t, offset=SCREEN_OFFSET):
    return int(np.floor((t + offset) * PFPS + 1e-6))


class QuantileMap:
    """promo BGR -> TV-as-seen-by-the-phone BGR, by matching each channel's distribution over the aligned screen.

    Distribution matching, not regression: least squares on not-quite-aligned samples shrinks contrast and
    saturation (the screen came out flat and washed), and a free polynomial bent below black and amplified grain.
    Quantile maps are monotonic by construction."""

    def __init__(self, promo_px, foot_px, n=513):
        qs = np.linspace(0, 1, n)
        self.luts = []
        for c in range(3):
            src = np.quantile(promo_px[:, c], qs) + np.arange(n) * 1e-6   # strictly increasing for interp
            self.luts.append((src, np.quantile(foot_px[:, c], qs)))

    def __call__(self, img):
        return np.stack([np.interp(img[..., c], *self.luts[c]) for c in range(3)], -1).astype(np.float32)


def denoise(img):
    """The phone's processing smoothed the promo's film grain away; do the same before mapping."""
    return cv2.fastNlMeansDenoisingColored(np.clip(img, 0, 255).astype(np.uint8), None, 5, 5, 7, 21).astype(np.float32)


def fit_color(foot, promo, corners):
    Hm = cv2.getPerspectiveTransform(PROMO_RECT, corners)
    inner = np.zeros((PH, PW), np.uint8)
    inner[40:PH - 40, 50:PW - 50] = 255
    m = cv2.warpPerspective(inner, Hm, (W, H), flags=cv2.INTER_NEAREST) > 0
    m[:, W - 5:] = False
    warped = cv2.GaussianBlur(cv2.warpPerspective(promo, Hm, (W, H)), (0, 0), 1.4)  # the phone's optics
    return QuantileMap(warped[m], foot[m])


def fit_glare(foot, mapped_promo, corners):
    """Smooth additive layer in screen space: the room reflecting on the glossy screen, lighter toward its near
    (left) edge. A low-order 2D polynomial of the residual between the TV as filmed and the mapped promo."""
    Hm = cv2.getPerspectiveTransform(PROMO_RECT, corners)
    inner = np.zeros((PH, PW), np.uint8)
    inner[80:PH - 80, 90:PW - 90] = 255
    m = cv2.warpPerspective(inner, Hm, (W, H), flags=cv2.INTER_NEAREST) > 0
    warped = cv2.GaussianBlur(cv2.warpPerspective(mapped_promo, Hm, (W, H)), (0, 0), 1.4)
    resid = cv2.GaussianBlur(foot, (0, 0), 8) - cv2.GaussianBlur(warped, (0, 0), 8)
    yy, xx = np.nonzero(m)
    pick = np.random.default_rng(1).choice(len(yy), min(30000, len(yy)), replace=False)
    yy, xx = yy[pick], xx[pick]
    uv = cv2.perspectiveTransform(np.float32(np.stack([xx, yy], 1))[None], np.linalg.inv(Hm))[0] / np.float32([PW, PH])
    basis = lambda u, v: np.stack([np.ones_like(u), u, v, u * u, u * v, v * v], -1)
    coef, *_ = np.linalg.lstsq(basis(uv[:, 0], uv[:, 1]).astype(np.float64), resid[yy, xx].astype(np.float64), rcond=None)
    gv, gu = np.mgrid[0:PH // 2, 0:PW // 2]
    glare = basis((gu + 0.5) / (PW // 2), (gv + 0.5) / (PH // 2)) @ coef
    print(f"screen reflection layer: range per channel (BGR) {glare.min((0, 1)).round(1)} .. {glare.max((0, 1)).round(1)}")
    return glare.astype(np.float32)


def main():
    plate = yuv_to_bgr(read_yuv_frames(SRC, W, H, PLATE_FRAME, 1)[0], W, H)
    k_lo = min(promo_index(0), promo_index(PLATE_FRAME / FPS, PICTURE_OFFSET))
    k_hi = max(promo_index((CUT_FRAME - 1) / FPS), promo_index(PLATE_FRAME / FPS, PICTURE_OFFSET))
    promo_bufs = dict(zip(range(k_lo, k_hi + 1), read_yuv_frames(PROMO, PW, PH, k_lo, k_hi - k_lo + 1)))
    promo = lambda k: yuv_to_bgr(promo_bufs[k], PW, PH)

    # fitted on the plate frame only: the phone's auto-exposure drifts between frames, and the plate's wall is
    # what the screen has to sit in
    cmap = fit_color(plate, denoise(promo(promo_index(PLATE_FRAME / FPS, PICTURE_OFFSET))), RIGHT_204)

    # screens: promo (pre-shrunk to half size, colour-mapped) warped into the plate
    S2 = np.diag([2.0, 2.0, 1.0]).astype(np.float64)
    screens = []
    for corners in (RIGHT_204, LEFT_204):
        Hm = cv2.getPerspectiveTransform(PROMO_RECT, corners).astype(np.float64) @ S2
        alpha = cv2.warpPerspective(np.ones((PH // 2, PW // 2), np.float32), Hm, (W, H), flags=cv2.INTER_LINEAR)
        screens.append((Hm, alpha[..., None]))
    mapped = {}
    for k in promo_bufs:
        mapped[k] = cmap(cv2.resize(denoise(promo(k)), (PW // 2, PH // 2), interpolation=cv2.INTER_AREA))

    k_plate = promo_index(PLATE_FRAME / FPS, PICTURE_OFFSET)   # what the plate's TV shows
    glare = fit_glare(plate, cv2.resize(mapped[k_plate], (PW, PH), interpolation=cv2.INTER_LINEAR), RIGHT_204)

    # the left strip is seen at a steeper angle: match its brightness to the plate separately
    Hl, al = screens[1]
    strip = (al[..., 0] > 0.99)
    strip[:, 150:] = False
    strip[:140, :] = False
    strip[690:, :] = False
    warped = cv2.GaussianBlur(cv2.warpPerspective(mapped[k_plate], Hl, (W, H)), (0, 0), 3)
    gain = np.clip(cv2.GaussianBlur(plate, (0, 0), 3)[strip].mean(0) / np.maximum(warped[strip].mean(0), 1), 0.75, 1.3)
    print(f"left strip gain (BGR) {gain.round(3)}")
    gains = [np.ones(3, np.float32), gain.astype(np.float32)]
    adds = [glare, np.zeros_like(glare)]

    tags = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", str(SRC),
         "-filter_complex", f"[1:v]trim=start_frame={CUT_FRAME},setpts=PTS-STARTPTS[rest];"
                            f"[0:v]setpts=PTS-STARTPTS[open];[open][rest]concat=n=2:v=1:a=0[v]",
         "-map", "[v]", "-map", "1:a", "-c:a", "copy",
         "-c:v", "libx264", "-preset", "slow", "-crf", "10", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
         *tags, "-movflags", "+faststart", str(OUT)], stdin=subprocess.PIPE)
    for n in range(CUT_FRAME):
        k = promo_index(n / FPS)
        frame = plate.copy()
        for (Hm, alpha), g, add in zip(screens, gains, adds):
            scr = cv2.warpPerspective(np.clip(mapped[k] * g + add, 0, 255), Hm, (W, H), flags=cv2.INTER_LINEAR)
            scr = cv2.GaussianBlur(scr, (0, 0), SOFTNESS)
            frame = frame * (1 - alpha) + scr * alpha
        frame += np.random.default_rng(n).normal(0, GRAIN, (H, W, 1)).astype(np.float32)
        enc.stdin.write(bgr_to_yuv(np.clip(frame, 0, 255)))
    enc.stdin.close()
    assert enc.wait() == 0, "encode failed"
    print(f"wrote {OUT.relative_to(ROOT)} (steady 0-{CUT_FRAME / FPS:.3f}s)")

    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT), "-vf", "scale=540:960:flags=area,fps=30", "-an",
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", *tags, "-movflags", "+faststart", str(BG)],
                   check=True)
    print(f"wrote {BG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
