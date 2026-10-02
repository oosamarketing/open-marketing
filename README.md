# Open Marketing

Free, open-source marketing tools you run with an AI coding agent. Clone this one repo, open it
in Claude Code (or Codex, Cursor, any agent that reads `AGENTS.md`), and ask for what you need in
plain English: a brand kit from your website, Meta ads in the right sizes, Amazon listing
infographics and A+ images.

Built by [OOSA](https://oosa.ai) from the tooling we run for our own clients. MIT licensed.
Everything runs on your computer. Your files stay in your folders.

## Quick start

```bash
git clone https://github.com/oosamarketing/open-marketing.git
cd open-marketing
scripts/setup.sh          # one time, about 3 minutes: Python environment + a headless browser
```

Then open the `open-marketing` folder in Claude Code and try:

> Make me a brand kit from https://mybrand.com, then two Meta ads (1:1 and 1.91:1) using the
> product photos in ~/Desktop/MyBrand/photos.

New to this? Follow the step-by-step **[tutorial](docs/tutorial.md)**.

## What's inside

| Tool | What it does |
|---|---|
| [`tools/brand-kit`](tools/brand-kit) | Reads your website and pulls out the logo, the colors actually used, fonts, taglines and tone. You confirm, and it builds a brand kit PDF plus a `brand-assets/` folder (logo files, round avatar, palette, tokens) the design tool reads. |
| [`tools/graphic-designer`](tools/graphic-designer) | Ads, Amazon gallery infographics and A+ rows as HTML/CSS templates rendered to PNG/JPG at exact platform sizes. Background removal for product photos. On a Mac with Adobe Illustrator it can also export editable `.ai` files with live text and make variations of an existing `.ai` template. Marketing emails as paste-ready sections: each a single `<div>` with inline CSS, graphics where design needs them and live text everywhere else, with a Gmail-safe build under 102 KB. |
| [`.claude/skills/canva`](.claude/skills/canva) | For teams that work in Canva: with the Canva connector attached, the agent builds designs natively in Canva (editable text and shapes), repairs designs you already have there, and knows what Canva's importers can't do. |
| [`.claude/skills/client-workspace`](.claude/skills/client-workspace) | Keeps client files organized: it works inside the folders you already have, or sets up a clean layout, and remembers your preferences in a `workspace.md`. |

A worked example brand, **Northpeak**, ships with the repo so you can see output before using your own brand:

```bash
cd tools/graphic-designer
../../.venv/bin/python render.py templates/meta-simple-hero.html --brand northpeak \
    --data data/northpeak-meta-1x1.json --out out/northpeak-ad.png
```

More tools (ad copy, image generation and photo expand, Amazon research) are being prepared for release.

## How it works with an agent

[`AGENTS.md`](AGENTS.md) tells the agent which tool handles what and the house rules: confirm the
brand before designing, show a plan, show previews, never invent product claims, save to your
folders. Claude Code also loads the skills in `.claude/skills/` automatically.

## Updating

```bash
scripts/update.sh --check   # see if there's a new version and what changed
scripts/update.sh           # apply it (your brands and files are never touched)
```

Made changes of your own? `scripts/update.sh --merge` saves them, makes a backup, merges the new
version in and tests it; `--rollback` undoes it. Keep your own templates in [`custom/`](custom/),
which updates never touch. Forked the repo? `git remote add upstream https://github.com/oosamarketing/open-marketing.git`
and the script updates from there.

Agents check weekly and ask before applying. See [`CHANGELOG.md`](CHANGELOG.md).

## Requirements

macOS or Linux (Windows through WSL), Python 3.10+, git. Optional: Adobe Illustrator on macOS for
`.ai` export; `scripts/setup.sh --cutouts` adds the background-removal model (about 400 MB).

## Contributing

Issues and pull requests welcome. Please keep client data out of the repo: brands other than the
Northpeak example belong in your own folders.
