#!/usr/bin/env python3
"""Validate a copy document against platform limits and the OOSA house style.

    python validate.py copy.json                # human-readable report, exit 1 on errors
    python validate.py copy.json --write        # also store the result in copy.json["validation"]
    python validate.py copy.json --json         # machine-readable result
    python validate.py --print-spec meta        # show the limits for a platform
"""

from __future__ import annotations

import argparse
import json
import sys

import _bootstrap  # noqa: F401

from ad_copywriter.document import dump_document, load_document
from ad_copywriter.spec import get_platform, platform_keys
from ad_copywriter.validate import apply_validation, validate_document


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("document", nargs="?", help="path to a copy document JSON")
    ap.add_argument("--write", action="store_true", help="store the validation result back into the document")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--print-spec", metavar="PLATFORM", choices=platform_keys(), help="print limits and exit")
    args = ap.parse_args(argv)

    if args.print_spec:
        print(json.dumps(get_platform(args.print_spec).to_dict(), indent=2))
        return 0
    if not args.document:
        ap.error("document is required unless --print-spec is used")

    try:
        doc = load_document(args.document)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"cannot load document: {exc}", file=sys.stderr)
        return 2

    result = apply_validation(doc, strict=args.strict) if args.write else validate_document(doc, strict=args.strict)
    if args.write:
        dump_document(doc, args.document)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) if args.json else result.format_text())
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
