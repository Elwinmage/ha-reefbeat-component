from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.redsea.switch import (
    ReefBeatSwitchEntity,
    ReefBeatSwitchEntityDescription,
)
from tests._switch_test_fakes import FakeCoordinator, State


@pytest.mark.asyncio
async def test_reefbeat_switch_compute_is_on_branches() -> None:
    device = FakeCoordinator()

    desc_device = ReefBeatSwitchEntityDescription(
        key="device_state",
        translation_key="device_state",
        value_name="$.local.mode",
        icon="mdi:on",
        icon_off="mdi:off",
    )
    ent_device = ReefBeatSwitchEntity(cast(Any, device), desc_device)
    device.get_data_map["$.local.mode"] = "off"
    assert ent_device._compute_is_on() is False
    device.get_data_map["$.local.mode"] = "auto"
    assert ent_device._compute_is_on() is True

    desc_maint = ReefBeatSwitchEntityDescription(
        key="maintenance",
        translation_key="maintenance",
        value_name="$.local.mode",
        icon="mdi:on",
        icon_off="mdi:off",
    )
    ent_maint = ReefBeatSwitchEntity(cast(Any, device), desc_maint)
    device.get_data_map["$.local.mode"] = "maintenance"
    assert ent_maint._compute_is_on() is True
    device.get_data_map["$.local.mode"] = "auto"
    assert ent_maint._compute_is_on() is False

    desc_generic = ReefBeatSwitchEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.local.some_bool",
        icon="mdi:on",
        icon_off="mdi:off",
    )
    ent_generic = ReefBeatSwitchEntity(cast(Any, device), desc_generic)
    device.get_data_map["$.local.some_bool"] = 0
    assert ent_generic._compute_is_on() is False
    device.get_data_map["$.local.some_bool"] = 1
    assert ent_generic._compute_is_on() is True

    assert ReefBeatSwitchEntity._restore_is_on("on") is True
    assert ReefBeatSwitchEntity._restore_is_on("off") is False


@pytest.mark.asyncio
async def test_reefbeat_switch_async_added_to_hass_restores_last_state_then_primes(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.entity import ReefBeatRestoreEntity

    async def _noop_added_to_hass(self: Any) -> None:
        return None

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_added_to_hass
    )

    handled: list[bool] = []

    def _noop_handle_update(self: Any) -> None:
        handled.append(True)

    monkeypatch.setattr(
        CoordinatorEntity,
        "_handle_coordinator_update",
        _noop_handle_update,
        raising=True,
    )

    device = FakeCoordinator(get_data_map={"$.local.some_bool": 1})
    desc = ReefBeatSwitchEntityDescription(
        key="generic",
        translation_key="generic",
        value_name="$.local.some_bool",
        icon="mdi:on",
        icon_off="mdi:off",
    )

    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    entity.hass = hass

    async def _last_state() -> State:
        return State("on")

    entity.async_get_last_state = _last_state  # type: ignore[assignment]

    wrote: list[bool] = []

    def _write() -> None:
        wrote.append(True)

    entity.async_write_ha_state = _write  # type: ignore[assignment]

    await entity.async_added_to_hass()

    assert entity.available is True
    assert entity.is_on is True
    assert handled == [True]
    # One write during restore block, one after priming.
    assert len(wrote) >= 1


def test_reefbeat_switch_device_info_returns_coordinator_device_info() -> None:
    device = FakeCoordinator()
    desc = ReefBeatSwitchEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.local.x",
        icon="mdi:on",
        icon_off="mdi:off",
    )
    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    assert entity.device_info == device.device_info


@pytest.mark.asyncio
async def test_reefbeat_switch_device_state_on_calls_delete(hass: Any) -> None:
    device = FakeCoordinator()

    desc = ReefBeatSwitchEntityDescription(
        key="device_state",
        translation_key="device_state",
        value_name="$.local.mode",
        icon="mdi:on",
        icon_off="mdi:off",
    )

    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()

    assert ("$.local.mode", "auto") in device.set_calls
    assert device.deleted == ["/off"]


@pytest.mark.asyncio
async def test_reefbeat_switch_device_state_off_calls_press(hass: Any) -> None:
    device = FakeCoordinator()

    desc = ReefBeatSwitchEntityDescription(
        key="device_state",
        translation_key="device_state",
        value_name="$.local.mode",
        icon="mdi:on",
        icon_off="mdi:off",
    )

    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()

    assert ("$.local.mode", "off") in device.set_calls
    assert device.pressed == ["off"]


@pytest.mark.asyncio
async def test_reefbeat_switch_maintenance_off_calls_delete_and_fetch(
    hass: Any,
) -> None:
    device = FakeCoordinator()

    desc = ReefBeatSwitchEntityDescription(
        key="maintenance",
        translation_key="maintenance",
        value_name="$.local.mode",
        icon="mdi:on",
        icon_off="mdi:off",
    )

    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()

    assert ("$.local.mode", "auto") in device.set_calls
    assert device.deleted == ["/maintenance"]
    assert device.fetched == ["/mode"]


@pytest.mark.asyncio
async def test_reefbeat_switch_cloud_connect_on_off(hass: Any) -> None:
    device = FakeCoordinator()

    desc = ReefBeatSwitchEntityDescription(
        key="cloud_connect",
        translation_key="cloud_connect",
        value_name="$.local.cloud_enabled",
        icon="mdi:cloud",
        icon_off="mdi:cloud-off",
    )

    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()
    assert device.pressed == ["cloud/enable"]
    assert device.get_data_map["$.local.cloud_enabled"] is True

    await entity.async_turn_off()
    assert device.pressed[-1] == "cloud/disable"
    assert device.get_data_map["$.local.cloud_enabled"] is False


@pytest.mark.asyncio
async def test_reefbeat_switch_generic_source_pushes_and_refreshes(hass: Any) -> None:
    device = FakeCoordinator()

    desc = ReefBeatSwitchEntityDescription(
        key="generic",
        translation_key="generic",
        value_name="$.sources[?(@.name=='/manual')].data.enabled",
        icon="mdi:on",
        icon_off="mdi:off",
        method="post",
    )

    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()
    assert device.pushed == [("/manual", "post")]
    assert device.refreshed == ["/manual"]

    await entity.async_turn_off()
    assert device.pushed[-1] == ("/manual", "post")
    assert device.refreshed[-1] == "/manual"


def test_reefbeat_switch_extracts_source_from_value_name_in_init() -> None:
    device = FakeCoordinator()
    desc = ReefBeatSwitchEntityDescription(
        key="generic",
        translation_key="generic",
        value_name="$.sources[?(@.name=='/manual')].data.enabled",
        icon="mdi:on",
        icon_off="mdi:off",
        method="post",
    )
    entity = ReefBeatSwitchEntity(cast(Any, device), desc)
    assert entity._source == "/manual"
