"""Data models for the Kia Developers integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class KiaVehicle:
    """A vehicle returned by Kia Developers."""

    car_id: str
    nickname: str | None = None
    car_type: str | None = None
    name: str | None = None
    sell_name: str | None = None

    @property
    def display_name(self) -> str:
        """Return the best user-facing vehicle name."""
        return self.nickname or self.sell_name or self.name or self.car_id

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> KiaVehicle:
        """Build a vehicle from a Kia API response."""
        car_id = value.get("carId") or value.get("carID") or value.get("id")
        if not isinstance(car_id, str) or not car_id:
            raise ValueError("Vehicle response does not contain a carId")

        return cls(
            car_id=car_id,
            nickname=_optional_string(value.get("carNickname")),
            car_type=_optional_string(value.get("carType")),
            name=_optional_string(value.get("carName")),
            sell_name=_optional_string(value.get("carSellname")),
        )


@dataclass(frozen=True, slots=True)
class KiaVehicleData:
    """Latest data for one Kia vehicle."""

    vehicle: KiaVehicle
    driving_range_km: float | None
    odometer_km: float | None = None
    available: bool = True
    driving_range_available: bool = True
    odometer_available: bool = True


def _optional_string(value: Any) -> str | None:
    """Return a non-empty string or None."""
    return value if isinstance(value, str) and value else None

