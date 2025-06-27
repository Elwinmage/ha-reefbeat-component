""" Implements the light entity """
import logging

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.core import HomeAssistant

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.light import (
    LightEntity,
    LightEntityDescription,
    ColorMode,
    ATTR_BRIGHTNESS,
    )

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import  DeviceInfo
from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    CONFIG_FLOW_IP_ADDRESS,
    WHITE_INTERNAL_NAME,
    BLUE_INTERNAL_NAME,
    MOON_INTERNAL_NAME,
)

from .coordinator import ReefLedCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefLedLightEntityDescription(LightEntityDescription):
    """Describes reefled Light entity."""
    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_fn: Callable[[ReefLedCoordinator], StateType]

LIGHTS: tuple[ReefLedLightEntityDescription, ...] = (
    ReefLedLightEntityDescription(
        key="white",
        translation_key="white",
        value_fn=lambda device: device.get_data(WHITE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(WHITE_INTERNAL_NAME),
        icon="mdi:lightbulb-outline",
    ),
    ReefLedLightEntityDescription(
        key="blue",
        translation_key="blue",
        value_fn=lambda device: device.get_data(BLUE_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(BLUE_INTERNAL_NAME),
        icon="mdi:lightbulb",
    ),
    ReefLedLightEntityDescription(
        key="moon",
        translation_key="moon",
        value_fn=lambda device: device.get_data(MOON_INTERNAL_NAME),
        exists_fn=lambda device: device.data_exist(MOON_INTERNAL_NAME),
        icon="mdi:lightbulb-night-outline",
    ),
)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        discovery_info=None, 
):

    device = hass.data[DOMAIN][config_entry.entry_id]
    
    entities=[]
    entities += [ReefLedLightEntity(device, description)
                 for description in LIGHTS
                 if description.exists_fn(device)]
    async_add_entities(entities, True)


class ReefLedLightEntity(LightEntity):
    """Represent an ReefLed light."""
    _attr_has_entity_name = True
    _attr_supported_color_modes = [ColorMode.BRIGHTNESS]
    _attr_color_mode = ColorMode.BRIGHTNESS
    
    def __init__(
        self, device: ReefLedCoordinator, entity_description: ReefLedLightEntityDescription
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._brighness = 0
        self._state = "off"
        
        
    async def async_update(self) -> None:
        """Update entity state."""
        try:
            await self._device.update()
        except Exception as e:
            # _LOGGER.warning("Update failed for %s: %s", self.entity_id,e)
            # self._attr_available = False  # Set property value
            # return
            pass
        self._attr_available = True
        # We don't need to check if device available here
        self._brightness =  self.entity_description.value_fn(
            self._device
        )  # Update "native_value" property
        if self.brightness > 0:
            self._state='on'
        else:
            self._state='off'

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug("Reefled.light.async_turn_on %s"%kwargs)
        if ATTR_BRIGHTNESS in kwargs:
            ha_value = int(kwargs[ATTR_BRIGHTNESS])
            self._device.set_data(self.entity_description.key,ha_value)
            self._device.push_values()

    async def async_turn_off(self, **kwargs):
        self._brightness=0
        self._state="off"
        self._device.set_data(self.entity_description.key,0)
        self._device.push_values()

    @property
    def brightness(self) -> int:
        """Return the current brightness"""
        return self._brightness

    @property
    def is_on(self) -> bool:
        return self.brightness > 0
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

