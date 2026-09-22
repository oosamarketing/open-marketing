"""
ai_export.py — Build a native Illustrator .ai with artwork as vectors and text as live,
editable text objects.

How it works
------------
1. In the rendered page, walk every text node, split it into lines, and record each line's
   position, baseline, font family/weight/style, size, color, opacity and letter-spacing.
   Coordinates are CSS px relative to #canvas.
2. Print the page to a vector PDF with all text made transparent (the "Artwork" layer).
3. Drive the installed Adobe Illustrator via AppleScript/ExtendScript: open the PDF,
   name that layer "Artwork", add a "Text" layer, and create one point-text object per
   line at the measured baseline using the matching installed font.

Units: Chromium prints CSS px at 0.75 pt/px, so all coordinates and sizes are scaled by 0.75.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

PX_TO_PT = 0.75

EXTRACT_TEXT_JS = r"""
() => {
  const root = document.getElementById('canvas') || document.body;
  const origin = root.getBoundingClientRect();
  const c2d = document.createElement('canvas').getContext('2d');
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const runs = [];
  const effOpacity = (el) => { let o = 1; for (let e = el; e && e !== root.parentElement; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity || 1); return o; };
  let node;
  while ((node = walker.nextNode())) {
    if (!node.textContent.trim()) continue;
    const el = node.parentElement;
    if (el.closest('script,style,#vector-export')) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const inSvg = el.namespaceURI === 'http://www.w3.org/2000/svg';
    const color = inSvg ? cs.fill : cs.color;
    const fontSize = parseFloat(cs.fontSize);
    const family = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
    c2d.font = `${cs.fontStyle} ${cs.fontWeight} ${fontSize}px ${cs.fontFamily}`;
    const m = c2d.measureText('Hg');
    const asc = m.fontBoundingBoxAscent, desc = m.fontBoundingBoxDescent;
    let text = node.textContent;
    if (cs.textTransform === 'uppercase') text = text.toUpperCase();
    else if (cs.textTransform === 'lowercase') text = text.toLowerCase();
    const re = /\S+\s*/g; let match; const lines = [];
    while ((match = re.exec(node.textContent))) {
      const r = document.createRange();
      r.setStart(node, match.index); r.setEnd(node, match.index + match[0].length);
      let rects = r.getClientRects();
      const rect = rects.length ? rects[0] : el.getBoundingClientRect();
      const word = text.substr(match.index, match[0].length);
      let line = lines[lines.length - 1];
      if (!line || Math.abs(line.top - rect.top) > 1) { line = { top: rect.top, left: rect.left, height: rect.height, text: '' }; lines.push(line); }
      line.text += word;
    }
    for (const ln of lines) {
      const scale = (asc + desc) ? ln.height / (asc + desc) : 1;   // ≈1 for HTML; viewBox scale for SVG
      const size = fontSize * scale;
      const ls = cs.letterSpacing === 'normal' ? 0 : parseFloat(cs.letterSpacing) * scale;
      runs.push({
        text: ln.text.replace(/\s+$/, ''),
        x: ln.left - origin.left,
        baseline: ln.top + asc * scale - origin.top,
        size, family, weight: cs.fontWeight, italic: cs.fontStyle !== 'normal',
        color, opacity: effOpacity(el), tracking: size ? (ls / size) * 1000 : 0,
      });
    }
  }
  return runs;
}
"""

HIDE_TEXT_CSS = """<style id="hide-text">
  #canvas, #canvas * { color: transparent !important; -webkit-text-fill-color: transparent !important; }
  #canvas svg text { fill: transparent !important; }
</style>"""

WEIGHT_STYLES = {
    "100": ["Thin"], "200": ["ExtraLight", "UltraLight"], "300": ["Light"],
    "400": ["Regular", "Roman", ""], "500": ["Medium"], "600": ["SemiBold", "DemiBold"],
    "700": ["Bold"], "800": ["ExtraBold", "Heavy"], "900": ["Black", "Heavy"],
}

JSX_TEMPLATE = r"""
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
app.coordinateSystem = CoordinateSystem.ARTBOARDCOORDINATESYSTEM;
var RUNS = %(runs)s;
while (app.documents.length) app.documents[0].close(SaveOptions.DONOTSAVECHANGES);
var doc = app.open(new File(%(pdf)s));
doc.layers[0].name = "Artwork";
var textLayer = doc.layers.add(); textLayer.name = "Text";
var fontCache = {};
function getFont(name) { try { return app.textFonts.getByName(name); } catch (e) { return null; } }
function pickFont(family, candidates) {
  var key = family + "|" + candidates.join(",");
  if (fontCache[key]) return fontCache[key];
  var fam = family.replace(/\s+/g, "");
  var f = null;
  for (var i = 0; i < candidates.length && !f; i++) f = getFont(candidates[i].replace("{F}", fam));
  if (!f) { for (var j = 0; j < app.textFonts.length; j++) if (app.textFonts[j].family == family) { f = app.textFonts[j]; break; } }
  fontCache[key] = f; return f;
}
function rgb(str) {
  var m = str.match(/(\d+(?:\.\d+)?)/g); var c = new RGBColor();
  c.red = parseFloat(m[0]); c.green = parseFloat(m[1]); c.blue = parseFloat(m[2]);
  var a = m.length > 3 ? parseFloat(m[3]) : 1; return { color: c, alpha: a };
}
var missing = {};
var ascCache = {};
// Illustrator's own ascent for a font (frame top -> baseline), per pt of size.
// Measured by outlining a capital H: its bottom edge sits exactly on the baseline.
function ascentPerPt(font) {
  var key = font ? font.name : "__default";
  if (ascCache[key] !== undefined) return ascCache[key];
  var t = textLayer.textFrames.add(); t.contents = "H";
  if (font) t.textRange.characterAttributes.textFont = font;
  t.textRange.characterAttributes.size = 100;
  t.top = 0; t.left = 0;
  var o = t.createOutline();
  ascCache[key] = -o.geometricBounds[3] / 100;
  o.remove();
  return ascCache[key];
}
for (var i = 0; i < RUNS.length; i++) {
  var r = RUNS[i];
  var tf = textLayer.textFrames.add();
  tf.contents = r.text;
  var ca = tf.textRange.characterAttributes;
  var font = pickFont(r.family, r.candidates);
  var applied = false;
  if (font) { try { ca.textFont = font; applied = true; } catch (e) { $.sleep(200); try { ca.textFont = font; applied = true; } catch (e2) {} } }
  if (!applied) missing[r.family + " " + r.weight] = true;
  ca.size = r.size * %(k)s;
  ca.tracking = r.tracking;
  var col = rgb(r.color); ca.fillColor = col.color; ca.strokeColor = new NoColor();
  tf.opacity = Math.round(r.opacity * col.alpha * 100);
  var sizePt = r.size * %(k)s;
  tf.left = r.x * %(k)s;
  tf.top = -(r.baseline * %(k)s) + ascentPerPt(font) * sizePt;
  tf.name = r.text.substring(0, 40);
}
var aiOpts = new IllustratorSaveOptions(); aiOpts.pdfCompatible = true; aiOpts.embedICCProfile = true; aiOpts.compressed = true;
doc.saveAs(new File(%(ai)s), aiOpts);
if (%(preview)s) {
  var po = new ExportOptionsPNG24(); po.artBoardClipping = true; po.antiAliasing = true; po.horizontalScale = 200; po.verticalScale = 200;
  doc.exportFile(new File(%(preview)s), ExportType.PNG24, po);
}
if (%(svg)s) {
  // SVG with text kept as <text> (Figma imports it as editable text when the font is installed) and rasters embedded
  var so = new ExportOptionsSVG(); so.fontType = SVGFontType.SVGFONT; so.fontSubsetting = SVGFontSubsetting.None;
  so.embedRasterImages = true; so.coordinatePrecision = 3; so.documentEncoding = SVGDocumentEncoding.UTF8; so.cssProperties = SVGCSSPropertyLocation.STYLEATTRIBUTES;
  doc.exportFile(new File(%(svg)s), ExportType.SVG, so);
}
doc.close(SaveOptions.DONOTSAVECHANGES);
var log = []; for (var k in missing) log.push(k);
var fh = new File(%(log)s); fh.open("w"); fh.write(log.join("\n")); fh.close();
"""


def font_candidates(family: str, weight: str, italic: bool) -> list[str]:
    styles = WEIGHT_STYLES.get(str(weight), ["Regular"])
    out = []
    for st in styles:
        if italic:
            out += [f"{{F}}-{st}Italic", f"{{F}}Italic-{st}Italic", f"{{F}}-Italic" if not st else f"{{F}}-{st}Italic"]
        else:
            out += [f"{{F}}-{st}" if st else "{F}-Regular", f"{{F}}{st}" if st else "{F}"]
    return out


def extract_text_runs(page) -> list[dict]:
    runs = page.evaluate(EXTRACT_TEXT_JS)
    for r in runs:
        r["candidates"] = font_candidates(r["family"], r["weight"], r["italic"])
    return runs


def run_illustrator(jsx: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".jsx", delete=False, encoding="utf-8") as fh:
        fh.write(jsx); path = fh.name
    script = f'tell application "Adobe Illustrator" to do javascript (read (POSIX file "{path}") as «class utf8»)'
    subprocess.run(["osascript", "-e", script], check=True, timeout=300)
    Path(path).unlink(missing_ok=True)


def build_ai(artwork_pdf: Path, runs: list[dict], ai_out: Path, preview_png: Path | None = None, svg_out: Path | None = None) -> list[str]:
    """Open artwork_pdf in Illustrator, add live text from runs, save ai_out (+ optional SVG). Returns missing fonts."""
    log = ai_out.with_suffix(".fontlog.txt")
    jsx = JSX_TEMPLATE % {
        "runs": json.dumps(runs, ensure_ascii=True),
        "pdf": json.dumps(str(artwork_pdf.resolve())),
        "ai": json.dumps(str(ai_out.resolve())),
        "preview": json.dumps(str(preview_png.resolve())) if preview_png else "null",
        "svg": json.dumps(str(svg_out.resolve())) if svg_out else "null",
        "log": json.dumps(str(log.resolve())),
        "k": PX_TO_PT,
    }
    run_illustrator(jsx)
    if not ai_out.exists():
        raise RuntimeError("Illustrator did not write the .ai file")
    missing = [l for l in log.read_text().splitlines() if l.strip()] if log.exists() else []
    log.unlink(missing_ok=True)
    return missing
