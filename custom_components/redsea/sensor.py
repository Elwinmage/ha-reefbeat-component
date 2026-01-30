"""Sensor entities for the Red Sea Reefeat integration.

This module registers Home Assistant `sensor` entities for supported devices.

Design notes (strict typing + HA patterns)
------------------------------------------
This file intentionally follows the "select/number style" used in this repo:

- We do **not** subclass `CoordinatorEntity` here.
- Instead, each entity subscribes to the device/coordinator via
  `device.async_add_listener(...)` inside `async_added_to_hass`.
- Entities read from a local data cache using `device.get_data(...)`.

This approach avoids:
- Pylance strict incompatibilities around `CoordinatorEntity.available`
- Stubs mismatches for descriptor signatures
- Unclear lifetime/availability semantics when the coordinator is custom

Strict typing strategy
----------------------
- We define a `DescriptionT` union for all description dataclasses used by sensors.
- Each entity stores the typed union in `self._description`.
- Subclasses narrow `self._description` via `cast(...)` before accessing fields
  specific to that description type (e.g. `value_name`, `id_name`).
- Special coordinator capabilities (`cloud_link`, `get_current_value`) are modeled
  with `Protocol`s and accessed using `cast(Protocol, device)`.

StateType constraints
---------------------
Home Assistant `StateType` is typically `str | int | float | None` (and a few other
simple types depending on HA version). It does **not** include `datetime.date`.
When a sensor has `device_class=DATE`, the native value should be an ISO-8601
string (YYYY-MM-DD). This file returns `.date().isoformat()` accordingly.

DeviceInfo handling
-------------------
`device.device_info` may be shared between entities. When we need to customize
it (e.g. per head / per pump), we clone it and adjust identifiers to avoid
mutating shared state.
"""

from __future__ import annotations

import datetime
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Protocol, TypeAlias, cast, runtime_checkable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ATO_MODE_INTERNAL_NAME,
    DOMAIN,
    LED_BLUE_INTERNAL_NAME,
    LED_WHITE_INTERNAL_NAME,
    LIGHTS_LIBRARY,
    SUPPLEMENTS_LIBRARY,
    WAVE_DIRECTIONS,
    WAVE_SCHEDULE_PATH,
    WAVE_TYPES,
    WAVES_LIBRARY,
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
from .entity import ReefBeatRestoreEntity, RestoreSpec
from .i18n import translate

_LOGGER = logging.getLogger(__name__)

# HA's StateType doesn't include date/datetime, but SensorEntity supports them for
# device classes like DATE/TIMESTAMP.
SensorNativeValue: TypeAlias = StateType | datetime.date | datetime.datetime

# -----------------------------------------------------------------------------
# Protocols (capability-based typing)
# -----------------------------------------------------------------------------


@runtime_checkable

# =============================================================================
# Classes
# =============================================================================

class _CloudLinkedCoordinator(Protocol):
    """Coordinator capability: indicates a cloud-linked device.

    Some coordinators expose a local device but are linked to a ReefBeat cloud account.
    We previously detected this by checking base-class names. Prefer a capability check.
    """

    def cloud_link(self) -> StateType: ...


@runtime_checkable
class _WaveValueCoordinator(Protocol):
    """Coordinator capability: expose current wave values.

    Some coordinator implementations provide a convenience getter that returns
    the current wave schedule values (e.g. type, direction, intensities).
    We model it as a Protocol and cast before calling.
    """

    def get_current_value(self, basename: str, name: str) -> Any: ...


# -----------------------------------------------------------------------------
# Entity descriptions
# -----------------------------------------------------------------------------


@dataclass(kw_only=True, frozen=True)
class ReefBeatSensorEntityDescription(SensorEntityDescription):
    """Description for device-backed sensors (most sensors).

    `value_fn` receives the coordinator instance and must return a Home Assistant
    StateType (e.g. str/int/float/None). This is the most strongly typed and
    avoids `value_name` JSONPath strings where possible.
    """

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefBeatCoordinator], StateType]


@dataclass(kw_only=True, frozen=True)
class ReefBeatCloudSensorEntityDescription(SensorEntityDescription):
    """Description for cloud-library sensors.

    These read by `value_name` JSONPath from the cloud coordinator response.
    """

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = ""


@dataclass(kw_only=True, frozen=True)
class ReefDoseSensorEntityDescription(SensorEntityDescription):
    """Description for per-head ReefDose sensors.

    - `head` selects the dosing head index.
    - `value_name` is the JSONPath to read.
    - `with_attr_*` optionally adds extra attributes (e.g. schedule data).
    """

    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: str = ""
    with_attr_name: str | None = None
    with_attr_value: str | None = None
    head: int = 0


@dataclass(kw_only=True, frozen=True)
class RestoreSensorEntityDescription(SensorEntityDescription):
    """Description for restore-capable sensors.

    These sensors keep an internal value that can be restored across restarts and
    optionally sync that value into the coordinator cache.

    - `value_name` is where to store the restored value into the cache.
    - `dependency` is an event key (string) to listen to for updates.
    """

    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    head: int = 0
    value_name: str | None = None
    dependency: str | None = None


@dataclass(kw_only=True, frozen=True)
class ReefRunSensorEntityDescription(SensorEntityDescription):
    """Description for per-pump ReefRun sensors."""

    exists_fn: Callable[[ReefRunCoordinator], bool] = lambda _: True
    value_name: str = ""
    pump: int = 0
    with_attr_name: str | None = None
    with_attr_value: str | None = None


@dataclass(kw_only=True, frozen=True)
class ReefLedScheduleSensorEntityDescription(SensorEntityDescription):
    """Description for LED schedule sensors.

    These show the current program name for a schedule id and expose backing
    raw data in extra attributes.
    """

    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_name: str = ""
    id_name: int = 0
    with_attr_name: str | None = None
    with_attr_value: str | None = None


@dataclass(kw_only=True, frozen=True)
class ReefWaveSensorEntityDescription(SensorEntityDescription):
    """Description for current wave schedule sensors.

    `value_basename` identifies the active schedule source, while `value_name`
    selects the field (e.g. 'type', 'direction', 'fti').
    """

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_basename: str = WAVE_SCHEDULE_PATH
    value_name: str = ""


DescriptionT = (
    ReefBeatSensorEntityDescription
    | ReefBeatCloudSensorEntityDescription
    | ReefDoseSensorEntityDescription
    | RestoreSensorEntityDescription
    | ReefRunSensorEntityDescription
    | ReefLedScheduleSensorEntityDescription
    | ReefWaveSensorEntityDescription
)


# -----------------------------------------------------------------------------
# Static sensors (descriptions)
# -----------------------------------------------------------------------------

CLOUD_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription(
        key="cloud_account",
        translation_key="cloud_account",
        value_fn=lambda device: cast(_CloudLinkedCoordinator, device).cloud_link(),
        icon="mdi:cloud-sync-outline",
    ),
)

USER_SENSORS: tuple[ReefBeatCloudSensorEntityDescription, ...] = (
    ReefBeatCloudSensorEntityDescription(
        key="email",
        translation_key="email",
        value_name="$.sources[?(@.name=='/user')].data.email",
        icon="mdi:at",
    ),
    ReefBeatCloudSensorEntityDescription(
        key="backup_email",
        translation_key="backup_email",
        value_name="$.sources[?(@.name=='/user')].data.backup_email",
        icon="mdi:at",
    ),
    ReefBeatCloudSensorEntityDescription(
        key="first_name",
        translation_key="first_name",
        value_name="$.sources[?(@.name=='/user')].data.first_name",
        icon="mdi:account",
    ),
    ReefBeatCloudSensorEntityDescription(
        key="last_name",
        translation_key="last_name",
        value_name="$.sources[?(@.name=='/user')].data.last_name",
        icon="mdi:account-outline",
    ),
    ReefBeatCloudSensorEntityDescription(
        key="mobile_number",
        translation_key="mobile_number",
        value_name="$.sources[?(@.name=='/user')].data.mobile_number",
        icon="mdi:phone",
    ),
    ReefBeatCloudSensorEntityDescription(
        key="language",
        translation_key="language",
        value_name="$.sources[?(@.name=='/user')].data.language",
        icon="mdi:translate",
    ),
    ReefBeatCloudSensorEntityDescription(
        key="country",
        translation_key="country",
        value_name="$.sources[?(@.name=='/user')].data.country",
        icon="mdi:earth",
    ),
    ReefBeatCloudSensorEntityDescription(
        key="zip_code",
        translation_key="zip_code",
        value_name="$.sources[?(@.name=='/user')].data.zip_code",
        icon="mdi:mailbox",
    ),
)

COMMON_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription(
        key="mode",
        translation_key="mode",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/mode')].data.mode"
        ),
        icon="mdi:play",
    ),
    ReefBeatSensorEntityDescription(
        key="last_alert_message",
        translation_key="last_alert_message",
        value_fn=lambda device: device.get_data("$.message.alert.message", True),
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ReefBeatSensorEntityDescription(
        key="last_message",
        translation_key="last_message",
        value_fn=lambda device: device.get_data("$.message.message", True),
        icon="mdi:note-check",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ReefBeatSensorEntityDescription(
        key="ip",
        translation_key="ip",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/wifi')].data.ip"
        ),
        icon="mdi:check-network-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ReefBeatSensorEntityDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/wifi')].data.ssid"
        ),
        icon="mdi:wifi-star",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ReefBeatSensorEntityDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/wifi')].data.signal_dBm"
        ),
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        icon="mdi:signal",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ReefBeatSensorEntityDescription(
        key="wifi_quality",
        translation_key="wifi_quality",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/wifi')].data.signal_dBm"
        ),
        icon="mdi:wifi-strength-4",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

LED_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription(
        key="fan",
        translation_key="fan",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/manual')].data.fan"
        ),
        exists_fn=lambda device: not isinstance(device, ReefVirtualLedCoordinator),
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan",
    ),
    ReefBeatSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/manual')].data.temperature"
        ),
        exists_fn=lambda device: not isinstance(device, ReefVirtualLedCoordinator),
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key="moon_intensity",
        translation_key="moon_intensity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/moonphase')].data.intensity"
        ),
        icon="mdi:moon-waning-crescent",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="todays_moon_day",
        translation_key="todays_moon_day",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/moonphase')].data.todays_moon_day"
        ),
        icon="mdi:calendar-today",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="next_full_moon",
        translation_key="next_full_moon",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/moonphase')].data.next_full_moon"
        ),
        icon="mdi:moon-full",
    ),
    ReefBeatSensorEntityDescription(
        key="next_new_moon",
        translation_key="next_new_moon",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/moonphase')].data.next_new_moon"
        ),
        icon="mdi:moon-new",
    ),
    ReefBeatSensorEntityDescription(
        key="acclimation_duration",
        translation_key="acclimation_duration",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/acclimation')].data.duration"
        ),
        icon="mdi:calendar-expand-horizontal",
    ),
    ReefBeatSensorEntityDescription(
        key="acclimation_start_intensity_factor",
        translation_key="acclimation_start_intensity_factor",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/acclimation')].data.start_intensity_factor"
        ),
        icon="mdi:sun-wireless-outline",
    ),
)

G2_LED_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription(
        key="white",
        translation_key="white",
        value_fn=lambda device: device.get_data(LED_WHITE_INTERNAL_NAME),
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:lightbulb-outline",
    ),
    ReefBeatSensorEntityDescription(
        key="blue",
        translation_key="blue",
        value_fn=lambda device: device.get_data(LED_BLUE_INTERNAL_NAME),
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:lightbulb",
    ),
)

MAT_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription(
        key="days_till_end_of_roll",
        translation_key="days_till_end_of_roll",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.days_till_end_of_roll"
        ),
        icon="mdi:sort-calendar-ascending",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="today_usage",
        translation_key="today_usage",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.today_usage"
        ),
        icon="mdi:tape-measure",
        suggested_display_precision=2,
    ),
    ReefBeatSensorEntityDescription(
        key="daily_average_usage",
        translation_key="daily_average_usage",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.daily_average_usage"
        ),
        icon="mdi:tape-measure",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key="total_usage",
        translation_key="total_usage",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.total_usage"
        )
        / 100,
        icon="mdi:paper-roll",
        suggested_display_precision=2,
    ),
    ReefBeatSensorEntityDescription(
        key="remaining_length",
        translation_key="remaining_length",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.remaining_length"
        )
        / 100,
        icon="mdi:paper-roll-outline",
        suggested_display_precision=2,
    ),
    ReefBeatSensorEntityDescription(
        key="model",
        translation_key="model",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/configuration')].data.model"
        ),
        icon="mdi:paper-roll-outline",
    ),
)

# -----------------------------------------------------------------------------
# Derived dynamic description lists (LED schedules)
# -----------------------------------------------------------------------------

_led_schedules: list[ReefLedScheduleSensorEntityDescription] = []
for auto_id in range(1, 8):
    _led_schedules.extend(
        [
            ReefLedScheduleSensorEntityDescription(
                key="auto_" + str(auto_id),
                translation_key="auto_" + str(auto_id),
                value_name="$.sources[?(@.name=='/preset_name')].data[?(@.day=="
                + str(auto_id)
                + ")].name",
                exists_fn=lambda device: device.get_data(
                    "$.sources[?(@.name=='/preset_name')].data", True
                )
                is not None,
                id_name=auto_id,
                icon="mdi:calendar",
            ),
            ReefLedScheduleSensorEntityDescription(
                key="auto_" + str(auto_id),
                translation_key="auto_" + str(auto_id),
                value_name="$.sources[?(@.name=='/preset_name/"
                + str(auto_id)
                + "')].data.name",
                exists_fn=lambda device: device.get_data(
                    "$.sources[?(@.name=='/preset_name/"
                    + str(auto_id)
                    + "')].data.name",
                    True,
                )
                is not None,
                id_name=auto_id,
                icon="mdi:calendar",
            ),
        ]
    )

LED_SCHEDULES: tuple[ReefLedScheduleSensorEntityDescription, ...] = tuple(
    _led_schedules
)

# -----------------------------------------------------------------------------
# Wave / ATO descriptions
# -----------------------------------------------------------------------------

WAVE_SCHEDULE_SENSORS: tuple[ReefWaveSensorEntityDescription, ...] = (
    ReefWaveSensorEntityDescription(
        key="wave_type",
        translation_key="wave_type",
        value_name="type",
        icon="mdi:wave",
    ),
    ReefWaveSensorEntityDescription(
        key="wave_name",
        translation_key="name",
        value_name="name",
        icon="mdi:identifier",
    ),
    ReefWaveSensorEntityDescription(
        key="wave_direction",
        translation_key="wave_direction",
        value_name="direction",
        icon="mdi:waves-arrow-right",
    ),
    ReefWaveSensorEntityDescription(
        key="wave_forward_time",
        translation_key="wave_forward_time",
        value_name="frt",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:waves-arrow-right",
    ),
    ReefWaveSensorEntityDescription(
        key="wave_backward_time",
        translation_key="wave_backward_time",
        value_name="rrt",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:waves-arrow-left",
    ),
    ReefWaveSensorEntityDescription(
        key="wave_forward_intensity",
        translation_key="wave_forward_intensity",
        value_name="fti",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:waves-arrow-right",
    ),
    ReefWaveSensorEntityDescription(
        key="wave_backward_intensity",
        translation_key="wave_backward_intensity",
        value_name="rti",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:waves-arrow-left",
    ),
    ReefWaveSensorEntityDescription(
        key="wave_step",
        translation_key="wave_step",
        value_name="sn",
        icon="mdi:stairs",
    ),
)

ATO_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription(
        key="s_water_level",
        translation_key="water_level",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.water_level"
        ),
        icon="mdi:waves-arrow-up",
    ),
    ReefBeatSensorEntityDescription(
        key="today_fills",
        translation_key="today_fills",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.today_fills"
        ),
        icon="mdi:counter",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="today_volume_usage",
        translation_key="today_volume_usage",
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.today_volume_usage"
        ),
        icon="mdi:waves-arrow-up",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="total_volume_usage",
        translation_key="total_volume_usage",
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.total_volume_usage"
        ),
        icon="mdi:waves-arrow-up",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="total_fills",
        translation_key="total_fills",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.total_fills"
        ),
        icon="mdi:counter",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="daily_fills_average",
        translation_key="daily_fills_average",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.daily_fills_average"
        ),
        icon="mdi:counter",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key="daily_volume_average",
        translation_key="daily_volume_average",
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.daily_volume_average"
        ),
        icon="mdi:waves-arrow-up",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="volume_left",
        translation_key="volume_left",
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        device_class=SensorDeviceClass.VOLUME,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.volume_left"
        ),
        icon="mdi:water-pump-off",
        suggested_display_precision=0,
    ),
    ReefBeatSensorEntityDescription(
        key="current_level",
        translation_key="current_level",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.ato_sensor.current_level"
        ),
        icon="mdi:car-coolant-level",
    ),
    ReefBeatSensorEntityDescription(
        key="current_read",
        translation_key="current_read",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.ato_sensor.current_read"
        ),
        icon="mdi:water-thermometer-outline",
        suggested_display_precision=1,
    ),
    ReefBeatSensorEntityDescription(
        key="temperature_probe_status",
        translation_key="temperature_probe_status",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.ato_sensor.temperature_probe_status"
        ),
        icon="mdi:thermometer-check",
    ),
    ReefBeatSensorEntityDescription(
        key="ato_mode",
        translation_key="ato_mode",
        value_fn=lambda device: device.get_data(ATO_MODE_INTERNAL_NAME),
        icon="mdi:play",
    ),
    ReefBeatSensorEntityDescription(
        key="pump_state",
        translation_key="pump_state",
        value_fn=lambda device: device.get_data(
            "$.sources[?(@.name=='/dashboard')].data.pump_state"
        ),
        icon="mdi:pump",
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
    """Set up sensor entities for a config entry.

    The device/coordinator instance is stored in `hass.data[DOMAIN][entry.entry_id]`.
    This function:
    - Narrows the coordinator type with `cast(...)` when we need device-specific fields.
    - Creates entities from static description lists.
    - Creates dynamic cloud library entities when running as a cloud coordinator.
    """
    device = cast(ReefBeatCoordinator, hass.data[DOMAIN][entry.entry_id])
    entities: list[SensorEntity] = []

    _LOGGER.debug("SENSORS")

    # Cloud linked coordinator diagnostics
    # Avoid brittle base-class-name checks; use capability instead.
    if isinstance(device, _CloudLinkedCoordinator):
        entities.extend(
            ReefBeatSensorEntity(device, description)
            for description in CLOUD_SENSORS
            if description.exists_fn(device)
        )

    if isinstance(device, (ReefLedG2Coordinator, ReefVirtualLedCoordinator)):
        entities.extend(
            ReefBeatSensorEntity(device, description)
            for description in G2_LED_SENSORS
            if description.exists_fn(device)
        )

    if isinstance(device, (ReefLedCoordinator, ReefLedG2Coordinator)):
        entities.extend(
            ReefBeatSensorEntity(device, description)
            for description in LED_SENSORS
            if description.exists_fn(device)
        )
    elif isinstance(device, ReefMatCoordinator):
        entities.extend(
            ReefBeatSensorEntity(device, description)
            for description in MAT_SENSORS
            if description.exists_fn(device)
        )
    elif isinstance(device, ReefWaveCoordinator):
        entities.extend(
            ReefWaveSensorEntity(device, description)
            for description in WAVE_SCHEDULE_SENSORS
            if description.exists_fn(device)
        )
    elif isinstance(device, ReefDoseCoordinator):
        dose_device = device  # already narrowed

        ds0: tuple[ReefDoseSensorEntityDescription, ...] = (
            ReefDoseSensorEntityDescription(
                key="dosing_queue",
                translation_key="dosing_queue",
                icon="mdi:tray-full",
                value_name="$.sources[?(@.name=='/dosing-queue')].data",
                with_attr_name="queue",
                with_attr_value="$.sources[?(@.name=='/dosing-queue')].data",
                head=0,
            ),
        )
        entities.extend(
            ReefBeatSensorEntity(device, description)
            for description in ds0
            if description.exists_fn(dose_device)
        )

        # Build dynamic descriptions using lists (cheaper + clearer than tuple +=)
        ds: list[ReefDoseSensorEntityDescription] = []
        init_sensors: list[RestoreSensorEntityDescription] = []

        for head in range(1, int(dose_device.heads_nb) + 1):
            ds.extend(
                [
                    ReefDoseSensorEntityDescription(
                        key="state_head_" + str(head),
                        translation_key="head_state",
                        icon="mdi:cog-play",
                        value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                        + str(head)
                        + ".state",
                        head=head,
                    ),
                    ReefDoseSensorEntityDescription(
                        key="last_calibration_head_" + str(head),
                        translation_key="last_calibration",
                        icon="mdi:calendar-start",
                        value_name="$.sources[?(@.name=='/head/"
                        + str(head)
                        + "/settings')].data.last_calibrated",
                        device_class=SensorDeviceClass.DATE,
                        head=head,
                    ),
                    ReefDoseSensorEntityDescription(
                        key="supplement_head_" + str(head),
                        translation_key="supplement",
                        icon="mdi:shaker",
                        value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                        + str(head)
                        + ".supplement",
                        with_attr_name="supplement",
                        with_attr_value="$.sources[?(@.name=='/head/"
                        + str(head)
                        + "/settings')].data.supplement",
                        head=head,
                    ),
                    ReefDoseSensorEntityDescription(
                        key="auto_dosed_today_head_" + str(head),
                        translation_key="auto_dosed_today",
                        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                        device_class=SensorDeviceClass.VOLUME,
                        icon="mdi:cup-water",
                        suggested_display_precision=0,
                        value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                        + str(head)
                        + ".auto_dosed_today",
                        head=head,
                    ),
                    ReefDoseSensorEntityDescription(
                        key="manual_dosed_today_head_" + str(head),
                        translation_key="manual_dosed_today",
                        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                        device_class=SensorDeviceClass.VOLUME,
                        icon="mdi:cup-water",
                        suggested_display_precision=0,
                        value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                        + str(head)
                        + ".manual_dosed_today",
                        head=head,
                    ),
                    ReefDoseSensorEntityDescription(
                        key="doses_today_head_" + str(head),
                        translation_key="doses_today",
                        icon="mdi:counter",
                        suggested_display_precision=0,
                        value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                        + str(head)
                        + ".doses_today",
                        head=head,
                    ),
                    ReefDoseSensorEntityDescription(
                        key="daily_dose_head_" + str(head),
                        translation_key="daily_dose",
                        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                        device_class=SensorDeviceClass.VOLUME,
                        icon="mdi:cup-water",
                        suggested_display_precision=0,
                        value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                        + str(head)
                        + ".daily_dose",
                        head=head,
                    ),
                    ReefDoseSensorEntityDescription(
                        key="remaining_days_head_" + str(head),
                        translation_key="remaining_days",
                        native_unit_of_measurement=UnitOfTime.DAYS,
                        icon="mdi:sort-calendar-ascending",
                        suggested_display_precision=0,
                        value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                        + str(head)
                        + ".remaining_days",
                        head=head,
                    ),
                    ReefDoseSensorEntityDescription(
                        key="daily_doses_head_" + str(head),
                        translation_key="daily_doses",
                        icon="mdi:counter",
                        suggested_display_precision=0,
                        value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                        + str(head)
                        + ".daily_doses",
                        head=head,
                    ),
                    ReefDoseSensorEntityDescription(
                        key="schedule_head_" + str(head),
                        translation_key="schedule_head",
                        icon="mdi:chart-timeline",
                        value_name="$.sources[?(@.name=='/head/"
                        + str(head)
                        + "/settings')].data.schedule.type",
                        with_attr_name="schedule",
                        with_attr_value="$.sources[?(@.name=='/head/"
                        + str(head)
                        + "/settings')].data.schedule",
                        head=head,
                    ),
                ]
            )

        entities.extend(
            RestoreSensorEntity(device, description)
            for description in tuple(init_sensors)
            if description.exists_fn(dose_device)
        )

        entities.extend(
            ReefDoseSensorEntity(device, description)
            for description in tuple(ds)
            if description.exists_fn(dose_device)
        )

    elif isinstance(device, ReefATOCoordinator):
        entities.extend(
            ReefBeatSensorEntity(device, description)
            for description in ATO_SENSORS
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefRunCoordinator):
        run_device = device  # already narrowed

        ds_run: list[ReefRunSensorEntityDescription] = []
        for pump in range(1, 3):
            ds_run.extend(
                [
                    ReefRunSensorEntityDescription(
                        key="name_pump_" + str(pump),
                        translation_key="name",
                        icon="mdi:pump",
                        value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                        + str(pump)
                        + ".name",
                        pump=pump,
                    ),
                    ReefRunSensorEntityDescription(
                        key="type_pump_" + str(pump),
                        translation_key="type",
                        icon="mdi:pump",
                        value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                        + str(pump)
                        + ".type",
                        pump=pump,
                    ),
                    ReefRunSensorEntityDescription(
                        key="model_pump_" + str(pump),
                        translation_key="model",
                        icon="mdi:pump",
                        value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                        + str(pump)
                        + ".model",
                        pump=pump,
                    ),
                    ReefRunSensorEntityDescription(
                        key="state_pump_" + str(pump),
                        translation_key="state",
                        icon="mdi:pump",
                        value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                        + str(pump)
                        + ".state",
                        entity_category=EntityCategory.DIAGNOSTIC,
                        pump=pump,
                    ),
                    ReefRunSensorEntityDescription(
                        key="temperature_pump_" + str(pump),
                        translation_key="temperature",
                        icon="mdi:thermometer",
                        value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                        + str(pump)
                        + ".temperature",
                        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                        device_class=SensorDeviceClass.TEMPERATURE,
                        state_class=SensorStateClass.MEASUREMENT,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        suggested_display_precision=1,
                        pump=pump,
                    ),
                ]
            )

        entities.extend(
            ReefRunSensorEntity(device, description)
            for description in tuple(ds_run)
            if description.exists_fn(run_device)
        )

    # Schedule sensors (LED coordinators)
    if isinstance(device, (ReefLedCoordinator, ReefVirtualLedCoordinator)):
        led_device = cast(ReefLedCoordinator, device)
        entities.extend(
            ReefLedScheduleSensorEntity(device, description)
            for description in LED_SCHEDULES
            if description.exists_fn(led_device)
        )

    # Common sensors (skip pure cloud + virtual LED to keep behavior consistent)
    if not isinstance(device, (ReefBeatCloudCoordinator, ReefVirtualLedCoordinator)):
        entities.extend(
            ReefBeatSensorEntity(device, description)
            for description in COMMON_SENSORS
            if description.exists_fn(device)
        )

    # Cloud library sensors
    if isinstance(device, ReefBeatCloudCoordinator):
        entities.extend(
            ReefBeatCloudSensorEntity(device, description)
            for description in USER_SENSORS
            if description.exists_fn(device)
        )

        progs = cast(
            list[dict[str, Any]],
            device.my_api.get_data(
                "$.sources[?(@.name=='" + LIGHTS_LIBRARY + "')].data"
            ),
        )
        cloud_descs: list[ReefBeatCloudSensorEntityDescription] = []
        for prog in progs:
            uid = prog.get("uid")
            cloud_descs.append(
                ReefBeatCloudSensorEntityDescription(
                    key="prog_" + str(uid),
                    translation_key="led_program",
                    icon="mdi:chart-bell-curve",
                    value_name="$.sources[?(@.name=='"
                    + LIGHTS_LIBRARY
                    + "')].data[?(@.uid=='"
                    + str(uid)
                    + "')].name",
                )
            )

        waves = cast(
            list[dict[str, Any]],
            device.my_api.get_data(
                "$.sources[?(@.name=='" + WAVES_LIBRARY + "')].data"
            ),
        )
        for wave in waves:
            uid = wave.get("uid")
            cloud_descs.append(
                ReefBeatCloudSensorEntityDescription(
                    key="wave_" + str(uid),
                    translation_key="wave_program",
                    icon="mdi:sine-wave",
                    value_name="$.sources[?(@.name=='"
                    + WAVES_LIBRARY
                    + "')].data[?(@.uid=='"
                    + str(uid)
                    + "')].name",
                )
            )
        if not device.disable_supplement:
            supplements = cast(
                list[dict[str, Any]],
                device.my_api.get_data(
                    "$.sources[?(@.name=='" + SUPPLEMENTS_LIBRARY + "')].data"
                ),
            )
            for supplement in supplements:
                uid = supplement.get("uid")
                cloud_descs.append(
                    ReefBeatCloudSensorEntityDescription(
                        key="supplement_" + str(uid),
                        translation_key="supplement_program",
                        icon="mdi:sine-supplement",
                        value_name="$.sources[?(@.name=='"
                        + SUPPLEMENTS_LIBRARY
                        + "')].data[?(@.uid=='"
                        + str(uid)
                        + "')].name",
                    )
                )

        entities.extend(
            ReefBeatCloudSensorEntity(device, description)
            for description in cloud_descs
            if description.exists_fn(device)
        )

    async_add_entities(entities, True)


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


# REEFBEAT
class ReefBeatSensorEntity(ReefBeatRestoreEntity, SensorEntity):  # type: ignore[reportIncompatibleVariableOverride]
    """Base sensor entity backed by a ReefBeat device/coordinator.

    Responsibilities:
    - Subscribe to coordinator changes via `async_add_listener`.
    - Compute native value + extra attributes using the entity description.
    - Provide base `device_info` that points to the coordinator’s device.

    Subclasses override `_get_value` and/or `_update_val` for specialized behavior.
    """

    _attr_has_entity_name = True

    @staticmethod
    def _restore_native_value(state: str) -> StateType:
        """Best-effort parse of restored state into a native value."""
        try:
            if re.fullmatch(r"-?\d+(?:\.\d+)?", state.strip()):
                return float(state)
        except Exception:
            pass
        return state

    def __init__(
        self, device: ReefBeatCoordinator, entity_description: DescriptionT
    ) -> None:
        ReefBeatRestoreEntity.__init__(
            self,
            device,
            restore=RestoreSpec("_attr_native_value", self._restore_native_value),
        )
        self._device = device

        self.entity_description = cast(SensorEntityDescription, entity_description)
        self._description: DescriptionT = entity_description

        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{self._description.key}"

    async def async_added_to_hass(self) -> None:
        """Restore last known value and prime from coordinator cache."""
        await super().async_added_to_hass()

        # If we restored a value, mark available so HA doesn't show `unavailable`.
        if self._attr_native_value is not None and not self._attr_available:
            self._attr_available = True

        # If coordinator already has fresh data, populate attributes now.
        if self._device.last_update_success:
            self._update_val()
            super()._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update cached `_attr_*` values from coordinator data."""
        self._update_val()
        super()._handle_coordinator_update()

    def _update_val(self) -> None:
        """Update native value and extra state attributes.

        Base behavior:
        - Mark entity available when we can compute a value.
        - Handle 'wifi_quality' as a derived sensor with an icon + qualitative output.
        - Otherwise compute native value via `_get_value`.
        - Optionally attach extra attributes based on `with_attr_*` description fields.
        """
        self._attr_available = True

        if self._description.key == "wifi_quality":
            signal_strength = cast(
                int,
                self._device.get_data("$.sources[?(@.name=='/wifi')].data.signal_dBm"),
            )
            if signal_strength < -80:
                self._attr_icon = "mdi:wifi-outline"
                self._attr_native_value = "Poor"
            elif signal_strength < -70:
                self._attr_icon = "mdi:wifi-strength-1"
                self._attr_native_value = "Low"
            elif signal_strength < -60:
                self._attr_icon = "mdi:wifi-strength-2"
                self._attr_native_value = "Medium"
            elif signal_strength < -50:
                self._attr_icon = "mdi:wifi-strength-3"
                self._attr_native_value = "Good"
            else:
                self._attr_native_value = "Excellent"
            return

        self._attr_native_value = self._get_value()

        with_attr_name = getattr(self._description, "with_attr_name", None)
        with_attr_value = getattr(self._description, "with_attr_value", None)
        if with_attr_name and with_attr_value:
            self._attr_extra_state_attributes = {
                with_attr_name: self._device.get_data(with_attr_value)
            }

    def _get_value(self) -> SensorNativeValue:
        """Compute the sensor native value for the current description."""
        if getattr(self._description, "translation_key", None) == "dosing_queue":
            value_name = cast(str, getattr(self._description, "value_name", ""))
            data = cast(list[dict[str, Any]], self._device.get_data(value_name))
            if data:
                return data[0].get("head")
            return translate("Empty", self._device.hass.config.language)

        if isinstance(self._description, ReefBeatSensorEntityDescription):
            return self._description.value_fn(self._device)

        if hasattr(self._description, "value_name"):
            value_name = cast(str, getattr(self._description, "value_name"))
            return self._device.get_data(value_name)

        _LOGGER.error("No method to get value for %s", self._description.key)
        return None

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return base device info for the coordinator device."""
        return self._device.device_info


# REEFLED
class ReefLedScheduleSensorEntity(ReefBeatSensorEntity):
    """LED schedule sensor.

    Exposes:
    - A friendly schedule/program name (native value)
    - Raw schedule/program data via extra attributes
    """

    _attr_has_entity_name = True

    def _update_val(self) -> None:
        self._attr_available = True
        desc = cast(ReefLedScheduleSensorEntityDescription, self._description)

        self._attr_native_value = self._device.get_data(desc.value_name)

        id_name = desc.id_name
        prog_data = self._device.get_data(
            f"$.sources[?(@.name=='/auto/{id_name}')].data"
        )
        cloud_data = self._device.get_data(
            f"$.sources[?(@.name=='/clouds/{id_name}')].data"
        )
        self._attr_extra_state_attributes = {"data": prog_data, "clouds": cloud_data}


# REEFDOSE
class ReefDoseSensorEntity(ReefBeatSensorEntity):
    """Per-head ReefDose sensor.

    This specializes:
    - per-head unique device info
    - date conversion for last calibration
    - an event fire when container volume increases (used by restore logic)
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefDoseSensorEntityDescription,
    ) -> None:
        super().__init__(device, entity_description)
        self._head: int = entity_description.head

    def _get_value(self) -> SensorNativeValue:
        desc = cast(ReefDoseSensorEntityDescription, self._description)
        if desc.translation_key == "last_calibration":
            raw = self._device.get_data(desc.value_name)
            if raw is None:
                return None
            try:
                ts = int(cast(int, raw))
            except (TypeError, ValueError):
                return None

            # Use UTC to avoid local timezone shifting the date (e.g. 1969-12-31).
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).date()
            return dt

        return self._device.get_data(desc.value_name)

    def _update_val(self) -> None:
        old_value = self._attr_native_value
        new_value = self._get_value()

        super()._update_val()

        desc = cast(ReefDoseSensorEntityDescription, self._description)
        if desc.translation_key == "container_volume":
            if (
                isinstance(new_value, (int, float))
                and isinstance(old_value, (int, float))
                and old_value < new_value
            ):
                self._device.hass.bus.fire(desc.value_name, {"value": new_value})

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return device info extended with the head identifier."""
        return cast(ReefDoseCoordinator, self._device).head_device_info(self._head)


# RESTORE
class RestoreSensorEntity(ReefDoseSensorEntity):
    """Restore-capable ReefDose sensor.

    This entity:
    - Restores its last state using HA's RestoreEntity
    - Optionally listens to a bus event (`dependency`) to update the restored value
    - Mirrors restored/updated values into the coordinator cache at `value_name`
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: RestoreSensorEntityDescription,
    ) -> None:
        super().__init__(
            device, cast(ReefDoseSensorEntityDescription, entity_description)
        )
        self._restore_description = entity_description

    async def async_added_to_hass(self) -> None:
        """Register event listener (if configured), restore state, then subscribe to updates."""
        dep = self._restore_description.dependency
        if dep:
            self.async_on_remove(
                self._device.hass.bus.async_listen(dep, self._handle_restore_event)
            )

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            # Prefer native_value (if present) so numbers restore as numbers.
            restored: StateType = cast(
                StateType, last_state.attributes.get("native_value", last_state.state)
            )
            self._attr_native_value = restored
            if self._restore_description.value_name:
                self._device.set_data(self._restore_description.value_name, restored)
        else:
            self._attr_native_value = None

        await super().async_added_to_hass()

    @callback
    def _handle_restore_event(self, event: Event) -> None:
        """Handle update events and persist the mirrored value into the cache."""
        new_val: StateType = cast(StateType, event.data.get("value"))
        vn = self._restore_description.value_name
        if vn is not None:
            self._device.set_data(vn, new_val)
        self._attr_native_value = new_val
        self.async_write_ha_state()


# REEFRUN
class ReefRunSensorEntity(ReefBeatSensorEntity):
    """Per-pump ReefRun sensor entity.

    Only specialization is per-pump device info identifiers.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefRunSensorEntityDescription,
    ) -> None:
        super().__init__(device, entity_description)
        self._pump: int = entity_description.pump

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return per-pump device info for ReefDose."""
        return cast(ReefRunCoordinator, self._device).pump_device_info(self._pump)


# REEFWAVE
class ReefWaveSensorEntity(ReefBeatSensorEntity):
    """Wave schedule sensor entity.

    Values are fetched from `device.get_current_value(...)` and translated
    for `type` and `direction` where needed.
    """

    _attr_has_entity_name = True

    def _get_value(self) -> StateType:
        desc = cast(ReefWaveSensorEntityDescription, self._description)
        val = cast(_WaveValueCoordinator, self._device).get_current_value(
            desc.value_basename, desc.value_name
        )

        if desc.value_name == "type" and val is not None:
            return translate(
                cast(str, val),
                self._device.hass.config.language,
                dictionary=WAVE_TYPES,
                src_lang="id",
            )

        if desc.value_name == "direction":
            if val is None:
                return "fw"
            return translate(
                cast(str, val),
                self._device.hass.config.language,
                dictionary=WAVE_DIRECTIONS,
                src_lang="id",
            )

        return cast(StateType, val)


# REEFCLOUD
class ReefBeatCloudSensorEntity(ReefBeatSensorEntity):
    """Cloud library sensor entity.

    These sensors read a name from a library entry and may include the aquarium
    name in both:
    - device name (DeviceInfo)
    - sensor native value (formatted as "{name}-{aquarium}")
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefBeatCloudSensorEntityDescription,
    ) -> None:
        super().__init__(device, entity_description)
        self._cloud_desc = entity_description

        aquarium_uid = device.get_data(
            self._cloud_desc.value_name.replace("].name", "].aquarium_uid"),
            True,
        )
        if aquarium_uid is not None:
            self._aquarium_name = device.get_data(
                "$.sources[?(@.name=='/aquarium')].data[?(@.uid=='"
                + str(aquarium_uid)
                + "')].name",
                True,
            )
        elif self._cloud_desc.key.startswith("supplement_"):
            self._aquarium_name = "Supplements"
        else:
            self._aquarium_name = None

    def _get_value(self) -> StateType:
        if self._aquarium_name is not None:
            self._attr_extra_state_attributes = self._device.get_data(
                self._cloud_desc.value_name.replace("].name", "]")
            )
            name = self._device.get_data(self._cloud_desc.value_name)
            return f"{name}-{self._aquarium_name}"
        return self._device.get_data(self._cloud_desc.value_name)

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return device info adjusted for aquarium/library grouping."""
        return cast(ReefBeatCloudCoordinator, self._device).aquarium_device_info(
            self._aquarium_name
        )
