"""
Selling Partner API Catalog Items (2022-04-01): brand, canonical title, Best
Sellers Rank and bullet points for ANY ASIN with a seller's own private-app
credentials. Official, no page loads. 2 requests/second, 20 ASINs per call.
"""
from __future__ import annotations

import os
import time

from . import config
from .lwa import access_token, get_with_429_retry

BATCH = 20
INCLUDED = "summaries,attributes,salesRanks"


def _headers() -> dict:
    token = access_token(os.environ["SPAPI_LWA_CLIENT_ID"], os.environ["SPAPI_LWA_CLIENT_SECRET"], os.environ["SPAPI_REFRESH_TOKEN"])
    return {"x-amz-access-token": token, "Content-Type": "application/json"}


def _val(item) -> str:
    return str(item.get("value", "")).strip() if isinstance(item, dict) else (str(item).strip() if item else "")


def _for_marketplace(entries, marketplace_id: str) -> dict:
    entries = entries or []
    for e in entries:
        if isinstance(e, dict) and e.get("marketplaceId") == marketplace_id:
            return e
    return entries[0] if entries and isinstance(entries[0], dict) else {}


def parse_catalog_item(item: dict, marketplace_id: str = "") -> dict:
    summary = _for_marketplace(item.get("summaries"), marketplace_id)
    ranks = _for_marketplace(item.get("salesRanks"), marketplace_id)
    attrs = item.get("attributes") or {}
    display = (ranks.get("displayGroupRanks") or [{}])[0] if ranks else {}
    classification = (ranks.get("classificationRanks") or []) if ranks else []
    bsr_ranks = [{"category": c.get("title") or "", "rank": c.get("rank")} for c in classification if isinstance(c, dict)]
    bsr_category = display.get("title") or (bsr_ranks[0]["category"] if bsr_ranks else "")
    bsr_rank = display.get("rank") or (bsr_ranks[0]["rank"] if bsr_ranks else None)
    return {
        "brand_name": (summary.get("brand") or (_val((attrs.get("brand") or [None])[0]) if attrs.get("brand") else ""))[:255],
        "catalog_title": (summary.get("itemName") or (_val((attrs.get("item_name") or [None])[0]) if attrs.get("item_name") else ""))[:512],
        "bsr_category": (bsr_category or "")[:255],
        "bsr_rank": int(bsr_rank) if bsr_rank else None,
        "bsr_ranks": bsr_ranks,
        "bullets": [_val(b) for b in (attrs.get("bullet_point") or []) if _val(b)],
    }


def fetch_catalog_items(asins: list[str], *, marketplace: str = "US", log=None) -> dict[str, dict]:
    """{asin: parsed fields}. Raises RuntimeError on a non-2xx response."""
    mp = config.marketplace(marketplace)
    base = config.SPAPI_BASE[mp["region"]]
    say = log or (lambda m: None)
    asins = [a.strip().upper() for a in asins if a and a.strip()]
    out: dict[str, dict] = {}
    headers = _headers()
    for i in range(0, len(asins), BATCH):
        batch = asins[i:i + BATCH]
        resp = get_with_429_retry(f"{base}/catalog/2022-04-01/items", headers=headers, params={
            "identifiers": ",".join(batch), "identifiersType": "ASIN", "marketplaceIds": mp["id"], "includedData": INCLUDED, "pageSize": BATCH,
        })
        if resp.status_code >= 400:
            raise RuntimeError(f"Catalog Items HTTP {resp.status_code}: {resp.text[:300]}")
        for item in (resp.json() or {}).get("items") or []:
            asin = (item.get("asin") or "").upper()
            if asin:
                out[asin] = parse_catalog_item(item, mp["id"])
        say(f"  catalog batch {i // BATCH + 1}: {len(batch)} asked, {len(out)} known so far")
        if i + BATCH < len(asins):
            time.sleep(0.6)
    return out
