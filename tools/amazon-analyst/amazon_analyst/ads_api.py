"""
Amazon Ads API: keyword recommendations v5 (reverse-ASIN) and bid
recommendations for a new ad group. Needs an approved Ads API app and a
profile you can access. Bids come back as integer cents under
bidInfo[].suggestedBid (verified live 2026-09-10); we convert to major units.
"""
from __future__ import annotations

import os

from . import config
from .lwa import access_token, post_with_429_retry

KW_REC_CONTENT_TYPE = "application/vnd.spkeywordsrecommendation.v5+json"
BID_REC_CONTENT_TYPE = "application/vnd.spthemebasedbidrecommendation.v4+json"
MAX_ASINS = 50
MAX_RECS = 200
_MATCH_EXPR = {"EXACT": "KEYWORD_EXACT_MATCH", "PHRASE": "KEYWORD_PHRASE_MATCH", "BROAD": "KEYWORD_BROAD_MATCH"}
_EXPR_MATCH = {v: k for k, v in _MATCH_EXPR.items()}


def _headers(content_type: str) -> dict:
    token = access_token(os.environ["ADS_LWA_CLIENT_ID"], os.environ["ADS_LWA_CLIENT_SECRET"], os.environ["ADS_REFRESH_TOKEN"])
    return {"Amazon-Advertising-API-ClientId": os.environ["ADS_LWA_CLIENT_ID"], "Amazon-Advertising-API-Scope": os.environ["ADS_PROFILE_ID"],
            "Authorization": f"Bearer {token}", "Content-Type": content_type, "Accept": content_type}


def _base() -> str:
    return config.ADS_BASE.get(os.getenv("ADS_REGION", "NA").upper(), config.ADS_BASE["NA"])


def _amount(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return round(v / 100.0, 2) if v == int(v) else round(v, 2)


def keyword_recommendations(asins: list[str], *, marketplace: str = "US", sort: str = "CLICKS", max_recommendations: int = MAX_RECS) -> tuple[list[dict], str]:
    """(items, error). items: keyword, rank, impression_rank, impression_share (percent), bid_info [{match_type, low, median, high}]."""
    asins = [a.strip().upper() for a in asins if a and a.strip()][:MAX_ASINS]
    if not asins:
        return [], "no ASINs"
    mp = config.marketplace(marketplace)
    if mp["code"] not in config.ADS_KEYWORD_REC_MARKETPLACES:
        return [], f"keyword recommendations are not offered in {mp['code']}"
    payload = {"recommendationType": "KEYWORDS_FOR_ASINS", "asins": asins, "maxRecommendations": max(1, min(int(max_recommendations), MAX_RECS)),
               "sortDimension": sort.upper(), "locale": mp["ads_locale"], "bidsEnabled": True}
    r = post_with_429_retry(f"{_base()}/sp/targets/keywords/recommendations", headers=_headers(KW_REC_CONTENT_TYPE), payload=payload, timeout=45)
    if r.status_code >= 400:
        return [], f"HTTP {r.status_code}: {r.text[:300]}"
    items = []
    for idx, t in enumerate(r.json().get("keywordTargetList") or [], start=1):
        kw = (t.get("keyword") or "").strip()
        if not kw:
            continue
        bids = []
        for bi in t.get("bidInfo") or []:
            rng = bi.get("suggestedBid") if isinstance(bi.get("suggestedBid"), dict) else bi
            bids.append({"match_type": (bi.get("matchType") or "").upper(), "low": _amount(rng.get("rangeStart")),
                         "median": _amount(rng.get("rangeMedian") if rng.get("rangeMedian") is not None else bi.get("bid")), "high": _amount(rng.get("rangeEnd"))})
        share, rank = t.get("searchTermImpressionShare"), t.get("searchTermImpressionRank")
        items.append({"keyword": kw, "rank": idx, "impression_rank": int(rank) if rank not in (None, "") else None,
                      "impression_share": float(share) if share not in (None, "") else None, "bid_info": bids})
    return items, ""


def bid_recommendations(asins: list[str], keywords: list[str], *, match_type: str = "EXACT") -> dict[str, dict]:
    """{"keyword": {"low", "median", "high"}} via BIDS_FOR_NEW_AD_GROUP."""
    asins = [a.strip().upper() for a in asins if a][:MAX_ASINS]
    if not asins or not keywords:
        return {}
    out: dict[str, dict] = {}
    exprs = [{"type": _MATCH_EXPR[match_type.upper()], "value": k} for k in keywords]
    for i in range(0, len(exprs), 100):
        r = post_with_429_retry(f"{_base()}/sp/targets/bid/recommendations", headers=_headers(BID_REC_CONTENT_TYPE),
                                payload={"targetingExpressions": exprs[i:i + 100], "asins": asins, "recommendationType": "BIDS_FOR_NEW_AD_GROUP"})
        if r.status_code >= 400:
            continue
        for theme in r.json().get("bidRecommendations", []):
            for rec in theme.get("bidRecommendationsForTargetingExpressions", []):
                kw = (rec.get("targetingExpression") or {}).get("value", "")
                vals = [float(v.get("suggestedBid", 0) or 0) for v in rec.get("bidValues", [])]
                if kw and vals and vals[len(vals) // 2] > 0:
                    out[kw] = {"low": vals[0], "median": vals[len(vals) // 2], "high": vals[-1]}
    return out
