""" Implements the sensor entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import HomeAssistant

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
    SwitchDeviceClass,
 )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo

from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    DAILY_PROG_INTERNAL_NAME,
    MAT_AUTO_ADVANCE_INTERNAL_NAME,
    ATO_AUTO_FILL_INTERNAL_NAME,
    )

from .coordinator import ReefBeatCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefBeatSwitchEntityDescription(SwitchEntityDescription):
    """Describes reefbeat Switch entity."""
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefBeatCoordinator], StateType]

    
LED_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="daily_prog",
        translation_key="daily_prog",
        value_fn=lambda device: device.get_data(DAILY_PROG_INTERNAL_NAME),
        exists_fn=lambda _: True,
        icon="mdi:calendar-range",
    ),
)

MAT_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="auto_advance",
        translation_key="auto_advance",
        value_fn=lambda device: device.get_data(MAT_AUTO_ADVANCE_INTERNAL_NAME),
        exists_fn=lambda _: True,
        icon="mdi:auto-mode",
    ),
)


ATO_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="auto_fill",
        translation_key="auto_fill",
        value_fn=lambda device: device.get_data(ATO_AUTO_FILL_INTERNAL_NAME),
        exists_fn=lambda _: True,
        icon="mdi:water-arrow-up",
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
    _LOGGER.debug("SWITCHES")
    _LOGGER.debug(type(device).__name__)
    if type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefLedVirtualCoordinator':
        _LOGGER.debug(LED_SWITCHES)
        entities += [ReefBeatSwitchEntity(device, description)
                 for description in LED_SWITCHES
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefMatCoordinator':
        _LOGGER.debug(MAT_SWITCHES)
        entities += [ReefBeatSwitchEntity(device, description)
                 for description in MAT_SWITCHES
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefATOCoordinator':
        _LOGGER.debug(ATO_SWITCHES)
        entities += [ReefBeatSwitchEntity(device, description)
                 for description in ATO_SWITCHES
                 if description.exists_fn(device)]

    async_add_entities(entities, True)


class ReefBeatSwitchEntity(SwitchEntity):
    """Represent an ReefBeat switch."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatSwitchEntityDescription
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._state = False
        
    async def async_update(self) -> None:
        """Update entity state."""
        self._attr_available = True
        self._state = self.entity_description.value_fn(
            self._device
        )

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Reefbeat.switch.async_turn_on %s"%kwargs)
        self._state=True
        #self._device.data[self.entity_description.key]=True
        self._device.set_data(self.entity_description.key,True)
        self._device.push_values()

    def async_turn_off(self, **kwargs):
        _LOGGER.debug("Reefbeat.switch.async_turn_off %s (%s)"%(kwargs,self.entity_description))
        self._state=False
        #self._device.data[self.entity_description.key]=False
        self._device.set_data(self.entity_description.key,False)
        self._device.push_values()
        
    @property
    def is_on(self) -> bool:
        return self._state
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info


