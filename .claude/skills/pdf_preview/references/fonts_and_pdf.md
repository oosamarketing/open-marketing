# Fonts and PDF rendering

## Installing WeasyPrint

| OS | Steps |
|---|---|
| macOS | `brew install pango` then `pip install weasyprint` (or `pip install -e ".[pdf]"` from the repo root) |
| Debian / Ubuntu | `apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 fontconfig` then `pip install weasyprint` |
| Windows | follow https://doc.courtbouillon.org/weasyprint/stable/first_steps.html (GTK runtime) |

HTML output never needs WeasyPrint; only `--pdf` does. If the import fails the script exits 2 with the install hint.

## Fonts

- Montserrat Regular / SemiBold / Bold are bundled under `ad_copywriter/preview/assets/fonts/` (SIL Open Font
  License, see `OFL.txt`) and referenced with `@font-face` using absolute `file://` URLs, so the PDF looks the same on a
  machine without Montserrat installed. `--embed` inlines them as data URIs.
- Fallback stack: `"Montserrat", "Helvetica Neue", Arial, "Apple Color Emoji", "Noto Color Emoji", "Segoe UI Emoji", sans-serif`.
- **Emoji**: macOS renders them through Apple Color Emoji. A Linux container needs `fonts-noto-color-emoji` installed
  or emoji print as empty boxes. HTML in a browser is unaffected.

## Troubleshooting

- Blank logo: `brand.logo_path` points to a missing file. The deck falls back to the OOSA logo, the Meta card to the brand initial.
- "Cannot load font": the fonts folder was not copied along with the package; run from the repo or reinstall.
- Everything on one page: an old WeasyPrint. `pip install -U weasyprint` (60+ tested, 70 used in development).
