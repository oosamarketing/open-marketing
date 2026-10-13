---
name: ad-copywriter
description: Write, validate and export Meta (Facebook/Instagram) and Google Ads (Performance Max / Search RSA) ad copy in OOSA's house style from a theme, a brand identity and optional existing copy. Use whenever someone asks to write, rewrite, refresh, expand or export ad copy, headlines, primary text, descriptions, PMax assets or RSA assets. You write the copy; the bundled scripts check character limits and the house style, then produce xlsx / csv / docx for client handoff.
---

> **Hub copy** of the `ad-copywriter` tool's skill (`skills/copywriter`). What it can do without that tool, and the commit it was copied from: [SOURCE.md](SOURCE.md).

# Ad copywriter

**You write the copy. The scripts check it and export it.** Nothing here calls a model on your behalf
(the headless generator is a secondary, opt-in path). Never invent product facts, prices, offers or
claims: everything factual comes from the brief, the brand identity or the existing copy. Ask when it's missing.

## 1. Inputs to collect first

| Input | Required | Notes |
|---|---|---|
| Platform | yes | `meta`, `google_pmax` or `google_rsa` |
| Theme(s) | yes | One set per theme: "Fall Sale", "Black Friday", a product line, or a full sentence brief like "Get the Northpeak 32 oz Steel Bottle before summer and keep your drinks ice cold all day on the trail." |
| Brand identity | yes | Voice / tone / personality. Accept a paragraph or the two-trait format in [references/brand_identity_template.md](references/brand_identity_template.md). If none exists, draft one from the website and confirm it. |
| Existing copy | no | Past ads to match in voice. Paste, a copy document JSON, or the legacy xlsx (`Primary Text | Headline | Description`, one sheet per theme). |
| Landing page + display URL | yes for export | Per theme. |
| Options per field | no | Default **3**. Never exceed the platform count (`validate.py --print-spec <platform>`). |
| CTA button | no | Meta only, default "Shop now". |

## 2. House style — Meta (the way OOSA writes it)

Primary text is **three blocks separated by a line that contains only `...`**:

```
🧊 Hook: one or two short lines that stop the scroll (stands alone within 125 characters)
...
Body: the concrete detail — what it is, where it's made, what's different
...
CTA: one engaging line that tells them what to do
```

- The hook block **must read complete within 125 characters**: that is what shows before "See more".
- Lead the hook with one emoji that fits the brand. A second emoji in the CTA is fine. Nowhere else.
- Headlines: **≤ 12 words and ≤ 40 characters**, drive action ("Get the 32 oz Steel Bottle").
- Descriptions: **≤ 8 words and ≤ 30 characters** ("Lifetime warranty").
- Three options per field, **each a different angle**: seasonal, identity, social proof, urgency, product detail.
- No hashtags, no ALL CAPS, no exclamation stacks, no "!!!", no claims the identity doesn't support.
- Keep regional / identity cues from the brand: its own nouns and places ("the trail", "the commute", a home town it names).
- Worked examples: [references/few_shot_examples.md](references/few_shot_examples.md). Full rules: [references/style_guide.md](references/style_guide.md).

## 3. House style — Google Ads

- Headlines ≤ 30 chars, **no exclamation marks**, each a distinct angle; at least two carry the brand name or core keyword.
  Performance Max works in batches of **5 / 10 / 15** (5 minimum; deliver 15 when the client is ready to upload).
- Long headlines (PMax only) ≤ 90 chars, complete sentences.
- Descriptions ≤ 90 chars, each with a call to action; RSA needs 2–4, PMax 4.
- Display path ≤ 15 chars per segment, no spaces. Sitelinks and callouts ≤ 25 chars.
- Title Case or sentence case consistently within a set. No ALL CAPS, no repeated punctuation.

## 4. Voice adaptation

Read the identity block for the dominant trait (`#1`) and the supporting trait (`#2`): the first shapes hooks and
headlines, the second shapes body and CTA tone. Mirror vocabulary from existing copy without repeating lines
verbatim. When existing copy is provided, the new set should sit next to it without a visible seam.

## 5. Workflow

Run the scripts from this folder. They need the `ad-copywriter` tool: its Python package is found when it is installed,
when the hub has `tools/ad-copywriter`, or through `AD_COPYWRITER_ROOT`. Without the tool, steps 1, 3, 4 and 5 are not
available: write the document by hand from [references/copy_document.md](references/copy_document.md), check every
option against [references/platform_limits.md](references/platform_limits.md) yourself (count characters, say that you
counted by hand), and deliver the copy as a table. Say which steps were skipped and why.

1. **Scaffold** a document (or hand-write one following [references/copy_document.md](references/copy_document.md)):
   ```bash
   python scripts/new_document.py --platform meta --brand "Northpeak" --website https://example.com \
       --identity-file brand_identity.md --themes "Steel Bottle 32 oz" "Daily Commute" --out copy.json
   # or import what the client already runs:
   python scripts/new_document.py --platform meta --brand "Northpeak" --from-legacy-xlsx existing.xlsx --out copy.json
   ```
2. **Write** the options into `sets[].fields` (`primary_text`, `headline`, `description`; Google adds
   `long_headline`, `path`, `sitelink`, `callout`). Fill `landing_page_url`, `display_url`, `cta`, and `media_path`
   (a product image for the mockups, optional).
3. **Validate** and fix until it passes:
   ```bash
   python scripts/validate.py copy.json --write
   ```
   Errors (over limit, too many/few options, duplicates, `!` in Google headlines) must be fixed.
   Warnings (hook beyond the 125 fold, missing `...` structure, no emoji lead, over the word budget, no CTA block)
   are rewrite prompts: fix them unless the user waived them. `--strict` turns warnings into failures.
4. **Export** for the client:
   ```bash
   python scripts/export.py copy.json --out out/ --format xlsx csv docx --layout both
   ```
   `assets` layout = the oosamarketing.com tool sheet (`Asset Type | Content | Character Count`);
   `legacy` layout = one sheet per theme with `Primary Text | Headline | Description` columns.
5. **Preview**: hand the same `copy.json` to the `ad-copy-pdf-preview` skill (`../pdf_preview/scripts/render_preview.py copy.json --style both --pdf --out out/`).
6. **Present** the options per theme in a table (field × option, with character counts), list the file paths,
   and ask which options to keep. Don't rename themes the user gave you: they become sheet names and deck sections.

## 6. Headless option (secondary)

`python scripts/generate.py --brief brief.json --out copy.json` asks the Anthropic API (`claude-opus-5`, structured
JSON output) to write a first draft with the same rules; it still needs `validate.py` and your review. Requires
`pip install anthropic` and `ANTHROPIC_API_KEY`. `--dry-run` prints the prompts without calling the API.
Prefer writing the copy yourself: it is faster to iterate and there is no key to manage.

## 7. Document JSON (short form)

```json
{"schema_version": 1, "platform": "meta",
 "brand": {"name": "Northpeak", "website": "https://example.com", "identity": "…"},
 "sets": [{"theme": "Steel Bottle 32 oz", "landing_page_url": "https://…", "display_url": "example.com", "cta": "Shop now",
           "fields": {"primary_text": ["🧊 Hook\n...\nBody\n...\nCTA"], "headline": ["…"], "description": ["…"]}}]}
```
`python scripts/validate.py --print-spec meta` prints every field with its limits. The validator output has
`errors[]`, `warnings[]` (each with `set`, `field`, `index`, `code`, `message`) and a per-set `summary` of counts.

## 8. Don'ts

- Don't paste model output through `eval` or any code path: it is JSON or it is text you wrote.
- Don't put credentials, tokens or client PII in the document.
- Don't exceed the spec counts to "give extra options": add a second set instead.
- Don't skip validation before export; the scripts refuse to export errors without `--force`.
