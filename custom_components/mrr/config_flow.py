"""Config flow for the MRR integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .api import MrrError, rigs_mine
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_PRICE_ENTITY,
    DEFAULT_PRICE_ENTITY,
    DOMAIN,
)
from .coordinator import normalise


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
                        data={
                            CONF_API_KEY: api_key,
                            CONF_API_SECRET: api_secret,
                            CONF_PRICE_ENTITY: user_input.get(CONF_PRICE_ENTITY)
                            or DEFAULT_PRICE_ENTITY,
                        },
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_API_SECRET): TextSelector(
                        TextSelectorConfig(type="password")
                    ),
                    vol.Optional(CONF_PRICE_ENTITY, default=DEFAULT_PRICE_ENTITY): str,
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
    """Update the API credentials and the BTC price entity."""

    async def async_step_init(self, user_input=None):
        """Ask for new values."""
        errors = {}
        entry = self.config_entry
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
                        entry,
                        data={
                            CONF_API_KEY: api_key,
                            CONF_API_SECRET: api_secret,
                            CONF_PRICE_ENTITY: user_input.get(CONF_PRICE_ENTITY)
                            or DEFAULT_PRICE_ENTITY,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_create_entry(data={})
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY, default=entry.data.get(CONF_API_KEY, "")
                    ): str,
                    vol.Required(CONF_API_SECRET): TextSelector(
                        TextSelectorConfig(type="password")
                    ),
                    vol.Optional(
                        CONF_PRICE_ENTITY,
                        default=entry.data.get(CONF_PRICE_ENTITY, DEFAULT_PRICE_ENTITY),
                    ): str,
                }
            ),
            errors=errors,
        )
