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

from .coordinator import ReefBeatCoordinator,ReefDoseCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatButtonEntityDescription(ButtonEntityDescription):
    """Describes reefbeat Button entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    press_fn: Callable[[ReefBeatCoordinator], StateType]

@dataclass(kw_only=True)
class ReefDoseButtonEntityDescription(ButtonEntityDescription):
    """Describes reefbeat Button entity."""
    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    action: "manual"
    head: 0

    
MAT_BUTTONS: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key='advance',
        translation_key='advance',
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("advance"),
        icon="mdi:paper-roll-outline",
    ),
)

ATO_BUTTONS: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key='fill',
        translation_key='fill',
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("manual-pump"),
        icon="mdi:water-pump",
    ),
    ReefBeatButtonEntityDescription(
        key='stop_fill',
        translation_key='stop_fill',
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("stop"),
        icon="mdi:water-pump-off",
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
    if type(device).__name__=='ReefATOCoordinator':
        _LOGGER.debug(ATO_BUTTONS)
        entities += [ReefBeatButtonEntity(device, description)
                 for description in ATO_BUTTONS
                 if description.exists_fn(device)]
    if type(device).__name__=='ReefDoseCoordinator':
        db=()
        for head in range(1,device.heads_nb+1):
            new_head= (ReefDoseButtonEntityDescription(
                key="manual_head_"+str(head),
                translation_key="manual_head",
                exists_fn=lambda _: True,
                icon="mdi:cup-water",
                action="manual",
                head=head,
            ), )
            db+=new_head
        _LOGGER.debug(db)
        entities += [ReefDoseButtonEntity(device, description)
                 for description in db
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
        self.entity_description.press_fn(self._device)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info



class ReefDoseButtonEntity(ReefBeatButtonEntity):
    """Represent an ReefBeat button."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseButtonEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._head=self.entity_description.head

    async def async_press(self) -> None:
        """Handle the button press."""
        self._device.press(self.entity_description.action,self.entity_description.head)


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



