# Brand guidelines — read this first (for AI agents and humans)

This folder is the single source of truth for *how things should look and sound*.
Templates in `templates/` define layout; this folder defines brand, copy voice, and
platform rules. When you generate or edit a graphic, follow the precedence below.

## Precedence (highest wins)

1. The user's explicit instruction in the current conversation.
2. `brands/<brand>/brand.md` and `brands/<brand>/tokens.json` for the brand in question.
3. `general/*.md` — house rules that apply to every brand (Amazon specs, design principles).
4. Template defaults.

## How to use

- **Identify the brand.** If the user names one, use `brands/<brand>/`. If none exists,
  copy `brands/_template/` to `brands/<new-brand>/`, fill it from whatever the user gave
  you (logo, site, existing ads), and tell the user what you assumed.
- **Load tokens.** `render.py --brand <brand>` merges `tokens.json` into the template data
  under the `brand` key, so `{{ brand.color }}`, `{{ brand.name }}` etc. resolve automatically.
  Per-job data files override tokens.
- **Read `brand.md` before writing copy.** Voice, claims that are allowed/forbidden, and
  audience live there. Never invent certifications, test results, or awards.
- **Check `general/`** for the platform you're targeting (Amazon gallery vs A+ vs social).
- **Assets** (logos, product photos) live in `brands/<brand>/assets/`. Reference them from
  templates with a relative path; never hot-link external images.
- **Never hardcode brand colors or fonts in a template.** Use `{{ brand.* }}` tokens or CSS
  custom properties fed by them.

## Updating a brand

Edit `brand.md` / `tokens.json` directly. Keep `tokens.json` machine-readable (no comments)
and keep the key names listed in `_template/tokens.json` so templates keep working.
When you learn a new preference from the user (e.g. "we never use red"), write it into the
brand's `brand.md` under **Do / Don't** so the next agent inherits it.

## Layout

```
brand-guidelines/
  README.md                  this file
  general/                   rules for all brands
    design-principles.md
    amazon-listing-images.md
  brands/
    _template/               copy me to start a new brand
      brand.md
      tokens.json
      assets/
    northpeak/               example brand used by data/water-bottle.json
```


## Where files go

Deliverables and user-supplied assets are saved **locally only**, in
`~/Downloads/<display_name> Infographics/` (assets under `assets/`). `display_name` comes from
the brand's `tokens.json`. The user can point a brand somewhere else with
`project.py set-location`. Nothing is written to a server. See `AGENTS.md`.
