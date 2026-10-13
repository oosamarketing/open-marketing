"""Turn any logo into a round profile avatar (the circle Meta/Instagram show next to the page name).

Wordmarks are wide and often two-tone; dropped straight into a 40 px circle they get cropped or
vanish on white. This centers the logo on a solid brand-color disc with padding, removes a white
background if the source is a JPEG/opaque PNG, and returns a square PNG with transparent corners.

    from ad_copywriter.preview.avatar import make_avatar
    make_avatar("logo.png", "avatar.png", bg="#7ea1c0")
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _strip_white_background(im: Image.Image, thresh: int = 235) -> Image.Image:
    """Make near-white pixels connected to the border transparent (opaque logos on white)."""
    from PIL import ImageOps
    if im.getchannel("A").getextrema()[0] < 255:
        return im  # already has transparency
    gray = ImageOps.grayscale(im.convert("RGB"))
    mask = gray.point(lambda v: 255 if v >= thresh else 0)  # white-ish = 255
    # flood from the corners: anything reachable through white-ish pixels is background
    bg = Image.new("L", im.size, 0)
    from PIL import ImageDraw as _D
    seed = mask.copy()
    for xy in [(0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1)]:
        if seed.getpixel(xy) == 255:
            _D.floodfill(seed, xy, 128)
    bgmask = seed.point(lambda v: 255 if v == 128 else 0)
    alpha = im.getchannel("A").copy()
    alpha.paste(0, mask=bgmask)
    out = im.copy(); out.putalpha(alpha)
    return out


def make_avatar(logo: str | Path, out: str | Path, *, bg: str = "#111111", size: int = 512, pad: float = 0.18,
                strip_white: bool = True) -> Path:
    im = Image.open(logo).convert("RGBA")
    if strip_white:
        im = _strip_white_background(im)
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
    inner = int(size * (1 - 2 * pad))
    scale = min(inner / im.width, inner / im.height)
    im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    fill = Image.new("RGBA", (size, size), _hex(bg) + (255,))
    disc.paste(fill, (0, 0), mask)
    disc.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    disc.save(out, "PNG", optimize=True)
    return out
