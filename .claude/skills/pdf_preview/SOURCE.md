# Where this skill comes from

Copy of `skills/pdf_preview` in the `ad-copywriter` tool at commit `75dbe87`, synced 2026-10-13. The tool's own
skill is the source: changes are made there and copied here by the maintainers' sync script, so an edit made
only in this copy is lost or blocks the next sync. `tools/ad-copywriter` ships in the public toolkit.

Where the tool is present (`tools/ad-copywriter`), its own skill and code are the reference and every command in
this skill runs. Where it is not, this copy is what is left:

## Without the tool

**Works:** Nothing that produces a file. The references describe the deck and the mockups precisely enough to check a preview someone else rendered.

**Needs the tool:** All of it: `scripts/render_preview.py` imports the `ad_copywriter` package for the templates, CSS, bundled fonts and the avatar builder. PDF output also needs WeasyPrint.

## Cleaned for this copy

- By rule: the public snapshot's rewrite rules, plus the note at the top of `SKILL.md`.
- By hand: `SKILL.md`, `references/deck_layout.md`, `references/fonts_and_pdf.md`, `references/mockup_specs.md`, `scripts/_bootstrap.py`, `scripts/render_preview.py`
- Left out: none
- Added here: none
