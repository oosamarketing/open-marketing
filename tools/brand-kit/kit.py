#!/usr/bin/env python
"""
kit.py — Turn a confirmed brand.json into a client-ready brand kit:

    python kit.py brands/<slug>.json --out "<client folder>/branding"

Writes:
  <out>/brand-assets/logo/*            copies of the logo files + avatar.png / avatar-secondary.png (round, for profile circles)
  <out>/brand-assets/palette.png       swatch strip
  <out>/brand-assets/brand.json        the source of truth (this file, copied)
  <out>/brand-assets/tokens.json       drop-in for graphic-designer/brand-guidelines/brands/<slug>/
  <out>/brand-assets/brand.md          drop-in for the same folder (voice, colors, fonts, do/don't)
  <out>/<Name> Brand Kit.pdf           6-page letter PDF (DRAFT watermark until sources.confirmed_by is set)

Rendering uses Chromium via Playwright. Fonts load from Google Fonts.
"""
from __future__ import annotations
import argparse, html, json, re, shutil, sys
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from avatar import make_avatar

def esc(s): return html.escape(str(s))

def palette_png(colors, out: Path):
    n = len(colors); w = 220; h = 300
    im = Image.new("RGB", (w * n, h), "white"); d = ImageDraw.Draw(im)
    try: font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except Exception: font = ImageFont.load_default()
    for i, c in enumerate(colors):
        d.rectangle([i * w, 0, (i + 1) * w, 220], fill=c["hex"])
        d.text((i * w + 14, 234), c["name"], fill="#222", font=font); d.text((i * w + 14, 262), c["hex"], fill="#666", font=font)
    im.save(out)

def tokens_from(b):
    by_role = {c["role"]: c["hex"] for c in b["colors"]}
    display = next((f["family"] for f in b["fonts"] if "display" in f["role"]), b["fonts"][0]["family"])
    body = next((f["family"] for f in b["fonts"] if "body" in f["role"]), b["fonts"][-1]["family"])
    return {
        "name": b["name"].upper(), "display_name": b["display_name"],
        "color": by_role.get("primary"), "accent": by_role.get("secondary"), "ink": by_role.get("text", "#111111"),
        "muted": by_role.get("dark accent", "#666666"), "paper": by_role.get("light", "#ffffff"),
        "font": body, "headline_font": display,
        "font_url": "https://fonts.googleapis.com/css2?family=" + "&family=".join(f["family"].replace(" ", "+") + ":wght@400;600;700;800" for f in b["fonts"]) + "&display=swap",
        # relative to the graphic-designer folder (render.py resolves brand tokens against its root)
        "logo": "brand-guidelines/brands/%s/assets/%s" % (b["slug"], Path(b["logo"]["primary"]).name),
        "avatar": "brand-guidelines/brands/%s/assets/avatar.png" % b["slug"],
        "website": b["website"],
        # every kit color by name, e.g. {{ brand.colors.brand_pink }} — lets templates pin a specific
        # color instead of depending on which one currently holds the 'secondary' role
        "colors": {re.sub(r"[^a-z0-9]+", "_", c["name"].lower()).strip("_"): c["hex"] for c in b["colors"]},
    }

def _has_wordmark(b) -> bool:
    return "wordmark" in (b["logo"].get("description", "") + " " + b.get("description", "")).lower()


def _logo_dont(b) -> str:
    bgs = b["logo"].get("backgrounds") or []
    return ("use the logo on backgrounds other than " + ", ".join(bgs)) if bgs else "recolor or stretch the logo"


def type_lead(b) -> str:
    disp = next((f["family"] for f in b["fonts"] if "display" in f["role"]), None)
    body = next((f["family"] for f in b["fonts"] if "body" in f["role"]), None)
    if disp and body and disp != body:
        s = f"{disp} for headlines, {body} for everything else."
    else:
        s = f"One family, {disp or body}, at two or three weights does all the work."
    if any("all caps" in f["role"].lower() for f in b["fonts"]):
        return s + " Set headlines and callouts in all caps; keep body copy in sentence case."
    s += " Keep headlines sentence case or Title Case"
    s += "; the wordmark is the only thing set in tracked caps." if _has_wordmark(b) else "; save all-caps for short labels."
    return s


def brand_md(b):
    v = b["voice"]; L = [f"# {b['name']}", "", "## Snapshot", f"- **Website:** {b['website']}", f"- **What they sell:** {b['description']}", f"- **Tagline:** {b['tagline']}", "",
         "## Voice", f"- Tone: {', '.join(v['tone'])}", f"- Style: {v['style']}", f"- Words we use: {', '.join(v['words_use'])}", f"- Words we avoid: {', '.join(v['words_avoid'])}", "",
         "## Taglines / headline bank"] + [f"- {t}" for t in b["taglines"]] + ["", "## Colors", "| Name | Hex | Role | Usage |", "|---|---|---|---|"] + \
        [f"| {c['name']} | `{c['hex']}` | {c['role']} | {c['usage']} |" for c in b["colors"]] + ["", "## Fonts"] + \
        [f"- **{f['family']}** — {f['role']} ({f['source']}; fallback {f['fallback']})" for f in b["fonts"]] + ["", "## Logo", f"- {b['logo']['description']}", f"- Clear space: {b['logo']['clear_space']}. Minimum width {b['logo']['min_width_px']} px.", f"- Backgrounds: {', '.join(b['logo']['backgrounds'])}", "", "## Products"] + \
        [f"- **{p['name']}** ({p['line_color']}): {p['hero_claim']}. " + "; ".join(p["facts"]) for p in b["products"]] + ["", "## Do / Don't", "- Do: keep copy short; use the headline bank and product facts above; lead with the primary color", f"- Don't: invent claims not in the product facts; {_logo_dont(b)}", "",
         f"_Source: extracted from {b['sources']['extracted_from']} on {b['sources']['extracted_at']}; " + (f"confirmed by {b['sources']['confirmed_by']} on {b['sources']['confirmed_at']}_" if b['sources'].get('confirmed_by') else "NOT YET CONFIRMED by the client_")]
    return "\n".join(L) + "\n"

def _lum(hex_: str) -> float:
    h = hex_.lstrip("#"); r, g, b_ = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b_


def color_lead(b) -> str:
    by = {c["role"]: c for c in b["colors"]}
    parts = []
    if "primary" in by: parts.append(f"{by['primary']['name']} is the primary: {by['primary']['usage'].split(';')[0].rstrip('.')}.")
    if "secondary" in by: parts.append(f"{by['secondary']['name']} is the secondary: {by['secondary']['usage'].split(';')[0].rstrip('.')}.")
    if "accent" in by: parts.append(f"{by['accent']['name']} is the soft accent: {by['accent']['usage'].split('.')[0].rstrip('.')}.")
    if "text" in by: parts.append(f"{by['text']['name']} is for text on light backgrounds.")
    if "light" in by: parts.append(f"{by['light']['name']} is the light neutral and the text color on dark panels.")
    extras = [c["name"] for c in b["colors"] if c["role"] in ("tertiary", "dark accent", "logo accent", "background")]
    if extras: parts.append("Also in the system: " + ", ".join(extras) + ". Keep these to accents, packaging references, and fine print.")
    return " ".join(parts)


def kit_html(b, assets: Path, draft: bool):
    fonts = "&family=".join(f["family"].replace(" ", "+") + ":wght@400;600;700;800" for f in b["fonts"])
    prim = next(c["hex"] for c in b["colors"] if c["role"] == "primary"); ink = next((c["hex"] for c in b["colors"] if c["role"] == "text"), "#222")
    light = next((c["hex"] for c in b["colors"] if c["role"] == "light"), "#fff"); sec = next((c["hex"] for c in b["colors"] if c["role"] == "secondary"), prim)
    disp = next((f["family"] for f in b["fonts"] if "display" in f["role"]), b["fonts"][0]["family"]); body = next((f["family"] for f in b["fonts"] if "body" in f["role"]), b["fonts"][-1]["family"])
    logo = (assets / "logo" / Path(b["logo"]["primary"]).name).resolve().as_uri()
    cover_bg = (b["logo"].get("backgrounds") or [prim])[0]
    cover_fg = light if _lum(cover_bg) < 0.5 else ink
    wm = f'<div class="wm">DRAFT — pending client confirmation</div>' if draft else ""
    sw = "".join(f'<div class="sw"><div class="chip" style="background:{c["hex"]}"></div><b>{esc(c["name"])}</b><code>{c["hex"]}</code><small>{esc(c["role"])}</small><p>{esc(c["usage"])}</p></div>' for c in b["colors"])
    fonts_html = "".join(f'<div class="ft"><div class="sample" style="font-family:\'{f["family"]}\';{'text-transform:uppercase' if 'all caps' in f['role'].lower() else ''}">Aa {esc(b["tagline"])} 0123</div><b>{esc(f["family"])}</b> <span>{esc(f["role"])}</span><small>{esc(f["source"])} · fallback {esc(f["fallback"])}</small></div>' for f in b["fonts"])
    dense = "dense" if (len(b["products"]) > 3 or sum(len(p["facts"]) for p in b["products"]) > 12) else ""
    prods = "".join(f'<div class="pr {dense}" style="border-left:10px solid {p["line_color"]}"><b>{esc(p["name"])}</b><div class="claim" style="font-family:\'{disp}\'">{esc(p["hero_claim"])}</div><ul>' + "".join(f"<li>{esc(x)}</li>" for x in p["facts"][:5]) + "</ul></div>" for p in b["products"][:4])
    tags = "".join(f'<li>{esc(t)}</li>' for t in b["taglines"][:8]); v = b["voice"]
    if len(b["taglines"]) > 8: print(f"note: {len(b['taglines'])} taglines; the Voice page shows the first 8", file=sys.stderr)
    if len(b["products"]) > 4: print(f"note: {len(b['products'])} products; the Products page shows the first 4", file=sys.stderr)
    logos_bg = "".join(f'<div class="lb" style="background:{bg}"><img src="{logo}"></div>' for bg in b["logo"]["backgrounds"])
    src = b["sources"]; conf = f"Confirmed by {esc(src['confirmed_by'])} on {esc(src['confirmed_at'])}." if src.get("confirmed_by") else "Not yet confirmed by the client."
    # optional page: a brand's graphic devices (bursts, bubbles, stickers...) shown as one image with rules
    g = b.get("graphics"); gfx = ""
    if g:
        gimg = (assets / Path(g["image"]).name).resolve().as_uri()
        grules = "".join(f"<li>{esc(r)}</li>" for r in g.get("rules", []))
        gfx = f'<div class="page"><h2><small>04</small>Graphic style</h2><p class="lead">{esc(g["lead"])}</p><img class="gfx" src="{gimg}"><ul class="rules">{grules}</ul><div class="foot">{esc(b["name"])} · Graphic style</div>{wm}</div>'
    n_voice, n_prod = ("05", "06") if g else ("04", "05")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(b['name'])} Brand Kit</title>
<link href="https://fonts.googleapis.com/css2?family={fonts}&display=swap" rel="stylesheet">
<style>
@page{{size:letter;margin:0}} *{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'{body}',Helvetica,Arial,sans-serif;color:{ink};-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{width:8.5in;height:11in;padding:.7in .8in;page-break-after:always;position:relative;overflow:hidden;background:#fff}}
.cover{{background:{cover_bg};color:{cover_fg};display:flex;flex-direction:column;justify-content:space-between}}
.cover img{{width:3.6in}} .cover h1{{font-family:'{disp}',serif;font-size:44pt;font-weight:400;line-height:1.1;max-width:6in}}
.cover .meta{{font-size:10pt;letter-spacing:.15em;text-transform:uppercase;opacity:.85}}
h2{{font-family:'{disp}',serif;font-weight:400;font-size:26pt;margin-bottom:.15in}} h2 small{{display:block;font-family:'{body}';font-size:9pt;letter-spacing:.2em;text-transform:uppercase;color:{sec};margin-bottom:6px}}
.lead{{font-size:11pt;line-height:1.5;max-width:6.4in;margin-bottom:.3in}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:.18in}} .sw .chip{{height:1.1in;border-radius:8px;margin-bottom:6px}}
.sw b{{display:block;font-size:10pt}} .sw code{{display:block;font-size:9pt;color:#666}} .sw small{{display:block;font-size:8pt;letter-spacing:.12em;text-transform:uppercase;color:{sec};margin:2px 0}} .sw p{{font-size:8.5pt;line-height:1.35;color:#555}}
.ft{{padding:.2in 0;border-bottom:1px solid #e5e5e5}} .ft .sample{{font-size:30pt;line-height:1.15;margin-bottom:6px}} .ft b{{font-size:11pt}} .ft span{{font-size:9pt;color:#666;margin-left:8px}} .ft small{{display:block;font-size:8.5pt;color:#888;margin-top:2px}}
.logos{{display:grid;grid-template-columns:repeat(3,1fr);gap:.18in;margin:.2in 0}} .lb{{height:1.7in;border-radius:8px;display:flex;align-items:center;justify-content:center}} .lb img{{width:60%}}
.rules{{font-size:10.5pt;line-height:1.55}} .rules li{{margin-left:1.2em;margin-bottom:4px}}
.pr.dense{{padding:.08in .2in;margin-bottom:.1in}} .pr.dense .claim{{font-size:15pt;margin:2px 0 3px}} .pr.dense ul{{font-size:8.5pt;line-height:1.35}} .pr.dense b{{font-size:10pt}}
.pr{{padding:.15in .25in;margin-bottom:.22in;background:#f6f6f4;border-radius:0 10px 10px 0}} .pr b{{font-size:11pt}} .pr .claim{{font-size:20pt;margin:4px 0 6px}} .pr ul{{font-size:9.5pt;line-height:1.5;margin-left:1.1em}}
.gfx{{width:100%;border:1px solid #eee;border-radius:8px;margin-bottom:.25in}} .voice li{{margin-left:1.2em;font-size:10.5pt;line-height:1.55}} .two{{display:grid;grid-template-columns:1fr 1fr;gap:.3in}}
.tags li{{font-family:'{disp}',serif;font-size:17pt;line-height:1.5;list-style:none;border-bottom:1px solid #eee;padding:4px 0}}
.wm{{position:absolute;right:.5in;top:.4in;font-size:8pt;letter-spacing:.2em;text-transform:uppercase;color:#c0392b;border:1px solid #c0392b;padding:4px 8px;border-radius:4px}}
.page{{padding-bottom:.75in}}
.foot{{position:absolute;left:.8in;bottom:.45in;font-size:8pt;color:#999;letter-spacing:.1em;text-transform:uppercase}}
</style></head><body>
<div class="page cover"><img src="{logo}"><div><h1>{esc(b['tagline'])}</h1><p style="margin-top:.25in;font-size:12pt;max-width:5.5in;line-height:1.5">{esc(b['description'])}</p></div><div class="meta">Brand kit · {esc(b['website'])} · {date.today():%B %Y}</div>{wm}</div>
<div class="page"><h2><small>01</small>Color</h2><p class="lead">{esc(color_lead(b))}</p><div class="grid">{sw}</div><div class="foot">{esc(b['name'])} · Color</div>{wm}</div>
<div class="page"><h2><small>02</small>Typography</h2><p class="lead">{esc(type_lead(b))}</p>{fonts_html}<div class="foot">{esc(b['name'])} · Typography</div>{wm}</div>
<div class="page"><h2><small>03</small>Logo</h2><p class="lead">{esc(b['logo']['description'])}</p><div class="logos">{logos_bg}</div><ul class="rules"><li>Clear space: {esc(b['logo']['clear_space'])}.</li><li>Minimum width: {b['logo']['min_width_px']} px on screen.</li><li>Do not recolor, stretch, outline, or add effects to the {'wordmark' if _has_wordmark(b) else 'logo'}.</li><li>On photography, place the logo on a color panel or in a corner over a calm area.</li></ul><div class="foot">{esc(b['name'])} · Logo</div>{wm}</div>
{gfx}
<div class="page"><h2><small>{n_voice}</small>Voice</h2><div class="two"><div><p class="lead"><b>Tone:</b> {esc(', '.join(v['tone']))}.<br><br>{esc(v['style'])}</p><ul class="voice"><li><b>Use:</b> {esc(', '.join(v['words_use']))}</li><li><b>Avoid:</b> {esc(', '.join(v['words_avoid']))}</li></ul></div><div><p class="lead" style="margin-bottom:.1in"><b>Headline bank</b></p><ul class="tags">{tags}</ul></div></div><div class="foot">{esc(b['name'])} · Voice</div>{wm}</div>
<div class="page"><h2><small>{n_prod}</small>Products</h2>{prods}<p class="lead" style="margin-top:.2in;font-size:9pt;color:#777">Source: extracted from {esc(src['extracted_from'])} on {esc(src['extracted_at'])}{' with client-supplied material' if src.get('client_supplied') else ''}. {conf}<br>{esc(src.get('extraction_notes',''))}</p><div class="foot">{esc(b['name'])} · Products & sources</div>{wm}</div>
</body></html>"""

def _resolve(b: dict, base: Path) -> None:
    """Logo paths in brand.json may be relative to the brand file, so example brands ship with the repo."""
    fix = lambda p: str(Path(p).expanduser() if Path(p).expanduser().is_absolute() else (base / p).resolve())
    b["logo"]["primary"] = fix(b["logo"]["primary"]); b["logo"]["variants"] = [fix(v) for v in b["logo"].get("variants", [])]
    if b.get("graphics"): b["graphics"]["image"] = fix(b["graphics"]["image"])


def build(brand_file: Path, out: Path):
    b = json.loads(brand_file.read_text()); _resolve(b, brand_file.parent); assets = out / "brand-assets"; (assets / "logo").mkdir(parents=True, exist_ok=True)
    for lg in [b["logo"]["primary"], *b["logo"].get("variants", [])]:
        if Path(lg).exists(): shutil.copy2(lg, assets / "logo" / Path(lg).name)
    if b.get("graphics") and Path(b["graphics"]["image"]).exists(): shutil.copy2(b["graphics"]["image"], assets / Path(b["graphics"]["image"]).name)
    palette_png(b["colors"], assets / "palette.png")
    # round avatar for social/profile circles: logo on the primary color (and on the secondary, for the other line)
    prim = next(c["hex"] for c in b["colors"] if c["role"] == "primary"); sec = next((c["hex"] for c in b["colors"] if c["role"] == "secondary"), prim)
    # use backgrounds the logo is documented to work on; a blue logo on a blue primary disappears
    safe = b["logo"].get("backgrounds") or []
    make_avatar(Path(b["logo"]["primary"]), assets / "logo" / "avatar.png", bg=safe[0] if safe else prim)
    make_avatar(Path(b["logo"]["primary"]), assets / "logo" / "avatar-secondary.png", bg=safe[1] if len(safe) > 1 else sec)
    (assets / "brand.json").write_text(json.dumps(b, indent=2)); (assets / "tokens.json").write_text(json.dumps(tokens_from(b), indent=2)); (assets / "brand.md").write_text(brand_md(b))
    draft = not b["sources"].get("confirmed_by")
    html_path = assets / "kit.html"; html_path.write_text(kit_html(b, assets, draft), encoding="utf-8")
    pdf = out / f"{b['name']} Brand Kit{' (DRAFT)' if draft else ''}.pdf"
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(); pg.goto(html_path.resolve().as_uri(), wait_until="networkidle"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
        pg.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True); br.close()
    return pdf, assets

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brand", type=Path); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv); pdf, assets = build(a.brand, a.out); print(pdf); print(assets)

if __name__ == "__main__": sys.exit(main())
