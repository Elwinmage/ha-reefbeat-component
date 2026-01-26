from __future__ import annotations

from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.switch import (
    ReefBeatSwitchEntity,
    ReefLedSwitchEntity,
    ReefLedSwitchEntityDescription,
)
from tests._switch_test_fakes import FakeCoordinator


class _LedDevice(FakeCoordinator):
    pass


@pytest.mark.asyncio
async def test_led_switch_turn_on_pushes_source(hass: Any) -> None:
    device = FakeCoordinator()

    desc = ReefLedSwitchEntityDescription(
        key="sw",
        translation_key="sw",
        value_name="$.sources[?(@.name=='/manual')].data.enabled",
        icon="mdi:on",
        icon_off="mdi:off",
        method="post",
    )

    entity = ReefLedSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()
    assert device.pushed == [("/manual", "post")]
    assert device.refreshed == ["/manual"]


@pytest.mark.asyncio
async def test_led_switch_turn_off_pushes_source(hass: Any) -> None:
    device = FakeCoordinator()

    desc = ReefLedSwitchEntityDescription(
        key="sw",
        translation_key="sw",
        value_name="$.sources[?(@.name=='/manual')].data.enabled",
        icon="mdi:on",
        icon_off="mdi:off",
        method="post",
    )

    entity = ReefLedSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()
    assert device.pushed == [("/manual", "post")]
    assert device.refreshed == ["/manual"]


@pytest.mark.asyncio
async def test_switch_async_setup_entry_led_adds_led_and_common(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(platform, "ReefLedCoordinator", _LedDevice, raising=True)
    monkeypatch.setattr(platform, "ReefVirtualLedCoordinator", _LedDevice, raising=True)
    monkeypatch.setattr(platform, "ReefLedG2Coordinator", _LedDevice, raising=True)

    # Ensure the cloud coordinator isinstance() doesn't short-circuit COMMON switches.
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="led", data={}, unique_id="led")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _LedDevice()

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    entities = added[0]

    assert any(isinstance(e, ReefLedSwitchEntity) for e in entities)
    assert any(isinstance(e, ReefBeatSwitchEntity) for e in entities)
