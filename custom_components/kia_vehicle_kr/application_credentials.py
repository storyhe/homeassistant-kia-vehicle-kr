"""OAuth application credentials for Kia Developers."""

from __future__ import annotations

import base64
from json import JSONDecodeError
import logging
import secrets
import time
from typing import cast, override

from aiohttp import ClientError
from yarl import URL

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import (
    AbstractOAuth2Implementation,
    LocalOAuth2Implementation,
)
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import (
    AUTHORIZE_URL,
    CONSENT_CALLBACK_PATH,
    DOMAIN,
    OAUTH_CALLBACK_PATH,
    TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)


class KiaOAuth2Implementation(LocalOAuth2Implementation):
    """Kia OAuth implementation using HTTP Basic client authentication."""

    @property
    @override
    def redirect_uri(self) -> str:
        """Return this Home Assistant instance's direct OAuth callback."""
        return _direct_callback_url(self.hass, OAUTH_CALLBACK_PATH)

    @override
    async def async_generate_authorize_url(self, flow_id: str) -> str:
        """Generate an authorize URL using an integration-owned opaque state."""
        state = secrets.token_urlsafe(32)
        now = time.monotonic()
        pending = self.hass.data.setdefault(DOMAIN, {}).setdefault(
            "oauth_flows", {}
        )
        for old_state, flow in list(pending.items()):
            if now - flow.get("created", 0) > 3600:
                pending.pop(old_state, None)
        pending[state] = {
            "created": now,
            "flow_id": flow_id,
            "redirect_uri": self.redirect_uri,
        }
        return str(
            URL(self.authorize_url).with_query(
                {
                    "response_type": "code",
                    "client_id": self.client_id,
                    "redirect_uri": self.redirect_uri,
                    "state": state,
                }
            )
        )

    @property
    @override
    def name(self) -> str:
        """Return a user-facing implementation name."""
        return "Kia Vehicle KR"

    @override
    async def _token_request(self, data: dict) -> dict:
        """Exchange or refresh a token using Kia's required Basic auth."""
        session = async_get_clientsession(self.hass)
        response = await session.post(
            self.token_url,
            data=data,
            headers={
                "Authorization": _basic_auth_header(
                    self.client_id, self.client_secret
                ),
                "Accept": "application/json",
            },
        )

        if response.status >= 400:
            try:
                error = await response.json(content_type=None)
            except (ClientError, JSONDecodeError, ValueError):
                error = {}
            if isinstance(error, dict):
                detail = (
                    error.get("error_description")
                    or error.get("error")
                    or error.get("message")
                    or "unknown"
                )
            else:
                detail = str(error)[:200] or "unknown"
            _LOGGER.error(
                "Kia token request failed with HTTP %s: %s",
                response.status,
                detail,
            )

        response.raise_for_status()
        return cast(dict, await response.json(content_type=None))

    @override
    async def _async_refresh_token(self, token: dict) -> dict:
        """Refresh a Kia token without putting client credentials in the body."""
        new_token = await self._token_request(
            {
                "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"],
            }
        )
        if not new_token.get("access_token"):
            raise ClientError("Kia token response did not include an access token")
        return {**token, **new_token}


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    """Return an RFC 7617 Basic authorization header."""
    credentials = f"{client_id}:{client_secret}".encode()
    return f"Basic {base64.b64encode(credentials).decode()}"


def _direct_callback_url(hass: HomeAssistant, path: str) -> str:
    """Build an externally reachable callback for this HA installation."""
    return f"{get_url(hass, prefer_external=True).rstrip('/')}{path}"


async def async_get_authorization_server(
    hass: HomeAssistant,
) -> AuthorizationServer:
    """Return Kia's OAuth endpoints."""
    return AuthorizationServer(
        authorize_url=AUTHORIZE_URL,
        token_url=TOKEN_URL,
    )


async def async_get_auth_implementation(
    hass: HomeAssistant,
    auth_domain: str,
    credential: ClientCredential,
) -> AbstractOAuth2Implementation:
    """Return the Kia OAuth implementation."""
    return KiaOAuth2Implementation(
        hass,
        auth_domain,
        credential.client_id,
        credential.client_secret,
        AUTHORIZE_URL,
        TOKEN_URL,
    )


async def async_get_description_placeholders(
    hass: HomeAssistant,
) -> dict[str, str]:
    """Return dynamic help links for the credentials dialog."""
    try:
        callback_url = _direct_callback_url(hass, OAUTH_CALLBACK_PATH)
        consent_callback_url = _direct_callback_url(hass, CONSENT_CALLBACK_PATH)
    except NoURLAvailableError:
        callback_url = f"<HOME_ASSISTANT_URL>{OAUTH_CALLBACK_PATH}"
        consent_callback_url = f"<HOME_ASSISTANT_URL>{CONSENT_CALLBACK_PATH}"

    return {
        "console_url": "https://console.developers.kia.com/",
        "callback_url": callback_url,
        "consent_callback_url": consent_callback_url,
    }

