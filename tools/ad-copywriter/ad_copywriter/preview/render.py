"""HTML rendering for the copy deck and the platform mockups, plus HTML → PDF.

All copy goes through ``html.escape``. Fonts are bundled and referenced with
absolute ``file://`` URLs so the same HTML renders identically from any cwd and
on a machine that has no Montserrat installed.
"""

from __future__ import annotations

import base64
import datetime as _dt
import html as _html
import mimetypes
from pathlib import Path

from ..document import CopyDocument, CopySet
from ..spec import PlatformSpec
from ..textutil import count_chars, domain_of, split_blocks, truncate_fold

_HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = _HERE / "templates"
ASSETS_DIR = _HERE / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
DEFAULT_LOGO = ASSETS_DIR / "oosa-logo.png"

STYLES = ("deck", "mockup", "both")

_FONT_FILES = (
    ("Montserrat-Regular.ttf", 400),
    ("Montserrat-SemiBold.ttf", 600),
    ("Montserrat-Bold.ttf", 700),
)


def e(text: object) -> str:
    return _html.escape("" if text is None else str(text), quote=True)


def _read(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def font_face_css(fonts_dir: str | Path | None = None, *, embed: bool = False) -> str:
    """``@font-face`` rules for the bundled Montserrat files (absolute file:// URLs, or base64 when ``embed``)."""
    fonts = Path(fonts_dir or FONTS_DIR)
    rules = []
    for name, weight in _FONT_FILES:
        p = fonts / name
        if not p.exists():
            continue
        if embed:
            data = base64.b64encode(p.read_bytes()).decode()
            src = f"url(data:font/ttf;base64,{data}) format('truetype')"
        else:
            src = f"url('{p.as_uri()}') format('truetype')"
        rules.append(f"@font-face{{font-family:'Montserrat';font-style:normal;font-weight:{weight};src:{src};}}")
    return "\n".join(rules)


def _logo_src(logo: str | Path | None, *, embed: bool) -> str | None:
    """Resolve a logo path/URL to an img src. Returns None when there is nothing usable."""
    if not logo:
        return None
    s = str(logo)
    if s.startswith(("http://", "https://", "data:")):
        return s
    p = Path(s)
    if not p.exists():
        return None
    if embed:
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    return p.resolve().as_uri()


def _head(title: str, css: list[str], *, fonts: bool, embed: bool) -> str:
    parts = [_read("base.css"), *css]
    font_css = font_face_css(embed=embed) if fonts else ""
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{e(title)}</title><style>{font_css}\n{chr(10).join(parts)}</style></head><body>"
    )


def _theme_meta(cs: CopySet) -> str:
    bits = [b for b in (cs.display_url, cs.landing_page_url) if b]
    return f"<p class=\"theme-meta\">{' · '.join(e(b) for b in bits)}</p>" if bits else ""


# -- deck -------------------------------------------------------------------

def render_deck_html(
    doc: CopyDocument,
    *,
    logo: str | Path | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    date: str | None = None,
    fonts: bool = True,
    embed_assets: bool = False,
    show_counts: bool = True,
    standalone: bool = True,
) -> str:
    spec = doc.spec
    body = _deck_body(doc, spec, logo=logo, title=title, subtitle=subtitle, date=date,
                      embed_assets=embed_assets, show_counts=show_counts)
    if not standalone:
        return body
    return _head(title or spec.deck_title, [_read("deck.css")], fonts=fonts, embed=embed_assets) + body + "</body></html>"


def _deck_body(doc: CopyDocument, spec: PlatformSpec, *, logo, title, subtitle, date, embed_assets, show_counts) -> str:
    logo_src = _logo_src(logo or doc.brand.get("logo_path") or DEFAULT_LOGO, embed=embed_assets)
    date_str = date or f"{_dt.date.today():%B %d, %Y}"
    sub = subtitle or f"{doc.brand_name} · {spec.deck_subtitle} · {date_str}"
    out = ["<header class=\"deck-header\">"]
    if logo_src:
        out.append(f"<img class=\"logo\" src=\"{e(logo_src)}\" alt=\"{e(doc.brand_name)}\">")
    else:
        out.append(f"<div class=\"wordmark\">{e(doc.brand_name)}</div>")
    out.append(f"<h1>{e(title or spec.deck_title)}</h1><p class=\"subtitle\">{e(sub)}</p></header><hr class=\"rule\">")

    for si, cs in enumerate(doc.sets):
        cls = "theme page-break" if si else "theme"
        out.append(f"<section class=\"{cls}\"><h2>{e(cs.theme)}</h2>{_theme_meta(cs)}")
        for f in spec.fields:
            options = cs.options(f.key)
            if not options:
                continue
            out.append(f"<h4>{e(f.plural)}</h4><ul>")
            for text in options:
                n = count_chars(text)
                count = ""
                if show_counts:
                    over = " over" if n > f.max_chars else ""
                    count = f"<span class=\"count{over}\">{n}/{f.max_chars}</span>"
                if f.multiline:
                    blocks = split_blocks(text) or [text]
                    inner = "\n...\n".join(e(b) for b in blocks)
                    out.append(f"<li class=\"block-text\"><span class=\"option\">{inner}</span>{count}</li>")
                else:
                    out.append(f"<li><span class=\"option\">{e(text)}</span>{count}</li>")
            out.append("</ul>")
        aud = [(r.label, cs.audiences.get(r.key)) for r in spec.optional_rows if cs.audiences.get(r.key)]
        if aud:
            out.append("<div class=\"audiences\">" + "".join(f"<span><b>{e(k)}:</b> {e(v)}</span>" for k, v in aud) + "</div>")
        if cs.notes:
            out.append(f"<p class=\"notes\">{e(cs.notes)}</p>")
        out.append("<hr class=\"rule\"></section>")
    return "".join(out)


# -- mockups ----------------------------------------------------------------

def _rot(items: list[str], i: int, n: int) -> list[str]:
    """``n`` items starting at ``i`` with wraparound; fewer if the list is short."""
    if not items:
        return []
    return [items[(i + k) % len(items)] for k in range(min(n, len(items)))]


def _handle(doc: CopyDocument) -> str:
    """Instagram-style username derived from the page name (``North Peak`` → ``northpeak``)."""
    name = str(doc.brand.get("page_name") or doc.brand_name)
    return "".join(ch for ch in name.lower() if ch.isalnum()) or "brand"


def _google_card(cs: CopySet, doc: CopyDocument, combo: int, *, logo_src: str | None) -> str:
    """A desktop Google search result: Sponsored label, favicon + site + URL, headline row, description, sitelinks, callouts."""
    domain = domain_of(cs.landing_page_url or doc.brand.get("website")) or "example.com"
    paths = [p for p in cs.options("path") if p]
    if cs.display_url and "/" in cs.display_url and not paths:
        paths = [seg for seg in cs.display_url.split("/")[1:] if seg]
    url = domain + "".join(f" › {p}" for p in paths[:2])
    headlines = _rot(cs.options("headline"), combo, 3)
    descriptions = _rot(cs.options("description"), combo, 2)
    fav = f"<img src=\"{e(logo_src)}\" alt=\"\">" if logo_src else e((doc.brand_name[:1] or "A").upper())
    out = [
        "<div class=\"gcard\"><div class=\"g-sponsored\">Sponsored</div>",
        f"<div class=\"g-top\"><div class=\"g-fav\">{fav}</div><div><div class=\"g-site\">{e(doc.brand_name)}</div>"
        f"<div class=\"g-url\">{e(url)}</div></div></div>",
        "<div class=\"g-headline\">" + "<span class=\"sep\">|</span>".join(e(h) for h in headlines) + "</div>",
        f"<div class=\"g-desc\">{' '.join(e(d) for d in descriptions)}</div>",
    ]
    sitelinks = cs.options("sitelink")[:4]
    if sitelinks:
        cells = [f"<td><div class=\"sl\">{e(s)}</div></td>" for s in sitelinks]
        rows = ["<tr>" + "".join(cells[i:i + 2]) + "</tr>" for i in range(0, len(cells), 2)]
        out.append("<table class=\"g-sitelinks\">" + "".join(rows) + "</table>")
    callouts = cs.options("callout")[:4]
    if callouts:
        out.append("<div class=\"g-callouts\">" + "<span class=\"dot\">·</span>".join(e(c) for c in callouts) + "</div>")
    out.append("</div>")
    return "".join(out)


def _fold_html(text: str, fold: int, marker: str = "… See more") -> str:
    visible, truncated = truncate_fold(text, fold, marker="")
    html = e(visible)
    if truncated:
        html += f"<span class=\"see-more\">{e(marker)}</span>"
    return html


def _media_src(cs: CopySet, combo: int, kind: str, *, embed: bool) -> tuple[str | None, bool]:
    """Creative for one mockup card → (src, is_wide). ``media_paths`` rotates per variation and carries
    square/wide versions (Instagram wants square, Facebook feed prefers wide); ``media_path`` is the
    single-image fallback."""
    if cs.media_paths:
        m = cs.media_paths[combo % len(cs.media_paths)]
        used = kind if m.get(kind) else ("square" if m.get("square") else "wide")
        return _logo_src(m.get(used), embed=embed), used == "wide"
    return _logo_src(cs.media_path, embed=embed), False


def _facebook_card(cs: CopySet, doc: CopyDocument, combo: int, *, logo_src: str | None, media_src: str | None,
                   media_wide: bool = False) -> str:
    """A Facebook feed post: page header, primary text with the See more fold, creative, link card with CTA, reactions."""
    page = doc.brand.get("page_name") or doc.brand_name
    primary = _rot(cs.options("primary_text"), combo, 1)
    headline = _rot(cs.options("headline"), combo, 1)
    desc = _rot(cs.options("description"), combo, 1)
    fold = doc.spec.field("primary_text").fold_chars or 125
    display_url = cs.display_url or domain_of(cs.landing_page_url or doc.brand.get("website")) or "example.com"
    avatar = f"<img src=\"{e(logo_src)}\" alt=\"\">" if logo_src else e((page[:1] or "A").upper())
    media = f"<img src=\"{e(media_src)}\" alt=\"\">" if media_src else "Image / video"
    media_cls = "fb-media wide" if (media_src and media_wide) else "fb-media"
    return (
        "<div class=\"fb\">"
        f"<div class=\"fb-head\"><div class=\"avatar\">{avatar}</div><div><div class=\"fb-name\">{e(page)}</div>"
        "<div class=\"fb-sub\">Sponsored · 🌐</div></div><div class=\"fb-menu\">···</div></div>"
        f"<div class=\"fb-text\">{_fold_html(primary[0] if primary else '', fold)}</div>"
        f"<div class=\"{media_cls}\">{media}</div>"
        f"<div class=\"fb-link\"><div class=\"txt\"><div class=\"dom\">{e(display_url)}</div>"
        f"<div class=\"hl\">{e(headline[0]) if headline else ''}</div><div class=\"dsc\">{e(desc[0]) if desc else ''}</div></div>"
        f"<div class=\"cta\">{e(cs.cta or 'Shop now')}</div></div>"
        "<div class=\"fb-react\"><span>👍 ❤️ 1.2K</span><span class=\"right\">34 comments · 9 shares</span></div>"
        "<div class=\"fb-actions\"><span>👍 Like</span><span>💬 Comment</span><span>↗ Share</span></div>"
        "</div>"
    )


def _instagram_card(cs: CopySet, doc: CopyDocument, combo: int, *, logo_src: str | None, media_src: str | None) -> str:
    """An Instagram feed post: handle header, square creative, blue CTA bar, action row, caption folded with 'more'."""
    handle = _handle(doc)
    primary = _rot(cs.options("primary_text"), combo, 1)
    fold = doc.spec.field("primary_text").fold_chars or 125
    avatar = f"<img src=\"{e(logo_src)}\" alt=\"\">" if logo_src else e((handle[:1] or "a").upper())
    media = f"<img src=\"{e(media_src)}\" alt=\"\">" if media_src else "Image / video"
    return (
        "<div class=\"ig\">"
        f"<div class=\"ig-head\"><div class=\"ig-avatar\">{avatar}</div><div><div class=\"ig-user\">{e(handle)}</div>"
        "<div class=\"ig-sub\">Sponsored</div></div><div class=\"ig-menu\">···</div></div>"
        f"<div class=\"ig-media\">{media}</div>"
        f"<div class=\"ig-cta\"><span>{e(cs.cta or 'Shop now')}</span><span class=\"chev\">›</span></div>"
        "<div class=\"ig-actions\"><span>♡</span><span>◯</span><span>➤</span><span class=\"save\">⊓</span></div>"
        "<div class=\"ig-likes\">1,204 likes</div>"
        f"<div class=\"ig-caption\"><b>{e(handle)}</b>{_fold_html(primary[0] if primary else '', fold, '… more')}</div>"
        "</div>"
    )


def render_mockup_html(
    doc: CopyDocument,
    *,
    logo: str | Path | None = None,
    avatar: str | Path | None = None,
    combos: int = 3,
    fonts: bool = True,
    embed_assets: bool = False,
    standalone: bool = True,
    first_page_break: bool = False,
) -> str:
    """Per theme: Google → one search result per variation; Meta → a Facebook feed post and an
    Instagram feed post side by side per variation. Rows never split across pages.
    ``sets[].media_paths`` (one entry per variation, square/wide) or ``sets[].media_path`` (single file or
    URL) is used as the creative; otherwise a grey placeholder."""
    spec = doc.spec
    # the round page avatar: brand.avatar_path (or --avatar) beats the wide logo, which crops badly in a circle
    logo_src = _logo_src(avatar or doc.brand.get("avatar_path") or logo or doc.brand.get("logo_path"), embed=embed_assets)
    out = []
    for si, cs in enumerate(doc.sets):
        cls = "mockup-page page-break" if (si or first_page_break) else "mockup-page"
        out.append(f"<section class=\"{cls}\"><h2>{e(cs.theme)} — {e(spec.label)} mockups</h2>{_theme_meta(cs)}")
        n_opts = max((len(cs.options(f.key)) for f in spec.fields), default=0)
        n = max(1, min(combos, n_opts))
        if cs.media_paths:
            n = max(n, min(combos, len(cs.media_paths)))
        out.append("<table class=\"mockup-grid\">")
        for i in range(n):
            if spec.mockup == "meta_feed":
                fb_src, fb_wide = _media_src(cs, i, "wide", embed=embed_assets)
                ig_src, _ = _media_src(cs, i, "square", embed=embed_assets)
                fb = _facebook_card(cs, doc, i, logo_src=logo_src, media_src=fb_src, media_wide=fb_wide)
                ig = _instagram_card(cs, doc, i, logo_src=logo_src, media_src=ig_src)
                out.append(f"<tr><td class=\"combo\"><p class=\"combo-label\">Variation {i + 1} · Facebook feed</p>{fb}</td>"
                           f"<td class=\"combo\"><p class=\"combo-label\">Variation {i + 1} · Instagram feed</p>{ig}</td></tr>")
            else:
                out.append(f"<tr><td class=\"combo\"><p class=\"combo-label\">Variation {i + 1} · Google Search</p>"
                           f"{_google_card(cs, doc, i, logo_src=logo_src)}</td></tr>")
        out.append("</table></section>")
    body = "".join(out)
    if not standalone:
        return body
    return _head(f"{spec.label} mockups", [_read("mockup.css")], fonts=fonts, embed=embed_assets) + body + "</body></html>"


# -- combined + pdf ----------------------------------------------------------

def render_html(
    doc: CopyDocument,
    style: str = "both",
    *,
    logo: str | Path | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    date: str | None = None,
    combos: int = 3,
    fonts: bool = True,
    embed_assets: bool = False,
    show_counts: bool = True,
    avatar: str | Path | None = None,
    mockups_first: bool = False,
) -> str:
    if style not in STYLES:
        raise ValueError(f"unknown style {style!r}; expected one of {STYLES}")
    spec = doc.spec
    if style == "deck":
        return render_deck_html(doc, logo=logo, title=title, subtitle=subtitle, date=date, fonts=fonts,
                                embed_assets=embed_assets, show_counts=show_counts)
    if style == "mockup":
        return render_mockup_html(doc, logo=logo, avatar=avatar, combos=combos, fonts=fonts, embed_assets=embed_assets)
    deck = render_deck_html(doc, logo=logo, title=title, subtitle=subtitle, date=date, fonts=fonts,
                            embed_assets=embed_assets, show_counts=show_counts, standalone=False)
    mock = render_mockup_html(doc, logo=logo, avatar=avatar, combos=combos, fonts=fonts, embed_assets=embed_assets,
                              standalone=False, first_page_break=not mockups_first)
    if mockups_first:
        deck = deck.replace("<section class=\"", "<section class=\"page-break ", 1)
        body = mock + deck
    else:
        body = deck + mock
    return (_head(title or spec.deck_title, [_read("deck.css"), _read("mockup.css")], fonts=fonts, embed=embed_assets)
            + body + "</body></html>")


def html_to_pdf(html: str, out_path: str | Path, *, base_url: str | Path | None = None) -> Path:
    """Render HTML to PDF with WeasyPrint. Raises ImportError with an install hint if missing."""
    try:
        from weasyprint import HTML
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "weasyprint is not installed. `pip install weasyprint` (macOS also needs `brew install pango`)."
        ) from exc
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(base_url or ASSETS_DIR)).write_pdf(str(out))
    return out
