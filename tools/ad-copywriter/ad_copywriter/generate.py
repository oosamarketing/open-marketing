"""Optional headless generator (secondary path) — the Anthropic API writes the copy.

The primary path is an agent (Claude in Cowork / Claude Code) following
``skills/copywriter/SKILL.md``. This module exists for CLI / cron runs with no
agent in the loop. It never ``eval``s model output: structured output + JSON
parsing + the same validator the agent uses.

Requires the ``anthropic`` package (``pip install "ad-copywriter[llm]"``) and
credentials (``ANTHROPIC_API_KEY`` or an ``ant auth login`` profile).
"""

from __future__ import annotations

import datetime as _dt
import json
from typing import Any

from .document import CopyDocument, CopySet, new_document
from .prompts import build_system_prompt, build_user_prompt, output_schema_for
from .spec import get_platform
from .validate import apply_validation

DEFAULT_MODEL = "claude-opus-5"
MAX_TOKENS = 16000


def brief_to_document(brief: dict[str, Any], sets: list[dict[str, Any]], *, model: str | None) -> CopyDocument:
    brand = dict(brief.get("brand") or {})
    doc = new_document(
        brief["platform"],
        brand.get("name") or "Brand",
        themes=[],
        website=brand.get("website") or "",
        identity=brand.get("identity") or "",
        logo_path=brand.get("logo_path"),
        generated_by="generate.py",
        page_name=brand.get("page_name"),
        primary_color=brand.get("primary_color"),
        secondary_color=brand.get("secondary_color"),
        font_family=brand.get("font_family"),
    )
    doc.meta["model"] = model
    per_theme = {str(t.get("theme", "")): t for t in (brief.get("set_defaults") or [])}
    for s in sets:
        defaults = per_theme.get(str(s.get("theme", "")), {})
        doc.sets.append(
            CopySet(
                theme=str(s.get("theme") or "Untitled theme"),
                fields={k: [str(x) for x in v] for k, v in (s.get("fields") or {}).items()},
                landing_page_url=defaults.get("landing_page_url") or brief.get("landing_page_url") or "",
                display_url=defaults.get("display_url") or brief.get("display_url") or "",
                cta=defaults.get("cta") or brief.get("cta") or "Shop now",
            )
        )
    return doc


def parse_model_json(text: str) -> dict[str, Any]:
    """Parse JSON from a model reply, tolerating code fences or surrounding prose."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    if "```" in text:
        chunk = text.split("```", 2)[1]
        chunk = chunk[4:] if chunk.startswith("json") else chunk
        try:
            return json.loads(chunk.strip())
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError("model reply did not contain a JSON object")


def generate_copy(
    brief: dict[str, Any],
    *,
    model: str = DEFAULT_MODEL,
    client: Any = None,
    options: int | None = None,
) -> CopyDocument:
    """Call the Anthropic API once and return a validated CopyDocument."""
    platform = get_platform(brief["platform"])
    n_options = int(options or brief.get("options") or 3)
    brief = {**brief, "options": n_options}
    schema = output_schema_for(platform, options=n_options)

    if client is None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError("anthropic is not installed: pip install 'ad-copywriter[llm]'") from exc
        client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=build_system_prompt(platform),
        messages=[{"role": "user", "content": build_user_prompt(brief)}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError("the model declined this request (stop_reason=refusal)")
    text = "".join(getattr(b, "text", "") for b in response.content if getattr(b, "type", "") == "text")
    data = parse_model_json(text)
    doc = brief_to_document(brief, data.get("sets") or [], model=getattr(response, "model", model))
    doc.meta["created_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    apply_validation(doc)
    return doc


def dry_run(brief: dict[str, Any], *, options: int | None = None) -> dict[str, Any]:
    """Return the prompts and schema that would be sent, without calling the API."""
    platform = get_platform(brief["platform"])
    n_options = int(options or brief.get("options") or 3)
    return {
        "model": DEFAULT_MODEL,
        "system": build_system_prompt(platform),
        "user": build_user_prompt({**brief, "options": n_options}),
        "output_schema": output_schema_for(platform, options=n_options),
    }
