#!/usr/bin/env python
"""
avatar.py — Turn any logo into a round profile avatar (Meta/Instagram page circle, favicons, app icons).

Wordmarks are wide and often two-tone; in a 40 px circle they crop or vanish on white. This puts the
logo on a solid brand-color disc with padding, strips a white background from JPEG/opaque logos,
and writes a square PNG with transparent corners.

    python avatar.py "logo.png" avatar.png --bg "#7ea1c0"            # 512 px, 18% padding
    python avatar.py "logo.jpeg" avatar.png --bg "#8a6996" --size 1024 --pad 0.22
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

def _hex(c: str): c = c.lstrip("#"); return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))

def strip_white_background(im: Image.Image, thresh: int = 235) -> Image.Image:
    """Make near-white pixels connected to the image border transparent."""
    if im.getchannel("A").getextrema()[0] < 255:
        return im
    gray = ImageOps.grayscale(im.convert("RGB")); seed = gray.point(lambda v: 255 if v >= thresh else 0)
    for xy in [(0, 0), (im.width-1, 0), (0, im.height-1), (im.width-1, im.height-1)]:
        if seed.getpixel(xy) == 255: ImageDraw.floodfill(seed, xy, 128)
    bgmask = seed.point(lambda v: 255 if v == 128 else 0)
    alpha = im.getchannel("A").copy(); alpha.paste(0, mask=bgmask); out = im.copy(); out.putalpha(alpha); return out

def make_avatar(logo: Path, out: Path, *, bg: str = "#111111", size: int = 512, pad: float = 0.18, strip_white: bool = True) -> Path:
    im = Image.open(logo).convert("RGBA")
    if strip_white: im = strip_white_background(im)
    bbox = im.getchannel("A").getbbox()
    if bbox: im = im.crop(bbox)
    inner = int(size * (1 - 2 * pad)); s = min(inner / im.width, inner / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size*4, size*4), 0); ImageDraw.Draw(mask).ellipse((0, 0, size*4-1, size*4-1), fill=255); mask = mask.resize((size, size), Image.LANCZOS)
    disc.paste(Image.new("RGBA", (size, size), _hex(bg) + (255,)), (0, 0), mask)
    disc.alpha_composite(im, ((size - im.width)//2, (size - im.height)//2))
    out.parent.mkdir(parents=True, exist_ok=True); disc.save(out, "PNG", optimize=True); return out

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logo", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--bg", default="#111111"); ap.add_argument("--size", type=int, default=512); ap.add_argument("--pad", type=float, default=0.18)
    ap.add_argument("--keep-white", action="store_true", help="don't strip a white background")
    a = ap.parse_args(argv); print(make_avatar(a.logo, a.out, bg=a.bg, size=a.size, pad=a.pad, strip_white=not a.keep_white))

if __name__ == "__main__": sys.exit(main())
