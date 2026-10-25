"""Data coordinator for Kia Developers."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    KiaApiAuthenticationError,
    KiaApiConnectionError,
    KiaDevelopersApi,
)
from .const import DOMAIN
from .models import KiaVehicle, KiaVehicleData

_LOGGER = logging.getLogger(__name__)


class KiaDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, KiaVehicleData]]
):
    """Coordinate Kia requests for all selected vehicles."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: KiaDevelopersApi,
        vehicle_ids: list[str],
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            config_entry=entry,
            update_interval=update_interval,
            always_update=False,
        )
        self.api = api
        self.vehicle_ids = frozenset(vehicle_ids)

    async def _async_update_data(self) -> dict[str, KiaVehicleData]:
        """Fetch vehicle metadata, driving ranges and odometers."""
        try:
            available_vehicles = {
                vehicle.car_id: vehicle
                for vehicle in await self.api.async_get_vehicles()
            }
        except KiaApiAuthenticationError as err:
            raise ConfigEntryAuthFailed("Kia authentication expired") from err
        except KiaApiConnectionError as err:
            raise UpdateFailed(str(err)) from err

        selected = [
            available_vehicles[vehicle_id]
            for vehicle_id in self.vehicle_ids
            if vehicle_id in available_vehicles
        ]
        if not selected:
            raise UpdateFailed("None of the selected Kia vehicles are available")

        results = await asyncio.gather(
            *(self._async_update_vehicle(vehicle) for vehicle in selected),
            return_exceptions=True,
        )

        data: dict[str, KiaVehicleData] = {}
        authentication_error: KiaApiAuthenticationError | None = None
        for vehicle, result in zip(selected, results, strict=True):
            if isinstance(result, KiaApiAuthenticationError):
                authentication_error = result
            elif isinstance(result, Exception):
                data[vehicle.car_id] = KiaVehicleData(
                    vehicle=vehicle,
                    driving_range_km=None,
                    available=False,
                    driving_range_available=False,
                    odometer_available=False,
                )
            else:
                data[vehicle.car_id] = result

        if authentication_error is not None:
            raise ConfigEntryAuthFailed(
                "Kia authentication expired"
            ) from authentication_error
        return data

    async def _async_update_vehicle(self, vehicle: KiaVehicle) -> KiaVehicleData:
        """Fetch data for one vehicle."""
        driving_range, odometer = await asyncio.gather(
            self.api.async_get_driving_range(vehicle.car_id),
            self.api.async_get_odometer(vehicle.car_id),
            return_exceptions=True,
        )
        if isinstance(driving_range, KiaApiAuthenticationError):
            raise driving_range
        if isinstance(driving_range, asyncio.CancelledError):
            raise driving_range
        if isinstance(odometer, asyncio.CancelledError):
            raise odometer

        range_available = not isinstance(driving_range, BaseException)
        odometer_available = not isinstance(odometer, BaseException)
        if isinstance(odometer, KiaApiAuthenticationError) and not range_available:
            raise odometer
        if not range_available:
            _LOGGER.warning("Kia driving range is unavailable for a vehicle")
        if not odometer_available:
            _LOGGER.warning("Kia odometer is unavailable for a vehicle")

        return KiaVehicleData(
            vehicle=vehicle,
            driving_range_km=driving_range if range_available else None,
            odometer_km=odometer if odometer_available else None,
            available=range_available or odometer_available,
            driving_range_available=range_available,
            odometer_available=odometer_available,
        )

