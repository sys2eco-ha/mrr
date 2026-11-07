"""Sensors for the MRR integration. One device and one set of sensors per rig."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import rig_price, to_th

RIG_SENSORS = (
    ("status", "Būsena"),
    ("advertised", "Skelbiamas hashrate"),
    ("last_5min", "Hashrate (5 min.)"),
    ("price", "Kaina BTC/TH/d"),
    ("price_btc_day", "Kaina BTC/d"),
    ("price_eur_day", "Kaina EUR/d"),
    ("credited", "Įskaityta BTC"),
    ("refunds", "Grąžinta BTC"),
    ("net", "Grynosios BTC"),
    ("credited_eur", "Įskaityta EUR"),
    ("refunds_eur", "Grąžinta EUR"),
    ("net_eur", "Grynosios EUR"),
    ("power", "Galios skaitiklis"),
    ("power_price", "Elektros kaina"),
    ("power_cost", "Elektra EUR/d"),
    ("profit", "Pelnas EUR/d"),
)

EUR_KEYS = {"credited_eur": "credited", "refunds_eur": "refunds", "net_eur": "net"}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        MrrRigSensor(coordinator, entry.entry_id, rig_id, key, label)
        for rig_id in coordinator.data["rigs"]
        for key, label in RIG_SENSORS
    ]
    entities.append(MrrBalanceSensor(coordinator, entry.entry_id, "balance", "Balansas BTC", "BTC"))
    entities.append(MrrBalanceSensor(coordinator, entry.entry_id, "balance_eur", "Balansas EUR", "EUR"))
    entities.append(MrrPriceSensor(coordinator, entry.entry_id))
    async_add_entities(entities)


class MrrRigSensor(CoordinatorEntity, SensorEntity):
    """One value of one rig. Rigs are never combined."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, rig_id, key, label):
        super().__init__(coordinator)
        self._rig_id = rig_id
        self._key = key
        self._attr_unique_id = f"{entry_id}_{rig_id}_{key}"
        self._attr_name = label
        if key in ("advertised", "last_5min"):
            self._attr_native_unit_of_measurement = "TH/s"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key == "price":
            self._attr_native_unit_of_measurement = "BTC/TH/d"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key == "price_btc_day":
            self._attr_native_unit_of_measurement = "BTC/d"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key == "price_eur_day":
            self._attr_native_unit_of_measurement = "EUR/d"
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key in ("credited", "refunds", "net"):
            self._attr_native_unit_of_measurement = "BTC"
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING if key == "credited" else None
        elif key in EUR_KEYS:
            self._attr_native_unit_of_measurement = "EUR"
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING if key == "credited_eur" else None
        elif key == "power":
            self._attr_native_unit_of_measurement = "W"
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key == "power_price":
            self._attr_native_unit_of_measurement = "EUR/kWh"
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:flash"
        elif key in ("power_cost", "profit"):
            self._attr_native_unit_of_measurement = "EUR/d"
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def _rig(self) -> dict:
        return self.coordinator.data["rigs"].get(self._rig_id, {})

    @property
    def _earnings(self) -> dict:
        return self.coordinator.data.get("earnings", {}).get(self._rig_id, {})

    @property
    def device_info(self):
        rig = self._rig
        return DeviceInfo(
            identifiers={(DOMAIN, self._rig_id)},
            name=rig.get("name") or f"Rig {self._rig_id}",
            manufacturer="Mining Rig Rentals",
            model=rig.get("type"),
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self._rig)

    @property
    def native_value(self):
        rig = self._rig
        costs = self.coordinator.data.get("costs", {}).get(self._rig_id, {})
        if self._key == "power":
            return costs.get("power")
        if self._key == "power_price":
            return costs.get("price")
        if self._key == "power_cost":
            return costs.get("cost")
        if self._key == "profit":
            rate = self.coordinator.data.get("btc_eur")
            net = self._earnings.get("net")
            cost = costs.get("cost")
            if net is None or not rate or cost is None:
                return None
            return round(net * rate - cost, 2)
        if self._key == "status":
            return (rig.get("status") or {}).get("status")
        if self._key == "price":
            return rig_price(rig)
        if self._key in ("price_btc_day", "price_eur_day"):
            unit_price = rig_price(rig)
            hashrate = to_th((rig.get("hashrate") or {}).get("advertised"))
            if unit_price is None or not hashrate:
                return None
            per_day = unit_price * hashrate
            if self._key == "price_btc_day":
                return round(per_day, 8)
            rate = self.coordinator.data.get("btc_eur")
            return round(per_day * rate, 2) if rate else None
        if self._key == "last_5min":
            return to_th((rig.get("hashrate") or {}).get("last_5min"))
        if self._key == "advertised":
            return to_th((rig.get("hashrate") or {}).get("advertised"))

        entry = self._earnings
        if not entry:
            return None
        if self._key in EUR_KEYS:
            rate = self.coordinator.data.get("btc_eur")
            base = entry.get(EUR_KEYS[self._key])
            return round(base * rate, 2) if base is not None and rate else None
        if self._key == "credited":
            return round(entry.get("credited", 0.0), 8)
        if self._key == "refunds":
            return round(entry.get("refunds", 0.0), 8)
        return round(entry.get("net", 0.0), 8)

    @property
    def extra_state_attributes(self):
        rig = self._rig
        if not rig:
            return None
        attributes = {
            "rig_id": self._rig_id,
            "owner": rig.get("owner"),
            "algorithm": rig.get("type"),
            "online": rig.get("online"),
            "rented": (rig.get("status") or {}).get("rented"),
            "pool_status": rig.get("poolstatus"),
            "region": rig.get("region"),
            "devices": rig.get("ndevices"),
            "min_hours": rig.get("minhours"),
            "max_hours": rig.get("maxhours"),
        }
        if self._key in ("credited", "refunds", "net", "credited_eur", "refunds_eur", "net_eur"):
            entry = self._earnings
            attributes.update(
                {
                    "transactions": entry.get("count", 0),
                    "pending": entry.get("pending", 0),
                    "last_transaction": entry.get("last"),
                }
            )
        return attributes


class MrrBalanceSensor(CoordinatorEntity, SensorEntity):
    """Confirmed BTC balance of the account, in BTC or EUR."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, key, label, unit):
        super().__init__(coordinator)
        self._key = key
        unique = "balance_btc" if key == "balance" else key
        self._attr_unique_id = f"{entry_id}_{unique}"
        self._attr_name = label
        self._attr_native_unit_of_measurement = unit
        if unit == "EUR":
            self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Mining Rig Rentals",
            manufacturer="Mining Rig Rentals",
        )

    @property
    def native_value(self):
        value = self.coordinator.data.get("balance")
        if self._key == "balance":
            return value
        rate = self.coordinator.data.get("btc_eur")
        return round(value * rate, 2) if value is not None and rate else None


class MrrPriceSensor(CoordinatorEntity, SensorEntity):
    """BTC price in EUR used for the conversions."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_btc_eur"
        self._attr_name = "BTC kursas"
        self._attr_native_unit_of_measurement = "EUR"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_icon = "mdi:currency-btc"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Mining Rig Rentals",
            manufacturer="Mining Rig Rentals",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get("btc_eur")
