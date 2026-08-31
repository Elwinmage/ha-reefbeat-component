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
from dataclasses import dataclass, field
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
    ATO_BUZZER_ENABLED_INTERNAL_NAME,
    ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME,
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
    REFRESH_DEVICE_DELAY,
    SENSOR_CONTROLLED_REFRESH_DELAY,
)
from .coordinator import (
    ReefATOCoordinator,
    ReefBeatCloudCoordinator,
    ReefBeatCoordinator,
    ReefControlCoordinator,
    ReefDoseCoordinator,
    ReefLedCoordinator,
    ReefLedG2Coordinator,
    ReefMatCoordinator,
    ReefPowerCoordinator,
    ReefRunCoordinator,
    ReefVirtualLedCoordinator,
)
from .entity import ReefBeatRestoreEntity, ReefRoleMixin, RestoreSpec
from .maintenance import (
    PROBE_SCOPES,
    MaintenanceStore,
    MaintenanceTask,
    iter_maintenance_probes,
    tasks_for,
)

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
    async def async_request_refresh(self, source: str) -> None: ...
    async def post_specific(self, source: str) -> None: ...
    async def delete(self, source: str) -> None: ...


@runtime_checkable
class _DosePush(Protocol):
    """Coordinator capability: push values for a dosing head."""

    async def push_values(self, head: int) -> None: ...
    async def async_request_refresh(self, source: str) -> None: ...


@runtime_checkable
class _RunPush(Protocol):
    """Coordinator capability: push values for run pumps.

    The existing coordinator API in this repo uses `push_values(source, method)`
    for most devices, so RUN switches should generally use that form.
    """

    async def push_values(
        self, source: str, method: str = "put", pump: int | None = None
    ) -> None: ...
    async def async_request_refresh(
        self,
        source: str | None = None,
        config: bool = False,
        wait: int = REFRESH_DEVICE_DELAY,
    ) -> None: ...


@runtime_checkable
class _CloudPush(Protocol):
    """Coordinator capability: push values for cloud.

    The existing coordinator API in this repo uses `push_values(source, method)`
    for most devices, so CLOUD switches should generally use that form.
    """

    async def async_request_refresh(self, source: str) -> None: ...


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
    - `push_source` overrides the endpoint a toggle is written to. It defaults
      to the source named in `value_name`, which is right whenever a setting
      is read and written at the same place. The ATO leak buzzer is the
      exception: the firmware only accepts it on `/configuration` but reports
      it on the far more frequently polled `/dashboard`, so it is read from
      one and written to the other. The refresh after a push always targets
      the read source, so the device confirms the new value.
    """

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = ""
    icon_off: str = ""
    method: str = "put"
    notify: bool = False
    push_source: str = ""


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
    # Source to re-read after a toggle. None means "refresh every data source",
    # needed when the toggle changes what the pump actually does and therefore
    # /dashboard, not only /pump/settings.
    refresh_source: str | None = "/pump/settings"
    # Seconds to wait before reading the device back
    refresh_wait: int = REFRESH_DEVICE_DELAY


@dataclass(kw_only=True, frozen=True)
class ReefCloudSwitchEntityDescription(SwitchEntityDescription):
    """Description for cloud shortcuts switches."""

    exists_fn: Callable[[ReefBeatCloudCoordinator], bool] = lambda _: True
    shortcut: str = ""
    value_name: str = ""
    icon_off: str = ""
    notify: bool = True
    aquarium: dict = field(default_factory=dict)


@dataclass(kw_only=True, frozen=True)
class ReefPowerSocketSwitchEntityDescription(SwitchEntityDescription):
    """Description for a per-socket toggle switch on a RSPOWER device.

    The switch backs `POST /socket/{n}/toggle`. Because that endpoint is a
    firmware-level toggle (it flips whichever state the socket currently
    holds), the switch has to compare the desired state against the current
    effective state before firing, so that HA-issued `turn_on`/`turn_off`
    do not accidentally invert an already-correct state.
    """

    exists_fn: Callable[[ReefPowerCoordinator], bool] = lambda _: True
    socket: int = 0  # 1-based socket index as used in the URL path
    icon_off: str = ""


@dataclass(kw_only=True, frozen=True)
class ReefControlPortSwitchEntityDescription(SwitchEntityDescription):
    """Description for a per-port toggle switch on a RSCONTROL device.

    Same pattern as sockets: `POST /port/{n}/toggle` is a firmware-level
    flip, so the entity must reconcile desired vs current state before
    firing.
    """

    exists_fn: Callable[[ReefControlCoordinator], bool] = lambda _: True
    port: int = 0  # 1-based port index as used in the URL path
    icon_off: str = ""


@dataclass(kw_only=True, frozen=True)
class ReefControlATOSwitchEntityDescription(SwitchEntityDescription):
    """Description for the per-port ATO auto-fill switch.

    Unlike the port toggle, this switch has a definite state boolean stored
    on the coordinator (`ports[?(@.number==N)].auto_fill`) and its update
    endpoint expects the full config payload, so we don't need any of the
    "compare current vs desired" gymnastics used by the socket/port toggle.
    """

    exists_fn: Callable[[ReefControlCoordinator], bool] = lambda _: True
    port: int = 0
    icon_off: str = ""


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
        icon="mdi:autorenew",
        icon_off="mdi:autorenew-off",
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
    ReefBeatSwitchEntityDescription(
        key="enabled",
        translation_key="enabled",
        value_name=ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME,
        # Read from `/dashboard`, written to `/configuration`, like the
        # buzzer below. See ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME.
        push_source="/configuration",
        icon="mdi:leak",
        icon_off="mdi:leak-off",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatSwitchEntityDescription(
        key="buzzer_enabled",
        translation_key="buzzer_enabled",
        value_name=ATO_BUZZER_ENABLED_INTERNAL_NAME,
        # Read from `/dashboard`, written to `/configuration`: the firmware
        # only accepts the setting there. See ATO_BUZZER_ENABLED_INTERNAL_NAME.
        push_source="/configuration",
        icon="mdi:bell-ring",
        icon_off="mdi:bell-off",
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
        icon="mdi:water-percent",
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
    elif isinstance(device, ReefBeatCloudCoordinator):
        cloud_descs: list[ReefCloudSwitchEntityDescription] = []
        for aquarium in device.get_data("$.sources[?(@.name=='/aquarium')].data"):
            cloud_descs.append(
                ReefCloudSwitchEntityDescription(
                    key="shortcut_emergency_1",
                    translation_key="shortcut_emergency",
                    icon="mdi:hand-back-left-outline",
                    shortcut="$.sources[?(@.name=='/aquarium')].data[?(@.uid='"
                    + aquarium["uid"]
                    + "')].properties.emergency_1",
                    value_name="$.sources[?(@.name=='/aquarium')].data[?(@.uid='"
                    + aquarium["uid"]
                    + "')].properties.emergency_1.enabled",
                    aquarium=aquarium,
                )
            )
            for id in [1, 2, 3]:
                cloud_descs.append(
                    ReefCloudSwitchEntityDescription(
                        key="shortcut_feeding_" + str(id),
                        translation_key="shortcut_feeding",
                        icon="mdi:fish",
                        shortcut="$.sources[?(@.name=='/aquarium')].data[?(@.uid='"
                        + aquarium["uid"]
                        + "')].properties.feeding_"
                        + str(id),
                        value_name="$.sources[?(@.name=='/aquarium')].data[?(@.uid='"
                        + aquarium["uid"]
                        + "')].properties.feeding_"
                        + str(id)
                        + ".enabled",
                        aquarium=aquarium,
                    )
                )
                cloud_descs.append(
                    ReefCloudSwitchEntityDescription(
                        key="shortcut_maintenance_" + str(id),
                        translation_key="shortcut_maintenance",
                        icon="mdi:wrench",
                        shortcut="$.sources[?(@.name=='/aquarium')].data[?(@.uid='"
                        + aquarium["uid"]
                        + "')].properties.maintenance_"
                        + str(id),
                        value_name="$.sources[?(@.name=='/aquarium')].data[?(@.uid='"
                        + aquarium["uid"]
                        + "')].properties.maintenance_"
                        + str(id)
                        + ".enabled",
                        aquarium=aquarium,
                    )
                )

        entities.extend(
            ReefCloudSwitchEntity(device, description)
            for description in cloud_descs
            if description.exists_fn(device)
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
                    icon="mdi:play",
                    icon_off="mdi:pause",
                    value_name="$.sources[?(@.name=='/pump/settings')].data.pump_"
                    + str(pump)
                    + ".schedule_enabled",
                    pump=pump,
                    entity_category=EntityCategory.CONFIG,
                )
            )
            run_descs.append(
                ReefRunSwitchEntityDescription(
                    key="sensor_controlled_pump_" + str(pump),
                    translation_key="sensor_controlled_switch",
                    icon="mdi:car-speed-limiter",
                    icon_off="mdi:car-speed-limiter",
                    value_name="$.sources[?(@.name=='/pump/settings')].data.pump_"
                    + str(pump)
                    + ".sensor_controlled",
                    pump=pump,
                    entity_category=EntityCategory.CONFIG,
                    # Handing control over to the sensor changes the running
                    # intensity, which lives in /dashboard: refresh everything,
                    # and leave the pump time to ramp to its new speed.
                    refresh_source=None,
                    refresh_wait=SENSOR_CONTROLLED_REFRESH_DELAY,
                )
            )

        entities.extend(
            ReefRunSwitchEntity(device, description)
            for description in run_descs
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefPowerCoordinator):
        # Per-socket toggle switch — one per AC socket.
        # Endpoint: `POST /socket/{n}/toggle`; `n` is the 0-based socket
        # index (RSPOWER6 exposes 0..5, RSPOWER8 exposes 0..7). The array
        # index in /dashboard.sockets[] uses the same 0-based scheme.
        # The user-facing display uses n+1 to match the existing sensor /
        # binary_sensor convention in this integration.
        socket_descs: list[ReefPowerSocketSwitchEntityDescription] = []
        for socket_idx in range(device.socket_count):
            socket_descs.append(
                ReefPowerSocketSwitchEntityDescription(
                    key=f"socket_{socket_idx}_on_off",
                    translation_key="socket_on_off",
                    translation_placeholders={"socket": str(socket_idx + 1)},
                    icon="mdi:power-plug",
                    icon_off="mdi:power-plug-off",
                    socket=socket_idx,
                )
            )
        entities.extend(
            ReefPowerSocketSwitchEntity(device, description)
            for description in socket_descs
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefControlCoordinator):
        # Per-port toggle switch — one per 12V DC port.
        # Endpoint: `POST /port/{n}/toggle`; `n` is the 0-based port index
        # (RSCONTROLLITE exposes 0, RSCONTROLPRO exposes 0..1). The array
        # index in /dashboard.ports[] uses the same 0-based scheme.
        port_descs: list[ReefControlPortSwitchEntityDescription] = []
        for port_idx in range(device.port_count):
            port_descs.append(
                ReefControlPortSwitchEntityDescription(
                    key=f"port_{port_idx}_on_off",
                    translation_key="port_on_off",
                    translation_placeholders={"port": str(port_idx + 1)},
                    icon="mdi:electric-switch-closed",
                    icon_off="mdi:electric-switch",
                    port=port_idx,
                )
            )
        entities.extend(
            ReefControlPortSwitchEntity(device, description)
            for description in port_descs
            if description.exists_fn(device)
        )

        # ATO auto-fill switch per ATO port. Discovered by walking the
        # /dashboard payload (`type == "ato"` on a `ports[]` entry), same
        # rule as the sensor/binary_sensor/button platforms. This is
        # coordinator-surface-agnostic.
        raw_ports = device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.ports",
            is_None_possible=True,
        )
        ato_port_indices: list[int] = (
            [
                p["number"]
                for p in raw_ports
                if isinstance(p, dict)
                and p.get("type") == "ato"
                and isinstance(p.get("number"), int)
            ]
            if isinstance(raw_ports, list)
            else []
        )
        ato_switch_descs: list[ReefControlATOSwitchEntityDescription] = []
        for port_idx in ato_port_indices:
            ato_switch_descs.append(
                ReefControlATOSwitchEntityDescription(
                    key=f"port_{port_idx}_ato_auto_fill",
                    translation_key="ato_auto_fill",
                    translation_placeholders={"port": str(port_idx + 1)},
                    icon="mdi:waves-arrow-up",
                    icon_off="mdi:waves",
                    port=port_idx,
                    entity_category=EntityCategory.CONFIG,
                )
            )
        entities.extend(
            ReefControlATOSwitchEntity(device, description)
            for description in ato_switch_descs
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
            dose_descs.append(
                ReefDoseSwitchEntityDescription(
                    key="dose_compensation_head_" + str(head),
                    translation_key="dose_compensation",
                    icon="mdi:water-plus",
                    value_name="$.sources[?(@.name=='/head/"
                    + str(head)
                    + "/settings')].data.dc",
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

    # ---- Maintenance notification switches -----------------------------------
    # One switch per maintenance task instance, mirroring the button/number
    # pair created in button.py / number.py.
    _add_maintenance_notify_switches(device, entities)

    async_add_entities(entities, True)


def _add_maintenance_notify_switches(
    device: ReefBeatCoordinator,
    entities: list[SwitchEntity],
) -> None:
    """Create one MaintenanceNotifySwitchEntity per applicable task instance.

    Mirrors `_add_maintenance_numbers` in number.py: same model lookup, same
    sub-device expansion rules, so the switch always sits next to the button
    and the interval slider of the very same task.
    """
    if isinstance(device, (ReefBeatCloudCoordinator, ReefVirtualLedCoordinator)):
        return

    hw_model = getattr(device, "_hw", None)
    if not isinstance(hw_model, str):
        return

    tasks = tasks_for(hw_model)
    if not tasks:
        return

    for task in tasks:
        if task.applies_to_sub == "head" and isinstance(device, ReefDoseCoordinator):
            for head in range(1, device.heads_nb + 1):
                entities.append(
                    MaintenanceNotifySwitchEntity(device, task, sub_id=head)
                )
        elif task.applies_to_sub in ("pump_return", "pump_skimmer") and isinstance(
            device, ReefRunCoordinator
        ):
            wanted = "return" if task.applies_to_sub == "pump_return" else "skimmer"
            for pump_id in (1, 2):
                try:
                    pump = device.get_data(
                        f"$.sources[?(@.name=='/dashboard')].data.pump_{pump_id}",
                        True,  # is_None_possible
                    )
                except Exception:
                    pump = None
                if isinstance(pump, dict) and pump.get("type") == wanted:
                    entities.append(
                        MaintenanceNotifySwitchEntity(device, task, sub_id=pump_id)
                    )
        elif task.applies_to_sub in PROBE_SCOPES:
            for sub_id, probe_name in iter_maintenance_probes(device, task):
                entities.append(
                    MaintenanceNotifySwitchEntity(
                        device,
                        task,
                        sub_id=sub_id,
                        placeholders={"probe": probe_name},
                    )
                )
        else:
            entities.append(MaintenanceNotifySwitchEntity(device, task, sub_id=0))


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

    @cached_property
    def available(self) -> bool:
        return True

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

        # Where a toggle is written, which is the read source unless the
        # description says otherwise (see `push_source`).
        #
        # Read through getattr: the per-device description dataclasses
        # (ReefLed…, ReefCloud…, ReefRun…) are siblings cast to this type
        # rather than subclasses, so they do not carry the field. Same pattern
        # as `with_attr_name` on the sensor side.
        self._push_source: str = getattr(self._desc, "push_source", "") or self._source

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
            await pusher.push_values(self._push_source, self._desc.method)
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
            await pusher.push_values(self._push_source, self._desc.method)
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
            await pusher.post_specific(self._source)
            await pusher.async_request_refresh(source=self._source)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._set_icon()

        self._device.set_data(self._typed_desc.value_name, False)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        if self._source:
            pusher = cast(_HasPushValuesBySource, self._device)
            await pusher.delete(self._source)
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
        await dose.push_values(head=self._head)
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
        await dose.push_values(head=self._head)
        await dose.async_request_refresh(
            source="/head/" + str(self._head) + "/settings"
        )

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return device info extended with the head identifier (non-mutating)."""
        return cast(ReefDoseCoordinator, self._device).head_device_info(self._head)


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

        await self._push_and_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._set_icon()

        self._device.set_data(self._typed_desc.value_name, False)
        self._device.async_update_listeners()
        self.async_write_ha_state()
        if self._typed_desc.notify:
            self._device.hass.bus.fire(self._typed_desc.value_name, {})
        await self._push_and_refresh()

    async def _push_and_refresh(self) -> None:
        """Send the new value then read the device back.

        Which sources are re-read, and after how long, depends on the switch:
        a schedule toggle only changes /pump/settings, while handing control
        over to the sensor also changes the intensity reported by /dashboard.
        """
        run = cast(_RunPush, self._device)
        await run.push_values(
            source="/pump/settings", method=self._typed_desc.method, pump=self._pump
        )
        await run.async_request_refresh(
            source=self._typed_desc.refresh_source,
            wait=self._typed_desc.refresh_wait,
        )

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return device info extended with the pump identifier."""
        return cast(ReefRunCoordinator, self._device).pump_device_info(self._pump)


# -----------------------------------------------------------------------------
# Shared derivation helper for socket / port state
# -----------------------------------------------------------------------------


# Manual override modes: firmware reports state="unknown" in these modes and
# the effective on/off answer is carried by `mode` itself.
_MANUAL_OVERRIDE_MODES: frozenset[str] = frozenset({"on", "off"})


def _effective_state_is_on(mode: Any, state: Any) -> bool | None:
    """Return the effective on/off state for a RSPOWER socket or RSCONTROL port.

    Mirrors ``_effective_socket_state`` in ``sensor.py`` but returns a bool
    suitable for a switch's ``_attr_is_on``:

        - mode == "on"                            -> True
        - mode == "off"                           -> False
        - state == "on"                           -> True
        - state == "standby" | any other string   -> False
        - both unknown                            -> None (leave as-is)
    """
    if isinstance(mode, str) and mode in _MANUAL_OVERRIDE_MODES:
        return mode == "on"
    if isinstance(state, str):
        return state == "on"
    return None


# REEFPOWER — per-socket toggle
class ReefPowerSocketSwitchEntity(ReefBeatRestoreEntity, SwitchEntity):  # type: ignore[reportIncompatibleVariableOverride]
    """Toggle a single AC socket on a RSPOWER device.

    Backing endpoint: ``POST /socket/{n}/toggle`` with an empty JSON body.
    That endpoint flips whichever state the socket currently holds, so the
    entity guards the call with a desired-vs-effective comparison to avoid
    inverting an already-correct state.
    """

    _attr_has_entity_name = True

    @staticmethod
    def _restore_is_on(state: str) -> bool:
        return state == "on"

    def __init__(
        self,
        device: ReefPowerCoordinator,
        entity_description: ReefPowerSocketSwitchEntityDescription,
    ) -> None:
        ReefBeatRestoreEntity.__init__(
            self,
            device,
            restore=RestoreSpec("_attr_is_on", self._restore_is_on),
        )
        self._device: ReefPowerCoordinator = device
        self._desc: ReefPowerSocketSwitchEntityDescription = entity_description
        self.entity_description = cast(SwitchEntityDescription, entity_description)
        self._socket: int = entity_description.socket

        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_is_on = False

        # Both the URL path and the sockets[] array use the same 0-based
        # index — RSPOWER6 numbers sockets 0..5, RSPOWER8 numbers them 0..7.
        base = f"$.sources[?(@.name=='/dashboard')].data.sockets[{self._socket}]"
        self._mode_path = f"{base}.mode"
        self._state_path = f"{base}.state"
        self._name_path = f"{base}.name"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            if self._attr_is_on is None or not self._attr_available:
                self._attr_is_on = last_state.state == "on"
                self._attr_available = True
                self.async_write_ha_state()

        self._handle_coordinator_update()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_available = True
        effective = _effective_state_is_on(
            self._device.get_data(self._mode_path, is_None_possible=True),
            self._device.get_data(self._state_path, is_None_possible=True),
        )
        if effective is not None:
            self._attr_is_on = effective
        self._set_icon()
        super()._handle_coordinator_update()

    def _set_icon(self) -> None:
        if self._attr_is_on:
            self._attr_icon = self._desc.icon
        elif self._desc.icon_off:
            self._attr_icon = self._desc.icon_off

    async def _send_toggle(self) -> None:
        # `POST /socket/{n}/toggle` with `{}` is a firmware flip.
        await self._device.my_api.http_send(
            f"/socket/{self._socket}/toggle", payload={}, method="post"
        )
        await self._device.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        current = _effective_state_is_on(
            self._device.get_data(self._mode_path, is_None_possible=True),
            self._device.get_data(self._state_path, is_None_possible=True),
        )
        # Optimistic update for immediate UI feedback.
        self._attr_is_on = True
        self._set_icon()
        self.async_write_ha_state()

        # Only toggle if we would actually change the state, so a redundant
        # turn_on from an automation does not accidentally flip a socket
        # that is already on.
        if current is not True:
            await self._send_toggle()

    async def async_turn_off(self, **kwargs: Any) -> None:
        current = _effective_state_is_on(
            self._device.get_data(self._mode_path, is_None_possible=True),
            self._device.get_data(self._state_path, is_None_possible=True),
        )
        self._attr_is_on = False
        self._set_icon()
        self.async_write_ha_state()

        if current is not False:
            await self._send_toggle()

    @property
    def name(self) -> str | None:  # type: ignore[reportIncompatibleVariableOverride]
        """Use the device-provided socket name as the entity's friendly name.

        ``has_entity_name`` is True, so HA prepends the device name — the
        result is e.g. "RSPOWER6 t1". Falls back to "Socket N" if the
        firmware hasn't reported a name yet. This is a plain (non-cached)
        property so a rename via the socket name text entity is reflected
        immediately.
        """
        n = self._device.get_data(self._name_path, is_None_possible=True)
        if isinstance(n, str) and n:
            return n
        return f"Socket {self._socket + 1}"

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        return self._device.device_info


# REEFCONTROL — per-port toggle
class ReefControlPortSwitchEntity(ReefBeatRestoreEntity, SwitchEntity):  # type: ignore[reportIncompatibleVariableOverride]
    """Toggle a single 12V DC port on a RSCONTROL device.

    Backing endpoint: ``POST /port/{n}/toggle``. Same firmware-flip semantics
    as sockets — see :class:`ReefPowerSocketSwitchEntity` for the rationale.
    """

    _attr_has_entity_name = True

    @staticmethod
    def _restore_is_on(state: str) -> bool:
        return state == "on"

    def __init__(
        self,
        device: ReefControlCoordinator,
        entity_description: ReefControlPortSwitchEntityDescription,
    ) -> None:
        ReefBeatRestoreEntity.__init__(
            self,
            device,
            restore=RestoreSpec("_attr_is_on", self._restore_is_on),
        )
        self._device: ReefControlCoordinator = device
        self._desc: ReefControlPortSwitchEntityDescription = entity_description
        self.entity_description = cast(SwitchEntityDescription, entity_description)
        self._port: int = entity_description.port

        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_is_on = False

        # Both the URL path and the ports[] array use the same 0-based index —
        # RSCONTROLLITE numbers its port 0, RSCONTROLPRO numbers them 0..1.
        base = f"$.sources[?(@.name=='/dashboard')].data.ports[{self._port}]"
        self._mode_path = f"{base}.mode"
        self._state_path = f"{base}.state"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            if self._attr_is_on is None or not self._attr_available:
                self._attr_is_on = last_state.state == "on"
                self._attr_available = True
                self.async_write_ha_state()

        self._handle_coordinator_update()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_available = True
        effective = _effective_state_is_on(
            self._device.get_data(self._mode_path, is_None_possible=True),
            self._device.get_data(self._state_path, is_None_possible=True),
        )
        if effective is not None:
            self._attr_is_on = effective
        self._set_icon()
        super()._handle_coordinator_update()

    def _set_icon(self) -> None:
        if self._attr_is_on:
            self._attr_icon = self._desc.icon
        elif self._desc.icon_off:
            self._attr_icon = self._desc.icon_off

    async def _send_toggle(self) -> None:
        await self._device.my_api.http_send(
            f"/port/{self._port}/toggle", payload={}, method="post"
        )
        await self._device.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        current = _effective_state_is_on(
            self._device.get_data(self._mode_path, is_None_possible=True),
            self._device.get_data(self._state_path, is_None_possible=True),
        )
        self._attr_is_on = True
        self._set_icon()
        self.async_write_ha_state()

        if current is not True:
            await self._send_toggle()

    async def async_turn_off(self, **kwargs: Any) -> None:
        current = _effective_state_is_on(
            self._device.get_data(self._mode_path, is_None_possible=True),
            self._device.get_data(self._state_path, is_None_possible=True),
        )
        self._attr_is_on = False
        self._set_icon()
        self.async_write_ha_state()

        if current is not False:
            await self._send_toggle()

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        return self._device.device_info


# REEFCONTROL — per-port ATO auto-fill toggle
class ReefControlATOSwitchEntity(ReefBeatRestoreEntity, SwitchEntity):  # type: ignore[reportIncompatibleVariableOverride]
    """Toggle the ``auto_fill`` flag on an ATO 12V port.

    Backing endpoint: ``PUT /port/{n}/ato/configuration`` with a JSON body
    ``{"auto_fill": bool}``. Unlike the socket/port toggle switches, the
    firmware maintains a proper boolean state here, so we can drive
    ``_attr_is_on`` directly from ``ports[?(@.number==N)].auto_fill``.
    """

    _attr_has_entity_name = True

    @staticmethod
    def _restore_is_on(state: str) -> bool:
        return state == "on"

    def __init__(
        self,
        device: ReefControlCoordinator,
        entity_description: ReefControlATOSwitchEntityDescription,
    ) -> None:
        ReefBeatRestoreEntity.__init__(
            self,
            device,
            restore=RestoreSpec("_attr_is_on", self._restore_is_on),
        )
        self._device: ReefControlCoordinator = device
        self._desc: ReefControlATOSwitchEntityDescription = entity_description
        self.entity_description = cast(SwitchEntityDescription, entity_description)
        self._port: int = entity_description.port

        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_is_on = False

        base = f"$.sources[?(@.name=='/dashboard')].data.ports[{self._port}]"
        self._auto_fill_path = f"{base}.auto_fill"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            if self._attr_is_on is None or not self._attr_available:
                self._attr_is_on = last_state.state == "on"
                self._attr_available = True
                self.async_write_ha_state()

        self._handle_coordinator_update()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_available = True
        auto_fill = self._device.get_data(self._auto_fill_path, is_None_possible=True)
        if isinstance(auto_fill, bool):
            self._attr_is_on = auto_fill
        self._set_icon()
        super()._handle_coordinator_update()

    def _set_icon(self) -> None:
        if self._attr_is_on:
            self._attr_icon = self._desc.icon
        elif self._desc.icon_off:
            self._attr_icon = self._desc.icon_off

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Optimistic update for immediate UI feedback.
        self._attr_is_on = True
        self._set_icon()
        self.async_write_ha_state()
        await self._device.my_api.push_ato_configuration(self._port, True)
        await self._device.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._set_icon()
        self.async_write_ha_state()
        await self._device.my_api.push_ato_configuration(self._port, False)
        await self._device.async_request_refresh()

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        return self._device.device_info


# REEFCLOUD
class ReefCloudSwitchEntity(ReefBeatSwitchEntity):
    """Reef cloud shortcuts switch."""

    _attr_has_entity_name = True
    _active_switches: dict[str, str] = {}

    # Recognized shortcut types (lowercased for case-insensitive matching).
    # The ReefBeat cloud has been observed to return `"type": "EMERGENCY"` on
    # some accounts, so we normalize both sides before comparing.
    _SHORTCUT_TYPES: frozenset[str] = frozenset({"feeding", "maintenance", "emergency"})

    @staticmethod
    def _coerce_enabled(value: Any) -> bool:
        """Coerce ReefBeat 'enabled' field to a real bool.

        The cloud API is inconsistent across accounts/firmwares: `enabled`
        may come back as a real bool (``true``/``false``) or as a JSON
        string (``"true"``/``"false"``). A raw truthiness check on the
        string ``"false"`` returns ``True`` (non-empty string), which
        incorrectly flags the shortcut as active and marks every shortcut
        switch as unavailable via the active-switch comparison.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() == "true"
        return bool(value)

    @classmethod
    def _recompute_active_switches(cls, device: ReefBeatCoordinator) -> None:
        cls._active_switches.clear()
        aquariums = device.get_data("$.sources[?(@.name=='/aquarium')].data") or []
        for aquarium in aquariums:
            uid = aquarium["uid"]
            for key, value in aquarium.get("properties", {}).items():
                if not isinstance(value, dict):
                    continue
                # Restrict to actual shortcut entries. Without this filter any
                # unrelated dict property with a truthy `enabled` (or a string
                # `"false"`) would be misdetected as the active shortcut.
                stype = str(value.get("type", "")).lower()
                if stype not in cls._SHORTCUT_TYPES:
                    continue
                if not cls._coerce_enabled(value.get("enabled")):
                    continue
                # Store the shortcut `code` (normalized to lowercase). The
                # availability comparison in `available` uses the same
                # normalization on the entity side, so mixed-case codes like
                # "EMERGENCY_1" vs "emergency_1" still match.
                code = str(value.get("code") or key).lower()
                cls._active_switches[uid] = code
                break

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefCloudSwitchEntityDescription,
    ) -> None:
        self._shortcut: dict = device.get_data(entity_description.shortcut, True)
        self._aquarium: dict = entity_description.aquarium
        self._present: bool = False
        if self._shortcut:
            self._attr_name = self._shortcut["name"]
            self._present = True
        else:
            self._attr_name = entity_description.key
            _LOGGER.info(
                "Shortcut {} not present in aquarium {}".format(
                    entity_description.key, entity_description.aquarium["name"]
                )
            )

        super().__init__(
            device, cast(ReefBeatSwitchEntityDescription, entity_description)
        )

        # Store the normalized `code` (lowercase), matching
        # `_recompute_active_switches`. Previously this branch stored
        # `entity_description.key` (e.g. "shortcut_emergency_1"), which never
        # matched `self._shortcut["code"]` (e.g. "emergency_1") in the
        # availability check.
        if self._present and self._coerce_enabled(self._shortcut.get("enabled")):
            code = str(self._shortcut.get("code", "")).lower()
            ReefCloudSwitchEntity._active_switches[self._aquarium["uid"]] = code
            self._attr_is_on = True
        else:
            self._attr_is_on = False

        self._attr_unique_id = f"{device.serial}_{entity_description.key}"

        self._typed_desc: ReefCloudSwitchEntityDescription = entity_description
        self.entity_description = cast(SwitchEntityDescription, entity_description)

    @callback
    def _handle_coordinator_update(self) -> None:
        ReefCloudSwitchEntity._recompute_active_switches(self._device)

        # Check availability first - this updates self._shortcut and self._present
        self._attr_available = self.available

        # Only compute is_on if the switch is available
        if self._attr_available:
            self._attr_is_on = self._compute_is_on()
        else:
            self._attr_is_on = False

        self._set_icon()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self._set_icon()

        await self._device.my_api.http_send(
            action="/aquarium/"
            + self._aquarium["uid"]
            + "/shortcut/"
            + self._shortcut["code"]
            + "/start",
            method="post",
        )

        self._device.async_update_listeners()
        self.async_write_ha_state()

        if self._typed_desc.notify:
            self._device.hass.bus.fire(
                "shortcut_state", {"code": self._shortcut["code"], "state": "on"}
            )

        cloud = cast(_CloudPush, self._device)
        await cloud.async_request_refresh(source="/aquarium")

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._set_icon()

        await self._device.my_api.http_send(
            action="/aquarium/"
            + self._aquarium["uid"]
            + "/shortcut/"
            + self._shortcut["code"]
            + "/stop",
            method="post",
        )

        self._device.async_update_listeners()
        self.async_write_ha_state()

        if self._typed_desc.notify:
            self._device.hass.bus.fire(
                "shortcut_state", {"code": self._shortcut["code"], "state": "off"}
            )

        cloud = cast(_CloudPush, self._device)
        await cloud.async_request_refresh(source="/aquarium")

    def _compute_is_on(self) -> bool:
        if not self._present:
            return False
        # Safely get the value, return False if shortcut was deleted.
        # Use `_coerce_enabled` because the cloud may return `enabled` as a
        # string ("true"/"false"); `bool("false")` is True, which would pin
        # the switch to ON.
        try:
            return self._coerce_enabled(self._device.get_data(self._desc.value_name))
        except (KeyError, ValueError):
            # Shortcut was deleted or data is invalid
            return False

    @property
    def available(self) -> bool:  # type: ignore[override]
        # get value form coordinator
        self._shortcut = self._device.get_data(self._typed_desc.shortcut, True)

        if not self._shortcut:
            # No shortcut, disable switch
            self._attr_name = self.entity_description.key
            self._present = False
            return False

        # The shorcut is configured
        self._attr_name = self._shortcut["name"]
        self._present = True

        # Get the active shortcut switch if exists
        active_switch = ReefCloudSwitchEntity._active_switches.get(
            self._aquarium["uid"]
        )
        # Return true if all shortcut switches are off, or if only this switch
        # is on. Both sides are lowercased so that servers returning mixed-case
        # codes (e.g. "EMERGENCY_1") don't cause spurious unavailability.
        my_code = str(self._shortcut.get("code", "")).lower()
        return not active_switch or active_switch == my_code

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return device info extended with the pump identifier."""
        return cast(ReefBeatCloudCoordinator, self._device).aquarium_device_info(
            self._aquarium["name"]
        )

    @cached_property
    def icon(self):
        if self._shortcut:
            # Normalize `type` to lowercase: the cloud has been observed to
            # return "EMERGENCY" on some accounts, which would resolve to a
            # non-existent "redsea:EMERGENCY" icon.
            mdi_icon = "redsea:" + str(self._shortcut["type"]).lower()
            if "icon" in self._shortcut:
                mdi_icon = "redsea:" + self._shortcut["icon"]
                return mdi_icon
        return self.entity_description.icon


# Maintenance notification switches share the ReefRoleMixin so their
# translation_key is also exposed as `reef_role` (consumed by the custom card).
class MaintenanceNotifySwitchEntity(ReefRoleMixin, SwitchEntity):  # type: ignore[misc]
    """Switch enabling/disabling overdue alerts for one maintenance task.

    The value lives in the persistent MaintenanceStore next to `last_reset`
    and `interval_days`, and is mirrored as the `notify` attribute of the
    matching MaintenanceButtonEntity. The alert blueprint reads that single
    attribute, so it never has to correlate two entities.

    `reef_role` is "<task.translation_key>_notify", which lets cards and
    templates tell it apart both from the action button ("maint_<task>") and
    from the interval number ("maint_<task>_interval_<unit>").
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        device: ReefBeatCoordinator,
        task: MaintenanceTask,
        sub_id: int = 0,
        placeholders: dict[str, str] | None = None,
    ) -> None:
        self._device = device
        self._task = task
        self._sub_id = sub_id
        if placeholders:
            self._attr_translation_placeholders = dict(placeholders)

        suffix = f"_{sub_id}" if sub_id > 0 else ""
        self._attr_unique_id = f"{device.serial}_{task.key}_notify{suffix}"
        self._attr_translation_key = f"{task.translation_key}_notify"

        # Bind to the right (sub-)device for UI grouping.
        if (
            sub_id > 0
            and hasattr(device, "head_device_info")
            and task.applies_to_sub == "head"
        ):
            self._attr_device_info = cast(Any, device).head_device_info(sub_id)
        elif sub_id > 0 and hasattr(device, "pump_device_info"):
            self._attr_device_info = cast(Any, device).pump_device_info(sub_id)
        else:
            self._attr_device_info = device.device_info

        self._attr_available = True
        self._unsub: Callable[[], None] | None = None

        # State is mirrored into `_attr_is_on` / `_attr_icon` rather than
        # exposed through overridden properties: the base SwitchEntity
        # declares both as `cached_property`, so a plain `property` override
        # fails pyright and would cache a value that must change.
        # These defaults match MaintenanceState.notify until the store is
        # read in `async_added_to_hass`.
        self._attr_is_on = True
        self._attr_icon = "mdi:bell-ring"

    # ---- store access -----------------------------------------------------

    @property
    def _store(self) -> MaintenanceStore:
        """Return the device's MaintenanceStore, lazy-creating a fallback.

        See `MaintenanceButtonEntity._store` for the rationale.
        """
        device = cast(Any, self._device)
        store = getattr(device, "maintenance", None)
        if store is None:
            _LOGGER.warning(
                "MaintenanceStore missing on %s; using ephemeral fallback "
                "(notification settings will not persist across restarts)",
                getattr(device, "_title", device.__class__.__name__),
            )
            store = MaintenanceStore(
                device._hass,
                f"fallback_{id(device)}",
            )
            device.maintenance = store
        return store

    # ---- state ------------------------------------------------------------

    def _refresh_state(self) -> None:
        """Pull the current value from the store into the entity attributes."""
        enabled = self._store.get_notify(
            self._device.serial, self._sub_id, self._task.key
        )
        self._attr_is_on = enabled
        self._attr_icon = "mdi:bell-ring" if enabled else "mdi:bell-off"

    # ---- lifecycle --------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # Read the persisted value before Home Assistant writes the first
        # state, otherwise a muted task would briefly show up as enabled.
        self._refresh_state()

        @callback
        def _on_store_change() -> None:
            self._refresh_state()
            self.async_write_ha_state()

        self._unsub = self._store.async_add_listener(
            self._device.serial, self._sub_id, self._task.key, _on_store_change
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()

    # ---- actions ----------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._store.async_set_notify(
            self._device.serial, self._sub_id, self._task.key, True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._store.async_set_notify(
            self._device.serial, self._sub_id, self._task.key, False
        )
