"""Entities of a ReefWave's group: whether the pump is grouped, and its
GPS weather mode.

- switch  wave_grouped   the pump belongs to its aquarium's ReefWave group,
                         as in the ReefBeat app (all the grouped ReefWaves of
                         an aquarium form one group)
- switch  wave_weather   the pump's speeds follow the weather of a place
                         (see wave_weather); turned on or off for the whole
                         group

It reads the account's device list (cloud) and writes through the cloud
(POST /device/<hwid>/group, /ungroup): without a cloud account there is no
group, and the switch is unavailable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import callback

from .wave_weather import save_wave_weather, store_of


class WaveGroupSwitchEntity(SwitchEntity):
    """Grouped with the aquarium's other ReefWaves."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: Any, description: SwitchEntityDescription) -> None:
        self._device = device
        self.entity_description = description
        self._attr_unique_id = f"{device.serial}_{description.key}"
        self._attr_device_info = device.device_info
        self._unsub: Callable[[], None] | None = None

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Only with a cloud account: the group lives there."""
        return self._device.wave_grouped() is not None

    @property
    def is_on(self) -> bool | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._device.wave_grouped()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._device.set_wave_grouped(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._device.set_wave_grouped(False)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _changed() -> None:
            self.async_write_ha_state()

        self._unsub = self._device.async_add_listener(_changed)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()


WAVE_WEATHER_ATTRS = (
    "status",
    "error",
    "updated",
    "source",
    "fallback",
    "sunrise",
    "sunset",
    "offset",
    "speeds",
)


class WaveWeatherSwitchEntity(SwitchEntity):
    """The pump's speeds follow the weather of a place (its whole group)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: Any, description: SwitchEntityDescription) -> None:
        self._device = device
        self.entity_description = description
        self._attr_unique_id = f"{device.serial}_{description.key}"
        self._attr_device_info = device.device_info
        self._unsub: Callable[[], None] | None = None

    @property
    def is_on(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        store = store_of(self._device)
        return store is not None and store.settings.enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """The last weather program: its place's day and its speeds."""
        store = store_of(self._device)
        if store is None or not store.result:
            return None
        return {k: store.result[k] for k in WAVE_WEATHER_ATTRS if k in store.result}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await save_wave_weather(self.hass, self._device, None, None, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await save_wave_weather(self.hass, self._device, None, None, False)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        store = store_of(self._device)

        @callback
        def _changed() -> None:
            self.async_write_ha_state()

        if store is not None:
            self._unsub = store.async_add_listener(_changed)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()
