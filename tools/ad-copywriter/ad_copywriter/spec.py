"""Platform spec: the single source of truth for fields, limits, labels and sheet names.

Backed by ``data/platform_spec.json``. Nothing else in the package hardcodes a
character limit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_SPEC_PATH = Path(__file__).resolve().parent / "data" / "platform_spec.json"


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    plural: str
    max_chars: int
    count: int
    min_count: int = 0
    fold_chars: int | None = None
    legacy_column: str | None = None
    multiline: bool = False
    optional: bool = False
    numbered: bool = True
    batches: tuple[int, ...] | None = None
    style: dict = field(default_factory=dict)

    def row_label(self, index: int) -> str:
        """Asset-sheet label, e.g. ``Headline 3`` (1-based). Unnumbered fields use the label."""
        if not self.numbered or self.count == 1:
            return self.label
        return f"{self.label} {index + 1}"


@dataclass(frozen=True)
class RowSpec:
    key: str
    label: str


@dataclass(frozen=True)
class PlatformSpec:
    key: str
    label: str
    deck_title: str
    deck_subtitle: str
    sheet_name: str
    export_filename: str
    mockup: str
    fields: tuple[FieldSpec, ...]
    rows: tuple[RowSpec, ...]
    optional_rows: tuple[RowSpec, ...]
    legacy_columns: tuple[str, ...]

    def field(self, key: str) -> FieldSpec:
        for f in self.fields:
            if f.key == key:
                return f
        raise KeyError(f"unknown field {key!r} for platform {self.key!r}")

    @property
    def field_keys(self) -> list[str]:
        return [f.key for f in self.fields]

    def legacy_field_for_column(self, column: str) -> FieldSpec | None:
        norm = column.strip().lower()
        for f in self.fields:
            if f.legacy_column and f.legacy_column.lower() == norm:
                return f
            if f.label.lower() == norm or f.key == norm:
                return f
        return None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "deck_title": self.deck_title,
            "sheet_name": self.sheet_name,
            "export_filename": self.export_filename,
            "mockup": self.mockup,
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "max_chars": f.max_chars,
                    "fold_chars": f.fold_chars,
                    "count": f.count,
                    "min_count": f.min_count,
                    "optional": f.optional,
                    "multiline": f.multiline,
                    "batches": list(f.batches) if f.batches else None,
                    "style": dict(f.style),
                }
                for f in self.fields
            ],
            "rows": [r.label for r in self.rows],
            "optional_rows": [r.label for r in self.optional_rows],
            "legacy_columns": list(self.legacy_columns),
        }


@lru_cache(maxsize=4)
def load_spec(path: str | Path | None = None) -> dict:
    """Load the raw spec JSON (cached)."""
    with open(path or _SPEC_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _field_from_dict(d: dict) -> FieldSpec:
    return FieldSpec(
        key=d["key"],
        label=d["label"],
        plural=d.get("plural", d["label"] + "s"),
        max_chars=int(d["max_chars"]),
        count=int(d["count"]),
        min_count=int(d.get("min_count", 0)),
        fold_chars=d.get("fold_chars"),
        legacy_column=d.get("legacy_column"),
        multiline=bool(d.get("multiline", False)),
        optional=bool(d.get("optional", False)),
        numbered=bool(d.get("numbered", True)),
        batches=tuple(d["batches"]) if d.get("batches") else None,
        style=dict(d.get("style", {})),
    )


@lru_cache(maxsize=16)
def get_platform(key: str, path: str | Path | None = None) -> PlatformSpec:
    spec = load_spec(path)
    try:
        p = spec["platforms"][key]
    except KeyError:
        raise KeyError(f"unknown platform {key!r}; expected one of {platform_keys(path)}") from None
    return PlatformSpec(
        key=key,
        label=p["label"],
        deck_title=p["deck_title"],
        deck_subtitle=p.get("deck_subtitle", ""),
        sheet_name=p["sheet_name"],
        export_filename=p["export_filename"],
        mockup=p["mockup"],
        fields=tuple(_field_from_dict(f) for f in p["fields"]),
        rows=tuple(RowSpec(r["key"], r["label"]) for r in p.get("rows", [])),
        optional_rows=tuple(RowSpec(r["key"], r["label"]) for r in p.get("optional_rows", [])),
        legacy_columns=tuple(p.get("legacy_columns", [])),
    )


def platform_keys(path: str | Path | None = None) -> list[str]:
    return list(load_spec(path)["platforms"].keys())


def spec_version(path: str | Path | None = None) -> int:
    return int(load_spec(path).get("spec_version", 1))


def block_separator(path: str | Path | None = None) -> str:
    return load_spec(path).get("block_separator", "...")
