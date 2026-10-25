"""Diagnostics for Kia Developers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import KiaConfigEntry

TO_REDACT = {
    "access_token",
    "refresh_token",
    "car_id",
    "carId",
    "userId",
    "masterId",
    "vehicle_ids",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: KiaConfigEntry,
) -> dict[str, Any]:
    """Return safely redacted diagnostics."""
    coordinator = entry.runtime_data.coordinator
    vehicles = [
        {
            "available": data.available,
            "vehicle_type": data.vehicle.car_type,
            "model": data.vehicle.sell_name or data.vehicle.name,
            "has_driving_range": data.driving_range_km is not None,
        }
        for data in coordinator.data.values()
    ]
    return async_redact_data(
        {
            "entry": {
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            "last_update_success": coordinator.last_update_success,
            "vehicles": vehicles,
        },
        TO_REDACT,
    )

