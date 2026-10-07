"""Entities of a ReefWave's group: whether the pump is grouped.

- switch  wave_grouped   the pump belongs to its aquarium's ReefWave group,
                         as in the ReefBeat app (all the grouped ReefWaves of
                         an aquarium form one group)

It reads the account's device list (cloud) and writes through the cloud
(POST /device/<hwid>/group, /ungroup): without a cloud account there is no
group, and the switch is unavailable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import callback


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
