from __future__ import annotations

from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import (
    DOMAIN,
    REFRESH_DEVICE_DELAY,
    SENSOR_CONTROLLED_REFRESH_DELAY,
)
from custom_components.redsea.switch import (
    ReefBeatSwitchEntity,
    ReefRunSwitchEntity,
    ReefRunSwitchEntityDescription,
)
from tests._switch_test_fakes import FakeRunCoordinator


class _RunDevice(FakeRunCoordinator):
    pass


@pytest.mark.asyncio
async def test_run_switch_device_info_adds_pump_suffix() -> None:
    device = FakeRunCoordinator()
    desc = ReefRunSwitchEntityDescription(
        key="run",
        translation_key="run",
        value_name="$.local.x",
        icon="mdi:on",
        pump=3,
    )

    entity = ReefRunSwitchEntity(cast(Any, device), desc)
    info = entity.device_info

    assert " pump 3" in cast(str, info.get("name"))
    identifiers = info.get("identifiers")
    assert identifiers is not None


@pytest.mark.asyncio
async def test_run_switch_notify_and_pushes_settings(hass: Any) -> None:
    device = FakeRunCoordinator()
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
    assert device.pump_pushed == [("/pump/settings", "put", 1)]
    assert device.refreshed == ["/pump/settings"]


@pytest.mark.asyncio
async def test_run_switch_turn_on_notify_and_pushes_settings(hass: Any) -> None:
    device = FakeRunCoordinator()
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
    assert device.pump_pushed == [("/pump/settings", "put", 1)]
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


# -- refresh policy after a toggle -------------------------------------------


@pytest.mark.asyncio
async def test_schedule_switch_only_refreshes_pump_settings(hass: Any) -> None:
    """A schedule toggle does not change what /dashboard reports."""
    device = FakeRunCoordinator()
    device.hass = hass

    desc = ReefRunSwitchEntityDescription(
        key="schedule_enabled_pump_1",
        translation_key="schedule_enabled",
        value_name="$.local.x",
        icon="mdi:play",
        pump=1,
    )
    entity = ReefRunSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()

    assert device.refresh_calls == [("/pump/settings", REFRESH_DEVICE_DELAY)]


@pytest.mark.asyncio
async def test_sensor_controlled_switch_refreshes_every_source(hass: Any) -> None:
    """Sensor control changes the running intensity, which lives in /dashboard."""
    device = FakeRunCoordinator()
    device.hass = hass

    desc = ReefRunSwitchEntityDescription(
        key="sensor_controlled_pump_1",
        translation_key="sensor_controlled_switch",
        value_name="$.local.x",
        icon="mdi:car-speed-limiter",
        pump=1,
        refresh_source=None,
        refresh_wait=SENSOR_CONTROLLED_REFRESH_DELAY,
    )
    entity = ReefRunSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()
    await entity.async_turn_off()

    # source None => full data refresh, and a longer settle delay
    assert device.refresh_calls == [
        (None, SENSOR_CONTROLLED_REFRESH_DELAY),
        (None, SENSOR_CONTROLLED_REFRESH_DELAY),
    ]


@pytest.mark.asyncio
async def test_sensor_controlled_descriptions_ask_for_a_full_refresh(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The platform must build the sensor_controlled switches with that policy."""
    monkeypatch.setattr(platform, "ReefRunCoordinator", _RunDevice, raising=True)
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="run", data={}, unique_id="run2")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _RunDevice()

    added: list[Any] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(new_entities)

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    descs = [e._typed_desc for e in added if isinstance(e, ReefRunSwitchEntity)]

    sensor_controlled = [
        d for d in descs if d.translation_key == "sensor_controlled_switch"
    ]
    assert len(sensor_controlled) == 2
    for desc in sensor_controlled:
        assert desc.refresh_source is None
        assert desc.refresh_wait == SENSOR_CONTROLLED_REFRESH_DELAY

    schedule = [d for d in descs if d.translation_key == "schedule_enabled"]
    assert len(schedule) == 2
    for desc in schedule:
        assert desc.refresh_source == "/pump/settings"
        assert desc.refresh_wait == REFRESH_DEVICE_DELAY
