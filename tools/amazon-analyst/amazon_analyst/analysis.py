"""
LLM competitive analysis of the shortlisted competitors' listing copy —
the part of the original competitor_analysis project that turned bullet
points into a technical analysis, a summary and a product strategy.

Optional: needs OPENAI_API_KEY. Model via OPENAI_MODEL (default gpt-4o).
"""
from __future__ import annotations

import os

SUMMARY_SYSTEM = ("You are a business analyst that helps choose products to take to market. You analyze product "
                  "features from marketing copy and summarize them. Only use the data you are given.")
ANALYSIS_SYSTEM = ("You are a business analyst that helps choose products to take to market. You analyze product "
                   "features and sales signals from data and help the team decide which features to use in R&D and "
                   "design. Only use the data you are given.")


def _client():
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pip install 'amazon-analyst[llm]' (openai) to use the analysis step") from exc
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=key, organization=os.getenv("OPENAI_ORG") or None)


def _model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o")


def summarize_features(client, bullets: list[str], product_type: str) -> str:
    text = "\n".join(b for b in bullets if b and b.strip()) or "(no bullet points)"
    resp = client.chat.completions.create(
        model=_model(), temperature=0.4, max_tokens=200,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": (
                f"Product type: {product_type}\n\nProduct features:\n{text}\n\n"
                "Write ONE concise sentence summarizing the product's features. Fewest words possible. Reply with the sentence only."
            )},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def competitive_analysis(products: list[dict], *, product_type: str, keywords: list[dict] | None = None,
                         summary: dict | None = None) -> str:
    """Markdown with: Technical analysis · Market summary · Competitive strategy.
    `products` need title, price, rating, review_count, bought_past_month_min, bsr_rank, bullets."""
    client = _client()
    lines = []
    for p in products:
        feat = summarize_features(client, p.get("bullets") or [], product_type) if p.get("bullets") else "(no bullets available)"
        lines.append(
            f"- {p.get('title', '')[:90]} | price {p.get('price')} | rating {p.get('rating')} | reviews {p.get('review_count')} | "
            f"units/month floor {p.get('bought_past_month_min')} | BSR {p.get('bsr_rank')} | features: {feat}"
        )
    kw_lines = [f"- {k['keyword']} (tier {k.get('demand_tier') or '-'}, rank {k.get('search_frequency_rank')}, seed overlap {k.get('seed_overlap')})"
                for k in (keywords or [])[:25]]
    s = summary or {}
    resp = client.chat.completions.create(
        model=_model(), temperature=0.5, max_tokens=2500,
        messages=[
            {"role": "system", "content": ANALYSIS_SYSTEM},
            {"role": "user", "content": (
                f"Product type / seed keyword: {product_type}\n\n"
                f"Market floors (lower bounds from Amazon's 'bought in past month' badge): page-1 units {s.get('page1_units_min_sum')}, "
                f"page-1 revenue {s.get('page1_revenue_min_sum')}, median price {s.get('median_price')}, median rating {s.get('median_rating')}\n\n"
                f"Top competitors:\n" + "\n".join(lines) + "\n\n"
                + (f"Keyword demand (search-frequency rank: lower = more searched):\n" + "\n".join(kw_lines) + "\n\n" if kw_lines else "")
                + "Write three short sections in markdown:\n"
                  "## Technical analysis — the concrete features/specs that recur across the best sellers, and the niche ones.\n"
                  "## Market summary — price bands, who dominates, review moats, seasonality hints, and what the keyword list says about intent.\n"
                  "## Competitive strategy — a product/R&D and positioning strategy for entering, with the 5-8 keywords to build the listing around.\n"
                  "Be concise. Treat units and revenue as lower bounds. Do not invent numbers."
            )},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
