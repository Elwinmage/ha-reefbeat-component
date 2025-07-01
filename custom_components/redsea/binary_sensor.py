""" Implements the binary sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import HomeAssistant

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
 )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    STATUS_INTERNAL_NAME,
    MAT_UNCLEAN_SENSOR_INTERNAL_NAME,
    MAT_AUTO_ADVANCE_INTERNAL_NAME,
    MAT_IS_EC_SENSOR_CONNECTED_INTERNAL_NAME,
    ATO_WATER_LEVEL_INTERNAL_NAME,
    ATO_IS_PUMP_ON_INTERNAL_NAME,
    ATO_LEAK_SENSOR_CONNECTED_INTERNAL_NAME,
    ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME,
    ATO_LEAK_SENSOR_BUZZER_ENABLED_INTERNAL_NAME,
    ATO_LEAK_SENSOR_STATUS_INTERNAL_NAME,
    ATO_ATO_SENSOR_IS_SENSOR_ERROR_INTERNAL_NAME,
    ATO_ATO_SENSOR_IS_TEMP_ENABLED_INTERNAL_NAME,
)

from .coordinator import ReefBeatCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes ReefLed binary sensor entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefBeatCoordinator], StateType]


""" ReefLed Binary Sensor List """    
SENSORS: tuple[ReefBeatBinarySensorEntityDescription, ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="status",
        translation_key="status",
        device_class=BinarySensorDeviceClass.LIGHT,
        value_fn=lambda device: device.get_data(STATUS_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(STATUS_INTERNAL_NAME),
        icon="mdi:wall-sconce-flat",
    ),
)

""" ReefMat Binary Sensor List """    
MAT_SENSORS: tuple[ReefBeatBinarySensorEntityDescription, ...] = (
    ReefBeatBinarySensorEntityDescription(
        key="unclean_sensor",
        translation_key="unclean_sensor",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.get_data(MAT_UNCLEAN_SENSOR_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MAT_UNCLEAN_SENSOR_INTERNAL_NAME),
        icon="mdi:liquid-spot",
    ),
    ReefBeatBinarySensorEntityDescription(
        key=MAT_IS_EC_SENSOR_CONNECTED_INTERNAL_NAME,
        translation_key=MAT_IS_EC_SENSOR_CONNECTED_INTERNAL_NAME,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.get_data(MAT_IS_EC_SENSOR_CONNECTED_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MAT_IS_EC_SENSOR_CONNECTED_INTERNAL_NAME),
        icon="mdi:connection",
    ),
)

ATO_SENSORS: tuple[ReefBeatBinarySensorEntityDescription, ...] = (
    ReefBeatBinarySensorEntityDescription(
        key=ATO_WATER_LEVEL_INTERNAL_NAME,
        translation_key=ATO_WATER_LEVEL_INTERNAL_NAME,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: not device.get_data(ATO_WATER_LEVEL_INTERNAL_NAME).startswith("desired"),
        exists_fn=lambda device: device.data_exist(ATO_WATER_LEVEL_INTERNAL_NAME),
        icon="mdi:water-alert",
    ),
    ReefBeatBinarySensorEntityDescription(
        key=ATO_LEAK_SENSOR_CONNECTED_INTERNAL_NAME,
        translation_key=ATO_LEAK_SENSOR_CONNECTED_INTERNAL_NAME,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.get_data(ATO_LEAK_SENSOR_CONNECTED_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_LEAK_SENSOR_CONNECTED_INTERNAL_NAME),
        icon="mdi:connection",
    ),
    ReefBeatBinarySensorEntityDescription(
        key=ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME,
        translation_key=ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME,
        value_fn=lambda device: device.get_data(ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME),
        icon="mdi:leak",
    ),
    ReefBeatBinarySensorEntityDescription(
        key=ATO_LEAK_SENSOR_BUZZER_ENABLED_INTERNAL_NAME,
        translation_key=ATO_LEAK_SENSOR_BUZZER_ENABLED_INTERNAL_NAME,
        value_fn=lambda device: device.get_data(ATO_LEAK_SENSOR_BUZZER_ENABLED_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_LEAK_SENSOR_BUZZER_ENABLED_INTERNAL_NAME),
        icon="mdi:volume-high",
    ),
    ReefBeatBinarySensorEntityDescription(
        key=ATO_LEAK_SENSOR_STATUS_INTERNAL_NAME,
        translation_key=ATO_LEAK_SENSOR_STATUS_INTERNAL_NAME,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.get_data(ATO_LEAK_SENSOR_STATUS_INTERNAL_NAME)!="dry",
        exists_fn=lambda device: device.data_exist(ATO_LEAK_SENSOR_STATUS_INTERNAL_NAME),
        icon="mdi:water-off",
    ),
    ReefBeatBinarySensorEntityDescription(
        key=ATO_ATO_SENSOR_IS_SENSOR_ERROR_INTERNAL_NAME,
        translation_key=ATO_ATO_SENSOR_IS_SENSOR_ERROR_INTERNAL_NAME,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda device: device.get_data(ATO_ATO_SENSOR_IS_SENSOR_ERROR_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_ATO_SENSOR_IS_SENSOR_ERROR_INTERNAL_NAME),
        icon="mdi:alert-circle-outline",
    ),
    ReefBeatBinarySensorEntityDescription(
        key=ATO_ATO_SENSOR_IS_TEMP_ENABLED_INTERNAL_NAME,
        translation_key=ATO_ATO_SENSOR_IS_TEMP_ENABLED_INTERNAL_NAME,
        value_fn=lambda device: device.get_data(ATO_ATO_SENSOR_IS_TEMP_ENABLED_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_ATO_SENSOR_IS_TEMP_ENABLED_INTERNAL_NAME),
        icon="mdi:thermometer-check",
    ),
    ReefBeatBinarySensorEntityDescription(
        key=ATO_IS_PUMP_ON_INTERNAL_NAME,
        translation_key=ATO_IS_PUMP_ON_INTERNAL_NAME,
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda device: device.get_data(ATO_IS_PUMP_ON_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(ATO_IS_PUMP_ON_INTERNAL_NAME),
        icon="mdi:pump",
    ),
)

async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        discovery_info=None,
):
    """ Configure binary entities from graphic user interface data """
    device = hass.data[DOMAIN][entry.entry_id]
    entities=[]
    if type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefLedVirtualCoordinator':
        entities += [ReefBeatBinarySensorEntity(device, description)
                     for description in SENSORS
                     if description.exists_fn(device)]
    if type(device).__name__=="ReefMatCoordinator":
        entities += [ReefBeatBinarySensorEntity(device, description)
                     for description in MAT_SENSORS
                     if description.exists_fn(device)]
    if type(device).__name__=="ReefATOCoordinator":
        entities += [ReefBeatBinarySensorEntity(device, description)
                     for description in ATO_SENSORS
                     if description.exists_fn(device)]
    
    async_add_entities(entities, True)


class ReefBeatBinarySensorEntity(BinarySensorEntity):
    """Represent an ReefLed binary sensor."""
    _attr_has_entity_name = True

    def __init__(
        self, device, entity_description
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._state=self.entity_description.value_fn(self._device)
        
    @property
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""
        self._state=self.entity_description.value_fn(self._device)
        return self._state

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

    

    
