"""
amazon_analyst/keywords.py

Deterministic keyword mining over the listing copy of a research run's
products (pure — no DB, no network).

Idea: the phrases that competitors who actually sell repeat across their titles
and bullets are the phrases shoppers search for. We weight each product by its
"bought in past month" floor so a 2K+/month listing counts more than a dead
one, mine 1-3 word n-grams from its title (×2) and bullets, and throw away
stopword-bounded fragments and anything containing a brand name.

Output is a ranked list of candidate dicts; the pipeline unions it with the Ads
API reverse-ASIN recommendations and scores everything in demand_scoring.py.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Iterable

_ENGLISH_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "in", "into",
    "is", "it", "its", "of", "on", "or", "our", "that", "the", "their", "these", "this", "those",
    "to", "with", "you", "your", "yours", "we", "will", "can", "all", "any", "each", "more", "most",
    "not", "no", "also", "than", "then", "so", "such", "up", "out", "if", "when", "while", "very",
    "just", "only", "over", "under", "per", "via", "etc", "who", "what", "which", "how", "why",
    "them", "they", "he", "she", "his", "her", "him", "us", "me", "my", "i", "do", "does", "did",
    "was", "were", "been", "being", "am", "but", "about", "after", "before", "between", "both",
    "off", "own", "same", "some", "too", "other", "one", "two", "three", "four", "five", "six",
}
_LISTING_JUNK = {
    "pack", "packs", "set", "sets", "piece", "pieces", "pcs", "pc", "inch", "inches", "cm", "mm",
    "ft", "size", "sizes", "color", "colors", "colour", "colours", "new", "perfect", "great",
    "premium", "quality", "durable", "design", "designed", "feature", "features", "material",
    "materials", "lbs", "lb", "oz", "count", "ideal", "best", "easy", "high", "made", "use",
    "used", "using", "include", "includes", "included", "including", "x", "w", "h", "l", "d",
    "sturdy", "long", "lasting", "brand", "product", "products", "item", "items", "amazon",
    "free", "fast", "shipping", "day", "days", "year", "years", "warranty", "guarantee",
    "guaranteed", "satisfaction", "money", "back", "please", "note", "get", "make", "makes",
    "keep", "keeps", "add", "adds", "come", "comes", "fit", "fits", "fitting", "large", "small",
    "medium", "big", "little", "extra", "multi", "various", "different", "many", "lot", "lots",
    "need", "needs", "want", "wants", "love", "loves", "enjoy", "look", "looks", "looking",
    "provide", "provides", "offer", "offers", "help", "helps", "way", "ways", "time", "times",
    "sure", "well", "good", "better", "top", "full", "wide", "every", "everyone", "anyone",
    "friend", "friends", "family", "families", "him", "her", "mom", "dad",
    "during", "adding", "automatically", "easily", "suitable", "thoughtful", "withstand", "fading", "fade",
    "occasion", "occasions", "craftsmanship", "ensure", "ensures", "provide", "allows", "allow", "bring",
    "brings", "create", "creates", "simply", "directly", "whether", "anywhere", "without", "within",
    "along", "even", "onto", "upon", "until", "gives", "perfectly", "beautifully", "hours", "hour",
    "night", "nights", "day", "daytime", "sunlight", "charging", "charge", "charged", "turns", "turn",
    "switch", "resistant", "proof", "weatherproof", "sturdy", "detailed", "details", "detail", "touch",
    "adds", "space", "spaces", "area", "areas", "place", "places", "anyone", "someone", "smile", "smiles",
    "surprise", "birthday", "birthdays", "christmas", "holiday", "holidays", "mother", "mothers", "father",
    "fathers", "grandma", "grandpa", "wife", "husband", "lover", "lovers", "enthusiast", "enthusiasts",
}
LISTING_STOPWORDS = _ENGLISH_STOPWORDS | _LISTING_JUNK

# Real modifiers we deliberately keep even though they look generic.
_KEEP = {"gift", "gifts", "outdoor", "indoor", "kids", "women", "men", "boys", "girls", "baby", "toddler",
         "christmas", "halloween", "birthday", "mother", "mothers", "father", "fathers", "solar", "led"}
LISTING_STOPWORDS -= _KEEP

FIELD_WEIGHTS = {"title": 2.0, "bullet": 1.0, "catalog_title": 1.0}
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9']*")


def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def normalize_keyword(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace — the canonical key
    used everywhere a keyword is compared or stored."""
    text = (text or "").lower().replace("-", " ").replace("/", " ")
    return " ".join(_TOKEN_RE.findall(text)).strip()


def tokenize(text: str) -> list[str]:
    """Tokens for n-gram mining: normalized, numerics and 1-char tokens dropped."""
    out = []
    for tok in _TOKEN_RE.findall((text or "").lower().replace("-", " ").replace("/", " ")):
        tok = tok.strip("'")
        if len(tok) < 2 or tok.isdigit():
            continue
        out.append(tok)
    return out


def singular(tok: str) -> str:
    if len(tok) <= 3:
        return tok
    if tok.endswith("ies"):
        return tok[:-3] + "y"
    if tok.endswith(("ses", "xes", "shes", "ches", "zes")):
        return tok[:-2]
    if tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def _ngram_key(tokens: list[str]) -> str:
    return " ".join(singular(t) for t in tokens)


def brand_tokens(brand_names: Iterable[str], *, seed: str = "") -> set[str]:
    """Tokens that identify a brand. Tokens also present in the seed keyword
    are not treated as brand tokens (a brand literally named after the
    category must not wipe out the category term)."""
    seed_toks = {singular(t) for t in tokenize(seed)}
    out: set[str] = set()
    for name in brand_names or ():
        for tok in tokenize(name):
            s = singular(tok)
            if len(s) >= 3 and s not in LISTING_STOPWORDS and s not in seed_toks:
                out.add(s)
    return out


def product_weight(product: Any) -> float:
    units = _get(product, "bought_past_month_min") or 0
    w = 1.0 + math.log2(1.0 + units / 50.0)
    if _get(product, "sponsored") and _get(product, "organic_position") is None:
        w *= 0.7
    return w


def select_products(products: list[Any], *, top_n: int = 30) -> list[Any]:
    """Shortlisted products if any are shortlisted, else all non-excluded,
    ordered by bought-floor desc (unknown last) then position."""
    pool = [p for p in products if not _get(p, "excluded")]
    shortlisted = [p for p in pool if _get(p, "shortlisted")]
    if shortlisted:
        pool = shortlisted

    def sort_key(p):
        units = _get(p, "bought_past_month_min")
        return (0 if units is not None else 1, -(units or 0), _get(p, "position") or 10**6)

    return sorted(pool, key=sort_key)[: max(1, top_n)]


def _fields(product: Any) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    title = _get(product, "title") or ""
    if title:
        fields.append(("title", title))
    catalog_title = _get(product, "catalog_title") or ""
    if catalog_title and catalog_title.strip().lower() != title.strip().lower():
        fields.append(("catalog_title", catalog_title))
    for bullet in _get(product, "bullets") or []:
        if bullet:
            fields.append(("bullet", str(bullet)))
    return fields


def extract_candidates(
    products: list[Any],
    *,
    seed: str,
    brand_names: Iterable[str] = (),
    top_n: int = 30,
    max_candidates: int = 150,
    max_ngram: int = 3,
    min_product_count: int = 2,
) -> list[dict]:
    """Mine candidate keywords from listing copy.

    Returns dicts sorted by ngram_score desc::

        {"keyword", "ngram_score" (0-100), "product_count", "weighted_units",
         "n", "contains_seed_all", "contains_seed_any", "is_branded",
         "from_seed", "from_listings", "surface_form"}

    The seed keyword is always present (from_seed=True). Branded n-grams are
    returned with is_branded=True so the caller can store and exclude them.
    """
    seed_norm = normalize_keyword(seed)
    seed_keys = {singular(t) for t in tokenize(seed)}
    brand_toks = brand_tokens(brand_names, seed=seed)

    score: dict[str, float] = defaultdict(float)
    prod_sets: dict[str, set] = defaultdict(set)
    units_for: dict[str, int] = defaultdict(int)
    surface_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    ngram_len: dict[str, int] = {}

    for product in select_products(products, top_n=top_n):
        w = product_weight(product)
        asin = _get(product, "asin") or id(product)
        units = _get(product, "bought_past_month_min") or 0
        for field_name, text in _fields(product):
            fw = FIELD_WEIGHTS.get(field_name, 1.0)
            toks = tokenize(text)
            counts: dict[str, int] = defaultdict(int)
            surfaces: dict[str, str] = {}
            for n in range(1, max_ngram + 1):
                for i in range(0, len(toks) - n + 1):
                    gram = toks[i:i + n]
                    if gram[0] in LISTING_STOPWORDS or gram[-1] in LISTING_STOPWORDS:
                        continue
                    if n == 1 and gram[0] in LISTING_STOPWORDS:
                        continue
                    key = _ngram_key(gram)
                    counts[key] += 1
                    surfaces.setdefault(key, " ".join(gram))
                    ngram_len[key] = n
            for key, c in counts.items():
                score[key] += w * fw * min(c, 2)
                surface_counts[key][surfaces[key]] += c
                if asin not in prod_sets[key]:
                    prod_sets[key].add(asin)
                    units_for[key] += units

    rows: list[dict] = []
    for key, raw in score.items():
        toks = key.split()
        contains_all = bool(seed_keys) and seed_keys.issubset(set(toks))
        contains_any = bool(seed_keys & set(toks))
        is_branded = any(t in brand_toks for t in toks)
        product_count = len(prod_sets[key])
        if product_count < min_product_count and not contains_all and not is_branded:
            continue  # branded n-grams are kept (and excluded downstream) for visibility
        adj = raw
        if contains_all:
            adj *= 1.5
        elif contains_any:
            adj *= 1.2
        n = ngram_len.get(key, len(toks))
        if n == 1 and not contains_any:
            adj *= 0.5  # lone adjectives / nouns ("outdoor", "hours") are rarely the query
        elif n == 2:
            adj *= 1.3
        elif n >= 3:
            adj *= 1.5
        surface = max(surface_counts[key].items(), key=lambda kv: kv[1])[0]
        rows.append({
            "keyword": normalize_keyword(surface),
            "key": key,
            "raw_score": adj,
            "product_count": product_count,
            "weighted_units": int(units_for[key]),
            "n": n,
            "contains_seed_all": contains_all,
            "contains_seed_any": contains_any,
            "is_branded": is_branded,
            "from_seed": False,
            "from_listings": True,
        })

    max_score = max((r["raw_score"] for r in rows), default=0.0) or 1.0
    for r in rows:
        r["ngram_score"] = round(100.0 * r["raw_score"] / max_score, 2)
        del r["raw_score"]

    rows.sort(key=lambda r: (-r["ngram_score"], r["keyword"]))
    # dedupe on the display keyword (two singular-keys can map to one surface form)
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in rows:
        if r["keyword"] in seen or not r["keyword"]:
            continue
        seen.add(r["keyword"])
        deduped.append(r)

    non_branded = [r for r in deduped if not r["is_branded"]][:max_candidates]
    branded = [r for r in deduped if r["is_branded"]][: max(10, max_candidates // 5)]
    out = non_branded + branded

    # The seed is the research target by definition: it always leads the list
    # with the top listing score, whether or not the mining surfaced it.
    seed_row = next((r for r in out if r["keyword"] == seed_norm), None)
    if seed_row is not None:
        out.remove(seed_row)
        seed_row.update({"from_seed": True, "ngram_score": 100.0})
    elif seed_norm:
        seed_row = {
            "keyword": seed_norm, "key": _ngram_key(tokenize(seed_norm)), "ngram_score": 100.0,
            "product_count": sum(1 for p in products if seed_keys and seed_keys.issubset(
                {singular(t) for t in tokenize(_get(p, "title") or "")})),
            "weighted_units": 0, "n": len(seed_keys), "contains_seed_all": True,
            "contains_seed_any": True, "is_branded": False, "from_seed": True, "from_listings": False,
        }
    if seed_row is not None:
        out.insert(0, seed_row)
    return out
