# Composite Pipelines

Multi-output workflows. Each assumes the stack is installed via `media-stack-setup`.

---

## 1. Content machine — one source, seven outputs

The highest-ROI pipeline in the stack. One recorded asset becomes an entire content cycle.

```
Source: talk / podcast / PR / long-form post
   │
   ├─ video-use            → the cut itself (filler words, dead space, self-eval)
   │                          ↳ spawns HyperFrames sub-agents for overlays
   ├─ /talking-head-recut  → packaged version with lower-thirds and callouts
   ├─ /embedded-captions   → burned captions
   ├─ yuv-viral-video      → 5 shorts, 9:16 and 16:9
   ├─ /motion-graphics     → 3 reusable transparent overlays
   ├─ parallax-landing     → landing page
   └─ /slideshow           → interactive deck with branching
```

Run through a single `frame.md` so every output shares brand identity. Render variants in parallel on Lambda. Schedule with any workflow orchestrator.

**Order matters:** produce the cut first. Everything downstream derives from the edited timeline, not the raw footage.

---

## 2. Changelog automation

```
GitHub PR merged to main
   → GitHub Action triggers agent
   → /pr-to-video reads the PR via gh CLI
   → renders changelog video with animated diff
   → publishes
```

Almost nobody runs this. It turns release notes into a video channel with zero marginal effort per release.

Keep videos under 60 seconds. A changelog video nobody finishes is worse than a text changelog.

---

## 3. Site to video and back

```
Client URL → /product-launch-video → promo video
promo video → cinematic-scrub-landing → new landing page
```

A closed loop. Useful for agencies: a prospect's existing site becomes a pitch asset before the first meeting.

---

## 4. Physical product pipeline

The image-to-object chain, when the deliverable is a physical good:

```
gpt-image-2 or Gemini 3 Pro Image  → product design
   → Meshy                          → image to 3D mesh
   → Blender (Python)               → scripted geometry corrections
   → Bambu Studio                   → slicing and printing
   → vision-model QA                → quality gate before shipping
   → model-viewer                   → interactive 3D on the product page
```

**Print time, not cost, is the bottleneck.** One printer produces two to three units a day. Model the queue before promising delivery dates.

Insert a vision QA gate between generation and production. A model that looks at the render and approves it cuts waste dramatically, and it is the step most pipelines skip.

---

## 5. frame.md — brand consistency across every output

Every brand has a `design.md`. None were written for a camera.

`frame.md` is the translation layer: the same tokens and rules, rewritten so an agent can compose video without guessing at scale or reaching for web chrome. The output is a `DESIGN.md` superset the whole toolchain reads.

Create one before the first render on any project that will produce more than a single video. Templates: hyperframes.dev/design

Without it, every render is a fresh negotiation about brand.

---

## 6. Media as a managed resource

The `/media-use` skill is not a generator — it resolves a media need (BGM, SFX, image, icon, logo, voice, color grade, LUT) into a frozen local file plus a ledger record.

It searches the catalog first and generates only on a miss, tracks provenance in a manifest, and reuses assets across projects.

Route media requests through it rather than generating fresh assets each time. That is the difference between a pipeline that regenerates forever and a brand library that compounds.
