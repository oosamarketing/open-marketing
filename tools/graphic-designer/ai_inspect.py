#!/usr/bin/env python
"""
ai_inspect.py — Dump the editable structure of an Illustrator .ai file as JSON.

    python ai_inspect.py "/path/file.ai" [--out report.json]

Reports artboards (name, size), layers (nested, visibility/lock), and every text frame
(contents, font, size, kind, bounds, parent layer), placed image (file path, bounds),
raster/embedded image (bounds), and top-level groups/paths counts. Bounds are in points,
artboard-relative for the artboard that contains the item's centre (top-left origin, y down).
Requires Adobe Illustrator on this Mac; opens the file read-only and closes without saving.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

JSX = r"""
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
while (app.documents.length) app.documents[0].close(SaveOptions.DONOTSAVECHANGES);
var doc = app.open(new File(%(path)s));
app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
function esc(s){ return String(s).replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/\r|\n/g,"\\n").replace(/\t/g,"\\t"); }
function num(n){ return Math.round(n*100)/100; }
var abs = [];
for (var i=0;i<doc.artboards.length;i++){ var r=doc.artboards[i].artboardRect; abs.push({name:doc.artboards[i].name, left:r[0], top:r[1], right:r[2], bottom:r[3]}); }
function abFor(b){ var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2; for (var i=0;i<abs.length;i++){ var a=abs[i]; if (cx>=a.left&&cx<=a.right&&cy<=a.top&&cy>=a.bottom) return i; } return -1; }
function rel(b){ var i=abFor(b); if (i<0) return {ab:-1, x:num(b[0]), y:num(-b[1]), w:num(b[2]-b[0]), h:num(b[1]-b[3])}; var a=abs[i];
  return {ab:i, x:num(b[0]-a.left), y:num(a.top-b[1]), w:num(b[2]-b[0]), h:num(b[1]-b[3])}; }
var out = [];
out.push('{"file":"'+esc(doc.fullName.fsName)+'","artboards":[');
for (var i=0;i<abs.length;i++){ var a=abs[i]; out.push((i?',':'')+'{"index":'+i+',"name":"'+esc(a.name)+'","w":'+num(a.right-a.left)+',"h":'+num(a.top-a.bottom)+'}'); }
out.push('],"layers":[');
function layerJSON(L, depth){
  var s='{"name":"'+esc(L.name)+'","visible":'+L.visible+',"locked":'+L.locked+',"depth":'+depth+',"items":'+L.pageItems.length+',"sublayers":[';
  for (var i=0;i<L.layers.length;i++) s+=(i?',':'')+layerJSON(L.layers[i], depth+1);
  return s+']}';
}
for (var i=0;i<doc.layers.length;i++) out.push((i?',':'')+layerJSON(doc.layers[i],0));
out.push('],"texts":[');
var n=0;
for (var i=0;i<doc.textFrames.length;i++){ var t=doc.textFrames[i]; var b=t.geometricBounds; var p=rel(b);
  var font=""; var size=0; try{ font=t.textRange.characterAttributes.textFont.name; size=t.textRange.characterAttributes.size; }catch(e){}
  var kind = t.kind==TextType.POINTTEXT?"point":(t.kind==TextType.AREATEXT?"area":"path");
  out.push((n++?',':'')+'{"name":"'+esc(t.name)+'","layer":"'+esc(t.layer.name)+'","artboard":'+p.ab+',"kind":"'+kind+'","font":"'+esc(font)+'","size":'+num(size)+',"x":'+p.x+',"y":'+p.y+',"w":'+p.w+',"h":'+p.h+',"hidden":'+t.hidden+',"contents":"'+esc(t.contents)+'"}');
}
out.push('],"placed":[');
n=0;
for (var i=0;i<doc.placedItems.length;i++){ var it=doc.placedItems[i]; var p=rel(it.geometricBounds); var f=""; try{ f=it.file.fsName; }catch(e){ f="(missing)"; }
  out.push((n++?',':'')+'{"name":"'+esc(it.name)+'","layer":"'+esc(it.layer.name)+'","artboard":'+p.ab+',"file":"'+esc(f)+'","x":'+p.x+',"y":'+p.y+',"w":'+p.w+',"h":'+p.h+',"hidden":'+it.hidden+'}');
}
out.push('],"rasters":[');
n=0;
for (var i=0;i<doc.rasterItems.length;i++){ var it=doc.rasterItems[i]; var p=rel(it.geometricBounds); var f=""; try{ f=it.file.fsName; }catch(e){ f=""; }
  out.push((n++?',':'')+'{"name":"'+esc(it.name)+'","layer":"'+esc(it.layer.name)+'","artboard":'+p.ab+',"file":"'+esc(f)+'","x":'+p.x+',"y":'+p.y+',"w":'+p.w+',"h":'+p.h+',"px_w":'+num(it.width)+',"px_h":'+num(it.height)+',"hidden":'+it.hidden+',"embedded":'+it.embedded+',"clipped":'+(it.parent.typename=="GroupItem"&&it.parent.clipped)+'}');
}
out.push('],"counts":{"groups":'+doc.groupItems.length+',"paths":'+doc.pathItems.length+',"symbols":'+doc.symbolItems.length+',"placed":'+doc.placedItems.length+',"rasters":'+doc.rasterItems.length+',"texts":'+doc.textFrames.length+'}}');
var fh = new File(%(out)s); fh.encoding="UTF-8"; fh.open("w"); fh.write(out.join("")); fh.close();
doc.close(SaveOptions.DONOTSAVECHANGES);
"""


def inspect(path: Path) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
        out = Path(fh.name)
    jsx = JSX % {"path": json.dumps(str(path.resolve())), "out": json.dumps(str(out))}
    with tempfile.NamedTemporaryFile("w", suffix=".jsx", delete=False, encoding="utf-8") as fh:
        fh.write(jsx); jsx_path = fh.name
    script = f'tell application "Adobe Illustrator" to do javascript (read (POSIX file "{jsx_path}") as «class utf8»)'
    subprocess.run(["osascript", "-e", script], check=True, timeout=600)
    data = json.loads(out.read_text(encoding="utf-8"))
    out.unlink(missing_ok=True); Path(jsx_path).unlink(missing_ok=True)
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path); ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    data = inspect(a.file)
    if a.out:
        a.out.write_text(json.dumps(data, indent=2))
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    sys.exit(main())
