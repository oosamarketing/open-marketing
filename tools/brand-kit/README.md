# brand-kit

Extract a brand from its website, confirm it with a human, and produce a client-ready brand
kit: a short PDF plus a `brand-assets/` folder that creative tools (like
[graphic-designer](https://github.com/oosamarketing/graphic-designer)) can consume directly.
Part of [Open Marketing](https://github.com/oosamarketing/open-marketing).

## Flow

```bash
PY=../../.venv/bin/python        # the toolkit venv; any venv with playwright + pillow works

# 1. Draft from the live site (Playwright/Chromium): colors by on-screen area, fonts actually
#    used, logo candidates, taglines, nav, body text for tone. Screenshots + logos land in raw/.
$PY extract.py https://example.com --out work/example

# 2. Write brands/<slug>.json from the extract + anything the client sent (palette, logo files).
#    Show the client the colors, fonts, logo, taglines and voice; edit until they say yes;
#    then set sources.confirmed_by / confirmed_at.

# 3. Build the kit into the client's folder
$PY kit.py brands/northpeak.json --out "<client folder>/branding"
```

Output:

```
<client folder>/branding/
  Northpeak Brand Kit.pdf            6 pages: cover, color, typography, logo, voice, products
                                     (named "(DRAFT)" with a watermark until confirmed)
  brand-assets/
    logo/                            copies of the logo files, plus avatar.png (round, logo on primary)
                                     and avatar-secondary.png — for Meta/IG page circles, favicons
    palette.png                      swatch strip
    brand.json                       source of truth
    tokens.json  brand.md            drop-in for graphic-designer/brand-guidelines/brands/<slug>/
    kit.html                         the PDF's source
```

## Round avatars from any logo

`avatar.py` puts a logo on a solid brand-color disc with padding, strips a white background from
opaque logos, and writes a square PNG with transparent corners. `kit.py` runs it automatically; use it
directly for other colors or sizes:

```bash
$PY avatar.py "brand-assets/logo/northpeak-logo-white.png" avatar-1024.png --bg "#0F6E6E" --size 1024
```


## brand.json

See `brands/northpeak.json` for a complete example. Colors carry a `role` (primary,
secondary, text, light, dark accent, background, tertiary) that `tokens.json` maps onto the
graphic-designer token names. Fonts carry a role containing "display" or "body". Logo paths
are absolute; the kit copies them.

## Why confirm before finalizing

The extractor measures what the site does, not what the brand intends: a theme's default
button color shows up as a "brand color", an old font name (Muli) hides a current one (Mulish),
and the logo in the header may be a low-res PNG. The client's own palette and logo files win
over extraction; the extraction is there to catch what they forgot to send and to fill voice
and taglines from live copy.
