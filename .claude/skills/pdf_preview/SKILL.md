---
name: ad-copy-pdf-preview
description: Render a validated ad copy document (Meta or Google Ads) into OOSA's branded copy-deck HTML/PDF and platform mockups (a Google search ad card and a Meta feed card). Use when asked to preview, mock up, or produce a client-ready PDF or HTML of ad copy, or right after the ad-copywriter skill has produced a copy document.
---

> **Hub copy** of the `ad-copywriter` tool's skill (`skills/pdf_preview`). What it can do without that tool, and the commit it was copied from: [SOURCE.md](SOURCE.md).

# Ad copy preview

Turns a copy document (`copy.json`, produced by the `ad-copywriter` skill) into:

- **deck** — the OOSA copy deck: centered logo, "Meta Ad Copy" / "Google Ads Copy" title, subtitle with brand and date,
  a 3px gold (`#F0E2B6`) rule, then one section per theme with Primary Text / Headlines / Descriptions lists
  (each option with its character count, `...` block separators preserved). One theme per page.
- **mockup** — per theme, up to three variations rendered as the platform would show them:
  a Google search result (Sponsored label, favicon + site + `domain › path`, `Headline 1 | Headline 2 | Headline 3`,
  two descriptions, sitelinks, callouts) or, for Meta, a Facebook feed post and an Instagram feed post side by side
  (page header, primary text folded at 125 characters with "… See more", the creative, link card with CTA, reactions).
  Set `sets[].media_path` to a product image (file path or URL) so the cards show the real creative.
- **both** (default) — deck pages followed by mockup pages in one file.

## Prerequisites

- The `ad-copywriter` tool. `scripts/render_preview.py` gets its templates, CSS, fonts and avatar builder from that
  tool's Python package (installed, at `tools/ad-copywriter` in the hub, or through `AD_COPYWRITER_ROOT`). Without it
  nothing here renders: say so, and offer the copy as a table instead of a preview.

- For realistic Meta cards, put the product image path in `sets[].media_path` (Shopify stores expose images at
  `/products/<handle>.json`; download the first image and reference the local file).

- A copy document. Run `../copywriter/scripts/validate.py copy.json` first; the renderer will still render an
  invalid document but tells you so, and over-limit options are flagged in red in the deck.
- HTML needs nothing extra. PDF needs WeasyPrint: `pip install weasyprint` (macOS: `brew install pango` first).
  See [references/fonts_and_pdf.md](references/fonts_and_pdf.md).

## Workflow

1. Render:
   ```bash
   python scripts/render_preview.py copy.json --out out/ --style both --pdf
   ```
   Produces `out/<brand>-<platform>-preview.html` and `.pdf` (`-deck` / `-mockup` when a single style is chosen).
2. Check the output (open the PDF, or read the HTML): logo present, one theme per deck page, no option shows a red
   count, Google cards show three headlines, Meta cards fold long primary text with "… See more", emoji render.
3. Deliver the PDF path (and the HTML if the client prefers a link).

## Options

| Flag | Effect |
|---|---|
| `--style deck\|mockup\|both` | which pages to produce |
| `--pdf` | also write a PDF |
| `--logo PATH_OR_URL` | override the logo (default: `brand.logo_path` in the document, else the OOSA logo) |
| `--title`, `--subtitle`, `--date` | deck header overrides |
| `--combos N` | mockup variations per theme (default 3, capped by the number of options) |
| `--embed` | inline fonts and logo as data URIs for a portable single-file HTML |
| `--no-fonts` | skip the bundled Montserrat `@font-face` rules (system font stack) |
| `--no-counts` | hide character counts in the deck |
| `--json` | machine-readable output paths |

Layout details: [references/deck_layout.md](references/deck_layout.md), [references/mockup_specs.md](references/mockup_specs.md).

## Branding tokens

Montserrat (bundled, OFL), gold rule `#F0E2B6`, ink `#1B1B1B`, muted `#6B6B6B`.
Google card: headline `#1a0dab`, URL/description `#4d5156`. Meta card: text `#050505`, meta `#65676B`, footer `#F0F2F5`.

## Don'ts

- Don't edit copy here; go back to the copywriter skill and re-validate.
- Don't hand over an HTML screenshot when the user asked for a PDF.
- Don't render an unvalidated document for a client without saying it is unvalidated.
