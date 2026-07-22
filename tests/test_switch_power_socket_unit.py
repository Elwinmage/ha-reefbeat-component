"""Tests for RSPOWER per-socket toggle switch.

Covers the interactions Elwin cares about:

- The switch derives its `is_on` from the (mode, state) pair, using the
  same "manual override wins" rule as the sensor. This matters because
  the firmware reports `state="unknown"` whenever the socket is in a
  manual mode (`mode == "on"` or `mode == "off"`).
- `async_turn_on` / `async_turn_off` compare the desired state to the
  current effective state before firing `POST /socket/{n}/toggle`, so
  that a redundant call from an automation does not invert an already
  correctly positioned socket.
- URL uses the 0-based socket index that the firmware expects
  (`/socket/0/toggle` for the first socket, `/socket/5/toggle` for the
  last one on a RSPOWER6).
- `async_setup_entry` on a RSPOWER coordinator produces `socket_count`
  switch entities with 0-based keys and 1-based display placeholders.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.switch import (
    ReefPowerSocketSwitchEntity,
    ReefPowerSocketSwitchEntityDescription,
)
from tests._switch_test_fakes import FakePowerCoordinator


def _make(device: FakePowerCoordinator, socket_idx: int) -> ReefPowerSocketSwitchEntity:
    """Build a socket switch entity wired up for direct testing."""
    desc = ReefPowerSocketSwitchEntityDescription(
        key=f"socket_{socket_idx}_on_off",
        translation_key="socket_on_off",
        translation_placeholders={"socket": str(socket_idx + 1)},
        icon="mdi:power-plug",
        icon_off="mdi:power-plug-off",
        socket=socket_idx,
    )
    entity = ReefPowerSocketSwitchEntity(cast(Any, device), desc)
    # Neutralize HA state writing so we can drive the entity synchronously.
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]
    return entity


# ---------------------------------------------------------------------------
# Effective state derivation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_socket_is_on_when_mode_is_manual_on() -> None:
    device = FakePowerCoordinator()
    # Manual override "on" — firmware reports state="unknown" in this case.
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[0].mode"] = (
        "on"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[0].state"] = (
        "unknown"
    )

    entity = _make(device, 0)
    entity._handle_coordinator_update()  # noqa: SLF001 — testing derived state

    assert entity.is_on is True


@pytest.mark.asyncio
async def test_socket_is_off_when_mode_is_manual_off() -> None:
    device = FakePowerCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[0].mode"] = (
        "off"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[0].state"] = (
        "unknown"
    )

    entity = _make(device, 0)
    entity._handle_coordinator_update()  # noqa: SLF001

    assert entity.is_on is False


@pytest.mark.asyncio
async def test_socket_uses_state_when_scheduled() -> None:
    """In `schedule`/`sensor`/`auto` modes the firmware fills state properly."""
    device = FakePowerCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[2].mode"] = (
        "schedule"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[2].state"] = (
        "on"
    )

    entity = _make(device, 2)
    entity._handle_coordinator_update()  # noqa: SLF001

    assert entity.is_on is True


@pytest.mark.asyncio
async def test_socket_is_off_when_scheduled_standby() -> None:
    device = FakePowerCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[2].mode"] = (
        "schedule"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[2].state"] = (
        "standby"
    )

    entity = _make(device, 2)
    entity._handle_coordinator_update()  # noqa: SLF001

    assert entity.is_on is False


# ---------------------------------------------------------------------------
# Toggle firing rules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_on_fires_toggle_when_currently_off() -> None:
    device = FakePowerCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[0].mode"] = (
        "off"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[0].state"] = (
        "unknown"
    )

    entity = _make(device, 0)
    await entity.async_turn_on()

    assert device.my_api.sent == [("/socket/0/toggle", {}, "post")]
    assert device.refreshed_all == 1


@pytest.mark.asyncio
async def test_turn_on_is_a_noop_when_already_on() -> None:
    """A redundant turn_on must not flip an already-on socket."""
    device = FakePowerCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[0].mode"] = (
        "on"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[0].state"] = (
        "unknown"
    )

    entity = _make(device, 0)
    await entity.async_turn_on()

    assert device.my_api.sent == []
    assert device.refreshed_all == 0


@pytest.mark.asyncio
async def test_turn_off_fires_toggle_when_currently_on() -> None:
    device = FakePowerCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[3].mode"] = (
        "schedule"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[3].state"] = (
        "on"
    )

    entity = _make(device, 3)
    await entity.async_turn_off()

    assert device.my_api.sent == [("/socket/3/toggle", {}, "post")]
    assert device.refreshed_all == 1


@pytest.mark.asyncio
async def test_turn_off_is_a_noop_when_already_off() -> None:
    device = FakePowerCoordinator()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[3].mode"] = (
        "schedule"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[3].state"] = (
        "standby"
    )

    entity = _make(device, 3)
    await entity.async_turn_off()

    assert device.my_api.sent == []
    assert device.refreshed_all == 0


# ---------------------------------------------------------------------------
# URL indexing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_last_socket_of_rspower8_uses_index_7() -> None:
    """RSPOWER8 exposes sockets 0..7; the URL must match exactly."""
    device = FakePowerCoordinator(socket_count=8)
    # Simulate socket 7 currently off in manual mode.
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[7].mode"] = (
        "off"
    )
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets[7].state"] = (
        "unknown"
    )

    entity = _make(device, 7)
    await entity.async_turn_on()

    assert device.my_api.sent == [("/socket/7/toggle", {}, "post")]


# ---------------------------------------------------------------------------
# Platform wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_setup_entry_creates_socket_count_entities(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every socket must materialize as one entity with the right key."""

    class _PowerDevice(FakePowerCoordinator):
        pass

    monkeypatch.setattr(platform, "ReefPowerCoordinator", _PowerDevice, raising=True)
    # Prevent the COMMON switches branch from firing on our fake.
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="power", data={}, unique_id="power")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _PowerDevice(socket_count=6)

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    socket_entities = [
        e for e in added[0] if isinstance(e, ReefPowerSocketSwitchEntity)
    ]
    assert len(socket_entities) == 6

    keys = {e.entity_description.key for e in socket_entities}
    assert keys == {f"socket_{i}_on_off" for i in range(6)}


@pytest.mark.asyncio
async def test_async_setup_entry_rspower8_creates_8_entities(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _PowerDevice(FakePowerCoordinator):
        pass

    monkeypatch.setattr(platform, "ReefPowerCoordinator", _PowerDevice, raising=True)
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="power8", data={}, unique_id="power8")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _PowerDevice(socket_count=8)

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    socket_entities = [
        e for e in added[0] if isinstance(e, ReefPowerSocketSwitchEntity)
    ]
    assert len(socket_entities) == 8
