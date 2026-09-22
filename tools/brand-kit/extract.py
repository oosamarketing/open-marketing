#!/usr/bin/env python
"""
extract.py — Pull a first-pass brand kit from a website with Playwright (Chromium).

    python extract.py https://example.com --out ./work/example

Writes <out>/extract.json with: title, meta description, og image, headings, candidate
taglines (short prominent strings), logo candidates (img/svg in header/nav, favicon, og:image),
fonts actually used (computed font-family of headings/body/buttons), colors actually used
(computed background/text/button colors weighted by on-screen area), and page text for tone.
Downloads logo candidates and screenshots the home page into <out>/raw/.
This is a DRAFT for a human to confirm — see brand-kit README.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

JS = r"""
() => {
  const out = {};
  const txt = (el) => (el && el.innerText || "").trim();
  out.title = document.title;
  const md = document.querySelector('meta[name="description"]'); out.description = md ? md.content : "";
  const og = document.querySelector('meta[property="og:image"]'); out.og_image = og ? og.content : "";
  const ic = document.querySelector('link[rel*="icon"]'); out.favicon = ic ? ic.href : "";
  out.headings = [...document.querySelectorAll('h1,h2,h3')].map(h => ({tag:h.tagName, text:txt(h)})).filter(h=>h.text && h.text.length<140).slice(0,60);
  // logo candidates: images/svgs inside header/nav or with logo in attrs
  const logoSel = 'header img, nav img, header svg, nav svg, [class*="logo"] img, [class*="logo"] svg, img[alt*="logo" i], img[src*="logo" i], a[href="/"] img';
  const seen = new Set(); out.logos = [];
  document.querySelectorAll(logoSel).forEach(el => {
    const r = el.getBoundingClientRect(); if (r.width < 20) return;
    if (el.tagName === 'svg' && r.width <= 40 && r.height <= 40) return;   // cart/search/account icons
    const src = el.tagName === 'IMG' ? (el.currentSrc || el.src) : null;
    const key = src || el.outerHTML.slice(0,200); if (seen.has(key)) return; seen.add(key);
    out.logos.push({tag: el.tagName, src, alt: el.alt || "", w: Math.round(r.width), h: Math.round(r.height), svg: el.tagName === 'svg' ? el.outerHTML : null});
  });
  // colors weighted by area (backgrounds), plus text and button colors
  const bg = new Map(), fg = new Map(), btn = new Map(), fonts = new Map();
  const add = (m,k,v) => m.set(k, (m.get(k)||0)+v);
  const vis = (el) => { const r = el.getBoundingClientRect(); return r.width>0 && r.height>0 && r.bottom>0 && r.top<document.documentElement.scrollHeight; };
  document.querySelectorAll('body *').forEach(el => {
    if (!vis(el)) return; const cs = getComputedStyle(el); const r = el.getBoundingClientRect(); const area = Math.min(r.width*r.height, 1e6);
    if (cs.backgroundColor && !cs.backgroundColor.startsWith('rgba(0, 0, 0, 0)')) add(bg, cs.backgroundColor, area);
    if (el.innerText && el.children.length === 0 && el.innerText.trim()) { add(fg, cs.color, el.innerText.length); add(fonts, cs.fontFamily.split(',')[0].replace(/["']/g,'').trim(), el.innerText.length); }
    if (el.matches('button, a.btn, a[class*="button" i], [class*="btn" i], input[type=submit]')) { add(btn, cs.backgroundColor + ' / ' + cs.color, 1); }
  });
  const top = (m, n) => [...m.entries()].sort((a,b)=>b[1]-a[1]).slice(0,n);
  out.bg_colors = top(bg, 12); out.text_colors = top(fg, 8); out.buttons = top(btn, 6); out.fonts = top(fonts, 6);
  out.heading_fonts = [...new Set([...document.querySelectorAll('h1,h2')].map(h => getComputedStyle(h).fontFamily.split(',')[0].replace(/["']/g,'').trim()))];
  // short prominent lines for tagline candidates
  const cands = [];
  document.querySelectorAll('h1,h2,p,span,li').forEach(el => { const t = txt(el); if (t && t.length>=8 && t.length<=70 && el.children.length===0) { const fs = parseFloat(getComputedStyle(el).fontSize); if (fs>=18) cands.push({text:t, size:fs}); } });
  out.taglines = [...new Map(cands.map(c=>[c.text,c])).values()].sort((a,b)=>b.size-a.size).slice(0,25);
  out.body_text = document.body.innerText.slice(0, 6000);
  out.nav = [...document.querySelectorAll('nav a, header a')].map(a=>txt(a)).filter(t=>t && t.length<30).slice(0,30);
  return out;
}
"""

def rgb_to_hex(s: str) -> str | None:
    m = re.findall(r"[\d.]+", s)
    if len(m) < 3: return None
    if len(m) == 4 and float(m[3]) == 0: return None
    return "#%02x%02x%02x" % tuple(int(float(v)) for v in m[:3])

def extract(url: str, out: Path) -> dict:
    raw = out / "raw"; raw.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
        # Shopify/analytics-heavy sites never reach networkidle; wait for load, then settle briefly
        try:
            pg.goto(url, wait_until="networkidle", timeout=20000)
        except Exception:
            pg.goto(url, wait_until="load", timeout=60000)
        pg.wait_for_timeout(2500)
        # dismiss common popups (cookie/newsletter) so screenshots are clean
        for sel in ["button[aria-label*='close' i]", "[class*='close' i] button", "button:has-text('No thanks')", "button:has-text('Close')"]:
            try:
                loc = pg.locator(sel).first
                if loc.count() and loc.is_visible(): loc.click(timeout=1000); pg.wait_for_timeout(400)
            except Exception: pass
        data = pg.evaluate(JS); data["url"] = pg.url
        pg.screenshot(path=str(raw / "home-fold.png"))
        pg.screenshot(path=str(raw / "home-full.png"), full_page=True)
        # download logo candidates via the page session
        for i, lg in enumerate(data["logos"]):
            try:
                if lg.get("svg"):
                    (raw / f"logo-{i}.svg").write_text(lg["svg"], encoding="utf-8"); lg["file"] = f"raw/logo-{i}.svg"
                elif lg.get("src"):
                    # header images are served resized (Shopify ?width=80, Squarespace ?format=300w …): fetch the original
                    src = re.sub(r"([?&])(width|w|h|height|format|size)=[^&]*&?", r"\1", urljoin(pg.url, lg["src"])).rstrip("?&")
                    src = re.sub(r"_(\d{2,4}x\d{0,4}|\d{2,4}x)(?=\.[a-z]+($|\?))", "", src)   # Shopify _480x480 suffix
                    r = pg.request.get(src)
                    if r.status != 200:
                        src = urljoin(pg.url, lg["src"]); r = pg.request.get(src)
                    ext = ".svg" if "svg" in r.headers.get("content-type", "") or src.endswith(".svg") else (".png" if "png" in r.headers.get("content-type","") else ".jpg")
                    (raw / f"logo-{i}{ext}").write_bytes(r.body()); lg["file"] = f"raw/logo-{i}{ext}"; lg["src"] = src
            except Exception as e:
                lg["error"] = str(e)[:100]
        for key in ("og_image", "favicon"):
            if data.get(key):
                try:
                    src = urljoin(pg.url, data[key]); r = pg.request.get(src); ext = Path(src.split("?")[0]).suffix or ".png"
                    (raw / f"{key}{ext}").write_bytes(r.body()); data[key + "_file"] = f"raw/{key}{ext}"
                except Exception: pass
        b.close()
    for k in ("bg_colors", "text_colors"):
        data[k] = [(rgb_to_hex(c), round(w)) for c, w in data[k] if rgb_to_hex(c)]
    data["buttons"] = [(" / ".join(rgb_to_hex(x) or x for x in c.split(" / ")), n) for c, n in data["buttons"]]
    (out / "extract.json").write_text(json.dumps(data, indent=2))
    return data

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url"); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv); d = extract(a.url, a.out)
    print(json.dumps({k: d[k] for k in ("title","description","bg_colors","text_colors","buttons","fonts","heading_fonts","taglines","nav","logos")}, indent=1)[:6000])

if __name__ == "__main__": sys.exit(main())
