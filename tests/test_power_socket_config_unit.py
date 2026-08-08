"""Tests for the RSPOWER socket-config control surface.

Covers the endpoints reverse-engineered from the ReefBeat app traffic:

- ``ReefPowerAPI.set_socket_mode``   → ``PUT /sockets/config``
- ``ReefPowerAPI.set_socket_schedule`` → ``PUT /socket/<n>/config/schedule``
- ``ReefPowerAPI.setup_finish``      → ``POST /setup-finish``
- the ``/sockets/config`` source registration
- ``ReefPowerCoordinator`` delegating methods (call API + refresh)
- the per-socket mode select entity (write + setup→None mapping)
- the "Finish setup" button wiring
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.button as button_platform
import custom_components.redsea.select as select_platform
from custom_components.redsea.const import (
    DOMAIN,
)
from tests._switch_test_fakes import FakePowerCoordinator

# ===========================================================================
# ReefPowerAPI write methods
# ===========================================================================


def _make_api() -> Any:
    """Build a ReefPowerAPI with a stub session and a recording http_send."""
    from custom_components.redsea.reefbeat.power import ReefPowerAPI

    api = ReefPowerAPI("10.0.0.9", False, cast(Any, MagicMock(name="session")))
    api.http_send = AsyncMock(return_value=None)  # type: ignore[method-assign]
    return api


def test_sockets_config_source_registered() -> None:
    """The API registers /sockets/config so socket modes/names are readable."""
    api = _make_api()
    names = [s.get("name") for s in api.data["sources"]]
    assert "/sockets/config" in names
    assert "/configuration" in names


@pytest.mark.asyncio
async def test_set_socket_mode_puts_partial_sockets_config() -> None:
    """set_socket_mode sends only the changed socket to /sockets/config."""
    api = _make_api()
    await api.set_socket_mode(2, "schedule")
    api.http_send.assert_awaited_once_with(
        "/sockets/config", {"sockets": [{"mode": "schedule", "number": 2}]}, "put"
    )


@pytest.mark.asyncio
async def test_set_socket_mode_includes_name_when_renaming() -> None:
    """A name is only included when explicitly renaming the socket."""
    api = _make_api()
    await api.set_socket_mode(0, "off", name="t1")
    api.http_send.assert_awaited_once_with(
        "/sockets/config",
        {"sockets": [{"mode": "off", "number": 0, "name": "t1"}]},
        "put",
    )


@pytest.mark.asyncio
async def test_set_socket_schedule_puts_intervals() -> None:
    """set_socket_schedule targets the per-socket schedule endpoint."""
    api = _make_api()
    intervals = [{"time": 0, "duration": 539}, {"time": 1320, "duration": 119}]
    await api.set_socket_schedule(2, intervals)
    api.http_send.assert_awaited_once_with(
        "/socket/2/config/schedule", {"intervals": intervals}, "put"
    )


@pytest.mark.asyncio
async def test_setup_finish_posts_empty_body() -> None:
    """setup_finish POSTs /setup-finish with an empty JSON body."""
    api = _make_api()
    await api.setup_finish()
    api.http_send.assert_awaited_once_with("/setup-finish", {}, "post")


# ===========================================================================
# ReefPowerCoordinator delegating methods
# ===========================================================================


def _make_coordinator() -> Any:
    """Build a ReefPowerCoordinator without running __init__ (no aiohttp session).

    The delegating methods only touch ``self.my_api`` and
    ``self.async_request_refresh``, so we bypass the network-touching
    constructor and wire those two attributes directly.
    """
    from custom_components.redsea.coordinator import ReefPowerCoordinator

    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = MagicMock(
        set_socket_mode=AsyncMock(),
        set_socket_schedule=AsyncMock(),
        setup_finish=AsyncMock(),
    )
    coord.async_request_refresh = AsyncMock()  # type: ignore[method-assign]
    return coord


@pytest.mark.asyncio
async def test_coordinator_set_socket_mode_delegates_and_refreshes() -> None:
    coord = _make_coordinator()
    await coord.set_socket_mode(3, "on")
    coord.my_api.set_socket_mode.assert_awaited_once_with(3, "on")
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_set_socket_schedule_delegates_and_refreshes() -> None:
    coord = _make_coordinator()
    intervals = [{"time": 0, "duration": 1439}]
    await coord.set_socket_schedule(1, intervals)
    coord.my_api.set_socket_schedule.assert_awaited_once_with(1, intervals)
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_setup_finish_delegates_and_refreshes() -> None:
    coord = _make_coordinator()
    await coord.setup_finish()
    coord.my_api.setup_finish.assert_awaited_once()
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_set_socket_name_sends_current_mode_with_name() -> None:
    """Renaming resends the socket's current mode alongside the new name."""
    coord = _make_coordinator()
    coord.get_data = MagicMock(return_value="schedule")  # type: ignore[method-assign]
    await coord.set_socket_name(2, "reactor")
    coord.my_api.set_socket_mode.assert_awaited_once_with(2, "schedule", name="reactor")
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_set_socket_name_falls_back_to_off_when_in_setup() -> None:
    """If the current mode isn't writable (e.g. 'setup'), fall back to 'off'."""
    coord = _make_coordinator()
    coord.get_data = MagicMock(return_value="setup")  # type: ignore[method-assign]
    await coord.set_socket_name(0, "t1")
    coord.my_api.set_socket_mode.assert_awaited_once_with(0, "off", name="t1")


# ===========================================================================
# Per-socket mode select entity
# ===========================================================================


def _make_select(device: FakePowerCoordinator, socket_idx: int) -> Any:
    desc = select_platform.ReefPowerSocketModeSelectEntityDescription(
        key=f"socket_{socket_idx}_mode",
        translation_key="socket_mode",
        translation_placeholders={"socket": str(socket_idx + 1)},
        value_name=(
            "$.sources[?(@.name=='/dashboard')].data.sockets"
            f"[?(@.number=={socket_idx})].user_config_mode"
        ),
        options=["off", "on", "schedule"],
        socket=socket_idx,
    )
    entity = select_platform.ReefPowerSocketModeSelectEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]
    return entity


def _mode_path(idx: int) -> str:
    return (
        "$.sources[?(@.name=='/dashboard')].data.sockets"
        f"[?(@.number=={idx})].user_config_mode"
    )


def test_select_reads_current_mode() -> None:
    device = FakePowerCoordinator()
    device.get_data_map[_mode_path(2)] = "schedule"
    entity = _make_select(device, 2)
    entity._update_val()
    assert entity.current_option == "schedule"
    # device_info is proxied straight from the coordinator.
    assert entity.device_info == device.device_info


def test_select_maps_setup_to_none() -> None:
    """A transient 'setup' mode is not a selectable option, so it maps to None."""
    device = FakePowerCoordinator()
    device.get_data_map[_mode_path(0)] = "setup"
    entity = _make_select(device, 0)
    entity._update_val()
    assert entity.current_option is None


def test_select_maps_unknown_to_none() -> None:
    device = FakePowerCoordinator()
    device.get_data_map[_mode_path(0)] = None
    entity = _make_select(device, 0)
    entity._update_val()
    assert entity.current_option is None


@pytest.mark.asyncio
async def test_select_option_calls_set_socket_mode() -> None:
    device = FakePowerCoordinator()
    entity = _make_select(device, 4)
    await entity.async_select_option("on")
    assert device.mode_calls == [(4, "on")]
    assert entity.current_option == "on"


@pytest.mark.asyncio
async def test_setup_entry_creates_one_mode_select_per_socket(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _PowerDevice(FakePowerCoordinator):
        pass

    monkeypatch.setattr(
        select_platform, "ReefPowerCoordinator", _PowerDevice, raising=True
    )

    device = _PowerDevice(socket_count=6)
    device.hass = hass
    entry = MockConfigEntry(domain=DOMAIN, title="pwr", unique_id="pwr")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []

    def _add(new: Any, _update: bool = False) -> None:
        added.extend(list(new))

    await select_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    mode_keys = {
        e.entity_description.key
        for e in added
        if e.entity_description.key.endswith("_mode")
    }
    assert mode_keys == {f"socket_{i}_mode" for i in range(6)}


# ===========================================================================
# Finish-setup button
# ===========================================================================


@pytest.mark.asyncio
async def test_setup_finish_button_calls_coordinator() -> None:
    """The setup_finish button's press_fn triggers coordinator.setup_finish()."""
    device = FakePowerCoordinator()
    description = next(
        d for d in button_platform.POWER_BUTTONS if d.key == "setup_finish"
    )
    assert description.press_fn is not None
    await cast(Any, description.press_fn(cast(Any, device)))
    assert device.setup_finished == 1


# ===========================================================================
# Switch friendly name = socket name
# ===========================================================================


def _make_switch(device: FakePowerCoordinator, socket_idx: int) -> Any:
    import custom_components.redsea.switch as switch_platform

    desc = switch_platform.ReefPowerSocketSwitchEntityDescription(
        key=f"socket_{socket_idx}_on_off",
        translation_key="socket_on_off",
        translation_placeholders={"socket": str(socket_idx + 1)},
        icon="mdi:power-plug",
        icon_off="mdi:power-plug-off",
        socket=socket_idx,
    )
    entity = switch_platform.ReefPowerSocketSwitchEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]
    return entity


def _name_path(idx: int) -> str:
    return f"$.sources[?(@.name=='/dashboard')].data.sockets[{idx}].name"


def test_switch_name_uses_socket_name() -> None:
    device = FakePowerCoordinator()
    device.get_data_map[_name_path(0)] = "t1"
    entity = _make_switch(device, 0)
    assert entity.name == "t1"


def test_switch_name_falls_back_when_unnamed() -> None:
    device = FakePowerCoordinator()
    device.get_data_map[_name_path(3)] = None
    entity = _make_switch(device, 3)
    assert entity.name == "Socket 4"


# ===========================================================================
# Per-socket name text entity
# ===========================================================================


def _make_name_text(device: FakePowerCoordinator, socket_idx: int) -> Any:
    import custom_components.redsea.text as text_platform

    desc = text_platform.ReefPowerSocketNameTextEntityDescription(
        key=f"socket_{socket_idx}_name",
        translation_key="socket_name",
        translation_placeholders={"socket": str(socket_idx + 1)},
        value_name=_name_path(socket_idx),
        socket=socket_idx,
    )
    entity = text_platform.ReefPowerSocketNameTextEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]
    return entity


def test_name_text_reads_current_name() -> None:
    device = FakePowerCoordinator()
    device.get_data_map[_name_path(2)] = "reactor"
    entity = _make_name_text(device, 2)
    assert entity.native_value == "reactor"


@pytest.mark.asyncio
async def test_name_text_set_value_calls_set_socket_name() -> None:
    device = FakePowerCoordinator()
    entity = _make_name_text(device, 4)
    await entity.async_set_value("skimmer")
    assert device.name_calls == [(4, "skimmer")]
    assert entity.native_value == "skimmer"


@pytest.mark.asyncio
async def test_text_setup_entry_creates_one_name_per_socket(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    import custom_components.redsea.text as text_platform

    class _PowerDevice(FakePowerCoordinator):
        pass

    monkeypatch.setattr(
        text_platform, "ReefPowerCoordinator", _PowerDevice, raising=True
    )

    device = _PowerDevice(socket_count=6)
    device.hass = hass
    entry = MockConfigEntry(domain=DOMAIN, title="pwr", unique_id="pwr")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []

    def _add(new: Any, _update: bool = False) -> None:
        added.extend(list(new))

    await text_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    keys = {e.entity_description.key for e in added}
    assert keys == {f"socket_{i}_name" for i in range(6)}
