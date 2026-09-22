#!/usr/bin/env python
"""
cutout_white.py — Background removal for subjects shot on a PURE WHITE seamless backdrop,
including subjects that are themselves white (jerseys, visors) where ML matting fails.

Rule: a pixel is background only if it is near-white AND connected to the image border
through other near-white pixels. White areas enclosed by the subject stay.
Optionally ANDs with a rembg alpha so soft edges (hair, straps) come from the model.

    python cutout_white.py in.jpg out.png [--thresh 242] [--no-rembg] [--pad 0] [--seed-edges top,left]

--seed-edges: which image borders count as "outside". Default all four. When the subject
runs off the right/bottom edge (a cropped torso), pass top,left so white parts of the subject
touching those edges are not mistaken for background.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
try:
    from scipy import ndimage
except ImportError:  # core install: label connected regions with Pillow instead
    ndimage = None

def cutout(src: Path, dst: Path, thresh=242, use_rembg=True, pad=0, seed_edges=("top","bottom","left","right")) -> Path:
    img = Image.open(src).convert("RGB"); a = np.asarray(img).astype(np.int16)
    near_white = a.min(axis=2) >= thresh
    if use_rembg:
        from rembg import remove, new_session
        alpha = np.asarray(remove(img, session=new_session("isnet-general-use")).getchannel("A"))
        near_white &= alpha < 200          # model is confident it's subject -> keep
    if ndimage is not None:
        lab, n = ndimage.label(near_white)
        edges = {"top": lab[0], "bottom": lab[-1], "left": lab[:, 0], "right": lab[:, -1]}
        border = np.unique(np.concatenate([edges[e] for e in seed_edges]))
        bg = np.isin(lab, border[border != 0])
        fg = ~bg
        fg = ndimage.binary_erosion(fg, iterations=1)
    else:
        from PIL import ImageDraw
        m = Image.fromarray((near_white * 255).astype(np.uint8)); H, W = near_white.shape
        seeds = {"top": [(x, 0) for x in range(0, W, 8)], "bottom": [(x, H - 1) for x in range(0, W, 8)],
                 "left": [(0, y) for y in range(0, H, 8)], "right": [(W - 1, y) for y in range(0, H, 8)]}
        for e in seed_edges:
            for xy in seeds[e]:
                if m.getpixel(xy) == 255: ImageDraw.floodfill(m, xy, 128)
        fg = np.asarray(m) != 128
        fg = np.asarray(Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0
    alpha_img = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    out = img.convert("RGBA"); out.putalpha(alpha_img)
    bbox = alpha_img.getbbox()
    if bbox and pad >= 0:
        l, t, r, b = bbox; out = out.crop((max(0, l-pad), max(0, t-pad), min(out.width, r+pad), min(out.height, b+pad)))
    dst.parent.mkdir(parents=True, exist_ok=True); out.save(dst, "PNG", optimize=True); return dst

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path); ap.add_argument("dst", type=Path)
    ap.add_argument("--thresh", type=int, default=242); ap.add_argument("--no-rembg", action="store_true"); ap.add_argument("--pad", type=int, default=0)
    ap.add_argument("--seed-edges", default="top,bottom,left,right")
    a = ap.parse_args(argv); p = cutout(a.src, a.dst, a.thresh, not a.no_rembg, a.pad, tuple(a.seed_edges.split(","))); print(p, Image.open(p).size)

if __name__ == "__main__": sys.exit(main())
