""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import (
    HomeAssistant,
    callback,
    )

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
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
    MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
)

from .coordinator import ReefBeatCoordinator,ReefDoseCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: ""

@dataclass(kw_only=True)
class ReefDoseNumberEntityDescription(NumberEntityDescription):
    """Describes reefbeat Number entity."""
    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    value_name: ""
    head: 0

    
MAT_NUMBERS: tuple[ReefBeatNumberEntityDescription, ...] = (
    ReefBeatNumberEntityDescription(
        key='custom_advance_value',
        translation_key='custom_advance_value',
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=NumberDeviceClass.DISTANCE,
        native_max_value=48,
        native_min_value=0.75,
        native_step=0.5,
        value_name=MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
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
    if type(device).__name__=='ReefMatCoordinator':
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
                native_max_value=300,
                value_name="$.local.head."+str(head)+".manual_dose",
                icon="mdi:cup-water",
                head=head,
            ), )
            dn+=new_head
            new_head= (ReefDoseNumberEntityDescription(
                key="daily_dose_head_"+str(head)+"_volume",
                translation_key="daily_dose",
                mode="box",
                native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                device_class=NumberDeviceClass.VOLUME,
                native_min_value=0,
                native_step=1,
                native_max_value=300,
                value_name="$.sources[?(@.name=='/head/"+str(head)+"/settings')].data.schedule.dd",
                icon="mdi:cup-water",
                head=head,
            ), )
            dn+=new_head
            
        entities += [ReefDoseNumberEntity(device, description)
                 for description in dn
                 if description.exists_fn(device)]
        
    async_add_entities(entities, True)


class ReefBeatNumberEntity(CoordinatorEntity,NumberEntity):
    """Represent an ReefBeat number."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatNumberEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_native_value=3.25

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = True
        self._attr_native_value=self._device.get_data(self.entity_description.value_name)
        self.async_write_ha_state()

        
    async def async_update(self) -> None:
        """Update entity state."""
        self._attr_available = True
        self._attr_native_value=self._device.get_data(self.entity_description.value_name)


    @callback
    def _async_update_attrs(self) -> None:
        """Update attrs from device."""
        _LOGGER.error("number.async_update_attrs")
        self._attr_native_value=self._device.get_data(self.entity_description.value_name)
        
    @property
    def native_value(self) -> float:
        return self._device.get_data(self.entity_description.value_name)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.debug("Reefbeat.number.set_native_value %f"%value)
        self._attr_native_value=value
        self._device.set_data(self.entity_description.value_name,value)
        self._device.push_values()
        await self._device.async_request_refresh()
      
       
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
        self._attr_native_value=0

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.debug("Reefbeat.number.set_native_value %f"%value)
        self._attr_native_value=value
        self._device.set_data(self.entity_description.value_name,value)
        self._device.push_values(self._head)
        await self._device.async_request_refresh()
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        di=self._device.device_info
        di['name']+='_head_'+str(self._head)
        identifiers=list(di['identifiers'])[0]
        head=("head_"+str(self._head),)
        identifiers+=head
        di['identifiers']={identifiers}
        return di
