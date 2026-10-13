# ad-copywriter

Ad copy for Meta (Facebook / Instagram) and Google Ads (Performance Max, Search RSA), written by your
agent in a consistent house style and then checked by code: character limits, option counts and style
rules are validated, the copy is exported for hand-off (xlsx / csv / docx), and a preview is rendered
as a copy deck plus platform mockups (HTML, optionally PDF).

The agent writes the copy. Nothing here calls a model on your behalf unless you opt in to the
headless generator at the end of this page.

## How it is laid out in this toolkit

```
tools/ad-copywriter/
  ad_copywriter/          the library: platform limits, the copy document, validation, exports, previews
    data/                 platform_spec.json (limits, labels) · copy_document.schema.json
    preview/              deck and mockup templates, bundled Montserrat fonts
.claude/skills/
  copywriter/             the skill your agent follows: house style, workflow, scripts, references, examples
  pdf_preview/            the preview skill: scripts/render_preview.py, layout references
```

`scripts/setup.sh` at the top of the toolkit installs this tool into the shared `.venv`.

## Use it

Ask your agent: *"Write Meta ad copy for my brand, themes Summer Sale and Back to School. Here is
our brand voice."* It follows `.claude/skills/copywriter/SKILL.md`: collects what it needs, writes
three options per field, validates, fixes, exports, and renders a preview for you to review.

By hand, from the top of the toolkit, with the example brand (Northpeak, fictional):

```bash
PY=.venv/bin/python
EX=.claude/skills/copywriter/assets/examples
$PY .claude/skills/copywriter/scripts/validate.py $EX/northpeak_meta_copy.json
$PY .claude/skills/copywriter/scripts/validate.py --print-spec google_pmax
$PY .claude/skills/copywriter/scripts/export.py   $EX/northpeak_meta_copy.json --out out/ --format xlsx csv docx --layout both
$PY .claude/skills/pdf_preview/scripts/render_preview.py $EX/northpeak_meta_copy.json --style both --out out/
```

Add `--pdf` to the last command for a PDF. That needs WeasyPrint (`.venv/bin/pip install weasyprint`;
on macOS `brew install pango` first). HTML previews need nothing extra.

## The copy document

One JSON file per brand and platform: `brand`, then `sets[]` (one per theme), each with `fields` such
as `primary_text`, `headline`, `description`, and for Google `long_headline`, `path`, `sitelink`,
`callout`. `validate.py --write` stores its result in the file. Full description:
`.claude/skills/copywriter/references/copy_document.md`.

## Platform limits

| Platform | Field | Max chars | Options |
|---|---|---|---|
| Meta | Primary text | 2200 (125 before "See more") | 5 |
| Meta | Headline | 40 | 5 |
| Meta | Description | 30 | 5 |
| Google PMax | Headline | 30 | 15 (5 / 10 / 15) |
| Google PMax | Long headline | 90 | 5 |
| Google PMax | Description | 90 | 4 |
| Google PMax | Display path / Sitelink / Callout | 15 / 25 / 25 | 1 / 4 / 4 |
| Google RSA | Headline / Description / Path | 30 / 90 / 15 | 15 / 4 / 2 |

Source of truth: `ad_copywriter/data/platform_spec.json`. Platforms change their limits; check the
platform's own page before a large upload.

## Headless generation (optional)

```bash
.venv/bin/pip install anthropic     # and set ANTHROPIC_API_KEY yourself
.venv/bin/python .claude/skills/copywriter/scripts/generate.py --brief .claude/skills/copywriter/assets/examples/brief_meta.json --out out/gen.json
```

It asks the Anthropic API for a first draft under the same rules and runs the same validator. Add
`--dry-run` to see the prompts without calling the API. Writing the copy with your agent in the loop
is the preferred path: it is easier to steer and there is no key to manage.

## Licenses

MIT. Montserrat is bundled under the SIL Open Font License (`ad_copywriter/preview/assets/fonts/OFL.txt`).
