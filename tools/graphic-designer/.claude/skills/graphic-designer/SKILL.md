---
name: graphic-designer
description: Produce marketing graphics and ad creatives for a brand — Amazon listing infographics, Meta/social ads, A+ modules — from HTML/CSS templates or from a client's existing Illustrator (.ai) template, rendered to PNG/JPG, vector PDF, or an editable .ai with live text. Use this whenever the user asks for an ad, infographic, listing image, banner, ad variation, "swap the photo/text in this .ai", a product photo cutout, or anything creative for a brand, even if they don't say "graphic" or "design". Also use it when the user hands over photos, an .ai file, or a brand name and wants creative made from them.
---

# Graphic designer

This repo turns templates plus brand tokens plus copy into finished creative, and can
also make variations of a client's existing Illustrator template. Everything runs on
this Mac: Chromium via Playwright for HTML, Adobe Illustrator 2026 via AppleScript for .ai.

Python to use for every script here (it has Playwright + Chromium + Pillow):
the toolkit's `.venv/bin/python` (from inside this folder: `../../.venv/bin/python`)

## Step 0: brand and destination, before any pixels

1. Read `brand-guidelines/README.md`, then `brand-guidelines/brands/<slug>/brand.md` and
   `tokens.json` for the brand at hand. If the brand has no folder, copy `brands/_template/`
   to `brands/<slug>/`, fill it from whatever the user gave (logo, site, an existing ad, an
   .ai file), and say what you assumed. Write new preferences the user states back into
   `brand.md` under Do / Don't so the next session inherits them.
2. Find where files go: `$PY project.py where --brand <slug>`. Default is
   `~/Downloads/<Brand> Infographics/` with user-supplied images under `assets/`. If the user
   points you at their own folder (an attached directory, "save it with the other ads"),
   register it once: `$PY project.py set-location --brand <slug> "<dir>"`. Deliverables and
   assets stay on the user's machine, never on a server.
3. File every image the user hands over before using it:
   `$PY project.py asset <file> --brand <slug> --name <clean-name.ext>` and reference the
   printed absolute path. Photos pasted into chat usually also exist in `~/Downloads`; check
   there by timestamp and dimensions.

## Pick the workflow

| Situation | Read |
|---|---|
| Make a new graphic from scratch (Amazon infographic, ad, banner) | `references/html-templates.md` |
| User has an existing `.ai` template and wants variations / new photo / new copy | `references/ai-editing.md` |
| Need a product photo, or a photo needs its background removed | `references/product-photos.md` |

Read only the one you need. The repo README has the full CLI reference if a flag is unclear.

## Approval loop

PNGs first. Editable `.ai` files (and SVGs, which are Figma-only and opt-in) come after the user
approves the set or asks for one; never generate them speculatively. See `CLAUDE.md`.

Show before you finish. Render a preview (PNG, or a contact sheet of several variants via
Pillow), look at it yourself first, fix what's obviously wrong, then show it to the user (attach or link the file). Give the user the paths of everything written. Ship the editable file (.ai)
alongside the PNG when the user is likely to hand work to a designer.

Check the preview for the failure modes that keep recurring:
- Text over a busy or same-tone photo area (dark text on a dark helmet, white text on a white
  jersey). Fix the crop, the composite, or the text color; do not ship it hoping.
- A cutout with holes where the subject was the same color as the backdrop.
- Copy that is not from the brand's copy bank or the user's brief. Never invent claims.
- Mirrored photos. Logos on gear flip; never flip a photo to fit a layout.
- Products that float or collide with copy. Two causes, both seen on real jobs: renderings
  delivered as padded squares (the visible product is a fraction of the file, so every size and
  anchor you set measures transparent space), and free-form placement. Crop renderings to
  their alpha bounds first, then compose on a rule: copy in one column, product in the other,
  both on a shared floor line, nothing crossing the split. A model photo is either the hero on
  its own or has the product in a genuinely empty area; never paste packaging over a face or hand.


## House rules in one breath

Brand colors and fonts come from tokens, never hardcoded. One message per graphic, readable at
thumbnail size. Amazon secondary images are 2000x2000 designed at 1000x1000 with 2x scale; the
main image is white-background product only and is not made here. Vector exports strip
box-shadows and filters because those rasterize. `out/` is scratch; the export folder is the
user's copy. If this folder is a git clone the user maintains, leave new templates and tools uncommitted and tell the user what changed; committing to their working copy is their call, not yours.
