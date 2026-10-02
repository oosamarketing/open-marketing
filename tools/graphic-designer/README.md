# graphic-designer

HTML/CSS → image pipeline for marketing graphics (Amazon listing infographics, ads,
social creatives). Design in HTML/CSS, approve in a browser, render to PNG/JPG with
headless Chromium (Playwright), export a vector PDF, or a native Illustrator `.ai` with
live text. Part of [Open Marketing](https://github.com/oosamarketing/open-marketing).

Optional companion: [gemini_manager](https://github.com/oosamarketing/gemini_manager) can generate or
expand product photos when installed alongside (see *Product photos* below).

## Requirements

- Python 3.11+ with `playwright` and `pillow`; run `playwright install chromium` once.
  (In the Open Marketing toolkit, `scripts/setup.sh` installs both into `.venv`.)
- Optional: `rembg[cpu]` for `cutout.py`; Adobe Illustrator (macOS) for `.ai` export.
- Fonts used by templates installed locally (Inter, Montserrat) so `.ai` text stays editable.

## Layout

```
render.py        CLI renderer: PNG/JPG (Playwright screenshot), PDF (vector), .ai (via Illustrator)
cutout.py        Background removal + auto-crop (rembg) → transparent product PNG
cutout_white.py  Background removal for white-backdrop shots where the subject is also white
defringe.py      Fade the white halo a cutout/render shows on colored backgrounds
restore_original.py  After a generative expand, paste the original photo's pixels back (keeps only the new edges AI-made)
ai_inspect.py    Dump an existing .ai: artboards, layers, text frames, placed/embedded images
ai_edit.py       Make variations of an existing .ai: swap photos (cover-fit), edit text, recolor, export
emails/          Email builder: sections as <div> snippets with inline CSS, full email, ≤102 KB lite build (see Email below)
project.py       Local-only export folders (~/Downloads/<Brand> Infographics/) + asset intake
ai_export.py     Builds the Illustrator file: "Artwork" layer (vectors) + "Text" layer (live text)
brand-guidelines/  Brand kits + house rules. READ brand-guidelines/README.md FIRST (agents too)
templates/       HTML templates with {{ placeholders }} and a <meta name="canvas"> size hint
data/            JSON variable sets — one per product / campaign (brand comes from --brand)
assets/          Product photos, logos, fonts referenced by templates (relative paths)
out/             Rendered images + the filled-in .html used to produce them
research/        Notes on comparable open-source tools and Amazon image best practices
```

## Quick start

```bash
PY=../../.venv/bin/python   # the toolkit venv (any venv with playwright + pillow works)
$PY render.py templates/amazon-infographic-callouts.html \
    --data data/water-bottle.json --out out/water-bottle.png
open out/water-bottle.png
```

`--html-only` writes just the filled HTML so a design can be approved in a browser
before rendering. Sizes come from the template's canvas meta tag, or `--width/--height/--scale`.
`--brand <slug>` loads `brand-guidelines/brands/<slug>/tokens.json` as `{{ brand.* }}`.

### Editable vector export (Illustrator)

```bash
$PY render.py templates/amazon-infographic-callouts.html --brand northpeak \
    --data data/water-bottle.json --out out/water-bottle.ai
```

- `.pdf` output: Chromium vector PDF, opens in Illustrator with editable paths.
- `.ai` output: drives the installed Adobe Illustrator 2026 (AppleScript → ExtendScript) to
  open the artwork PDF and add a **Text** layer where every line is a live, editable text
  object in the matching installed font (weight mapped from CSS; tracking from letter-spacing).
  Baselines are measured in the browser and matched to Illustrator's own font metrics.
  A `*.ai-preview.png` rendered by Illustrator is written next to it for verification.
- Shadows/filters are stripped for vector output (they would rasterize); `--keep-effects` keeps them.
- `--outline-text` skips the live-text step and leaves text as it comes out of the PDF.
- Fonts must be installed on the Mac (Inter, Montserrat are). Missing ones are reported and
  fall back to the family's closest face.

## Workflow

1. Drop an example / brief → pick or write a template.
2. Fill `data/<name>.json` with copy, colors, badges.
3. Approve the HTML in a browser (`--html-only`).
4. Render to image. Amazon secondary images: 1000x1000 CSS px at scale 2 → 2000x2000.

### Product photos

Templates take `{{ product.image }}` (a transparent PNG; paths in job data are relative to the data
file, absolute paths work too) and fall back to an SVG placeholder when it's missing. Prefer the
brand's own photography. Cut backgrounds out with:

```bash
$PY cutout.py photo.jpg cutout.png            # colored product on white (needs `scripts/setup.sh --cutouts`)
$PY cutout_white.py photo.jpg cutout.png      # white product on white
$PY cutout_clear.py photo.jpg cutout.png      # clear parts (lenses, glass)
$PY defringe.py cutout.png cutout-fixed.png   # pale rim on colored backgrounds
```

If the optional `gemini_manager` tool is installed next to this one, it can generate a stand-in
product image or expand a photo to a wider format (`restore_original.py` then pastes the real
pixels back). Generated images are placeholders for comps, never for live listings.

## Amazon image rules of thumb baked into the template

- 2000x2000 px square (≥1600 px enables zoom); product fills ~60–70% of the frame.
- Benefit-led headline readable at thumbnail size; 3–5 callouts max; icons + short text.
- Big numeric badges (24H COLD) for the key claim; dark trust bar for compliance-type claims.
- Main image must be pure white background and product only — this template is a *secondary* image.

## Editing existing Illustrator templates

Given a client's `.ai` ad template, produce variations without touching the original:

```bash
$PY ai_inspect.py "Client/Ads/Template.ai" --out report.json   # what's editable, per artboard
$PY ai_edit.py spec.json                                         # see ai_edit.py docstring for the spec
```

`ai_edit.py` opens the template, saves a copy, and for each variant: swaps the photo inside the
artboard's clipping group (cover-fit, anchored), replaces text by matching current contents,
hides stray objects, optionally recolors white text/logos for light photos, and exports the
artboard as PNG.

Light photos on a template designed for white text: cut the subject out (`cutout_white.py` for
white-backdrop shots), composite onto the brand's dark color, and use that as the photo.

## Amazon A+ references

- Figma: [Premium A+ Content Modules](https://www.figma.com/community/file/1565067483797388969/premium-a-content-modules) (OOSA community file) for Premium layouts.
- Basic module sizes and house defaults: `brand-guidelines/general/amazon-listing-images.md`.

## Roadmap

- [ ] Shareable / standalone version lives here
- [ ] Template gallery: comparison chart, lifestyle w/ photo, size guide, how-to steps, A+ modules
- [ ] Layered PSD export (per-element transparent renders assembled with ag-psd / pytoshop)
- [x] Editable .ai export with live text layer

## Claude Code skill

`.claude/skills/graphic-designer/` is a project skill that teaches Claude Code these workflows
(brand setup, HTML rendering, .ai variations, product photos). It loads automatically when the
repo is the working directory; add this directory as an additional working directory to use it
from elsewhere.

## Email

`emails/build_email.py <spec.json>` builds an email as stackable snippets: each section is one
`<div>` with inline CSS (no `<html>`, `<head>`, `<body>`, `<style>`), so it pastes into any ESP's
HTML block. Graphic sections are rendered from `templates/` like any other graphic; text sections
are live, responsive HTML. Output: `sections/`, `email.html`, `email-lite.html` when the markup
exceeds Gmail's ~102 KB clip limit, `images/` to host, desktop and mobile previews, and a size and
lint report. Example: `emails/examples/northpeak-launch.json`. Skill: `.claude/skills/email-designer/`.
