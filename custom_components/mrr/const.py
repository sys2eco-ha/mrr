"""Constants for the MRR integration."""

DOMAIN = "mrr"

CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"

DEFAULT_SCAN_INTERVAL = 600

API_BASE = "https://www.miningrigrentals.com/api/v2"
PRICE_URLS = (
    "https://api.coinbase.com/v2/prices/BTC-EUR/spot",
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur",
)
