"""Shared Kia entity base class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KiaDataUpdateCoordinator
from .models import KiaVehicleData


class KiaVehicleEntity(CoordinatorEntity[KiaDataUpdateCoordinator]):
    """Base class for entities belonging to a Kia vehicle."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KiaDataUpdateCoordinator,
        vehicle_id: str,
    ) -> None:
        """Initialize a vehicle entity."""
        super().__init__(coordinator)
        self.vehicle_id = vehicle_id

    @property
    def vehicle_data(self) -> KiaVehicleData | None:
        """Return current data for this vehicle."""
        return self.coordinator.data.get(self.vehicle_id)

    @property
    def available(self) -> bool:
        """Return whether this vehicle's latest request succeeded."""
        data = self.vehicle_data
        return super().available and data is not None and data.available

    @property
    def device_info(self) -> DeviceInfo:
        """Return the Home Assistant device description."""
        data = self.vehicle_data
        name = data.vehicle.display_name if data else self.vehicle_id
        model = "KIA Connect KR"
        if data:
            model = (
                data.vehicle.sell_name
                or data.vehicle.name
                or data.vehicle.car_type
                or model
            )
        return DeviceInfo(
            identifiers={(DOMAIN, self.vehicle_id)},
            manufacturer="KIA",
            model=model,
            name=name,
        )

