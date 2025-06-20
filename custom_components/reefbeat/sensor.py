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
    EntityCategory,
)

from .const import (
    DOMAIN,
    FAN_INTERNAL_NAME,
    TEMPERATURE_INTERNAL_NAME,
    IP_INTERNAL_NAME,
)

from .coordinator import ReefLedCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefLedSensorEntityDescription(SensorEntityDescription):
    """Describes reefled sensor entity."""
    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefLedCoordinator], StateType]

""" Reeled sensors list """
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
    """Configure reefled sensors from graphic user interface data"""
    device = hass.data[DOMAIN][entry.entry_id]
    entities=[]
    if type(device).__name__=='ReefLedCoordinator':
        entities += [ReefLedSensorEntity(device, description)
                     for description in SENSORS
                     if description.exists_fn(device)]
    entities += [ReefLedSensorEntity(device, description)
                 for description in SCHEDULES
                 if description.exists_fn(device)]
    async_add_entities(entities, True)


class ReefLedSensorEntity(SensorEntity):
    """Represent an ReefLed sensor."""
    _attr_has_entity_name = True

    def __init__(
        self, device: ReefLedCoordinator, entity_description: ReefLedSensorEntityDescription
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
        self._attr_extra_state_attributes=self._device.get_prog_data(self.entity_description.key)
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

