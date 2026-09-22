#!/usr/bin/env python
"""
ai_edit.py — Make ad variations from an existing Illustrator template by swapping photos,
editing text, and exporting artboards. Never overwrites the source .ai.

    python ai_edit.py spec.json

spec.json:
{
  "source": "/path/template.ai",
  "save_as": "/path/template - variations.ai",
  "export_dir": "/path/out", "export_scale": 100,
  "variants": [
    {"artboard": 1, "export": "fire-mobile",
     "image": "/abs/photo.jpg", "anchor": [0.5, 0.2],          # cover-fit; anchor = which part to keep (0..1, x then y)
     "texts": {"OLD HEADLINE.": "NEW HEADLINE."},            # match by current contents (case/space-insensitive)
     "hide_texts": ["Lorem ipsum"],
     "recolor_white_to": "#111111"}                             # invert white text/logo/brackets for light photos
  ]
}

Photo swap: finds the clipping group on the artboard that holds raster images, hides the
visible raster(s), places the new file inside the same group, scales it to cover the clip
path, positions it by anchor, and embeds it. Everything above (gradients, text, logos) is
untouched. Requires Adobe Illustrator on this Mac.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

JSX = r"""
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
while (app.documents.length) app.documents[0].close(SaveOptions.DONOTSAVECHANGES);
var SPEC = %(spec)s;
var LOG = [];
function log(s){ LOG.push(String(s)); }
var doc = app.open(new File(SPEC.source));
var so = new IllustratorSaveOptions(); so.pdfCompatible = true; so.compressed = true;
doc.saveAs(new File(SPEC.save_as), so);
// unlock everything so edits can land (the template ships with locked layers/items)
function unlockAll(container){ for (var i=0;i<container.pageItems.length;i++){ var it=container.pageItems[i]; try{ if (it.locked) it.locked=false; }catch(e){} if (it.typename=="GroupItem") unlockAll(it); } }
for (var L=0;L<doc.layers.length;L++){ var lay=doc.layers[L]; lay.locked=false; lay.visible=true; unlockAll(lay); for (var S=0;S<lay.layers.length;S++){ lay.layers[S].locked=false; unlockAll(lay.layers[S]); } }

function abRect(i){ return doc.artboards[i].artboardRect; }
function centerIn(b, r){ var cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2; return cx>=r[0]&&cx<=r[2]&&cy<=r[1]&&cy>=r[3]; }
function norm(s){ return String(s).replace(/[\r\n\t]+/g," ").replace(/\s+/g," ").replace(/^\s+|\s+$/g,"").toUpperCase(); }
function hexRGB(h){ var c=new RGBColor(); c.red=parseInt(h.substr(1,2),16); c.green=parseInt(h.substr(3,2),16); c.blue=parseInt(h.substr(5,2),16); return c; }
function isWhiteish(col){
  try {
    if (col.typename=="RGBColor") return col.red>200&&col.green>200&&col.blue>200;
    if (col.typename=="CMYKColor") return col.cyan<10&&col.magenta<10&&col.yellow<10&&col.black<10;
    if (col.typename=="GrayColor") return col.gray<10;
  } catch(e){}
  return false;
}
// all descendants of a container (layer or group)
function descendants(container, acc){
  for (var i=0;i<container.pageItems.length;i++){ var it=container.pageItems[i]; acc.push(it); if (it.typename=="GroupItem") descendants(it, acc); }
  return acc;
}
function itemsOnArtboard(i){
  var r=abRect(i), acc=[], out=[];
  for (var L=0;L<doc.layers.length;L++) descendants(doc.layers[L], acc);
  for (var k=0;k<acc.length;k++){ var b; try{ b=acc[k].geometricBounds; }catch(e){ continue; } if (centerIn(b,r)) out.push(acc[k]); }
  return out;
}
function findClipPath(grp){ for (var i=0;i<grp.pageItems.length;i++){ var it=grp.pageItems[i]; if (it.typename=="PathItem"&&it.clipping) return it; if (it.typename=="CompoundPathItem"&&it.pathItems.length&&it.pathItems[0].clipping) return it; } return null; }
function collectRasters(container, acc){ for (var i=0;i<container.pageItems.length;i++){ var it=container.pageItems[i]; if (it.typename=="RasterItem") acc.push(it); else if (it.typename=="GroupItem") collectRasters(it, acc);} return acc; }

function swapPhoto(abIndex, imgPath, anchor){
  var r=abRect(abIndex);
  // clipping groups whose clip path is centred on this artboard and that contain rasters
  var acc=[]; for (var L=0;L<doc.layers.length;L++) descendants(doc.layers[L], acc);
  var best=null, bestArea=0;
  for (var k=0;k<acc.length;k++){ var it=acc[k]; if (it.typename!="GroupItem"||!it.clipped) continue;
    var cp=findClipPath(it); if(!cp) continue; var b=cp.geometricBounds; if(!centerIn(b,r)) continue;
    var ras=collectRasters(it,[]); if(!ras.length) continue;
    var area=(b[2]-b[0])*(b[1]-b[3]); if (area>bestArea){ best=it; bestArea=area; } }
  if (!best){ log("AB"+abIndex+": no photo clip group found"); return false; }
  var cp=findClipPath(best), cb=cp.geometricBounds, cw=cb[2]-cb[0], ch=cb[1]-cb[3];
  var rasters=collectRasters(best,[]); var parentGroup=best; var visibleOpacity=100;
  for (var i=0;i<rasters.length;i++){ if (!rasters[i].hidden){ parentGroup=rasters[i].parent; visibleOpacity=rasters[i].opacity; rasters[i].hidden=true; } }
  if (parentGroup==best) parentGroup=rasters[0].parent;
  var pl=parentGroup.placedItems.add(); pl.file=new File(imgPath);
  var w0=pl.width, h0=pl.height; var s=Math.max(cw/w0, ch/h0);
  pl.width=w0*s; pl.height=h0*s;
  var W=pl.width, H=pl.height;
  pl.position=[cb[0]-(W-cw)*anchor[0], cb[1]+(H-ch)*anchor[1]];
  pl.opacity=visibleOpacity;
  pl.embed();
  log("AB"+abIndex+": placed "+imgPath.replace(/^.*\//,"")+" cover "+Math.round(W)+"x"+Math.round(H)+" into clip "+Math.round(cw)+"x"+Math.round(ch)+", hid "+rasters.length+" rasters");
  return true;
}
function editTexts(abIndex, map, hide){
  var items=itemsOnArtboard(abIndex), n=0, h=0;
  for (var i=0;i<items.length;i++){ var it=items[i]; if (it.typename!="TextFrame") continue; var cur=norm(it.contents);
    if (map) for (var k in map){ if (norm(k)==cur){ it.contents=String(map[k]).replace(/\n/g,"\r"); n++; } }
    if (hide) for (var j=0;j<hide.length;j++){ if (norm(hide[j])==cur){ it.hidden=true; h++; } } }
  log("AB"+abIndex+": replaced "+n+" texts, hid "+h);
}
function recolor(abIndex, hex){
  var dark=hexRGB(hex), items=itemsOnArtboard(abIndex), n=0;
  for (var i=0;i<items.length;i++){ var it=items[i]; if (it.hidden) continue;
    try {
      if (it.typename=="TextFrame"){ var ca=it.textRange.characterAttributes; if (isWhiteish(ca.fillColor)){ ca.fillColor=dark; n++; } }
      else if (it.typename=="PathItem"){ if (it.clipping) continue; if (it.filled&&isWhiteish(it.fillColor)){ it.fillColor=dark; n++; } if (it.stroked&&isWhiteish(it.strokeColor)){ it.strokeColor=dark; n++; } }
      else if (it.typename=="CompoundPathItem"){ for (var p=0;p<it.pathItems.length;p++){ var pp=it.pathItems[p]; if (pp.filled&&isWhiteish(pp.fillColor)){ pp.fillColor=dark; n++; } if (pp.stroked&&isWhiteish(pp.strokeColor)){ pp.strokeColor=dark; n++; } } }
    } catch(e){}
  }
  log("AB"+abIndex+": recolored "+n+" white items to "+hex);
}
function exportAB(abIndex, name){
  doc.artboards.setActiveArtboardIndex(abIndex);
  var o=new ExportOptionsPNG24(); o.artBoardClipping=true; o.antiAliasing=true; o.transparency=false;
  o.horizontalScale=SPEC.export_scale||100; o.verticalScale=SPEC.export_scale||100;
  var f=new File(SPEC.export_dir+"/"+name+".png"); doc.exportFile(f, ExportType.PNG24, o);
  log("AB"+abIndex+": exported "+f.fsName);
}
for (var v=0; v<SPEC.variants.length; v++){
  var V=SPEC.variants[v];
  try {
    if (V.image) swapPhoto(V.artboard, V.image, V.anchor||[0.5,0.5]);
    if (V.texts||V.hide_texts) editTexts(V.artboard, V.texts, V.hide_texts);
    if (V.recolor_white_to) recolor(V.artboard, V.recolor_white_to);
    if (V.export) exportAB(V.artboard, V.export);
  } catch(e){ log("AB"+V.artboard+": ERROR "+e); }
}
doc.save();
doc.close(SaveOptions.DONOTSAVECHANGES);
var fh=new File(SPEC.log); fh.encoding="UTF-8"; fh.open("w"); fh.write(LOG.join("\n")); fh.close();
"""


def run(spec: dict) -> str:
    Path(spec["export_dir"]).mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as fh:
        spec["log"] = fh.name
    jsx = JSX % {"spec": json.dumps(spec, ensure_ascii=True)}
    with tempfile.NamedTemporaryFile("w", suffix=".jsx", delete=False, encoding="utf-8") as fh:
        fh.write(jsx); jsx_path = fh.name
    script = f'tell application "Adobe Illustrator" to do javascript (read (POSIX file "{jsx_path}") as «class utf8»)'
    subprocess.run(["osascript", "-e", script], check=True, timeout=1200)
    Path(jsx_path).unlink(missing_ok=True)
    log = Path(spec["log"]).read_text(encoding="utf-8"); Path(spec["log"]).unlink(missing_ok=True)
    return log


def main(argv=None):
    spec = json.loads(Path((argv or sys.argv[1:])[0]).read_text())
    print(run(spec))


if __name__ == "__main__":
    sys.exit(main())
