"""Export a copy document to xlsx / csv / docx.

Two xlsx layouts:
- ``legacy``: one sheet per theme, columns = field labels (``Primary Text | Headline | Description``),
  one option per row. The format the original pipeline read and wrote.
- ``assets``: the oosamarketing.com copywriting-tool layout — ``Asset Type | Content | Character Count``
  with fixed numbered rows (``Headline 1..15``) followed by URL / audience rows.
"""

from __future__ import annotations

from pathlib import Path

from ..document import CopyDocument
from ..textutil import slugify
from .csv import write_assets_csv
from .docx import write_docx
from .xlsx import write_assets_xlsx, write_legacy_xlsx

FORMATS = ("xlsx", "csv", "docx")
LAYOUTS = ("legacy", "assets", "both")


def default_basename(doc: CopyDocument) -> str:
    return f"{slugify(doc.brand_name)}-{doc.platform.replace('_', '-')}"


def export_all(
    doc: CopyDocument,
    out_dir: str | Path,
    *,
    formats: tuple[str, ...] | list[str] = ("xlsx",),
    layout: str = "both",
    basename: str | None = None,
    logo: str | Path | None = None,
) -> dict[str, list[Path]]:
    """Write the requested files and return ``{format: [paths]}``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = basename or default_basename(doc)
    spec = doc.spec
    written: dict[str, list[Path]] = {}

    for fmt in formats:
        if fmt not in FORMATS:
            raise ValueError(f"unknown format {fmt!r}; expected one of {FORMATS}")
    if layout not in LAYOUTS:
        raise ValueError(f"unknown layout {layout!r}; expected one of {LAYOUTS}")

    if "xlsx" in formats:
        paths = []
        if layout in ("assets", "both"):
            paths.append(write_assets_xlsx(doc, out / f"{spec.export_filename}.xlsx"))
        if layout in ("legacy", "both"):
            paths.append(write_legacy_xlsx(doc, out / f"{base}-legacy.xlsx"))
        written["xlsx"] = paths
    if "csv" in formats:
        written["csv"] = write_assets_csv(doc, out, spec.export_filename)
    if "docx" in formats:
        written["docx"] = [write_docx(doc, out / f"{base}-copy-deck.docx", logo=logo)]
    return written


__all__ = ["export_all", "default_basename", "write_assets_xlsx", "write_legacy_xlsx",
           "write_assets_csv", "write_docx", "FORMATS", "LAYOUTS"]
