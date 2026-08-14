---
name: media-stack-setup
description: >
  Installs the open-source agentic media stack from upstream sources. Use when the user says
  "set up the media stack", "install hyperframes", "install video-use", "install the video skills",
  "התקן את הסטאק", "התקן hyperframes", or asks to make video/landing-page generation available.
  Also use when another skill in this plugin reports that a required upstream skill is missing.
---

# Media Stack Setup

Install the three upstream skill ecosystems this plugin routes to. This plugin deliberately does **not** vendor copies of them — upstream stays the source of truth. Install from upstream, verify, report.

## Before installing

Check prerequisites and report which are missing before running anything:

```bash
node --version      # must be 22 or higher
ffmpeg -version     # required by all three ecosystems
python3 --version   # required by video-use and the ai-agents-skills suite
```

If Node is below 22, stop and tell the user — HyperFrames will fail at render, not at install, which wastes their time.

Install missing prerequisites per platform:

- macOS: `brew install node ffmpeg`
- Debian/Ubuntu: `sudo apt install nodejs ffmpeg`
- Windows: recommend WSL or Git Bash; `winget install FFmpeg`

## Ask before installing

Do not install all three unless the user asked for everything. Ask which they need:

| Ecosystem | Install when the user wants |
| --- | --- |
| HyperFrames | Rendering video from HTML, motion graphics, decks, PR-to-video |
| video-use | Editing existing footage — cutting filler words, captions, color grade |
| ai-agents-skills | Landing pages from video, Hebrew/RTL work, viral shorts, design system |
| Design & copy pack | Websites that look designed — typography, taste, motion, copywriting |

## 1. HyperFrames (HeyGen)

```bash
npx skills add heygen-com/hyperframes --full-depth --yes
```

**The `--full-depth` flag is mandatory.** Without it, `skills add` fetches the skills.sh registry blob, which lags `main` by hours — the user silently gets an older copy of a skill and then reports bugs that were already fixed upstream.

Default to the core set. Do not install all 19 skills up front — the `/hyperframes` router pulls each creation workflow on demand via `npx hyperframes skills update <workflow>`. Only pass `--all` if the user explicitly wants everything offline.

Verify:
```bash
npx hyperframes doctor
```

## 2. video-use (Browser Use)

```bash
git clone https://github.com/browser-use/video-use ~/Developer/video-use
ln -sfn ~/Developer/video-use ~/.claude/skills/video-use
cd ~/Developer/video-use && uv sync    # or: pip install -e .
```

For Codex, symlink to `~/.codex/skills/video-use` instead.

video-use needs an ElevenLabs API key for Scribe transcription (word-level timestamps and speaker diarization). Ask the user to paste one — do not proceed silently without it, and never write it anywhere except `.env`:

```bash
cd ~/Developer/video-use && cp .env.example .env
# then set ELEVENLABS_API_KEY in .env
```

Keys are at elevenlabs.io/app/settings/api-keys.

Optional but recommended: `brew install yt-dlp` for pulling online sources.

**Do not transcribe anything during setup.** Report that the stack is ready and wait for the user to drop footage into a folder.

## 3. ai-agents-skills (Yuval Avidani)

Full install — also wires ffmpeg, Node, Python, faster-whisper, and the hyperframes CLI:

```bash
curl -sSL https://raw.githubusercontent.com/hoodini/ai-agents-skills/master/install.sh | bash
```

Selective install, when the user wants one thing:

```bash
npx skills add hoodini/ai-agents-skills --skill <name> --agent claude-code
```

Before piping any install script to bash, tell the user what the script does and offer to show it first with `curl -sSL <url> | less`. Some users and most corporate environments require reviewing it.

## 4. Design & copy pack (optional)

The website quality layer documented in `media-pipeline/references/web-and-content.md`.
Install when the user wants sites and pages that look designed, not just generated:

```bash
npx skills add pbakaus/impeccable
npx skills add Leonxlnx/taste-skill
npx skills add nextlevelbuilder/ui-ux-pro-max-skill
npx skills add emilkowalski/skills
npx skills add greensock/gsap-skills
npx skills add coreyhaines31/marketingskills
npx skills add blader/humanizer
npx skills add charlie947/social-media-skills
```

Skip any the user already has. Some of these ship as Claude Code plugins rather than skills —
if `skills add` finds nothing to install for a repo, follow that repo's README instead of
guessing. Report which of the eight landed and which need the README route.

## After install

Report a short table of what installed, what version, and what is still missing. Then point the user at the `media-pipeline` skill to choose a workflow — do not start producing anything unprompted.

## Updating

Upstream moves fast. To refresh without reinstalling:

```bash
npx hyperframes skills update           # HyperFrames core set
cd ~/Developer/video-use && git pull    # video-use
```

This plugin holds no copies, so updating upstream updates everything this plugin routes to.
