"""SQLite storage. One `run` per (keyword, marketplace, time); products, keyword
candidates and Brand Analytics terms hang off it. Rows are plain dicts."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    marketplace TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    pages_requested INTEGER DEFAULT 3,
    pages_scraped INTEGER DEFAULT 0,
    products_found INTEGER DEFAULT 0,
    sponsored_count INTEGER DEFAULT 0,
    captcha_detected INTEGER DEFAULT 0,
    error TEXT DEFAULT '',
    summary TEXT DEFAULT '{}',
    analysis TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS products (
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    asin TEXT NOT NULL,
    position INTEGER, page INTEGER, page_position INTEGER, organic_position INTEGER,
    sponsored INTEGER DEFAULT 0,
    title TEXT DEFAULT '', price REAL, currency TEXT DEFAULT '', rating REAL, review_count INTEGER,
    bought_past_month_min INTEGER, bought_past_month_raw TEXT DEFAULT '', badge TEXT DEFAULT '',
    image_url TEXT DEFAULT '', is_prime INTEGER DEFAULT 0,
    brand_name TEXT DEFAULT '', catalog_title TEXT DEFAULT '', bsr_category TEXT DEFAULT '', bsr_rank INTEGER,
    bsr_ranks TEXT DEFAULT '[]', bullets TEXT DEFAULT '[]', enriched_from TEXT DEFAULT '', enrich_error TEXT DEFAULT '',
    shortlisted INTEGER DEFAULT 0, excluded INTEGER DEFAULT 0, note TEXT DEFAULT '',
    PRIMARY KEY (run_id, asin)
);
CREATE INDEX IF NOT EXISTS idx_products_asin ON products(asin);
CREATE TABLE IF NOT EXISTS candidates (
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    from_seed INTEGER DEFAULT 0, from_listings INTEGER DEFAULT 0, from_ads INTEGER DEFAULT 0, from_ba INTEGER DEFAULT 0,
    seed_overlap TEXT DEFAULT '', is_branded INTEGER DEFAULT 0, excluded INTEGER DEFAULT 0,
    ngram_score REAL, product_count INTEGER DEFAULT 0, weighted_units INTEGER DEFAULT 0,
    rec_rank INTEGER, rec_sort TEXT DEFAULT '', impression_rank INTEGER, impression_share REAL,
    bid_low REAL, bid_median REAL, bid_high REAL,
    search_frequency_rank INTEGER, ba_matched_term TEXT DEFAULT '',
    our_impressions INTEGER, est_total_ad_impressions INTEGER,
    demand_score REAL, demand_tier TEXT DEFAULT '', confidence REAL, competition_score REAL, sources TEXT DEFAULT '[]',
    PRIMARY KEY (run_id, keyword)
);
CREATE TABLE IF NOT EXISTS ba_terms (
    marketplace TEXT NOT NULL, period TEXT NOT NULL, period_start TEXT NOT NULL,
    search_term TEXT NOT NULL, search_frequency_rank INTEGER NOT NULL, department TEXT DEFAULT '',
    asin_1 TEXT DEFAULT '', title_1 TEXT DEFAULT '', click_share_1 REAL, conversion_share_1 REAL,
    asin_2 TEXT DEFAULT '', title_2 TEXT DEFAULT '', click_share_2 REAL, conversion_share_2 REAL,
    asin_3 TEXT DEFAULT '', title_3 TEXT DEFAULT '', click_share_3 REAL, conversion_share_3 REAL,
    PRIMARY KEY (marketplace, period, period_start, search_term)
);
CREATE INDEX IF NOT EXISTS idx_ba_terms_term ON ba_terms(marketplace, search_term);
"""

_JSON_COLS = {"bsr_ranks", "bullets", "sources", "summary"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    config.ensure_dirs()
    conn = sqlite3.connect(str(path or config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for k in _JSON_COLS & d.keys():
        try:
            d[k] = json.loads(d[k]) if isinstance(d[k], str) else d[k]
        except ValueError:
            pass
    return d


def _prep(values: dict) -> dict:
    out = {}
    for k, v in values.items():
        if k in _JSON_COLS and not isinstance(v, str):
            v = json.dumps(v, default=str)
        elif isinstance(v, bool):
            v = int(v)
        out[k] = v
    return out


def _upsert(conn: sqlite3.Connection, table: str, keys: dict, values: dict) -> None:
    data = _prep({**keys, **values})
    cols = ", ".join(data)
    marks = ", ".join("?" for _ in data)
    updates = ", ".join(f"{c}=excluded.{c}" for c in data if c not in keys)
    sql = f"INSERT INTO {table} ({cols}) VALUES ({marks})"
    if updates:
        sql += f" ON CONFLICT({', '.join(keys)}) DO UPDATE SET {updates}"
    conn.execute(sql, list(data.values()))


# ---------------------------------------------------------------- runs

def create_run(conn, *, keyword: str, marketplace: str, pages: int) -> int:
    cur = conn.execute(
        "INSERT INTO runs (keyword, marketplace, created_at, pages_requested) VALUES (?, ?, ?, ?)",
        (keyword.strip(), marketplace.upper(), now_iso(), pages),
    )
    return int(cur.lastrowid)


def get_run(conn, run_id: int) -> dict | None:
    return _row(conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone())


def latest_run(conn, keyword: str | None = None) -> dict | None:
    if keyword:
        r = conn.execute("SELECT * FROM runs WHERE lower(keyword) = lower(?) ORDER BY id DESC LIMIT 1", (keyword.strip(),)).fetchone()
    else:
        r = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    return _row(r)


def update_run(conn, run_id: int, **values) -> None:
    data = _prep(values)
    sets = ", ".join(f"{k} = ?" for k in data)
    conn.execute(f"UPDATE runs SET {sets} WHERE id = ?", [*data.values(), run_id])


def list_runs(conn, *, keyword: str | None = None, limit: int = 20) -> list[dict]:
    if keyword:
        rows = conn.execute("SELECT * FROM runs WHERE lower(keyword) = lower(?) ORDER BY id DESC LIMIT ?", (keyword.strip(), limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r) for r in rows]


# ---------------------------------------------------------------- products

def replace_products(conn, run_id: int, products: Iterable[dict]) -> int:
    conn.execute("DELETE FROM products WHERE run_id = ?", (run_id,))
    n = 0
    for p in products:
        _upsert(conn, "products", {"run_id": run_id, "asin": p["asin"]}, {k: v for k, v in p.items() if k != "asin"})
        n += 1
    return n


def update_product(conn, run_id: int, asin: str, **values) -> None:
    _upsert(conn, "products", {"run_id": run_id, "asin": asin}, values)


def list_products(conn, run_id: int, *, include_excluded: bool = True) -> list[dict]:
    sql = "SELECT * FROM products WHERE run_id = ?" + ("" if include_excluded else " AND excluded = 0") + " ORDER BY position"
    return [_row(r) for r in conn.execute(sql, (run_id,)).fetchall()]


def product_history(conn, asin: str) -> list[dict]:
    """Every sighting of an ASIN across runs — the basis for tracking a competitor over time."""
    rows = conn.execute(
        "SELECT r.id AS run_id, r.keyword, r.marketplace, r.created_at, p.position, p.organic_position, p.sponsored, p.price, "
        "p.rating, p.review_count, p.bought_past_month_min, p.bsr_rank, p.bsr_category, p.title FROM products p JOIN runs r ON r.id = p.run_id "
        "WHERE p.asin = ? ORDER BY r.created_at", (asin.upper(),),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- candidates

def upsert_candidate(conn, run_id: int, keyword: str, **values) -> None:
    _upsert(conn, "candidates", {"run_id": run_id, "keyword": keyword}, values)


def get_candidate(conn, run_id: int, keyword: str) -> dict | None:
    return _row(conn.execute("SELECT * FROM candidates WHERE run_id = ? AND keyword = ?", (run_id, keyword)).fetchone())


def list_candidates(conn, run_id: int, *, include_excluded: bool = False, seed_overlap: str = "") -> list[dict]:
    sql = "SELECT * FROM candidates WHERE run_id = ?"
    args: list[Any] = [run_id]
    if not include_excluded:
        sql += " AND excluded = 0"
    if seed_overlap:
        sql += " AND seed_overlap = ?"
        args.append(seed_overlap)
    sql += " ORDER BY demand_score DESC, keyword"
    return [_row(r) for r in conn.execute(sql, args).fetchall()]


def delete_candidates(conn, run_id: int) -> None:
    conn.execute("DELETE FROM candidates WHERE run_id = ?", (run_id,))


# ---------------------------------------------------------------- brand analytics

def upsert_ba_terms(conn, rows: Iterable[dict]) -> int:
    n = 0
    for r in rows:
        keys = {"marketplace": r["marketplace"], "period": r["period"], "period_start": r["period_start"], "search_term": r["search_term"]}
        _upsert(conn, "ba_terms", keys, {k: v for k, v in r.items() if k not in keys})
        n += 1
    return n


def ba_periods(conn, marketplace: str, period: str) -> list[str]:
    rows = conn.execute("SELECT DISTINCT period_start FROM ba_terms WHERE marketplace = ? AND period = ? ORDER BY period_start DESC",
                        (marketplace.upper(), period.upper())).fetchall()
    return [r[0] for r in rows]


def prune_ba_periods(conn, marketplace: str, period: str, keep: int = 12) -> int:
    starts = ba_periods(conn, marketplace, period)
    if len(starts) <= keep:
        return 0
    cutoff = starts[keep - 1]
    cur = conn.execute("DELETE FROM ba_terms WHERE marketplace = ? AND period = ? AND period_start < ?", (marketplace.upper(), period.upper(), cutoff))
    return cur.rowcount


def ba_rows_for_terms(conn, marketplace: str, terms: list[str]) -> dict[str, dict]:
    """Most recent row per exact term."""
    out: dict[str, dict] = {}
    if not terms:
        return out
    for i in range(0, len(terms), 500):
        chunk = terms[i:i + 500]
        marks = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"SELECT * FROM ba_terms WHERE marketplace = ? AND search_term IN ({marks}) ORDER BY search_term, period_start DESC",
            [marketplace.upper(), *chunk],
        ).fetchall()
        for r in rows:
            out.setdefault(r["search_term"], dict(r))
    return out
