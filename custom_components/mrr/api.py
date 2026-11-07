"""Minimal Mining Rig Rentals API client."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request

from .const import API_BASE, PRICE_URLS


class MrrError(Exception):
    """Raised when the MRR API reports a failure."""


def _sign(api_key: str, api_secret: str, nonce: str, endpoint: str) -> dict:
    """Build the authentication headers for a signed endpoint."""
    message = f"{api_key}{nonce}{endpoint}".encode()
    signature = hmac.new(api_secret.encode(), message, hashlib.sha1).hexdigest()
    return {
        "x-api-key": api_key,
        "x-api-nonce": nonce,
        "x-api-sign": signature,
    }


def _request(endpoint: str, params: dict | None = None, api_key: str | None = None, api_secret: str | None = None):
    """Perform one request and return the `data` payload."""
    url = API_BASE + endpoint
    if params:
        query = "&".join(f"{key}={value}" for key, value in params.items())
        url = f"{url}?{query}"
    headers = {"Accept": "application/json"}
    if api_key and api_secret:
        headers.update(_sign(api_key, api_secret, str(time.time_ns()), endpoint))
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")
        raise MrrError(f"HTTP {err.code}: {body[:200]}") from err
    except (urllib.error.URLError, OSError, ValueError) as err:
        raise MrrError(type(err).__name__) from err
    if not payload.get("success"):
        raise MrrError(str(payload.get("data")))
    return payload.get("data")


def rigs_mine(api_key: str, api_secret: str):
    """Return every rig owned by the authenticated account."""
    return _request("/rig/mine", api_key=api_key, api_secret=api_secret)


def get_rig(rig_id: str) -> dict:
    """Return the current state of one rig."""
    return _request(f"/rig/{rig_id}")


def account_balance(api_key: str, api_secret: str):
    """Return the account balance."""
    return _request("/account/balance", api_key=api_key, api_secret=api_secret)


def account_profile(api_key: str, api_secret: str):
    """Return the account profile."""
    return _request("/account/profile", api_key=api_key, api_secret=api_secret)


def account_transactions(api_key: str, api_secret: str):
    """Return the account transactions."""
    return _request("/account/transactions", api_key=api_key, api_secret=api_secret)


def btc_eur_price() -> float | None:
    """Return the current BTC price in EUR, or None when unavailable."""
    for url in PRICE_URLS:
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8", "replace"))
        except (urllib.error.HTTPError, OSError, ValueError):
            continue
        try:
            if "data" in payload:
                return float(payload["data"]["amount"])
            return float(payload["bitcoin"]["eur"])
        except (KeyError, TypeError, ValueError):
            continue
    return None
