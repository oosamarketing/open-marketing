# Changelog

Newest first. `scripts/update.sh --check` shows the entries you don't have yet.

## 0.2.2 — 2026-10-02
- First run: the agent handles prerequisites itself (Python 3.11+, the Chromium download, brand fonts: Google fonts are installed, licensed ones are requested) instead of sending the user to do it.
- Handed-over client folders: read their `HANDOFF.md` first, rebuild from the self-contained spec in place, compare with the included previews, add alongside, never reorganize.
- `scripts/setup.sh` checks for Python 3.11+ and says what it downloads.

## 0.2.1 — 2026-10-02
- Email: `build/handoff.md` assembly guide: image rows map to the editor's native image blocks (file, link, alt), live rows to custom HTML blocks with the snippet inline; `"editor": "preset"` marks footer/social/button sections the editor already provides.
- Email: specs can be self-contained (`brand_tokens` next to the spec), so a client folder rebuilds anywhere.
- Email: every build reports total download weight (HTML + images) against benchmarks, recompresses images with the new `compress.py` (quality ladder against a pixel-error threshold), and offers `--profile light` for lighter emails.
- Email: buttons are ALL CAPS with tracking by default.

## 0.2.0 — 2026-10-02
- New: email designer (`tools/graphic-designer/emails/`, skill `email-designer`). Builds marketing emails as stackable sections: each one a single `<div>` with inline CSS (never html/head/body/style), so it pastes into any ESP's HTML block. Section types for header, hero graphic, offer with code chip, text, columns that stack on phones, us-vs-them comparison rows, image tiles, quotes, footer. Writes `email.html`, an `email-lite.html` under Gmail's ~102 KB clip limit when needed, images to host, desktop and mobile previews, and a size/lint report.
- New: review cards that look verified: real reviews checked against the review platform's public feed, the platform's own logo and font, a link to the client's page.
- Buttons are ALL CAPS with tracking by default; brand elements in graphics are opt-in per template.

## 0.1.1 — 2026-09-22
- New Canva skill: build or repair designs natively through the Canva connector; what its importers can and can't do.
- Agents no longer commit to your clone on their own; design files are not an import path; never publish your local files to a public URL.
- Fix: white-on-white cutouts silently produced a fully opaque image when scipy wasn't installed (Pillow floodfill on a read-only image). Now works, and fails loudly if nothing is removed.
- Fix: brand-kit's tokens now render with the logo (paths resolve against the tool folder); missing images abort with a clear message.
- Fix: kit PDF pages fit at 8 taglines / 4 products; wording comes from the brand, not a leftover.
- Fix: extractor fetches the full-size logo and skips theme icons.
- Templates: draw icons as SVG paths, not characters (they become boxes in `.ai`).
- `project.py where` no longer creates folders; update.sh explains a missing remote.

## 0.1.0 — 2026-09-20
- First public release: brand-kit, graphic-designer, the client-workspace skill, setup and update scripts, tutorial.
- Example brand Northpeak with an Amazon infographic and Meta ad data in 1:1 and 1.91:1.
