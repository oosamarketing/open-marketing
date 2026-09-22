#!/usr/bin/env python
"""
defringe.py — Remove the pale halo a product cutout shows on colored backgrounds.

Renders and cutouts made against white keep white in their semi-transparent pixels (glass
edges, ground reflections, soft shadows). On a dark or colored background those pixels read as
a gray/white rim. This fades the alpha of semi-transparent near-white pixels.

    python defringe.py in.png out.png            # alpha of white-ish semi pixels * 0.15
    python defringe.py in.png out.png --keep 0   # remove them entirely
    python defringe.py in.png out.png --white 200 --keep 0.3
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
from PIL import Image

def defringe(src: Path, dst: Path, keep: float = 0.15, white: int = 200) -> Path:
    a = np.asarray(Image.open(src).convert("RGBA")).astype(float)
    A, rgb = a[..., 3], a[..., :3]
    mask = (A > 0) & (A < 250) & (rgb.min(axis=2) > white)
    a[..., 3] = np.where(mask, A * keep, A)
    Image.fromarray(a.astype(np.uint8)).save(dst, "PNG", optimize=True)
    return dst

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path); ap.add_argument("dst", type=Path)
    ap.add_argument("--keep", type=float, default=0.15, help="alpha multiplier for the halo pixels (0 removes)")
    ap.add_argument("--white", type=int, default=200, help="min RGB channel value to count as white-ish")
    a = ap.parse_args(argv); print(defringe(a.src, a.dst, a.keep, a.white))

if __name__ == "__main__": sys.exit(main())
