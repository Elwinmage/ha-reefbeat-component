""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import (
    HomeAssistant,
    callback,
    )


from homeassistant.config_entries import ConfigEntry

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
 )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo

from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    )

from .coordinator import ReefBeatCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatButtonEntityDescription(ButtonEntityDescription):
    """Describes reefbeat Button entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True

    
MAT_BUTTONS: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key='advance',
        translation_key='advance',
        exists_fn=lambda _: True,
        icon="mdi:paper-roll-outline",
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
    _LOGGER.debug("BUTTONS")
    _LOGGER.debug(type(device).__name__)
    if type(device).__name__=='ReefMatCoordinator':
        _LOGGER.debug(MAT_BUTTONS)
        entities += [ReefBeatButtonEntity(device, description)
                 for description in MAT_BUTTONS
                 if description.exists_fn(device)]

    async_add_entities(entities, True)


class ReefBeatButtonEntity(ButtonEntity):
    """Represent an ReefBeat button."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatButtonEntityDescription
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"


    async def async_press(self) -> None:
        """Handle the button press."""
        self._device.advance()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info


