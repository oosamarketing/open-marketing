# Design principles (all brands)

- **One message per graphic.** Headline states the benefit; everything else supports it.
- **Thumbnail test.** Headline and hero must read at 375 px wide. Body text ≥ 18 px at
  1000 px canvas scale; headlines 56–72 px; badge numerals 40+ px.
- **3–5 callouts max.** Icon + 2–4 word title + one short sentence. No paragraphs.
- **Hierarchy:** brand mark → headline → product → callouts → trust bar. Don't let badges
  fight the headline.
- **Color:** brand primary for structure (icons, badges, lines), accent only for emphasis
  (check marks, one number). Neutral backgrounds; product must be the most saturated thing.
- **Type:** one family per brand (see tokens). Weights: 900/800 for display, 500 for body.
  Tight letter-spacing on headlines (-0.02em), wide tracking on small caps labels (0.15–0.22em).
- **Product:** use real product photography when the brand has it; the SVG hero in the
  example template is a placeholder. Product occupies 55–70% of frame height.
- **No stock clip-art, no drop shadows on text, no gradients on text.**
- **Claims:** only claims present in `brand.md` or the user's brief. Mark unverified ones.
- **Vector export:** avoid effects that rasterize (box-shadow, filter, backdrop-filter) when
  a design is destined for Illustrator; render.py strips them for .pdf/.ai anyway.
