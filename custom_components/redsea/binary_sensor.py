"""Binary sensor platform for the Red Sea ReefBeat integration.

Defines binary sensors for ReefBeat devices and cloud-linked devices.

Sensors are created from `BinarySensorEntityDescription` dataclasses and read
their values from coordinator data via jsonpath lookups and/or callables.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Generic, TypeVar, cast

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
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

_LOGGER = logging.getLogger(__name__)

TCoord = TypeVar("TCoord", bound=ReefBeatCoordinator)


# Entity descriptions
@dataclass(kw_only=True, frozen=True)

# =============================================================================
# Classes
# =============================================================================

class ReefBeatBinarySensorEntityDescription(
    BinarySensorEntityDescription, Generic[TCoord]
):
    """Description for binary sensors backed by a ReefBeatCoordinator."""

    exists_fn: Callable[[TCoord], bool] = lambda _: True
    value_fn: Callable[[TCoord], StateType] | None = None
    value_name: str | None = None


@dataclass(kw_only=True, frozen=True)
class ReefDoseBinarySensorEntityDescription(
    ReefBeatBinarySensorEntityDescription[ReefDoseCoordinator]
):
    """Description for ReefDose head-scoped binary sensors."""

    head: int = 0


@dataclass(kw_only=True, frozen=True)
class ReefRunBinarySensorEntityDescription(
    ReefBeatBinarySensorEntityDescription[ReefRunCoordinator]
):
    """Description for ReefRun pump-scoped binary sensors."""

    pump: int = 0


# Sensor descriptions
COMMON_SENSORS: tuple[
    ReefBeatBinarySensorEntityDescription[ReefBeatCoordinator], ...
] = (
    ReefBeatBinarySensorEntityDescription(
        key="cloud_state",
        translation_key="cloud_state",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/cloud')].data.connected"
        ),
        icon="mdi:cloud-check-variant-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

BATTERY_SENSORS: tuple[
    ReefBeatBinarySensorEntityDescription[ReefBeatCoordinator], ...
] = (
    ReefBeatBinarySensorEntityDescription(
        key="battery_level",
        translation_key="battery_level",
        device_class=BinarySensorDeviceClass.BATTERY,
        exists_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.battery_level", True
        )
        is not None,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.battery_level"
        )
        == "low",
        icon="mdi:battery-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

LED_SENSORS: tuple[ReefBeatBinarySensorEntityDescription[ReefBeatCoordinator], ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="status",
        translation_key="status",
        device_class=BinarySensorDeviceClass.LIGHT,
        value_fn=lambda device: device.get_data("$.local.status"),
        icon="mdi:wall-sconce-flat",
    ),
)

MAT_SENSORS: tuple[ReefBeatBinarySensorEntityDescription[ReefBeatCoordinator], ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="unclean_sensor",
        translation_key="unclean_sensor",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.unclean_sensor"
        ),
        icon="mdi:liquid-spot",
    ),
    ReefBeatBinarySensorEntityDescription(
        key="is_ec_sensor_connected",
        translation_key="is_ec_sensor_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.is_ec_sensor_connected"
        ),
        icon="mdi:connection",
    ),
)

ATO_SENSORS: tuple[ReefBeatBinarySensorEntityDescription[ReefBeatCoordinator], ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="water_level",
        translation_key="water_level",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: not device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.water_level"
        ).startswith("desired"),
        icon="mdi:water-alert",
    ),
    ReefBeatBinarySensorEntityDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.leak_sensor.connected"
        ),
        icon="mdi:connection",
    ),
    ReefBeatBinarySensorEntityDescription(
        key="enabled",
        translation_key="enabled",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.leak_sensor.enabled"
        ),
        icon="mdi:leak",
    ),
    ReefBeatBinarySensorEntityDescription(
        key="buzzer_enabled",
        translation_key="buzzer_enabled",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.leak_sensor.buzzer_enabled"
        ),
        icon="mdi:volume-high",
    ),
    ReefBeatBinarySensorEntityDescription(
        key="status",
        translation_key="status",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.leak_sensor.status"
        )
        != "dry",
        icon="mdi:water-off",
    ),
    ReefBeatBinarySensorEntityDescription(
        key="is_sensor_error",
        translation_key="is_sensor_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.ato_sensor.is_sensor_error"
        ),
        icon="mdi:alert-circle-outline",
    ),
    ReefBeatBinarySensorEntityDescription(
        key="is_temp_enabled",
        translation_key="is_temp_enabled",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.ato_sensor.is_temp_enabled"
        ),
        icon="mdi:thermometer-check",
    ),
    ReefBeatBinarySensorEntityDescription(
        key="is_pump_on",
        translation_key="is_pump_on",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.is_pump_on"
        ),
        icon="mdi:pump",
    ),
)

RUN_SENSORS: tuple[ReefBeatBinarySensorEntityDescription[ReefRunCoordinator], ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="ec_sensor_connected",
        translation_key="ec_sensor_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.ec_sensor_connected"
        ),
        icon="mdi:connection",
    ),
)


# Platform setup
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities for a config entry."""
    device = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    # Device-specific sensors
    if isinstance(
        device, (ReefLedCoordinator, ReefVirtualLedCoordinator, ReefLedG2Coordinator)
    ):
        entities.extend(
            ReefBeatBinarySensorEntity(device, description)
            for description in LED_SENSORS
            if description.exists_fn(device)
        )
    elif isinstance(device, ReefMatCoordinator):
        entities.extend(
            ReefBeatBinarySensorEntity(device, description)
            for description in MAT_SENSORS
            if description.exists_fn(device)
        )
    elif isinstance(device, ReefATOCoordinator):
        entities.extend(
            ReefBeatBinarySensorEntity(device, description)
            for description in ATO_SENSORS
            if description.exists_fn(device)
        )
    elif isinstance(device, ReefDoseCoordinator):
        dose_descs: list[ReefDoseBinarySensorEntityDescription] = []
        for head in range(1, device.heads_nb + 1):
            dose_descs.append(
                ReefDoseBinarySensorEntityDescription(
                    key="recalibration_required_head_" + str(head),
                    translation_key="recalibration_required",
                    icon="mdi:water-percent-alert",
                    device_class=BinarySensorDeviceClass.PROBLEM,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                    + str(head)
                    + ".recalibration_required",
                    head=head,
                )
            )
        entities.extend(ReefDoseBinarySensorEntity(device, desc) for desc in dose_descs)

    elif isinstance(device, ReefRunCoordinator):
        run_descs: list[ReefRunBinarySensorEntityDescription] = []
        for pump in range(1, 3):
            # IMPORTANT: bind pump into lambda default to avoid late-binding bug
            run_descs.append(
                ReefRunBinarySensorEntityDescription(
                    key="constant_speed_pump_" + str(pump),
                    translation_key="constant_speed",
                    icon="mdi:car-cruise-control",
                    value_fn=lambda device, pump=pump: len(
                        device.get_data(
                            "$.sources[?(@.name=='/pump/settings')].data.pump_"
                            + str(pump)
                            + ".schedule"
                        )
                    )
                    == 1,
                    pump=pump,
                    entity_category=EntityCategory.DIAGNOSTIC,
                )
            )
            run_descs.append(
                ReefRunBinarySensorEntityDescription(
                    key="sensor_controlled_pump_" + str(pump),
                    translation_key="sensor_controlled",
                    icon="mdi:car-speed-limiter",
                    value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                    + str(pump)
                    + ".sensor_controlled",
                    pump=pump,
                )
            )
            run_descs.append(
                ReefRunBinarySensorEntityDescription(
                    key="schedule_enabled_pump_" + str(pump),
                    translation_key="schedule_enabled",
                    icon="mdi:calendar-arrow-right",
                    value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                    + str(pump)
                    + ".schedule_enabled",
                    pump=pump,
                )
            )
            run_descs.append(
                ReefRunBinarySensorEntityDescription(
                    key="missing_sensor_pump_" + str(pump),
                    translation_key="missing_sensor",
                    device_class=BinarySensorDeviceClass.PROBLEM,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    icon="mdi:leak-off",
                    value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                    + str(pump)
                    + ".missing_sensor",
                    pump=pump,
                )
            )
            run_descs.append(
                ReefRunBinarySensorEntityDescription(
                    key="missing_pump_pump_" + str(pump),
                    translation_key="missing_pump",
                    device_class=BinarySensorDeviceClass.PROBLEM,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    icon="mdi:alert-outline",
                    value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                    + str(pump)
                    + ".missing_pump",
                    pump=pump,
                )
            )

        entities.extend(ReefRunBinarySensorEntity(device, desc) for desc in run_descs)
        entities.extend(
            ReefBeatBinarySensorEntity(device, description)
            for description in RUN_SENSORS
            if description.exists_fn(device)
        )

    # Common sensors (device dependent)
    if isinstance(
        device, (ReefRunCoordinator, ReefLedCoordinator, ReefDoseCoordinator)
    ):
        entities.extend(
            ReefBeatBinarySensorEntity(device, description)
            for description in BATTERY_SENSORS
            if description.exists_fn(device)
        )

    if not isinstance(device, ReefBeatCloudCoordinator):
        entities.extend(
            ReefBeatBinarySensorEntity(device, description)
            for description in COMMON_SENSORS
            if description.exists_fn(device)
        )

    async_add_entities(entities, True)


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


TDevice = TypeVar("TDevice", bound=ReefBeatCoordinator)


# REEFBEAT
class ReefBeatBinarySensorEntity(  # pyright: ignore[reportIncompatibleVariableOverride]
    RestoreEntity, CoordinatorEntity[TDevice], BinarySensorEntity, Generic[TDevice]
):
    """Binary sensor backed by a ReefBeat coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: TDevice,
        entity_description: ReefBeatBinarySensorEntityDescription[TDevice],
    ) -> None:
        """Initialize the entity."""
        super().__init__(device)
        self._device = device
        self.entity_description = entity_description
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_device_info = device.device_info
        self._attr_is_on = self._coerce_bool(self._get_value())

    async def async_added_to_hass(self) -> None:
        """Restore the last state on Home Assistant restart."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._attr_is_on = last_state.state == "on"

    @property
    def desc(self) -> ReefBeatBinarySensorEntityDescription[TDevice]:
        return cast(
            ReefBeatBinarySensorEntityDescription[TDevice], self.entity_description
        )

    @staticmethod
    def _coerce_bool(state: StateType) -> bool | None:
        if state is None:
            return None
        return state if isinstance(state, bool) else bool(state)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self._coerce_bool(self._get_value())
        self.async_write_ha_state()

    def _get_value(self) -> StateType:
        """Resolve current value via value_fn or value_name."""
        desc = self.desc
        if desc.value_fn is not None:
            return desc.value_fn(self._device)
        if desc.value_name is not None:
            return self._device.get_data(desc.value_name)
        _LOGGER.error("%s: no value_fn or value_name for %s", __name__, desc.key)
        return None


# REEFDOSE
class ReefDoseBinarySensorEntity(ReefBeatBinarySensorEntity[ReefDoseCoordinator]):
    """Binary sensor for ReefDose heads."""

    def __init__(
        self,
        device: ReefDoseCoordinator,
        entity_description: ReefDoseBinarySensorEntityDescription,
    ) -> None:
        super().__init__(device, entity_description)
        self._head = entity_description.head

    def _get_value(self) -> StateType:
        """Dose sensors always use value_name."""
        value_name = self.desc.value_name
        if value_name is None:
            _LOGGER.error("%s: missing value_name for %s", __name__, self.desc.key)
            return None
        return self._device.get_data(value_name)

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return per-head device info for ReefDose."""
        if self._head <= 0:
            return self._device.device_info

        base_di = dict(self._device.device_info)
        base_identifiers = base_di.get("identifiers") or {(DOMAIN, self._device.serial)}
        domain, ident = next(iter(cast(set[tuple[str, str]], base_identifiers)))

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
class ReefRunBinarySensorEntity(ReefBeatBinarySensorEntity[ReefRunCoordinator]):
    """Binary sensor for ReefRun pumps."""

    def __init__(
        self,
        device: ReefRunCoordinator,
        entity_description: ReefRunBinarySensorEntityDescription,
    ) -> None:
        super().__init__(device, entity_description)
        self._pump = entity_description.pump
