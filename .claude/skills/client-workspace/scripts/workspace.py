#!/usr/bin/env python3
"""
workspace.py — inspect or scaffold a client workspace (see ../SKILL.md).

    python workspace.py inspect "<path>"                 # what is here, which mode, where to write
    python workspace.py init "<client path>" [--entry cowork] [--only branding assets meta-ads]

inspect never changes anything. init only creates folders and a workspace.md; it never moves files.
"""
from __future__ import annotations
import argparse, json, re, sys
from datetime import date
from pathlib import Path

STANDARD = ["branding", "assets", "meta-ads", "google-ads", "amazon", "ad-copy"]
ENTRY_NAMES = ["cowork", "ai", "workspace", "_ai", "agent"]
KNOWN = set(STANDARD) | {"ads", "shared", "previews"}


def scan(path: Path) -> dict:
    kids = [p for p in path.iterdir() if not p.name.startswith(".")] if path.is_dir() else []
    dirs = [p.name for p in kids if p.is_dir()]; files = [p.name for p in kids if p.is_file()]
    low = {d.lower() for d in dirs}
    entry = next((d for d in dirs if d.lower() in ENTRY_NAMES), None)
    standardish = len(low & KNOWN)
    humanish = sum(1 for d in dirs if re.search(r"\b(19|20)\d{2}\b|january|february|march|april|may|june|july|august|september|october|november|december|final|old|v\d", d, re.I)) \
        + sum(1 for d in dirs if " " in d) + (1 if len(files) > 6 else 0)
    if not dirs and len(files) <= 3: humanish = 0          # a couple of loose files is not a structure
    has_ws = (path / "workspace.md").exists()
    if not path.exists() or not kids or (not dirs and len(files) <= 3):
        mode, root = "pure", path
    elif has_ws or (standardish >= 2 and humanish <= 1) or (standardish >= 1 and humanish == 0 and not entry):
        mode, root = "existing", path
    elif entry:
        mode, root = "entry point", path / entry
    elif path.name.lower() in ENTRY_NAMES:
        mode, root = "existing", path
    else:
        mode, root = "entry point", path / "cowork"
    return {"path": str(path), "mode": mode, "write_root": str(root), "write_root_exists": root.exists(),
            "has_workspace_md": (root / "workspace.md").exists(), "dirs": sorted(dirs)[:40], "loose_files": len(files),
            "recognized": sorted(low & KNOWN), "human_signals": humanish,
            "note": {"pure": "Empty or new: create the standard layout here.",
                     "existing": "Already organized for this workflow: use it and read workspace.md first.",
                     "entry point": "Pre-existing human structure: leave it alone and work inside the entry-point subfolder."}[mode]}


def init(path: Path, entry: str | None, only: list[str] | None, root_flag: bool = False) -> Path:
    info = scan(path); root = path / entry if entry else (path if root_flag else Path(info["write_root"]))
    for d in (only or ["branding", "assets"]):
        (root / d).mkdir(parents=True, exist_ok=True)
    ws = root / "workspace.md"
    if not ws.exists():
        ws.write_text(f"""# Workspace — {path.name}

- **Entry point:** `{root}` ({'inside an existing client folder; nothing outside this folder is modified' if root != path else 'client root'})
- **Created:** {date.today():%Y-%m-%d}

## Preferences
- Campaign structure: _not decided yet_ (flat / by ratio / by variation / by product)
- Naming: lowercase-kebab, `<brand>-<concept>-<ratio>.png`
- Notes from the client about their folders: _none yet_

## Where things are
- Brand kit: `branding/`
- Source material and links: `assets/` (`assets/resources.md`)
""")
    return root


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inspect"); i.add_argument("path", type=Path)
    n = sub.add_parser("init"); n.add_argument("path", type=Path); n.add_argument("--entry"); n.add_argument("--root", action="store_true", help="use the client folder itself even if it has other files"); n.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    if a.cmd == "inspect": print(json.dumps(scan(a.path.expanduser()), indent=2))
    else: print(init(a.path.expanduser(), a.entry, a.only, a.root))


if __name__ == "__main__":
    sys.exit(main())
