"""amazon-analyst command line. `amazon-analyst --help` lists every command."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from . import __version__, brand_analytics, config, db, pipeline


def say(msg: str) -> None:
    print(msg, flush=True)


def _run_id(conn, args) -> int:
    if getattr(args, "run", None):
        return int(args.run)
    latest = db.latest_run(conn)
    if not latest:
        sys.exit("no runs yet — start with: amazon-analyst search \"your keyword\"")
    return latest["id"]


def _fmt(v, width=0):
    s = "" if v is None else (f"{v:,.0f}" if isinstance(v, float) and v >= 100 else str(v))
    return s.rjust(width) if width else s


def print_products(conn, run_id: int, limit: int = 15) -> None:
    rows = [p for p in pipeline.products_with_revenue(conn, run_id) if p["organic_position"] is not None and not p["excluded"]]
    rows.sort(key=lambda p: (-(p["revenue_min"] or 0), p["position"]))
    say(f"\n  {'pos':>3} {'ASIN':<11} {'units/mo':>8} {'price':>7} {'rev/mo':>8} {'reviews':>7} {'BSR':>8}  title")
    for p in rows[:limit]:
        say(f"  {p['position']:>3} {p['asin']:<11} {_fmt(p['bought_past_month_min'], 8)} {_fmt(p['price'], 7)} {_fmt(p['revenue_min'], 8)} "
            f"{_fmt(p['review_count'], 7)} {_fmt(p['bsr_rank'], 8)}  {p['title'][:60]}")
    s = db.get_run(conn, run_id).get("summary") or {}
    say(f"\n  page-1 floors: {s.get('page1_units_min_sum')} units / {_fmt(s.get('page1_revenue_min_sum'))} revenue per month "
        f"(badge on {s.get('page1_units_known_count')} of {s.get('page1_organic_count')} organic listings; lower bounds)")


def print_keywords(conn, run_id: int, limit: int = 12) -> None:
    for label, overlap in (("On-topic", "all"), ("Partial", "any"), ("Related", "none")):
        rows = db.list_candidates(conn, run_id, seed_overlap=overlap)
        if not rows:
            continue
        say(f"\n  {label} keywords")
        say(f"  {'tier':<4} {'score':>5} {'conf':>4} {'SFR':>8} {'rec':>4} {'IS%':>5} {'bid':>5}  keyword  [sources]")
        for c in rows[:limit]:
            say(f"  {c['demand_tier'] or '-':<4} {_fmt(c['demand_score'], 5)} {_fmt(c['confidence'], 4)} {_fmt(c['search_frequency_rank'], 8)} "
                f"{_fmt(c['rec_rank'], 4)} {_fmt(c['impression_share'], 5)} {_fmt(c['bid_median'], 5)}  {c['keyword']}  {c['sources']}")


def cmd_status(args):
    say(f"amazon-analyst {__version__}")
    say(f"  data dir:   {config.DATA_DIR}")
    say(f"  output dir: {config.OUTPUT_DIR}")
    say(f"  SP-API (catalog + Brand Analytics): {'configured' if config.spapi_configured() else 'not configured — enrichment falls back to product pages, no search-frequency ranks'}")
    say(f"  Ads API (keyword recs + bids):     {'configured' if config.ads_configured() else 'not configured — no Amazon keyword recommendations'}")
    say(f"  LLM analysis (OpenAI):             {'configured' if config.llm_configured() else 'not configured — `analyze` unavailable'}")
    with db.connect() as conn:
        for mp in sorted({r["marketplace"] for r in db.list_runs(conn, limit=200)} | {"US"}):
            periods = db.ba_periods(conn, mp, "WEEK")
            say(f"  Brand Analytics {mp}: {len(periods)} weekly period(s) stored" + (f", latest {periods[0]}" if periods else ""))


def cmd_search(args):
    with db.connect() as conn:
        run = pipeline.search(conn, args.keyword, marketplace=args.marketplace, pages=args.pages, log=say)
        if run["status"] == "failed":
            sys.exit(1)
        print_products(conn, run["id"])
        say(f"\nnext: amazon-analyst enrich --run {run['id']}   |   amazon-analyst keywords --run {run['id']}   |   amazon-analyst report --run {run['id']}")


def cmd_enrich(args):
    with db.connect() as conn:
        rid = _run_id(conn, args)
        pipeline.enrich(conn, rid, source=args.source, limit=args.limit, force=args.force, log=say)
        print_products(conn, rid)


def cmd_keywords(args):
    with db.connect() as conn:
        rid = _run_id(conn, args)
        pipeline.keywords(conn, rid, top_n=args.top_n, use_ads=False if args.no_ads else None, log=say)
        print_keywords(conn, rid)


def cmd_analyze(args):
    with db.connect() as conn:
        rid = _run_id(conn, args)
        say(pipeline.analyze(conn, rid, top_n=args.top_n, log=say))


def cmd_report(args):
    with db.connect() as conn:
        pipeline.report(conn, _run_id(conn, args), log=say)


def cmd_run(args):
    with db.connect() as conn:
        run = pipeline.search(conn, args.keyword, marketplace=args.marketplace, pages=args.pages, log=say)
        if run["status"] == "failed":
            sys.exit(1)
        if not args.no_enrich:
            pipeline.enrich(conn, run["id"], source=args.enrich_source, log=say)
        print_products(conn, run["id"])
        if not args.no_keywords:
            pipeline.keywords(conn, run["id"], top_n=args.top_n, use_ads=False if args.no_ads else None, log=say)
            print_keywords(conn, run["id"])
        if args.analyze:
            if not config.llm_configured():
                say("  OPENAI_API_KEY not set — skipping analysis")
            else:
                pipeline.analyze(conn, run["id"], log=say)
        if not args.no_report:
            pipeline.report(conn, run["id"], log=say)


def cmd_runs(args):
    with db.connect() as conn:
        say(f"  {'id':>4} {'date':<10} {'mkt':<3} {'status':<13} {'prods':>5} {'p1 units':>8} {'p1 rev':>9}  keyword")
        for r in db.list_runs(conn, keyword=args.keyword, limit=args.limit):
            s = r.get("summary") or {}
            say(f"  {r['id']:>4} {r['created_at'][:10]:<10} {r['marketplace']:<3} {r['status']:<13} {r['products_found']:>5} "
                f"{_fmt(s.get('page1_units_min_sum'), 8)} {_fmt(s.get('page1_revenue_min_sum'), 9)}  {r['keyword']}")


def cmd_track(args):
    with db.connect() as conn:
        rows = pipeline.track(conn, args.keyword, limit=args.limit)
        if not rows:
            sys.exit(f"no runs for {args.keyword!r}")
        say(f"  {'date':<10} {'run':>4} {'prods':>5} {'p1 units':>8} {'p1 rev':>9} {'all units':>9} {'med price':>9}  top seller")
        for r in rows:
            say(f"  {r['date']:<10} {r['run_id']:>4} {r['products']:>5} {_fmt(r['page1_units_min_sum'], 8)} {_fmt(r['page1_revenue_min_sum'], 9)} "
                f"{_fmt(r['all_pages_units_min_sum'], 9)} {_fmt(r['median_price'], 9)}  {r['top_seller'] or ''}")
        say("\nRe-run `amazon-analyst search` for the same keyword weekly to build this history; `amazon-analyst history <ASIN>` follows one competitor.")


def cmd_history(args):
    with db.connect() as conn:
        rows = db.product_history(conn, args.asin)
        if not rows:
            sys.exit(f"no sightings of {args.asin}")
        say(f"  {'date':<10} {'keyword':<28} {'pos':>4} {'price':>7} {'rating':>6} {'reviews':>7} {'units/mo':>8} {'BSR':>8}")
        for r in rows:
            say(f"  {r['created_at'][:10]:<10} {r['keyword'][:28]:<28} {_fmt(r['organic_position'] or r['position'], 4)} {_fmt(r['price'], 7)} "
                f"{_fmt(r['rating'], 6)} {_fmt(r['review_count'], 7)} {_fmt(r['bought_past_month_min'], 8)} {_fmt(r['bsr_rank'], 8)}")


def cmd_shortlist(args):
    with db.connect() as conn:
        rid = _run_id(conn, args)
        n = pipeline.shortlist(conn, rid, args.asins, exclude=args.exclude, note=args.note)
        say(f"  {'excluded' if args.exclude else 'shortlisted'} {n} product(s) on run #{rid}; re-run `keywords --run {rid}` to score on the shortlist")


def cmd_ba_ingest(args):
    if not config.spapi_configured() and not args.from_file:
        sys.exit("SP-API credentials not configured (SPAPI_LWA_CLIENT_ID / SECRET / REFRESH_TOKEN)")
    with db.connect() as conn:
        start = date.fromisoformat(args.start) if args.start else None
        end = date.fromisoformat(args.end) if args.end else None
        res = brand_analytics.ingest(conn, args.marketplace, period=args.period, start=start, end=end, keep_top=args.keep_top,
                                     raw_file=args.from_file, log=say)
        say(json.dumps(res, indent=2))


def cmd_recs(args):
    if not config.ads_configured():
        sys.exit("Ads API credentials not configured (ADS_LWA_CLIENT_ID / SECRET / REFRESH_TOKEN / ADS_PROFILE_ID)")
    from . import ads_api
    items, err = ads_api.keyword_recommendations(args.asins, marketplace=args.marketplace, sort=args.sort, max_recommendations=args.max)
    if err:
        sys.exit(err)
    say(f"  {'#':>3} {'imp rank':>8} {'IS%':>6} {'bid':>6}  keyword")
    for it in items:
        bid = next((b for b in it["bid_info"] if b["match_type"] == "EXACT"), it["bid_info"][0] if it["bid_info"] else None)
        say(f"  {it['rank']:>3} {_fmt(it['impression_rank'], 8)} {_fmt(it['impression_share'], 6)} {_fmt(bid and bid['median'], 6)}  {it['keyword']}")


def cmd_demand(args):
    with db.connect() as conn:
        ranks = brand_analytics.latest_ranks_for(conn, args.marketplace, args.keywords)
        missing = [k for k in args.keywords if k.lower() not in ranks]
        if missing and brand_analytics.latest_index_path(args.marketplace):
            ranks.update(brand_analytics.lookup_index(conn, args.marketplace, missing))
        say(f"  {'search-freq rank':>16}  {'matched term':<30} {'period':<10} keyword")
        for k in args.keywords:
            r = ranks.get(k.lower())
            say(f"  {_fmt(r and r['search_frequency_rank'], 16)}  {(r or {}).get('matched_term', '') :<30} {(r or {}).get('period_start', '') :<10} {k}")
        if not ranks:
            say("  no Brand Analytics data yet — run `amazon-analyst ba-ingest`")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="amazon-analyst", description="Free Amazon product, keyword and competitor research. Research use only.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="show which integrations are configured and what data is stored"); s.set_defaults(fn=cmd_status)

    s = sub.add_parser("search", help="scrape the first pages of search results into a new run")
    s.add_argument("keyword"); s.add_argument("--marketplace", default="US"); s.add_argument("--pages", type=int, default=3); s.set_defaults(fn=cmd_search)

    s = sub.add_parser("enrich", help="add brand / BSR / bullets (SP-API catalog, or product pages as a slow fallback)")
    s.add_argument("--run", type=int); s.add_argument("--source", choices=["auto", "sp-api", "page", "none"], default="auto")
    s.add_argument("--limit", type=int); s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_enrich)

    s = sub.add_parser("keywords", help="mine + score keyword candidates for a run")
    s.add_argument("--run", type=int); s.add_argument("--top-n", type=int, default=30); s.add_argument("--no-ads", action="store_true"); s.set_defaults(fn=cmd_keywords)

    s = sub.add_parser("analyze", help="LLM competitive analysis of the top competitors (needs OPENAI_API_KEY)")
    s.add_argument("--run", type=int); s.add_argument("--top-n", type=int, default=12); s.set_defaults(fn=cmd_analyze)

    s = sub.add_parser("report", help="write the markdown report for a run"); s.add_argument("--run", type=int); s.set_defaults(fn=cmd_report)

    s = sub.add_parser("run", help="search → enrich → keywords → (analyze) → report in one go")
    s.add_argument("keyword"); s.add_argument("--marketplace", default="US"); s.add_argument("--pages", type=int, default=3)
    s.add_argument("--no-enrich", action="store_true"); s.add_argument("--enrich-source", choices=["auto", "sp-api", "page", "none"], default="auto")
    s.add_argument("--no-keywords", action="store_true"); s.add_argument("--no-ads", action="store_true"); s.add_argument("--top-n", type=int, default=30)
    s.add_argument("--analyze", action="store_true"); s.add_argument("--no-report", action="store_true"); s.set_defaults(fn=cmd_run)

    s = sub.add_parser("runs", help="list runs"); s.add_argument("--keyword"); s.add_argument("--limit", type=int, default=20); s.set_defaults(fn=cmd_runs)
    s = sub.add_parser("track", help="floors for one keyword across runs over time"); s.add_argument("keyword"); s.add_argument("--limit", type=int, default=12); s.set_defaults(fn=cmd_track)
    s = sub.add_parser("history", help="one ASIN across every run it appeared in"); s.add_argument("asin"); s.set_defaults(fn=cmd_history)

    s = sub.add_parser("shortlist", help="mark products as the competitor set (or exclude them)")
    s.add_argument("asins", nargs="+"); s.add_argument("--run", type=int); s.add_argument("--exclude", action="store_true"); s.add_argument("--note", default=""); s.set_defaults(fn=cmd_shortlist)

    s = sub.add_parser("ba-ingest", help="ingest the Brand Analytics Top Search Terms report (needs SP-API + Brand Registry)")
    s.add_argument("--marketplace", default="US"); s.add_argument("--period", default="WEEK", choices=["DAY", "WEEK", "MONTH", "QUARTER"])
    s.add_argument("--start"); s.add_argument("--end"); s.add_argument("--keep-top", type=int, default=50_000); s.add_argument("--from-file"); s.set_defaults(fn=cmd_ba_ingest)

    s = sub.add_parser("recs", help="Amazon's keyword recommendations for ASINs (reverse ASIN; needs Ads API)")
    s.add_argument("asins", nargs="+"); s.add_argument("--marketplace", default="US"); s.add_argument("--sort", default="CLICKS", choices=["CLICKS", "CONVERSIONS", "DEFAULT"])
    s.add_argument("--max", type=int, default=100); s.set_defaults(fn=cmd_recs)

    s = sub.add_parser("demand", help="Brand Analytics search-frequency rank for keywords"); s.add_argument("keywords", nargs="+"); s.add_argument("--marketplace", default="US"); s.set_defaults(fn=cmd_demand)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
