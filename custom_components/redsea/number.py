""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import (
    HomeAssistant,
    callback,
    )


from homeassistant.config_entries import ConfigEntry

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
 )

from homeassistant.const import (
    UnitOfLength,
    UnitOfVolume,
)


from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo

from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    MAT_NUMBERS_INTERNAL_NAME,
    MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
    DOSE_MANUAL_HEAD_1_VOLUME_INTERNAL_NAME,    
)

from .coordinator import ReefBeatCoordinator,ReefDoseCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefBeatCoordinator], StateType]

@dataclass(kw_only=True)
class ReefDoseNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefDoseCoordinator], StateType]
    head: 0

    
MAT_NUMBERS: tuple[ReefBeatNumberEntityDescription, ...] = (
    ReefBeatNumberEntityDescription(
        key=MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
        translation_key=MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=NumberDeviceClass.DISTANCE,
        native_max_value=48,
        native_min_value=0.75,
        native_step=0.5,
        value_fn=lambda device:  device.get_data(MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME),
        icon="mdi:arrow-expand-right",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,  
):
    """Configuration de la plate-forme tuto_hacs à partir de la configuration graphique"""
    device = hass.data[DOMAIN][config_entry.entry_id]
    
    entities=[]
    _LOGGER.debug("NUMBERS")
    _LOGGER.debug(type(device).__name__)
    if type(device).__name__=='ReefMatCoordinator':
        _LOGGER.debug(MAT_NUMBERS)
        entities += [ReefBeatNumberEntity(device, description)
                 for description in MAT_NUMBERS
                 if description.exists_fn(device)]

    if type(device).__name__=='ReefDoseCoordinator':
        dn=()
        for head in range(1,device.heads_nb+1):
            new_head= (ReefDoseNumberEntityDescription(
                key="manual_head_"+str(head)+"_volume",
                translation_key="manual_head_volume",
                mode="box",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=NumberDeviceClass.VOLUME,
                native_min_value=0,
                native_step=1,
                value_fn=lambda _: 0,
                exists_fn=lambda  _: True,
                icon="mdi:cup-water",
                head=head,
            ), )
            dn+=new_head
        _LOGGER.debug(dn)
        entities += [ReefDoseNumberEntity(device, description)
                 for description in dn
                 if description.exists_fn(device)]
        
    async_add_entities(entities, True)


class ReefBeatNumberEntity(NumberEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatNumberEntityDescription
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_native_value=3.25
        
    async def async_update(self) -> None:
        """Update entity state."""
        self._attr_available = True
        _LOGGER.debug("Reefbeat.number.async_update %s: %s"%(self.entity_description.key,self._device.get_data(self.entity_description.key)))
        self._attr_native_value=self._device.get_data(self.entity_description.key)


    @callback
    def _async_update_attrs(self) -> None:
        """Update attrs from device."""
        #if (value := self.entity_description.value_fn(self._device)) is not None:
        #    self._attr_native_value = float(value)
        _LOGGER.debug("Reefbeat.number._async_update_attrs")
        self._attr_native_value = float(self._device.get_data(self.entity_description.key))
        _LOGGER.debug("Reefbeat.number._async_update_attrs %s %f"%(self.entity_description.key,self._device.get_data(self.entity_description.key)))
        
    @property
    def native_value(self) -> float:
        _LOGGER.debug("Reefbeat.number.native_value %s: %s"%(self.entity_description.key,self._device.get_data(self.entity_description.key)))
        return self._device.get_data(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.debug("Reefbeat.number.set_native_value %f"%value)
        self._attr_native_value=value
        self._device.set_data(self.entity_description.key,value)
        self._device.push_values()
       
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info


class ReefDoseNumberEntity(ReefBeatNumberEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseNumberEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._head=self.entity_description.head
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        di=self._device.device_info
        di['name']+='_head_'+str(self._head)
        identifiers=list(di['identifiers'])[0]
        head=("head_"+str(self._head),)
        identifiers+=head
        di['identifiers']={identifiers}
        _LOGGER.info(di)
        return di
