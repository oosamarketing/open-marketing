"""
Brand Analytics Top Search Terms (SP-API report GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT):
every search term on the marketplace ranked by search frequency, with the three
most-clicked ASINs. The one official marketplace-wide keyword-demand signal.
Needs Brand Registry + the Brand Analytics role on your private SP-API app.

The weekly US document is ~8 million rows / 3 GB uncompressed, so this module
streams: download to disk, incremental JSON decode, keep only the top
`keep_top` terms plus watched ones, and write a compact `rank<TAB>term` index
for long-tail lookups.
"""
from __future__ import annotations

import gzip
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator

import requests

from . import config, db
from .keywords import singular
from .lwa import access_token

REPORT_TYPE = "GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT"
ROW_KEY = "dataByDepartmentAndSearchTerm"
_CHUNK = 1 << 20


def _headers() -> dict:
    token = access_token(os.environ["SPAPI_LWA_CLIENT_ID"], os.environ["SPAPI_LWA_CLIENT_SECRET"], os.environ["SPAPI_REFRESH_TOKEN"])
    return {"x-amz-access-token": token, "Content-Type": "application/json"}


def default_period_bounds(period: str = "WEEK", ref: date | None = None, *, lag_days: int = 3) -> tuple[date, date]:
    period = period.upper()
    cutoff = (ref or date.today()) - timedelta(days=lag_days)
    if period == "WEEK":
        end = cutoff - timedelta(days=(cutoff.weekday() - 5) % 7)
        return end - timedelta(days=6), end
    if period == "MONTH":
        end = cutoff.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    if period == "QUARTER":
        q = ((cutoff.month - 1) // 3) * 3 + 1
        end = cutoff.replace(month=q, day=1) - timedelta(days=1)
        return end.replace(month=((end.month - 1) // 3) * 3 + 1, day=1), end
    return cutoff, cutoff


def _iso(d: date, end: bool = False) -> str:
    t = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc) if end else datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def raw_path(marketplace: str, period: str, start: date) -> Path:
    return config.DATA_DIR / f"ba_search_terms_{marketplace}_{period}_{start.isoformat()}.json.gz"


def index_path(marketplace: str, period: str, start: date) -> Path:
    return config.DATA_DIR / f"ba_terms_index_{marketplace}_{period}_{start.isoformat()}.tsv.gz"


def latest_index_path(marketplace: str, period: str = "WEEK") -> Path | None:
    files = sorted(config.DATA_DIR.glob(f"ba_terms_index_{marketplace.upper()}_{period.upper()}_*.tsv.gz")) if config.DATA_DIR.exists() else []
    return files[-1] if files else None


# ---------------------------------------------------------------- reports API (REST)

def request_report(marketplace: str, *, period: str, start: date, end: date, log=None) -> Path:
    """create → poll → stream-download the report. Returns the raw .json.gz path."""
    mp = config.marketplace(marketplace)
    base = config.SPAPI_BASE[mp["region"]]
    say = log or (lambda m: None)
    r = requests.post(f"{base}/reports/2021-06-30/reports", headers=_headers(), json={
        "reportType": REPORT_TYPE, "marketplaceIds": [mp["id"]], "reportOptions": {"reportPeriod": period.upper()},
        "dataStartTime": _iso(start), "dataEndTime": _iso(end, True),
    }, timeout=30)
    if r.status_code >= 400:
        hint = " (403 usually means the app lacks the Brand Analytics role or the seller is not brand-registered)" if r.status_code == 403 else ""
        raise RuntimeError(f"createReport HTTP {r.status_code}: {r.text[:300]}{hint}")
    report_id = r.json()["reportId"]
    say(f"  report {report_id} requested")
    doc_id = None
    for attempt in range(80):
        s = requests.get(f"{base}/reports/2021-06-30/reports/{report_id}", headers=_headers(), timeout=30).json()
        status = s.get("processingStatus")
        say(f"  {status} ({attempt + 1})")
        if status == "DONE":
            doc_id = s["reportDocumentId"]
            break
        if status in ("CANCELLED", "FATAL"):
            raise RuntimeError(f"report ended {status}")
        time.sleep(15)
    if not doc_id:
        raise RuntimeError("report not DONE after 20 minutes")
    doc = requests.get(f"{base}/reports/2021-06-30/documents/{doc_id}", headers=_headers(), timeout=30).json()
    dest = raw_path(mp["code"], period.upper(), start)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(doc["url"], stream=True, timeout=(30, 900)) as resp:
        resp.raise_for_status()
        opener = open(tmp, "wb") if doc.get("compressionAlgorithm") == "GZIP" else gzip.open(tmp, "wb", compresslevel=5)
        with opener as fh:
            for chunk in resp.iter_content(_CHUNK):
                fh.write(chunk)
    tmp.replace(dest)
    say(f"  downloaded {dest.stat().st_size / 1e6:.0f} MB → {dest}")
    return dest


# ---------------------------------------------------------------- streaming parse

def iter_json_array(path: Path, key: str = ROW_KEY) -> Iterator[dict]:
    decoder = json.JSONDecoder()
    marker = f'"{key}"'
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        buf = ""
        while True:
            chunk = fh.read(_CHUNK)
            if not chunk:
                return
            buf += chunk
            i = buf.find(marker)
            if i != -1:
                j = buf.find("[", i + len(marker))
                if j != -1:
                    buf = buf[j + 1:]
                    break
            else:
                buf = buf[-len(marker):]
        pos = 0
        while True:
            while pos < len(buf) and buf[pos] in " \t\r\n,":
                pos += 1
            if pos >= len(buf):
                chunk = fh.read(_CHUNK)
                if not chunk:
                    return
                buf, pos = chunk, 0
                continue
            if buf[pos] == "]":
                return
            try:
                obj, end = decoder.raw_decode(buf, pos)
            except json.JSONDecodeError:
                chunk = fh.read(_CHUNK)
                if not chunk:
                    return
                buf, pos = buf[pos:] + chunk, 0
                continue
            yield obj
            pos = end
            if pos > _CHUNK:
                buf, pos = buf[pos:], 0


def _f(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def pivot_rows(rows: Iterable[dict], *, keep_top: int | None = None, watch: set[str] | None = None, index_writer=None) -> tuple[list[dict], int]:
    watch = watch or set()
    pivot: dict[str, dict] = {}
    seen = 0
    for row in rows:
        seen += 1
        term = (row.get("searchTerm") or "").strip().lower()
        rank = int(row.get("searchFrequencyRank") or 0)
        if not term or rank <= 0:
            continue
        if index_writer is not None:
            index_writer(rank, term)
        if keep_top is not None and rank > keep_top and term not in watch:
            continue
        e = pivot.get(term)
        if e is None:
            e = pivot[term] = {"search_term": term[:255], "search_frequency_rank": rank, "department": row.get("departmentName") or ""}
        elif rank < e["search_frequency_rank"]:
            e["search_frequency_rank"], e["department"] = rank, row.get("departmentName") or ""
        csr = int(row.get("clickShareRank") or 0)
        if 1 <= csr <= 3 and not e.get(f"asin_{csr}"):
            e[f"asin_{csr}"] = (row.get("clickedAsin") or "")[:16]
            e[f"title_{csr}"] = (row.get("clickedItemName") or row.get("clickedTitle") or "")[:512]
            e[f"click_share_{csr}"] = _f(row.get("clickShare"))
            e[f"conversion_share_{csr}"] = _f(row.get("conversionShare"))
    return sorted(pivot.values(), key=lambda e: e["search_frequency_rank"]), seen


def parse_document(payload: dict | bytes | str) -> list[dict]:
    if isinstance(payload, (bytes, str)):
        payload = json.loads(payload)
    return pivot_rows(payload.get(ROW_KEY) or [])[0]


class _IndexWriter:
    def __init__(self, path: Path):
        self.path, self.tmp = path, path.with_suffix(path.suffix + ".part")
        self.fh = gzip.open(self.tmp, "wt", encoding="utf-8", compresslevel=5)

    def __call__(self, rank: int, term: str) -> None:
        self.fh.write(f"{rank}\t{term}\n")

    def close(self) -> Path:
        self.fh.close()
        self.tmp.replace(self.path)
        return self.path


def stream_file(path: Path, *, keep_top: int | None, watch: set[str] | None, index: Path | None) -> tuple[list[dict], int]:
    writer = _IndexWriter(index) if index else None
    try:
        return pivot_rows(iter_json_array(path), keep_top=keep_top, watch=watch, index_writer=writer)
    finally:
        if writer:
            writer.close()


# ---------------------------------------------------------------- variants + lookups

def term_variants(keyword: str) -> list[str]:
    kw = (keyword or "").strip().lower()
    if not kw:
        return []
    toks = kw.split()
    last = toks[-1]
    variants = [kw]
    if singular(last) != last:
        variants.append(" ".join(toks[:-1] + [singular(last)]))
    if not last.endswith("s"):
        variants.append(" ".join(toks[:-1] + [last + "s"]))
        if last.endswith(("sh", "ch", "x", "z")):
            variants.append(" ".join(toks[:-1] + [last + "es"]))
    elif last.endswith("y") and len(last) > 2:
        variants.append(" ".join(toks[:-1] + [last[:-1] + "ies"]))
    all_sing = " ".join(singular(t) for t in toks)
    if all_sing not in variants:
        variants.append(all_sing)
    return variants


def latest_ranks_for(conn, marketplace: str, keywords: list[str]) -> dict[str, dict]:
    """{keyword: {search_frequency_rank, matched_term, period_start, top_asins}} — plural/singular variants matched."""
    variant_map = {k.lower(): term_variants(k) for k in keywords if k}
    rows = db.ba_rows_for_terms(conn, marketplace, sorted({v for vs in variant_map.values() for v in vs}))
    out = {}
    for kw, variants in variant_map.items():
        hits = [rows[v] for v in variants if v in rows]
        if not hits:
            continue
        r = min(hits, key=lambda r: r["search_frequency_rank"])
        out[kw] = {"search_frequency_rank": r["search_frequency_rank"], "matched_term": r["search_term"], "period_start": r["period_start"],
                   "top_asins": [a for a in (r.get("asin_1"), r.get("asin_2"), r.get("asin_3")) if a]}
    return out


def lookup_index(conn, marketplace: str, keywords: list[str], *, period: str = "WEEK") -> dict[str, dict]:
    """Long-tail fallback: scan the latest rank index for the keywords, upsert hits, return latest_ranks_for()."""
    path = latest_index_path(marketplace, period)
    if path is None or not keywords:
        return {}
    wanted: set[str] = set()
    for k in keywords:
        wanted.update(term_variants(k))
    best: dict[str, int] = {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            rank_s, _, term = line.rstrip("\n").partition("\t")
            if term in wanted:
                rank = int(rank_s)
                if rank < best.get(term, 1 << 31):
                    best[term] = rank
    if not best:
        return {}
    stem = path.name.split(".")[0].split("_")
    per, start = stem[-2], stem[-1]
    db.upsert_ba_terms(conn, [{"marketplace": marketplace.upper(), "period": per, "period_start": start, "search_term": t, "search_frequency_rank": r} for t, r in best.items()])
    return latest_ranks_for(conn, marketplace, keywords)


def ingest(conn, marketplace: str, *, period: str = "WEEK", start: date | None = None, end: date | None = None,
           keep_top: int = 50_000, raw_file: Path | None = None, watch: set[str] | None = None, log=None) -> dict:
    """Request (or re-parse) the report and store top terms + watched terms. Returns counts."""
    period = period.upper()
    if start is None or end is None:
        start, end = default_period_bounds(period)
    say = log or (lambda m: None)
    path = Path(raw_file) if raw_file else request_report(marketplace, period=period, start=start, end=end, log=log)
    watch = set(watch or set())
    for k in [r["keyword"] for r in conn.execute("SELECT DISTINCT keyword FROM candidates WHERE excluded = 0").fetchall()]:
        watch.update(term_variants(k))
    rows, total = stream_file(path, keep_top=keep_top, watch=watch, index=index_path(marketplace.upper(), period, start))
    say(f"  streamed {total} rows → keeping {len(rows)} terms")
    n = db.upsert_ba_terms(conn, [{"marketplace": marketplace.upper(), "period": period, "period_start": start.isoformat(), **r} for r in rows])
    pruned = db.prune_ba_periods(conn, marketplace, period, keep=12)
    for old in sorted(config.DATA_DIR.glob(f"ba_search_terms_{marketplace.upper()}_{period}_*.json.gz"))[:-1]:
        old.unlink(missing_ok=True)
    return {"stored": n, "total_rows": total, "pruned": pruned, "raw_path": str(path), "period_start": start.isoformat(), "period_end": end.isoformat()}
