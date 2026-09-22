---
name: client-workspace
description: Decide where client files live and keep them organized — brand kits, source assets, ad campaigns, Amazon content, ad copy, previews. Use this at the start of ANY work for a client or brand, before saving a single file, and whenever the user says "set up a folder", "where should this go", "new campaign", "organize this", attaches a client directory, or a tool is about to write deliverables. It recognizes folder structures that already exist and works inside them instead of imposing a new one.
---

# Client workspace

Every tool in Open Marketing writes files for a client. This skill answers one question
consistently: **where, and under what name?** The goal is that a person opening the folder six
months later finds the brand kit, the source photos, and the final ads without asking anyone.

## 1. Find the entry point (never assume)

Run the helper on whatever folder the user pointed at, or the client folder you were told about:

```bash
.venv/bin/python .claude/skills/client-workspace/scripts/workspace.py inspect "<path>"   # from the toolkit root
```

It reports what it recognizes and recommends one of three modes:

| What's there | Mode | What to do |
|---|---|---|
| Nothing, or a new client | **pure** | Create the standard layout (section 2) at `<client>/` |
| A folder that already follows this layout (has `workspace.md`, or `branding/` plus campaign folders) | **existing** | Use it as is; read `workspace.md` first |
| A client folder organized by a human before AI work started (dated folders, mixed file types, their own naming) | **entry point** | Do not reorganize it. Create or use one subfolder as the AI entry point (default name `cowork/`) and keep the standard layout inside that. Read their folders for source material; write only inside the entry point unless they ask otherwise |

Never move, rename, or delete a person's existing files to fit the layout. If their structure
already has an obvious home for something (an `Artboard Export/<SET>/` convention, an `Ads/<Month>/`
folder), mirror their convention when they ask for output there.

Create the structure with:

```bash
.venv/bin/python .claude/skills/client-workspace/scripts/workspace.py init "<client path>" [--entry cowork]   # add --root to force the client root
```

## 2. The standard layout

```
<client or entry point>/
  workspace.md            decisions and preferences for this client (read first, keep current)
  branding/
    <Brand> Brand Kit.pdf
    brand-assets/         logo/, avatar.png, palette.png, brand.json, tokens.json, brand.md
  assets/                 source material shared across projects
    photos/  products/<handle>/  elements/  resources.md (links: sheets, drives, sites)
  meta-ads/<campaign>/    assets/  previews/  final files (see section 3)
  google-ads/<campaign>/
  amazon/<product-or-line>/   gallery/  aplus/  assets/
  ad-copy/                copy documents, exports, previews/
```

Only create what the job needs. A client with one product and one campaign does not need empty
folders for channels they don't use. When a client has several product lines with their own
assets, split by line first (`bottles/`, `tumblers/`) and keep truly shared things in `shared/`.

## 3. Inside a campaign: split by what actually varies

Pick the shallowest structure that keeps files findable. Count the axes that vary (concept,
ratio, product, variation) and how many files result.

| Situation | Structure | Example |
|---|---|---|
| Few files, one or two axes (≤ ~8) | flat, axes in the filename | `fall-launch/northpeak-ice-cold-1x1.png` |
| Several concepts × several ratios, uploaded by placement | folder per ratio | `fall-launch/1x1/ice-cold.png`, `fall-launch/1.91x1/ice-cold.png` |
| Testing variations of one concept | folder per variation | `fall-launch/variation_1/1x1.png` |
| Campaign spans products | folder per product, then as above | `fall-launch/face-mask/1x1/…` |

Always keep `assets/` (inputs made for this campaign: cutouts, expanded photos) and `previews/`
(contact sheets, client preview PDFs) separate from final files so "the finals" is an obvious set.
Editable files (.ai, .svg) sit next to the PNG they belong to, same basename.

**Ask when it changes the outcome.** If the structure is a judgment call and the user will live
with it (more than ~8 files, a recurring campaign, a client they hand to someone else), ask one
short question with a recommended default: "By ratio or by concept? I'd go by ratio since Meta
uploads are per placement." If it's a handful of files, just choose and say what you chose.

## 4. Names

- Generated files: lowercase kebab-case, no spaces: `<brand>-<concept>-<ratio>.png`. Ratios as
  `1x1`, `1.91x1`, `9x16`, `4x5`. Campaign folders lead with what a person would say
  (`fall-launch`, `2026-09-prime-day`); use `YYYY-MM` when campaigns recur.
- Numbered sets that upload in order (Amazon gallery) start with the slot: `02-set.png`.
- Inside a person's pre-existing folders, follow their naming, not this one.

## 5. Record decisions in `workspace.md`

After the first job, write down what was decided so the next session (or another agent) doesn't
ask again: entry point and mode, campaign structure preference, naming exceptions, where source
material lives (links in `assets/resources.md`), anything the user said about their folders
("don't touch Ads/, that's the designer's"). Update it when a preference changes. Keep it short.

## 6. Hooking the tools up

- graphic-designer: `project.py set-location --brand <slug> "<entry>/meta-ads/<campaign>"` (or the
  folder chosen above); client-supplied images go under `<entry>/assets/`.
- brand-kit: `kit.py brands/<slug>.json --out "<entry>/branding"`.
- ad-copywriter: keep the copy document in `<entry>/ad-copy/`; previews render to `ad-copy/previews/`.
- Everything stays on the user's machine. No client files in tool repos or on servers.
