"""Prompt builders for headless generation (secondary path).

The house style lives in ``skills/copywriter/SKILL.md``; this module is a distilled
copy for API use so the generator and the agent write the same way. Keep the two
in sync when the style changes.
"""

from __future__ import annotations

import json
from typing import Any

from .spec import PlatformSpec, get_platform

META_STYLE = """\
House style for Meta primary text (Facebook / Instagram feed):
- Three blocks separated by a line that contains only "..." :
  1. an emoji-led hook of one or two short lines that must stand alone within 125 characters
     (that is what shows before "See more");
  2. body copy with the concrete product / offer / place detail;
  3. optionally another "..." line, then a single call-to-action line.
- Headlines: at most 12 words and 40 characters; they drive action.
- Descriptions: at most 8 words and 30 characters.
- Each option takes a different angle (seasonal, identity, social proof, urgency, product detail).
- No hashtags, no ALL CAPS, one emoji in the hook (a second in the CTA is fine), no claims the
  brand identity does not support, never invent prices or offers."""

GOOGLE_STYLE = """\
House style for Google Ads text assets:
- Headlines: at most 30 characters, no exclamation marks, each a distinct angle; include at least two
  that name the brand or the core keyword. Performance Max works in batches of 5 / 10 / 15.
- Long headlines (Performance Max only): at most 90 characters, complete sentences.
- Descriptions: at most 90 characters, each ending in or containing a call to action.
- Display path segments: at most 15 characters, no spaces. Sitelinks and callouts: at most 25 characters.
- Sentence case or title case, never ALL CAPS, no repeated punctuation."""

EXAMPLES = {
    "meta": {
        "primary_text": (
            "🧊 Ice cold for 24 hours. Fill it in the morning, drink it cold at night.\n"
            "...\n"
            "Triple-wall vacuum insulation in 18/8 stainless steel. 32 oz, leak-proof lid, fits your cup holder.\n"
            "...\n"
            "Get the bottle that keeps up with your day."
        ),
        "headline": "Ice cold for 24 hours.",
        "description": "Leak-proof. Fits cup holders.",
    }
}


def build_system_prompt(platform: PlatformSpec | str) -> str:
    spec = get_platform(platform) if isinstance(platform, str) else platform
    style = META_STYLE if spec.key == "meta" else GOOGLE_STYLE
    limits = "\n".join(
        f"- {f.label}: up to {f.count} options, max {f.max_chars} characters each"
        + (f", first block within {f.fold_chars} characters" if f.fold_chars else "")
        + (" (optional)" if f.optional else "")
        for f in spec.fields
    )
    example = ""
    if spec.key in EXAMPLES:
        example = "\nReference examples of the voice (do not copy them):\n" + "\n".join(
            f"- {k}: {json.dumps(v, ensure_ascii=False)}" for k, v in EXAMPLES[spec.key].items()
        )
    return (
        f"You are a senior direct-response copywriter writing {spec.label} copy for OOSA Marketing's clients. "
        "You write from a theme, a brand identity, and (when given) examples of the brand's existing ads. "
        "Use only the theme, identity and examples you are given for facts.\n\n"
        f"{style}\n\nPlatform limits:\n{limits}\n{example}\n\n"
        "Return only JSON matching the provided schema. Count characters carefully; stay under every limit."
    )


def build_user_prompt(brief: dict[str, Any]) -> str:
    brand = brief.get("brand") or {}
    themes = brief.get("themes") or ["Untitled theme"]
    options = int(brief.get("options") or 3)
    lines = [
        f"Brand: {brand.get('name', 'the brand')}",
    ]
    if brand.get("website"):
        lines.append(f"Website: {brand['website']}")
    if brand.get("identity"):
        lines.append(f"\nBrand identity:\n{brand['identity']}")
    if brief.get("context"):
        lines.append(f"\nAdditional context:\n{brief['context']}")
    existing = brief.get("existing_copy")
    if existing:
        lines.append("\nExisting ad copy to match in voice (do not repeat verbatim):")
        lines.append(json.dumps(existing, ensure_ascii=False, indent=2))
    lines.append("\nWrite one set per theme, with " f"{options} options for each field:")
    for t in themes:
        lines.append(f"- Theme: {t}")
    if brief.get("instructions"):
        lines.append(f"\nExtra instructions: {brief['instructions']}")
    return "\n".join(lines)


def output_schema_for(platform: PlatformSpec | str, *, options: int = 3) -> dict[str, Any]:
    """JSON schema for structured output: ``{"sets": [{"theme", "fields": {...}}]}``."""
    spec = get_platform(platform) if isinstance(platform, str) else platform
    fields_props = {}
    required = []
    for f in spec.fields:
        max_items = min(f.count, max(options, f.min_count)) if f.key != "path" else f.count
        fields_props[f.key] = {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": max_items,
            "description": f"{f.label}: max {f.max_chars} characters each",
        }
        if not f.optional:
            required.append(f.key)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["sets"],
        "properties": {
            "sets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["theme", "fields"],
                    "properties": {
                        "theme": {"type": "string"},
                        "fields": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": required,
                            "properties": fields_props,
                        },
                    },
                },
            }
        },
    }
