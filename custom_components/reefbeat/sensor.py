""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType

from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    UnitOfLength,
    UnitOfTime,
    EntityCategory,
)

from .const import (
    DOMAIN,
    FAN_INTERNAL_NAME,
    TEMPERATURE_INTERNAL_NAME,
    IP_INTERNAL_NAME,
    MAT_TODAY_USAGE_INTERNAL_NAME,
    MAT_DAILY_AVERAGE_USAGE_INTERNAL_NAME,
    MAT_TOTAL_USAGE_INTERNAL_NAME,
    MAT_REMAINING_LENGTH_INTERNAL_NAME,
    MAT_DAYS_TILL_END_OF_ROLL_INTERNAL_NAME,
)

from .coordinator import ReefLedCoordinator,ReefMatCoordinator,ReefDoseCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefLedSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""
    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefLedCoordinator], StateType]

@dataclass(kw_only=True)
class ReefMatSensorEntityDescription(SensorEntityDescription):
    """Describes reefbeat sensor entity."""
    exists_fn: Callable[[ReefMatCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefMatCoordinator], StateType]


    
""" Reefbeat sensors list """
SENSORS: tuple[ReefLedSensorEntityDescription, ...] = (
    ReefLedSensorEntityDescription(
        key="fan",
        translation_key="fan",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(FAN_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(FAN_INTERNAL_NAME),
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:fan",
    ),
    ReefLedSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(TEMPERATURE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(TEMPERATURE_INTERNAL_NAME),
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer",
    ),
    ReefLedSensorEntityDescription(
        key="ip",
        translation_key="ip",
        value_fn=lambda device:  device.get_data(IP_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(IP_INTERNAL_NAME),
        icon="mdi:check-network-outline",
    ),
)

""" ReefMat sensors list """
MAT_SENSORS: tuple[ReefMatSensorEntityDescription, ...] = (

    ReefMatSensorEntityDescription(
        key="days_till_end_of_roll",
        translation_key="days_till_end_of_roll",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda device:  device.get_data(MAT_DAYS_TILL_END_OF_ROLL_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MAT_DAYS_TILL_END_OF_ROLL_INTERNAL_NAME),
        icon="mdi:sun-clock-outline",
        suggested_display_precision=0,
    ),
    ReefMatSensorEntityDescription(
        key="today_usage",
        translation_key="today_usage",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(MAT_TODAY_USAGE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MAT_TODAY_USAGE_INTERNAL_NAME),
        icon="mdi:tape-measure",
        suggested_display_precision=2,
    ),
    ReefMatSensorEntityDescription(
        key="daily_average_usage",
        translation_key="daily_average_usage",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(MAT_DAILY_AVERAGE_USAGE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MAT_DAILY_AVERAGE_USAGE_INTERNAL_NAME),
        icon="mdi:tape-measure",
        suggested_display_precision=1,
    ),
    ReefMatSensorEntityDescription(
        key="total_usage",
        translation_key="total_usage",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(MAT_TOTAL_USAGE_INTERNAL_NAME)/100,
        exists_fn=lambda device: device.data_exist(MAT_TOTAL_USAGE_INTERNAL_NAME),
        icon="mdi:paper-roll",
        suggested_display_precision=2,
    ),
    ReefMatSensorEntityDescription(
        key="remaining_length",
        translation_key="remaining_length",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device:  device.get_data(MAT_REMAINING_LENGTH_INTERNAL_NAME)/100,
        exists_fn=lambda device: device.data_exist(MAT_REMAINING_LENGTH_INTERNAL_NAME),
        icon="mdi:paper-roll-outline",
        suggested_display_precision=2,
    ),
)


SCHEDULES = ()
""" Lights and cloud schedule as sensors """
for auto_id in range(1,8):
    SCHEDULES += (ReefLedSensorEntityDescription(
        key="auto_"+str(auto_id),
        translation_key="auto_"+str(auto_id),
        value_fn=lambda device: device.get_prog_name("auto_"+str(auto_id)),
        exists_fn=lambda device: device.data_exist("auto_"+str(auto_id)),
        icon="mdi:calendar",
    ),)

async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        discovery_info=None,
):
    """Configure reefbeat sensors from graphic user interface data"""
    device = hass.data[DOMAIN][entry.entry_id]
    entities=[]
    _LOGGER.debug("SENSORS")
    _LOGGER.debug(type(device).__name__)
    if type(device).__name__=='ReefLedCoordinator':
        entities += [ReefBeatSensorEntity(device, description)
                     for description in SENSORS
                     if description.exists_fn(device)]
    elif type(device).__name__=='ReefMatCoordinator':
        _LOGGER.debug(MAT_SENSORS)
        entities += [ReefBeatSensorEntity(device, description)
                     for description in MAT_SENSORS
                     if description.exists_fn(device)]

    if type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefLedVirtualCoordinator':
        entities += [ReefBeatSensorEntity(device, description)
                     for description in SCHEDULES
                     if description.exists_fn(device)]
    async_add_entities(entities, True)


class ReefBeatSensorEntity(SensorEntity):
    """Represent an ReefBeat sensor."""
    _attr_has_entity_name = True

    def __init__(
        self, device, entity_description
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False  
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        
    async def async_update(self) -> None:
        """Update entity state."""
        try:
            await self._device.update()
        except Exception as e:
           # _LOGGER.warning("Update failed for %s: %s", self.entity_id,e)
           # self._attr_available = False  # Set property value
           # return
            pass
        self._attr_available = True
        # We don't need to check if device available here
        self._attr_native_value =  self.entity_description.value_fn(
            self._device
        )  # Update "native_value" property
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

