"""Orchestration: search → enrich → keywords → analyze → report, all against the SQLite store."""
from __future__ import annotations

import json
import statistics
import time
from collections import Counter
from typing import Callable

from . import ads_api, brand_analytics, catalog, config, db, product_page
from .analysis import competitive_analysis
from .keywords import extract_candidates, normalize_keyword, singular, tokenize
from .report import build_report, write_report
from .scoring import score_run
from .search_scraper import fetch_search_results

Log = Callable[[str], None]


def _say(log: Log | None) -> Log:
    return log or (lambda m: None)


# ---------------------------------------------------------------- summary

def _median(vals) -> float | None:
    vals = [float(v) for v in vals if v is not None]
    return round(statistics.median(vals), 2) if vals else None


def compute_summary(conn, run_id: int) -> dict:
    products = db.list_products(conn, run_id)
    organic = [p for p in products if p["organic_position"] is not None and not p["excluded"]]
    page1 = [p for p in organic if p["page"] == 1]

    def rev(p):
        return round(p["price"] * p["bought_past_month_min"], 2) if p["price"] is not None and p["bought_past_month_min"] else None

    known1 = [p for p in page1 if p["bought_past_month_min"]]
    known = [p for p in organic if p["bought_past_month_min"]]
    top = sorted(known, key=lambda p: -(rev(p) or 0))[:10]
    brands = Counter(p["brand_name"] for p in products if p["brand_name"])
    summary = {
        "page1_organic_count": len(page1), "page1_units_known_count": len(known1),
        "page1_units_min_sum": sum(p["bought_past_month_min"] for p in known1) or None,
        "page1_revenue_min_sum": round(sum(rev(p) or 0 for p in known1), 2) or None,
        "all_pages_organic_count": len(organic), "all_pages_units_known_count": len(known),
        "all_pages_units_min_sum": sum(p["bought_past_month_min"] for p in known) or None,
        "all_pages_revenue_min_sum": round(sum(rev(p) or 0 for p in known), 2) or None,
        "median_price": _median(p["price"] for p in page1), "median_rating": _median(p["rating"] for p in page1),
        "median_review_count": _median(p["review_count"] for p in page1),
        "top_brands": [{"brand": b, "count": c} for b, c in brands.most_common(5)],
        "top_sellers": [{"asin": p["asin"], "title": p["title"][:80], "brand_name": p["brand_name"], "price": p["price"],
                         "units_min": p["bought_past_month_min"], "revenue_min": rev(p), "bsr_rank": p["bsr_rank"]} for p in top],
        "note": "units are Amazon's bucketed 'bought in past month' floors (hidden under ~50/mo); revenue = floor × retail price; all lower bounds",
    }
    db.update_run(conn, run_id, summary=summary)
    return summary


def products_with_revenue(conn, run_id: int) -> list[dict]:
    rows = db.list_products(conn, run_id)
    for p in rows:
        p["revenue_min"] = round(p["price"] * p["bought_past_month_min"], 2) if p["price"] is not None and p["bought_past_month_min"] else None
    return rows


# ---------------------------------------------------------------- steps

def search(conn, keyword: str, *, marketplace: str = "US", pages: int = 3, fetch: Callable = None, log: Log | None = None) -> dict:
    say = _say(log)
    mp = config.marketplace(marketplace)["code"]
    run_id = db.create_run(conn, keyword=keyword, marketplace=mp, pages=pages)
    db.update_run(conn, run_id, status="scraping")
    say(f"run #{run_id}: scraping up to {pages} page(s) of {mp} results for {keyword!r}")
    result = (fetch or fetch_search_results)(keyword, marketplace=mp, max_pages=pages, log=log)
    products = result.get("products") or []
    db.replace_products(conn, run_id, products)
    db.update_run(conn, run_id, status="scraped" if result.get("ok") else "failed", pages_scraped=len(result.get("pages") or []),
                  products_found=len(products), sponsored_count=sum(1 for p in products if p.get("sponsored")),
                  captcha_detected=bool(result.get("captcha")), error=result.get("error") or "")
    compute_summary(conn, run_id)
    run = db.get_run(conn, run_id)
    say(f"  {run['pages_scraped']} page(s), {run['products_found']} products ({run['sponsored_count']} sponsored-only)"
        + (f" — FAILED: {run['error']} (dump: {result.get('dump_path')})" if not result.get("ok") else ""))
    return run


def enrich(conn, run_id: int, *, source: str = "auto", limit: int | None = None, force: bool = False, log: Log | None = None) -> dict:
    """Fill brand / BSR / bullets. source: auto (SP-API if configured, else page), sp-api, page, none."""
    say = _say(log)
    products = [p for p in db.list_products(conn, run_id) if force or not p["enriched_from"]]
    if source == "auto":
        source = "sp-api" if config.spapi_configured() else "page"
    if source == "none" or not products:
        return {"source": source, "enriched": 0, "missing": []}
    if source == "page":
        organic = [p for p in products if p["organic_position"] is not None and not p["excluded"]]
        products = sorted(organic, key=lambda p: (0 if p["bought_past_month_min"] else 1, -(p["bought_past_month_min"] or 0), p["position"]))[: limit or product_page.MAX_PAGES_PER_RUN]
        say(f"  reading {len(products)} product pages (slow, research-only; set SP-API creds to avoid this)")
        data = product_page.fetch_product_pages([p["asin"] for p in products], marketplace=db.get_run(conn, run_id)["marketplace"], log=log)
    else:
        if limit:
            products = products[:limit]
        say(f"  SP-API catalog lookup for {len(products)} ASIN(s)")
        data = catalog.fetch_catalog_items([p["asin"] for p in products], marketplace=db.get_run(conn, run_id)["marketplace"], log=log)
    enriched, missing = 0, []
    for p in products:
        d = data.get(p["asin"])
        if not d or d.get("error"):
            db.update_product(conn, run_id, p["asin"], enrich_error=(d or {}).get("error") or "not_in_catalog")
            missing.append(p["asin"])
            continue
        fields = {k: d[k] for k in ("brand_name", "catalog_title", "bsr_category", "bsr_rank", "bsr_ranks", "bullets") if k in d}
        for k in ("rating", "review_count", "price"):
            if d.get(k) is not None and p.get(k) is None:
                fields[k] = d[k]
        db.update_product(conn, run_id, p["asin"], enriched_from=source, enrich_error="", **fields)
        enriched += 1
    db.update_run(conn, run_id, status="enriched")
    compute_summary(conn, run_id)
    say(f"  enriched {enriched}, missing {len(missing)}")
    return {"source": source, "enriched": enriched, "missing": missing}


def _asins_for_recs(products: list[dict], top_n: int) -> list[str]:
    pool = [p for p in products if not p["excluded"]]
    short = [p["asin"] for p in pool if p["shortlisted"]]
    if short:
        return short[:50]
    pool.sort(key=lambda p: (0 if p["bought_past_month_min"] else 1, -(p["bought_past_month_min"] or 0), p["position"]))
    return [p["asin"] for p in pool[: min(top_n, 50)]]


def _overlap(seed: str, kw: str) -> str:
    s = {singular(t) for t in tokenize(seed)}
    k = {singular(t) for t in tokenize(kw)}
    return "all" if s and s <= k else ("any" if s & k else "none")


def keywords(conn, run_id: int, *, top_n: int = 30, max_candidates: int = 150, use_ads: bool | None = None, log: Log | None = None) -> dict:
    say = _say(log)
    run = db.get_run(conn, run_id)
    products = db.list_products(conn, run_id)
    if not products:
        raise RuntimeError("run has no products — search first")
    seed = run["keyword"]
    brand_names = sorted({p["brand_name"] for p in products if p["brand_name"]})
    rows = [dict(p, excluded=bool(p["excluded"])) for p in products]
    cands = extract_candidates(rows, seed=seed, brand_names=brand_names, top_n=top_n, max_candidates=max_candidates)
    db.delete_candidates(conn, run_id)
    for c in cands:
        db.upsert_candidate(conn, run_id, c["keyword"], from_seed=c["from_seed"], from_listings=c["from_listings"], ngram_score=c["ngram_score"],
                            product_count=c["product_count"], weighted_units=c["weighted_units"], is_branded=c["is_branded"],
                            excluded=c["is_branded"], seed_overlap="all" if c["contains_seed_all"] else ("any" if c["contains_seed_any"] else "none"))
    say(f"  {len(cands)} listing-copy candidates")

    warnings: list[str] = []
    n_recs = 0
    if use_ads is None:
        use_ads = config.ads_configured()
    if use_ads and not config.ads_configured():
        warnings.append("Ads API not configured — skipping keyword recommendations")
    elif use_ads:
        asins = _asins_for_recs(products, top_n)
        for i, sort in enumerate(("CLICKS", "CONVERSIONS")):
            if i:
                time.sleep(2)
            items, err = ads_api.keyword_recommendations(asins, marketplace=run["marketplace"], sort=sort)
            if err:
                warnings.append(f"keyword recommendations ({sort}): {err}")
                continue
            n_recs = max(n_recs, len(items))
            for it in items:
                kw = normalize_keyword(it["keyword"])
                if not kw:
                    continue
                cur = db.get_candidate(conn, run_id, kw) or {}
                vals = {"from_ads": 1}
                if cur.get("rec_rank") is None or it["rank"] < cur["rec_rank"]:
                    vals.update(rec_rank=it["rank"], rec_sort=sort)
                if it["impression_rank"] is not None:
                    vals["impression_rank"] = it["impression_rank"]
                if it["impression_share"] is not None:
                    vals["impression_share"] = it["impression_share"]
                bid = next((b for b in it["bid_info"] if b["match_type"] == "EXACT"), it["bid_info"][0] if it["bid_info"] else None)
                if bid and cur.get("bid_median") is None:
                    vals.update(bid_low=bid["low"], bid_median=bid["median"], bid_high=bid["high"])
                if not cur:
                    vals["seed_overlap"] = _overlap(seed, kw)
                db.upsert_candidate(conn, run_id, kw, **vals)
            say(f"  Amazon keyword recommendations ({sort}): {len(items)}")
        unpriced = [c["keyword"] for c in db.list_candidates(conn, run_id) if c["bid_median"] is None]
        if unpriced:
            bids = ads_api.bid_recommendations(asins, unpriced)
            for kw, b in bids.items():
                db.upsert_candidate(conn, run_id, normalize_keyword(kw), bid_low=b["low"], bid_median=b["median"], bid_high=b["high"])
            say(f"  bid recommendations for {len(bids)} unpriced keyword(s)")

    all_kws = [c["keyword"] for c in db.list_candidates(conn, run_id)]
    ba = brand_analytics.latest_ranks_for(conn, run["marketplace"], all_kws)
    missing = [k for k in all_kws if k not in ba]
    if missing and brand_analytics.latest_index_path(run["marketplace"]):
        ba.update(brand_analytics.lookup_index(conn, run["marketplace"], missing))
    for kw, info in ba.items():
        db.upsert_candidate(conn, run_id, kw, from_ba=1, search_frequency_rank=info["search_frequency_rank"], ba_matched_term=info["matched_term"])
    if not ba:
        warnings.append("no Brand Analytics data for this marketplace (run `ba-ingest` with SP-API creds) — scores are Ads/listing-driven")
    say(f"  Brand Analytics ranks matched: {len(ba)}")

    summary = run.get("summary") or {}
    signals = []
    for c in db.list_candidates(conn, run_id):
        signals.append({"keyword": c["keyword"], "search_frequency_rank": c["search_frequency_rank"], "impression_rank": c["impression_rank"],
                        "rec_rank": c["rec_rank"], "our_impressions": c["our_impressions"], "impression_share": c["impression_share"],
                        "units": summary.get("page1_units_min_sum") if c["from_seed"] else (c["weighted_units"] or None),
                        "ngram_score": c["ngram_score"], "bid_median": c["bid_median"]})
    for s in score_run(signals, n_recs=n_recs):
        db.upsert_candidate(conn, run_id, s["keyword"], demand_score=s["demand_score"], demand_tier=s["demand_tier"], confidence=s["confidence"],
                            competition_score=s["competition_score"], sources=s["sources"], est_total_ad_impressions=s["est_total_ad_impressions"])
    db.update_run(conn, run_id, status="keywords_done")
    for w in warnings:
        say(f"  warning: {w}")
    return {"candidates": len(signals), "ads_recs": n_recs, "ba_matched": len(ba), "warnings": warnings}


def analyze(conn, run_id: int, *, top_n: int = 12, log: Log | None = None) -> str:
    say = _say(log)
    run = db.get_run(conn, run_id)
    products = [p for p in products_with_revenue(conn, run_id) if p["organic_position"] is not None and not p["excluded"]]
    short = [p for p in products if p["shortlisted"]]
    pool = short or sorted(products, key=lambda p: (-(p["revenue_min"] or 0), p["position"]))[:top_n]
    say(f"  LLM competitive analysis over {len(pool)} competitor(s) …")
    text = competitive_analysis(pool, product_type=run["keyword"], keywords=db.list_candidates(conn, run_id), summary=run.get("summary") or {})
    db.update_run(conn, run_id, analysis=text)
    return text


def report(conn, run_id: int, log: Log | None = None):
    run = db.get_run(conn, run_id)
    path = write_report(run, build_report(run, products_with_revenue(conn, run_id), db.list_candidates(conn, run_id), analysis=run.get("analysis") or ""))
    _say(log)(f"  report → {path}")
    return path


def shortlist(conn, run_id: int, asins: list[str], *, exclude: bool = False, note: str = "") -> int:
    n = 0
    for a in asins:
        db.update_product(conn, run_id, a.upper(), **({"excluded": 1, "shortlisted": 0} if exclude else {"shortlisted": 1, "excluded": 0}), note=note)
        n += 1
    compute_summary(conn, run_id)
    return n


def track(conn, keyword: str, *, limit: int = 12) -> list[dict]:
    """Runs for a keyword over time with their floors — the sales-tracking view."""
    out = []
    for r in db.list_runs(conn, keyword=keyword, limit=limit):
        s = r.get("summary") or {}
        out.append({"run_id": r["id"], "date": r["created_at"][:10], "products": r["products_found"], "page1_units_min_sum": s.get("page1_units_min_sum"),
                    "page1_revenue_min_sum": s.get("page1_revenue_min_sum"), "all_pages_units_min_sum": s.get("all_pages_units_min_sum"),
                    "median_price": s.get("median_price"), "top_seller": (s.get("top_sellers") or [{}])[0].get("asin")})
    return out
