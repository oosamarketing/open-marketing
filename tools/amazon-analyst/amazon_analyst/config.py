"""Environment, paths and marketplace tables. Everything API-backed is optional."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("AMAZON_ANALYST_DATA_DIR", "data")).resolve()
OUTPUT_DIR = Path(os.getenv("AMAZON_ANALYST_OUTPUT_DIR", "output")).resolve()
DB_PATH = DATA_DIR / "amazon_analyst.sqlite3"

MARKETPLACES: dict[str, dict] = {
    "US": {"domain": "amazon.com", "id": "ATVPDKIKX0DER", "locale": "en-US", "lang": "en-US,en;q=0.9", "currency": "USD", "region": "NA", "ads_locale": "en_US"},
    "CA": {"domain": "amazon.ca", "id": "A2EUQ1WTGCTBG2", "locale": "en-CA", "lang": "en-CA,en;q=0.9", "currency": "CAD", "region": "NA", "ads_locale": "en_CA"},
    "MX": {"domain": "amazon.com.mx", "id": "A1AM78C64UM0Y8", "locale": "es-MX", "lang": "es-MX,es;q=0.9", "currency": "MXN", "region": "NA", "ads_locale": "es_MX"},
    "UK": {"domain": "amazon.co.uk", "id": "A1F83G8C2ARO7P", "locale": "en-GB", "lang": "en-GB,en;q=0.9", "currency": "GBP", "region": "EU", "ads_locale": "en_GB"},
    "DE": {"domain": "amazon.de", "id": "A1PA6795UKMFR9", "locale": "de-DE", "lang": "de-DE,de;q=0.9,en;q=0.8", "currency": "EUR", "region": "EU", "ads_locale": "de_DE"},
    "FR": {"domain": "amazon.fr", "id": "A13V1IB3VIYZZH", "locale": "fr-FR", "lang": "fr-FR,fr;q=0.9,en;q=0.8", "currency": "EUR", "region": "EU", "ads_locale": "fr_FR"},
    "IT": {"domain": "amazon.it", "id": "APJ6JRA9NG5V4", "locale": "it-IT", "lang": "it-IT,it;q=0.9,en;q=0.8", "currency": "EUR", "region": "EU", "ads_locale": "it_IT"},
    "ES": {"domain": "amazon.es", "id": "A1RKKUPIHCS9HS", "locale": "es-ES", "lang": "es-ES,es;q=0.9,en;q=0.8", "currency": "EUR", "region": "EU", "ads_locale": "es_ES"},
    "AU": {"domain": "amazon.com.au", "id": "A39IBJ37TRP1C6", "locale": "en-AU", "lang": "en-AU,en;q=0.9", "currency": "AUD", "region": "FE", "ads_locale": "en_AU"},
    "JP": {"domain": "amazon.co.jp", "id": "A1VC38T7YXB528", "locale": "ja-JP", "lang": "ja-JP,ja;q=0.9,en;q=0.8", "currency": "JPY", "region": "FE", "ads_locale": "ja_JP"},
}

SPAPI_BASE = {"NA": "https://sellingpartnerapi-na.amazon.com", "EU": "https://sellingpartnerapi-eu.amazon.com", "FE": "https://sellingpartnerapi-fe.amazon.com"}
ADS_BASE = {"NA": "https://advertising-api.amazon.com", "EU": "https://advertising-api-eu.amazon.com", "FE": "https://advertising-api-fe.amazon.com"}
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

# Keyword recommendations v5 is only offered in these marketplaces.
ADS_KEYWORD_REC_MARKETPLACES = {"US", "CA", "UK", "DE", "FR", "ES", "IN", "JP"}


def marketplace(code: str) -> dict:
    mp = (code or "US").upper()
    if mp not in MARKETPLACES:
        raise ValueError(f"unknown marketplace {code!r}; known: {', '.join(MARKETPLACES)}")
    return {"code": mp, **MARKETPLACES[mp]}


def spapi_configured() -> bool:
    return all(os.getenv(k) for k in ("SPAPI_LWA_CLIENT_ID", "SPAPI_LWA_CLIENT_SECRET", "SPAPI_REFRESH_TOKEN"))


def ads_configured() -> bool:
    return all(os.getenv(k) for k in ("ADS_LWA_CLIENT_ID", "ADS_LWA_CLIENT_SECRET", "ADS_REFRESH_TOKEN", "ADS_PROFILE_ID"))


def llm_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
