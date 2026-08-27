from __future__ import annotations

from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import (
    ATO_BUZZER_ENABLED_INTERNAL_NAME,
    ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME,
    DOMAIN,
)
from custom_components.redsea.switch import ReefBeatSwitchEntity
from tests._switch_test_fakes import FakeCoordinator


class _AtoDevice(FakeCoordinator):
    pass


@pytest.mark.asyncio
async def test_switch_async_setup_entry_ato_adds_ato_switches_and_common(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(platform, "ReefATOCoordinator", _AtoDevice, raising=True)

    # Ensure the cloud coordinator isinstance() doesn't short-circuit COMMON switches.
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ato", data={}, unique_id="ato")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _AtoDevice()

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    entities = added[0]

    assert entities
    assert all(isinstance(e, ReefBeatSwitchEntity) for e in entities)


@pytest.mark.asyncio
async def test_switch_platform_builds_ato_buzzer(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The RSATO+ exposes the leak buzzer as a config switch."""
    monkeypatch.setattr(platform, "ReefATOCoordinator", _AtoDevice, raising=True)
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ato", data={}, unique_id="ato-buzzer")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _AtoDevice()

    added: list[Any] = []
    await platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    keys = {e.entity_description.key for e in added}
    assert "buzzer_enabled" in keys
    assert "auto_fill" in keys


@pytest.mark.asyncio
async def test_ato_buzzer_switch_toggle_pushes_configuration() -> None:
    """Toggling writes the cache, PUTs `/configuration`, re-reads `/dashboard`.

    The two endpoints differ on purpose: the firmware only accepts the setting
    on `/configuration`, but reports it on the polled `/dashboard`.
    """
    device = _AtoDevice()
    desc = next(d for d in platform.ATO_SWITCHES if d.key == "buzzer_enabled")

    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()
    assert entity._attr_is_on is True
    assert entity._attr_icon == "mdi:bell-ring"
    assert (ATO_BUZZER_ENABLED_INTERNAL_NAME, True) in device.set_calls
    assert device.pushed == [("/configuration", "put")]
    assert device.refreshed == ["/dashboard"]

    await entity.async_turn_off()
    assert entity._attr_is_on is False
    assert entity._attr_icon == "mdi:bell-off"
    assert (ATO_BUZZER_ENABLED_INTERNAL_NAME, False) in device.set_calls
    assert device.pushed == [("/configuration", "put"), ("/configuration", "put")]


@pytest.mark.asyncio
async def test_switch_platform_builds_ato_leak_sensor(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The leak probe's arming flag is a switch, not a read-only sensor."""
    monkeypatch.setattr(platform, "ReefATOCoordinator", _AtoDevice, raising=True)
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ato", data={}, unique_id="ato-leak")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _AtoDevice()

    added: list[Any] = []
    await platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    assert "enabled" in {e.entity_description.key for e in added}


@pytest.mark.asyncio
async def test_ato_leak_sensor_switch_toggle_pushes_configuration() -> None:
    """Same split as the buzzer: PUT `/configuration`, re-read `/dashboard`."""
    device = _AtoDevice()
    desc = next(d for d in platform.ATO_SWITCHES if d.key == "enabled")

    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()
    assert entity._attr_is_on is False
    assert entity._attr_icon == "mdi:leak-off"
    assert (ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME, False) in device.set_calls
    assert device.pushed == [("/configuration", "put")]
    assert device.refreshed == ["/dashboard"]

    await entity.async_turn_on()
    assert entity._attr_is_on is True
    assert entity._attr_icon == "mdi:leak"
