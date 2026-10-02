#!/usr/bin/env python
"""
compress.py — Shrink images for email and web without visible loss.

    python compress.py <file or folder> [--out DIR] [--max-width 1200] [--profile rich|light]
                       [--max-error 1.6] [--report]

What it does, per image:
  * JPEG (and PNG without transparency, which becomes JPEG): walks quality down from 90 and keeps
    the lowest quality whose mean pixel error against the original stays under --max-error
    (0–255 scale; 1.6 is below what people notice on photos, 1.0 is very safe for flat graphics).
    Progressive, optimized Huffman tables, 4:2:0 chroma for photos / 4:4:4 for graphics with text.
  * PNG with transparency: quantized to 256 colors when that keeps error under the threshold,
    otherwise left as 32-bit but optimized.
  * Resizes to --max-width first (email at 600 px wide needs 1200 px images, nothing more).
  * Never upsizes, never touches SVG/GIF.

Profiles: rich = max-error 1.6 (quality usually lands 78–86); light = max-error 3.0 and
--max-width 1000 (usually 60–72). Prints before/after per file and the total.
"""
from __future__ import annotations
import argparse, io, sys
from pathlib import Path
import numpy as np
from PIL import Image

PROFILES = {"rich": {"max_error": 1.6, "max_width": 1200, "min_q": 70}, "light": {"max_error": 3.0, "max_width": 1000, "min_q": 56}}


def _err(a: Image.Image, b: Image.Image) -> float:
    x = np.asarray(a.convert("RGB"), dtype=np.float32); y = np.asarray(b.convert("RGB"), dtype=np.float32)
    return float(np.abs(x - y).mean())


def _is_graphic(im: Image.Image) -> bool:
    """Flat colors / text (few distinct colors in a sample) → keep chroma at 4:4:4 so edges stay crisp."""
    s = im.convert("RGB").resize((min(im.width, 256), min(im.height, 256)))
    return len(set(s.getdata())) < 4000


def compress_image(src: Path, dst: Path, max_width: int, max_error: float, min_q: int = 70) -> tuple[int, int, str]:
    im = Image.open(src); orig_bytes = src.stat().st_size
    if src.suffix.lower() in (".svg", ".gif"):
        if src != dst: dst.write_bytes(src.read_bytes())
        return orig_bytes, orig_bytes, "copied"
    im.load()
    if im.width > max_width:
        im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if has_alpha and im.convert("RGBA").getchannel("A").getextrema()[0] < 255:
        rgba = im.convert("RGBA"); best = None
        for colors in (256, 128, 64):
            q = rgba.quantize(colors=colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)
            if _err(q.convert("RGBA"), rgba) <= max_error:
                buf = io.BytesIO(); q.save(buf, "PNG", optimize=True); best = (buf.getvalue(), f"png {colors}c")
            else:
                break
        if best is None:
            buf = io.BytesIO(); rgba.save(buf, "PNG", optimize=True); best = (buf.getvalue(), "png 32-bit")
        data, how = best; dst = dst.with_suffix(".png")
    else:
        rgb = im.convert("RGB"); subs = 0 if _is_graphic(rgb) else 2; chosen = None
        for q in (90, 86, 82, 78, 74, 70, 66, 62, 58):
            if q < min_q: break
            buf = io.BytesIO(); rgb.save(buf, "JPEG", quality=q, optimize=True, progressive=True, subsampling=subs)
            if _err(Image.open(io.BytesIO(buf.getvalue())), rgb) <= max_error:
                chosen = (buf.getvalue(), f"jpeg q{q}")
            else:
                break
        if chosen is None:
            buf = io.BytesIO(); rgb.save(buf, "JPEG", quality=92, optimize=True, progressive=True, subsampling=subs); chosen = (buf.getvalue(), "jpeg q92")
        data, how = chosen; dst = dst.with_suffix(".jpg")
    if len(data) >= orig_bytes and src.suffix.lower() == dst.suffix.lower() and im.size == Image.open(src).size:
        if src != dst: dst.write_bytes(src.read_bytes())
        return orig_bytes, orig_bytes, "kept (already small)"
    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(data)
    if src != dst and src.suffix.lower() != dst.suffix.lower() and src.parent == dst.parent: src.unlink()
    return orig_bytes, len(data), how


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path); ap.add_argument("--out", type=Path, help="output dir (default: in place)")
    ap.add_argument("--profile", choices=PROFILES, default="rich"); ap.add_argument("--max-width", type=int); ap.add_argument("--max-error", type=float)
    a = ap.parse_args(argv); prof = PROFILES[a.profile]
    mw = a.max_width or prof["max_width"]; me = a.max_error if a.max_error is not None else prof["max_error"]
    files = [a.path] if a.path.is_file() else sorted(p for p in a.path.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"))
    tb = ta = 0
    for f in files:
        dst = (a.out / f.name) if a.out else f
        b, after, how = compress_image(f, dst, mw, me, prof["min_q"]); tb += b; ta += after
        print(f"{f.name:40s} {b/1024:7.1f} KB → {after/1024:7.1f} KB  {how}")
    print(f"{'TOTAL':40s} {tb/1024:7.1f} KB → {ta/1024:7.1f} KB  ({(1 - ta/max(tb,1)):.0%} smaller)")


if __name__ == "__main__":
    sys.exit(main())
