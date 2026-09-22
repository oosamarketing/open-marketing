#!/usr/bin/env python
"""
restore_original.py — After a generative expand, put the ORIGINAL photo's pixels back.

Generative expand re-renders the whole frame, so small details inside the original area drift:
jersey lettering, logos, faces. This finds where the original sits inside the expanded image
(scale + offset search on downsampled grayscale), color-matches the original to the expansion
so the seam doesn't show, and pastes it back with feathered edges. Only the new margins stay
AI-generated.

    python restore_original.py original.jpg expanded.jpg out.jpg [--feather 70] [--erase-mark]

--erase-mark patches a small photographer watermark at the top center of the ORIGINAL with
neighboring pixels before pasting (common on shoot deliveries).
Prints the match (scale, x, y, error). An error above ~12 means the expansion did not preserve
the original framing; look at the result before using it.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageDraw


def _gray(im: Image.Image, size) -> np.ndarray:
    return np.asarray(im.convert("L").resize(size, Image.BILINEAR), dtype=np.float32)


def find_match(orig: Image.Image, exp: Image.Image):
    EW, EH = exp.size; best = (1e9, 1.0, 0, 0)
    def search(div, scales, xr, yr):
        nonlocal best
        e = _gray(exp, (EW // div, EH // div))
        for s in scales:
            h = int(round(EH * s)); w = int(round(h * orig.width / orig.height))
            o = _gray(orig, (max(2, w // div), max(2, h // div))); oh, ow = o.shape
            for y in yr(h):
                for x in xr(w):
                    xs, ys = x // div, y // div
                    x0, y0 = max(xs, 0), max(ys, 0); x1, y1 = min(xs + ow, e.shape[1]), min(ys + oh, e.shape[0])
                    if x1 - x0 < ow * 0.8 or y1 - y0 < oh * 0.6: continue
                    a = e[y0:y1, x0:x1]; b = o[y0 - ys:y1 - ys, x0 - xs:x1 - xs]
                    err = float(np.abs((a - a.mean()) - (b - b.mean())).mean())
                    if err < best[0]: best = (err, s, x, y)
    # coarse: 1/16 res, scale 0.80–1.15, any x, y within ±20% of height
    search(16, np.arange(0.80, 1.151, 0.01), lambda w: range(0, max(1, EW - w + 1), 16), lambda h: range(min(0, EH - h) - 32, max(0, EH - h) + 33, 16))
    _, s0, x0, y0 = best; best = (1e9, s0, x0, y0)
    # fine: 1/4 res around the coarse hit
    search(4, np.arange(s0 - 0.012, s0 + 0.0121, 0.003), lambda w: range(x0 - 24, x0 + 25, 4), lambda h: range(y0 - 24, y0 + 25, 4))
    return best


def erase_top_center_mark(im: Image.Image) -> Image.Image:
    """Remove a thin light watermark (monogram in a circle, signature) from the top-center zone.
    A large median filter wipes thin strokes and keeps the sky/background; pixels that differ
    from that median are the mark, and they are replaced by it through a soft, dilated mask."""
    W, H = im.size; box = (int(W * 0.40), 0, int(W * 0.60), int(H * 0.11)); zone = im.crop(box)
    small = zone.resize((zone.width // 2, zone.height // 2), Image.BILINEAR)
    bg = small.filter(ImageFilter.MedianFilter(size=41)).resize(zone.size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(3))
    diff = np.abs(np.asarray(zone.convert("L"), dtype=np.float32) - np.asarray(bg.convert("L"), dtype=np.float32))
    mask = Image.fromarray(((diff > 2.2) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(17)).filter(ImageFilter.GaussianBlur(5))
    # ignore the zone's outer rim so real edges (goalposts, roofs) crossing the zone are left alone
    rim = Image.new("L", zone.size, 0); ImageDraw.Draw(rim).rectangle((int(zone.width * .18), int(zone.height * .08), int(zone.width * .82), int(zone.height * .92)), fill=255)
    mask = Image.fromarray(np.minimum(np.asarray(mask), np.asarray(rim.filter(ImageFilter.GaussianBlur(10)))))
    zone.paste(bg, (0, 0), mask); out = im.copy(); out.paste(zone, box[:2]); return out


def restore(original: Path, expanded: Path, out: Path, feather: int = 70, erase_mark: bool = False):
    orig = Image.open(original).convert("RGB"); exp = Image.open(expanded).convert("RGB")
    if erase_mark:
        # the expansion re-renders the mark too, and the feathered top edge would let it show through
        orig = erase_top_center_mark(orig); exp = erase_top_center_mark(exp)
    err, s, x, y = find_match(orig, exp)
    h = int(round(exp.height * s)); w = int(round(h * orig.width / orig.height)); o = orig.resize((w, h), Image.LANCZOS)
    # color-match original to the expansion over the overlap (per-channel mean/std)
    x0, y0 = max(x, 0), max(y, 0); x1, y1 = min(x + w, exp.width), min(y + h, exp.height)
    E = np.asarray(exp.crop((x0, y0, x1, y1)), dtype=np.float32); O = np.asarray(o.crop((x0 - x, y0 - y, x1 - x, y1 - y)), dtype=np.float32)
    arr = np.asarray(o, dtype=np.float32)
    for c in range(3):
        g = E[..., c].std() / max(O[..., c].std(), 1e-3); g = float(np.clip(g, 0.85, 1.15))
        arr[..., c] = (arr[..., c] - O[..., c].mean()) * g + E[..., c].mean()
    o = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    # feathered mask: soft on sides that border generated area, hard where the original touches the frame edge
    m = np.ones((h, w), dtype=np.float32); ramp = np.linspace(0, 1, feather, dtype=np.float32)
    if x > 2: m[:, :feather] *= ramp[None, :]
    if x + w < exp.width - 2: m[:, -feather:] *= ramp[::-1][None, :]
    if y > 2: m[:feather, :] *= ramp[:, None]
    if y + h < exp.height - 2: m[-feather:, :] *= ramp[::-1][:, None]
    res = exp.copy(); res.paste(o, (x, y), Image.fromarray((m * 255).astype(np.uint8)))
    out.parent.mkdir(parents=True, exist_ok=True); res.save(out, quality=95)
    return {"error": round(err, 2), "scale": round(float(s), 4), "x": int(x), "y": int(y), "size": res.size}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original", type=Path); ap.add_argument("expanded", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--feather", type=int, default=70); ap.add_argument("--erase-mark", action="store_true")
    a = ap.parse_args(argv); print(restore(a.original, a.expanded, a.out, a.feather, a.erase_mark))


if __name__ == "__main__":
    sys.exit(main())
