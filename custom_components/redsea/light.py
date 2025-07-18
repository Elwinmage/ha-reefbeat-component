""" Implements the light entity """
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
    LED_WHITE_INTERNAL_NAME,
    LED_BLUE_INTERNAL_NAME,
    LED_MOON_INTERNAL_NAME,
    LED_INTENSITY_INTERNAL_NAME,
    LED_CONVERSION_COEF,
)

from .coordinator import ReefLedCoordinator, ReefVirtualLedCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(kw_only=True)
class ReefLedLightEntityDescription(LightEntityDescription):
    """Describes reefled Light entity."""
    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_name: ''

@dataclass(kw_only=True)
class ReefVirtualLedLightEntityDescription(LightEntityDescription):
    """Describes reefled Light entity."""
    exists_fn: Callable[[ReefVirtualLedCoordinator], bool] = lambda _: True
    value_name: ''

COMMON_LIGHTS: tuple[ReefLedLightEntityDescription, ...] = (
    ReefLedLightEntityDescription(
        key="moon",
        translation_key="moon",
        value_name=LED_MOON_INTERNAL_NAME,
        icon="mdi:lightbulb-night-outline",
    ),
)

    
LIGHTS: tuple[ReefLedLightEntityDescription, ...] = (
    ReefLedLightEntityDescription(
        key="white",
        translation_key="white",
        value_name=LED_WHITE_INTERNAL_NAME,
        icon="mdi:lightbulb-outline",
    ),
    ReefLedLightEntityDescription(
        key="blue",
        translation_key="blue",
        value_name=LED_BLUE_INTERNAL_NAME,
        icon="mdi:lightbulb",
    ),
)

G2_LIGHTS: tuple[ReefLedLightEntityDescription, ...] = (
    ReefLedLightEntityDescription(
        key="intensity",
        translation_key="intensity",
        value_name="$.sources[?(@.name=='/manual')].data.intensity",
        icon="mdi:lightbulb-on-50",
    ),
)


VIRTUAL_LIGHTS: tuple[ReefVirtualLedLightEntityDescription, ...] = (
    # ReefVirtualLedLightEntityDescription(
    #     key="white",
    #     translation_key="white",
    #     value_name=LED_WHITE_INTERNAL_NAME,
    #     icon="mdi:lightbulb-outline",
    # ),
    # ReefVirtualLedLightEntityDescription(
    #     key="blue",
    #     translation_key="blue",
    #     value_name=LED_BLUE_INTERNAL_NAME,
    #     icon="mdi:lightbulb",
    # ),
    ReefLedLightEntityDescription(
        key="intensity",
        translation_key="intensity",
        value_name="$.sources[?(@.name=='/manual')].data.intensity",
        icon="mdi:lightbulb-on-50",
    ),
    ReefVirtualLedLightEntityDescription(
        key="moon",
        translation_key="moon",
        value_name=LED_MOON_INTERNAL_NAME,
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
    if type(device).__name__=='ReefLedCoordinator':
        entities += [ReefLedLightEntity(device, description)
                     for description in LIGHTS
                     if description.exists_fn(device)]
        entities += [ReefLedLightEntity(device, description)
                     for description in COMMON_LIGHTS
                     if description.exists_fn(device)]
        entities += [ReefLedLightEntity(device, description)
                     for description in G2_LIGHTS
                     if description.exists_fn(device)]
    elif type(device).__name__=='ReefLedG2Coordinator':
        entities += [ReefLedLightEntity(device, description)
                     for description in COMMON_LIGHTS
                     if description.exists_fn(device)]
        entities += [ReefLedLightEntity(device, description)
                     for description in G2_LIGHTS
                     if description.exists_fn(device)]
    elif type(device).__name__=='ReefVirtualLedCoordinator':
        entities += [ReefLedLightEntity(device, description)
                     for description in VIRTUAL_LIGHTS
                     if description.exists_fn(device)]
    async_add_entities(entities, True)

################################################################################
# LED
class ReefLedLightEntity(CoordinatorEntity,LightEntity):
    """Represent an ReefLed light."""
    _attr_has_entity_name = True
    _attr_supported_color_modes = [ColorMode.BRIGHTNESS]
    _attr_color_mode = ColorMode.BRIGHTNESS
    
    def __init__(
        self, device, entity_description
    ) -> None:
        """Set up the instance."""
        super().__init__(device,entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._brighness = 0
        self._old_brighness=0
        self._state = "off"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update()
        self.async_write_ha_state()
        
    async def async_update(self) -> None:
        """Update entity state."""
        self._update()
        
    def _update(self):
        self._attr_available = True
        raw_data=self._device.get_data(self.entity_description.value_name)
        if (raw_data != None):
            self._brightness =  self._device.get_data(self.entity_description.value_name)/LED_CONVERSION_COEF
        else:
            self._attr_available = False
            self._brightness = 0
        if self.brightness > 0:
            self._state='on'
            self._attr_is_on=True
        else:
            self._state='off'
            self._attr_is_on=False
            
    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug("Reefled.light.async_turn_on %s"%kwargs)
        if ATTR_BRIGHTNESS in kwargs:
            ha_value = int(kwargs[ATTR_BRIGHTNESS])
        else:
            ha_value = self._old_brighness
        self._state='on'
        self._attr_is_on=True
        self._brightness = ha_value
        self._device.set_data(self.entity_description.value_name,ha_value*LED_CONVERSION_COEF)
        self._device.force_status_update(True)
        self.async_write_ha_state()
        await self._device.push_values('/manual','post')
        await self._device.async_quick_request_refresh('/manual')
        #await self._device.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        self._old_brighness=self._brightness
        self._brightness=0
        self._attr_is_on=False
        self._state="off"
        self._device.set_data(self.entity_description.value_name,0)
        self._device.force_status_update()
        self.async_write_ha_state()
        await self._device.push_values('/manual','post')
        await self._device.async_quick_request_refresh('/manual')
        #await self._device.async_request_refresh()

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

