"""Config flow for Kia Developers."""

from __future__ import annotations

import hashlib
import logging
import secrets
from collections.abc import Mapping
from typing import Any, override

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import config_entry_oauth2_flow, selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import async_register_callback_views
from .api import KiaApiAgreementRequiredError, KiaApiError, KiaDevelopersApi
from .const import (
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_IDS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_UPDATE_INTERVAL_MINUTES,
)
from .models import KiaVehicle

_LOGGER = logging.getLogger(__name__)


class KiaDevelopersConfigFlow(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    """Handle a Kia Developers config flow."""

    DOMAIN = DOMAIN
    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        super().__init__()
        self._oauth_data: dict[str, Any] | None = None
        self._vehicles: dict[str, KiaVehicle] | None = None
        self._account_id: str | None = None
        self._consent_state: str | None = None

    @property
    @override
    def logger(self) -> logging.Logger:
        """Return the flow logger."""
        return _LOGGER

    @override
    async def async_generate_authorize_url(self) -> str:
        """Install the callback before sending the browser to Kia."""
        async_register_callback_views(self.hass)
        return await super().async_generate_authorize_url()

    @override
    async def async_oauth_create_entry(
        self, data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Continue to vehicle selection after OAuth succeeds."""
        if self.source == SOURCE_REAUTH:
            self._oauth_data = data
            try:
                await self._async_load_account_and_vehicles()
            except KiaApiError:
                return self.async_abort(reason="cannot_connect")
            entry = self._get_reauth_entry()
            await self.async_set_unique_id(self._account_id)
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                entry,
                data_updates=data,
            )

        self._oauth_data = data
        try:
            await self._async_load_account_and_vehicles()
        except KiaApiAgreementRequiredError:
            return await self.async_step_consent()
        except KiaApiError:
            return self.async_abort(reason="cannot_connect")
        return await self.async_step_vehicles()

    async def async_step_consent(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Run Kia's personal-data consent flow only when the API requires it."""
        if self._oauth_data is None:
            return self.async_abort(reason="oauth_error")

        if user_input is not None:
            state = user_input.get("state")
            user_id = user_input.get("userId") or user_input.get("userID")
            pending = self.hass.data.setdefault(DOMAIN, {}).setdefault(
                "consent_flows", {}
            )
            flow_id = pending.pop(state, None)
            if (
                not isinstance(state, str)
                or state != self._consent_state
                or flow_id != self.flow_id
                or not isinstance(user_id, str)
                or not user_id
            ):
                return self.async_abort(reason="invalid_consent_callback")
            self._account_id = f"account:{user_id}"
            return self.async_external_step_done(next_step_id="vehicles")

        token = self._oauth_data["token"]
        api = KiaDevelopersApi(
            async_get_clientsession(self.hass).request,
            access_token=token["access_token"],
        )
        self._consent_state = secrets.token_urlsafe(32)
        self.hass.data.setdefault(DOMAIN, {}).setdefault("consent_flows", {})[
            self._consent_state
        ] = self.flow_id
        try:
            url = await api.async_get_consent_url(self._consent_state)
        except KiaApiError:
            self.hass.data[DOMAIN]["consent_flows"].pop(
                self._consent_state, None
            )
            return self.async_abort(reason="consent_failed")
        return self.async_external_step(step_id="consent", url=url)

    async def async_step_vehicles(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user select one or more Kia vehicles."""
        if self._oauth_data is None:
            return self.async_abort(reason="oauth_error")

        errors: dict[str, str] = {}
        if self._vehicles is None:
            try:
                await self._async_load_account_and_vehicles()
            except KiaApiError:
                errors["base"] = "cannot_connect"

        if self._vehicles is None:
            return self.async_show_form(
                step_id="vehicles",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        if not self._vehicles:
            return self.async_abort(reason="no_vehicles")

        if user_input is not None:
            selected = list(dict.fromkeys(user_input[CONF_VEHICLE_IDS]))
            if not selected:
                errors[CONF_VEHICLE_IDS] = "select_vehicle"
            elif any(vehicle_id not in self._vehicles for vehicle_id in selected):
                errors[CONF_VEHICLE_IDS] = "invalid_vehicle"
            else:
                await self.async_set_unique_id(self._account_id)
                self._abort_if_unique_id_configured()
                title = _entry_title([self._vehicles[item] for item in selected])
                return self.async_create_entry(
                    title=title,
                    data=self._oauth_data,
                    options={
                        CONF_VEHICLE_IDS: selected,
                        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL_MINUTES,
                    },
                )

        return self.async_show_form(
            step_id="vehicles",
            data_schema=_vehicle_schema(
                self._vehicles,
                default=list(self._vehicles),
            ),
            errors=errors,
        )

    async def _async_load_account_and_vehicles(self) -> None:
        """Fetch the profile and vehicles with the newly issued token."""
        assert self._oauth_data is not None
        token = self._oauth_data["token"]
        api = KiaDevelopersApi(
            async_get_clientsession(self.hass).request,
            access_token=token["access_token"],
        )
        vehicles = await api.async_get_vehicles()

        profile: dict[str, Any] = {}
        try:
            profile = await api.async_get_profile()
        except KiaApiError:
            _LOGGER.debug("Kia profile could not be loaded during setup")

        self._vehicles = {vehicle.car_id: vehicle for vehicle in vehicles}
        if self._account_id is None:
            self._account_id = _account_unique_id(profile, vehicles)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return KiaDevelopersOptionsFlow(config_entry)


class KiaDevelopersOptionsFlow(OptionsFlow):
    """Change selected vehicles and polling interval."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = config_entry
        self._vehicles: dict[str, KiaVehicle] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration options."""
        errors: dict[str, str] = {}
        if self._vehicles is None:
            try:
                runtime_data = self._entry.runtime_data
                vehicles = await runtime_data.api.async_get_vehicles()
                self._vehicles = {vehicle.car_id: vehicle for vehicle in vehicles}
            except (AttributeError, KiaApiError):
                errors["base"] = "cannot_connect"

        if self._vehicles is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        current_ids = [
            vehicle_id
            for vehicle_id in self._entry.options.get(CONF_VEHICLE_IDS, [])
            if vehicle_id in self._vehicles
        ]

        if user_input is not None:
            selected = list(dict.fromkeys(user_input[CONF_VEHICLE_IDS]))
            if not selected:
                errors[CONF_VEHICLE_IDS] = "select_vehicle"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_VEHICLE_IDS: selected,
                        CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
                    },
                )

        schema = _vehicle_schema(
            self._vehicles,
            default=current_ids or list(self._vehicles),
        ).extend(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self._entry.options.get(
                        CONF_UPDATE_INTERVAL,
                        DEFAULT_UPDATE_INTERVAL_MINUTES,
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=MIN_UPDATE_INTERVAL_MINUTES,
                        max=MAX_UPDATE_INTERVAL_MINUTES,
                    ),
                )
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )


def _vehicle_schema(
    vehicles: dict[str, KiaVehicle],
    *,
    default: list[str],
) -> vol.Schema:
    """Return a multi-select vehicle schema."""
    options = [
        selector.SelectOptionDict(value=vehicle.car_id, label=vehicle.display_name)
        for vehicle in vehicles.values()
    ]
    return vol.Schema(
        {
            vol.Required(CONF_VEHICLE_IDS, default=default): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


def _account_unique_id(
    profile: dict[str, Any], vehicles: list[KiaVehicle]
) -> str:
    """Return a stable, non-secret account identifier."""
    profile_id = _find_profile_id(profile)
    if profile_id:
        return f"account:{profile_id}"

    car_ids = "\x00".join(sorted(vehicle.car_id for vehicle in vehicles))
    digest = hashlib.sha256(car_ids.encode()).hexdigest()
    return f"vehicles:{digest}"


def _find_profile_id(value: Any) -> str | None:
    """Find a documented or commonly returned Kia user identifier."""
    if isinstance(value, dict):
        for key in ("userId", "userID", "masterId", "masterID", "id"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
        for nested in value.values():
            candidate = _find_profile_id(nested)
            if candidate:
                return candidate
    return None


def _entry_title(vehicles: list[KiaVehicle]) -> str:
    """Return a concise config entry title."""
    if len(vehicles) == 1:
        return vehicles[0].display_name
    return f"Kia ({len(vehicles)} vehicles)"

