"""Polling for the MRR integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    MrrError,
    account_balance,
    account_transactions,
    btc_eur_price,
    rigs_mine,
)
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

HASH_FACTORS = {
    "h": 1e-12,
    "kh": 1e-9,
    "mh": 1e-6,
    "gh": 1e-3,
    "th": 1.0,
    "ph": 1e3,
    "eh": 1e6,
}


def to_th(payload) -> float | None:
    """Convert a hashrate payload to TH/s."""
    if not isinstance(payload, dict):
        return None
    try:
        value = float(payload.get("hash"))
    except (TypeError, ValueError):
        return None
    factor = HASH_FACTORS.get(str(payload.get("type", "")).lower())
    return None if factor is None else round(value * factor, 6)


def rig_price(payload) -> float | None:
    """Return the BTC price per TH per day."""
    try:
        return float(payload["price"]["BTC"]["price"])
    except (KeyError, TypeError, ValueError):
        return None


def balance_btc(payload) -> float | None:
    """Return the confirmed BTC balance."""
    try:
        return float(payload["BTC"]["confirmed"])
    except (KeyError, TypeError, ValueError):
        return None


def earnings(payload) -> dict:
    """Group transactions per rig id."""
    transactions = payload.get("transactions") if isinstance(payload, dict) else None
    result: dict[str, dict] = {}
    for tx in transactions or []:
        rig_id = str(tx.get("rig"))
        if rig_id == "None":
            continue
        entry = result.setdefault(
            rig_id,
            {"credited": 0.0, "refunds": 0.0, "net": 0.0, "count": 0,
             "pending": 0, "last": None},
        )
        try:
            amount = float(tx.get("amount"))
        except (TypeError, ValueError):
            continue
        if tx.get("type") == "Credit":
            entry["credited"] += amount
        else:
            entry["refunds"] += abs(amount)
        entry["net"] = round(entry["credited"] - entry["refunds"], 10)
        entry["count"] += 1
        if tx.get("status") == "Pending":
            entry["pending"] += 1
        when = tx.get("when")
        if when and (entry["last"] is None or when > entry["last"]):
            entry["last"] = when
    return result


def normalise(payload) -> dict:
    """Turn a `/rig/mine` response into a mapping of rig id to rig data."""
    records = payload
    if isinstance(payload, dict):
        records = payload.get("records") or payload.get("rigs") or []
    if not isinstance(records, list):
        return {}
    return {
        str(record["id"]): record
        for record in records
        if isinstance(record, dict) and "id" in record
    }


class MrrCoordinator(DataUpdateCoordinator):
    """Poll every rig of one MRR account and the BTC price."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        self.api_key = entry.data[CONF_API_KEY]
        self.api_secret = entry.data[CONF_API_SECRET]
        self.btc_eur: float | None = None

    async def _async_update_data(self) -> dict:
        try:
            payload = await self.hass.async_add_executor_job(
                rigs_mine, self.api_key, self.api_secret
            )
        except MrrError as err:
            raise UpdateFailed(str(err)) from err

        data = {
            "rigs": normalise(payload),
            "earnings": {},
            "balance": None,
            "btc_eur": self.btc_eur,
        }

        price = await self.hass.async_add_executor_job(btc_eur_price)
        if price:
            self.btc_eur = price
            data["btc_eur"] = price

        try:
            balance = await self.hass.async_add_executor_job(
                account_balance, self.api_key, self.api_secret
            )
            transactions = await self.hass.async_add_executor_job(
                account_transactions, self.api_key, self.api_secret
            )
        except MrrError as err:
            _LOGGER.debug("MRR account request failed: %s", err)
        else:
            data["balance"] = balance_btc(balance)
            data["earnings"] = earnings(transactions)
        return data
