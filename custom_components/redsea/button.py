
""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import (
    HomeAssistant,
    callback,
    )

from homeassistant.const import (
    EntityCategory,
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

from .coordinator import ReefBeatCoordinator,ReefDoseCoordinator,ReefRunCoordinator

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
    action: str = "manual"
    head: 0

@dataclass(kw_only=True)
class ReefRunButtonEntityDescription(ButtonEntityDescription):
    """Describes reefbeat Button entity."""
    exists_fn: Callable[[ReefRunCoordinator], bool] = lambda _: True
    pump: 0

    
FETCH_CONFIG_BUTTON: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key='fetch_config',
        translation_key='fetch_config',
        exists_fn=lambda _: True,
        press_fn=lambda device: device.fetch_config(),
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
    ),
)
    
    
MAT_BUTTONS: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key='advance',
        translation_key='advance',
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("advance"),
        icon="mdi:paper-roll-outline",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatButtonEntityDescription(
        key='new_roll',
        translation_key='new_roll',
        exists_fn=lambda _: True,
        press_fn=lambda device: device.new_roll(),
        icon="mdi:paper-roll-outline",
        entity_category=EntityCategory.CONFIG,
    ),
)

ATO_BUTTONS: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key='fill',
        translation_key='fill',
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("manual-pump"),
        icon="mdi:water-pump",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatButtonEntityDescription(
        key='stop_fill',
        translation_key='stop_fill',
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("stop"),
        icon="mdi:water-pump-off",
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
    _LOGGER.debug("BUTTONS")
    if type(device).__name__=='ReefMatCoordinator':
        entities += [ReefBeatButtonEntity(device, description)
                 for description in MAT_BUTTONS
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefATOCoordinator':
        entities += [ReefBeatButtonEntity(device, description)
                 for description in ATO_BUTTONS
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefRunCoordinator':
        if device.my_api._live_config_update == False:
            for pump in range(1,3):
                CONFIG_BUTTONS: tuple[ReefRunButtonEntityDescription, ...] =(
                    ReefRunButtonEntityDescription(
                        key="fetch_config_"+str(pump),
                        translation_key="fetch_config",
                        icon="mdi:update",
                        entity_category=EntityCategory.CONFIG,
                        pump=pump,
                    ),
                )
                entities += [ReefRunButtonEntity(device, description)
                             for description in CONFIG_BUTTONS
                             if description.exists_fn(device)]
    elif type(device).__name__=='ReefDoseCoordinator':
        db=()
        for head in range(1,device.heads_nb+1):
            new_head= (ReefDoseButtonEntityDescription(
                key="manual_head_"+str(head),
                translation_key="manual_head",
                icon="mdi:cup-water",
                action="manual",
                entity_category=EntityCategory.CONFIG,
                head=head,
            ),
            )
            db+=new_head
            if device.my_api._live_config_update == False:
                CONFIG_BUTTONS: tuple[ReefDoseButtonEntityDescription, ...] =(
                    ReefDoseButtonEntityDescription(
                        key="fetch_config_"+str(head),
                        translation_key="fetch_config",
                        icon="mdi:update",
                        action='fetch_config',
                        entity_category=EntityCategory.CONFIG,
                        head=head,
                    ),
                )
                entities += [ReefDoseButtonEntity(device, description)
                             for description in CONFIG_BUTTONS
                             if description.exists_fn(device)]

                
        entities += [ReefDoseButtonEntity(device, description)
                 for description in db
                 if description.exists_fn(device)]
    if device.my_api._live_config_update == False:
        entities += [ReefBeatButtonEntity(device, description)
                 for description in FETCH_CONFIG_BUTTON 
                 if description.exists_fn(device)]

    async_add_entities(entities, True)

################################################################################
# BEAT
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
        await self.entity_description.press_fn(self._device)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

################################################################################
# DOSE
class ReefDoseButtonEntity(ReefBeatButtonEntity):
    """Represent a ReefDose button."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefDoseButtonEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._head=self.entity_description.head

    async def async_press(self) -> None:
        """Handle the button press."""
        if self.entity_description.action == 'fetch_config':
            await self._device.fetch_config('/head/'+str(self.entity_description.head)+'/settings')
        else:
            await self._device.press(self.entity_description.action,self.entity_description.head)

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



################################################################################
# RUN
class ReefRunButtonEntity(ReefBeatButtonEntity):
    """Represent a ReefDose button."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefRunButtonEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._pump=self.entity_description.pump

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._device.fetch_config()

        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        di=self._device.device_info
        di['name']+='_pump_'+str(self._pump)
        identifiers=list(di['identifiers'])[0]
        pump=("pump_"+str(self._pump),)
        identifiers+=pump
        di['identifiers']={identifiers}
        return di



