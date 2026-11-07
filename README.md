# Mining Rig Rentals for Home Assistant

Custom integration that reads your Mining Rig Rentals account through the official API v2.

Every rig becomes its own Home Assistant device with its own sensors. Rigs are never combined, so each rig can be assigned to a different client.

## What it provides

For each rig:

| Sensor | Unit | Description |
| --- | --- | --- |
| Status | — | `available`, `rented`, `disabled` |
| Advertised hashrate | TH/s | Hashrate listed on MRR |
| Hashrate 5 min | TH/s | Reported by the rig |
| Price | BTC/TH/d | Current listing price |
| Credited | BTC | Sum of credits for this rig |
| Refunds | BTC | Sum of refunds for this rig |
| Net | BTC | Credited minus refunds |

Attributes on the earnings sensors: transaction count, pending count, last transaction time.
Attributes on the hashrate/status sensors: owner, algorithm, online, rented, pool status, region, device count, min/max rental hours.

Account level: one `Balance` sensor with the confirmed BTC balance.

## Requirements

- Home Assistant 2024.1 or newer
- Mining Rig Rentals API key and secret (MRR → Account → API)

## Installation

### HACS

1. HACS → Integrations → three dots → Custom repositories.
2. Add `https://github.com/sys2eco-ha/mrr` as an **Integration**.
3. Install **Mining Rig Rentals** and restart Home Assistant.
4. Settings → Devices & services → Add integration → **Mining Rig Rentals**.
5. Enter the API key and secret.

### Manual

Copy `custom_components/mrr` into `/config/custom_components/mrr` and restart Home Assistant.

## Notes

- Data is polled every 5 minutes. The MRR API is rate limited, so do not lower this without reason.
- `Credited`, `Refunds` and `Net` are summed from the transactions the API returns (up to 100 per poll). They cover that window, not the lifetime of the rig.
- Earnings are grouped by the `rig` field of each transaction. Rigs that no longer exist in the account are not shown.
- API credentials are stored in the Home Assistant config entry, never in this repository.

## License

MIT
