"""
amazon_analyst/scoring.py

Turn the honest demand signals we can collect into one 0-100 demand score per
keyword, with an explicit confidence and the list of sources that fed it
(pure — no DB, no network).

Signals and weights (renormalized over whichever are present):

  ba     0.45  Brand Analytics search-frequency rank (marketplace-wide, official)
  imp    0.20  Ads keyword-rec searchTermImpressionRank (our rank among advertisers)
  rec    0.10  position in Amazon's ranked keyword recommendations for the ASIN set
  share  0.15  est. total ad impressions = our impressions / our impression share
  units  0.07  page-1 "bought in past month" floors (seed) / weighted units (derived)
  ngram  0.03  listing-copy prevalence

The score divides by max(present weight, MIN_WEIGHT=0.35): a keyword backed
only by listing copy (0.10) tops out at ~29, while Brand Analytics alone (0.45)
or the Ads trio (0.45) can reach 100. `confidence` reports the present weight.

No signal is a search-volume number and none pretends to be. Bid median is a
competition signal, not demand — exposed separately as competition_score.
Phase 3 adds calibrate_sfr_to_volume(): a log-log fit of Search Query
Performance volumes (our own ASINs) against search-frequency rank, which turns
rank into an *estimated* volume clearly labelled as such.
"""
from __future__ import annotations

import math
from typing import Any

WEIGHTS = {"ba": 0.45, "imp": 0.20, "rec": 0.10, "share": 0.15, "units": 0.07, "ngram": 0.03}
# Scores are normalised over the weight actually present, but never over less
# than this — listing-only evidence (0.10) must not produce a 100.
MIN_WEIGHT = 0.35
TIERS = ((70.0, "A"), (45.0, "B"), (25.0, "C"))


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _log_norm(value, max_value) -> float | None:
    if value is None or max_value in (None, 0) or value <= 0:
        return None
    return _clamp(math.log1p(value) / math.log1p(max_value))


def est_total_ad_impressions(our_impressions, impression_share) -> int | None:
    """our_impressions / (share%/100). Both must be > 0."""
    try:
        ours = float(our_impressions or 0)
        share = float(impression_share or 0)
    except (TypeError, ValueError):
        return None
    if ours <= 0 or share <= 0:
        return None
    return int(round(ours / (share / 100.0)))


# A tier is a claim about demand; with only listing signals present it would
# be a claim about nothing. Confidence below these floors caps the tier.
TIER_CONFIDENCE_FLOORS = ((0.35, "A"), (0.15, "C"))


def tier_for(score: float | None, confidence: float | None = None) -> str:
    if score is None:
        return ""
    tier = "D"
    for threshold, t in TIERS:
        if score >= threshold:
            tier = t
            break
    if confidence is not None:
        if confidence < 0.15:
            return "D"
        if confidence < 0.35 and tier in ("A", "B"):
            return "C"
    return tier


def component_scores(
    signal: dict[str, Any],
    *,
    n_recs: int = 0,
    max_est_impressions: int | None = None,
    max_units: int | None = None,
) -> dict[str, float | None]:
    """Each component in 0-1, or None when its source is absent.

    signal keys: search_frequency_rank, impression_rank, rec_rank,
    est_total_ad_impressions, units, ngram_score.
    """
    sfr = signal.get("search_frequency_rank")
    imp_rank = signal.get("impression_rank")
    rec_rank = signal.get("rec_rank")
    est_imp = signal.get("est_total_ad_impressions")
    units = signal.get("units")
    ngram = signal.get("ngram_score")

    s_ba = _clamp(1.0 - math.log10(sfr) / 6.0) if sfr and sfr > 0 else None
    s_imp = _clamp(1.0 - math.log10(imp_rank) / 5.0) if imp_rank and imp_rank > 0 else None
    s_rec = None
    if rec_rank and rec_rank > 0 and n_recs and n_recs > 0:
        s_rec = _clamp(1.0 - (rec_rank - 1) / float(max(n_recs, 1)))
    s_share = _log_norm(est_imp, max_est_impressions)
    s_units = _log_norm(units, max_units)
    s_ngram = _clamp(float(ngram) / 100.0) if ngram is not None else None
    return {"ba": s_ba, "imp": s_imp, "rec": s_rec, "share": s_share, "units": s_units, "ngram": s_ngram}


def score_keyword(
    signal: dict[str, Any],
    *,
    n_recs: int = 0,
    max_est_impressions: int | None = None,
    max_units: int | None = None,
) -> dict[str, Any]:
    """Return {"demand_score", "demand_tier", "confidence", "sources", "components"}.

    demand_score = 100 · Σ(w·s over present) / Σ(w over present)
    confidence   = Σ(w over present)  (1.0 when every source fed the score)
    """
    comps = component_scores(signal, n_recs=n_recs, max_est_impressions=max_est_impressions, max_units=max_units)
    present = {k: v for k, v in comps.items() if v is not None}
    if not present:
        return {"demand_score": None, "demand_tier": "", "confidence": 0.0, "sources": [], "components": comps}
    weight_sum = sum(WEIGHTS[k] for k in present)
    score = 100.0 * sum(WEIGHTS[k] * v for k, v in present.items()) / max(weight_sum, MIN_WEIGHT)
    score = round(score, 2)
    confidence = round(weight_sum, 3)
    return {
        "demand_score": score,
        "demand_tier": tier_for(score, confidence),
        "confidence": confidence,
        "sources": sorted(present.keys(), key=lambda k: -WEIGHTS[k]),
        "components": comps,
    }


def competition_score(bid_median, max_bid_median) -> float | None:
    try:
        b = float(bid_median or 0)
        m = float(max_bid_median or 0)
    except (TypeError, ValueError):
        return None
    if b <= 0 or m <= 0:
        return None
    return round(_clamp(b / m), 3)


def score_run(signals: list[dict[str, Any]], *, n_recs: int = 0) -> list[dict[str, Any]]:
    """Score every keyword of a run with run-level normalization maxima.
    Each input dict may carry: keyword, search_frequency_rank, impression_rank,
    rec_rank, our_impressions, impression_share, units, ngram_score, bid_median.
    The output is the same dicts, extended in place with est_total_ad_impressions,
    demand_score, demand_tier, confidence, sources, competition_score."""
    for s in signals:
        s["est_total_ad_impressions"] = est_total_ad_impressions(s.get("our_impressions"), s.get("impression_share"))
    max_est = max((s["est_total_ad_impressions"] or 0 for s in signals), default=0) or None
    max_units = max((s.get("units") or 0 for s in signals), default=0) or None
    max_bid = max((float(s.get("bid_median") or 0) for s in signals), default=0.0) or None
    for s in signals:
        result = score_keyword(s, n_recs=n_recs, max_est_impressions=max_est, max_units=max_units)
        s.update({k: v for k, v in result.items() if k != "components"})
        s["competition_score"] = competition_score(s.get("bid_median"), max_bid)
    return signals


# ---------------------------------------------------------------------------
# Phase 3 — search-frequency rank → estimated volume calibration
# ---------------------------------------------------------------------------

def calibrate_sfr_to_volume(pairs: list[tuple[int, int]]) -> tuple[float, float] | None:
    """Least-squares fit of log(volume) = a + b·log(rank) over (rank, volume)
    pairs where both are > 0. Needs at least 5 pairs. Returns (a, b) or None."""
    pts = [(math.log(r), math.log(v)) for r, v in pairs if r and v and r > 0 and v > 0]
    if len(pts) < 5:
        return None
    n = len(pts)
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in pts) / sxx
    a = my - b * mx
    return a, b


def estimate_volume(search_frequency_rank: int | None, fit: tuple[float, float] | None) -> int | None:
    if not search_frequency_rank or search_frequency_rank <= 0 or not fit:
        return None
    a, b = fit
    return int(round(math.exp(a + b * math.log(search_frequency_rank))))
