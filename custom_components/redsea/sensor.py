"""Implements the sensor entity"""

import logging
import datetime

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import callback

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType

from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    UnitOfLength,
    UnitOfVolume,
    UnitOfTime,
    EntityCategory,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
)

from .const import (
    DOMAIN,
    LIGHTS_LIBRARY,
    WAVES_LIBRARY,
    SUPPLEMENTS_LIBRARY,
    LED_WHITE_INTERNAL_NAME,
    LED_BLUE_INTERNAL_NAME,
    WAVE_DIRECTIONS,
    WAVE_TYPES,
    WAVE_SCHEDULE_PATH,
)

from .coordinator import (
    ReefBeatCoordinator,
    ReefDoseCoordinator,
    ReefRunCoordinator,
    ReefLedCoordinator,
    ReefWaveCoordinator,
)

from .i18n import translate


_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True)
class ReefBeatSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefBeatCoordinator], StateType]


@dataclass(kw_only=True)
class ReefBeatCloudSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = ""


@dataclass(kw_only=True)
class ReefDoseSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""

    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: str = ""
    with_attr_name: str = None
    with_attr_value: str = None
    head: int = 0


@dataclass(kw_only=True)
class RestoreSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""

    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    head: int = 0
    value_name: str = None
    dependency: str = None


@dataclass(kw_only=True)
class ReefRunSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""

    exists_fn: Callable[[ReefRunCoordinator], bool] = lambda _: True
    value_name: str = ""
    pump: int = 0
    with_attr_name: str = None
    with_attr_value: str = None


@dataclass(kw_only=True)
class ReefWaveSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""

    exists_fn: Callable[[ReefWaveCoordinator], bool] = lambda _: True
    value_basename: str = WAVE_SCHEDULE_PATH
    value_name: str = ""


@dataclass(kw_only=True)
class ReefLedScheduleSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""

    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_name: str = ""
    id_name: int = 0
    with_attr_name: str = None
    with_attr_value: str = None


CLOUD_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
    ReefBeatSensorEntityDescription(
        key="cloud_account",
        translation_key="cloud_account",
        value_fn=lambda device: device.cloud_link(),
        icon="mdi:cloud-sync-outline",
    ),
)

USER_SENSORS: tuple[ReefBeatSensorEntityDescription, ...] = (
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

""" Reefbeat sensors list """
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

""" ReefMat sensors list """
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


LED_SCHEDULES = ()
""" Lights and cloud schedule as sensors """
for auto_id in range(1, 8):
    LED_SCHEDULES += (
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
                "$.sources[?(@.name=='/preset_name/" + str(auto_id) + "')].data.name",
                True,
            )
            is not None,
            id_name=auto_id,
            icon="mdi:calendar",
        ),
    )

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

""" ATO sensors list """
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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    """Configure reefbeat sensors from graphic user interface data"""
    device = hass.data[DOMAIN][entry.entry_id]
    entities = []
    _LOGGER.debug("SENSORS")
    # Display account cloud link
    if device.__class__.__bases__[0].__name__ == "ReefBeatCloudLinkedCoordinator":
        entities += [
            ReefBeatSensorEntity(device, description)
            for description in CLOUD_SENSORS
            if description.exists_fn(device)
        ]
    if (
        type(device).__name__ == "ReefLedG2Coordinator"
        or type(device).__name__ == "ReefVirtualLedCoordinator"
    ):
        entities += [
            ReefBeatSensorEntity(device, description)
            for description in G2_LED_SENSORS
            if description.exists_fn(device)
        ]
    if (
        type(device).__name__ == "ReefLedCoordinator"
        or type(device).__name__ == "ReefLedG2Coordinator"
    ):
        entities += [
            ReefBeatSensorEntity(device, description)
            for description in LED_SENSORS
            if description.exists_fn(device)
        ]
    elif type(device).__name__ == "ReefMatCoordinator":
        entities += [
            ReefBeatSensorEntity(device, description)
            for description in MAT_SENSORS
            if description.exists_fn(device)
        ]
    elif type(device).__name__ == "ReefWaveCoordinator":
        entities += [
            ReefWaveSensorEntity(device, description)
            for description in WAVE_SCHEDULE_SENSORS
            if description.exists_fn(device)
        ]
    elif type(device).__name__ == "ReefDoseCoordinator":
        ds = ()
        new_head = (
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
        ds += new_head
        entities += [
            ReefBeatSensorEntity(device, description)
            for description in ds
            if description.exists_fn(device)
        ]

        ds = ()
        for head in range(1, device.heads_nb + 1):
            new_head = (
                ReefDoseSensorEntityDescription(
                    key="state_head_" + str(head),
                    translation_key="head_state",
                    icon="mdi:cog-play",
                    value_name="$.sources[?(@.name=='/dashboard')].data.heads."
                    + str(head)
                    + ".state",
                    head=head,
                ),
            )
            ds += new_head
            new_head = (
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
            )
            ds += new_head
            new_head = (
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
            )
            ds += new_head
            new_head = (
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
            )
            ds += new_head
            new_head = (
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
            )
            ds += new_head
            new_head = (
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
            )
            ds += new_head
            new_head = (
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
            )
            ds += new_head
            new_head = (
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
            )
            ds += new_head
            new_head = (
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
            )
            ds += new_head
            new_head = (
                ReefDoseSensorEntityDescription(
                    key="container_volume_head_" + str(head),
                    translation_key="container_volume",
                    native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                    device_class=SensorDeviceClass.VOLUME,
                    state_class=SensorStateClass.TOTAL,
                    icon="mdi:hydraulic-oil-level",
                    suggested_display_precision=0,
                    value_name="$.sources[?(@.name=='/head/"
                    + str(head)
                    + "/settings')].data.container_volume",
                    head=head,
                ),
            )
            ds += new_head
            new_head = (
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
            )
            ds += new_head

        entities += [
            ReefDoseSensorEntity(device, description)
            for description in ds
            if description.exists_fn(device)
        ]

    elif type(device).__name__ == "ReefATOCoordinator":
        entities += [
            ReefBeatSensorEntity(device, description)
            for description in ATO_SENSORS
            if description.exists_fn(device)
        ]

    elif type(device).__name__ == "ReefRunCoordinator":
        ds = ()
        for pump in range(1, 3):
            new_pump = (
                ReefRunSensorEntityDescription(
                    key="name_pump_" + str(pump),
                    translation_key="name",
                    icon="mdi:pump",
                    value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                    + str(pump)
                    + ".name",
                    pump=pump,
                ),
            )
            ds += new_pump
            new_pump = (
                ReefRunSensorEntityDescription(
                    key="type_pump_" + str(pump),
                    translation_key="type",
                    icon="mdi:pump",
                    value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                    + str(pump)
                    + ".type",
                    pump=pump,
                ),
            )
            ds += new_pump
            new_pump = (
                ReefRunSensorEntityDescription(
                    key="model_pump_" + str(pump),
                    translation_key="model",
                    icon="mdi:pump",
                    value_name="$.sources[?(@.name=='/dashboard')].data.pump_"
                    + str(pump)
                    + ".model",
                    pump=pump,
                ),
            )
            ds += new_pump
            new_pump = (
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
            )
            ds += new_pump
            new_pump = (
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
            )
            ds += new_pump
        entities += [
            ReefRunSensorEntity(device, description)
            for description in ds
            if description.exists_fn(device)
        ]

    if (
        type(device).__name__ == "ReefLedCoordinator"
        or type(device).__name__ == "ReefVirtualLedCoordinator"
    ):
        entities += [
            ReefLedScheduleSensorEntity(device, description)
            for description in LED_SCHEDULES
            if description.exists_fn(device)
        ]

    if (
        type(device).__name__ != "ReefBeatCloudCoordinator"
        and type(device).__name__ != "ReefVirtualLedCoordinator"
    ):
        entities += [
            ReefBeatSensorEntity(device, description)
            for description in COMMON_SENSORS
            if description.exists_fn(device)
        ]

    if type(device).__name__ == "ReefBeatCloudCoordinator":
        # user
        entities += [
            ReefBeatCloudSensorEntity(device, description)
            for description in USER_SENSORS
            if description.exists_fn(device)
        ]
        # LED
        progs = device.my_api.get_data(
            "$.sources[?(@.name=='" + LIGHTS_LIBRARY + "')].data"
        )
        ds = []
        for prog in progs:
            new_prog = (
                ReefBeatCloudSensorEntityDescription(
                    key="prog_" + str(prog["uid"]),
                    translation_key="led_program",
                    icon="mdi:chart-bell-curve",
                    value_name="$.sources[?(@.name=='"
                    + LIGHTS_LIBRARY
                    + "')].data[?(@.uid=='"
                    + str(prog["uid"])
                    + "')].name",
                ),
            )
            ds += new_prog
        # WAVES
        waves = device.my_api.get_data(
            "$.sources[?(@.name=='" + WAVES_LIBRARY + "')].data"
        )
        for wave in waves:
            new_wave = (
                ReefBeatCloudSensorEntityDescription(
                    key="wave_" + str(wave["uid"]),
                    translation_key="wave_program",
                    icon="mdi:sine-wave",
                    value_name="$.sources[?(@.name=='"
                    + WAVES_LIBRARY
                    + "')].data[?(@.uid=='"
                    + str(wave["uid"])
                    + "')].name",
                ),
            )
            ds += new_wave
        # SUPPLEMENTS
        if not device.disable_supplement:
            supplements = device.my_api.get_data(
                "$.sources[?(@.name=='" + SUPPLEMENTS_LIBRARY + "')].data"
            )
            for supplement in supplements:
                new_supplement = (
                    ReefBeatCloudSensorEntityDescription(
                        key="supplement_" + str(supplement["uid"]),
                        translation_key="supplement_program",
                        icon="mdi:sine-supplement",
                        value_name="$.sources[?(@.name=='"
                        + SUPPLEMENTS_LIBRARY
                        + "')].data[?(@.uid=='"
                        + str(supplement["uid"])
                        + "')].name",
                    ),
                )
                ds += new_supplement
        entities += [
            ReefBeatCloudSensorEntity(device, description)
            for description in ds
            if description.exists_fn(device)
        ]

    async_add_entities(entities, True)


################################################################################
# BEAT
class ReefBeatSensorEntity(CoordinatorEntity, SensorEntity):
    """Represent an ReefBeat sensor."""

    _attr_has_entity_name = True

    def __init__(self, device, entity_description) -> None:
        """Set up the instance."""
        super().__init__(device, entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"

    def _update_val(self) -> str:
        self._attr_available = True
        if self.entity_description.key == "wifi_quality":
            signal_strength = self._device.get_data(
                "$.sources[?(@.name=='/wifi')].data.signal_dBm"
            )
            if signal_strength < -80:
                signal_val = "Poor"
                self.icon = "mdi:wifi-outline"
            elif signal_strength < -70:
                signal_val = "Low"
                self.icon = "mdi:wifi-strength-1"
            elif signal_strength < -60:
                signal_val = "Medium"
                self.icon = "mdi:wifi-strength-2"
            elif signal_strength < -50:
                signal_val = "Good"
                self.icon = "mdi:wifi-strength-3"
            else:
                signal_val = "Excellent"
            self._attr_native_value = signal_val
        else:
            self._attr_native_value = self._get_value()
            if (
                hasattr(self.entity_description, "with_attr_name")
                and self.entity_description.with_attr_name
            ):
                self._attr_extra_state_attributes = {
                    self.entity_description.with_attr_name: self._device.get_data(
                        self.entity_description.with_attr_value
                    )
                }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_val()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update entity state."""
        self._update_val()

    def _get_value(self):
        if self.entity_description.translation_key == "dosing_queue":
            data = self._device.get_data(self.entity_description.value_name)
            if len(data) > 0:
                return data[0]["head"]
            else:
                return translate("Empty", self._device._hass.config.language)
        elif hasattr(self.entity_description, "value_fn"):
            return self.entity_description.value_fn(self._device)
        elif hasattr(self.entity_description, "value_name"):
            return self._device.get_data(self.entity_description.value_name)
        else:
            _LOGGER.error(
                "redsea.binary_sensor.ReefBeatBinarySensorEntity._get_value: no method to get value"
            )

    @property
    def available(self) -> bool:
        return self._attr_native_value is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info


################################################################################
# LED SCHEDULE
class ReefLedScheduleSensorEntity(ReefBeatSensorEntity):
    """Represent an ReefBeat number."""

    _attr_has_entity_name = True

    def __init__(
        self, device, entity_description: ReefDoseSensorEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device, entity_description)

    async def async_update(self) -> None:
        self._attr_available = True
        # We don't need to check if device available here
        self._attr_native_value = self._device.get_data(
            self.entity_description.value_name
        )
        prog_data = self._device.get_data(
            "$.sources[?(@.name=='/auto/"
            + str(self.entity_description.id_name)
            + "')].data"
        )
        cloud_data = self._device.get_data(
            "$.sources[?(@.name=='/clouds/"
            + str(self.entity_description.id_name)
            + "')].data"
        )
        self._attr_extra_state_attributes = {"data": prog_data, "clouds": cloud_data}


################################################################################
# DOSE
class ReefDoseSensorEntity(ReefBeatSensorEntity):
    """Represent an ReefBeat number."""

    _attr_has_entity_name = True

    def __init__(
        self, device, entity_description: ReefDoseSensorEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device, entity_description)
        self._head = self.entity_description.head

    def _update_val(self) -> str:
        old_value = self._attr_native_value
        new_value = self._get_value()
        super()._update_val()
        if self.entity_description.translation_key == "container_volume":
            if (
                new_value is not None
                and old_value is not None
                and old_value < new_value
            ):
                self._device._hass.bus.fire(
                    self.entity_description.value_name, {"value": new_value}
                )
        # super()._update_val()
        # self._attr_native_value =  new_value

    def _get_value(self):
        if self.entity_description.translation_key == "last_calibration":
            return datetime.datetime.fromtimestamp(
                int(self._device.get_data(self.entity_description.value_name))
            ).date()
        else:
            return self._device.get_data(self.entity_description.value_name)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        di = self._device.device_info
        di["name"] += "_head_" + str(self._head)
        identifiers = list(di["identifiers"])[0]
        head = ("head_" + str(self._head),)
        identifiers += head
        di["identifiers"] = {identifiers}
        return di


################################################################################
# RUN
class ReefRunSensorEntity(ReefBeatSensorEntity):
    """Represent an ReefBeat sensor."""

    _attr_has_entity_name = True

    def __init__(
        self, device, entity_description: ReefRunSensorEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device, entity_description)
        self._pump = self.entity_description.pump

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        di = self._device.device_info
        di["name"] += "_pump_" + str(self._pump)
        identifiers = list(di["identifiers"])[0]
        pump = ("pump_" + str(self._pump),)
        identifiers += pump
        di["identifiers"] = {identifiers}
        return di


################################################################################
# WAVE
class ReefWaveSensorEntity(ReefBeatSensorEntity):
    """Represent an ReefBeat sensor."""

    _attr_has_entity_name = True

    def __init__(
        self, device, entity_description: ReefBeatSensorEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device, entity_description)

    def _get_value(self):
        val = self._device.get_current_value(
            self.entity_description.value_basename, self.entity_description.value_name
        )
        if self.entity_description.value_name == "type":
            val = translate(
                val,
                self._device._hass.config.language,
                dictionnary=WAVE_TYPES,
                src_lang="id",
            )
        elif self.entity_description.value_name == "direction":
            if val is None:
                val = "fw"
            else:
                val = translate(
                    val,
                    self._device._hass.config.language,
                    dictionnary=WAVE_DIRECTIONS,
                    src_lang="id",
                )
        return val


################################################################################
# CLOUD
class ReefBeatCloudSensorEntity(ReefBeatSensorEntity):
    """Represent an ReefBeat sensor."""

    _attr_has_entity_name = True

    def __init__(
        self, device, entity_description: ReefBeatCloudSensorEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device, entity_description)
        self._entity_description = entity_description
        aquarium_uid = device.get_data(
            self._entity_description.value_name.replace("].name", "].aquarium_uid"),
            True,
        )
        if aquarium_uid is not None:
            self._aquarium_name = device.get_data(
                "$.sources[?(@.name=='/aquarium')].data[?(@.uid=='"
                + aquarium_uid
                + "')].name",
                True,
            )
        elif self._entity_description.key.startswith("supplement_"):
            self._aquarium_name = "Supplements"
        else:
            self._aquarium_name = None
        self._library_name = ""

    def _get_value(self):
        if self._aquarium_name is not None:
            self._attr_extra_state_attributes = self._device.get_data(
                self._entity_description.value_name.replace("].name", "]")
            )
            return (
                self._device.get_data(self._entity_description.value_name)
                + "-"
                + self._aquarium_name
            )
        else:
            return self._device.get_data(self._entity_description.value_name)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        di = self._device.device_info
        if self._aquarium_name is not None:
            di["name"] = self._aquarium_name
            identifiers = list(di["identifiers"])[0]
            identifiers += (self._aquarium_name,)
            di["identifiers"] = {identifiers}
        return di
