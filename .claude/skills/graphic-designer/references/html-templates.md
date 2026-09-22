# New graphics from HTML/CSS templates

## Flow

1. Pick a template in `templates/` or write one. Templates are plain HTML with
   `{{ key }}` placeholders (dot paths, list indexes: `{{ trust.0 }}`) and
   `{% if key %}…{% else %}…{% endif %}` blocks. Declare the canvas in the head:
   `<meta name="canvas" content="width=1000,height=1000,scale=2">` and wrap the design in
   `<div id="canvas">`; only that element is screenshotted.
2. Put copy and per-job values in `data/<job>.json`. Brand values come from `--brand`
   (`tokens.json` is merged under `brand`, so `{{ brand.color }}`, `{{ brand.name }}` resolve).
   A product photo goes in as `"product": {"image": "/abs/path.png"}`; templates fall back
   to an SVG placeholder when it is missing.
3. Approve the HTML first when the design is new:
   `$PY render.py templates/x.html --brand <slug> --data data/job.json --html-only --out out/job.html`
4. Render and deliver:
   `$PY render.py templates/x.html --brand <slug> --data data/job.json --out out/job.png --deliver`
   `.jpg` with `--quality 90` for Amazon uploads. `--deliver` copies into the brand's export folder.
5. Editable handoff: same command with `--out out/job.ai`. This prints a vector PDF with text
   hidden, then drives Illustrator to add a **Text** layer of live text objects at the measured
   baselines (`ai_export.py`). A `*.ai-preview.png` rendered by Illustrator lands next to it;
   look at it. `--outline-text` skips the live-text step; `.pdf` output skips Illustrator.
   Add `--svg` for an SVG with `<text>` elements next to the .ai; Figma imports it with
   editable text when the font is installed. Fonts must be installed on the Mac for both
   (download the Google Fonts TTFs into `~/Library/Fonts`, then restart Illustrator so it sees
   them). Illustrator's font names differ from CSS (NanumMyeongjo, MulishRoman-Bold); the
   exporter tries the common patterns and warns when it falls back.
   Use `--keep-effects` for ad templates that rely on blur, glow, or drop shadows: those
   rasterize into the PDF and Illustrator renders them faithfully. Leave effects stripped only
   for pure-vector infographics where every shape should stay editable.

## Writing a template well

- Design at CSS size and let `scale` do the pixels. Body text ≥ 18 px, headline 56–72 px,
  badge numerals 40+ px at a 1000 px canvas.
- Use CSS custom properties fed from tokens (`--brand: {{ brand.color }}`), Inter or the brand
  font via Google Fonts link plus a local fallback. Fonts must also be installed on the Mac for
  `.ai` text to stay editable (Inter and Montserrat are).
- Keep effects that rasterize (box-shadow, filter, backdrop-filter) decorative only; vector
  export strips them.
- Draw icons and checkmarks as inline SVG, never as characters like `✓`. Chromium falls back to
  a system font so they look fine in the PNG, but Illustrator renders glyphs the brand font lacks
  as empty boxes in the `.ai`.
- Existing example: `templates/amazon-infographic-callouts.html` with `data/water-bottle.json`
  and brand `northpeak` (feature callouts, claim badges, trust bar, photo-or-SVG hero).
- Platform specs live in `brand-guidelines/general/amazon-listing-images.md` (gallery sizes,
  A+ module sizes, what the main image may not contain).

## Illustrator quirks already handled in `ai_export.py`

Scripts cannot set a text anchor, so text is positioned by top/left using an ascent measured
inside Illustrator (a capital H outlined once per font). Stale open documents make Illustrator
throw generic errors; the script closes them before opening. If a font is missing Illustrator
substitutes and the script prints a warning: install the font or accept the substitute.
