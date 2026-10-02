#!/usr/bin/env python
"""
build_email.py — Build an email as stackable HTML snippets from a JSON spec.

    PY=../../.venv/bin/python            # any Python with playwright + pillow
    $PY emails/build_email.py spec.json                      # sections/, email.html, previews/, report.md
    $PY emails/build_email.py spec.json --base-url https://cdn.example.com/email/2026-10/   # hosted image URLs
    $PY emails/build_email.py spec.json --lite               # always write email-lite.html (≤ 102 KB)
    $PY emails/build_email.py spec.json --no-preview         # skip screenshots
    $PY emails/build_email.py spec.json --profile light      # smaller images (~400 KB budget) vs rich (default)

What comes out (in the spec's "out" folder, or --out):
    sections/NN-type.html   one snippet per section: a single <div>…</div>, inline CSS, no html/head/body
    email.html              all snippets stacked, in order. Still no html/head/body: paste into the ESP
    email-lite.html         written when email.html is over the Gmail clip limit (or with --lite):
                            minified, and if still too big the heaviest text sections become images
    images/                 every image the email needs (resized to 2x the email width); host these
    previews/               desktop.png, mobile.png and _preview.html (a wrapper for looking only, never delivered)
    report.md               bytes per section, total vs the 102 KB limit, lint results, images to host
    handoff.md              assembly guide for a human in the ESP editor: image rows → native image blocks
                            (which file, link, alt), everything else → custom HTML block with the snippet inline

Spec (paths are relative to the spec file):
{
  "brand": "northpeak",                     // brand-guidelines/brands/<slug>/tokens.json, OR
  "brand_tokens": "../branding/brand-assets/tokens.json",   // a tokens file next to the spec (portable folders)
  "out": "out/email/launch",
  "theme": {"width": 600, "headline_fallback": "serif", "btn_bg": "#0F6E6E"},
  "base_url": "",                           // or pass --base-url later, once images are hosted
  "sections": [
    {"type": "header", "logo": "../brand-guidelines/brands/northpeak/assets/logo.png", "href": "https://…"},
    {"type": "graphic", "name": "hero", "template": "../templates/email-hero.html", "data": {...}, "alt": "…", "href": "…"},
    {"type": "hero_text", "eyebrow": "New", "headline": "…", "body": "…", "button": {"text": "Shop now", "href": "https://…"}},
    {"type": "columns", "items": [{"image": "…", "title": "…", "text": "…", "href": "…", "link_text": "Shop"}]},
    {"type": "footer", "lines": ["Northpeak · 123 Trail Rd", "{% unsubscribe %}"]}
  ]
}
Any section may carry "editor": "preset" to say the ESP's built-in block (footer, social icons, button)
  should be used instead of the snippet; the handoff guide then lists it that way.
Section types: header, image, graphic, hero_text, text, button, columns, quote, divider, spacer, footer, raw,
  offer (copy + code chip + button), compare (us-vs-them rows), tiles (fixed 2-up image grid), social (text links).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402
import sections as S   # noqa: E402

GMAIL_CLIP = 102 * 1024          # Gmail clips the message above ~102 KB of HTML
TARGET = 98 * 1024               # leave room for what the ESP adds (tracking, wrappers, footer)
IMG_KEYS = ("src", "logo", "image")


# ------------------------------------------------------------------ lint
def lint(snippet: str) -> list[str]:
    issues = []; low = snippet.lower().strip()
    if not low.startswith("<div"): issues.append("ERROR does not start with <div")
    if not low.endswith("</div>"): issues.append("ERROR does not end with </div>")
    for tag in ("<html", "<body", "<head", "<style", "<script", "<link", "<!doctype"):
        if tag in low: issues.append(f"ERROR contains {tag}")
    if low.count("<div") != low.count("</div>"): issues.append("ERROR unbalanced <div> tags")
    for m in re.finditer(r"<img\b[^>]*>", snippet, re.I):
        tag = m.group(0)
        if not re.search(r'\balt="', tag): issues.append("ERROR <img> without alt")
        if 'src="data:' in tag: issues.append("ERROR image embedded as data: URI (host it instead)")
        if not re.search(r'\bwidth="', tag): issues.append("WARN <img> without width attribute (Outlook needs it)")
    for m in re.finditer(r'href="([^"]*)"', snippet):
        h = m.group(1)
        if not re.match(r"(https?://|mailto:|tel:|\{\{|\{%|#$)", h): issues.append(f"WARN relative or empty link: {h[:60]!r}")
    if re.search(r'\sclass="', snippet): issues.append("WARN class attribute has no effect without <style>")
    return issues


# ------------------------------------------------------------------ helpers
def minify(html: str) -> str:
    html = re.sub(r"<!--(?!\[if)(?!<!\[endif).*?-->", "", html, flags=re.S)   # keep MSO conditionals
    html = re.sub(r">\s+<", "><", html)
    return re.sub(r"[ \t]{2,}", " ", html).strip()


def text_of(snippet: str, limit: int = 400) -> str:
    t = re.sub(r"<!--.*?-->", " ", snippet, flags=re.S); t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&[a-z]+;", " ", t); t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def prepare_image(src: str, base: Path, images: Path, max_px: int, log: list) -> str:
    """Copy a local image into images/ (downscaled to 2x email width) and return its relative src."""
    if src.startswith(("http://", "https://", "{{", "{%")):
        return src
    p = Path(src).expanduser(); p = p if p.is_absolute() else (base / p)
    if not p.exists():
        raise SystemExit(f"Image not found: {src} (resolved to {p})")
    images.mkdir(parents=True, exist_ok=True)
    im = Image.open(p); has_alpha = im.mode in ("RGBA", "LA", "P") and "A" in im.convert("RGBA").getbands() and im.convert("RGBA").getchannel("A").getextrema()[0] < 255
    ext = ".png" if has_alpha else ".jpg"; name = re.sub(r"[^a-z0-9._-]+", "-", p.stem.lower()).strip("-") + ext; dest = images / name
    if im.width > max_px:
        im = im.resize((max_px, round(im.height * max_px / im.width)), Image.LANCZOS)
    if has_alpha: im.convert("RGBA").save(dest, optimize=True)
    else: im.convert("RGB").save(dest, quality=86, optimize=True, progressive=True)
    log.append((name, im.size, dest.stat().st_size))
    return f"images/{name}"


def shoot(page, html_path: Path, locator: str, out: Path, quality: int = 82):
    page.goto(html_path.resolve().as_uri(), wait_until="load"); page.wait_for_timeout(200)
    page.locator(locator).first.screenshot(path=str(out), type="jpeg", quality=quality)


# ------------------------------------------------------------------ build
def build(spec_path: Path, out: Path | None, base_url: str | None, force_lite: bool, preview: bool, profile: str | None = None) -> dict:
    spec = json.loads(spec_path.read_text()); base = spec_path.resolve().parent
    profile = profile or spec.get("profile") or "rich"
    out = (out or (base / spec.get("out", "out/email"))).resolve(); images = out / "images"; (out / "sections").mkdir(parents=True, exist_ok=True)
    tokens = {}
    if spec.get("brand_tokens"):                       # self-contained specs: tokens file next to the spec
        tf = (base / spec["brand_tokens"]).resolve()
        if not tf.exists(): raise SystemExit(f"brand_tokens not found: {tf}")
        tokens = json.loads(tf.read_text())
        for k in ("logo", "logo_dark", "avatar", "elements"):   # relative paths in a tokens file resolve against it
            v = tokens.get(k)
            if isinstance(v, str) and v and not v.startswith(("http://", "https://")) and not Path(v).is_absolute():
                tokens[k] = str((tf.parent / v).resolve())
    elif spec.get("brand"):
        tf = ROOT / "brand-guidelines" / "brands" / spec["brand"] / "tokens.json"
        if not tf.exists(): raise SystemExit(f"no brand '{spec['brand']}': expected {tf}")
        tokens = json.loads(tf.read_text())
    t = S.Theme.from_tokens(tokens, spec.get("theme")); max_px = t.width * 2
    base_url = (base_url if base_url is not None else spec.get("base_url") or "").strip()
    img_log: list = []; built = []   # (name, type, snippet)

    for i, sec in enumerate(spec["sections"], start=1):
        sec = json.loads(json.dumps(sec)); typ = sec["type"]; name = sec.get("name", typ)
        if typ == "graphic":
            import render as R
            data = dict(sec.get("data") or {})
            if sec.get("data_file"): data = {**json.loads((base / sec["data_file"]).read_text()), **data}
            missing: list = []; R.resolve_paths(data, base, missing)
            if tokens: data["brand"] = {**tokens, **data.get("brand", {})}
            data.setdefault("email", {"width": t.width})
            # data strings may themselves use {{ brand.* }} (e.g. an <img> inside a headline): expand them first
            data = json.loads(R.fill(json.dumps(data), data))
            images.mkdir(parents=True, exist_ok=True); dest = images / f"{i:02d}-{name}.jpg"
            tpl = Path(sec["template"]); tpl = tpl if tpl.is_absolute() else (base / tpl)
            R.render(tpl, dest, data, width=sec.get("width", t.width), height=sec.get("height"), scale=2, quality=sec.get("quality", 84))
            dest.with_suffix(".html").unlink(missing_ok=True)
            with Image.open(dest) as im: img_log.append((dest.name, im.size, dest.stat().st_size))
            sec = {"type": "image", "src": f"images/{dest.name}", "alt": sec.get("alt", ""), "href": sec.get("href")}; typ = "image"
        else:
            for k in IMG_KEYS:
                if isinstance(sec.get(k), str):
                    limit = int(sec.get("logo_width", 160)) * 2 if k == "logo" else max_px
                    sec[k] = prepare_image(sec[k], base, images, limit, img_log)
            for k in ("yes_icon", "no_icon"):
                if isinstance(sec.get(k), str) and not sec[k].startswith("text:"): sec[k] = prepare_image(sec[k], base, images, 80, img_log)
            n_cols = int(sec.get("cols", min(len(sec.get("items", [])) or 1, 3)))
            for it in sec.get("items", []):
                if isinstance(it.get("image"), str):
                    per = 2 * t.width // n_cols if typ == "tiles" else 2 * (t.width - 2 * t.pad_x) // n_cols
                    it["image"] = prepare_image(it["image"], base, images, max(per, 200), img_log)
        if typ not in S.BUILDERS: raise SystemExit(f"unknown section type: {typ}")
        built.append((f"{i:02d}-{name}", typ, S.BUILDERS[typ](t, sec)))

    def final(snippet: str) -> str:
        return snippet.replace('src="images/', f'src="{base_url.rstrip("/")}/') if base_url else snippet

    # ---- write sections + full email
    issues = {}
    for f in (out / "sections").glob("*.html"): f.unlink()
    for name, typ, snip in built:
        (out / "sections" / f"{name}.html").write_text(final(snip) + "\n", encoding="utf-8")
        li = lint(final(snip))
        if li: issues[name] = li
    email = "\n".join(final(s) for _, _, s in built); (out / "email.html").write_text(email + "\n", encoding="utf-8")
    size = len(email.encode("utf-8")); sizes = [(n, ty, len(final(s).encode("utf-8"))) for n, ty, s in built]

    # ---- lite build: minify, then rasterize the heaviest live-text sections until under the target
    lite_info = None; lite_built = [(n, ty, minify(s)) for n, ty, s in built]
    lite_size = lambda: len("\n".join(final(s) for _, _, s in lite_built).encode("utf-8"))
    need_browser = preview or (lite_size() > TARGET)
    pw = browser = page = None
    if need_browser:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start(); browser = pw.chromium.launch(); page = browser.new_page(viewport={"width": t.width, "height": 900}, device_scale_factor=2)
    if size > TARGET or force_lite:
        rasterized = []
        while lite_size() > TARGET:
            cands = [(len(s), k) for k, (n, ty, s) in enumerate(lite_built) if ty not in S.KEEP_LIVE]
            if not cands: break
            _, k = max(cands); n, ty, s = lite_built[k]
            tmp = out / ".__raster.html"; tmp.write_text(f'<!doctype html><html><body style="margin:0;"><div id="cap" style="width:{t.width}px;">{s}</div></body></html>', encoding="utf-8")
            images.mkdir(parents=True, exist_ok=True); dest = images / f"{n}-lite.jpg"; shoot(page, tmp, "#cap", dest); tmp.unlink(missing_ok=True)
            with Image.open(dest) as im: img_log.append((dest.name, im.size, dest.stat().st_size))
            href = re.search(r'href="(https?://[^"]+)"', s)
            lite_built[k] = (n, "image", S.image(t, {"src": f"images/{dest.name}", "alt": text_of(s), "href": href.group(1) if href else None})); rasterized.append(n)
        lite = "\n".join(final(s) for _, _, s in lite_built); (out / "email-lite.html").write_text(lite + "\n", encoding="utf-8")
        lite_info = {"bytes": len(lite.encode("utf-8")), "rasterized": rasterized}
        for n, ty, s in lite_built:
            li = lint(final(s))
            if li: issues[f"{n} (lite)"] = li

    # ---- previews (wrapper is for looking only; it is never a deliverable)
    if preview:
        prev = out / "previews"; prev.mkdir(exist_ok=True)
        local = "\n".join(s for _, _, s in built)
        (prev / "_preview.html").write_text('<!doctype html><html><head><meta charset="utf-8"><base href="../"><meta name="viewport" content="width=device-width,initial-scale=1"></head>'
                                            f'<body style="margin:0;padding:24px 0;background:#e9e9e9;">{local}</body></html>', encoding="utf-8")
        for label, w in (("desktop", 700), ("mobile", 390)):
            pg = browser.new_page(viewport={"width": w, "height": 900}, device_scale_factor=2 if label == "mobile" else 1.5)
            pg.goto((prev / "_preview.html").resolve().as_uri(), wait_until="load"); pg.wait_for_timeout(300)
            pg.screenshot(path=str(prev / f"{label}.png"), full_page=True); pg.close()
    if browser: browser.close(); pw.stop()

    # ---- compress images (rich: invisible loss; light: smaller and softer) and measure weight
    import compress as C
    prof = C.PROFILES[profile]; img_log = []
    for f in sorted(images.glob("*")):
        if f.suffix.lower() not in (".jpg", ".jpeg", ".png"): continue
        before, after, how = C.compress_image(f, f, prof["max_width"], prof["max_error"], prof["min_q"])
        newf = f.with_suffix(".jpg") if how.startswith("jpeg") else f.with_suffix(".png")
        if newf.name != f.name:   # extension changed: fix every snippet that references it
            built = [(n, ty, sn.replace(f"images/{f.name}", f"images/{newf.name}")) for n, ty, sn in built]
            lite_built = [(n, ty, sn.replace(f"images/{f.name}", f"images/{newf.name}")) for n, ty, sn in lite_built]
        with Image.open(newf) as im: img_log.append((newf.name, im.size, after, before, how))
    for name, typ, snip in built: (out / "sections" / f"{name}.html").write_text(final(snip) + "\n", encoding="utf-8")
    email = "\n".join(final(s) for _, _, s in built); (out / "email.html").write_text(email + "\n", encoding="utf-8"); size = len(email.encode("utf-8"))
    if (out / "email-lite.html").exists():
        lite = "\n".join(final(s) for _, _, s in lite_built); (out / "email-lite.html").write_text(lite + "\n", encoding="utf-8")
    used = set(re.findall(r'images/([^"\s]+)', email)); img_total = sum(b for n, _, b, _, _ in img_log if n in used)
    weight = size + img_total

    # ---- handoff guide: which sections are native editor blocks (images) and which are custom HTML
    NATIVE = {"image", "header", "tiles", "spacer", "divider"}
    guide = [f"# Assembling this email in your editor", "",
             "Work top to bottom. **Image** rows: use the editor's own image / multi-image block and drop in the file from `images/`",
             "(set the link and alt text shown). **Custom HTML** rows: add a custom HTML / code block and paste the snippet",
             "(each is one `<div>` with inline CSS; no `<html>`/`<body>`). Image URLs inside snippets point at `images/…`",
             "until you rebuild with `--base-url` or replace them with the editor's hosted URLs.", ""]
    for (name, typ, snip), sec in zip(built, spec["sections"]):
        imgs = re.findall(r'<img src="([^"]+)"[^>]*alt="([^"]*)"', final(snip)); links = re.findall(r'href="([^"]+)"', final(snip))
        all_images = typ in NATIVE or (typ == "columns" and sec.get("items") and all(it.get("image") and not (it.get("title") or it.get("text")) for it in sec["items"]))
        if all_images and imgs:
            n = len(imgs); block = {1: "Image block", 2: "2-image row", 3: "3-image row", 4: "2x2 image grid (or two 2-image rows)"}.get(n, f"{n}-image layout")
            guide.append(f"## {name} — {block} (editor block)")
            for (src, alt), href in zip(imgs, links + [None] * n):
                guide.append(f"- `{src.split('/')[-1]}`" + (f" → link `{href}`" if href else "") + (f" · alt: {alt}" if alt else ""))
            if typ == "header": guide.append("- Center it; keep the logo about " + str(sec.get("logo_width", 160)) + " px wide.")
        elif sec.get("editor") == "preset":
            guide.append(f"## {name} — use the editor's built-in {typ} block")
            hint = {"footer": "address + unsubscribe come from the editor; match the colors in the snippet",
                    "social": "editor's social-icons block with these links",
                    "button": "editor's button block: ALL CAPS label, blue #0B73CB, white text, rounded 6 px"}.get(typ, "")
            if hint: guide.append(f"- {hint}")
            for href in links: guide.append(f"- link: `{href}`")
            guide.append(f"- (custom-HTML fallback: `sections/{name}.html`)")
        elif typ in ("spacer", "divider"):
            guide.append(f"## {name} — {typ} (editor block or skip)")
        else:
            guide.append(f"## {name} — Custom HTML block (paste `sections/{name}.html`)")
            guide.append("```html"); guide.append(final(snip)); guide.append("```")
        guide.append("")
    (out / "handoff.md").write_text("\n".join(guide) + "\n", encoding="utf-8")

    # ---- report
    kb = lambda b: f"{b / 1024:.1f} KB"
    L = [f"# Email build report — {spec_path.name}", "", f"- Sections: {len(built)}", f"- **email.html: {kb(size)}** ({size / GMAIL_CLIP:.0%} of Gmail's 102 KB clip limit; build target {kb(TARGET)})"]
    if lite_info: L.append(f"- **email-lite.html: {kb(lite_info['bytes'])}**" + (f" — rasterized to images: {', '.join(lite_info['rasterized'])}" if lite_info["rasterized"] else " — minified only"))
    L += [f"- Image URLs: {'hosted at ' + base_url if base_url else 'RELATIVE (`images/…`). Upload the images folder, then rebuild with --base-url <folder URL>'}", "",
          "| Section | Type | Size |", "|---|---|---|"] + [f"| {n} | {ty} | {kb(b)} |" for n, ty, b in sizes]
    verdict = ("lightweight" if weight < 500 * 1024 else "typical marketing email" if weight < 1200 * 1024 else "heavy: expect a visible wait on mobile data and more image-off views" if weight < 2500 * 1024 else "very heavy: trim images or go light")
    L += ["", "## Weight", f"- **Total download: {kb(weight)}** = HTML {kb(size)} + images {kb(img_total)} ({len(used)} images actually used). Profile: **{profile}**.",
          f"- Verdict: {verdict}. Benchmarks: a plain-text email is ~10 KB; a typical marketing email with 4–8 images is 500 KB–1.2 MB; over ~2 MB loads noticeably slowly on mobile and some clients stop fetching images.",
          f"- HTML vs Gmail's 102 KB clip: {size / GMAIL_CLIP:.0%}. Images never count toward the clip; they only affect load time.",
          f"- Images were recompressed with `compress.py` ({'invisible loss' if profile == 'rich' else 'light: smaller, slightly softer'}): {kb(sum(b for *_, b, _ in [(n,s_,a,b,h) for n,s_,a,b,h in img_log]))} → {kb(sum(a for _, _, a, _, _ in img_log))}. Rebuild with `--profile light` for a lighter email or `--profile rich` for best quality."]
    L += ["", "## Images to host", "| File | Pixels | Size | Before | How |", "|---|---|---|---|---|"] + [f"| {n} | {w}x{h} | {kb(a)} | {kb(b)} | {how} |" for n, (w, h), a, b, how in img_log]
    L += ["", "## Lint"] + ([f"- **{n}**: " + "; ".join(v) for n, v in issues.items()] or ["- clean: every section is a single `<div>` with inline CSS, no html/head/body/style/script"])
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    errors = [i for v in issues.values() for i in v if i.startswith("ERROR")]
    return {"out": str(out), "bytes": size, "images_bytes": img_total, "weight_bytes": weight, "profile": profile, "lite": lite_info, "sections": len(built), "errors": errors, "warnings": sum(len(v) for v in issues.values()) - len(errors)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path); ap.add_argument("--out", type=Path); ap.add_argument("--base-url")
    ap.add_argument("--lite", action="store_true"); ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--profile", choices=("rich", "light"), help="image weight: rich (default, ~1 MB budget) or light (~400 KB, smaller/softer images)")
    a = ap.parse_args(argv)
    r = build(a.spec, a.out, a.base_url, a.lite, not a.no_preview, a.profile)
    print(json.dumps(r, indent=2))
    return 1 if r["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
