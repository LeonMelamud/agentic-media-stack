# Agentic Media Stack

![Agentic Media Stack](assets/banner.jpg)

A Claude Code plugin that turns your coding agent into a media production studio —
video, landing pages, decks, and motion graphics, with the agent doing the work
and **checking its own work** before showing you anything.

## Install

**Claude Code — two commands:**

```bash
claude plugin marketplace add LeonMelamud/agentic-media-stack
claude plugin install agentic-media-stack@media-stack
```

Then start `claude` and say:

> set up the media stack

**Using Claude Cowork or Claude Desktop instead?** Install the Cowork edition:
**[agentic-media-stack-cowork](https://github.com/LeonMelamud/agentic-media-stack-cowork)** —
same domain knowledge, rewritten for hosted generation with no terminal, no ffmpeg and nothing
to install. The skills in *this* repo drive local tools (`npx`, `ffmpeg`, Whisper, git), so in
Cowork their first instruction is one you cannot follow.

This repo's ZIP still uploads in Desktop (Settings → Cowork → Plugins → **Upload plugin**,
`.zip` unpacked — Hebrew walkthrough: [INSTALL-he.md](INSTALL-he.md)) if you deliberately want
the CLI-shaped skills there.

New to all this? Just say **"I want to make a video"** — the guided beginner mode
takes over, asks one question at a time, and defaults to free, local tools.
It's safe for kids: nothing goes online without asking first.

## What makes it different: the agent validates its own output

AI-generated video fails in ways you can't see in a thumbnail: a voice says
"Claws" instead of "Claude", a magic wand drifts into a power drill between
shots, dead air gets filled with invented gibberish speech. The
`generated-video-qa` skill makes validation mechanical:

- **Transcribe every clip locally** (Whisper) and diff against the script —
  the ear misses what the transcript catches
- Dialogue-writing rules the voices can actually say
- Character-consistency rules: multishot in one generation beats chaining
- Logos and titles are never model-drawn — always overlaid locally, pixel-perfect

## What's inside

| Skill | What it does |
| --- | --- |
| `easy-media` | Guided beginner mode — plain language, free-and-local defaults, kid-safe |
| `media-pipeline` | Routes each job to the right ecosystem; choosing wrong costs a render cycle |
| `media-stack-setup` | Installs the three upstream ecosystems, checks prerequisites first |
| `generated-video-qa` | Transcribe-and-diff validation for AI-generated talking-character video |
| `hebrew-media-rules` | Hebrew/RTL production: transcription correction, bidi text, mirrored layout |
| `reference-photo-image-rules` | Putting a real person from a photo into a generated image without likeness or layout drift |
| `hosted-video-generation` | Hosted video models: which model, cost discipline, smooth motion |
| `reproducible-cinematic-video` | Finished footage into platform versions (Reels, 4:5 for LinkedIn/Facebook, X): zoom-out framing, karaoke Hebrew captions, hook and closing line, a steady opening, delivery checks |

## What it routes to

| Ecosystem | Source | Handles |
| --- | --- | --- |
| **HyperFrames** | `heygen-com/hyperframes` | HTML → deterministic MP4: product launch, explainers, motion graphics, slideshows |
| **video-use** | `browser-use/video-use` | Editing existing footage — the model reads video as text |
| **ai-agents-skills** | `hoodini/ai-agents-skills` | Landing pages from video, viral shorts, decks, Hebrew tooling |

Plus bundled MCP servers (image/video/voice/music generation, browser control,
scraping, deploys) — see [`PLUGIN.md`](PLUGIN.md) for the
full documentation, prerequisites, and design notes.

**This plugin holds no copies of upstream skills.** It installs them from source;
upstream stays the source of truth.

## License

MIT — see [LICENSE](LICENSE).
