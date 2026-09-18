"""Tests for the RSCONTROL port-config control surface.

The 12V ports of the ReefControl hub are configured like the AC sockets of
the ReefControl Power center, so this mirrors
``test_power_socket_config_unit.py``. Two behavioural differences matter, both
confirmed by capturing the ReefBeat app configuring a real port:

1. The hub takes a **bare JSON array** on ``PUT /ports/config`` whereas the
   power center wraps its entries in ``{"sockets": [...]}``.
2. The hub wants the **whole entry** on every write, and refuses any write to
   a port that has not been installed first via ``POST /port/<n>/install``.

Covers:

- ``ReefControlAPI.install_port``      → ``POST /port/<n>/install``
- ``ReefControlAPI.set_port_mode``     → ``PUT /ports/config`` (bare array)
- ``ReefControlAPI.set_port_schedule`` → ``PUT /port/<n>/schedule``
- ``ReefControlAPI.setup_finish``      → ``POST /setup-finish``
- ``ReefControlCoordinator`` delegating methods (call API + refresh)
- the per-port name text entity

Port mode selection itself (off/on/schedule/sensor) is configured from
ha-reef-card via the generic ``redsea.request`` service, not from an HA
entity — there is no select entity here to test (mirrors RSPower's sockets).
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.text as text_platform
from custom_components.redsea.const import DOMAIN
from tests._switch_test_fakes import FakeControlCoordinator

# ===========================================================================
# ReefControlAPI write methods
# ===========================================================================


# The full `/ports/config` entry the firmware returns for an installed port,
# copied from a real RSCONTROLPRO capture.
_PORT0_CONFIG: dict[str, Any] = {
    "number": 0,
    "type": "other",
    "mode": "off",
    "user_config_mode": "off",
    "enabled": True,
    "name": "t1",
    "shortcut_off_delay": 0,
    "power_detector_enabled": False,
    "power_on_percent": 80,
    "is_btn_assigned": True,
    "sensor": None,
}
_PORT1_UNINSTALLED: dict[str, Any] = {
    "number": 1,
    "type": "unknown",
    "mode": "setup",
    "user_config_mode": "setup",
    "enabled": True,
    "name": "S2",
    "shortcut_off_delay": 0,
    "power_detector_enabled": False,
    "power_on_percent": 100,
    "is_btn_assigned": False,
    "sensor": None,
}


def _make_api() -> Any:
    """Build a ReefControlAPI with a stub session and a recording http_send.

    The `/ports/config` cache is primed because `set_port_mode` rebuilds the
    whole entry from it.
    """
    from custom_components.redsea.reefbeat.control import ReefControlAPI

    api = ReefControlAPI("10.0.0.7", False, cast(Any, MagicMock(name="session")))
    api.http_send = AsyncMock(return_value={"ok": True})  # type: ignore[method-assign]
    for source in api.data["sources"]:
        if source["name"] == "/ports/config":
            source["data"] = [dict(_PORT0_CONFIG), dict(_PORT1_UNINSTALLED)]
    return api


def test_ports_config_source_registered() -> None:
    """`/ports/config` must be polled: PUT needs the whole cached entry."""
    api = _make_api()
    names = [s.get("name") for s in api.data["sources"]]
    assert "/ports/config" in names


def test_port_is_installed_reads_type() -> None:
    """A factory-fresh port reports `type == "unknown"` and is not writable."""
    api = _make_api()
    assert api.port_is_installed(0) is True
    assert api.port_is_installed(1) is False


@pytest.mark.asyncio
async def test_delete_port_sends_delete() -> None:
    """Uninstalling resets the port to type=unknown / mode=setup."""
    api = _make_api()
    await api.delete_port(0)
    api.http_send.assert_awaited_once_with("/port/0", None, "delete")


@pytest.mark.asyncio
async def test_set_port_button_assigned_is_a_partial_write() -> None:
    """The firmware accepts a partial entry — the app relies on it here."""
    api = _make_api()
    await api.set_port_button_assigned(1)
    api.http_send.assert_awaited_once_with(
        "/ports/config", [{"number": 1, "is_btn_assigned": True}], "put"
    )


@pytest.mark.asyncio
async def test_unsubscribe_socket_puts_on_the_hub() -> None:
    """The hub holds its own half of a probe->socket binding."""
    api = _make_api()
    await api.unsubscribe_socket(0)
    api.http_send.assert_awaited_once_with("/socket/0/unsubscribe", {}, "put")


@pytest.mark.asyncio
async def test_install_port_posts_type() -> None:
    """Installing is the first step of the app's port wizard."""
    api = _make_api()
    await api.install_port(1, "other")
    api.http_send.assert_awaited_once_with("/port/1/install", {"type": "other"}, "post")


@pytest.mark.asyncio
async def test_set_port_mode_puts_whole_entry_as_bare_array() -> None:
    """The hub expects a bare array carrying the complete port entry.

    A partial ``[{"number": n, "mode": m}]`` is what the power center accepts;
    here the app resends `type`, `enabled`, `power_on_percent`,
    `power_detector_enabled` and `is_btn_assigned` every time, so we do too.
    """
    api = _make_api()
    await api.set_port_mode(0, "schedule")
    api.http_send.assert_awaited_once_with(
        "/ports/config",
        [
            {
                "number": 0,
                "mode": "schedule",
                "name": "t1",
                "type": "other",
                "enabled": True,
                "power_on_percent": 80,
                "power_detector_enabled": False,
                "is_btn_assigned": True,
            }
        ],
        "put",
    )


@pytest.mark.asyncio
async def test_set_port_mode_includes_name_when_renaming() -> None:
    """An explicit name overrides the cached one."""
    api = _make_api()
    await api.set_port_mode(0, "off", name="Pompe ATO")
    sent = api.http_send.await_args.args[1]
    assert sent[0]["name"] == "Pompe ATO"
    assert sent[0]["mode"] == "off"


@pytest.mark.asyncio
async def test_set_port_mode_refreshes_cache_so_rename_is_not_reverted() -> None:
    """After a rename, a later mode change must not resend the stale name.

    `/ports/config` is a config source and is not re-fetched on every data
    refresh, so the write updates the cached entry in place.
    """
    api = _make_api()
    await api.set_port_mode(0, "off", name="Refuge")
    await api.set_port_mode(0, "on")
    sent = api.http_send.await_args.args[1]
    assert sent[0]["name"] == "Refuge"


@pytest.mark.asyncio
async def test_set_port_schedule_puts_intervals() -> None:
    """Schedules use the same {"time", "duration"} shape as the power center."""
    api = _make_api()
    intervals = [{"time": 0, "duration": 720}]
    await api.set_port_schedule(0, intervals)
    api.http_send.assert_awaited_once_with(
        "/port/0/schedule", {"intervals": intervals}, "put"
    )


@pytest.mark.asyncio
async def test_setup_finish_posts() -> None:
    api = _make_api()
    await api.setup_finish()
    api.http_send.assert_awaited_once_with("/setup-finish", {}, "post")


@pytest.mark.asyncio
async def test_power_discover_scan_and_pair() -> None:
    """The app always scans (pair=False) before confirming (pair=True); only
    the latter actually commits the link.
    """
    api = _make_api()
    await api.power_discover()  # default: scan only
    api.http_send.assert_awaited_once_with("/power/discover", {"pair": False}, "post")

    await api.power_discover(pair=True)
    api.http_send.assert_awaited_with("/power/discover", {"pair": True}, "post")


@pytest.mark.asyncio
async def test_power_unpair_posts() -> None:
    api = _make_api()
    await api.power_unpair()
    api.http_send.assert_awaited_once_with("/power/unpair", {}, "post")


# ===========================================================================
# ReefControlCoordinator delegating methods
# ===========================================================================


def _make_coordinator() -> Any:
    """Build a ReefControlCoordinator without running __init__.

    The delegating methods only touch ``self.my_api`` and
    ``self.async_request_refresh``, so we bypass the network-touching
    constructor and wire those two attributes directly.
    """
    from custom_components.redsea.coordinator import ReefControlCoordinator

    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = MagicMock(
        install_port=AsyncMock(),
        delete_port=AsyncMock(),
        unsubscribe_socket=AsyncMock(),
        set_port_button_assigned=AsyncMock(),
        set_port_mode=AsyncMock(),
        set_port_schedule=AsyncMock(),
        setup_finish=AsyncMock(),
        power_discover=AsyncMock(),
        power_unpair=AsyncMock(),
    )
    coord.async_request_refresh = AsyncMock()  # type: ignore[method-assign]
    return coord


@pytest.mark.asyncio
async def test_coordinator_set_port_schedule_delegates_and_refreshes() -> None:
    coord = _make_coordinator()
    intervals = [{"time": 0, "duration": 1439}]
    await coord.set_port_schedule(0, intervals)
    coord.my_api.set_port_schedule.assert_awaited_once_with(0, intervals)
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_setup_finish_delegates_and_refreshes() -> None:
    coord = _make_coordinator()
    await coord.setup_finish()
    coord.my_api.setup_finish.assert_awaited_once()
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_pair_power_delegates_and_refreshes() -> None:
    coord = _make_coordinator()
    await coord.pair_power()
    coord.my_api.power_discover.assert_awaited_once_with(pair=True)
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_unpair_power_delegates_and_refreshes() -> None:
    coord = _make_coordinator()
    await coord.unpair_power()
    coord.my_api.power_unpair.assert_awaited_once()
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_delete_port_hands_button_to_remaining_port() -> None:
    """After deleting a port, the physical button goes to the other one."""
    coord = _make_coordinator()
    coord.port_count = 2
    coord.my_api.port_is_installed = MagicMock(side_effect=lambda n: n == 1)
    await coord.delete_port(0)
    coord.my_api.delete_port.assert_awaited_once_with(0)
    coord.my_api.set_port_button_assigned.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_coordinator_delete_port_skips_handover_on_lite() -> None:
    """A single-port RSCONTROLLITE has nothing to hand the button over to."""
    coord = _make_coordinator()
    coord.port_count = 1
    coord.my_api.port_is_installed = MagicMock(return_value=False)
    await coord.delete_port(0)
    coord.my_api.delete_port.assert_awaited_once_with(0)
    coord.my_api.set_port_button_assigned.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_set_port_name_keeps_current_mode() -> None:
    """Renaming resends the port's current mode from the cached entry."""
    coord = _make_coordinator()
    coord.my_api.port_config = MagicMock(return_value=dict(_PORT0_CONFIG))
    await coord.set_port_name(0, "Refuge")
    coord.my_api.set_port_mode.assert_awaited_once_with(0, "off", name="Refuge")
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_set_port_name_falls_back_to_off_without_cache() -> None:
    """With no cached entry there is no mode to preserve, so use 'off'."""
    coord = _make_coordinator()
    coord.my_api.port_config = MagicMock(return_value=None)
    await coord.set_port_name(0, "S1")
    coord.my_api.set_port_mode.assert_awaited_once_with(0, "off", name="S1")


# ===========================================================================
# Per-port name text entity
# ===========================================================================


@pytest.mark.asyncio
async def test_text_set_value_calls_set_port_name() -> None:
    device = FakeControlCoordinator()
    desc = text_platform.ReefControlPortNameTextEntityDescription(
        key="port_0_name",
        translation_key="port_name",
        translation_placeholders={"port": "1"},
        value_name=(
            "$.sources[?(@.name=='/dashboard')].data.ports[?(@.number==0)].name"
        ),
        port=0,
    )
    entity = text_platform.ReefControlPortNameTextEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]
    await entity.async_set_value("Refuge")
    assert device.name_calls == [(0, "Refuge")]
    assert entity.native_value == "Refuge"


@pytest.mark.asyncio
async def test_setup_entry_creates_one_name_text_per_port(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _ControlDevice(FakeControlCoordinator):
        pass

    monkeypatch.setattr(
        text_platform, "ReefControlCoordinator", _ControlDevice, raising=True
    )

    device = _ControlDevice(port_count=1)
    device.hass = hass
    entry = MockConfigEntry(domain=DOMAIN, title="ctrl-lite", unique_id="ctrl-lite")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []

    def _add(new: Any, _update: bool = False) -> None:
        added.extend(list(new))

    await text_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    name_keys = {e.entity_description.key for e in added}
    assert name_keys == {"port_0_name"}


# ===========================================================================
# RSPOWER socket deletion (the mirror of the hub's port deletion)
# ===========================================================================


def _make_power_api() -> Any:
    """Build a ReefPowerAPI with a stub session and a recording http_send."""
    from custom_components.redsea.reefbeat.power import ReefPowerAPI

    api = ReefPowerAPI("10.0.0.8", False, cast(Any, MagicMock(name="session")))
    api.http_send = AsyncMock(return_value={"ok": True})  # type: ignore[method-assign]
    return api


@pytest.mark.asyncio
async def test_delete_socket_sends_delete_on_config() -> None:
    """Sockets are deleted on `/socket/<n>/config`, not `/socket/<n>`.

    The hub uses the bare `/port/<n>` path; the power center does not.
    """
    api = _make_power_api()
    await api.delete_socket(0)
    api.http_send.assert_awaited_once_with("/socket/0/config", None, "delete")


@pytest.mark.asyncio
async def test_unsubscribe_sockets_takes_a_list() -> None:
    api = _make_power_api()
    await api.unsubscribe_sockets([0])
    api.http_send.assert_awaited_once_with("/unsubscribe", {"sockets": [0]}, "put")


@pytest.mark.asyncio
async def test_power_coordinator_delete_socket_also_unsubscribes() -> None:
    """A binding must not outlive the socket it belonged to."""
    from custom_components.redsea.coordinator import ReefPowerCoordinator

    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = MagicMock(
        delete_socket=AsyncMock(),
        unsubscribe_sockets=AsyncMock(),
    )
    coord.async_request_refresh = AsyncMock()  # type: ignore[method-assign]
    await coord.delete_socket(2)
    coord.my_api.delete_socket.assert_awaited_once_with(2)
    coord.my_api.unsubscribe_sockets.assert_awaited_once_with([2])
    coord.async_request_refresh.assert_awaited_once_with(config=True)


def test_text_unavailable_when_port_not_installed() -> None:
    """The name field follows the same gate as the mode select."""
    device = FakeControlCoordinator(installed_ports=set())
    desc = text_platform.ReefControlPortNameTextEntityDescription(
        key="port_0_name",
        translation_key="port_name",
        translation_placeholders={"port": "1"},
        value_name=(
            "$.sources[?(@.name=='/dashboard')].data.ports[?(@.number==0)].name"
        ),
        port=0,
    )
    entity = text_platform.ReefControlPortNameTextEntity(cast(Any, device), desc)
    assert entity.available is False
    device.installed_ports.add(0)
    assert entity.available is True


# ===========================================================================
# Coverage top-up: fallback paths and thin delegates
# ===========================================================================


def test_port_is_installed_false_when_port_absent_everywhere() -> None:
    """Neither `/ports/config` nor `/dashboard` knows this port number.

    Exercised by a RSCONTROLLITE (a single port) if anything ever asks about
    port 1, and by any device whose config sources have not been fetched yet.
    """
    api = _make_api()
    assert api.port_is_installed(9) is False


def test_port_is_installed_falls_back_to_dashboard() -> None:
    """`/ports/config` is a config source and may lag behind `/dashboard`.

    `/dashboard` also carries the port `type`, so it is used as a fallback
    rather than reporting a freshly installed port as uninstalled.
    """
    api = _make_api()
    for source in api.data["sources"]:
        if source["name"] == "/ports/config":
            source["data"] = []
        elif source["name"] == "/dashboard":
            source["data"] = {"ports": [{"number": 0, "type": "other"}]}
    assert api.port_is_installed(0) is True
    assert api.port_is_installed(1) is False


def test_coordinator_port_is_installed_delegates_to_api() -> None:
    coord = _make_coordinator()
    coord.my_api.port_is_installed = MagicMock(return_value=True)
    assert coord.port_is_installed(1) is True
    coord.my_api.port_is_installed.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_coordinator_unsubscribe_socket_delegates_and_refreshes() -> None:
    """The hub half of a probe->socket binding, cleared from the hub's entry."""
    coord = _make_coordinator()
    await coord.unsubscribe_socket(3)
    coord.my_api.unsubscribe_socket.assert_awaited_once_with(3)
    coord.async_request_refresh.assert_awaited_once_with(config=True)
