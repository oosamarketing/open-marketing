# Where this skill comes from

Copy of `skills/copywriter` in the `ad-copywriter` tool at commit `75dbe87`, synced 2026-10-13. The tool's own
skill is the source: changes are made there and copied here by the maintainers' sync script, so an edit made
only in this copy is lost or blocks the next sync. `tools/ad-copywriter` ships in the public toolkit.

Where the tool is present (`tools/ad-copywriter`), its own skill and code are the reference and every command in
this skill runs. Where it is not, this copy is what is left:

## Without the tool

**Works:** Writing the copy. The house style, the platform limits table, the brand identity template, the copy document format and the Northpeak examples in `references/` and `assets/examples/` are complete without any code, so an agent can write Meta and Google copy to spec and count characters itself.

**Needs the tool:** Every script in `scripts/`: `validate.py`, `export.py` (xlsx / csv / docx), `new_document.py` and `generate.py` are thin wrappers that import the `ad_copywriter` Python package, which is in the tool and not in this folder. Without the tool they stop with a message saying so. `generate.py` also needs an Anthropic API key, set by the user.

## Cleaned for this copy

- By rule: the public snapshot's rewrite rules, plus the note at the top of `SKILL.md`.
- By hand: `SKILL.md`, `assets/examples/brief_meta.json`, `assets/examples/legacy_format_example.xlsx`, `references/brand_identity_template.md`, `references/copy_document.md`, `references/few_shot_examples.md`, `references/platform_limits.md`, `references/style_guide.md`, `scripts/_bootstrap.py`, `scripts/new_document.py`
- Left out: 3 file(s) of the source that could not be cleaned (client material)
- Added here: `assets/examples/northpeak_brand_identity.md`, `assets/examples/northpeak_google_pmax.json`, `assets/examples/northpeak_meta_copy.json`
