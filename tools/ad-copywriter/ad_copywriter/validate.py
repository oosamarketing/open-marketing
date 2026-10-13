"""Deterministic validation of a copy document against the platform spec and house style.

Errors block export (unless forced). Warnings are rewrite prompts for the agent.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .document import CopyDocument, CopySet
from .spec import FieldSpec, PlatformSpec, spec_version
from .textutil import (
    count_chars,
    has_block_separator,
    has_emoji_lead,
    is_all_caps,
    split_blocks,
    word_count,
)

CTA_VERBS = (
    "shop", "get", "grab", "order", "try", "save", "discover", "see", "book", "visit",
    "claim", "buy", "start", "join", "learn", "explore", "find", "sign", "download",
    "unlock", "upgrade", "reserve", "browse", "check", "tap", "click", "gear up", "step",
)

ERROR_CODES = {
    "unknown_field",
    "empty_value",
    "over_max",
    "too_many_options",
    "too_few_options",
    "duplicate_option",
    "google_exclamation_in_headline",
    "newline_in_field",
    "spaces_in_path",
}


@dataclass
class Issue:
    set: str | None
    field: str | None
    index: int | None
    code: str
    message: str
    chars: int | None = None
    limit: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    checked_at: str = ""
    spec_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checked_at": self.checked_at,
            "spec_version": self.spec_version,
            "errors": [i.to_dict() for i in self.errors],
            "warnings": [i.to_dict() for i in self.warnings],
            "summary": self.summary,
        }

    def format_text(self) -> str:
        lines = []
        for kind, items in (("ERROR", self.errors), ("WARN", self.warnings)):
            for i in items:
                where = f"{i.set or '-'} / {i.field or '-'}"
                if i.index is not None:
                    where += f" #{i.index + 1}"
                lines.append(f"{kind:5} {where:40} {i.code:30} {i.message}")
        lines.append("OK" if self.ok else f"FAILED ({len(self.errors)} errors, {len(self.warnings)} warnings)")
        return "\n".join(lines)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _check_option(cs: CopySet, f: FieldSpec, idx: int, text: str, platform: PlatformSpec,
                  errors: list[Issue], warnings: list[Issue]) -> None:
    n = count_chars(text)
    if not text.strip():
        errors.append(Issue(cs.theme, f.key, idx, "empty_value", f"{f.label} {idx + 1} is empty"))
        return
    if n > f.max_chars:
        errors.append(Issue(cs.theme, f.key, idx, "over_max",
                            f"{f.label} {idx + 1} is {n} chars (max {f.max_chars})", n, f.max_chars))
    if "\n" in text and not f.multiline:
        errors.append(Issue(cs.theme, f.key, idx, "newline_in_field", f"{f.label} {idx + 1} contains a line break"))
    if f.style.get("no_exclamation") and "!" in text:
        errors.append(Issue(cs.theme, f.key, idx, "google_exclamation_in_headline",
                            f"{f.label} {idx + 1} contains '!' (not allowed in Google headlines)"))
    if f.style.get("no_spaces") and " " in text.strip():
        errors.append(Issue(cs.theme, f.key, idx, "spaces_in_path", f"{f.label} {idx + 1} must not contain spaces"))

    max_words = f.style.get("max_words")
    if max_words and word_count(text) > max_words:
        warnings.append(Issue(cs.theme, f.key, idx, "over_max_words",
                              f"{f.label} {idx + 1} has {word_count(text)} words (house style: ≤ {max_words})",
                              word_count(text), max_words))
    if is_all_caps(text):
        warnings.append(Issue(cs.theme, f.key, idx, "all_caps", f"{f.label} {idx + 1} is all caps"))
    if "  " in text:
        warnings.append(Issue(cs.theme, f.key, idx, "double_space", f"{f.label} {idx + 1} has a double space"))
    if text != text.strip():
        warnings.append(Issue(cs.theme, f.key, idx, "trailing_space", f"{f.label} {idx + 1} has leading/trailing whitespace"))

    if f.style.get("blocks"):
        blocks = split_blocks(text)
        if not has_block_separator(text):
            warnings.append(Issue(cs.theme, f.key, idx, "missing_block_structure",
                                  f"{f.label} {idx + 1} has no '...' separator lines (house style: hook ... body ... CTA)"))
        hook = blocks[0] if blocks else text
        if f.fold_chars and count_chars(hook) > f.fold_chars:
            warnings.append(Issue(cs.theme, f.key, idx, "hook_beyond_fold",
                                  f"{f.label} {idx + 1} hook is {count_chars(hook)} chars; keep the first block within "
                                  f"{f.fold_chars} so it reads before 'See more'", count_chars(hook), f.fold_chars))
        if f.style.get("emoji_lead") and not has_emoji_lead(hook):
            warnings.append(Issue(cs.theme, f.key, idx, "missing_emoji_lead",
                                  f"{f.label} {idx + 1} hook does not open with an emoji"))
        if f.style.get("cta_block") and blocks:
            last = blocks[-1].lower()
            if not any(v in last for v in CTA_VERBS):
                warnings.append(Issue(cs.theme, f.key, idx, "no_cta_block",
                                      f"{f.label} {idx + 1} last block doesn't read like a call to action"))
    elif f.fold_chars and n > f.fold_chars:
        warnings.append(Issue(cs.theme, f.key, idx, "over_fold", f"{f.label} {idx + 1} exceeds the {f.fold_chars}-char fold", n, f.fold_chars))


def validate_document(doc: CopyDocument, *, strict: bool = False) -> ValidationResult:
    platform = doc.spec
    errors: list[Issue] = []
    warnings: list[Issue] = []
    summary: dict[str, Any] = {}

    if not doc.sets:
        errors.append(Issue(None, None, None, "no_sets", "document has no sets"))

    seen_themes: set[str] = set()
    for cs in doc.sets:
        if not cs.theme.strip():
            errors.append(Issue(cs.theme, None, None, "empty_theme", "a set has an empty theme"))
        if _norm(cs.theme) in seen_themes:
            warnings.append(Issue(cs.theme, None, None, "duplicate_theme", f"theme '{cs.theme}' appears more than once"))
        seen_themes.add(_norm(cs.theme))

        set_summary: dict[str, Any] = {}
        for key in cs.fields:
            if key not in platform.field_keys:
                errors.append(Issue(cs.theme, key, None, "unknown_field",
                                    f"'{key}' is not a {platform.label} field (expected {platform.field_keys})"))

        for f in platform.fields:
            options = cs.options(f.key)
            count = len(options)
            set_summary[f.key] = {
                "count": count,
                "min_count": f.min_count,
                "max_count": f.count,
                "max_chars": f.max_chars,
                "fold_chars": f.fold_chars,
                "chars": [count_chars(o) for o in options],
            }
            if count > f.count:
                errors.append(Issue(cs.theme, f.key, None, "too_many_options",
                                    f"{count} {f.plural.lower()} given; {platform.label} allows {f.count}", count, f.count))
            if count < f.min_count:
                errors.append(Issue(cs.theme, f.key, None, "too_few_options",
                                    f"{count} {f.plural.lower()} given; at least {f.min_count} required", count, f.min_count))
            if f.batches and count and count not in f.batches:
                warnings.append(Issue(cs.theme, f.key, None, "count_below_batch",
                                      f"{count} {f.plural.lower()}; the site tool works in batches of {list(f.batches)}"))
            seen: dict[str, int] = {}
            for idx, text in enumerate(options):
                _check_option(cs, f, idx, text, platform, errors, warnings)
                k = _norm(text)
                if k and k in seen:
                    errors.append(Issue(cs.theme, f.key, idx, "duplicate_option",
                                        f"{f.label} {idx + 1} duplicates {f.label} {seen[k] + 1}"))
                seen.setdefault(k, idx)

        if cs.options("sitelink") and not cs.landing_page_url:
            warnings.append(Issue(cs.theme, "sitelink", None, "sitelink_without_landing_url",
                                  "sitelinks given but no landing_page_url on the set"))
        summary[cs.theme] = set_summary

    ok = not errors and not (strict and warnings)
    return ValidationResult(
        ok=ok,
        errors=errors,
        warnings=warnings,
        summary=summary,
        checked_at=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        spec_version=spec_version(),
    )


def apply_validation(doc: CopyDocument, *, strict: bool = False) -> ValidationResult:
    """Validate and store the result on ``doc.validation``."""
    result = validate_document(doc, strict=strict)
    doc.validation = result.to_dict()
    return result
