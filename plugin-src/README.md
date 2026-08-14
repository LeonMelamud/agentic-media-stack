# Agentic Media Stack

A router and installer for the open-source agentic media stack. Generate video, landing pages, decks, and motion graphics from a coding agent.

**This plugin holds no copies of upstream skills.** It installs them from source and teaches the agent which to use when. Upstream stays the source of truth — when HeyGen or Browser Use or the ai-agents-skills suite ships an update, you get it with a `git pull`, not a plugin release.

## New to this? Start here

You don't need to know any of the tool names below. Just tell your agent:

> I want to make a video

The `easy-media` skill takes over: it asks what you want to make, walks you through it one
step at a time, and defaults to the free path — animated videos and slideshows need only
Node and FFmpeg, no accounts and no API keys. It works for kids too: it talks simply, and
nothing gets put online without asking first.

## What it routes to

| Ecosystem | Source | Handles |
| --- | --- | --- |
| **HyperFrames** | `heygen-com/hyperframes` | HTML to deterministic MP4. 19 skills — product launch, PR-to-video, faceless explainer, music-to-video, motion graphics, slideshow |
| **video-use** | `browser-use/video-use` | Editing existing footage. The model reads the video as text rather than watching frames |
| **ai-agents-skills** | `hoodini/ai-agents-skills` | Landing pages from video, viral shorts, design system, decks, Hebrew tooling |

## What it adds

Five skills that do not exist upstream:

- **`easy-media`** — guided beginner mode. Plain language, one question at a time, free-and-local defaults, and one guardrail: nothing goes online without asking first
- **`media-stack-setup`** — installs all three ecosystems, checks prerequisites first, handles the `--full-depth` trap that silently gives you stale skills
- **`media-pipeline`** — routing. The three ecosystems overlap superficially and are built for different jobs; choosing wrong costs a full render cycle. Includes composite multi-output pipelines, plus references for non-video websites (verified design-quality and copy skills) and RSS-triggered content automation
- **`hebrew-media-rules`** — Hebrew and RTL production rules. No upstream repo combines transcription correction, bidi text rendering, typography, and layout mirroring in one place
- **`generated-video-qa`** — mechanical validation for AI-generated talking-character video: transcribe every clip locally and diff against the script, dialogue-writing rules the voices can actually say, and character-consistency rules for multishot vs chained generation

## Install

Two commands, any machine — a brand-new Mac included:

```bash
claude plugin marketplace add LeonMelamud/agentic-media-stack
claude plugin install agentic-media-stack@media-stack
```

Then start `claude` and say:

> set up the media stack

The setup skill checks prerequisites (Node 22+, FFmpeg — offers to install what's missing),
asks which parts you need, and installs everything from upstream: the three media ecosystems
plus an optional design-and-copy pack for website work. One plugin, one conversation, full stack.

To share: this plugin ships inside a folder with a `.claude-plugin/marketplace.json` — push
that folder to GitHub and anyone installs it with `claude plugin marketplace add <you>/<repo>`.

### Prerequisites

Setup handles these, listed for reference:

- Node.js 22 or higher
- FFmpeg
- Python 3
- An ElevenLabs API key, if you want video-use transcription

## MCP servers

Bundled in `.mcp.json`, referenced rather than vendored:

| Server | Transport | Credential |
| --- | --- | --- |
| Netlify | official remote HTTP | OAuth on first use |
| Playwright | `npx`, stdio | none |
| Firecrawl | official remote HTTP | none — keyless, shared daily limits |
| Supabase | official remote HTTP, read-only | OAuth on first use |
| Magnific | official remote HTTP | OAuth on first use |

No API keys or environment variables needed. Netlify, Supabase, and Magnific ask you to sign
in the first time you use them (`/mcp` → select the server → Authenticate). Magnific covers
image generation, upscaling, retouching, AI video, TTS, and music — note its generations
spend account credits, so the ask-before-spending guardrail applies. Firecrawl works
immediately without an account; for higher limits and account tools, swap its URL to
`https://mcp.firecrawl.dev/v2/mcp-oauth` and sign in the same way.

Supabase is pinned to read-only via the `?read_only=true` query parameter. Remove it only if
you intend the agent to write to your database.

Package names and endpoints change. If a server fails to start, check the vendor's current MCP documentation rather than assuming the plugin is broken.

## What this plugin does not do

- It does not vendor upstream skills. Updates come from upstream
- It does not cover the non-skill tools in this space — Bambu Studio, Blender, and Meshy are desktop applications or hosted services, not agent skills. `references/pipelines.md` documents how they fit into a physical-product pipeline, but you drive them yourself
- It does not include API keys or accounts

## Updating

```bash
npx hyperframes skills update           # HyperFrames core set
cd ~/Developer/video-use && git pull    # video-use
```

## Credits

This plugin is a router. The work belongs to:

- **HyperFrames** — HeyGen, Apache 2.0
- **video-use** — Browser Use, MIT
- **ai-agents-skills** — Yuval Avidani, MIT

Install them directly if you would rather skip the routing layer.

## License

MIT
