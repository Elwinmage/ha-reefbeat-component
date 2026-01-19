"""Implements the light entity"""

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
    ATTR_COLOR_TEMP_KELVIN,
)


from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    LED_WHITE_INTERNAL_NAME,
    LED_BLUE_INTERNAL_NAME,
    LED_MOON_INTERNAL_NAME,
    LED_CONVERSION_COEF,
    EVENT_KELVIN_LIGHT_UPDATED,
    EVENT_WB_LIGHT_UPDATED,
)

from .coordinator import ReefLedCoordinator, ReefVirtualLedCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True)
class ReefLedLightEntityDescription(LightEntityDescription):
    """Describes reefled Light entity."""

    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_name: str = ""


@dataclass(kw_only=True)
class ReefVirtualLedLightEntityDescription(LightEntityDescription):
    """Describes reefled Light entity."""

    exists_fn: Callable[[ReefVirtualLedCoordinator], bool] = lambda _: True
    value_name: str = ""


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

G1_LIGHTS: tuple[ReefLedLightEntityDescription, ...] = (
    ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.local.manual_trick",
        icon="mdi:palette",
    ),
)


G2_LIGHTS: tuple[ReefLedLightEntityDescription, ...] = (
    ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
        icon="mdi:palette",
    ),
)


VIRTUAL_LIGHTS: tuple[ReefVirtualLedLightEntityDescription, ...] = (
    ReefVirtualLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        # value_name="$.sources[?(@.name=='/manual')].data",
        # specific two values first for G1 second for G2
        value_name="$.local.manual_trick $.sources[?(@.name=='/manual')].data",
        icon="mdi:palette",
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
    entities = []
    if type(device).__name__ == "ReefLedCoordinator":
        entities += [
            ReefLedLightEntity(device, description)
            for description in LIGHTS
            if description.exists_fn(device)
        ]
        entities += [
            ReefLedLightEntity(device, description)
            for description in G1_LIGHTS
            if description.exists_fn(device)
        ]
        entities += [
            ReefLedLightEntity(device, description)
            for description in COMMON_LIGHTS
            if description.exists_fn(device)
        ]
    elif type(device).__name__ == "ReefLedG2Coordinator":
        entities += [
            ReefLedLightEntity(device, description)
            for description in COMMON_LIGHTS
            if description.exists_fn(device)
        ]
        entities += [
            ReefLedLightEntity(device, description)
            for description in G2_LIGHTS
            if description.exists_fn(device)
        ]
    elif type(device).__name__ == "ReefVirtualLedCoordinator":
        entities += [
            ReefLedLightEntity(device, description)
            for description in VIRTUAL_LIGHTS
            if description.exists_fn(device)
        ]
        if device._only_g1:
            _LOGGER.info(
                "G1 protocol activated for %s. White and Blue lights can be set."
                % device._title
            )
            entities += [
                ReefLedLightEntity(device, description)
                for description in LIGHTS
                if description.exists_fn(device)
            ]

    async_add_entities(entities, True)


################################################################################
# LED
class ReefLedLightEntity(CoordinatorEntity, LightEntity):
    """Represent an ReefLed light."""

    _attr_has_entity_name = True
    _attr_supported_color_modes = [ColorMode.BRIGHTNESS]
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, device, entity_description) -> None:
        """Set up the instance."""
        super().__init__(device, entity_description)
        self._device = device
        self.entity_description = entity_description
        self._attr_available = False
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._brighness = 0
        # self._turned_on_avoid_echo=False
        #        self._old_brighness=0
        self._state = "off"
        if self.entity_description.key == "kelvin_intensity":
            self._attr_supported_color_modes = [ColorMode.COLOR_TEMP]
            self._attr_color_mode = ColorMode.COLOR_TEMP
            if self._device.my_api._g1:
                self._attr_min_color_temp_kelvin = 9000
            else:
                self._attr_min_color_temp_kelvin = 8000
            self._attr_max_color_temp_kelvin = 23000
            self._attr_color_temp_kelvin = 15000
            self._device._hass.bus.async_listen(
                EVENT_WB_LIGHT_UPDATED, self._handle_coordinator_update
            )
        else:
            self._device._hass.bus.async_listen(
                EVENT_KELVIN_LIGHT_UPDATED, self._handle_coordinator_update
            )

    @callback
    def _handle_coordinator_update(self, event=None) -> None:
        """Handle updated data from the coordinator."""
        self._update()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update entity state."""
        self._update()

    def _update(self):
        self._attr_available = True
        # if (self._turned_on_avoid_echo):
        #     _LOGGER.debug("AVOID Echo")
        #     self._turned_on_avoid_echo=False
        #     return
        raw_data = self._device.get_data(self.entity_description.value_name)
        if raw_data is not None:
            if self.entity_description.key == "kelvin_intensity":
                self._brightness = raw_data["intensity"] / LED_CONVERSION_COEF
                self._attr_color_temp_kelvin = raw_data["kelvin"]
            else:
                self._brightness = (
                    self._device.get_data(self.entity_description.value_name)
                    / LED_CONVERSION_COEF
                )
        else:
            self._attr_available = False
            self._brightness = 0

        if self._brightness > 0:
            self._state = "on"
            self._attr_is_on = True
        else:
            self._state = "off"
            self._attr_is_on = False

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug("Reefled.light.async_turn_on %s" % kwargs)
        # self._turned_on_avoid_echo=True
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = int(kwargs[ATTR_COLOR_TEMP_KELVIN])
            if not self._device.my_api._g1:
                if kelvin > self._attr_color_temp_kelvin:
                    if self._attr_color_temp_kelvin < 10000:
                        kelvin = kelvin // 200 * 200
                    else:
                        kelvin = kelvin // 500 * 500
                    if kelvin > 23000:
                        kelvin = 23000
                elif kelvin < self._attr_color_temp_kelvin:
                    if self._attr_color_temp_kelvin > 10000:
                        if (kelvin // 500 * 500) < 10000:
                            kelvin = kelvin // 200 * 200
                        else:
                            kelvin = kelvin // 500 * 500
                    else:
                        kelvin = kelvin // 200 * 200
                    if kelvin < 8000:
                        kelvin = 8000
            self._attr_color_temp_kelvin = kelvin
            self._device.set_data(
                self.entity_description.value_name + ".kelvin",
                self._attr_color_temp_kelvin,
            )
        if ATTR_BRIGHTNESS in kwargs:
            ha_value = int(kwargs[ATTR_BRIGHTNESS])
            self._brightness = ha_value
            #            self._old_brighness=ha_value
        else:
            if self.entity_description.key == "kelvin_intensity":
                ha_value = self._device.get_data(
                    self.entity_description.value_name + ".intensity"
                )
            else:
                ha_value = self._device.get_data(self.entity_description.value_name)
        self._state = "on"
        self._attr_is_on = True
        #        self._brightness = ha_value
        if self.entity_description.key == "kelvin_intensity":
            if ATTR_BRIGHTNESS in kwargs:
                # ha_value = int(kwargs[ATTR_BRIGHTNESS])
                self._device.set_data(
                    self.entity_description.value_name + ".intensity",
                    round(ha_value * LED_CONVERSION_COEF),
                )
            self._device._hass.bus.fire(EVENT_KELVIN_LIGHT_UPDATED, {})

        else:
            self._device.set_data(
                self.entity_description.value_name,
                round(ha_value * LED_CONVERSION_COEF),
            )
            self._device._hass.bus.fire(EVENT_WB_LIGHT_UPDATED, {})
        self.async_write_ha_state()
        await self._device.push_values("/manual", "post")

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("redsea.light.async_turn_off")
        self._brightness = 0
        self._attr_is_on = False
        self._state = "off"
        if self.entity_description.key == "kelvin_intensity":
            self._device.set_data(self.entity_description.value_name + ".intensity", 0)
            self._device._hass.bus.fire(EVENT_KELVIN_LIGHT_UPDATED, {})
        else:
            self._device.set_data(self.entity_description.value_name, 0)
            self._device._hass.bus.fire(EVENT_WB_LIGHT_UPDATED, {})
        self._device.force_status_update()
        self.async_write_ha_state()
        await self._device.push_values("/manual", "post")
        await self._device.async_request_refresh(source="/manual")

    @property
    def available(self) -> bool:
        if type(self._device).__name__ == "ReefVirtualLedCoordinator" and (
            self.entity_description.key == "white"
            or self.entity_description.key == "blue"
        ):
            return self._device._only_g1
        else:
            return True

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
