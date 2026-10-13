#!/usr/bin/env python3
"""Render a copy document to the branded copy deck and/or platform mockups (HTML, optionally PDF).

    python render_preview.py copy.json --out out/                     # both styles, HTML
    python render_preview.py copy.json --out out/ --pdf               # + PDF (needs weasyprint)
    python render_preview.py copy.json --out out/ --style deck --pdf
    python render_preview.py copy.json --out out/ --style mockup --combos 2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from ad_copywriter.document import load_document
from ad_copywriter.exports import default_basename
from ad_copywriter.preview import STYLES, html_to_pdf, render_html
from ad_copywriter.validate import validate_document


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("document")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--style", default="both", choices=STYLES)
    ap.add_argument("--pdf", action="store_true", help="also write a PDF (WeasyPrint)")
    ap.add_argument("--logo", help="logo image path or URL (default: brand.logo_path, else the OOSA logo)")
    ap.add_argument("--avatar", help="round page avatar for the mockups (default: brand.avatar_path, else --logo)")
    ap.add_argument("--make-avatar", metavar="HEX", help="build the avatar from the logo on this background color (e.g. #0F6E6E)")
    ap.add_argument("--mockups-first", action="store_true", help="in --style both, put the platform mockups before the copy deck")
    ap.add_argument("--title")
    ap.add_argument("--subtitle")
    ap.add_argument("--date")
    ap.add_argument("--combos", type=int, default=3, help="mockup variations per theme (default 3)")
    ap.add_argument("--no-fonts", action="store_true", help="skip bundled Montserrat @font-face rules")
    ap.add_argument("--embed", action="store_true", help="embed fonts/logo as data URIs (portable single-file HTML)")
    ap.add_argument("--no-counts", action="store_true", help="hide character counts in the deck")
    ap.add_argument("--basename")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    doc = load_document(args.document)
    result = validate_document(doc)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = args.basename or default_basename(doc)
    suffix = {"deck": "deck", "mockup": "mockup", "both": "preview"}[args.style]

    avatar = args.avatar
    if args.make_avatar:
        from ad_copywriter.preview.avatar import make_avatar
        src = args.logo or doc.brand.get("logo_path")
        if not src:
            print("--make-avatar needs --logo or brand.logo_path", file=sys.stderr)
            return 2
        avatar = str(make_avatar(src, out / f"{base}-avatar.png", bg=args.make_avatar))
    html = render_html(doc, args.style, logo=args.logo, title=args.title, subtitle=args.subtitle, date=args.date,
                       combos=args.combos, fonts=not args.no_fonts, embed_assets=args.embed, show_counts=not args.no_counts,
                       avatar=avatar, mockups_first=args.mockups_first)
    html_path = out / f"{base}-{suffix}.html"
    html_path.write_text(html, encoding="utf-8")
    paths = {"html": str(html_path)}
    if args.pdf:
        try:
            pdf_path = html_to_pdf(html, out / f"{base}-{suffix}.pdf")
        except ImportError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        paths["pdf"] = str(pdf_path)

    if args.json:
        print(json.dumps({"paths": paths, "validation_ok": result.ok, "errors": len(result.errors),
                          "warnings": len(result.warnings)}, indent=2))
    else:
        for k, v in paths.items():
            print(f"{k:4} {v}")
        if not result.ok:
            print(f"note: document has {len(result.errors)} validation error(s) — preview rendered anyway", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
