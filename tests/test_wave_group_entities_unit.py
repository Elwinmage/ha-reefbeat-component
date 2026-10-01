"""Switch of a ReefWave's group (wave_group_entities)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.redsea.switch import WAVE_GROUP_SWITCH
from custom_components.redsea.wave_group_entities import WaveGroupSwitchEntity


class _Pump:
    serial = "SER"
    device_info: dict[str, Any] = {}

    def __init__(self, grouped: bool | None) -> None:
        self.grouped = grouped
        self.set_wave_grouped = AsyncMock()
        self.listeners: list[Any] = []
        self.removed = False
        self.wave_weather: Any = None

    def wave_grouped(self) -> bool | None:
        return self.grouped

    def async_add_listener(self, cb: Any) -> Any:
        self.listeners.append(cb)

        def _remove() -> None:
            self.removed = True

        return _remove


@pytest.mark.asyncio
async def test_switch_reads_and_writes_the_group() -> None:
    pump = _Pump(True)
    sw = WaveGroupSwitchEntity(pump, WAVE_GROUP_SWITCH)
    assert sw.unique_id == "SER_wave_grouped"
    assert sw.translation_key == "wave_grouped"
    assert sw.available is True and sw.is_on is True
    await sw.async_turn_off()
    pump.set_wave_grouped.assert_awaited_with(False)
    await sw.async_turn_on()
    pump.set_wave_grouped.assert_awaited_with(True)
    # Without cloud: unavailable
    pump.grouped = None
    assert sw.available is False

    # Listener: the state is written on every coordinator update
    sw.hass = MagicMock()
    sw.async_write_ha_state = MagicMock()  # type: ignore[method-assign]
    await sw.async_added_to_hass()
    pump.listeners[0]()
    sw.async_write_ha_state.assert_called_once()
    await sw.async_will_remove_from_hass()
    assert pump.removed is True
    # Twice is harmless
    await sw.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_weather_switch(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    import custom_components.redsea.wave_group_entities as E
    from custom_components.redsea.switch import WAVE_WEATHER_SWITCH
    from custom_components.redsea.wave_weather import WaveWeatherStore

    saved: list[Any] = []

    async def _save(_hass: Any, pump: Any, settings: Any, offsets: Any, on: bool):
        saved.append((pump, settings, offsets, on))
        return {}

    monkeypatch.setattr(E, "save_wave_weather", _save)
    pump = _Pump(True)
    sw = E.WaveWeatherSwitchEntity(pump, WAVE_WEATHER_SWITCH)
    assert sw.unique_id == "SER_wave_weather"
    # No store (yet): off, no attributes, no listener
    assert sw.is_on is False and sw.extra_state_attributes is None
    sw.hass = hass
    await sw.async_added_to_hass()
    await sw.async_will_remove_from_hass()

    store = WaveWeatherStore(hass, "sw")
    pump.wave_weather = store
    assert sw.extra_state_attributes is None
    store.settings.enabled = True
    store.result = {"status": "ok", "speeds": [1], "hours": [], "sunrise": "06:00"}
    assert sw.is_on is True
    assert sw.extra_state_attributes == {
        "status": "ok",
        "sunrise": "06:00",
        "speeds": [1],
    }
    await sw.async_turn_on()
    await sw.async_turn_off()
    assert saved == [(pump, None, None, True), (pump, None, None, False)]
    sw.async_write_ha_state = MagicMock()  # type: ignore[method-assign]
    await sw.async_added_to_hass()
    await store.async_save()
    sw.async_write_ha_state.assert_called_once()
    await sw.async_will_remove_from_hass()
    await store.async_save()
    sw.async_write_ha_state.assert_called_once()
