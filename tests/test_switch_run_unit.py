from __future__ import annotations

from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.switch import (
    ReefBeatSwitchEntity,
    ReefRunSwitchEntity,
    ReefRunSwitchEntityDescription,
)
from tests._switch_test_fakes import FakeCoordinator


class _RunDevice(FakeCoordinator):
    pass


@pytest.mark.asyncio
async def test_run_switch_device_info_adds_pump_suffix() -> None:
    device = FakeCoordinator()
    desc = ReefRunSwitchEntityDescription(
        key="run",
        translation_key="run",
        value_name="$.local.x",
        icon="mdi:on",
        pump=3,
    )

    entity = ReefRunSwitchEntity(cast(Any, device), desc)
    info = entity.device_info

    assert "_pump_3" in cast(str, info.get("name"))
    identifiers = info.get("identifiers")
    assert identifiers is not None


@pytest.mark.asyncio
async def test_run_switch_notify_and_pushes_settings(hass: Any) -> None:
    device = FakeCoordinator()
    device.hass = hass

    events: list[str] = []

    def _on_event(evt: Any) -> None:
        events.append(cast(str, evt.event_type))

    hass.bus.async_listen("event.run", _on_event)

    desc = ReefRunSwitchEntityDescription(
        key="run",
        translation_key="run",
        value_name="event.run",
        icon="mdi:on",
        pump=1,
        notify=True,
        method="put",
    )

    entity = ReefRunSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()
    await hass.async_block_till_done()

    assert events == ["event.run"]
    assert device.pushed == [("/pump/settings", "put")]
    assert device.refreshed == ["/pump/settings"]


@pytest.mark.asyncio
async def test_run_switch_turn_on_notify_and_pushes_settings(hass: Any) -> None:
    device = FakeCoordinator()
    device.hass = hass

    events: list[str] = []

    def _on_event(evt: Any) -> None:
        events.append(cast(str, evt.event_type))

    hass.bus.async_listen("event.run", _on_event)

    desc = ReefRunSwitchEntityDescription(
        key="run",
        translation_key="run",
        value_name="event.run",
        icon="mdi:on",
        pump=1,
        notify=True,
        method="put",
    )

    entity = ReefRunSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()
    await hass.async_block_till_done()

    assert events == ["event.run"]
    assert device.pushed == [("/pump/settings", "put")]
    assert device.refreshed == ["/pump/settings"]


@pytest.mark.asyncio
async def test_switch_async_setup_entry_run_adds_run_and_common(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(platform, "ReefRunCoordinator", _RunDevice, raising=True)

    # Ensure the cloud coordinator isinstance() doesn't short-circuit COMMON switches.
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="run", data={}, unique_id="run")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _RunDevice()

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    entities = added[0]

    assert any(isinstance(e, ReefRunSwitchEntity) for e in entities)
    assert any(isinstance(e, ReefBeatSwitchEntity) for e in entities)
