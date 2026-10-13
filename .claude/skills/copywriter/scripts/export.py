#!/usr/bin/env python3
"""Export a copy document to xlsx / csv / docx.

    python export.py copy.json --out out/                              # assets + legacy xlsx
    python export.py copy.json --out out/ --format xlsx csv docx       # everything
    python export.py copy.json --out out/ --layout legacy              # only the sheet-per-theme xlsx

Refuses to export a document with validation errors unless --force is given.
"""

from __future__ import annotations

import argparse
import json
import sys

import _bootstrap  # noqa: F401

from ad_copywriter.document import load_document
from ad_copywriter.exports import FORMATS, LAYOUTS, export_all
from ad_copywriter.validate import validate_document


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("document")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--format", nargs="+", default=["xlsx"], choices=FORMATS)
    ap.add_argument("--layout", default="both", choices=LAYOUTS, help="xlsx layout (default both)")
    ap.add_argument("--basename", help="file basename override (default <brand>-<platform>)")
    ap.add_argument("--logo", help="logo image for the docx header")
    ap.add_argument("--force", action="store_true", help="export even if validation has errors")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    doc = load_document(args.document)
    result = validate_document(doc)
    if not result.ok and not args.force:
        print(result.format_text(), file=sys.stderr)
        print("refusing to export a document with errors (use --force to override)", file=sys.stderr)
        return 1

    written = export_all(doc, args.out, formats=args.format, layout=args.layout, basename=args.basename, logo=args.logo)
    if args.json:
        print(json.dumps({k: [str(p) for p in v] for k, v in written.items()}, indent=2))
    else:
        for fmt, paths in written.items():
            for p in paths:
                print(f"{fmt:5} {p}")
        if result.warnings:
            print(f"({len(result.warnings)} validation warnings — run validate.py for details)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
