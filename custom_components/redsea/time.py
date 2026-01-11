"""Time platform for the Red Sea ReefBeat integration.

Exposes device configuration times (minutes since midnight in the device cache)
as Home Assistant `time` entities.

HA 2025.12 notes:
- Avoid `type(x).__name__` checks; use `isinstance`.
- Use `entities.extend(...)` instead of `+= [...]`.
- Keep `entity_description` as the HA base type, store typed description separately.
- Subscribe to coordinator updates via the coordinator's listener mechanism.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import time as dt_time
from functools import cached_property
from typing import cast

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ReefMatCoordinator

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Entity descriptions
# =============================================================================


@dataclass(kw_only=True, frozen=True)
class ReefMatTimeEntityDescription(TimeEntityDescription):
    """Describes a ReefMat time entity."""

    value_name: str
    exists_fn: Callable[[ReefMatCoordinator], bool] = lambda _: True


MAT_TIMES: tuple[ReefMatTimeEntityDescription, ...] = (
    ReefMatTimeEntityDescription(
        key="schedule_time",
        translation_key="schedule_time",
        value_name="$.sources[?(@.name=='/configuration')].data.schedule_time",
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
    ),
)


# =============================================================================
# Platform setup
# =============================================================================


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up time entities for a config entry."""
    device = cast(ReefMatCoordinator, hass.data[DOMAIN][config_entry.entry_id])

    entities: list[TimeEntity] = []
    _LOGGER.debug("TIMES")

    entities.extend(
        ReefMatTimeEntity(device, description)
        for description in MAT_TIMES
        if description.exists_fn(device)
    )

    async_add_entities(entities, True)


# =============================================================================
# Entities
# =============================================================================


class ReefMatTimeEntity(TimeEntity):
    """ReefMat time entity backed by the coordinator cache."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefMatCoordinator,
        entity_description: ReefMatTimeEntityDescription,
    ) -> None:
        super().__init__()
        self._device = device

        # Keep HA typing for entity_description; store typed description separately.
        self.entity_description = cast(TimeEntityDescription, entity_description)
        self._desc: ReefMatTimeEntityDescription = entity_description

        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"

        self._attr_native_value = self._minutes_to_time(
            cast(int | None, self._device.get_data(self._desc.value_name))
        )

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener after entity is added to HA."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._device.async_add_listener(self._handle_device_update)
        )
        self._handle_device_update()

    @callback
    def _handle_device_update(self) -> None:
        """Handle updated data from the coordinator cache."""
        self._attr_available = True
        minutes = cast(int | None, self._device.get_data(self._desc.value_name))
        self._attr_native_value = self._minutes_to_time(minutes)
        self.async_write_ha_state()

    @staticmethod
    def _minutes_to_time(minutes: int | None) -> dt_time | None:
        """Convert minutes since midnight to a `datetime.time`."""
        if minutes is None:
            return None
        minutes = int(minutes)
        return dt_time(minutes // 60, minutes % 60)

    async def async_set_value(self, value: dt_time) -> None:
        """Set the time on the device (stored as minutes since midnight)."""
        self._attr_native_value = value
        mat_value = value.hour * 60 + value.minute

        self._device.set_data(self._desc.value_name, mat_value)
        self._device.async_update_listeners()
        self.async_write_ha_state()

        # ReefMatCoordinator uses a parameterless push for its configuration.
        await self._device.push_values()

    @cached_property  # type: ignore[override]
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info
