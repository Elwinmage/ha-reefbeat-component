"""Entities of a device group (virtual LED): its staggered sunrise.

- switch  staggered_sunrise   each lamp of the group starts its day later
                              than the previous one (group order)
- number  staggered_delay     minutes between two lamps (1-15, as the app)

They read and write the group's GroupStore; turning the staggered sunrise
on, off or changing the delay writes the offset of every lamp (refused,
nothing changed, when a lamp of the group is missing).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from .const import STAGGERED_DELAY_MAX, STAGGERED_DELAY_MIN
from .groups import GroupStore

# Name of the store attribute on a group's coordinator
STORE_ATTR = "group_store"


class GroupSettingEntity(Entity):
    """An entity showing one setting of the GroupStore."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: Any, key: str) -> None:
        self._device = device
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{device.serial}_{key}"
        self._attr_device_info = device.device_info
        # Stable role for the card and blueprints (see ReefRoleMixin)
        self._attr_extra_state_attributes = {"reef_role": key}
        self._unsub: Callable[[], None] | None = None

    @property
    def _store(self) -> GroupStore:
        return getattr(self._device, STORE_ATTR)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _changed() -> None:
            self.async_write_ha_state()

        self._unsub = self._store.async_add_listener(_changed)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()


class StaggeredSunriseSwitch(GroupSettingEntity, SwitchEntity):
    """Staggered sunrise of the group on / off."""

    _attr_icon = "mdi:weather-sunset-up"

    @property
    def is_on(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._store.staggered

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._device.async_set_staggered(staggered=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._device.async_set_staggered(staggered=False)


class StaggeredDelayNumber(GroupSettingEntity, NumberEntity):
    """Minutes between the sunrises of two lamps of the group."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-sand"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = STAGGERED_DELAY_MIN
    _attr_native_max_value = STAGGERED_DELAY_MAX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self) -> float:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._store.delay

    async def async_set_native_value(self, value: float) -> None:
        await self._device.async_set_staggered(delay=value)


def group_entities(device: Any, platform: str) -> list[Any]:
    """Group entities of a platform, for a group holding a GroupStore."""
    if not isinstance(getattr(device, STORE_ATTR, None), GroupStore):
        return []
    builders: dict[str, Callable[[], list[Any]]] = {
        "switch": lambda: [StaggeredSunriseSwitch(device, "staggered_sunrise")],
        "number": lambda: [StaggeredDelayNumber(device, "staggered_delay")],
    }
    build = builders.get(platform)
    return build() if build else []
