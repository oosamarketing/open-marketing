---
name: brand-kit
description: Build or update a brand kit for a client from their website and any files they share — logo, 2–3 main colors, fonts, tone, taglines — confirm the findings in chat, then produce a PDF kit and a brand-assets folder that graphic-designer can use. Use this whenever a user names a brand or URL and wants creative made, asks for "brand guidelines", "brand kit", "extract the logo/colors from the site", "what are their brand colors", or when a creative job starts for a brand that has no brand-guidelines folder yet.
---

# Brand kit

Turn a website plus whatever the client sent into a confirmed, reusable brand definition.
Python: the toolkit's `.venv/bin/python` (from inside this folder: `../../.venv/bin/python`).

## Steps

1. **Extract.** `$PY extract.py <url> --out work/<slug>`. Read `work/<slug>/extract.json`
   and look at `raw/home-fold.png`. Note the top background colors by area (page background,
   header, section panels), text color, button colors, fonts by character count, the logo file
   the header actually uses, and the largest short lines as tagline candidates.
2. **Reconcile with the client.** Anything the user gave you (hex codes, a palette image, logo
   files, a tone note) beats the extraction. Compare the two explicitly in chat: which colors
   matched, which the site has that the client didn't mention (theme button colors are usually
   noise), which the client has that the site doesn't show (often the logo's own colors).
3. **Draft `brands/<slug>.json`.** Roles matter: exactly one `primary`, one `secondary`, one
   `text`, one `light`. Fonts: one role containing "display", one containing "body". Voice comes
   from live copy plus any existing ad copy files the client has; keep the client's phrasing.
4. **Confirm before finalizing.** Present colors, fonts, logo treatment, taglines, and tone as a
   short list and ask for a yes or edits. Until the user confirms, build with
   `sources.confirmed_by` empty so the PDF carries the DRAFT watermark. When they confirm, set
   `confirmed_by` and `confirmed_at` and rebuild.
5. **Build.** `$PY kit.py brands/<slug>.json --out "<client folder>/branding"`. Then copy
   `brand-assets/tokens.json` and `brand.md` into
   `graphic-designer/brand-guidelines/brands/<slug>/` (copy the `logo/` files into that brand's
   `assets/` too, since `tokens.json` points there) so creative jobs pick them up, and show the user the PDF.
   Page budgets: about 8 taglines and 4 products with up to 5 facts fit; the builder trims and says so.

## Avatars

Social mockups and profiles need a round avatar, and a wide two-tone wordmark never survives a
40 px circle on white. `kit.py` writes `brand-assets/logo/avatar.png` (logo on the primary color)
and `avatar-secondary.png`; `avatar.py` makes more for other colors or sizes. Other tools that show a
profile circle (ad mockups, social previews) can point at it.

## Judgment calls

- A two-tone logo (light word + dark word) only works on mid-tone backgrounds; say so in the
  logo description and list the backgrounds it works on.
- Extracted font names can be legacy aliases (Muli → Mulish). Use the Google Fonts name.
- Don't invent taglines. Headline bank = site lines + the client's existing ad copy.
- Keep the kit to what a designer needs on page one: colors, type, logo rules, voice, products.
