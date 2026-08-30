---
name: reference-photo-image-rules
description: >
  Use when generating an image that must contain a real, specific person supplied as a photo —
  event posters, promo key visuals, banners, thumbnails with the host in them, "put me on a
  poster", "add a parrot on my shoulder", "make this photo into a flyer", "תעשה לי פוסטר עם
  התמונה שלי", "תוסיף אותי לתמונה". Also use when a generated face has drifted from the source,
  when subjects keep overlapping or will not move apart no matter how the prompt is worded, or
  when an image model rejects a prompt of a real person as unsafe.
---

# Reference Photo Image Rules

Likeness and layout failures surface only after the render, and every round spends the user's
credits. Almost all of them originate in the reference photo, not in the prompt — so fix the
reference first. Prompt force is the weakest tool available; reach for it last.

## Model naming traps

| The user says | Pass this slug |
| --- | --- |
| "Seedance image", "seedream" | `seedream-5-pro` — **Seedance is the video family**, Seedream is its image sibling |
| "Nano Banana 2" | `imagen-nano-banana-2-flash` |
| "Nano Banana Pro" | `imagen-nano-banana-2` |

Confirm with `images_models_list` before generating. Never assume a slug from the product name.

## Prepare the reference before you prompt

**Un-mirror selfies.** Front-camera photos are horizontally flipped. Feeding one in degrades
likeness and renders any shirt or badge text backwards. Check for reversed lettering in the
source; if present, `ffmpeg -i in.jpg -vf hflip out.jpg` before uploading.

**One person per reference.** A reference containing two people carries their *spatial
relationship*, and the model reproduces it faithfully — including the cheek-to-cheek overlap of
a selfie. No amount of "stand side by side, do not overlap, leave a gap between them" overrides
it. Crop the photo into one image per person and pass them as separate `image` references.

**Crop out neighbours.** A sliver of someone else's shoulder at the frame edge gets composited
into the subject. Verify each crop by viewing it, not by trusting the crop maths.

**Watch for stock watermarks.** An iStock/Getty reference can bleed its watermark into output.
Add "no watermark, no stock-photo text" and check the result.

## Escalation ladder

Work down this list. Each step costs more than the one above it — don't skip ahead, don't
linger after two failures at one step.

1. **Fresh generation**, single-person references, layout described as a *genre*
   ("symmetrical two-person studio portrait") rather than as a correction.
2. **Different model.** Likeness is model-dependent, not prompt-dependent. Seedream held
   likeness materially better than Nano Banana Pro on real faces; Nano Banana Pro is the
   stronger pick for edits and logo/brand fidelity.
3. **Mechanical composite** (below). Guarantees both geometry and likeness.

**Do not pass a previous render as an `image` reference when the change is compositional.**
It locks the layout you are trying to change. Edit-framing ("keep everything, change X") is
correct for content changes and actively counterproductive for arrangement changes.

**Two failed rounds on the same axis means the reference is wrong, not the wording.** Stop
rewriting the prompt.

## Safety-filter false positives

Image models flag prompts that ask to preserve a real person's likeness. Symptom:
`NSFW: Content detected` on an entirely benign brief.

Fixes, in order: drop phrasing like "preserve their exact facial likeness" in favour of "the man
from the first reference photo"; use single-person crops rather than a group photo; reframe as a
photo edit; switch model. Report the flag to the user as a filter false positive — don't silently
retry the same wording.

## Text and logos

- **Never let the model render Hebrew or any RTL text.** Leave clean negative space and
  composite the type afterwards. **REQUIRED:** read `hebrew-media-rules` first.
- Large Latin wordmarks (an `aws` lockup) often render correctly. Small brand text on clothing
  reliably garbles — "HUGO BOSS" came back as "MURO BOSA". Prompt "no lettering on clothing".
- For anything going to print, composite the real logo SVG rather than shipping the generated one.
- Ask which logos are actually wanted. A reference poster may carry only one brand even when the
  user names two.

## Mechanical composite — the guaranteed path

Faces are the user's real pixels, so they cannot drift, and spacing is exact. This is how event
posters are genuinely made, so it is not a downgrade.

1. `images_remove_background` on each single-person crop and on the prop/animal.
2. Generate a **people-free background plate** — no likeness risk, so any model and any wording.
3. Composite with PIL at final canvas size. Scale each cutout so **head heights match and
   eye-lines are level** — cutouts are rarely the same scale. Leave a deliberate gap of visible
   background between subjects.
4. Harmonize with `images_relight` or a local grade. **Do not run the composite back through
   `images_generate` for polish** — that regenerates the faces and reintroduces the exact drift
   you just eliminated.

Trade-off to state plainly: a slightly more "pasted" look, in exchange for exact faces.

## Verification — look at the actual image

Download and open every render before presenting it. Check: likeness against the source crops;
subjects genuinely separated at the same depth and scale; no garbled lettering; no watermark;
requested logos present and undistorted; negative space still clear for type.

Name the specific failure when one fails. Do not describe a render you have not viewed.

## Credits and batching

Generations spend the user's account credits. Ask before the first spend, use `count: N` in a
single call for variants rather than N calls, and prefer a cheap model for layout exploration
before committing to a final pass.

## Common mistakes

| Mistake | Reality |
| --- | --- |
| Re-wording the prompt after a layout failure | The pose lives in the reference. Split or re-crop it. |
| Using the last render as the reference for a layout change | Locks the composition you want changed. |
| Passing a selfie as-is | It is mirrored. Likeness suffers and text reads backwards. |
| Assuming "seedance" means the image model | Seedance is video. Seedream is the image sibling. |
| Retrying verbatim after an NSFW flag | It is a likeness-preservation false positive. Change the wording or the model. |
| Letting the model set Hebrew type | It garbles. Composite type afterwards. |
| Presenting a render you only read the URL of | Open it. Models place text over faces and clip subjects at the edge. |
