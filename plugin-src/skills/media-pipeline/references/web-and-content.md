# Websites and Content Automation

What to reach for when the request goes beyond the video-driven landing pages in the routing
table. This plugin stays a router: everything here is a pointer to upstream, not a bundled copy.

---

## Websites that are not video-driven

Site generation itself is outside this plugin's core. What the stack contributes:

| The user wants | Path |
| --- | --- |
| A landing page driven by video | The three mechanics in the routing table — this is the plugin's home turf |
| A static site or simple landing page | Author it directly; apply the design-quality layer below; deploy with the bundled **Netlify MCP** |
| A store | WordPress + ACF + WooCommerce is the proven no-code-owner path. The agent scaffolds; the owner runs it. Payments and hosting are accounts the user opens, not skills |
| An app or dashboard | Next.js. Outside this plugin — route to whatever web-dev skills the user has installed |

## The design-quality layer

The generated pages work; these make them look designed. Verified third-party skills worth
recommending when the user cares how the site looks. Install with `npx skills add <owner>/<repo>`
or per each repo's README — some ship as plugins rather than skills.

| Skill | Repo | Adds |
| --- | --- | --- |
| Impeccable | `pbakaus/impeccable` | Full design language: critique, hierarchy, typography, accessibility, motion |
| Taste Skill | `Leonxlnx/taste-skill` | Visual taste — stops generic-looking interface output |
| UI UX Pro Max | `nextlevelbuilder/ui-ux-pro-max-skill` | UI/UX design partnership, design systems, styling |
| Emil | `emilkowalski/skills` | Motion and interface feel, from the creator of Sonner |
| GSAP | `greensock/gsap-skills` | Official GSAP guidance for proper web animation |

## The copy layer

| Skill | Repo | Adds |
| --- | --- | --- |
| Marketing Skills | `coreyhaines31/marketingskills` | Copywriting, SEO, conversion optimization workflows |
| Humanizer | `blader/humanizer` | Strips characteristic AI patterns from the copy |
| Social Media Skills | `charlie947/social-media-skills` | Multi-platform content distribution system |

## Content automation — triggers and distribution

The content-machine pipeline (see `pipelines.md` §1) becomes hands-off when wired to a trigger
and a sink:

```
Trigger:  RSS.app (makes an RSS feed from any site or social account)
          or Firecrawl (bundled MCP — scrape/monitor a source)
   → the content machine: cut, shorts, captions, overlays, landing page
   → Distribution: Upload Post (one API, every network) / Vimeo
```

- The orchestration layer (cron, n8n, GitHub Actions) is external — this stack is CLI and
  skills; schedule it with whatever the user already runs.
- **The publish guardrail applies with full force here.** An automated pipeline that posts on
  its own is exactly the case the rule exists for: the *pipeline setup* gets explicit user
  approval for where output goes, and any change of destination needs a new yes.
- RSS.app, Upload Post, and Vimeo are hosted services with accounts and pricing — the user
  signs up, not the agent.
