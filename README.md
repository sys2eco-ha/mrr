# Mining Rig Rentals for Home Assistant

Custom integration that reads a Mining Rig Rentals account through the official API v2.

Every rig becomes its own Home Assistant device with its own sensors. Rigs are never combined, so each rig can be tracked for a different client.

## What it provides

Per rig:

| Sensor | Unit | Description |
| --- | --- | --- |
| Status | — | `available`, `rented` or `disabled` |
| Advertised hashrate | TH/s | Hashrate listed on MRR |
| Hashrate 5 min | TH/s | Hashrate the rig reports |
| Price | BTC/TH/d | Current listing price |
| Credited | BTC | Sum of credits for this rig |
| Refunds | BTC | Sum of refunds for this rig |
| Net | BTC | Credited minus refunds |

Attributes:

- Status and hashrate sensors: `rig_id`, `owner`, `algorithm`, `online`, `rented`, `pool_status`, `region`, `devices`, `min_hours`, `max_hours`.
- Earnings sensors: `transactions`, `pending`, `last_transaction`.

Account level: one **Balance** sensor with the confirmed BTC balance.

## Requirements

- Home Assistant with config entries (any recent release).
- Mining Rig Rentals API key and secret: MRR → Account → API.

## Installation

### HACS

1. HACS → **Integrations** → three dots → **Custom repositories**.
2. Add `https://github.com/sys2eco-ha/mrr` as an **Integration**.
3. Download **Mining Rig Rentals** and restart Home Assistant.
4. **Settings → Devices & services → Add integration → Mining Rig Rentals**.
5. Enter the API key and secret.

### Manual

Copy `custom_components/mrr` into `/config/custom_components/mrr` and restart Home Assistant.

## Request signing

MRR API v2 requires three headers on every authenticated call:

```text
x-api-key:    <api key>
x-api-nonce:  <unique, increasing value>
x-api-sign:   SHA1_HMAC(api_secret, api_key + nonce + endpoint)
```

Endpoints used:

| Endpoint | Purpose |
| --- | --- |
| `/rig/mine` | every rig of the account, all algorithms |
| `/account/balance` | confirmed and unconfirmed balances |
| `/account/transactions` | credits and refunds, grouped per rig |

## Notes

- Data is polled every 5 minutes. MRR rate limits the API; do not lower this without reason.
- `Credited`, `Refunds` and `Net` sum the transactions the API returns in one response (currently up to 100). They cover that window, not the lifetime of the rig.
- Earnings are grouped by the `rig` field of each transaction. A rig that no longer exists in the account has no device, so its transactions are not shown.
- Disabled rigs are listed with the status `disabled`.
- API credentials are stored in the Home Assistant config entry, never in this repository.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `cannot_connect` while adding | The key and secret must match; each nonce must be new for every call. |
| `no_rigs` while adding | The account has no rigs, or the key belongs to a different account. |
| Sensors show `unknown` | The API returned an error; check the Home Assistant log for `mrr`. |
| Values stop updating | The API rate limit was likely hit; wait and check the log. |

## License

MIT
