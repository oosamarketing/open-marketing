"""csv writer — one file per set in the site-tool ``Asset Type | Content | Character Count`` layout."""

from __future__ import annotations

import csv
from pathlib import Path

from ..document import CopyDocument
from ..textutil import slugify
from .xlsx import assets_rows


def write_assets_csv(doc: CopyDocument, out_dir: str | Path, basename: str) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    spec = doc.spec
    for cs in doc.sets:
        name = f"{basename}.csv" if len(doc.sets) == 1 else f"{basename}-{slugify(cs.theme)}.csv"
        path = out / name
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["Asset Type", "Content", "Character Count"])
            for row in assets_rows(cs, spec):
                w.writerow(row)
        paths.append(path)
    return paths
