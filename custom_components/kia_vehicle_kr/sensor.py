"""Sensor entities for Kia Developers."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KiaConfigEntry
from .entity import KiaVehicleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KiaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Kia sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        sensor
        for vehicle_id in coordinator.vehicle_ids
        for sensor in (
            KiaDrivingRangeSensor(coordinator, vehicle_id),
            KiaOdometerSensor(coordinator, vehicle_id),
        )
    )


class KiaDrivingRangeSensor(KiaVehicleEntity, SensorEntity):
    """Driving range reported by Kia."""

    _attr_translation_key = "driving_range"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:map-marker-distance"

    def __init__(self, coordinator, vehicle_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_driving_range"

    @property
    def native_value(self) -> float | None:
        """Return the latest driving range."""
        data = self.vehicle_data
        return data.driving_range_km if data else None

    @property
    def available(self) -> bool:
        """Return whether the latest driving-range request succeeded."""
        data = self.vehicle_data
        return super().available and data is not None and data.driving_range_available


class KiaOdometerSensor(KiaVehicleEntity, SensorEntity):
    """Cumulative driving distance reported by Kia."""

    _attr_translation_key = "odometer"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, vehicle_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_odometer"

    @property
    def native_value(self) -> float | None:
        """Return the latest odometer reading."""
        data = self.vehicle_data
        return data.odometer_km if data else None

    @property
    def available(self) -> bool:
        """Return whether the latest odometer request succeeded."""
        data = self.vehicle_data
        return super().available and data is not None and data.odometer_available

