"""Login-with-Amazon refresh-token exchange (shared by the SP-API and Ads API clients)."""
from __future__ import annotations

import time

import requests

from .config import LWA_TOKEN_URL

_CACHE: dict[str, tuple[str, float]] = {}


def access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    cached = _CACHE.get(refresh_token)
    if cached and cached[1] > time.monotonic():
        return cached[0]
    resp = requests.post(LWA_TOKEN_URL, data={"grant_type": "refresh_token", "refresh_token": refresh_token,
                                              "client_id": client_id, "client_secret": client_secret}, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"LWA token exchange failed: HTTP {resp.status_code} {resp.text[:200]}")
    payload = resp.json()
    token = payload["access_token"]
    _CACHE[refresh_token] = (token, time.monotonic() + max(60, int(payload.get("expires_in", 3600)) - 60))
    return token


def post_with_429_retry(url: str, *, headers: dict, payload: dict, timeout: int = 30, delays=(2, 5, 10, 20)):
    r = None
    for delay in (*delays, None):
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if r.status_code != 429 or delay is None:
            return r
        time.sleep(delay)
    return r


def get_with_429_retry(url: str, *, headers: dict, params: dict, timeout: int = 30, delays=(2, 5, 10)):
    r = None
    for delay in (*delays, None):
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        if r.status_code != 429 or delay is None:
            return r
        time.sleep(delay)
    return r
