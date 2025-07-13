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

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
 )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo

from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    DAILY_PROG_INTERNAL_NAME,
    MAT_AUTO_ADVANCE_INTERNAL_NAME,
    ATO_AUTO_FILL_INTERNAL_NAME,
    HW_MAT_MODEL,
    MAT_MODEL_INTERNAL_NAME,
    MAT_POSITION_INTERNAL_NAME,
    )

from .coordinator import ReefBeatCoordinator,ReefDoseCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatSelectEntityDescription(SelectEntityDescription):
    """Describes reefbeat Select entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    entity_registry_visible_default: bool = True
    value_name: ''
    options: []
    
MAT_SELECTS: tuple[ReefBeatSelectEntityDescription, ...] = (
    ReefBeatSelectEntityDescription(
        key="model",
        translation_key="model",
        value_name=MAT_MODEL_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:movie-roll",
        options=HW_MAT_MODEL,
        entity_registry_visible_default=False,
    ),
    ReefBeatSelectEntityDescription(
        key="position",
        translation_key="position",
        value_name=MAT_POSITION_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:set-left-right",
        options=['left','right'],
        entity_registry_visible_default=False,
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
    _LOGGER.debug("SELECTS")
    if type(device).__name__=='ReefMatCoordinator':
        entities += [ReefBeatSelectEntity(device, description)
                 for description in MAT_SELECTS
                 if description.exists_fn(device)]

    async_add_entities(entities, True)


class ReefBeatSelectEntity(CoordinatorEntity,SelectEntity):
    """Represent an ReefBeat select."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatSelectEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_options = entity_description.options
        self._value_name=entity_description.value_name
        self._attr_current_option = self._device.get_data(self._value_name)
        self._source = self.entity_description.value_name.split('\'')[1]

        
    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        self._device.set_data(self._value_name,option)
        self.async_write_ha_state()        
        await self._device.push_values(self._source)
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info
