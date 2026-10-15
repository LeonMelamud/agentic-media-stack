# Third-party code

## instagram-agent-skill

Five skills in `skills/` are adapted from
[instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)
by Jake Schincariol, at commit `d03c56bb598be770c60b201f94237e5d1a4268a6`
(2026-09-13, version 1.0.0):

| Skill | Upstream path |
| --- | --- |
| `ig-reel` | `skills/ig-reel/` (SKILL.md, hooks.json, hookscore.py, beats.py) |
| `ig-caption` | `skills/ig-caption/` (SKILL.md, caption.py) |
| `ig-human` | `skills/ig-human/` (SKILL.md, humanize.py, detect.py, slop.json) |
| `ig-carousel` | `skills/ig-carousel/SKILL.md` |
| `ig-repurpose` | `skills/ig-repurpose/SKILL.md` |

The other eight skills in that pack (account and community work, not media)
are not copied. Install the `instagram-agent`
plugin itself for them.

### What changed here (2026-10-14)

- **Hebrew in the tools.**
  - Every tool now detects Hebrew text (more Hebrew letters than Latin) and counts Hebrew words.
  - `hookscore.py`:
    - Scores Hebrew on LENGTH (4-9 words), SPECIFICITY (digits and spoken Hebrew numbers) and FRONTLOAD.
    - Reports STAKES and ADDRESS as n/a.
  - `beats.py`:
    - Times Hebrew at a measured 130 words per minute.
    - Matches a loop word through Hebrew prefixes, and reports a shared root as a possible loop.
  - `caption.py`:
    - Counts Hebrew hashtags.
    - Recognises common Hebrew asks.
  - `humanize.py` and `detect.py`:
    - Keep and ignore direction marks (LRM, RLM, ALM) in RTL text.
    - `detect.py` reports its two English-lexicon checks as n/a on Hebrew.
- **English behaviour is unchanged.** `tests/ig/` compares every tool's JSON output on English fixtures with output recorded from the upstream commit before any change.
- **SKILL.md:**
  - Hebrew sections and trigger phrases.
  - `ig-carousel` points at `hebrew-media-rules`.
  - `ig-repurpose` routes the cutting to `media-pipeline` and adds the Hebrew transcript rule.
  - The `ig-reel` safe zone now points at this plugin's `social-delivery.md`.
  - Links to the ten skills that are not copied are marked optional.
  - Dollar amounts in `ig-reel` and `ig-carousel` are written out: in Claude Code, `$4,200` in a skill body is read as an argument placeholder when the skill is invoked with arguments.

Upstream changes are not pulled automatically. To update, diff the upstream
skill folders against these, and re-run `python3 -m unittest discover -s tests/ig`.

### Licence

MIT License

Copyright (c) 2026 Jake Schincariol

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
