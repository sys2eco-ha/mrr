"""Config flow for the MRR integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .api import MrrError, rigs_mine
from .const import CONF_API_KEY, CONF_API_SECRET, DOMAIN
from .coordinator import normalise

CONF_RIGS = "rigs"


class MrrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one Mining Rig Rentals account."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Ask for the API credentials."""
        errors = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            api_secret = user_input[CONF_API_SECRET].strip()
            try:
                payload = await self.hass.async_add_executor_job(
                    rigs_mine, api_key, api_secret
                )
            except MrrError:
                errors["base"] = "cannot_connect"
            else:
                if not normalise(payload):
                    errors["base"] = "no_rigs"
                else:
                    return self.async_create_entry(
                        title="Mining Rig Rentals",
                        data={CONF_API_KEY: api_key, CONF_API_SECRET: api_secret},
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_API_SECRET): TextSelector(
                        TextSelectorConfig(type="password")
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow used to update credentials."""
        return MrrOptionsFlow()


class MrrOptionsFlow(config_entries.OptionsFlow):
    """Update credentials or the per-rig power settings."""

    async def async_step_init(self, user_input=None):
        """Choose what to change."""
        return self.async_show_menu(step_id="init", menu_options=["credentials", "power"])

    @property
    def _rigs(self) -> dict:
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        return (coordinator.data.get("rigs") if coordinator else {}) or {}

    @property
    def _settings(self) -> dict:
        return (self.config_entry.options.get(CONF_RIGS) or {})

    async def async_step_credentials(self, user_input=None):
        """Update the MRR API key and secret."""
        errors = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            api_secret = user_input[CONF_API_SECRET].strip()
            try:
                payload = await self.hass.async_add_executor_job(
                    rigs_mine, api_key, api_secret
                )
            except MrrError:
                errors["base"] = "cannot_connect"
            else:
                if not normalise(payload):
                    errors["base"] = "no_rigs"
                else:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={CONF_API_KEY: api_key, CONF_API_SECRET: api_secret},
                    )
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    return self.async_create_entry(data={CONF_RIGS: self._settings})
        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY, default=self.config_entry.data.get(CONF_API_KEY, "")
                    ): str,
                    vol.Required(CONF_API_SECRET): TextSelector(
                        TextSelectorConfig(type="password")
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_power(self, user_input=None):
        """Set the power sensor and the electricity price for every rig."""
        rigs = self._rigs
        if user_input is not None:
            settings = dict(self._settings)
            for rig_id in rigs:
                power_value = (user_input.get(f"power_{rig_id}") or "").strip()
                price_value = user_input.get(f"price_{rig_id}")
                settings[rig_id] = {
                    "power_entity": power_value or None,
                    "price": float(price_value) if price_value else None,
                }
            return self.async_create_entry(data={CONF_RIGS: settings})
        fields = {}
        for rig_id, rig in rigs.items():
            current = self._settings.get(rig_id, {})
            label = (rig.get("name") or rig_id).split("|")[0].strip()[:32]
            fields[
                vol.Optional(
                    f"power_{rig_id}", default=current.get("power_entity") or ""
                )
            ] = str
            fields[
                vol.Optional(
                    f"price_{rig_id}", default=current.get("price") or 0.0
                )
            ] = vol.Coerce(float)
        return self.async_show_form(step_id="power", data_schema=vol.Schema(fields))
