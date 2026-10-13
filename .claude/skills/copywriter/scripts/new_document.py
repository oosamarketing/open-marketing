#!/usr/bin/env python3
"""Scaffold a copy document so the agent starts from the right shape.

    python new_document.py --platform meta --brand "Northpeak" --themes "Steel Bottle 32 oz" "Daily Commute" --out copy.json
    python new_document.py --platform meta --brand "Northpeak" --from-legacy-xlsx existing.xlsx --out copy.json
    python new_document.py --platform google_pmax --brand "Northpeak" --from-assets-xlsx google-ads-copywriting-assets.xlsx --out copy.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from ad_copywriter.document import dump_document, from_assets_xlsx, from_legacy_xlsx, new_document
from ad_copywriter.spec import platform_keys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform", required=True, choices=platform_keys())
    ap.add_argument("--brand", required=True, help="brand name")
    ap.add_argument("--website", default="")
    ap.add_argument("--identity-file", help="markdown / text file with the brand identity")
    ap.add_argument("--logo", help="logo path for previews")
    ap.add_argument("--themes", nargs="*", default=None, help="one set per theme")
    ap.add_argument("--from-legacy-xlsx", help="import sheet-per-theme xlsx (Primary Text | Headline | Description)")
    ap.add_argument("--from-assets-xlsx", help="import site-tool xlsx (Asset Type | Content | Character Count)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    identity = Path(args.identity_file).read_text(encoding="utf-8").strip() if args.identity_file else ""
    extra = {"website": args.website, "identity": identity, "logo_path": args.logo}
    if args.from_legacy_xlsx:
        doc = from_legacy_xlsx(args.from_legacy_xlsx, args.platform, args.brand, **extra)
    elif args.from_assets_xlsx:
        doc = from_assets_xlsx(args.from_assets_xlsx, args.platform, args.brand, **extra)
    else:
        doc = new_document(args.platform, args.brand, themes=args.themes, **extra)
    dump_document(doc, args.out)
    print(f"wrote {args.out} ({len(doc.sets)} set(s): {', '.join(doc.themes)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
