#!/usr/bin/env python
"""
render.py — Render an HTML/CSS graphic template to a PNG/JPG with headless Chromium.

Usage (any Python with Playwright + Chromium; the toolkit's is ../../.venv):

    PY=../../.venv/bin/python

    # Render a template with its default data at 2x (1000x1000 CSS px -> 2000x2000 image)
    $PY render.py templates/amazon-infographic-callouts.html \
        --data data/water-bottle.json --out out/water-bottle.png

    # Force a specific output size (CSS px viewport * scale)
    $PY render.py templates/foo.html --width 1080 --height 1080 --scale 2 --out out/foo.png

    # JPG at quality 90
    $PY render.py templates/foo.html --out out/foo.jpg --quality 90

    # Just build the filled-in HTML (for approving in a browser before rendering)
    $PY render.py templates/foo.html --data data/x.json --html-only --out out/foo.html

    # Load a brand kit (brand-guidelines/brands/<slug>/tokens.json) as {{ brand.* }}
    $PY render.py templates/foo.html --brand northpeak --data data/x.json --out out/foo.png

    # --deliver also copies the result to the brand's LOCAL export folder
    # (default ~/Downloads/<Brand> Infographics/, see project.py / export-locations.json)
    $PY render.py templates/foo.html --brand northpeak --data data/x.json --out out/foo.png --deliver

    # Vector export: .pdf opens in Illustrator with editable paths; .ai drives the
    # installed Illustrator to build a native file with an "Artwork" layer (vectors)
    # and a "Text" layer of live, editable text objects. --outline-text skips the
    # text layer and leaves text as it comes out of the PDF.
    # Shadows/filters are stripped (they rasterize) unless --keep-effects is given.
    $PY render.py templates/foo.html --data data/x.json --out out/foo.ai

Template conventions
--------------------
* Templates are plain HTML files. `{{ key }}` placeholders are replaced from the JSON
  data file (nested keys via dot notation: `{{ brand.name }}`). Missing keys render empty.
  `{% if key %}...{% else %}...{% endif %}` switches blocks on whether a key is set
  (e.g. real product photo vs. SVG placeholder). Absolute file paths work in <img src>.
* A template may declare its canvas in a meta tag so callers don't need --width/--height:
      <meta name="canvas" content="width=1000,height=1000,scale=2">
* The element with id="canvas" (or <body> if absent) is what gets screenshotted, so
  margins/scrollbars never leak into the output.
* Relative asset paths (assets/foo.png) resolve relative to the template file.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import ai_export
import project

VECTOR_CSS = """<style id="vector-export">
  *, *::before, *::after { box-shadow: none !important; filter: none !important;
    text-shadow: none !important; backdrop-filter: none !important; }
  html, body { background: transparent !important; }
</style>"""

ILLUSTRATOR_JSX = """
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var doc = app.open(new File("%(pdf)s"));
var opts = new IllustratorSaveOptions();
opts.pdfCompatible = true; opts.embedICCProfile = true; opts.compressed = true;
doc.saveAs(new File("%(ai)s"), opts);
doc.close(SaveOptions.DONOTSAVECHANGES);
"""

PLACEHOLDER = re.compile(r"{{\s*([a-zA-Z0-9_.]+)\s*}}")
# {% if key %}...{% else %}...{% endif %}  (no nesting; truthy = non-empty value)
CONDITIONAL = re.compile(r"{%\s*if\s+([a-zA-Z0-9_.]+)\s*%}(.*?)(?:{%\s*else\s*%}(.*?))?{%\s*endif\s*%}", re.S)
CANVAS_META = re.compile(r'<meta\s+name="canvas"\s+content="([^"]+)"', re.I)


def lookup(data: dict, dotted: str):
    cur = data
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, (list, tuple)) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return ""
    return cur


def fill(template_html: str, data: dict) -> str:
    def cond(m):
        return (m.group(2) if lookup(data, m.group(1)) else (m.group(3) or ""))
    html = CONDITIONAL.sub(cond, template_html)
    return PLACEHOLDER.sub(lambda m: str(lookup(data, m.group(1))), html)


def canvas_from_meta(html: str) -> dict:
    m = CANVAS_META.search(html)
    out = {}
    if m:
        for kv in m.group(1).split(","):
            k, _, v = kv.strip().partition("=")
            if k and v:
                out[k] = float(v) if k == "scale" else int(v)
    return out


def convert_pdf_to_ai(pdf: Path, ai: Path) -> Path:
    """Use the installed Adobe Illustrator to open a PDF and save it as a native .ai."""
    jsx = ILLUSTRATOR_JSX % {"pdf": str(pdf.resolve()), "ai": str(ai.resolve())}
    script = f'tell application "Adobe Illustrator" to do javascript "{jsx.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))}"'
    subprocess.run(["osascript", "-e", script], check=True, timeout=180)
    if not ai.exists():
        raise RuntimeError("Illustrator did not write the .ai file")
    return ai


ROOT = Path(__file__).resolve().parent
IMAGE_KEYS = ("logo", "logo_dark", "avatar", "image")


def resolve_paths(obj, base: Path, missing: list):
    """Make relative image paths absolute (against `base`) so templates work from any folder, and
    collect paths that don't exist. Brand tokens resolve against the repo root; job data against
    the data file's folder (or the repo root when the JSON came from elsewhere)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in IMAGE_KEYS and isinstance(v, str) and v and not v.startswith(("http://", "https://", "data:")):
                pth = Path(v).expanduser()
                if not pth.is_absolute():
                    cand = [base / v, ROOT / v, ROOT / "templates" / v]
                    pth = next((c for c in cand if c.exists()), cand[0])
                if not pth.exists():
                    missing.append(f"{k}: {v}")
                obj[k] = str(pth.resolve())
            else:
                resolve_paths(v, base, missing)
    elif isinstance(obj, list):
        for v in obj:
            resolve_paths(v, base, missing)


def render(template: Path, out: Path, data: dict | None = None, width: int | None = None,
           height: int | None = None, scale: float | None = None, quality: int | None = None,
           html_only: bool = False, full_page: bool = False, keep_effects: bool = False,
           outline_text: bool = False, preview: bool = True, svg: bool = False) -> Path:
    html = template.read_text(encoding="utf-8")
    missing: list = []
    resolve_paths(data or {}, getattr(data, "_base", ROOT), missing)
    if missing:
        raise SystemExit("Image file(s) not found, the render would show blank spots:\n  " + "\n  ".join(missing)
                         + "\nPaths in brand tokens are relative to the graphic-designer folder; paths in job data are relative to the data file.")
    html = fill(html, data or {})
    vector = out.suffix.lower() in (".pdf", ".ai")
    if vector and not keep_effects:
        html = html.replace("</head>", VECTOR_CSS + "\n</head>", 1)
    meta = canvas_from_meta(html)
    width = width or meta.get("width", 1000)
    height = height or meta.get("height", 1000)
    scale = scale or meta.get("scale", 2)

    out.parent.mkdir(parents=True, exist_ok=True)
    # Write the filled HTML next to the output so it can be opened/approved in a browser.
    filled = out.with_suffix(".html")
    filled.write_text(html, encoding="utf-8")
    if html_only:
        return filled

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height},
                                device_scale_factor=scale)
        # goto(file://) instead of set_content so relative assets resolve against the template dir.
        # We copy the filled HTML into the template dir temporarily for that reason.
        tmp = template.parent / f".__render_{out.stem}.html"
        tmp.write_text(html, encoding="utf-8")
        try:
            page.goto(tmp.resolve().as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(150)
            if vector:
                is_ai = out.suffix.lower() == ".ai"
                live_text = is_ai and not outline_text
                runs = ai_export.extract_text_runs(page) if live_text else []
                if live_text:
                    page.add_style_tag(content=ai_export.HIDE_TEXT_CSS.split(">", 1)[1].rsplit("<", 1)[0])
                pdf = out if not is_ai else out.with_name(out.stem + (".artwork" if live_text else "") + ".pdf")
                page.pdf(path=str(pdf), width=f"{width}px", height=f"{height}px",
                         print_background=True, page_ranges="1")
                browser.close()
                tmp.unlink(missing_ok=True)
                if not is_ai:
                    return pdf
                if not live_text:
                    return convert_pdf_to_ai(pdf, out)
                missing = ai_export.build_ai(pdf, runs, out, out.with_name(out.stem + ".ai-preview.png") if preview else None,
                                             out.with_suffix(".svg") if svg else None)
                pdf.unlink(missing_ok=True)
                if missing:
                    print("WARNING fonts not found in Illustrator (fallback used):", ", ".join(missing), file=sys.stderr)
                return out
            target = page.locator("#canvas") if page.locator("#canvas").count() else page
            kwargs = {"path": str(out), "type": "jpeg" if out.suffix.lower() in (".jpg", ".jpeg") else "png"}
            if kwargs["type"] == "jpeg":
                kwargs["quality"] = quality or 92
            if target is page:
                kwargs["full_page"] = full_page
            target.screenshot(**kwargs)
        finally:
            tmp.unlink(missing_ok=True)
            browser.close()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("template", type=Path)
    ap.add_argument("--data", type=Path, help="JSON file of template variables")
    ap.add_argument("--brand", help="brand slug: merges brand-guidelines/brands/<slug>/tokens.json under data['brand']")
    ap.add_argument("--deliver", action="store_true",
                    help="also copy the result into the brand's local export folder (see project.py; requires --brand)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--scale", type=float, help="deviceScaleFactor (2 = retina / 2x pixels)")
    ap.add_argument("--quality", type=int, help="JPEG quality 1-100")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--full-page", action="store_true")
    ap.add_argument("--keep-effects", action="store_true", help="vector export: keep shadows/filters (they rasterize)")
    ap.add_argument("--outline-text", action="store_true", help=".ai export: skip live text layer")
    ap.add_argument("--no-preview", action="store_true", help=".ai export: skip Illustrator PNG preview")
    ap.add_argument("--svg", action="store_true", help=".ai export: also write an SVG with live text (for Figma)")
    a = ap.parse_args(argv)
    data = json.loads(a.data.read_text()) if a.data else {}
    if a.data:
        m = []; resolve_paths(data, a.data.resolve().parent, m)   # job-data paths: relative to the data file
    if a.brand:
        tokens = Path(__file__).parent / "brand-guidelines" / "brands" / a.brand / "tokens.json"
        if not tokens.exists():
            ap.error(f"no brand '{a.brand}': expected {tokens}")
        data["brand"] = {**json.loads(tokens.read_text()), **data.get("brand", {})}
    result = render(a.template, a.out, data, a.width, a.height, a.scale, a.quality, a.html_only, a.full_page, a.keep_effects,
                    a.outline_text, not a.no_preview, a.svg)
    print(result)
    if a.deliver:
        if not a.brand:
            ap.error("--deliver requires --brand")
        print("delivered:", project.deliver(Path(result), a.brand))


if __name__ == "__main__":
    sys.exit(main())
