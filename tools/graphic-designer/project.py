#!/usr/bin/env python
"""
project.py — Where deliverables and user-supplied assets get saved (LOCAL ONLY).

Rule: everything we produce or receive for a brand is saved on this Mac under the brand's
export folder on this machine, never on a server. Default folder:

    ~/Downloads/<Brand display name> Infographics/
        water-bottle.png            rendered deliverables
        water-bottle.ai
        assets/water-bottle.png     images the user gave us to use in the design

Usage
-----
    PY=../../.venv/bin/python

    $PY project.py where --brand northpeak                    # print the export folder
    $PY project.py set-location --brand northpeak ~/Desktop/NP   # user prefers another place
    $PY project.py asset ~/Downloads/IMG_1234.jpg --brand northpeak --name water-bottle.jpg
        # copies the file into <export>/assets/ and prints the absolute path to use in data JSON

render.py --deliver uses the same folder for its output.
Config lives in export-locations.json (default root, folder pattern, per-brand overrides).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG = ROOT / "export-locations.json"          # local, git-ignored; copy from export-locations.example.json
if not CONFIG.exists():
    import shutil as _sh; _sh.copy(ROOT / "export-locations.example.json", CONFIG)
BRANDS = ROOT / "brand-guidelines" / "brands"


def load_config() -> dict:
    return json.loads(CONFIG.read_text())


def save_config(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")


def brand_display_name(slug: str) -> str:
    tokens = BRANDS / slug / "tokens.json"
    if tokens.exists():
        t = json.loads(tokens.read_text())
        return t.get("display_name") or t.get("name") or slug
    return slug.replace("-", " ").title()


def export_dir(slug: str, create: bool = True) -> Path:
    cfg = load_config()
    override = cfg.get("brands", {}).get(slug, {}).get("export_dir")
    if override:
        d = Path(override).expanduser()
    else:
        d = Path(cfg["default_root"]).expanduser() / cfg["folder_pattern"].format(brand=brand_display_name(slug))
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def assets_dir(slug: str) -> Path:
    d = export_dir(slug) / load_config().get("assets_subdir", "assets")
    d.mkdir(parents=True, exist_ok=True)
    return d


def set_location(slug: str, path: str) -> Path:
    cfg = load_config()
    cfg.setdefault("brands", {}).setdefault(slug, {})["export_dir"] = path
    save_config(cfg)
    return export_dir(slug)


def save_asset(src: Path, slug: str, name: str | None = None) -> Path:
    dest = assets_dir(slug) / (name or src.name)
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest


def deliver(src: Path, slug: str, name: str | None = None) -> Path:
    dest = export_dir(slug) / (name or src.name)
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("where"); w.add_argument("--brand", required=True)
    s = sub.add_parser("set-location"); s.add_argument("path"); s.add_argument("--brand", required=True)
    a = sub.add_parser("asset"); a.add_argument("src", type=Path); a.add_argument("--brand", required=True); a.add_argument("--name")
    d = sub.add_parser("deliver"); d.add_argument("src", type=Path); d.add_argument("--brand", required=True); d.add_argument("--name")
    args = ap.parse_args(argv)
    if args.cmd == "where":
        print(export_dir(args.brand, create=False))
    elif args.cmd == "set-location":
        print(set_location(args.brand, args.path))
    elif args.cmd == "asset":
        print(save_asset(args.src, args.brand, args.name))
    elif args.cmd == "deliver":
        print(deliver(args.src, args.brand, args.name))


if __name__ == "__main__":
    sys.exit(main())
