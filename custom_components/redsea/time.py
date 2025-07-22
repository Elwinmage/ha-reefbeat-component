""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable
from datetime import time as dt_time

from homeassistant.core import (
    HomeAssistant,
    callback,
    )

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.time import (
    TimeEntity,
    TimeEntityDescription,
 )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo


from homeassistant.const import (
    EntityCategory,
)

from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    )

from .coordinator import ReefMatCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefMatTimeEntityDescription(TimeEntityDescription):
    """Describes reefbeat Time entity."""
    exists_fn: Callable[[ReefMatCoordinator], bool] = lambda _: True
    value_name: ''
    
MAT_TIMES: tuple[ReefMatTimeEntityDescription, ...] = (
    ReefMatTimeEntityDescription(
        key='schedule_time',
        translation_key='schedule_time',
        value_name="$.sources[?(@.name=='/configuration')].data.schedule_time",
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
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
    _LOGGER.debug("TIMES")
    if type(device).__name__=='ReefMatCoordinator':
        entities += [ReefMatTimeEntity(device, description)
                 for description in MAT_TIMES
                 if description.exists_fn(device)]
    async_add_entities(entities, True)

################################################################################
# MAT
class ReefMatTimeEntity(TimeEntity):
    """Represent an ReefMat time."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefMatTimeEntityDescription
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"

        time=self._device.get_data(self.entity_description.value_name)
        self._attr_native_value=dt_time(int(time/60),time%60)
        #self._attr_native_value=dt_time(0,0)

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("time.async_update")
        time=self._device.get_data(self.entity_description.value_name)
        self._attr_native_value=dt_time(int(time/60),time%60)
        self.async_write_ha_state()

    async def async_set_value(self, value: dt_time) -> None:
        """Update the current value."""
        _LOGGER.debug("time %s <- %s"%(self._attr_native_value,value))
        self._attr_native_value=value
        mat_value=value.hour*60+value.minute
        self._device.set_data(self.entity_description.value_name,mat_value)
        await self._device.push_values()
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

