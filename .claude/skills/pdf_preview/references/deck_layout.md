# Copy deck layout

The copy deck: the Primary Text / Headlines / Descriptions lists of every theme under a centered logo and a gold rule.

```
┌──────────────────────────────────────────────┐
│                   [logo]                     │  .deck-header .logo   height 64px (falls back to a text wordmark)
│               Meta Ad Copy                   │  h1, Montserrat 700, 24pt      (deck_title from the platform spec)
│  Brand · A preview of … for your review · date│  .subtitle, muted 10.5pt
│ ────────────────── gold rule ─────────────── │  hr.rule: 80% wide, 3px solid #F0E2B6
│                                              │
│ Steel Bottle 32 oz                           │  section.theme h2, 17pt 700    (one theme per page)
│ example.com · https://…                      │  .theme-meta, muted 9.5pt
│ Primary Text                                 │  h4, 11.5pt 600
│  • 🧊 Hook …                     214/2200    │  li.block-text .option (white-space: pre-line), .count muted / red when over
│    ...                                       │
│    Body …                                    │
│ Headlines                                    │
│  • Ice cold for 24 hours.           22/40    │
│ Descriptions                                 │
│  • Lifetime warranty                17/30    │
│ Interests: … In-Market: …                    │  .audiences (optional rows)
│ notes                                        │  .notes, italic muted
│ ────────────────── gold rule ─────────────── │
└──────────────────────────────────────────────┘
```

- Page: Letter, 0.75in margins (`base.css` `@page`). Each theme after the first starts on a new page.
- Field order follows the platform spec; empty fields are skipped.
- Counts: `n/max` per option, red when `n > max` (so an unvalidated deck still shows the problem).
- Fonts: bundled Montserrat 400/600/700 via `@font-face` with absolute `file://` URLs (or data URIs with `--embed`).
- Tokens live in `ad_copywriter/preview/templates/base.css` in the `ad-copywriter` tool; deck rules in `deck.css`.
