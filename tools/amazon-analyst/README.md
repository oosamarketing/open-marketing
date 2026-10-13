# amazon-analyst

Free Amazon product, keyword and competitor research from your terminal. It answers the three questions people pay Helium 10 or Jungle Scout for:

1. **What actually sells for a keyword?** Scrape the first few search-result pages and read Amazon's own *"N+ bought in past month"* badge, price, rating and reviews for every listing. Multiply floor × price and you have a gross **units and revenue floor per competitor and per page**.
2. **What keywords does this market run on?** Mine the top listings' titles and bullets, add Amazon's own keyword recommendations for the competitor ASINs (a free "reverse ASIN" lookup through the Ads API), and rank everything by **Brand Analytics search-frequency rank** — Amazon's official, marketplace-wide ranking of every search term.
3. **What do the best sellers have in common?** An optional LLM pass turns the competitors' bullet points and sales signals into a technical analysis, a market summary and a competitive strategy.

Every number is labelled for what it is. There is no invented "search volume" and no modelled "sales estimate": units are Amazon's bucketed floors, demand is a rank, and the score that blends them carries a **confidence** telling you how much signal was actually present.

> **Research use only.** Amazon's Conditions of Use prohibit automated data collection. This tool loads a handful of search-result pages per run, slowly, exactly the way you would in a browser, and stops at the first captcha (it never solves or bypasses one). Everything else comes from Amazon's official APIs under your own seller authorization. Keep runs small and infrequent, don't build a crawler out of it, and don't resell or republish scraped data.

## Install

```bash
cd tools/amazon-analyst      # in the Open Marketing toolkit; or use your own venv
source ../../.venv/bin/activate
pip install -e '.[llm]'          # drop [llm] if you don't want the OpenAI analysis step
playwright install firefox
cp .env.example .env            # optional — see "Unlocking more signals"
amazon-analyst status
```

Works with **nothing configured**: search-page floors, listing-copy keyword mining and reports. Each credential block in `.env` unlocks one more official signal.

## Quick start

```bash
# One command: search → enrich → keywords → report
amazon-analyst run "black cat statue" --pages 3

# Or step by step
amazon-analyst search "black cat statue" --pages 3     # creates run #N, prints the competitor table
amazon-analyst enrich --run N                          # brand / Best Sellers Rank / bullets
amazon-analyst shortlist --run N B0XXXXXXXX B0YYYYYYYY # optional: name the real competitors
amazon-analyst keywords --run N                        # mine + score keywords
amazon-analyst analyze --run N                         # LLM competitive analysis (OPENAI_API_KEY)
amazon-analyst report --run N                          # markdown → output/black-cat-statue/<date>_runN.md
```

Sample output of `search`:

```
  pos ASIN        units/mo   price   rev/mo reviews      BSR  title
    7 B0FG2X72BT       100   15.92    1,592     525  140,425  Cuayaes Black Cat Memorial Gifts for Women, Resin Cat Figurine
    9 B0GKCYFX41       100   24.99    2,499      55   70,155  Gothic Black Cat Lamp with Tealight Candle Holder Cat Statue
   24 B0GZVYKNDK       100   15.99    1,599     198   35,962  DoubleFill 3 Pcs Halloween Figurine Tabletop Decor Black Cat
  ...
  page-1 floors: 3950 units / 62,160 revenue per month (badge on 19 of 47 organic listings; lower bounds)
```

## Tracking sales, keywords and competitors over time

Everything is stored in a local SQLite database (`data/amazon_analyst.sqlite3`), so a keyword becomes a time series simply by running it again:

```bash
amazon-analyst search "black cat statue"   # run this weekly (a cron line is fine — it is one search, a few pages)
amazon-analyst track "black cat statue"    # page-1 units / revenue floors and median price per run
amazon-analyst history B0FG2X72BT          # one competitor: position, price, reviews, units floor, BSR across every run
amazon-analyst runs                         # everything you have researched
```

Keep the cadence gentle: one run per keyword per week is plenty and stays well inside "a person looking at Amazon".

## What each number means

| Field | What it is | How to read it |
|---|---|---|
| `units/mo` | Floor parsed from Amazon's bucketed badge (50+, 100+, 1K+, …). Blank when Amazon shows no badge — roughly below 50 units a month. | "at least N units a month". Never "sells N". |
| `rev/mo` | units floor × current retail price | gross revenue floor |
| `page-1 floors` | Sum of the above over organic page-1 listings | how big the front page is, as a lower bound |
| `BSR` | Best Sellers Rank in the listing's display category (SP-API catalog, or the product page) | lower is better; compare within one category |
| `SFR` (search-frequency rank) | Brand Analytics: the term's rank among **all** searches on the marketplace that week | #66 is huge, #400,000 is a long-tail query |
| `rec` | Position in Amazon's ranked keyword recommendations for the competitor ASIN set | Amazon's own view of relevance |
| `IS%` / impression rank | Your share of ad impressions on the term and your rank among advertisers (Ads API) | only meaningful if you advertise |
| `bid` | Amazon's suggested bid, median of the range | **competition**, not demand |
| `score` / `tier` | Weighted blend of rank, recommendation, impression signals, unit floors and listing prevalence, divided by max(present weight, 0.35) | A ≥ 70, B ≥ 45, C ≥ 25, else D |
| `conf` | Share of the signal weight that was actually present | 0.10 = listing copy only; 0.45 = Brand Analytics only; 1.0 = everything |
| seed overlap | On-topic (contains the whole seed) / partial / related | high-demand *related* terms are category demand, not your product's |

## Unlocking more signals

### Selling Partner API — catalog + Brand Analytics (free with a seller account)

In Seller Central go to **Apps & Services → Develop apps**, create a private app (no approval process for private apps), self-authorize it and copy the LWA client id, client secret and refresh token into `.env`:

```
SPAPI_LWA_CLIENT_ID=…
SPAPI_LWA_CLIENT_SECRET=…
SPAPI_REFRESH_TOKEN=…
```

- `enrich` now uses the **Catalog Items API** for brand, BSR and bullet points of *any* ASIN, batched 20 at a time, instead of loading product pages.
- If your brand is enrolled in **Brand Registry** and you tick the *Brand Analytics* role on the app, `ba-ingest` pulls the **Top Search Terms** report — every search term on the marketplace ranked by frequency, with the three most-clicked ASINs:

```bash
amazon-analyst ba-ingest --marketplace US --period WEEK   # ~3-5 minutes; the US weekly file is ~500 MB and 8M rows, streamed
amazon-analyst demand "black cat statue" "cat figurine"  # look ranks up directly
```

Only the top 50,000 terms plus anything you have researched are stored (12 weeks retained); the full file is also written as a compact `rank<TAB>term` index so long-tail lookups still work. This is the same underlying data the paid tools model their "search volume" from.

### Amazon Ads API — keyword recommendations and bids

Needs an approved Ads API developer application and a profile you can access (your own advertising account, or one you manage):

```
ADS_LWA_CLIENT_ID=…
ADS_LWA_CLIENT_SECRET=…
ADS_REFRESH_TOKEN=…
ADS_PROFILE_ID=…
ADS_REGION=NA
```

`keywords` then adds Amazon's ranked suggestions for the competitor ASIN set (reverse ASIN), your impression share and rank on each, and suggested bid ranges; `recs B0A B0B` does an ad-hoc lookup. Offered in US, CA, UK, DE, FR, ES, IN, JP.

### LLM competitive analysis

```
OPENAI_API_KEY=sk-…
OPENAI_MODEL=gpt-4o
```

`analyze` summarizes each top competitor's bullets, then writes a technical analysis, market summary and competitive strategy that names the keywords to build a listing around. It is appended to the report.

## How honest is this compared with a paid tool?

Paid tools show a **search volume** per keyword and a **sales estimate** per listing. Neither exists in any Amazon API. Volume is modelled from the same search-frequency rank you get here; sales are modelled from BSR with a per-category curve fitted on their customers' data, plus the same badge you get here. Their own published accuracy is roughly two-thirds of estimates within 20 percent of actual.

What this tool gives you instead is the raw, official material: the floors, the rank, the recommendations, the bids, and the BSR — labelled, with a confidence, and yours to keep. If you sell on Amazon you can fit your own BSR-to-units curve from your real sales in the categories you know; that is the one thing a paid tool adds, and it is more accurate when it comes from your own numbers.

## Limits and etiquette

- Search pages: at most 7 per run (default 3), 4–9 s between pages, one Firefox session per run, warm-up on the storefront, one retry on Amazon's generic error page, hard stop on a captcha (the page is saved under `data/dumps/` for you to look at).
- Product pages (only without SP-API creds): at most 25 per run, 5–10 s apart.
- Don't run many keywords back to back; don't schedule anything more than weekly; don't use this from a datacenter IP.
- Amazon changes its HTML. If a run parses zero products the page is dumped to `data/dumps/empty_*.html`; update the selectors in `search_scraper.py` and the tests in `tests/`.

## Layout

```
amazon_analyst/
  cli.py              commands
  pipeline.py         search → enrich → keywords → analyze → report; summaries; tracking
  search_scraper.py   Playwright Firefox search pages + pure bs4 parser
  product_page.py     optional product-page reader (fallback when no SP-API)
  catalog.py          SP-API Catalog Items (brand, BSR, bullets)
  brand_analytics.py  SP-API Top Search Terms report, streamed; rank index; variant matching
  ads_api.py          Ads API keyword recommendations v5 + bid recommendations
  keywords.py         listing-copy n-gram mining (pure)
  scoring.py          demand score / tier / confidence (pure)
  analysis.py         OpenAI competitive analysis
  report.py           markdown report
  db.py               SQLite schema + helpers
tests/                pytest, with saved-HTML fixtures
```

Part of [Open Marketing](https://github.com/oosamarketing/open-marketing), OOSA's collection of free marketing tools.

MIT licensed. Built from the market-research module of an agency's internal app plus an older Selenium + ChatGPT competitor-analysis script; this is the standalone, framework-free version.
