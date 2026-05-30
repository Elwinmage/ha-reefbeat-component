"""Number platform for Red Sea ReefBeat devices.

This module exposes device settings as `number` entities (configuration sliders/boxes)
for supported ReefBeat devices (LED, Mat, Dose, Run, Wave, ATO).

Most entities read/write values via their device coordinator. Some entities are
conditionally available depending on other device state (dependency fields).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Protocol, cast, runtime_checkable

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATO_VOLUME_LEFT_INTERNAL_NAME,
    DOMAIN,
    LED_ACCLIMATION_DURATION_INTERNAL_NAME,
    LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
    LED_ACCLIMATION_INTENSITY_INTERNAL_NAME,
    LED_MANUAL_DURATION_INTERNAL_NAME,
    LED_MOON_DAY_INTERNAL_NAME,
    LED_MOONPHASE_ENABLED_INTERNAL_NAME,
    MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
    MAT_MIN_ROLL_DIAMETER,
    MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME,
    WAVE_SHORTCUT_OFF_DELAY,
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
    ReefWaveCoordinator,
)
from .entity import ReefRoleMixin
from .maintenance import (
    MaintenanceStore,
    MaintenanceTask,
    tasks_for,
)

_LOGGER = logging.getLogger(__name__)


# Coordinator capability protocols (typing only)
@runtime_checkable

# =============================================================================
# Classes
# =============================================================================

class _HasDeviceInfo(Protocol):
    device_info: Any

    @property
    def title(self) -> str: ...

    @property
    def serial(self) -> str: ...

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]: ...
    def get_data(self, name: str, is_None_possible: bool = False) -> Any: ...
    def set_data(self, name: str, value: Any) -> None: ...
    async def push_values(
        self,
        source: str = "/configuration",
        method: str = "put",
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
    async def async_request_refresh(self, *, wait: int = 2) -> None: ...


@runtime_checkable
class _HasPostSpecific(Protocol):
    async def post_specific(self, source: str) -> None: ...


@runtime_checkable
class _HasPumpIntensity(Protocol):
    async def set_pump_intensity(self, pump: int, intensity: int) -> None: ...
    async def push_values(
        self,
        source: str = "/configuration",
        method: str = "put",
        pump: int | None = None,
    ) -> None: ...


@runtime_checkable
class _HasATOVolumeLeft(Protocol):
    async def set_volume_left(self, volume_ml: int) -> None: ...


# Entity descriptions
@dataclass(kw_only=True, frozen=True)
class ReefBeatNumberEntityDescription(NumberEntityDescription):
    """Common description for ReefBeat number entities."""

    exists_fn: Callable[[Any], bool] = lambda _: True
    value_name: str = ""
    dependency: str | None = None
    dependency_values: Sequence[Any] | None = None
    source: str = "/configuration"


@dataclass(kw_only=True, frozen=True)
class ReefRunNumberEntityDescription(ReefBeatNumberEntityDescription):
    """Description for ReefRun number entities."""

    pump: int = 0


@dataclass(kw_only=True, frozen=True)
class ReefLedNumberEntityDescription(ReefBeatNumberEntityDescription):
    """Description for ReefLED number entities."""

    post_specific: str | None = None


@dataclass(kw_only=True, frozen=True)
class ReefDoseNumberEntityDescription(ReefBeatNumberEntityDescription):
    """Description for ReefDose number entities."""

    head: int = 0


DescriptionT = (
    ReefBeatNumberEntityDescription
    | ReefRunNumberEntityDescription
    | ReefLedNumberEntityDescription
    | ReefDoseNumberEntityDescription
)

WAVE_NUMBERS: tuple[ReefBeatNumberEntityDescription, ...] = (
    ReefBeatNumberEntityDescription(
        key="shortcut_off_delay",
        translation_key="shortcut_off_delay",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=600,
        native_min_value=0,
        native_step=1,
        value_name=WAVE_SHORTCUT_OFF_DELAY,
        icon="mdi:arrow-expand-right",
        entity_category=EntityCategory.CONFIG,
    ),
)

WAVE_PREVIEW_NUMBERS: tuple[ReefBeatNumberEntityDescription, ...] = (
    ReefBeatNumberEntityDescription(
        key="wave_forward_time",
        translation_key="wave_forward_time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=60,
        native_min_value=2,
        native_step=1,
        value_name="$.sources[?(@.name=='/preview')].data.frt",
        icon="mdi:waves-arrow-right",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        dependency_values=["st", "ra", "re", "un"],
    ),
    ReefBeatNumberEntityDescription(
        key="wave_backward_time",
        translation_key="wave_backward_time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=60,
        native_min_value=2,
        native_step=1,
        value_name="$.sources[?(@.name=='/preview')].data.rrt",
        icon="mdi:waves-arrow-left",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        dependency_values=["st", "ra", "re", "un"],
    ),
    ReefBeatNumberEntityDescription(
        key="wave_forward_intensity",
        translation_key="wave_forward_intensity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.POWER_FACTOR,
        native_max_value=100,
        native_min_value=10,
        native_step=10,
        value_name="$.sources[?(@.name=='/preview')].data.fti",
        icon="mdi:waves-arrow-right",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        dependency_values=["st", "ra", "re", "su", "un"],
    ),
    ReefBeatNumberEntityDescription(
        key="wave_backward_intensity",
        translation_key="wave_backward_intensity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.POWER_FACTOR,
        native_max_value=100,
        native_min_value=10,
        native_step=10,
        value_name="$.sources[?(@.name=='/preview')].data.rti",
        icon="mdi:waves-arrow-left",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        dependency_values=["st", "ra", "re", "su", "un"],
    ),
    ReefBeatNumberEntityDescription(
        key="wave_preview_duration",
        translation_key="wave_preview_duration",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=600000,
        native_min_value=60000,
        native_step=60000,
        value_name="$.sources[?(@.name=='/preview')].data.duration",
        icon="mdi:timer-sand",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatNumberEntityDescription(
        key="wave_preview_step",
        translation_key="wave_preview_step",
        device_class=NumberDeviceClass.DURATION,
        native_max_value=10,
        native_min_value=3,
        native_step=1,
        value_name="$.sources[?(@.name=='/preview')].data.sn",
        icon="mdi:stairs",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        dependency_values=["st"],
    ),
    ReefBeatNumberEntityDescription(
        key="wave_preview_wave_duration",
        translation_key="wave_preview_wave_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        native_max_value=25,
        native_min_value=2,
        native_step=1,
        value_name="$.sources[?(@.name=='/preview')].data.pd",
        icon="mdi:clock-time-five",
        entity_category=EntityCategory.CONFIG,
        dependency="$.sources[?(@.name=='/preview')].data.type",
        dependency_values=["st", "un", "su"],
    ),
)


MAT_NUMBERS: tuple[ReefBeatNumberEntityDescription, ...] = (
    ReefBeatNumberEntityDescription(
        key="custom_advance_value",
        translation_key="custom_advance_value",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=NumberDeviceClass.DISTANCE,
        native_max_value=48,
        native_min_value=0.75,
        native_step=0.5,
        value_name=MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
        icon="mdi:arrow-expand-right",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatNumberEntityDescription(
        key="started_roll_diameter",
        translation_key="started_roll_diameter",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=NumberDeviceClass.DISTANCE,
        native_max_value=11.1,
        native_min_value=MAT_MIN_ROLL_DIAMETER,
        native_step=0.1,
        value_name=MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME,
        icon="mdi:arrow-expand-right",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatNumberEntityDescription(
        key="schedule_length",
        translation_key="schedule_length",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=NumberDeviceClass.DISTANCE,
        native_min_value=5,
        native_max_value=45,
        native_step=2.5,
        value_name="$.sources[?(@.name=='/configuration')].data.schedule_length",
        icon="mdi:arrow-expand-right",
        entity_category=EntityCategory.CONFIG,
    ),
)

LED_NUMBERS: tuple[ReefLedNumberEntityDescription, ...] = (
    ReefLedNumberEntityDescription(
        key="moon_day",
        translation_key="moon_day",
        native_max_value=28,
        native_min_value=1,
        native_step=1,
        value_name=LED_MOON_DAY_INTERNAL_NAME,
        post_specific="/moonphase",
        icon="mdi:moon-waning-crescent",
        entity_category=EntityCategory.CONFIG,
        dependency=LED_MOONPHASE_ENABLED_INTERNAL_NAME,
    ),
    ReefLedNumberEntityDescription(
        key="acclimation_duration",
        translation_key="acclimation_duration",
        native_max_value=99,
        native_min_value=2,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_name=LED_ACCLIMATION_DURATION_INTERNAL_NAME,
        icon="mdi:calendar-expand-horizontal",
        post_specific="/acclimation",
        dependency=LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
        entity_category=EntityCategory.CONFIG,
    ),
    ReefLedNumberEntityDescription(
        key="acclimation_start_intensity_factor",
        translation_key="acclimation_start_intensity_factor",
        native_max_value=100,
        native_min_value=1,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        value_name=LED_ACCLIMATION_INTENSITY_INTERNAL_NAME,
        post_specific="/acclimation",
        icon="mdi:sun-wireless-outline",
        dependency=LED_ACCLIMATION_ENABLED_INTERNAL_NAME,
        entity_category=EntityCategory.CONFIG,
    ),
    ReefLedNumberEntityDescription(
        key="manual_duration",
        translation_key="manual_duration",
        native_max_value=120,
        native_min_value=0,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_name=LED_MANUAL_DURATION_INTERNAL_NAME,
        post_specific="/timer",
        icon="mdi:clock-start",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities from a config entry."""
    device = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[NumberEntity] = []

    if isinstance(
        device, (ReefLedCoordinator, ReefVirtualLedCoordinator, ReefLedG2Coordinator)
    ):
        entities.extend(
            ReefLedNumberEntity(device, description)
            for description in LED_NUMBERS
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefMatCoordinator):
        entities.extend(
            ReefBeatNumberEntity(device, description)
            for description in MAT_NUMBERS
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefDoseCoordinator):
        descriptions: list[ReefDoseNumberEntityDescription] = []

        descriptions.append(
            ReefDoseNumberEntityDescription(
                key="stock_alert_days",
                translation_key="stock_alert_days",
                native_unit_of_measurement=UnitOfTime.DAYS,
                native_min_value=1,
                native_step=1,
                native_max_value=45,
                value_name="$.sources[?(@.name=='/device-settings')].data.stock_alert_days",
                icon="mdi:hydraulic-oil-level",
                head=0,
                entity_category=EntityCategory.CONFIG,
            )
        )
        descriptions.append(
            ReefDoseNumberEntityDescription(
                key="dosing_waiting_period",
                translation_key="dosing_waiting_period",
                native_unit_of_measurement=UnitOfTime.SECONDS,
                native_min_value=15,
                native_step=1,
                native_max_value=600,
                value_name="$.sources[?(@.name=='/device-settings')].data.dosing_waiting_period",
                icon="mdi:sleep",
                head=0,
                entity_category=EntityCategory.CONFIG,
            )
        )

        for head in range(1, device.heads_nb + 1):
            descriptions.append(
                ReefDoseNumberEntityDescription(
                    key=f"save_initial_container_volume_head_{head}",
                    translation_key="save_initial_container_volume",
                    native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                    device_class=NumberDeviceClass.VOLUME_STORAGE,
                    native_min_value=25,
                    native_step=1,
                    native_max_value=20000,
                    value_name=f"$.local.head.{head}.initial_volume",
                    icon="mdi:content-save-cog",
                    dependency=f"$.sources[?(@.name=='/head/{head}/settings')].data.slm",
                    head=head,
                    entity_category=EntityCategory.CONFIG,
                ),
            )
            descriptions.append(
                ReefDoseNumberEntityDescription(
                    key=f"manual_head_{head}_volume",
                    translation_key="manual_head_volume",
                    mode=NumberMode.BOX,
                    native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                    device_class=NumberDeviceClass.VOLUME,
                    native_min_value=0,
                    native_step=0.1,
                    native_max_value=300,
                    value_name=f"$.local.head.{head}.manual_dose",
                    icon="mdi:cup-water",
                    head=head,
                    entity_category=EntityCategory.CONFIG,
                )
            )
            descriptions.append(
                ReefDoseNumberEntityDescription(
                    key=f"calibration_dose_value_head_{head}",
                    translation_key="calibration_dose_value",
                    native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                    native_min_value=3.5,
                    native_step=0.05,
                    native_max_value=5.5,
                    value_name=f"$.local.head.{head}.calibration_dose",
                    icon="mdi:test-tube-empty",
                    head=head,
                    entity_category=EntityCategory.CONFIG,
                    entity_registry_visible_default=False,
                )
            )
            descriptions.append(
                ReefDoseNumberEntityDescription(
                    key=f"daily_dose_head_{head}_volume",
                    translation_key="daily_dose",
                    mode=NumberMode.BOX,
                    native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                    device_class=NumberDeviceClass.VOLUME,
                    native_min_value=0,
                    native_step=0.1,
                    native_max_value=300,
                    value_name=(
                        "$.sources[?(@.name=='/head/"
                        + str(head)
                        + "/settings')].data.schedule.dd"
                    ),
                    icon="mdi:cup-water",
                    head=head,
                    entity_category=EntityCategory.CONFIG,
                )
            )
            descriptions.append(
                ReefDoseNumberEntityDescription(
                    key=f"container_volume_head_{head}_volume",
                    translation_key="container_volume",
                    mode=NumberMode.BOX,
                    native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                    device_class=NumberDeviceClass.VOLUME,
                    native_min_value=0,
                    native_step=1,
                    native_max_value=20000,
                    value_name=(
                        "$.sources[?(@.name=='/head/"
                        + str(head)
                        + "/settings')].data.container_volume"
                    ),
                    icon="mdi:cup-water",
                    head=head,
                    entity_category=EntityCategory.CONFIG,
                    dependency=(
                        "$.sources[?(@.name=='/head/"
                        + str(head)
                        + "/settings')].data.slm"
                    ),
                )
            )

        entities.extend(
            ReefDoseNumberEntity(device, description)
            for description in descriptions
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefRunCoordinator):
        # global overskimming threshold (single entity)
        entities.append(
            ReefBeatNumberEntity(
                device,
                ReefBeatNumberEntityDescription(
                    key="overskimming_threshold",
                    translation_key="overskimming_threshold",
                    native_unit_of_measurement=PERCENTAGE,
                    native_min_value=0,
                    native_step=1,
                    native_max_value=100,
                    value_name="$.sources[?(@.name=='/pump/settings')].data.overskimming.threshold",
                    icon="mdi:cloud-percent-outline",
                ),
            )
        )

        run_descs: list[ReefRunNumberEntityDescription] = []
        for pump in (1, 2):
            run_descs.append(
                ReefRunNumberEntityDescription(
                    key=f"pump_{pump}_intensity",
                    translation_key="speed",
                    native_unit_of_measurement=PERCENTAGE,
                    native_min_value=40,
                    native_step=1,
                    native_max_value=100,
                    value_name=f"$.sources[?(@.name=='/dashboard')].data.pump_{pump}.intensity",
                    icon="mdi:waves",
                    pump=pump,
                )
            )
            run_descs.append(
                ReefRunNumberEntityDescription(
                    key=f"preview_pump_{pump}_intensity",
                    translation_key="preview_speed",
                    native_unit_of_measurement=PERCENTAGE,
                    native_min_value=40,
                    native_step=1,
                    native_max_value=100,
                    value_name=f"$.sources[?(@.name=='/preview')].data.pump_{pump}.ti",
                    icon="mdi:waves",
                    pump=pump,
                    entity_category=EntityCategory.CONFIG,
                )
            )

        entities.extend(
            ReefRunNumberEntity(device, description)
            for description in run_descs
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefWaveCoordinator):
        entities.extend(
            ReefBeatNumberEntity(device, description)
            for description in WAVE_NUMBERS
            if description.exists_fn(device)
        )
        entities.extend(
            ReefWaveNumberEntity(device, description)
            for description in WAVE_PREVIEW_NUMBERS
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefATOCoordinator):
        # single entity
        entities.append(
            ReefATOVolumeLeftNumberEntity(
                device,
                ReefBeatNumberEntityDescription(
                    key="ato_volume_left",
                    translation_key="ato_volume_left",
                    mode=NumberMode.BOX,
                    native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                    device_class=NumberDeviceClass.VOLUME,
                    native_min_value=0,
                    native_step=1,
                    native_max_value=200000,
                    value_name=ATO_VOLUME_LEFT_INTERNAL_NAME,
                    icon="mdi:cup-water",
                    entity_category=EntityCategory.CONFIG,
                ),
            )
        )

    # ---- Maintenance interval numbers ---------------------------------------
    # One number entity per task instance, paired with the matching button.
    # Mirrors the button's sub-device fan-out (heads / pumps).
    _add_maintenance_numbers(device, entities)

    async_add_entities(entities, update_before_add=True)


def _add_maintenance_numbers(
    device: ReefBeatCoordinator,
    entities: list[NumberEntity],
) -> None:
    """Create one MaintenanceIntervalNumberEntity per applicable task instance."""
    if isinstance(device, (ReefBeatCloudCoordinator, ReefVirtualLedCoordinator)):
        return

    # The coordinator stores its hw model id in `_hw` (set from
    # CONFIG_FLOW_HW_MODEL in coordinator.py). Match button.py.
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
                    MaintenanceIntervalNumberEntity(device, task, sub_id=head)
                )
        elif task.applies_to_sub in ("pump_return", "pump_skimmer") and isinstance(
            device, ReefRunCoordinator
        ):
            wanted = "return" if task.applies_to_sub == "pump_return" else "skimmer"
            # RSRUN is hardware-fixed to 2 pumps; the "common parts" device
            # exposed by the integration has no pump_N data, so we keep
            # `is_None_possible=True` to suppress its ERROR log silently.
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
                        MaintenanceIntervalNumberEntity(device, task, sub_id=pump_id)
                    )
        else:
            entities.append(MaintenanceIntervalNumberEntity(device, task, sub_id=0))


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


# REEFBEAT
class ReefBeatNumberEntity(CoordinatorEntity[ReefBeatCoordinator], RestoreNumber):  # type: ignore[reportIncompatibleVariableOverride]
    """Base number entity backed by a ReefBeat coordinator.

    Uses CoordinatorEntity for automatic updates and RestoreNumber for state persistence.
    """

    _attr_has_entity_name = True

    def __init__(self, device: _HasDeviceInfo, description: DescriptionT) -> None:
        """Initialize the entity."""
        super().__init__(
            #            self,
            cast(ReefBeatCoordinator, device),
        )
        self._device: _HasDeviceInfo = device
        self._description: DescriptionT = description

        if description.translation_key is not None:
            self._attr_translation_key = description.translation_key
        if description.icon is not None:
            self._attr_icon = description.icon
        if description.entity_category is not None:
            self._attr_entity_category = description.entity_category
        if description.device_class is not None:
            self._attr_device_class = description.device_class
        if description.native_unit_of_measurement is not None:
            self._attr_native_unit_of_measurement = (
                description.native_unit_of_measurement
            )

        # HA stubs type these as Optional[...] on the description, but the entity
        # attributes are non-optional. Coalesce to safe defaults for strict typing.
        #
        # Defaults chosen to be neutral and should never matter for our entities
        # because we always set these fields in our descriptions. If a future
        # description omits them, the entity still behaves sensibly.
        self._attr_mode = description.mode or NumberMode.AUTO
        self._attr_native_min_value = (
            float(description.native_min_value)
            if description.native_min_value is not None
            else 0.0
        )
        self._attr_native_max_value = (
            float(description.native_max_value)
            if description.native_max_value is not None
            else 100.0
        )
        self._attr_native_step = (
            float(description.native_step)
            if description.native_step is not None
            else 1.0
        )

        self._attr_unique_id = f"{device.serial}_{description.key}"
        self._attr_device_info = device.device_info
        self._attr_native_value: float | None = None

        # Derive the push source from the JSONPath, default to configuration.
        self._source = "/configuration"
        try:
            self._source = str(description.value_name).split("'")[1]
        except Exception:
            pass

    async def async_added_to_hass(self) -> None:
        """Restore last known value and prime from coordinator cache."""

        res = await self.async_get_last_extra_data()
        if res is not None:
            self._attr_native_value = res.as_dict()["native_value"]
            self._device.set_data(self._description.value_name, self._attr_native_value)
        else:
            self._attr_native_value = None
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Sync cached `_attr_*` state from coordinator data."""
        self._attr_available = self._compute_available()
        self._attr_native_value = cast(
            float | None, self._device.get_data(self._description.value_name, True)
        )
        super()._handle_coordinator_update()

    def _compute_available(self) -> bool:
        """Return True when this number should be shown as available."""
        dep = self._description.dependency
        if dep is None:
            return True

        dep_value = self._device.get_data(dep, True)
        if self._description.dependency_values is None:
            return bool(dep_value)

        return dep_value in self._description.dependency_values

    async def async_set_native_value(self, value: float) -> None:
        """Set a new value and push to the device."""
        _LOGGER.debug("redsea.number.set_native_value %s", value)

        f_value: Any = (
            int(value)
            if self._description.native_unit_of_measurement == UnitOfTime.SECONDS
            else value
        )
        self._attr_native_value = cast(float | None, f_value)

        self._device.set_data(self._description.value_name, f_value)
        await self._device.push_values(self._source)
        await self._device.async_request_refresh()

    @cached_property
    def available(self) -> bool:  # type: ignore[override]
        return self._compute_available()


# REEFLED
class ReefLedNumberEntity(ReefBeatNumberEntity):
    """LED-specific number entity (some values require POST to a special endpoint)."""

    def __init__(
        self, device: _HasDeviceInfo, description: ReefLedNumberEntityDescription
    ) -> None:
        super().__init__(device, description)
        self._led_description = description

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self._device.set_data(self._description.value_name, value)
        self.async_write_ha_state()

        # POST to special endpoint when required.
        if self._led_description.post_specific:
            if isinstance(self._device, _HasPostSpecific):
                await self._device.post_specific(self._led_description.post_specific)
            else:
                _LOGGER.debug(
                    "Device does not support post_specific; falling back to push_values"
                )
                await self._device.push_values(self._source, "post")
        else:
            await self._device.push_values(self._source, "post")

        await self._device.async_request_refresh()


# REEFDOSE
class ReefDoseNumberEntity(ReefBeatNumberEntity):
    """Dose-specific number entity (head-scoped pushes)."""

    def __init__(
        self, device: _HasDeviceInfo, description: ReefDoseNumberEntityDescription
    ) -> None:
        super().__init__(device, description)
        self._dose_description = description
        self._head = description.head

        # Attach per-head entities to the head device card, not the base doser device.
        if self._head > 0:
            base_di = dict(self._device.device_info)
            base_identifiers = base_di.get("identifiers") or {
                (DOMAIN, self._device.serial)
            }
            domain, ident = next(iter(cast(set[tuple[str, str]], base_identifiers)))

            di_dict: dict[str, Any] = {
                "identifiers": {(domain, ident, f"head_{self._head}")},
                "name": f"{self._device.title} head {self._head}",
            }

            for key in (
                "manufacturer",
                "model",
                "model_id",
                "hw_version",
                "sw_version",
            ):
                val = base_di.get(key)
                if isinstance(val, str) or val is None:
                    di_dict[key] = val

            via_device = base_di.get("via_device")
            if via_device is not None:
                di_dict["via_device"] = via_device

            self._attr_device_info = cast(DeviceInfo, di_dict)

    async def async_set_native_value(self, value: float) -> None:
        v: Any = int(value) if float(value).is_integer() else value
        self._attr_native_value = cast(float | None, v)

        self._device.set_data(self._description.value_name, v)
        self.async_write_ha_state()

        head = self._dose_description.head
        if head > 0:
            if self._dose_description.translation_key != "calibration_dose_value":
                # Push head-scoped changes via coordinator API.
                await self._device.push_values(source="/configuration", head=head)
        else:
            await self._device.push_values("/device-settings")

        await self._device.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        head = self._dose_description.head
        if head <= 0:
            return

        if self._dose_description.dependency:
            self._attr_available = self._device.get_data(
                self._dose_description.dependency
            )
            self.async_on_remove(
                self.hass.bus.async_listen(
                    self._dose_description.dependency, self._handle_available_update
                )
            )
        else:
            self._attr_available = True

    @callback
    def _handle_available_update(self, event: Any) -> None:
        if self._dose_description.dependency is not None:
            self._attr_available = self._device.get_data(
                self._dose_description.dependency
            )

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return device info extended with the head identifier (non-mutating)."""
        return cast(ReefDoseCoordinator, self._device).head_device_info(self._head)


# REEFRUN
class ReefRunNumberEntity(ReefBeatNumberEntity):
    """Run-specific number entity (pump-scoped)."""

    def __init__(
        self, device: _HasDeviceInfo, description: ReefRunNumberEntityDescription
    ) -> None:
        super().__init__(device, description)
        self._run_description = description
        self._pump = description.pump

    async def async_set_native_value(self, value: float) -> None:
        v = int(value)
        self._attr_native_value = float(v)

        if self._description.key == f"preview_pump_{self._pump}_intensity":
            self._device.set_data(self._description.value_name, v)
            self.async_write_ha_state()
            return

        if self._description.key == f"pump_{self._pump}_intensity" and isinstance(
            self._device, _HasPumpIntensity
        ):
            await self._device.set_pump_intensity(self._pump, v)
            self.async_write_ha_state()
            await self._device.push_values(source="/pump/settings", pump=self._pump)
            await self._device.async_request_refresh()
            return

        self._device.set_data(self._description.value_name, v)
        self.async_write_ha_state()

        if isinstance(self._device, _HasPumpIntensity):
            await self._device.push_values(source=self._source, pump=self._pump)
        else:
            await self._device.push_values(self._source)
        await self._device.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Register event listener after HA has set `self.hass`."""
        await super().async_added_to_hass()
        self._attr_available = True

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return per-pump device info for ReefRun."""
        return cast(ReefRunCoordinator, self._device).pump_device_info(self._pump)


# REEFWAVE
class ReefWaveNumberEntity(ReefBeatNumberEntity):
    """Wave preview number entity (dynamic min/max/step depending on wave type)."""

    @callback
    def _handle_coordinator_update(self) -> None:
        self._handle_device_update()

    @callback
    def _handle_device_update(self) -> None:
        value = self._device.get_data(self._description.value_name, True)

        preview_type = self._device.get_data(
            "$.sources[?(@.name=='/preview')].data.type", True
        )

        if (
            self._description.key == "wave_preview_wave_duration"
            and preview_type == "su"
        ):
            # Limit values for surface mode.
            self._attr_native_min_value = 0.5
            self._attr_native_max_value = 5.9
            self._attr_native_step = 0.1
        else:
            # description fields are Optional[float] in stubs; keep previous values if None.
            self._attr_native_min_value = (
                self._description.native_min_value or self._attr_native_min_value
            )
            self._attr_native_max_value = (
                self._description.native_max_value or self._attr_native_max_value
            )
            self._attr_native_step = (
                self._description.native_step or self._attr_native_step
            )

            if value is not None:
                value = int(value)

        if value is None:
            self._attr_available = False
            self._attr_native_value = None
        else:
            self._attr_available = self._compute_available()
            self._attr_native_value = cast(float | None, value)
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set a new value and push to the device."""
        _LOGGER.debug(
            "redsea.number.set_native_value %s %s" % (self._description.key, value)
        )

        f_value: Any = (
            int(value)
            if self._description.native_unit_of_measurement == UnitOfTime.SECONDS
            else value
        )

        self._attr_native_value = cast(float | None, f_value)

        self._device.set_data(self._description.value_name, f_value)
        self.async_write_ha_state()


# REEFATO+
class ReefATOVolumeLeftNumberEntity(ReefBeatNumberEntity):
    """ATO number: remaining reservoir volume."""

    async def async_set_native_value(self, value: float) -> None:
        volume_ml = int(value)
        if isinstance(self._device, _HasATOVolumeLeft):
            await self._device.set_volume_left(volume_ml)
        else:
            # Fallback: set locally and push (keeps integration usable even if coordinator differs)
            self._device.set_data(self._description.value_name, volume_ml)
            await self._device.push_values(self._source)

        await self._device.async_request_refresh()


# =============================================================================
# MAINTENANCE INTERVAL NUMBER
# =============================================================================


class MaintenanceIntervalNumberEntity(ReefRoleMixin, NumberEntity):  # type: ignore[misc]
    """Number entity exposing the per-instance maintenance interval (days).

    The entity is a thin facade over the persistent MaintenanceStore: its
    native_value reads `store.get_interval(...)` and `async_set_native_value`
    writes back. The matching MaintenanceButtonEntity reads the same value
    when computing `days_left`.

    `reef_role` (via the mixin) is set to "<task.translation_key>_interval"
    so blueprints and cards can distinguish the interval entity from the
    main maintenance entity (the button).
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-range"
    _attr_entity_category = EntityCategory.CONFIG
    # Slider gives an immediate visual of the tunable range; min/max and unit
    # come from the task definition (see catalogue in maintenance.py).
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 1.0
    # Intervals are inherently integer; hide trailing ".0" in the UI.
    _attr_suggested_display_precision = 0

    # Days-per-unit conversion factors. Storage stays in days everywhere;
    # only this entity converts to/from the task's display unit.
    _DAYS_PER_UNIT: dict[str, int] = {"weeks": 7, "months": 30}

    def __init__(
        self,
        device: ReefBeatCoordinator,
        task: "MaintenanceTask",
        sub_id: int = 0,
    ) -> None:
        self._device = device
        self._task = task
        self._sub_id = sub_id

        suffix = f"_{sub_id}" if sub_id > 0 else ""
        self._attr_unique_id = f"{device.serial}_{task.key}_interval{suffix}"

        # translation_key is the task's role with "_interval" appended; the
        # mixin exposes this as reef_role so blueprints can target intervals
        # separately from the action button.
        # translation_key carries the display unit suffix so the entity name
        # can be properly localized in each language (e.g. "Clean lens (weeks)"
        # vs "Clean motor (months)"). Storage remains in days regardless.
        unit = getattr(task, "unit", "weeks")
        self._attr_translation_key = f"{task.translation_key}_interval_{unit}"

        # Convert the day-based bounds into the task's display unit (weeks/months).
        # Storage remains in days; only the slider UI sees the converted values.
        factor = self._DAYS_PER_UNIT.get(unit, 7)
        self._unit_factor = factor
        # No native_unit_of_measurement: the unit is encoded in the entity
        # name via the translation_key, so the same slider works for weeks
        # and months without requiring HA to localize a custom unit string.
        self._attr_native_min_value = float(task.min_days // factor)
        self._attr_native_max_value = float(task.max_days // factor)

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

    # ---- store access -----------------------------------------------------

    @property
    def _store(self) -> "MaintenanceStore":
        """Return the device's MaintenanceStore, lazy-creating a fallback.

        See `MaintenanceButtonEntity._store` for the rationale.
        """
        device = cast(Any, self._device)
        store = getattr(device, "maintenance", None)
        if store is None:
            _LOGGER.warning(
                "MaintenanceStore missing on %s; using ephemeral fallback "
                "(intervals will revert to defaults across restarts)",
                getattr(device, "_title", device.__class__.__name__),
            )
            store = MaintenanceStore(
                getattr(device, "_hass"),
                f"fallback_{id(device)}",
            )
            device.maintenance = store
        return store

    @property
    def native_value(self) -> float | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the stored interval (days) converted to the display unit."""
        try:
            days = self._store.get_interval(
                self._device.serial,
                self._sub_id,
                self._task.key,
                self._task.default_days,
            )
        except Exception:
            days = self._task.default_days
        # Integer floor-division: 35 days / 7 = 5 weeks; 90 days / 30 = 3 months.
        return float(days // self._unit_factor)

    # NOTE: the blank line between methods plus the next `async def` signature
    # are occasionally mis-reported as uncovered by coverage.py under Python
    # 3.14, even though the test suite exercises `async_set_native_value`. The
    # `noqa` on the next line prevents linters from joining them while keeping
    # tracing happy on both old and new Python versions.
    async def async_set_native_value(self, value: float) -> None:  # noqa: E303
        """Persist the slider value as days (converted from the display unit)."""
        days = int(round(value)) * self._unit_factor
        await self._store.async_set_interval(
            self._device.serial, self._sub_id, self._task.key, days
        )

    # ---- lifecycle --------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _on_store_change() -> None:
            self.async_write_ha_state()

        self._unsub = self._store.async_add_listener(
            self._device.serial, self._sub_id, self._task.key, _on_store_change
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()
