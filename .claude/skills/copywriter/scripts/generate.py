#!/usr/bin/env python3
"""Headless generation via the Anthropic API (secondary path — prefer writing the copy as the agent).

    python generate.py --brief brief.json --out copy.json
    python generate.py --brief brief.json --out copy.json --model claude-opus-5 --options 3
    python generate.py --brief brief.json --dry-run          # print prompts + schema, no API call

brief.json: {"platform": "meta", "brand": {"name", "website", "identity"}, "themes": ["Fall Sale"],
             "existing_copy": {...optional copy document or list...}, "options": 3,
             "landing_page_url": "...", "display_url": "...", "cta": "Shop now", "instructions": "..."}
Needs `pip install anthropic` and ANTHROPIC_API_KEY (or an `ant auth login` profile).
"""

from __future__ import annotations

import argparse
import json
import sys

import _bootstrap  # noqa: F401

from ad_copywriter.document import dump_document
from ad_copywriter.generate import DEFAULT_MODEL, dry_run, generate_copy


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--out")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--options", type=int, help="options per field (default from brief or 3)")
    ap.add_argument("--platform", help="override brief.platform")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    with open(args.brief, encoding="utf-8") as fh:
        brief = json.load(fh)
    if args.platform:
        brief["platform"] = args.platform
    if "platform" not in brief:
        ap.error("brief needs a platform (or pass --platform)")

    if args.dry_run:
        print(json.dumps(dry_run(brief, options=args.options), indent=2, ensure_ascii=False))
        return 0
    if not args.out:
        ap.error("--out is required unless --dry-run")

    try:
        doc = generate_copy(brief, model=args.model, options=args.options)
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    dump_document(doc, args.out)
    v = doc.validation or {}
    print(f"wrote {args.out}: {len(doc.sets)} set(s); validation ok={v.get('ok')} "
          f"errors={len(v.get('errors', []))} warnings={len(v.get('warnings', []))}")
    return 0 if v.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
