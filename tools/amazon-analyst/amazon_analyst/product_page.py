"""
Optional product-page reader (Playwright Firefox) for listing detail when no
Selling Partner API credentials are configured: title, brand, bullet points,
Best Sellers Rank, rating, review count, price.

Prefer catalog.py (official API, no page loads). This exists so the tool still
works for someone with no seller account, at a deliberately slow pace: one
page every few seconds, a hard cap per run, and an immediate stop on any
captcha. Research use only.
"""
from __future__ import annotations

import random
import re
import time

from . import config
from .search_scraper import classify_block, parse_count, parse_price, parse_rating

MAX_PAGES_PER_RUN = 25
PAGE_JITTER_MS = (5000, 10000)
_BSR_RE = re.compile(r"#\s?([\d,]+)\s+in\s+([^()\n]+?)(?:\s*\(|$)")


def parse_product_page(html: str) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    out: dict = {"catalog_title": "", "brand_name": "", "bullets": [], "bsr_category": "", "bsr_rank": None,
                 "bsr_ranks": [], "rating": None, "review_count": None, "price": None}
    t = soup.select_one("#productTitle")
    out["catalog_title"] = t.get_text(strip=True)[:512] if t else ""
    b = soup.select_one("#bylineInfo")
    if b:
        out["brand_name"] = re.sub(r"^(visit the|brand:)\s*", "", b.get_text(strip=True), flags=re.I).replace(" Store", "").strip()[:255]
    out["bullets"] = [li.get_text(" ", strip=True) for li in soup.select("#feature-bullets li span.a-list-item") if li.get_text(strip=True)][:10]
    ranks_text = " ".join(el.get_text(" ", strip=True) for el in soup.select("#detailBulletsWrapper_feature_div, #productDetails_detailBullets_sections1, #prodDetails") if el)
    for m in _BSR_RE.finditer(ranks_text):
        try:
            out["bsr_ranks"].append({"rank": int(m.group(1).replace(",", "")), "category": m.group(2).strip()[:120]})
        except ValueError:
            continue
    if out["bsr_ranks"]:
        out["bsr_category"], out["bsr_rank"] = out["bsr_ranks"][0]["category"], out["bsr_ranks"][0]["rank"]
    r = soup.select_one("#acrPopover")
    out["rating"] = parse_rating(r.get("title") or "") if r else None
    rc = soup.select_one("#acrCustomerReviewText")
    out["review_count"] = parse_count(rc.get_text(strip=True)) if rc else None
    p = soup.select_one("#corePrice_feature_div .a-offscreen, #apex_desktop .a-offscreen, .a-price .a-offscreen")
    out["price"] = parse_price(p.get_text(strip=True)) if p else None
    return out


def fetch_product_pages(asins: list[str], *, marketplace: str = "US", log=None) -> dict[str, dict]:
    """{asin: parsed fields | {"error": ...}}; stops on the first captcha."""
    from playwright.sync_api import sync_playwright

    mp = config.marketplace(marketplace)
    say = log or (lambda m: None)
    out: dict[str, dict] = {}
    asins = [a.upper() for a in asins][:MAX_PAGES_PER_RUN]
    with sync_playwright() as pw:
        browser = pw.firefox.launch(headless=True)
        context = browser.new_context(locale=mp["locale"], viewport={"width": 1366, "height": 768},
                                      extra_http_headers={"Accept-Language": mp["lang"]})
        page = context.new_page()
        try:
            for i, asin in enumerate(asins):
                try:
                    page.goto(f"https://www.{mp['domain']}/dp/{asin}", wait_until="domcontentloaded", timeout=45_000)
                    page.wait_for_timeout(1500)
                    html = page.content()
                except Exception as exc:  # noqa: BLE001
                    out[asin] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
                    continue
                block = classify_block(html)
                if block == "captcha":
                    say(f"  robot check on {asin} — stopping product-page reads")
                    out[asin] = {"error": "captcha"}
                    break
                out[asin] = parse_product_page(html) if block == "" else {"error": "error_page"}
                say(f"  {asin}: {'ok' if 'error' not in out[asin] else out[asin]['error']}")
                if i < len(asins) - 1:
                    time.sleep(random.randint(*PAGE_JITTER_MS) / 1000)
        finally:
            context.close()
            browser.close()
    return out
