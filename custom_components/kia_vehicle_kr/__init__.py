"""Kia Developers integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from aiohttp import web

from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.typing import ConfigType

from .api import KiaDevelopersApi
from .const import (
    CONSENT_CALLBACK_PATH,
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_IDS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    OAUTH_CALLBACK_PATH,
)
from .coordinator import KiaDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


@dataclass(slots=True)
class KiaRuntimeData:
    """Runtime objects for a Kia config entry."""

    api: KiaDevelopersApi
    coordinator: KiaDataUpdateCoordinator


type KiaConfigEntry = ConfigEntry[KiaRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register callbacks used by Kia's OAuth and data-consent flows."""
    async_register_callback_views(hass)
    return True


@callback
def async_register_callback_views(hass: HomeAssistant) -> None:
    """Register callbacks before the first config entry is created."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("callback_views_registered"):
        return
    domain_data.setdefault("oauth_flows", {})
    domain_data.setdefault("consent_flows", {})
    hass.http.register_view(KiaOAuthCallbackView())
    hass.http.register_view(KiaConsentCallbackView())
    domain_data["callback_views_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: KiaConfigEntry) -> bool:
    """Set up Kia Developers from a config entry."""
    try:
        implementation = (
            await config_entry_oauth2_flow.async_get_config_entry_implementation(
                hass, entry
            )
        )
    except config_entry_oauth2_flow.ImplementationUnavailableError as err:
        raise ConfigEntryNotReady("Kia OAuth implementation is unavailable") from err

    oauth_session = config_entry_oauth2_flow.OAuth2Session(
        hass,
        entry,
        implementation,
    )
    api = KiaDevelopersApi(oauth_session.async_request)

    vehicle_ids = list(entry.options.get(CONF_VEHICLE_IDS, []))
    update_minutes = entry.options.get(
        CONF_UPDATE_INTERVAL,
        DEFAULT_UPDATE_INTERVAL_MINUTES,
    )
    coordinator = KiaDataUpdateCoordinator(
        hass,
        entry,
        api,
        vehicle_ids,
        timedelta(minutes=update_minutes),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = KiaRuntimeData(api=api, coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KiaConfigEntry) -> bool:
    """Unload a Kia config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: KiaConfigEntry) -> None:
    """Reload after vehicle or interval options change."""
    await hass.config_entries.async_reload(entry.entry_id)


class KiaConsentCallbackView(HomeAssistantView):
    """Receive Kia's personal-data consent result."""

    requires_auth = False
    url = CONSENT_CALLBACK_PATH
    name = "api:kia_vehicle_kr:consent_callback"

    async def get(self, request: web.Request) -> web.Response:
        """Resume the matching config flow."""
        hass: HomeAssistant = request.app[KEY_HASS]
        state = request.query.get("state")
        pending = hass.data.get(DOMAIN, {}).get("consent_flows", {})
        flow_id = pending.get(state)
        if not state or not flow_id:
            return web.Response(text="Invalid or expired state", status=400)

        await hass.config_entries.flow.async_configure(
            flow_id=flow_id,
            user_input=dict(request.query),
        )
        return web.Response(
            text="<script>window.close()</script>",
            content_type="text/html",
        )


class KiaOAuthCallbackView(HomeAssistantView):
    """Receive Kia's OAuth result without Home Assistant's JWT state."""

    requires_auth = False
    url = OAUTH_CALLBACK_PATH
    name = "api:kia_vehicle_kr:oauth_callback"

    async def get(self, request: web.Request) -> web.Response:
        """Resume the matching Kia config flow."""
        hass: HomeAssistant = request.app[KEY_HASS]
        state = request.query.get("state")
        pending = hass.data.get(DOMAIN, {}).get("oauth_flows", {})
        flow = pending.pop(state, None)
        if not state or not isinstance(flow, dict):
            return web.Response(text="Invalid or expired OAuth state", status=400)

        user_input: dict = {
            "state": {
                "flow_id": flow["flow_id"],
                "redirect_uri": flow["redirect_uri"],
            }
        }
        if code := request.query.get("code"):
            user_input["code"] = code
        elif error := request.query.get("error"):
            user_input["error"] = error
        else:
            return web.Response(text="Missing OAuth code or error", status=400)

        await hass.config_entries.flow.async_configure(
            flow_id=flow["flow_id"],
            user_input=user_input,
        )
        return web.Response(
            text="<script>window.close()</script>",
            content_type="text/html",
        )

