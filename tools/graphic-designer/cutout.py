#!/usr/bin/env python
"""
cutout.py — Remove the background from a product photo and auto-crop to the subject.

Turns a product photo into a transparent PNG
that can sit on any template background via `{{ product.image }}`.

Needs rembg: from the toolkit root run `scripts/setup.sh --cutouts` once (or pip install "rembg[cpu]"), then
    ../../.venv/bin/python cutout.py in.jpg out.png            # isnet-general-use model
    ../../.venv/bin/python cutout.py in.jpg out.png --pad 40   # px of transparent padding
    ../../.venv/bin/python cutout.py in.jpg out.png --model u2net
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image
from rembg import new_session, remove


def cutout(src: Path, dst: Path, model: str = "isnet-general-use", pad: int = 40, alpha_matting: bool = False) -> Path:
    img = Image.open(src).convert("RGBA")
    out = remove(img, session=new_session(model), alpha_matting=alpha_matting,
                 post_process_mask=True)
    bbox = out.getchannel("A").getbbox()
    if bbox:
        l, t, r, b = bbox
        out = out.crop((max(0, l - pad), max(0, t - pad), min(out.width, r + pad), min(out.height, b + pad)))
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, "PNG", optimize=True)
    return dst


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path); ap.add_argument("dst", type=Path)
    ap.add_argument("--model", default="isnet-general-use"); ap.add_argument("--pad", type=int, default=40)
    ap.add_argument("--alpha-matting", action="store_true")
    a = ap.parse_args(argv)
    p = cutout(a.src, a.dst, a.model, a.pad, a.alpha_matting)
    print(p, Image.open(p).size)


if __name__ == "__main__":
    sys.exit(main())
