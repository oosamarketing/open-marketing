#!/usr/bin/env python
"""
cutout_clear.py — Cut out a product that has CLEAR parts (goggle lenses, glass, windows) shot on white.

rembg gives the outer silhouette but keeps the lens panes opaque (they show the white backdrop).
A plain "remove all white" kills the frame's highlights too. This does both halves properly:
  1. rembg alpha = subject silhouette.
  2. Inside the silhouette, near-white regions that are large and enclosed are treated as see-through
     panes: their alpha follows a luminance ramp (pure white -> transparent, tint/reflection -> partly kept).
     Small bright regions (frame highlights, strap print) are left alone.

    python cutout_clear.py in.jpg out.png [--white 228] [--min-area 0.015] [--keep 0.25]
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

def cutout(src: Path, dst: Path, white=228, min_area=0.015, keep=0.25) -> Path:
    from rembg import remove, new_session
    img = Image.open(src).convert("RGB")
    alpha = np.asarray(remove(img, session=new_session("isnet-general-use")).getchannel("A")).astype(float) / 255
    subj = alpha > 0.5
    a = np.asarray(img).astype(float); lum = a.min(axis=2)
    bright = (lum >= white) & subj
    lab, n = ndimage.label(bright)
    sizes = ndimage.sum(bright, lab, range(1, n + 1)); area = subj.sum()
    pane = np.zeros_like(subj)
    for i, sz in enumerate(sizes, start=1):
        if sz >= min_area * area:
            pane |= (lab == i)
    pane = ndimage.binary_dilation(pane, iterations=2)
    # inside panes: ramp by luminance (white -> 0, darker -> up to `keep`), elsewhere keep rembg alpha
    ramp = np.clip((255 - lum) / (255 - white + 1e-6), 0, 1) * keep + 0.0
    out_alpha = np.where(pane, np.minimum(alpha, ramp), alpha)
    out = img.convert("RGBA"); out.putalpha(Image.fromarray((out_alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)))
    bbox = out.getchannel("A").point(lambda v: 255 if v > 30 else 0).getbbox()
    if bbox: out = out.crop(bbox)
    dst.parent.mkdir(parents=True, exist_ok=True); out.save(dst, "PNG", optimize=True); return dst

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path); ap.add_argument("dst", type=Path)
    ap.add_argument("--white", type=int, default=228); ap.add_argument("--min-area", type=float, default=0.015); ap.add_argument("--keep", type=float, default=0.25)
    a = ap.parse_args(argv); print(cutout(a.src, a.dst, a.white, a.min_area, a.keep), Image.open(a.dst).size)

if __name__ == "__main__": sys.exit(main())
