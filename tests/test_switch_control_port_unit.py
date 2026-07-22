"""Tests for RSCONTROL per-port toggle switch.

Same shape as the RSPOWER socket tests, but on ``ports[]`` and with
``port_count`` = 1 (RSCONTROLLITE) or 2 (RSCONTROLPRO). Endpoints tested:
``POST /port/{n}/toggle`` with `n` starting at 0.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.switch import (
    ReefControlPortSwitchEntity,
    ReefControlPortSwitchEntityDescription,
)
from tests._switch_test_fakes import FakeControlCoordinator


def _make(device: FakeControlCoordinator, port_idx: int) -> ReefControlPortSwitchEntity:
    desc = ReefControlPortSwitchEntityDescription(
        key=f"port_{port_idx}_on_off",
        translation_key="port_on_off",
        translation_placeholders={"port": str(port_idx + 1)},
        icon="mdi:electric-switch-closed",
        icon_off="mdi:electric-switch",
        port=port_idx,
    )
    entity = ReefControlPortSwitchEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]
    return entity


# ---------------------------------------------------------------------------
# Effective state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_port_is_on_when_manual_on() -> None:
    device = FakeControlCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].mode"] = "on"
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].state"] = (
        "unknown"
    )

    entity = _make(device, 0)
    entity._handle_coordinator_update()  # noqa: SLF001

    assert entity.is_on is True


@pytest.mark.asyncio
async def test_port_is_off_when_manual_off() -> None:
    device = FakeControlCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[1].mode"] = "off"
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[1].state"] = (
        "unknown"
    )

    entity = _make(device, 1)
    entity._handle_coordinator_update()  # noqa: SLF001

    assert entity.is_on is False


@pytest.mark.asyncio
async def test_port_uses_state_when_scheduled() -> None:
    device = FakeControlCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].mode"] = (
        "sensor"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].state"] = "on"

    entity = _make(device, 0)
    entity._handle_coordinator_update()  # noqa: SLF001

    assert entity.is_on is True


# ---------------------------------------------------------------------------
# Toggle rules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_on_fires_toggle_when_currently_off() -> None:
    device = FakeControlCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].mode"] = "off"
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].state"] = (
        "unknown"
    )

    entity = _make(device, 0)
    await entity.async_turn_on()

    assert device.my_api.sent == [("/port/0/toggle", {}, "post")]
    assert device.refreshed_all == 1


@pytest.mark.asyncio
async def test_turn_off_fires_toggle_when_currently_on() -> None:
    device = FakeControlCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[1].mode"] = "on"
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[1].state"] = (
        "unknown"
    )

    entity = _make(device, 1)
    await entity.async_turn_off()

    assert device.my_api.sent == [("/port/1/toggle", {}, "post")]
    assert device.refreshed_all == 1


@pytest.mark.asyncio
async def test_turn_on_is_a_noop_when_already_on() -> None:
    device = FakeControlCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].mode"] = "on"
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].state"] = (
        "unknown"
    )

    entity = _make(device, 0)
    await entity.async_turn_on()

    assert device.my_api.sent == []


@pytest.mark.asyncio
async def test_turn_off_is_a_noop_when_already_off() -> None:
    device = FakeControlCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].mode"] = (
        "sensor"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[0].state"] = (
        "standby"
    )

    entity = _make(device, 0)
    await entity.async_turn_off()

    assert device.my_api.sent == []


# ---------------------------------------------------------------------------
# Platform wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_setup_entry_control_lite_creates_1_entity(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _ControlDevice(FakeControlCoordinator):
        pass

    monkeypatch.setattr(
        platform, "ReefControlCoordinator", _ControlDevice, raising=True
    )
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _ControlDevice(port_count=1)

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    port_entities = [e for e in added[0] if isinstance(e, ReefControlPortSwitchEntity)]
    assert len(port_entities) == 1
    assert port_entities[0].entity_description.key == "port_0_on_off"


@pytest.mark.asyncio
async def test_async_setup_entry_control_pro_creates_2_entities(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _ControlDevice(FakeControlCoordinator):
        pass

    monkeypatch.setattr(
        platform, "ReefControlCoordinator", _ControlDevice, raising=True
    )
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _ControlDevice(port_count=2)

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    port_entities = [e for e in added[0] if isinstance(e, ReefControlPortSwitchEntity)]
    assert len(port_entities) == 2
    keys = {e.entity_description.key for e in port_entities}
    assert keys == {"port_0_on_off", "port_1_on_off"}
