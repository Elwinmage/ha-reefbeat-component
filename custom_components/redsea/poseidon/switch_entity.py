"""The Poseidon entities of a device: mode switch, polling pause, strategy.

One per device whose keys are known. It belongs to the Poseidon entry but is
attached to the device's own registry entry (``device_entry``, as helpers
do: identifiers are only unique within a config entry), so it shows on the
device page and goes away with the Poseidon entry.

The mode switch reads its state from the device: ``on`` when ``/cloud.url``
is the relay. No RestoreEntity: what the device says is the truth. The
polling pause is not restored either: a restart always gives the polling
back.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import SIGNAL_POSEIDON_UPDATE, STRATEGIES, STRATEGY_SPY
from .manager import Poseidon


class _PoseidonDeviceEntity:
    """What the Poseidon entities of a device share."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _unique_prefix = "poseidon"

    def __init__(self, poseidon: Poseidon, hwid: str, device: dr.DeviceEntry) -> None:
        self._poseidon = poseidon
        self._hwid = hwid
        self._attr_unique_id = f"{self._unique_prefix}_{hwid}"
        self.device_entry = device

    def _device_ready(self) -> bool:
        coordinator = self._poseidon.coordinator(self._hwid)
        dev = self._poseidon.keystore.get(self._hwid)
        return (
            coordinator is not None
            and bool(getattr(coordinator, "last_update_success", False))
            and dev is not None
            and dev.has_keys
        )


def _connect_updates(entity: Any) -> None:
    entity.async_on_remove(
        async_dispatcher_connect(
            entity.hass, SIGNAL_POSEIDON_UPDATE, entity.async_write_ha_state
        )
    )


class PoseidonSwitch(_PoseidonDeviceEntity, SwitchEntity):
    """Poseidon mode of one device."""

    _attr_translation_key = "poseidon_mode"
    _attr_icon = "redsea:trident"

    async def async_added_to_hass(self) -> None:
        _connect_updates(self)

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._device_ready()

    @property
    def is_on(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._poseidon.in_poseidon(self._poseidon.cached_cloud(self._hwid))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # pyright: ignore[reportIncompatibleVariableOverride]
        cloud = self._poseidon.cached_cloud(self._hwid) or {}
        traffic = self._poseidon.traffic(self._hwid)
        return {
            "connection_state": cloud.get("connection_state"),
            "last_up": traffic.last_up.isoformat() if traffic.last_up else None,
            "last_down": traffic.last_down.isoformat() if traffic.last_down else None,
            # In Poseidon mode, but nothing went through the relay for a while
            "silent": self._poseidon.silent(self._hwid),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._poseidon.async_switch(self._hwid, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._poseidon.async_switch(self._hwid, False)


class PoseidonPollPauseSwitch(_PoseidonDeviceEntity, SwitchEntity):
    """Polling of a device in spy mode paused: no HTTP request at all, for a
    baseline of what the device pushes on its own."""

    _attr_translation_key = "poseidon_poll_pause"
    _attr_icon = "mdi:pause-octagon-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _unique_prefix = "poseidon_poll_pause"

    async def async_added_to_hass(self) -> None:
        _connect_updates(self)

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        return (
            self._device_ready()
            and self._poseidon.active.get(self._hwid) == STRATEGY_SPY
        )

    @property
    def is_on(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._hwid in self._poseidon.paused

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._poseidon.async_set_paused(self._hwid, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._poseidon.async_set_paused(self._hwid, False)


class PoseidonStrategySelect(_PoseidonDeviceEntity, SelectEntity):
    """Strategy of a device while it is in Poseidon mode."""

    _attr_translation_key = "poseidon_strategy"
    _attr_icon = "mdi:eye-settings-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(STRATEGIES)
    _unique_prefix = "poseidon_strategy"

    async def async_added_to_hass(self) -> None:
        _connect_updates(self)

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._device_ready()

    @property
    def current_option(self) -> str:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._poseidon.strategy_of(self._hwid)

    async def async_select_option(self, option: str) -> None:
        self._poseidon.async_set_strategy(self._hwid, option)
