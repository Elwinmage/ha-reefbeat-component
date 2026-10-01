"""Entities of the ReefLED weather program (see led_weather.py).

Each setting of the weather program is an entity of the lamp, so it can be
set from the card, a dashboard or an automation:

- switch  weather_sync           weather mode (GPS weather) or standard
                                 programs
- switch  weather_clouds         set the lamp's clouds from the cloud cover
- select  weather_period         next_week (forecast) / last_week (measured)
- select  weather_anchor         place / sunrise / sunset / both
- text    weather_location       "lat, lon" or a map link (empty: HA home)
- number  weather_min_intensity  guard rails of the intensity, %
- number  weather_max_intensity
- number  weather_refresh_days   days between two weather fetches (3-15)
- time    weather_sunrise        tank times of an anchored day
- time    weather_sunset
- sensor  weather_program        result of the last generation

They read and write the lamp's WeatherStore, not the lamp itself. The lamps
of a group share their group's store: set on one lamp, it is set for all.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import time as dt_time
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.text import TextEntity
from homeassistant.components.time import TimeEntity
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import SIGNAL_GROUP_MEMBER_GONE, SIGNAL_GROUP_MEMBER_READY
from .led_weather import (
    ANCHORS,
    PERIODS,
    REFRESH_DAYS_MAX,
    REFRESH_DAYS_MIN,
    WeatherStore,
    parse_hhmm,
    set_weather_mode,
)

# Name of the store attribute on a lamp's coordinator
STORE_ATTR = "weather"


class WeatherSettingEntity(Entity):
    """An entity showing one setting (or the result) of the WeatherStore."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, device: Any, key: str, setting: str | None = None) -> None:
        self._device = device
        self._key = key
        self._setting = setting
        self._attr_translation_key = key
        self._attr_unique_id = f"{device.serial}_{key}"
        self._attr_device_info = device.device_info
        # Stable role for the card and blueprints (see ReefRoleMixin)
        self._attr_extra_state_attributes = {"reef_role": key}
        self._unsub: Callable[[], None] | None = None
        self._subscribed: WeatherStore | None = None

    @property
    def _store(self) -> WeatherStore:
        return getattr(self._device, STORE_ATTR)

    def _value(self) -> Any:
        return getattr(self._store.settings, self._setting or "")

    async def _async_set(self, value: Any) -> None:
        await self._store.async_set(self._setting or "", value)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._subscribe()
        # A lamp shows its group's weather program while grouped: follow the
        # store when a group (or the lamp) is loaded or unloaded.
        for signal in (SIGNAL_GROUP_MEMBER_READY, SIGNAL_GROUP_MEMBER_GONE):
            self.async_on_remove(
                async_dispatcher_connect(self.hass, signal, self._follow_store)
            )

    @callback
    def _changed(self) -> None:
        self.async_write_ha_state()

    @callback
    def _subscribe(self) -> None:
        self._subscribed = self._store
        self._unsub = self._subscribed.async_add_listener(self._changed)

    @callback
    def _follow_store(self, _entry_id: str) -> None:
        """Listen to the store the lamp now uses, if it changed."""
        if self._store is self._subscribed:
            return
        if self._unsub is not None:
            self._unsub()
        self._subscribe()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()


class WeatherSwitch(WeatherSettingEntity, SwitchEntity):
    """On/off setting."""

    _attr_icon = "mdi:weather-cloudy"

    @property
    def is_on(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        return bool(self._value())

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)


class WeatherModeSwitch(WeatherSwitch):
    """Weather mode: the GPS weather drives the lamp, or its standard week.

    Turned on, the lamp's standard programs are kept aside and the weather
    week is sent at once; turned off, the standard programs come back.
    """

    _attr_entity_category = None
    _attr_icon = "mdi:weather-partly-cloudy"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await set_weather_mode(self.hass, self._device, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await set_weather_mode(self.hass, self._device, False)


class WeatherSelect(WeatherSettingEntity, SelectEntity):
    """Choice among fixed options (translated states)."""

    def __init__(self, device: Any, key: str, setting: str, options: list[str]) -> None:
        super().__init__(device, key, setting)
        self._attr_options = list(options)

    @property
    def current_option(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        return str(self._value())

    async def async_select_option(self, option: str) -> None:
        await self._async_set(option)


class WeatherNumber(WeatherSettingEntity, NumberEntity):
    """Intensity bound (%) or days between two fetches."""

    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        device: Any,
        key: str,
        setting: str,
        bounds: tuple[int, int] = (0, 100),
        unit: str = PERCENTAGE,
    ) -> None:
        super().__init__(device, key, setting)
        self._attr_native_min_value = bounds[0]
        self._attr_native_max_value = bounds[1]
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> float:  # pyright: ignore[reportIncompatibleVariableOverride]
        return float(self._value())

    async def async_set_native_value(self, value: float) -> None:
        await self._async_set(value)


class WeatherText(WeatherSettingEntity, TextEntity):
    """The place: "lat, lon" or a map link."""

    _attr_native_max = 255
    _attr_icon = "mdi:map-marker"

    @property
    def native_value(self) -> str:  # pyright: ignore[reportIncompatibleVariableOverride]
        return str(self._value())

    async def async_set_value(self, value: str) -> None:
        await self._async_set(value)


class WeatherTime(WeatherSettingEntity, TimeEntity):
    """Tank time of the sunrise or of the sunset."""

    @property
    def native_value(self) -> dt_time | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        minutes = parse_hhmm(str(self._value()))
        return None if minutes is None else dt_time(minutes // 60, minutes % 60)

    async def async_set_value(self, value: dt_time) -> None:
        await self._async_set(f"{value.hour:02d}:{value.minute:02d}")


class WeatherSensor(WeatherSettingEntity, SensorEntity):
    """Result of the last generation: ok / error, with the week's summary."""

    _attr_entity_category = None
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["ok", "error"]
    _attr_icon = "mdi:weather-partly-cloudy"

    @property
    def native_value(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        status = self._store.result.get("status")
        return status if status in ("ok", "error") else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        return {
            **{k: v for k, v in self._store.result.items() if k != "status"},
            # A week being written to the lamps: {done, total} days
            "writing": self._store.writing,
            "reef_role": self._key,
        }


def weather_entities(device: Any, platform: str) -> list[Any]:
    """Weather entities of a platform, for a lamp holding a WeatherStore."""
    if not isinstance(getattr(device, STORE_ATTR, None), WeatherStore):
        return []
    builders: dict[str, Callable[[], list[Any]]] = {
        "switch": lambda: [
            WeatherModeSwitch(device, "weather_sync", "enabled"),
            WeatherSwitch(device, "weather_clouds", "clouds"),
        ],
        "select": lambda: [
            WeatherSelect(device, "weather_period", "period", PERIODS),
            WeatherSelect(device, "weather_anchor", "anchor", ANCHORS),
        ],
        "text": lambda: [WeatherText(device, "weather_location", "location")],
        "number": lambda: [
            WeatherNumber(device, "weather_min_intensity", "min_intensity"),
            WeatherNumber(device, "weather_max_intensity", "max_intensity"),
            WeatherNumber(
                device,
                "weather_refresh_days",
                "refresh_days",
                (REFRESH_DAYS_MIN, REFRESH_DAYS_MAX),
                UnitOfTime.DAYS,
            ),
        ],
        "time": lambda: [
            WeatherTime(device, "weather_sunrise", "sunrise"),
            WeatherTime(device, "weather_sunset", "sunset"),
        ],
        "sensor": lambda: [WeatherSensor(device, "weather_program")],
    }
    build = builders.get(platform)
    return build() if build else []
