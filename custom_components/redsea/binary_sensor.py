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

    

    
