"""Async client for the official Kia Developers APIs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import math
from typing import Any

from aiohttp import ClientError, ClientResponse

from .const import CONSENT_URL, DATA_API_BASE_URL, PROFILE_URL, VEHICLES_URL
from .models import KiaVehicle

RequestCallable = Callable[..., Awaitable[ClientResponse]]


class KiaApiError(Exception):
    """Base Kia API error."""


class KiaApiAuthenticationError(KiaApiError):
    """Kia rejected the current credentials."""


class KiaApiConnectionError(KiaApiError):
    """Kia could not be reached or returned an invalid response."""


class KiaApiAgreementRequiredError(KiaApiError):
    """Kia requires a separate personal-data agreement for this account."""


class KiaDevelopersApi:
    """Small API wrapper shared by config flow and runtime polling."""

    def __init__(
        self,
        request: RequestCallable,
        *,
        access_token: str | None = None,
    ) -> None:
        """Initialize the client."""
        self._request = request
        self._access_token = access_token

    async def async_get_profile(self) -> dict[str, Any]:
        """Return the Kia user profile."""
        return await self._async_get_json(PROFILE_URL)

    async def async_get_vehicles(self) -> list[KiaVehicle]:
        """Return vehicles made available to this OAuth grant."""
        payload = await self._async_get_json(VEHICLES_URL)
        raw_cars = payload.get("cars", [])

        if isinstance(raw_cars, dict):
            if "carId" in raw_cars or "carID" in raw_cars:
                raw_cars = [raw_cars]
            else:
                raw_cars = list(raw_cars.values())

        if not isinstance(raw_cars, list):
            raise KiaApiConnectionError("Kia returned an invalid vehicle list")

        vehicles: list[KiaVehicle] = []
        for raw_car in raw_cars:
            if not isinstance(raw_car, dict):
                continue
            try:
                vehicles.append(KiaVehicle.from_dict(raw_car))
            except ValueError:
                continue
        return vehicles

    async def async_get_consent_url(self, state: str) -> str:
        """Start Kia's third-party personal-data consent flow."""
        if not self._access_token:
            raise KiaApiAuthenticationError("An access token is required for consent")

        try:
            response = await self._request(
                "POST",
                CONSENT_URL,
                data={
                    "token": f"Bearer {self._access_token}",
                    "state": state,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=False,
            )
            async with response:
                if response.status in (401, 403):
                    raise KiaApiAuthenticationError("Kia authentication failed")
                if response.status not in (301, 302, 303, 307, 308):
                    raise KiaApiConnectionError(
                        f"Kia consent request failed with HTTP {response.status}"
                    )
                location = response.headers.get("Location")
        except KiaApiError:
            raise
        except (ClientError, TimeoutError) as err:
            raise KiaApiConnectionError("Unable to start Kia consent") from err

        if not location:
            raise KiaApiConnectionError("Kia did not return a consent URL")
        return location

    async def async_get_driving_range(self, car_id: str) -> float | None:
        """Return the vehicle's driving range in kilometers."""
        payload = await self._async_get_json(
            f"{DATA_API_BASE_URL}/car/status/{car_id}/dte"
        )
        value = _find_value(payload, ("value", "dte", "distance"))
        if value is None:
            return None
        return _distance_in_kilometers(value, payload.get("unit", 1))

    async def async_get_odometer(self, car_id: str) -> float | None:
        """Return the latest cumulative driving distance in kilometers."""
        payload = await self._async_get_json(
            f"{DATA_API_BASE_URL}/car/status/{car_id}/odometer"
        )
        readings = payload.get("odometers")
        if readings is None or readings == []:
            return None
        if isinstance(readings, dict):
            readings = [readings]
        if not isinstance(readings, list) or not all(
            isinstance(reading, dict) for reading in readings
        ):
            raise KiaApiConnectionError("Kia returned an invalid odometer response")

        latest = max(
            readings,
            key=lambda reading: str(
                reading.get("timestamp") or reading.get("date") or ""
            ),
        )
        if latest.get("value") is None:
            return None
        return _distance_in_kilometers(latest["value"], latest.get("unit", 1))

    async def _async_get_json(self, url: str) -> dict[str, Any]:
        """Perform an authenticated GET and decode its JSON response."""
        headers = {"Accept": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        try:
            response = await self._request("GET", url, headers=headers)
            async with response:
                if response.status in (401, 403):
                    raise KiaApiAuthenticationError("Kia authentication failed")
                try:
                    payload = await response.json(content_type=None)
                except (ClientError, ValueError) as err:
                    raise KiaApiConnectionError(
                        "Kia returned an invalid JSON response"
                    ) from err
                if response.status >= 400:
                    error_code = (
                        str(payload.get("errCode"))
                        if isinstance(payload, dict) and payload.get("errCode")
                        else None
                    )
                    if error_code == "5005":
                        raise KiaApiAgreementRequiredError(
                            "Kia requires a personal-data agreement"
                        )
                    raise KiaApiConnectionError(
                        "Kia API request failed with HTTP "
                        f"{response.status}"
                        + (f" ({error_code})" if error_code else "")
                    )
        except KiaApiError:
            raise
        except (ClientError, TimeoutError, ValueError) as err:
            raise KiaApiConnectionError("Unable to communicate with Kia") from err

        if not isinstance(payload, dict):
            raise KiaApiConnectionError("Kia returned an invalid JSON response")
        return payload


def _find_value(payload: Any, keys: tuple[str, ...]) -> Any:
    """Find the first matching scalar in a shallowly varying API response."""
    if isinstance(payload, dict):
        for key in keys:
            if key in payload and not isinstance(payload[key], (dict, list)):
                return payload[key]
        for value in payload.values():
            found = _find_value(value, keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_value(value, keys)
            if found is not None:
                return found
    return None


def _distance_in_kilometers(value: Any, unit: Any) -> float:
    """Convert Kia's distance unit codes to kilometers."""
    if isinstance(value, bool) or isinstance(unit, bool):
        raise KiaApiConnectionError("Kia returned an invalid distance")
    try:
        distance = float(value)
        unit_code = int(unit)
    except (TypeError, ValueError, OverflowError) as err:
        raise KiaApiConnectionError("Kia returned an invalid distance") from err
    if not math.isfinite(distance) or distance < 0 or unit_code != unit:
        raise KiaApiConnectionError("Kia returned an invalid distance")
    factors = {0: 0.0003048, 1: 1.0, 2: 0.001, 3: 1.609344}
    if unit_code not in factors:
        raise KiaApiConnectionError("Kia returned an unknown distance unit")
    return distance * factors[unit_code]

