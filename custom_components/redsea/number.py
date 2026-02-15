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
    ReefBeatCoordinator,
    ReefDoseCoordinator,
    ReefLedCoordinator,
    ReefLedG2Coordinator,
    ReefMatCoordinator,
    ReefRunCoordinator,
    ReefVirtualLedCoordinator,
    ReefWaveCoordinator,
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
                    native_min_value=0,
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
                    native_min_value=1,
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

    async_add_entities(entities, update_before_add=True)


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
