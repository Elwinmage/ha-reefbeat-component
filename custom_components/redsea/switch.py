"""Switch entities for the Red Sea ReefBeat integration.

This module implements Home Assistant `switch` entities for ReefBeat devices.

Goals (HA 2025.12 + strict typing)
----------------------------------
- Use idiomatic Home Assistant patterns:
  - `async_setup_entry` to create entities
  - entities subscribe to coordinator updates via `async_add_listener`
  - avoid direct use of protected members (no `device._hass`)
- Keep type checking clean under Pylance strict / Ruff:
  - define description dataclasses with explicit types
  - narrow device types via `isinstance`
  - avoid `type(x).__name__` / base-name string checks
- Use list `.extend(...)` / `.append(...)` (avoid `+=` for clarity)
- Avoid mutating shared `DeviceInfo` dicts; clone before customizing.

Notes
-----
This file previously used `CoordinatorEntity` from `homeassistant.helpers.update_coordinator`
but the integration’s coordinators are custom (not necessarily `DataUpdateCoordinator`).
To keep behavior consistent with other platforms in this repo (sensor/select),
we use `device.async_add_listener(...)` and update state from device cache.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Protocol, cast, runtime_checkable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType

from .const import (
    ATO_AUTO_FILL_INTERNAL_NAME,
    COMMON_CLOUD_CONNECTION,
    COMMON_MAINTENANCE_SWITCH,
    COMMON_ON_OFF_SWITCH,
    DOMAIN,
    FULLCUP_ENABLED_INTERNAL_NAME,
    LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
    LED_MOONPHASE_ENABLED_INTERNAL_NAME,
    MAT_AUTO_ADVANCE_INTERNAL_NAME,
    MAT_SCHEDULE_ADVANCE_INTERNAL_NAME,
    OVERSKIMMING_ENABLED_INTERNAL_NAME,
)
from .coordinator import (
    ReefATOCoordinator,
    ReefBeatCloudCoordinator,
    ReefBeatCoordinator,
    ReefDoseCoordinator,
    ReefLedCoordinator,
    ReefLedG2Coordinator,
    ReefMatCoordinator,
    ReefRunCoordinator,
    ReefVirtualLedCoordinator,
)
from .entity import ReefBeatRestoreEntity, RestoreSpec

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Protocols (capability-based typing)
# -----------------------------------------------------------------------------


@runtime_checkable

# =============================================================================
# Classes
# =============================================================================

class _CloudLinkedCoordinator(Protocol):
    """Coordinator capability: cloud-linked device."""

    def cloud_link(self) -> StateType: ...


@runtime_checkable
class _HasPressDelete(Protocol):
    """Coordinator capability: can press/delete/fetch_config."""

    async def press(self, cmd: str) -> None: ...
    async def delete(self, path: str) -> None: ...
    async def fetch_config(self, path: str) -> None: ...


@runtime_checkable
class _HasPushValuesBySource(Protocol):
    """Coordinator capability: push cached values for a source and refresh."""

    async def push_values(self, source: str, method: str = "put") -> None: ...
    async def async_quick_request_refresh(self, source: str) -> None: ...


@runtime_checkable
class _DosePush(Protocol):
    """Coordinator capability: push values for a dosing head."""

    async def push_values(self, head: int) -> None: ...
    async def async_quick_request_refresh(self, source: str) -> None: ...


@runtime_checkable
class _RunPush(Protocol):
    """Coordinator capability: push values for run pumps.

    The existing coordinator API in this repo uses `push_values(source, method)`
    for most devices, so RUN switches should generally use that form.
    """

    async def push_values(self, source: str, method: str = "put") -> None: ...
    async def async_quick_request_refresh(self, source: str) -> None: ...


# -----------------------------------------------------------------------------
# Entity descriptions
# -----------------------------------------------------------------------------


@dataclass(kw_only=True, frozen=True)
class ReefBeatSwitchEntityDescription(SwitchEntityDescription):
    """Description for generic device switches.

    - `value_name` points to the underlying cache path / key used by the coordinator.
    - `method` indicates the HTTP verb used by `push_values` when applicable.
    - `icon_off` is used when state is off (HA does not auto-handle this).
    - `notify` optionally fires an HA bus event when toggled (used by dose/run).
    """

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = ""
    icon_off: str = ""
    method: str = "put"
    notify: bool = False


@dataclass(kw_only=True, frozen=True)
class ReefLedSwitchEntityDescription(SwitchEntityDescription):
    """Description for LED-specific switches."""

    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_name: str = ""
    icon_off: str = ""
    method: str = "put"
    notify: bool = False


@dataclass(kw_only=True, frozen=True)
class ReefDoseSwitchEntityDescription(SwitchEntityDescription):
    """Description for per-head dosing switches."""

    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: str = ""
    icon_off: str = ""
    head: int = 0
    method: str = "put"
    notify: bool = False


@dataclass(kw_only=True, frozen=True)
class ReefRunSwitchEntityDescription(SwitchEntityDescription):
    """Description for per-pump run switches."""

    exists_fn: Callable[[ReefRunCoordinator], bool] = lambda _: True
    value_name: str = ""
    icon_off: str = ""
    pump: int = 0
    method: str = "put"
    notify: bool = False


@dataclass(kw_only=True, frozen=True)
class SaveStateSwitchEntityDescription(SwitchEntityDescription):
    """Description for switches that persist their state locally across restarts."""

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    icon_off: str = ""


DescriptionT = (
    ReefBeatSwitchEntityDescription
    | ReefLedSwitchEntityDescription
    | ReefDoseSwitchEntityDescription
    | ReefRunSwitchEntityDescription
    | SaveStateSwitchEntityDescription
)

# -----------------------------------------------------------------------------
# Static descriptions
# -----------------------------------------------------------------------------

SAVE_STATE_SWITCHES: tuple[SaveStateSwitchEntityDescription, ...] = (
    SaveStateSwitchEntityDescription(
        key="use_cloud_api",
        translation_key="use_cloud_api",
        icon="mdi:cloud-check-variant",
        icon_off="mdi:cloud-cancel",
        entity_category=EntityCategory.CONFIG,
    ),
)

COMMON_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="device_state",
        translation_key="device_state",
        value_name=COMMON_ON_OFF_SWITCH,
        icon="mdi:power-plug",
        icon_off="mdi:power-plug-off",
        method="post",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatSwitchEntityDescription(
        key="cloud_connect",
        translation_key="cloud_connect",
        value_name=COMMON_CLOUD_CONNECTION,
        icon="mdi:cloud-check-variant-outline",
        icon_off="mdi:cloud-cancel-outline",
        method="post",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatSwitchEntityDescription(
        key="maintenance",
        translation_key="maintenance",
        value_name=COMMON_MAINTENANCE_SWITCH,
        icon="mdi:account-wrench",
        icon_off="mdi:account-wrench-outline",
        method="post",
        entity_category=EntityCategory.CONFIG,
    ),
)

LED_SWITCHES: tuple[ReefLedSwitchEntityDescription, ...] = (
    ReefLedSwitchEntityDescription(
        key="sw_acclimation_enabled",
        translation_key="acclimation",
        value_name=LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
        icon="mdi:fish",
        method="post",
        entity_category=EntityCategory.CONFIG,
        notify=True,
    ),
    ReefLedSwitchEntityDescription(
        key="sw_moonphase_enabled",
        translation_key="moon_phase",
        value_name=LED_MOONPHASE_ENABLED_INTERNAL_NAME,
        icon="mdi:weather-night",
        method="post",
        entity_category=EntityCategory.CONFIG,
        notify=True,
    ),
)

MAT_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="auto_advance",
        translation_key="auto_advance",
        value_name=MAT_AUTO_ADVANCE_INTERNAL_NAME,
        icon="mdi:auto-mode",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatSwitchEntityDescription(
        key="scheduled_advance",
        translation_key="scheduled_advance",
        value_name=MAT_SCHEDULE_ADVANCE_INTERNAL_NAME,
        icon="mdi:auto-mode",
        entity_category=EntityCategory.CONFIG,
    ),
)

ATO_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="auto_fill",
        translation_key="auto_fill",
        value_name=ATO_AUTO_FILL_INTERNAL_NAME,
        icon="mdi:waves-arrow-up",
        entity_category=EntityCategory.CONFIG,
    ),
)

RUN_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="fullcup_enabled",
        translation_key="fullcup_enabled",
        value_name=FULLCUP_ENABLED_INTERNAL_NAME,
        icon="mdi:cup",
        icon_off="mdi:cup-off",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatSwitchEntityDescription(
        key="overskimming_enabled",
        translation_key="overskimming_enabled",
        value_name=OVERSKIMMING_ENABLED_INTERNAL_NAME,
        icon="mdi:stack-overflow",
        entity_category=EntityCategory.CONFIG,
    ),
)


# -----------------------------------------------------------------------------
# Platform setup
# -----------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities for a config entry."""
    device = cast(ReefBeatCoordinator, hass.data[DOMAIN][entry.entry_id])
    entities: list[SwitchEntity] = []

    _LOGGER.debug("SWITCHES")

    if isinstance(device, _CloudLinkedCoordinator) and not isinstance(
        device, ReefVirtualLedCoordinator
    ):
        entities.extend(
            SaveStateSwitchEntity(device, description)
            for description in SAVE_STATE_SWITCHES
            if description.exists_fn(device)
        )

    if isinstance(
        device, (ReefLedCoordinator, ReefVirtualLedCoordinator, ReefLedG2Coordinator)
    ):
        led_device = cast(ReefLedCoordinator, device)
        entities.extend(
            ReefLedSwitchEntity(device, description)
            for description in LED_SWITCHES
            if description.exists_fn(led_device)
        )

    elif isinstance(device, ReefMatCoordinator):
        entities.extend(
            ReefBeatSwitchEntity(device, description)
            for description in MAT_SWITCHES
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefATOCoordinator):
        entities.extend(
            ReefBeatSwitchEntity(device, description)
            for description in ATO_SWITCHES
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefRunCoordinator):
        entities.extend(
            ReefBeatSwitchEntity(device, description)
            for description in RUN_SWITCHES
            if description.exists_fn(device)
        )

        run_descs: list[ReefRunSwitchEntityDescription] = []
        for pump in range(1, 3):
            run_descs.append(
                ReefRunSwitchEntityDescription(
                    key="schedule_enabled_pump_" + str(pump),
                    translation_key="schedule_enabled",
                    icon="mdi:pump",
                    icon_off="mdi:pump-off",
                    value_name="$.sources[?(@.name=='/pump/settings')].data.pump_"
                    + str(pump)
                    + ".schedule_enabled",
                    pump=pump,
                    entity_category=EntityCategory.CONFIG,
                )
            )

        entities.extend(
            ReefRunSwitchEntity(device, description)
            for description in run_descs
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefDoseCoordinator):
        dose_descs: list[ReefDoseSwitchEntityDescription] = []
        for head in range(1, int(device.heads_nb) + 1):
            dose_descs.append(
                ReefDoseSwitchEntityDescription(
                    key="schedule_enabled_head_" + str(head),
                    translation_key="schedule_enabled",
                    icon="mdi:pump",
                    icon_off="mdi:pump-off",
                    value_name="$.sources[?(@.name=='/head/"
                    + str(head)
                    + "/settings')].data.schedule_enabled",
                    head=head,
                    entity_category=EntityCategory.CONFIG,
                )
            )
            dose_descs.append(
                ReefDoseSwitchEntityDescription(
                    key="slm_head_" + str(head),
                    translation_key="slm",
                    icon="mdi:hydraulic-oil-level",
                    value_name="$.sources[?(@.name=='/head/"
                    + str(head)
                    + "/settings')].data.slm",
                    head=head,
                    entity_category=EntityCategory.CONFIG,
                    notify=True,
                )
            )

        entities.extend(
            ReefDoseSwitchEntity(device, description)
            for description in dose_descs
            if description.exists_fn(device)
        )

    if not isinstance(device, ReefBeatCloudCoordinator):
        entities.extend(
            ReefBeatSwitchEntity(device, description)
            for description in COMMON_SWITCHES
            if description.exists_fn(device)
        )

    async_add_entities(entities, True)


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


# SAVESTATE
class SaveStateSwitchEntity(RestoreEntity, SwitchEntity):
    """Switch that persists simple local state in the coordinator cache.

    Uses RestoreEntity to restore the last HA state, then mirrors the boolean into
    the coordinator cache at `$.local.<key>`.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: SaveStateSwitchEntityDescription,
    ) -> None:
        super().__init__()
        self._device = device
        self.entity_description = cast(SwitchEntityDescription, entity_description)
        self._desc: SaveStateSwitchEntityDescription = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"

    def _set_icon(self) -> None:
        if not self._attr_is_on and self._desc.icon_off:
            self._attr_icon = self._desc.icon_off
        else:
            self._attr_icon = self._desc.icon

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self._set_icon()
        self._device.set_data("$.local." + self._desc.key, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._set_icon()
        self._device.set_data("$.local." + self._desc.key, False)
        self.async_write_ha_state()
        await self.async_get_last_state()

    async def async_added_to_hass(self) -> None:
        """Restore last known state and prime from coordinator cache."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is None:
            self._attr_is_on = True
        else:
            self._attr_is_on = state.state == "on"
        self._set_icon()
        self._device.set_data(
            "$.local." + self.entity_description.key, self._attr_is_on
        )
        self.async_write_ha_state()

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        return self._device.device_info


# REEFBEAT
class ReefBeatSwitchEntity(ReefBeatRestoreEntity, SwitchEntity):  # type: ignore[reportIncompatibleVariableOverride]
    """Base switch entity backed by the ReefBeat coordinator cache."""

    _attr_has_entity_name = True

    @staticmethod
    def _restore_is_on(state: str) -> bool:
        return state == "on"

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefBeatSwitchEntityDescription,
    ) -> None:
        ReefBeatRestoreEntity.__init__(
            self,
            device,
            restore=RestoreSpec("_attr_is_on", self._restore_is_on),
        )
        self._device = device

        self.entity_description = cast(SwitchEntityDescription, entity_description)
        self._desc: ReefBeatSwitchEntityDescription = entity_description

        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_is_on: bool | None = False

        # Some value_name entries embed a source name in quotes; keep best-effort.
        self._source: str = ""
        try:
            self._source = self._desc.value_name.split("'")[1]
        except IndexError:
            self._source = ""

    async def async_added_to_hass(self) -> None:
        """Register listeners and restore the last state on Home Assistant restart."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            if self._attr_is_on is None or not self._attr_available:
                self._attr_is_on = last_state.state == "on"
                self._attr_available = True
                self.async_write_ha_state()

        # Prime state from the coordinator cache immediately after (optional) restore.
        self._handle_coordinator_update()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update cached `_attr_*` values from coordinator data."""
        self._attr_available = True
        self._attr_is_on = self._compute_is_on()
        self._set_icon()
        super()._handle_coordinator_update()

    def _compute_is_on(self) -> bool:
        raw = self._device.get_data(self._desc.value_name)

        if self._desc.key == "device_state":
            return raw != "off"
        if self._desc.key == "maintenance":
            return raw == "maintenance"
        return bool(raw)

    def _set_icon(self) -> None:
        if self._attr_is_on:
            self._attr_icon = self._desc.icon
        elif self._desc.icon_off:
            self._attr_icon = self._desc.icon_off

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self._set_icon()

        if self._desc.key == "device_state":
            self._device.set_data(self._desc.value_name, "auto")
            self._device.async_update_listeners()
            self.async_write_ha_state()
            await cast(_HasPressDelete, self._device).delete("/off")
            return

        if self._desc.key == "maintenance":
            self._device.set_data(self._desc.value_name, "maintenance")
            self._device.async_update_listeners()
            self.async_write_ha_state()
            await cast(_HasPressDelete, self._device).press("maintenance")
            return

        if self._desc.key == "cloud_connect":
            await cast(_HasPressDelete, self._device).press("cloud/enable")
            self._device.set_data(self._desc.value_name, True)
            self.async_write_ha_state()
            return

        self._device.set_data(self._desc.value_name, True)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        if self._source:
            pusher = cast(_HasPushValuesBySource, self._device)
            await pusher.push_values(self._source, self._desc.method)
            await pusher.async_request_refresh(source=self._source)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._set_icon()

        if self._desc.key == "device_state":
            self._device.set_data(self._desc.value_name, "off")
            self._device.async_update_listeners()
            self.async_write_ha_state()
            await cast(_HasPressDelete, self._device).press("off")
            return

        if self._desc.key == "maintenance":
            self._device.set_data(self._desc.value_name, "auto")
            self.async_write_ha_state()
            helper = cast(_HasPressDelete, self._device)
            await helper.delete("/maintenance")
            await helper.fetch_config("/mode")
            return

        if self._desc.key == "cloud_connect":
            self._device.set_data(self._desc.value_name, False)
            await cast(_HasPressDelete, self._device).press("cloud/disable")
            self.async_write_ha_state()
            return

        self._device.set_data(self._desc.value_name, False)
        self._device.async_update_listeners()
        self.async_write_ha_state()

        if self._source:
            pusher = cast(_HasPushValuesBySource, self._device)
            await pusher.push_values(self._source, self._desc.method)
            await pusher.async_request_refresh(source=self._source)

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        return self._device.device_info


# REEFLED
class ReefLedSwitchEntity(ReefBeatSwitchEntity):
    """LED switch entity.

    Uses the base cache-first behavior. Typed description is stored separately to
    avoid invariant override issues in Pylance.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefLedSwitchEntityDescription,
    ) -> None:
        super().__init__(
            device, cast(ReefBeatSwitchEntityDescription, entity_description)
        )
        self._typed_desc: ReefLedSwitchEntityDescription = entity_description
        self.entity_description = cast(SwitchEntityDescription, entity_description)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self._set_icon()

        self._device.set_data(self._typed_desc.value_name, True)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        if self._source:
            pusher = cast(_HasPushValuesBySource, self._device)
            await pusher.push_values(self._source, self._typed_desc.method)
            await pusher.async_request_refresh(source=self._source)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._set_icon()

        self._device.set_data(self._typed_desc.value_name, False)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        if self._source:
            pusher = cast(_HasPushValuesBySource, self._device)
            await pusher.push_values(self._source, self._typed_desc.method)
            await pusher.async_request_refresh(source=self._source)


# REEFDOSE
class ReefDoseSwitchEntity(ReefBeatSwitchEntity):
    """Per-head dosing switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefDoseSwitchEntityDescription,
    ) -> None:
        super().__init__(
            device, cast(ReefBeatSwitchEntityDescription, entity_description)
        )
        self._typed_desc: ReefDoseSwitchEntityDescription = entity_description
        self.entity_description = cast(SwitchEntityDescription, entity_description)
        self._head: int = entity_description.head

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self._set_icon()

        self._device.set_data(self._typed_desc.value_name, True)
        self._device.async_update_listeners()
        self.async_write_ha_state()

        if self._typed_desc.notify:
            self._device.hass.bus.fire(self._typed_desc.value_name, {})
        dose = cast(_DosePush, self._device)
        await dose.push_values(self._head)
        await dose.async_request_refresh(
            source="/head/" + str(self._head) + "/settings"
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._set_icon()

        self._device.set_data(self._typed_desc.value_name, False)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        if self._typed_desc.notify:
            self._device.hass.bus.fire(self._typed_desc.value_name, {})

        dose = cast(_DosePush, self._device)
        await dose.push_values(self._head)
        await dose.async_request_refresh(
            source="/head/" + str(self._head) + "/settings"
        )

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        if self._head <= 0:
            return self._device.device_info

        base_di = dict(self._device.device_info)
        base_identifiers = base_di.get("identifiers") or {(DOMAIN, self._device.serial)}
        domain, ident = next(iter(cast(set[tuple[str, str]], base_identifiers)))

        # DeviceInfo is a TypedDict; copying values from a generic dict makes mypy/pyright
        # widen types to object | None, so we guard and only assign strings (or omit keys).
        di_dict: dict[str, Any] = {
            "identifiers": {(domain, ident, f"head_{self._head}")},
            "name": f"{self._device.title} head {self._head}",
        }

        for key in ("manufacturer", "model", "model_id", "hw_version", "sw_version"):
            val = base_di.get(key)
            if isinstance(val, str) or val is None:
                di_dict[key] = val

        via_device = base_di.get("via_device")
        if via_device is not None:
            di_dict["via_device"] = via_device

        return cast(DeviceInfo, di_dict)


# REEFRUN
class ReefRunSwitchEntity(ReefBeatSwitchEntity):
    """Per-pump ReefRun switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefRunSwitchEntityDescription,
    ) -> None:
        super().__init__(
            device, cast(ReefBeatSwitchEntityDescription, entity_description)
        )
        self._typed_desc: ReefRunSwitchEntityDescription = entity_description
        self.entity_description = cast(SwitchEntityDescription, entity_description)
        self._pump: int = entity_description.pump

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self._set_icon()

        self._device.set_data(self._typed_desc.value_name, True)
        self._device.async_update_listeners()
        self.async_write_ha_state()

        if self._typed_desc.notify:
            self._device.hass.bus.fire(self._typed_desc.value_name, {})

        run = cast(_RunPush, self._device)
        await run.push_values("/pump/settings", self._typed_desc.method, self._pump)
        await run.async_request_refresh(source="/pump/settings")

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._set_icon()

        self._device.set_data(self._typed_desc.value_name, False)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        if self._typed_desc.notify:
            self._device.hass.bus.fire(self._typed_desc.value_name, {})
        run = cast(_RunPush, self._device)
        await run.push_values("/pump/settings", self._typed_desc.method, self._pump)
        await run.async_request_refresh(source="/pump/settings")

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        di = dict(self._device.device_info)
        di["name"] = f"{di.get('name', '')}_pump_{self._pump}"

        identifiers_set = di.get("identifiers")
        if identifiers_set:
            base = next(iter(cast(set[tuple[Any, ...]], identifiers_set)))
            di["identifiers"] = {tuple(base) + (f"pump_{self._pump}",)}
        return cast(DeviceInfo, di)
