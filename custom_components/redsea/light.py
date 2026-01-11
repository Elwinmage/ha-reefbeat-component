"""Light platform for Red Sea ReefBeat devices.

This module exposes ReefLED channels and a virtual "combined" ReefLED as
Home Assistant light entities.

Notes:
- The integration uses a DataUpdateCoordinator for device state, but light
  entities also listen to a couple of integration-local bus events to reflect
  immediate UI changes after writes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.components.light.const import ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    EVENT_KELVIN_LIGHT_UPDATED,
    EVENT_WB_LIGHT_UPDATED,
    LED_BLUE_INTERNAL_NAME,
    LED_CONVERSION_COEF,
    LED_MOON_INTERNAL_NAME,
    LED_WHITE_INTERNAL_NAME,
)
from .coordinator import (
    ReefLedCoordinator,
    ReefLedG2Coordinator,
    ReefVirtualLedCoordinator,
)

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Entity descriptions
# -----------------------------------------------------------------------------
@dataclass(kw_only=True, frozen=True)
class ReefLedLightEntityDescription(LightEntityDescription):
    """Description for a physical ReefLED entity."""

    exists_fn: Callable[[ReefLedCoordinator], bool] = lambda _: True
    value_name: str = ""


@dataclass(kw_only=True, frozen=True)
class ReefVirtualLedLightEntityDescription(LightEntityDescription):
    """Description for a virtual ReefLED entity."""

    exists_fn: Callable[[ReefVirtualLedCoordinator], bool] = lambda _: True
    value_name: str = ""


DescriptionT = ReefLedLightEntityDescription | ReefVirtualLedLightEntityDescription


# -----------------------------------------------------------------------------
# Entity description tables
# -----------------------------------------------------------------------------
COMMON_LIGHTS: Final[tuple[ReefLedLightEntityDescription, ...]] = (
    ReefLedLightEntityDescription(
        key="moon",
        translation_key="moon",
        value_name=LED_MOON_INTERNAL_NAME,
        icon="mdi:lightbulb-night-outline",
    ),
)

LIGHTS: Final[tuple[ReefLedLightEntityDescription, ...]] = (
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

G1_LIGHTS: Final[tuple[ReefLedLightEntityDescription, ...]] = (
    ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.local.manual_trick",
        icon="mdi:palette",
    ),
)

G2_LIGHTS: Final[tuple[ReefLedLightEntityDescription, ...]] = (
    ReefLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        value_name="$.sources[?(@.name=='/manual')].data",
        icon="mdi:palette",
    ),
)

VIRTUAL_LIGHTS: Final[tuple[ReefVirtualLedLightEntityDescription, ...]] = (
    ReefVirtualLedLightEntityDescription(
        key="kelvin_intensity",
        translation_key="kelvin_intensity",
        # "g1_path g2_path" (first for G1, second for G2) - handled by the virtual coordinator.
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


# -----------------------------------------------------------------------------
# Platform setup
# -----------------------------------------------------------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform from a config entry."""
    device = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[LightEntity] = []

    if isinstance(device, ReefLedG2Coordinator):
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

    elif isinstance(device, ReefLedCoordinator):
        # Physical LED (G1)
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

    elif isinstance(device, ReefVirtualLedCoordinator):
        entities += [
            ReefLedLightEntity(device, description)
            for description in VIRTUAL_LIGHTS
            if description.exists_fn(device)
        ]
        if device.only_g1:
            _LOGGER.info(
                "G1 protocol activated for %s. White and Blue lights can be set.",
                device.title,
            )
            entities += [
                ReefLedLightEntity(device, description)
                for description in LIGHTS
                if description.exists_fn(device)
            ]

    async_add_entities(entities, update_before_add=True)


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------
class ReefLedLightEntity(LightEntity):
    """Light entity for a ReefBeat LED channel.

    Reads state from the device coordinator and writes changes back via the
    coordinator API.
    """

    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, device: ReefLedCoordinator, description: DescriptionT) -> None:
        """Initialize the entity."""
        super().__init__()
        self._device = device
        self._description = description

        self._attr_unique_id = f"{device.serial}_{description.key}"
        self._attr_device_info = device.device_info

        self._attr_brightness = 0
        self._attr_is_on = False

        if self._description.key == "kelvin_intensity":
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_min_color_temp_kelvin = 9000 if device.is_g1 else 8000
            self._attr_max_color_temp_kelvin = 23000
            self._attr_color_temp_kelvin = 15000

    async def async_added_to_hass(self) -> None:
        """Register listeners and initialize state once added to Home Assistant."""
        # Coordinator listener => update entity when coordinator refreshes.
        self.async_on_remove(
            self._device.async_add_listener(self._handle_coordinator_update)
        )

        # Integration-local events => fast UI update after write operations.
        event = (
            EVENT_WB_LIGHT_UPDATED
            if self._description.key == "kelvin_intensity"
            else EVENT_KELVIN_LIGHT_UPDATED
        )
        self.hass.bus.async_listen(event, self._handle_event_update)

        self._update_from_device()

    @callback
    def _handle_event_update(self, event: Any | None = None) -> None:
        """Handle integration-local update events."""
        self._update_from_device()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator refresh updates."""
        self._update_from_device()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update entity state (called by HA polling when applicable)."""
        self._update_from_device()

    def _update_from_device(self) -> None:
        """Pull state from the coordinator and update HA attributes."""
        value_name = self._description.value_name
        raw_data = self._device.get_data(value_name, True)

        if raw_data is None:
            self._attr_available = False
            self._attr_brightness = 0
            self._attr_is_on = False
            return

        # Virtual LED: hide per-channel white/blue entities when mixed G1/G2.
        if (
            isinstance(self._device, ReefVirtualLedCoordinator)
            and self._description.key in ("white", "blue")
            and not self._device.only_g1
        ):
            self._attr_available = False
            self._attr_brightness = 0
            self._attr_is_on = False
            return

        self._attr_available = True

        if self._description.key == "kelvin_intensity":
            # expected: {"intensity": ..., "kelvin": ...}
            try:
                self._attr_brightness = int(
                    float(raw_data["intensity"]) / LED_CONVERSION_COEF
                )
                self._attr_color_temp_kelvin = int(raw_data["kelvin"])
            except Exception:
                _LOGGER.debug("Unexpected kelvin_intensity payload: %r", raw_data)
                self._attr_brightness = 0
        else:
            self._attr_brightness = int(float(raw_data) / LED_CONVERSION_COEF)

        self._attr_is_on = (self._attr_brightness or 0) > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        _LOGGER.debug("ReefLED async_turn_on kwargs=%s", kwargs)

        value_name = self._description.value_name

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = int(kwargs[ATTR_COLOR_TEMP_KELVIN])

            # Keep existing G2 rounding behavior.
            if not self._device.is_g1:
                current_kelvin = int(self._attr_color_temp_kelvin or 0)
                if kelvin > current_kelvin:
                    step = 200 if current_kelvin < 10000 else 500
                    kelvin = (kelvin // step) * step
                    kelvin = min(kelvin, 23000)
                elif kelvin < current_kelvin:
                    if current_kelvin > 10000:
                        if (kelvin // 500 * 500) < 10000:
                            kelvin = (kelvin // 200) * 200
                        else:
                            kelvin = (kelvin // 500) * 500
                    else:
                        kelvin = (kelvin // 200) * 200
                    kelvin = max(kelvin, 8000)

            self._attr_color_temp_kelvin = kelvin
            self._device.set_data(value_name + ".kelvin", self._attr_color_temp_kelvin)

        if ATTR_BRIGHTNESS in kwargs:
            ha_value = int(kwargs[ATTR_BRIGHTNESS])
        else:
            if self._description.key == "kelvin_intensity":
                ha_value = int(
                    self._device.get_data(value_name + ".intensity", True) or 0
                )
            else:
                ha_value = int(self._device.get_data(value_name, True) or 0)

        self._attr_brightness = ha_value
        self._attr_is_on = True

        if self._description.key == "kelvin_intensity":
            if ATTR_BRIGHTNESS in kwargs:
                self._device.set_data(
                    value_name + ".intensity",
                    round(ha_value * LED_CONVERSION_COEF),
                )
            self.hass.bus.fire(EVENT_KELVIN_LIGHT_UPDATED, {})
        else:
            self._device.set_data(value_name, round(ha_value * LED_CONVERSION_COEF))
            self.hass.bus.fire(EVENT_WB_LIGHT_UPDATED, {})

        self.async_write_ha_state()
        await self._device.push_values("/manual", "post")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        _LOGGER.debug("ReefLED async_turn_off")

        self._attr_brightness = 0
        self._attr_is_on = False

        value_name = self._description.value_name
        if self._description.key == "kelvin_intensity":
            self._device.set_data(value_name + ".intensity", 0)
            self.hass.bus.fire(EVENT_KELVIN_LIGHT_UPDATED, {})
        else:
            self._device.set_data(value_name, 0)
            self.hass.bus.fire(EVENT_WB_LIGHT_UPDATED, {})

        self._device.force_status_update()
        self.async_write_ha_state()
        await self._device.push_values("/manual", "post")
        await self._device.async_quick_request_refresh("/manual")
