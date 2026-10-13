"""
Amazon search-result pages → product cards, with Playwright Firefox.

RESEARCH USE ONLY. Amazon's Conditions of Use prohibit automated data
collection; this module exists to look at a handful of result pages the way a
person would, not to harvest the catalog. Guardrails are deliberate:
  - at most HARD_MAX_PAGES pages per run, randomized waits between pages
  - a storefront warm-up before the first search (cold deep-links get the
    generic error page) and a single retry on that error page
  - captcha / robot-check pages abort the run and are dumped for inspection.
    Nothing here solves or bypasses a captcha, ever.
  - product pages are NOT scraped here; listing detail comes from the
    Selling Partner API (catalog.py) or, optionally, product_page.py.

What each card yields: asin, position, sponsored flag, title, price, rating,
review count, Amazon's bucketed "N+ bought in past month" badge (stored as an
integer floor), badge (Amazon's Choice / Best Seller / Overall Pick), image
and Prime flag. The parser (`parse_search_page`) is pure BeautifulSoup so it
can be tested on saved HTML.
"""
from __future__ import annotations

import logging
import random
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote_plus

from . import config

logger = logging.getLogger(__name__)

TRANSPORT = "playwright_firefox"
DEFAULT_MAX_PAGES = 3
HARD_MAX_PAGES = 7
PAGE_JITTER_MS = (4000, 9000)
WARMUP_WAIT_MS = (2500, 4500)

_CAPTCHA_MARKERS = (
    "/errors/validatecaptcha", 'id="captchacharacters"', "type the characters you see in this image",
    "enter the characters you see below", "<title>robot check</title>", "api-services-support@amazon.com",
    "automated access to amazon data",
)
_ERROR_PAGE_MARKERS = ("sorry! something went wrong", "<title>sorry!")

_BOUGHT_PATTERNS = (
    re.compile(r"(\d[\d,.]*)\s*([KkMm])?\s*\+?\s*bought in (?:the )?past month", re.I),
    re.compile(r"(\d[\d,.]*)\s*([KkMm])?\s*\+?\s*(?:mal\s+)?im letzten monat gekauft", re.I),
    re.compile(r"(\d[\d,.]*)\s*([KkMm])?\s*\+?\s*achet[ée]s? au cours du mois dernier", re.I),
    re.compile(r"(\d[\d,.]*)\s*([KkMm])?\s*\+?\s*comprados? el mes pasado", re.I),
    re.compile(r"(\d[\d,.]*)\s*([KkMm])?\s*\+?\s*acquistat[oi] il mese scorso", re.I),
    re.compile(r"過去1か月で\s*(\d[\d,.]*)\s*([KkMm])?\s*点以上購入", re.I),
)
_RATING_RE = re.compile(r"(\d(?:[.,]\d)?)\s*(?:out of|von|sur|de|su|/)\s*5", re.I)
_COUNT_RE = re.compile(r"(\d[\d,.]*)\s*([KkMm])?")
_SPONSORED_SELECTORS = (
    '[aria-label="View Sponsored information or leave ad feedback"]',
    ".puis-sponsored-label-text", ".s-sponsored-label-text", ".puis-sponsored-label-info-icon",
)
_BADGE_MAP = {"amazon's choice": "amazons_choice", "amazons choice": "amazons_choice", "best seller": "best_seller",
              "overall pick": "overall_pick", "climate pledge friendly": "climate_pledge"}


# ------------------------------------------------------------------ helpers

def build_search_url(keyword: str, marketplace: str = "US", page: int = 1) -> str:
    mp = config.marketplace(marketplace)
    url = f"https://www.{mp['domain']}/s?k={quote_plus(keyword.strip())}"
    if page and page > 1:
        url += f"&page={page}&ref=sr_pg_{page}"
    return url


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40] or "kw"


def dump_html(html: str, *, marketplace: str, keyword: str, kind: str, page: int = 0) -> str:
    d = config.DATA_DIR / "dumps"
    d.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = d / f"{kind}_{marketplace.upper()}_{_slug(keyword)}_p{page}_{ts}.html"
    try:
        path.write_text(html or "", encoding="utf-8")
    except OSError:
        return ""
    return str(path)


def classify_block(html: str) -> str:
    """'' (normal), 'captcha' (abort) or 'error_page' (retry once)."""
    if not html:
        return "error_page"
    low = html.lower()
    if any(m in low for m in _CAPTCHA_MARKERS):
        return "captcha"
    if any(m in low for m in _ERROR_PAGE_MARKERS):
        return "error_page"
    return ""


def parse_count(text: str) -> int | None:
    m = _COUNT_RE.search(text or "")
    if not m:
        return None
    num, suffix = m.group(1), (m.group(2) or "").upper()
    try:
        if suffix:
            return int(round(float(num.replace(",", ".")) * (1000 if suffix == "K" else 1_000_000)))
        return int(num.replace(",", "").replace(".", ""))
    except ValueError:
        return None


def parse_bought_past_month(text: str) -> tuple[int | None, str]:
    for pattern in _BOUGHT_PATTERNS:
        m = pattern.search(text or "")
        if m:
            return parse_count(f"{m.group(1)}{m.group(2) or ''}"), m.group(0).strip()[:32]
    return None, ""


def parse_price(text: str) -> float | None:
    cleaned = re.sub(r"[^\d,.]", "", text or "")
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".") if cleaned.rfind(",") > cleaned.rfind(".") else cleaned.replace(",", "")
    elif "," in cleaned:
        head, _, tail = cleaned.rpartition(",")
        cleaned = f"{head.replace(',', '')}.{tail}" if len(tail) == 2 else cleaned.replace(",", "")
    try:
        return float(Decimal(cleaned).quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError):
        return None


def parse_rating(text: str) -> float | None:
    m = _RATING_RE.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _badge_key(text: str) -> str:
    low = (text or "").strip().lower()
    for needle, key in _BADGE_MAP.items():
        if needle in low:
            return key
    return re.sub(r"[^a-z0-9]+", "_", low).strip("_")[:32]


def _is_sponsored(card) -> bool:
    if any(card.select_one(sel) is not None for sel in _SPONSORED_SELECTORS):
        return True
    for el in card.select("span.puis-label-popover-default, span.s-label-popover-default, .a-color-secondary"):
        if el.get_text(strip=True).lower() in {"sponsored", "gesponsert", "sponsorisé", "patrocinado", "sponsorizzato", "スポンサー"}:
            return True
    return False


def _review_count(card) -> int | None:
    block = card.select_one('[data-cy="reviews-block"]') or card
    for sel in ("span.s-underline-text", "a[aria-label*='rating']", "span[aria-label*='rating']"):
        el = block.select_one(sel)
        if el is not None:
            v = parse_count(el.get_text(strip=True) or el.get("aria-label") or "")
            if v is not None:
                return v
    return None


def parse_search_page(html: str, page_number: int = 1, *, marketplace: str = "US") -> list[dict]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    currency = config.marketplace(marketplace)["currency"]
    items: list[dict] = []
    seen: set[str] = set()
    for card in soup.select('div[data-component-type="s-search-result"][data-asin]'):
        asin = (card.get("data-asin") or "").strip().upper()
        if not asin or asin in seen:
            continue
        seen.add(asin)
        text = card.get_text(" ", strip=True)
        h2 = card.select_one("h2")
        title = re.sub(r"\s+", " ", (h2.get_text(" ", strip=True) or h2.get("aria-label") or "") if h2 else "")[:512]
        price_el = card.select_one(".a-price .a-offscreen")
        rating_el = card.select_one("span.a-icon-alt")
        badge_el = card.select_one("span.a-badge-text") or card.select_one("span.a-badge-label-inner")
        img = card.select_one("img.s-image")
        bought_min, bought_raw = parse_bought_past_month(text)
        items.append({
            "asin": asin, "page": page_number, "page_position": len(items) + 1, "sponsored": _is_sponsored(card),
            "title": title, "price": parse_price(price_el.get_text(strip=True)) if price_el else None, "currency": currency,
            "rating": parse_rating(rating_el.get_text(strip=True)) if rating_el else None, "review_count": _review_count(card),
            "bought_past_month_min": bought_min, "bought_past_month_raw": bought_raw,
            "badge": _badge_key(badge_el.get_text(strip=True)) if badge_el else "",
            "image_url": (img.get("src") or "") if img else "", "is_prime": card.select_one("i.a-icon-prime, .s-prime") is not None,
        })
    return items


def has_next_page(html: str) -> bool:
    from bs4 import BeautifulSoup

    nxt = BeautifulSoup(html or "", "html.parser").select_one(".s-pagination-next")
    return nxt is not None and "s-pagination-disabled" not in (nxt.get("class") or [])


def dedupe_products(products: list[dict]) -> list[dict]:
    """Collapse repeat sightings across pages; first sighting keeps page/position,
    first organic sighting sets organic_position; sponsored=True only if never organic."""
    by_asin: dict[str, dict] = {}
    rank = 0
    for p in sorted(products, key=lambda p: (p.get("page", 1), p.get("page_position", 0))):
        asin = p["asin"]
        if asin not in by_asin:
            rank += 1
            entry = dict(p)
            entry["position"] = rank
            entry["organic_position"] = None if p.get("sponsored") else rank
            entry["sponsored"] = bool(p.get("sponsored"))
            by_asin[asin] = entry
            continue
        entry = by_asin[asin]
        if entry["organic_position"] is None and not p.get("sponsored"):
            entry["organic_position"] = entry["position"]
            entry["sponsored"] = False
        for key in ("price", "rating", "review_count", "bought_past_month_min", "bought_past_month_raw", "badge", "image_url"):
            if not entry.get(key) and p.get(key):
                entry[key] = p[key]
    return list(by_asin.values())


# ------------------------------------------------------------------ fetcher

def _launch(pw, marketplace: str):
    mp = config.marketplace(marketplace)
    browser = pw.firefox.launch(headless=True)
    context = browser.new_context(locale=mp["locale"], viewport={"width": 1366, "height": 768},
                                  extra_http_headers={"Accept-Language": mp["lang"]})
    return browser, context, context.new_page()


def fetch_search_results(keyword: str, *, marketplace: str = "US", max_pages: int = DEFAULT_MAX_PAGES,
                         dump_on_failure: bool = True, dump_html_dir: str | None = None,
                         jitter_ms: tuple[int, int] = PAGE_JITTER_MS, log=None) -> dict:
    """Returns {"ok", "captcha", "error", "dump_path", "pages": [...], "products": [...]}. Never raises."""
    from playwright.sync_api import sync_playwright

    mp = config.marketplace(marketplace)
    max_pages = max(1, min(int(max_pages or 1), HARD_MAX_PAGES))
    pages_meta: list[dict] = []
    all_products: list[dict] = []
    result: dict = {"ok": True, "captcha": False, "error": "", "dump_path": "", "transport": TRANSPORT}
    say = log or (lambda m: None)
    try:
        with sync_playwright() as pw:
            browser, context, page = _launch(pw, mp["code"])
            try:
                try:
                    page.goto(f"https://www.{mp['domain']}/", wait_until="domcontentloaded", timeout=45_000)
                    page.wait_for_timeout(random.randint(*WARMUP_WAIT_MS))
                except Exception:  # noqa: BLE001 — warm-up is best-effort
                    pass
                for n in range(1, max_pages + 1):
                    url = build_search_url(keyword, mp["code"], n)
                    say(f"  page {n}: {url}")
                    html, block = "", ""
                    for attempt in (1, 2):
                        page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                        page.wait_for_timeout(1500)
                        try:
                            page.mouse.wheel(0, 3000)
                            page.wait_for_timeout(800)
                        except Exception:  # noqa: BLE001
                            pass
                        html = page.content()
                        block = classify_block(html)
                        if block != "error_page" or attempt == 2:
                            break
                        say("  Amazon error page — retrying once")
                        page.wait_for_timeout(random.randint(*jitter_ms))
                    if dump_html_dir:
                        Path(dump_html_dir).mkdir(parents=True, exist_ok=True)
                        (Path(dump_html_dir) / f"amazon_search_{mp['code'].lower()}_{_slug(keyword)}_p{n}.html").write_text(html, encoding="utf-8")
                    if block:
                        result.update({
                            "ok": False, "captcha": block == "captcha",
                            "error": f"Amazon served a robot check on page {n} — stop and try again later (never bypass it)"
                            if block == "captcha" else f"Amazon served its error page twice on page {n} (cold session / soft block)",
                            "dump_path": dump_html(html, marketplace=mp["code"], keyword=keyword, kind="blocked", page=n) if dump_on_failure else "",
                        })
                        break
                    items = parse_search_page(html, n, marketplace=mp["code"])
                    meta = {"page": n, "url": url, "result_count": len(items)}
                    if not items:
                        meta["dump_path"] = dump_html(html, marketplace=mp["code"], keyword=keyword, kind="empty", page=n) if dump_on_failure else ""
                        pages_meta.append(meta)
                        if n == 1:
                            result.update({"ok": False, "error": "no product cards parsed on page 1 (layout change?)", "dump_path": meta["dump_path"]})
                        break
                    pages_meta.append(meta)
                    all_products.extend(items)
                    if n < max_pages and not has_next_page(html):
                        break
                    if n < max_pages:
                        page.wait_for_timeout(random.randint(*jitter_ms))
            finally:
                try:
                    context.close()
                    browser.close()
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001
        logger.exception("scrape failed")
        result.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]})
    result["pages"] = pages_meta
    result["products"] = dedupe_products(all_products)
    return result
