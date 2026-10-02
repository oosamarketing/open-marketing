"""
sections.py — email section builders.

Every builder returns ONE snippet: a single `<div>…</div>` with inline CSS only. No <html>, <head>,
<body>, <style>, <script>, classes or ids. Snippets paste straight into an ESP's HTML/code block
(Klaviyo, Mailchimp, Shopify Email) and stack to form a full email.

Layout rules that make them survive real inboxes:
  - max-width container that is fluid below it (no media queries exist without <style>)
  - tables with role="presentation" inside the div, bgcolor attributes duplicated for Outlook
  - multi-column rows are inline-block cells that wrap on narrow screens, with an MSO ghost table
  - images are display:block, width:100%, height:auto, with alt text and a width attribute
  - buttons are table cells with a padded link (no images, no VML)
"""
from __future__ import annotations

import html as _h
import re
from dataclasses import dataclass, field


def esc(s) -> str:
    return _h.escape(str(s if s is not None else ""), quote=True)


@dataclass
class Theme:
    width: int = 600
    bg: str = "#ffffff"          # section background
    ink: str = "#222222"         # body text
    muted: str = "#666666"       # secondary text
    brand: str = "#111111"       # primary brand color
    accent: str = "#d9822b"      # highlights, eyebrow text
    btn_bg: str = ""             # defaults to brand
    btn_fg: str = "#ffffff"
    radius: int = 6
    font: str = "Helvetica, Arial, sans-serif"
    headline_font: str = "Helvetica, Arial, sans-serif"
    pad_x: int = 24
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_tokens(cls, tokens: dict, overrides: dict | None = None) -> "Theme":
        o = overrides or {}
        serif = o.get("headline_fallback", tokens.get("headline_fallback", "sans")) == "serif"
        body = tokens.get("font")
        head = tokens.get("headline_font") or body
        t = cls(
            bg=tokens.get("paper", "#ffffff"), ink=tokens.get("ink", "#222222"), muted=tokens.get("muted", "#666666"),
            brand=tokens.get("color", "#111111"), accent=tokens.get("accent", "#d9822b"),
            font=(f"'{body}', " if body else "") + "Helvetica, Arial, sans-serif",
            headline_font=(f"'{head}', " if head else "") + ("Georgia, 'Times New Roman', serif" if serif else "Helvetica, Arial, sans-serif"),
        )
        for k, v in o.items():
            if hasattr(t, k):
                setattr(t, k, v)
        t.btn_bg = t.btn_bg or t.brand
        return t


def inline(text, t: Theme, link_color: str | None = None) -> str:
    """Escape, then allow **bold**, [text](url) and newlines."""
    s = esc(text)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", lambda m: f'<a href="{m.group(2)}" style="color:{link_color or t.brand};text-decoration:underline;">{m.group(1)}</a>', s)
    return s.replace("\n", "<br>")


def _wrap(t: Theme, inner: str, bg: str | None = None, pad: str | None = None, align: str = "left", color: str | None = None) -> str:
    bg = bg or t.bg
    pad = pad if pad is not None else f"32px {t.pad_x}px"
    return (f'<div style="margin:0 auto;width:100%;max-width:{t.width}px;background-color:{bg};">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">'
            f'<tr><td bgcolor="{bg}" align="{align}" style="padding:{pad};font-family:{t.font};font-size:16px;line-height:1.5;color:{color or t.ink};text-align:{align};">'
            f'{inner}</td></tr></table></div>')


def _button(t: Theme, text: str, href: str, bg: str | None = None, fg: str | None = None, align: str = "center") -> str:
    bg = bg or t.btn_bg; fg = fg or t.btn_fg
    margin = "0 auto" if align == "center" else "0"
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="{align}" style="margin:{margin};border-collapse:separate;">'
            f'<tr><td bgcolor="{bg}" align="center" style="background-color:{bg};border-radius:{t.radius}px;">'
            f'<a href="{esc(href)}" target="_blank" style="display:inline-block;padding:14px 30px;font-family:{t.font};font-size:15px;line-height:1.2;font-weight:700;letter-spacing:{t.extra.get("button_tracking", "1px")};text-transform:{t.extra.get("button_case", "uppercase")};'
            f'color:{fg};text-decoration:none;border-radius:{t.radius}px;">{esc(text)}</a></td></tr></table>')


def _img(src: str, alt: str, width: int, href: str | None = None, radius: int = 0) -> str:
    r = f"border-radius:{radius}px;" if radius else ""
    tag = (f'<img src="{esc(src)}" alt="{esc(alt)}" width="{width}" '
           f'style="display:block;width:100%;max-width:{width}px;height:auto;border:0;outline:none;text-decoration:none;{r}">')
    return f'<a href="{esc(href)}" target="_blank" style="display:block;text-decoration:none;">{tag}</a>' if href else tag


# ---------------------------------------------------------------- sections

def header(t: Theme, s: dict) -> str:
    """Logo bar. s: logo (src), alt, href, logo_width, bg, align"""
    w = int(s.get("logo_width", 160))
    return _wrap(t, f'<div style="display:inline-block;width:100%;max-width:{w}px;">{_img(s["logo"], s.get("alt", "Logo"), w, s.get("href"))}</div>',
                 bg=s.get("bg"), pad=s.get("pad", f"22px {t.pad_x}px"), align=s.get("align", "center"))


def image(t: Theme, s: dict) -> str:
    """Full-width graphic or photo. s: src, alt, href"""
    return (f'<div style="margin:0 auto;width:100%;max-width:{t.width}px;font-size:0;line-height:0;">'
            f'{_img(s["src"], s.get("alt", ""), t.width, s.get("href"))}</div>')


def hero_text(t: Theme, s: dict) -> str:
    """Live-text hero. s: eyebrow, headline, body, button{text,href}, bg, color, align"""
    color = s.get("color"); parts = []
    if s.get("eyebrow"):
        parts.append(f'<div style="font-size:13px;line-height:1.3;letter-spacing:2px;text-transform:uppercase;font-weight:700;color:{s.get("eyebrow_color", t.accent)};margin:0 0 12px;">{inline(s["eyebrow"], t)}</div>')
    parts.append(f'<div role="heading" aria-level="1" style="font-family:{t.headline_font};font-size:{s.get("size", 36)}px;line-height:1.15;font-weight:700;color:{color or t.ink};margin:0 0 14px;">{inline(s["headline"], t)}</div>')
    if s.get("body"):
        parts.append(f'<div style="font-size:17px;line-height:1.55;color:{color or t.muted};margin:0 0 24px;">{inline(s["body"], t, color)}</div>')
    if s.get("button"):
        parts.append(_button(t, s["button"]["text"], s["button"]["href"], s["button"].get("bg"), s["button"].get("fg"), s.get("align", "center")))
    return _wrap(t, "".join(parts), bg=s.get("bg"), pad=s.get("pad", f"44px {t.pad_x}px"), align=s.get("align", "center"), color=color)


def text(t: Theme, s: dict) -> str:
    """Heading + paragraphs + optional bullets. s: heading, paragraphs[], bullets[], button, bg, align"""
    color = s.get("color"); parts = []
    if s.get("heading"):
        parts.append(f'<div role="heading" aria-level="2" style="font-family:{t.headline_font};font-size:{s.get("size", 24)}px;line-height:1.25;font-weight:700;color:{color or t.ink};margin:0 0 12px;">{inline(s["heading"], t)}</div>')
    for p in s.get("paragraphs", []):
        parts.append(f'<div style="font-size:16px;line-height:1.6;color:{color or t.ink};margin:0 0 14px;">{inline(p, t, color)}</div>')
    if s.get("bullets"):
        rows = "".join(f'<tr><td valign="top" style="padding:0 10px 8px 0;font-size:16px;line-height:1.5;color:{t.accent};">&bull;</td>'
                       f'<td valign="top" style="padding:0 0 8px;font-family:{t.font};font-size:16px;line-height:1.5;color:{color or t.ink};text-align:left;">{inline(b, t, color)}</td></tr>' for b in s["bullets"])
        parts.append(f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;margin:0 0 8px;">{rows}</table>')
    if s.get("button"):
        parts.append(f'<div style="padding-top:10px;">{_button(t, s["button"]["text"], s["button"]["href"], align=s.get("align", "left"))}</div>')
    return _wrap(t, "".join(parts), bg=s.get("bg"), pad=s.get("pad"), align=s.get("align", "left"), color=color)


def button(t: Theme, s: dict) -> str:
    """Standalone call to action. s: text, href, bg, fg, section_bg"""
    return _wrap(t, _button(t, s["text"], s["href"], s.get("bg"), s.get("fg")), bg=s.get("section_bg"), pad=s.get("pad", f"8px {t.pad_x}px 32px"), align="center")


def columns(t: Theme, s: dict) -> str:
    """2–3 cards that sit side by side on desktop and stack on phones.
    s: heading, items[{image, alt, title, text, price, href, link_text}], cols, bg"""
    items = s["items"]; n = int(s.get("cols", min(len(items), 3))); gap = 12
    col_w = (t.width - 2 * t.pad_x) // n
    cells = []
    for it in items:
        inner = ""
        if it.get("image"):
            inner += _img(it["image"], it.get("alt", it.get("title", "")), col_w - gap, it.get("href"), radius=s.get("image_radius", 0))
        if it.get("title"):
            inner += f'<div style="font-family:{t.headline_font};font-size:18px;line-height:1.3;font-weight:700;color:{t.ink};margin:12px 0 4px;">{inline(it["title"], t)}</div>'
        if it.get("text"):
            inner += f'<div style="font-size:14px;line-height:1.5;color:{t.muted};margin:0 0 6px;">{inline(it["text"], t)}</div>'
        if it.get("price"):
            inner += f'<div style="font-size:15px;line-height:1.4;font-weight:700;color:{t.ink};margin:0 0 6px;">{esc(it["price"])}</div>'
        if it.get("href") and it.get("link_text"):
            inner += f'<a href="{esc(it["href"])}" target="_blank" style="font-size:14px;line-height:1.4;font-weight:700;color:{t.brand};text-decoration:underline;">{esc(it["link_text"])}</a>'
        cells.append(f'<div style="display:inline-block;width:100%;max-width:{col_w}px;vertical-align:top;font-family:{t.font};font-size:16px;line-height:1.5;text-align:{s.get("align", "center")};">'
                     f'<div style="padding:{gap // 2}px;">{inner}</div></div>')
    ghost_open = f'<!--[if mso]><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td width="{col_w}" valign="top"><![endif]-->'
    ghost_mid = f'<!--[if mso]></td><td width="{col_w}" valign="top"><![endif]-->'
    ghost_close = '<!--[if mso]></td></tr></table><![endif]-->'
    rows = []
    for i in range(0, len(cells), n):
        rows.append(ghost_open + ghost_mid.join(cells[i:i + n]) + ghost_close)
    head = ""
    if s.get("heading"):
        head = f'<div role="heading" aria-level="2" style="font-family:{t.headline_font};font-size:24px;line-height:1.25;font-weight:700;color:{t.ink};margin:0 0 16px;">{inline(s["heading"], t)}</div>'
    body = head + f'<div style="font-size:0;line-height:0;text-align:center;">{"".join(rows)}</div>'
    return _wrap(t, body, bg=s.get("bg"), pad=s.get("pad", f"28px {t.pad_x}px"), align="center")


def quote(t: Theme, s: dict) -> str:
    """Testimonial. s: text, author, bg"""
    inner = (f'<div style="font-family:{t.headline_font};font-size:22px;line-height:1.4;color:{s.get("color", t.ink)};margin:0 0 12px;">&ldquo;{inline(s["text"], t)}&rdquo;</div>'
             + (f'<div style="font-size:14px;line-height:1.4;letter-spacing:1px;text-transform:uppercase;color:{s.get("color", t.muted)};">{esc(s["author"])}</div>' if s.get("author") else ""))
    return _wrap(t, inner, bg=s.get("bg"), pad=s.get("pad", f"36px {t.pad_x + 12}px"), align="center")


def divider(t: Theme, s: dict) -> str:
    return _wrap(t, f'<div style="border-top:1px solid {s.get("color", "#e5e5e5")};font-size:0;line-height:0;height:0;">&nbsp;</div>', bg=s.get("bg"), pad=s.get("pad", f"8px {t.pad_x}px"))


def spacer(t: Theme, s: dict) -> str:
    h = int(s.get("height", 24))
    return f'<div style="margin:0 auto;width:100%;max-width:{t.width}px;height:{h}px;line-height:{h}px;font-size:0;background-color:{s.get("bg", t.bg)};">&nbsp;</div>'


def footer(t: Theme, s: dict) -> str:
    """Legal footer stays live text, always. s: lines[], links[{text,href}], bg, color
    ESP merge tags (e.g. {% unsubscribe %}, {{ organization.full_address }}) pass through untouched."""
    color = s.get("color", t.muted); parts = []
    if s.get("links"):
        parts.append('<div style="margin:0 0 12px;">' + " &nbsp;|&nbsp; ".join(
            f'<a href="{l["href"]}" target="_blank" style="color:{color};text-decoration:underline;">{esc(l["text"])}</a>' for l in s["links"]) + "</div>")
    for ln in s.get("lines", []):
        parts.append(f'<div style="margin:0 0 6px;">{ln if "{%" in ln or "{{" in ln else inline(ln, t, color)}</div>')
    return _wrap(t, f'<div style="font-size:12px;line-height:1.6;color:{color};">{"".join(parts)}</div>', bg=s.get("bg"), pad=s.get("pad", f"28px {t.pad_x}px"), align="center", color=color)


def raw(t: Theme, s: dict) -> str:
    """Hand-written snippet. Must already be a single <div>…</div> with inline CSS; it is linted like the rest."""
    return s["html"].strip()


def offer(t: Theme, s: dict) -> str:
    """Live offer block: body copy, a copyable code chip, a note, one button.
    s: body, code_label, code, note, button{text,href}, bg, color, chip_bg, chip_fg, chip_border"""
    color = s.get("color", t.ink); parts = []
    if s.get("body"):
        parts.append(f'<div style="font-size:17px;line-height:1.55;color:{color};margin:0 0 22px;">{inline(s["body"], t, color)}</div>')
    if s.get("code"):
        chip_bg = s.get("chip_bg", "#000000"); chip_fg = s.get("chip_fg", t.accent); border = s.get("chip_border", t.accent)
        parts.append(f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:0 auto 10px;border-collapse:separate;">'
                     f'<tr><td bgcolor="{chip_bg}" align="center" style="background-color:{chip_bg};border:2px solid {border};border-radius:{t.radius}px;padding:12px 22px;">'
                     f'<span style="font-family:{t.font};font-size:13px;letter-spacing:2px;text-transform:uppercase;color:{color};">{esc(s.get("code_label", "Use code"))}</span>'
                     f'&nbsp;&nbsp;<span style="font-family:{t.font};font-size:24px;line-height:1.2;font-weight:800;letter-spacing:3px;color:{chip_fg};">{s["code"] if ("{%" in s["code"] or "{{" in s["code"]) else esc(s["code"])}</span>'
                     f'</td></tr></table>')
    if s.get("note"):
        parts.append(f'<div style="font-size:13px;line-height:1.4;color:{s.get("note_color", t.muted)};margin:0 0 22px;">{inline(s["note"], t, color)}</div>')
    if s.get("button"):
        parts.append(_button(t, s["button"]["text"], s["button"]["href"], s["button"].get("bg"), s["button"].get("fg")))
    return _wrap(t, "".join(parts), bg=s.get("bg"), pad=s.get("pad", f"30px {t.pad_x}px 36px"), align="center", color=color)


def compare(t: Theme, s: dict) -> str:
    """Us-vs-them rows that stay paired on phones. Each row: a "yes" cell and a "no" cell side by side
    on desktop; on narrow screens the pair stacks (yes above no) so the comparison still reads.
    s: heading, left_label, right_label, rows[{yes_title, yes, no_title, no}], yes_icon (image src), no_icon,
       bg, color, muted, rule"""
    color = s.get("color", t.ink); muted = s.get("muted", t.muted); rule = s.get("rule", "#333333")
    half = (t.width - 2 * t.pad_x) // 2; icon_w = 20
    def cell(title, body, icon, title_color, w):
        ic = (f'<img src="{esc(icon)}" alt="" width="{icon_w}" style="display:block;width:{icon_w}px;height:auto;border:0;">' if icon and not icon.startswith("text:")
              else f'<span style="font-size:18px;line-height:1;font-weight:700;color:{title_color};">{esc(icon[5:]) if icon else ""}</span>')
        return (f'<div style="display:inline-block;width:100%;max-width:{w}px;vertical-align:top;padding:0 0 10px;">'
                f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;"><tr>'
                f'<td valign="top" width="{icon_w + 12}" style="padding:2px 12px 0 0;width:{icon_w + 12}px;">{ic}</td>'
                f'<td valign="top" style="padding:0 12px 0 0;font-family:{t.font};text-align:left;">'
                f'<div style="font-size:15px;line-height:1.3;font-weight:800;letter-spacing:.5px;text-transform:uppercase;color:{title_color};margin:0 0 3px;">{inline(title, t)}</div>'
                f'<div style="font-size:14px;line-height:1.45;color:{color};">{inline(body, t, color)}</div></td></tr></table></div>')
    rows = []
    for r in s["rows"]:
        rows.append(f'<div style="padding:16px 0 6px;border-bottom:1px solid {rule};font-size:0;line-height:0;">'
                    + cell(r["yes_title"], r["yes"], s.get("yes_icon"), s.get("yes_color", t.accent), half)
                    + cell(r["no_title"], r["no"], s.get("no_icon", "text:✕"), s.get("no_color", muted), half) + "</div>")
    head = ""
    if s.get("left_label") or s.get("right_label"):
        lab = lambda txt, c: f'<div style="display:inline-block;width:100%;max-width:{half}px;vertical-align:top;font-family:{t.font};font-size:13px;line-height:1.3;letter-spacing:2px;text-transform:uppercase;font-weight:800;color:{c};text-align:left;">{esc(txt)}</div>'
        head = f'<div style="padding:0 0 6px;border-bottom:2px solid {s.get("yes_color", t.accent)};font-size:0;line-height:0;">{lab(s.get("left_label", ""), s.get("yes_color", t.accent))}{lab(s.get("right_label", ""), muted)}</div>'
    if s.get("heading"):
        head = f'<div role="heading" aria-level="2" style="font-family:{t.headline_font};font-size:24px;line-height:1.25;font-weight:800;text-transform:uppercase;color:{color};margin:0 0 14px;text-align:center;">{inline(s["heading"], t)}</div>' + head
    return _wrap(t, head + "".join(rows), bg=s.get("bg"), pad=s.get("pad", f"26px {t.pad_x}px 30px"), align="left", color=color)


def tiles(t: Theme, s: dict) -> str:
    """Fixed grid of image tiles (2 across on every screen, including phones). Use for category
    tiles whose text is baked into the image. s: items[{image, alt, href}], cols, gap, bg"""
    n = int(s.get("cols", 2)); gap = int(s.get("gap", 4)); w = (t.width - gap * (n - 1)) // n
    rows = []
    for i in range(0, len(s["items"]), n):
        cells = []
        for j, it in enumerate(s["items"][i:i + n]):
            pad = f"0 {gap}px 0 0" if j < n - 1 else "0"
            cells.append(f'<td width="{100 // n}%" valign="top" style="padding:{pad};">{_img(it["image"], it.get("alt", ""), w, it.get("href"))}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>' + (f'<tr><td colspan="{n}" style="height:{gap}px;line-height:{gap}px;font-size:0;">&nbsp;</td></tr>' if i + n < len(s["items"]) else ""))
    return (f'<div style="margin:0 auto;width:100%;max-width:{t.width}px;background-color:{s.get("bg", t.bg)};font-size:0;line-height:0;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">{"".join(rows)}</table></div>')


def social(t: Theme, s: dict) -> str:
    """Text social links (no icon images to host). s: links[{text,href}], bg, color"""
    color = s.get("color", t.muted)
    links = " &nbsp;&middot;&nbsp; ".join(f'<a href="{l["href"]}" target="_blank" style="color:{color};text-decoration:none;font-weight:700;letter-spacing:1px;text-transform:uppercase;font-size:12px;">{esc(l["text"])}</a>' for l in s["links"])
    return _wrap(t, f'<div style="font-size:12px;line-height:1.6;color:{color};">{links}</div>', bg=s.get("bg"), pad=s.get("pad", f"6px {t.pad_x}px 18px"), align="center", color=color)


BUILDERS = {"header": header, "image": image, "hero_text": hero_text, "text": text, "button": button, "columns": columns,
            "quote": quote, "divider": divider, "spacer": spacer, "footer": footer, "raw": raw,
            "offer": offer, "compare": compare, "tiles": tiles, "social": social}
KEEP_LIVE = {"footer", "header", "button", "spacer", "divider", "image", "offer", "tiles", "social"}   # never rasterized by the lite build
