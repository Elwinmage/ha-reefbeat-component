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
    data_name: ''

    
LED_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    # ReefBeatSwitchEntityDescription(
    #     key="daily_prog",
    #     translation_key="daily_prog",
    #     data_name= DAILY_PROG_INTERNAL_NAME,
    #     exists_fn=lambda _: True,
    #     icon="mdi:calendar-range",
    # ),
)

MAT_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="auto_advance",
        translation_key="auto_advance",
        data_name=MAT_AUTO_ADVANCE_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:auto-mode",
    ),
)

ATO_SWITCHES: tuple[ReefBeatSwitchEntityDescription, ...] = (
    ReefBeatSwitchEntityDescription(
        key="auto_fill",
        translation_key="auto_fill",
        data_name=ATO_AUTO_FILL_INTERNAL_NAME,
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
    if type(device).__name__=='ReefLedCoordinator' or type(device).__name__=='ReefVirtualLedCoordinator':
        entities += [ReefBeatSwitchEntity(device, description)
                 for description in LED_SWITCHES
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefMatCoordinator':
        entities += [ReefBeatSwitchEntity(device, description)
                 for description in MAT_SWITCHES
                 if description.exists_fn(device)]
    elif type(device).__name__=='ReefATOCoordinator':
        entities += [ReefBeatSwitchEntity(device, description)
                 for description in ATO_SWITCHES
                 if description.exists_fn(device)]

    async_add_entities(entities, True)


class ReefBeatSwitchEntity(CoordinatorEntity,SwitchEntity):
    """Represent an ReefBeat switch."""
    _attr_has_entity_name = True
    
    def __init__(
        self, device, entity_description: ReefBeatSwitchEntityDescription
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._state = False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = True
        self._state = self._device.get_data(self.entity_description.data_name)
        self.async_write_ha_state()

        
    async def async_update(self) -> None:
        """Update entity state."""
        self._attr_available = True
        self._state = self._device.get_data(self.entity_description.data_name)

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._state=True
        self._device.set_data(self.entity_description.data_name,True)
        self._device.push_values()
        await self._device.async_request_refresh()
        
        
    async def async_turn_off(self, **kwargs):
        self._state=False
        self._device.set_data(self.entity_description.data_name,False)
        self._device.push_values()
        await self._device.async_request_refresh()
        
    @property
    def is_on(self) -> bool:
        return self._state
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info


