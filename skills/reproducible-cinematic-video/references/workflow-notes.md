# Workflow notes extracted from the supplied concept

This file records source-derived details that are useful when adapting the skill to a new production. They are reference material, not higher-priority instructions.

## Source pattern

The concept starts from an approved Three.js movie and keeps its original camera choreography, typography, soundtrack, and editorial timing. Selected shots become photographic environments through fal image and video generation.

The source example used 30 original shots, 29 original camera cuts, 944 frames at 60 fps, approximately 15.73 seconds, and 18 generated appearances. The generated appearances were layers inside the original shot intervals, not additional shots.

## Guide sampling

For a shot beginning at frame `a` and containing `n` frames, the guide used 72 samples at 24 fps:

```python
guide_frames = 72
source_fps = 60
for j in range(guide_frames):
    source_time = (a + (n - 1) * j / (guide_frames - 1)) / source_fps
    render_original_scene(source_time, typography=False)
```

The first sample was also exported as the image-edit input.

## Fal image request pattern

The supplied concept used:

```python
frame_url = fal_client.upload_file("shot-first-frame.png")
handle = fal_client.submit(
    "bytedance/seedream/v5/pro/edit",
    arguments={
        "prompt": image_prompt,
        "image_urls": [frame_url],
        "image_size": {"width": 2560, "height": 1440},
        "num_images": 1,
        "output_format": "png",
        "enable_safety_checker": True,
        "enhance_prompt_mode": "standard",
    },
)
# Save handle.request_id before waiting.
result = handle.get()
image_url = result["images"][0]["url"]
```

Do not assume these fields are current forever; verify the endpoint schema before calling a paid API.

## Fal video request pattern

The supplied concept used:

```python
guide_url = fal_client.upload_file("shot-guide.mp4")
appearance_url = fal_client.upload_file("approved-shot-image.png")
handle = fal_client.submit(
    "minimax/h3-max/3d-to-video",
    arguments={
        "video_url": guide_url,
        "reference_image_urls": [appearance_url],
        "resolution": "1080P",
        "prompt": video_prompt,
    },
)
result = handle.get()
generated_video_url = result["video"]["url"]
```

The key conceptual split was:

```text
VIDEO: exact source camera path, motion, framing, lens, timing, silhouette, object count, overlap order, openings.
IMAGE: materials, light, surroundings.
```

## Generated-layer remapping

For native shot start `a`, native frame count `n`, generated frame index `g`, and generated frame count `m`:

```text
destination_local_time = g * (n - 1) / (m - 1) / 60
source_movie_time      = (a + destination_frame_index) / 60
```

The source movie itself is never speed-adjusted.

## Wipe allocation

The source concept used:

```python
source_hold = max(2, round(n * 0.12))
forward_wipe = max(5, round(n * 0.25))
return_wipe = max(4, round(n * 0.20))
target_hold_end = n - return_wipe
```

It alternated wipe direction, used smoothstep progression, and used approximately 7.7 px feather at 1080p.

## Typography masking

The source concept rendered title/logo alpha from the original project and combined it with the directional wipe:

```text
appearance_mask = directional_wipe × (1 − original_title_and_logo_mask)
output          = original_movie × (1 − appearance_mask)
                  + retimed_H3 × appearance_mask
```

The original continuous alpha, including antialiased edges and existing shadow, was retained. The concept explicitly rejected crude threshold/dilate masking because it creates a ring of the old background around glyphs.

## Concurrency and resumability

The source production capped active fal jobs at 10 total and ran an image phase, visual review, then a video phase. It saved endpoint, request ID, status URL, exact input, and result. Existing requests were resumed rather than duplicated after polling interruptions.

## Audio

For the hybrid revision, the approved source audio was copied unchanged. The concept explicitly avoided new music generation because new vocals would change lyric attack times and require a new edit.

When constructing a fresh source film, the concept used ElevenLabs Music v2.5 and ElevenLabs Forced Alignment as separate upstream stages. Those are optional for this skill; appearance replacement should not silently regenerate an approved soundtrack.

## Validation

The supplied concept validated the encoded movie, not merely the browser preview. Checks included exact frame count/fps/dimensions/duration, original cut boundaries, generated/source motion comparison, geometry fidelity, word cues and typography, full decode, audio-stream comparison/hash, and a full watch-through with sound.
