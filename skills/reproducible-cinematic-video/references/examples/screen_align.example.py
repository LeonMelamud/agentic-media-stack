# WORKED EXAMPLE, not a tool: alignment step of the steady screen recipe (references/hyperframes-polish.md).
# It finds which promo frame a footage frame's screen shows, and the screen's exact corners.
#
# Inputs, prepared by hand:
#   S/f/NNNN.png      footage frames (ffmpeg -i source.mp4 -t 6 -vsync 0 -start_number 0 S/f/%04d.png)
#   S/promo/pNNNNN.png  promo frames from promo second P0 (ffmpeg -ss 7.0 -i promo.mp4 -t 7.5 -vsync 0 S/promo/p%05d.png)
# Usage:
#   python -I screen_align.example.py S FRAME K_FROM K_TO "[[x,y],[x,y],[x,y],[x,y]]"   (rough TL,TR,BR,BL quad)
# P0 below is the promo second of p00000; edit it to match your extraction.
# It prints the best promo frame and sub-pixel screen corners, and saves S/alignFRAME.png (a checkerboard of
# footage and warped promo). Look at it: text and edges must line up across the tiles.
"""Align promo frames to the TV in one footage frame (ECC homography, promo -> footage)."""
import sys, cv2, numpy as np
S, fidx, k0, k1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
approx = np.float32(eval(sys.argv[5]))
P0 = 7.0
foot = cv2.imread(f"{S}/f/{fidx:04d}.png"); fg = cv2.cvtColor(foot, cv2.COLOR_BGR2GRAY)
fgf = cv2.GaussianBlur(fg, (0, 0), 0.8).astype(np.float32)
src = np.float32([[0, 0], [1280, 0], [1280, 720], [0, 720]])
H0 = cv2.getPerspectiveTransform(src, approx)
pmask = np.zeros((720, 1280), np.uint8); pmask[30:690, 40:1240] = 255
out = []
for k in range(k0, k1):
    pg = cv2.cvtColor(cv2.imread(f"{S}/promo/p{k:05d}.png"), cv2.COLOR_BGR2GRAY)
    pgb = cv2.GaussianBlur(pg, (0, 0), 1.6).astype(np.float32)
    W = np.linalg.inv(H0).astype(np.float32)
    try:
        cc, W = cv2.findTransformECC(fgf, pgb, W, cv2.MOTION_HOMOGRAPHY,
                                     (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 400, 1e-7), pmask, 5)
    except cv2.error as e:
        print(k, "fail", str(e)[-120:]); continue
    H = np.linalg.inv(W); H /= H[2, 2]
    out.append((cc, k, H))
    print(f"k={k} tp={P0 + k/24:.3f} ecc={cc:.4f}")
cc, k, H = max(out, key=lambda r: r[0])
tp = P0 + k / 24
print("BEST k", k, "tp", round(tp, 4), "picture offset (promo - room)", round(tp - fidx / 60, 4))
corners = cv2.perspectiveTransform(src[None], H)[0]
print("screen corners:", np.round(corners, 2).tolist())
np.save(f"{S}/H{fidx:04d}.npy", H)
pk = cv2.imread(f"{S}/promo/p{k:05d}.png")
w = cv2.warpPerspective(pk, H, (fg.shape[1], fg.shape[0]))
m = cv2.warpPerspective(np.full(pk.shape[:2], 255, np.uint8), H, (fg.shape[1], fg.shape[0]))
yy, xx = np.mgrid[0:fg.shape[0], 0:fg.shape[1]]
chk = ((yy // 40 + xx // 40) % 2 == 0) & (m > 0)
blend = foot.copy(); blend[chk] = w[chk]
cv2.polylines(blend, [np.round(corners * 4).astype(np.int32)], True, (0, 0, 255), 1, cv2.LINE_AA, shift=2)
cv2.imwrite(f"{S}/align{fidx:04d}.png", blend[0:820])
