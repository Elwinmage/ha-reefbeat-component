"""Tests for the ATO module (Red Sea ATO kit) of the RSCONTROL hub.

The module sits on one of the hub's 12V ports (a port of type ``ato``) and is
driven through ``/ato/*``. This covers everything behind its entities (which
are tested in test_control_ato_port_unit.py):

- ``ReefControlAPI``: locating the module, polling ``/ato/configuration``
  only while it is installed, the optimistic updates of its writes, the
  install sequence and the setters;
- ``ReefControlCoordinator``: the read helpers, the install, the setters,
  and following the module across ports (purge / reload);
- the options flow's "install the ATO module" step and its menu entry;
- the purge of a stale module's entities at setup.

The API is the real one, with only the network boundary (``_http_send`` and
``fetch_config``) mocked, so a write goes through ``http_send`` and its
optimistic update as it does in production.
"""

from __future__ import annotations

import logging
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea as integration
from custom_components.redsea import config_flow
from custom_components.redsea.const import (
    CONFIG_FLOW_ATO_AUTO_FILL,
    CONFIG_FLOW_ATO_HOSE_HEIGHT,
    CONFIG_FLOW_ATO_HOSE_LENGTH,
    CONFIG_FLOW_ATO_PORT,
    CONFIG_FLOW_ATO_PROBE,
    CONFIG_FLOW_ATO_VOLUME,
    CONFIG_FLOW_ATO_VOLUME_MONITOR,
    CONFIG_FLOW_HW_MODEL,
    DOMAIN,
    OPTIONS_MENU_INSTALL_ATO,
)
from custom_components.redsea.coordinator import (
    ReefBeatCoordinator,
    ReefControlCoordinator,
)
from custom_components.redsea.reefbeat.api import ReefBeatAPI
from custom_components.redsea.reefbeat.control import ReefControlAPI

BASE = "http://10.0.0.7"
ATO_UID = "0xA70"
PORTS_PATH = "$.sources[?(@.name=='/dashboard')].data.ports"


# ---------------------------------------------------------------------------
# Payloads, shaped as the hub reports them
# ---------------------------------------------------------------------------


def _plain_port(number: int, ptype: str = "other") -> dict[str, Any]:
    """A `/dashboard` port without the module (``unknown``: not installed)."""
    return {
        "number": number,
        "type": ptype,
        "mode": "off" if ptype == "other" else "setup",
        "user_config_mode": "off" if ptype == "other" else "setup",
        "name": f"S{number + 1}",
        "state": "off",
    }


def _ato_port(number: int, **fields: Any) -> dict[str, Any]:
    """The `/dashboard` port holding the ATO module."""
    return {
        "number": number,
        "type": "ato",
        "mode": "auto",
        "user_config_mode": "auto",
        "name": "ATO Module",
        "uid": ATO_UID,
        "auto_fill": True,
        "temp_log_enabled": True,
        "volume_left": 15000,
        "is_pump_on": True,
        **fields,
    }


def _port_config(number: int, ptype: str) -> dict[str, Any]:
    return {
        "number": number,
        "type": ptype,
        "mode": "auto" if ptype != "unknown" else "setup",
        "name": f"S{number + 1}",
        "is_btn_assigned": number == 0,
    }


_ATO_CONFIG: dict[str, Any] = {
    "port_index": 1,
    "auto_fill": True,
    "rvm_enabled": True,
    "notify": True,
    "volume_left": 15000,
    "hose": {"length": 150, "height": 40},
    "pump_override": {"speed_override": 80, "flow_rate_override": -1},
}

_PROBES: list[dict[str, Any]] = [
    {"type": "ato", "uid": ATO_UID, "name": "ATO"},
    {"type": "temperature", "uid": "0xT1", "name": "Sump"},
]


def _set_source(api: Any, name: str, data: Any) -> None:
    for source in api.data["sources"]:
        if source["name"] == name:
            source["data"] = data
            return
    api.add_source(name, "data", data)


def _api(
    ports: list[Any] | None,
    ato_config: Any = None,
    answer: Any = None,
) -> Any:
    """A ReefControlAPI whose only fakes are the HTTP call and the re-reads.

    ``ports`` is the dashboard's port list (None: dashboard not read yet),
    ``ato_config`` the cached ``/ato/configuration`` (None: source absent),
    ``answer`` the JSON every accepted write answers.
    """
    api: Any = ReefControlAPI("10.0.0.7", False, cast(Any, MagicMock(name="session")))
    api._http_send = AsyncMock(
        return_value={"ok": True, "json": {} if answer is None else answer}
    )
    api.fetch_config = AsyncMock()
    _set_source(
        api,
        "/dashboard",
        None if ports is None else {"ports": ports, "probes": list(_PROBES)},
    )
    listed = [
        p
        for p in ports or []
        if isinstance(p, dict) and isinstance(p.get("number"), int)
    ]
    _set_source(
        api, "/ports/config", [_port_config(p["number"], p["type"]) for p in listed]
    )
    if ato_config is not None:
        api.add_source(ReefControlAPI.ATO_CONFIG, "config", ato_config)
    return api


def _source_names(api: Any) -> list[str]:
    return [s["name"] for s in api.data["sources"]]


def _sent(api: Any) -> list[Any]:
    """The requests sent, as ``call(url, payload, method)``."""
    return list(api._http_send.await_args_list)


# ===========================================================================
# ReefControlAPI — locating the module
# ===========================================================================


def test_ato_port_number_finds_the_ato_port() -> None:
    api = _api([_plain_port(0), _ato_port(1)])
    assert api.ato_port_number() == 1
    assert api.ato_dashboard() == _ato_port(1)
    assert api.dashboard_port(0) == _plain_port(0)
    # A port the dashboard does not list
    assert api.dashboard_port(5) is None


def test_ato_port_number_without_module() -> None:
    assert _api([_plain_port(0), _plain_port(1, "unknown")]).ato_port_number() is None
    # Dashboard not read yet
    unread = _api(None)
    assert unread.ato_port_number() is None
    assert unread.ato_dashboard() is None


def test_ato_port_number_ignores_malformed_entries() -> None:
    """An entry that is no object, or has no usable number, holds no module."""
    api = _api(["garbage", {"type": "ato"}, {"type": "ato", "number": "1"}])
    assert api.ato_port_number() is None


def test_ato_config_is_none_until_read() -> None:
    assert _api([_ato_port(1)]).ato_config() is None
    # Source registered, not fetched yet: its placeholder is not a config
    assert _api([_ato_port(1)], ato_config="").ato_config() is None
    assert _api([_ato_port(1)], ato_config=dict(_ATO_CONFIG)).ato_config() == (
        _ATO_CONFIG
    )


# ===========================================================================
# ReefControlAPI — /ato/configuration is polled only with a module
# ===========================================================================


def test_reconcile_ato_source_follows_the_module() -> None:
    api = _api([_plain_port(0), _ato_port(1)])
    assert ReefControlAPI.ATO_CONFIG not in _source_names(api)

    # Module there, source missing: added as a config source, and reported
    assert api._reconcile_ato_source() is True
    added = [s for s in api.data["sources"] if s["name"] == ReefControlAPI.ATO_CONFIG]
    assert len(added) == 1
    assert added[0]["type"] == "config"

    # Already there: nothing to read again, and no duplicate
    assert api._reconcile_ato_source() is False
    assert _source_names(api).count(ReefControlAPI.ATO_CONFIG) == 1

    # Module uninstalled: the source goes, so its endpoint is not polled
    api.data["sources"] = [
        {**s, "data": {"ports": [_plain_port(0), _plain_port(1, "unknown")]}}
        if s["name"] == "/dashboard"
        else s
        for s in api.data["sources"]
    ]
    api.clear_cache()
    assert api._reconcile_ato_source() is False
    assert ReefControlAPI.ATO_CONFIG not in _source_names(api)

    # No module, no source: nothing to do
    assert api._reconcile_ato_source() is False
    assert ReefControlAPI.ATO_CONFIG not in _source_names(api)


@pytest.mark.asyncio
async def test_fetch_data_reads_the_ato_config_once_added(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A module found by a refresh has its configuration read at once."""
    api = _api([_plain_port(0), _ato_port(1)])
    monkeypatch.setattr(ReefBeatAPI, "fetch_data", AsyncMock(return_value={"ok": 1}))

    assert await api.fetch_data() == {"ok": 1}
    assert ReefControlAPI.ATO_CONFIG in _source_names(api)
    api.fetch_config.assert_any_await(ReefControlAPI.ATO_CONFIG)

    # Next refresh: the source is there, it waits for the config refresh
    api.fetch_config.reset_mock()
    await api.fetch_data()
    assert call(ReefControlAPI.ATO_CONFIG) not in api.fetch_config.await_args_list


@pytest.mark.asyncio
async def test_fetch_data_without_module_does_not_read_the_ato_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api([_plain_port(0), _plain_port(1, "unknown")])
    monkeypatch.setattr(ReefBeatAPI, "fetch_data", AsyncMock(return_value={"ok": 1}))
    await api.fetch_data()
    assert ReefControlAPI.ATO_CONFIG not in _source_names(api)
    assert call(ReefControlAPI.ATO_CONFIG) not in api.fetch_config.await_args_list


# ===========================================================================
# ReefControlAPI — optimistic updates of the module's writes
# ===========================================================================


@pytest.mark.asyncio
async def test_put_config_replaces_the_cache_and_updates_the_dashboard() -> None:
    answer = {**_ATO_CONFIG, "auto_fill": False, "volume_left": 9000}
    api = _api(
        [_plain_port(0), _ato_port(1)], ato_config=dict(_ATO_CONFIG), answer=answer
    )

    result = await api.set_ato_config(
        {"auto_fill": False, "volume_left": 9000, "notify": False}
    )

    assert result == {"ok": True, "json": answer}
    # `port_index` is added, as the app always sends it
    assert _sent(api) == [
        call(
            BASE + "/ato/configuration",
            {"auto_fill": False, "volume_left": 9000, "notify": False, "port_index": 1},
            "put",
        )
    ]
    # The hub answers the whole configuration: it becomes the cached one
    assert api.ato_config() == answer
    # Fields the dashboard also carries follow; the others do not leak in
    dash = api.ato_dashboard()
    assert dash["auto_fill"] is False
    assert dash["volume_left"] == 9000
    assert dash["temp_log_enabled"] is True
    assert "notify" not in dash
    assert "port_index" not in dash


@pytest.mark.asyncio
async def test_put_config_keeps_the_cache_when_the_answer_is_no_config() -> None:
    """An answer without ``port_index`` is not the configuration."""
    api = _api([_ato_port(1)], ato_config=dict(_ATO_CONFIG), answer={"success": True})
    await api.set_ato_config({"temp_log_enabled": False})
    assert api.ato_config() == _ATO_CONFIG
    # The dashboard field is still set from what was sent
    assert api.ato_dashboard()["temp_log_enabled"] is False


@pytest.mark.asyncio
async def test_put_config_without_a_dashboard_port_only_updates_the_cache() -> None:
    """The card may write the configuration before the dashboard shows the port."""
    answer = {**_ATO_CONFIG, "auto_fill": False}
    api = _api([_plain_port(0)], ato_config=dict(_ATO_CONFIG), answer=answer)
    await api.http_send("/ato/configuration", {"auto_fill": False}, "put")
    assert api.ato_config() == answer
    assert api.dashboard_port(0) == _plain_port(0)


@pytest.mark.asyncio
async def test_update_volume_sets_the_volume_left() -> None:
    api = _api([_ato_port(1)])
    await api.update_ato_volume(12345.6)
    assert _sent(api) == [call(BASE + "/ato/update-volume", {"volume": 12346}, "post")]
    assert api.ato_dashboard()["volume_left"] == 12346


@pytest.mark.asyncio
@pytest.mark.parametrize("volume", ["full", None, True])
async def test_update_volume_ignores_a_volume_that_is_no_number(volume: Any) -> None:
    """What the card posts through ``redsea.request`` is not validated here."""
    api = _api([_ato_port(1)])
    await api.http_send("/ato/update-volume", {"volume": volume}, "post")
    assert api.ato_dashboard()["volume_left"] == 15000


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ReefControlAPI.ATO_FAULT_MODES)
async def test_resume_gives_a_faulty_port_its_configured_mode(fault: str) -> None:
    api = _api([_ato_port(1, mode=fault, user_config_mode="auto")])
    await api.ato_resume()
    assert _sent(api) == [call(BASE + "/ato/resume", {}, "post")]
    assert api.ato_dashboard()["mode"] == "auto"


@pytest.mark.asyncio
async def test_resume_defaults_to_auto_and_leaves_a_healthy_port_alone() -> None:
    # No configured mode reported: auto
    port = _ato_port(1, mode="empty")
    del port["user_config_mode"]
    api = _api([port])
    await api.ato_resume()
    assert api.ato_dashboard()["mode"] == "auto"

    # Not in fault: the mode is not touched
    api = _api([_ato_port(1, mode="off", user_config_mode="auto")])
    await api.ato_resume()
    assert api.ato_dashboard()["mode"] == "off"


@pytest.mark.asyncio
async def test_stop_and_manual_pump() -> None:
    api = _api([_ato_port(1, is_pump_on=True)])
    await api.ato_stop()
    assert api.ato_dashboard()["is_pump_on"] is False

    # A manual fill is only requested: the hub reports when the pump runs
    before = dict(api.ato_dashboard())
    await api.ato_manual_pump()
    assert api.ato_dashboard() == before
    assert _sent(api) == [
        call(BASE + "/ato/stop", {}, "post"),
        call(BASE + "/ato/manual-pump", {}, "post"),
    ]


@pytest.mark.asyncio
async def test_ato_writes_without_module_leave_the_dashboard_alone() -> None:
    ports = [_plain_port(0), _plain_port(1, "unknown")]
    api = _api([dict(p) for p in ports])
    await api.ato_stop()
    await api.ato_resume()
    await api.update_ato_volume(500)
    assert [api.dashboard_port(0), api.dashboard_port(1)] == ports


@pytest.mark.asyncio
async def test_a_refused_ato_write_is_not_mirrored() -> None:
    api = _api([_ato_port(1, is_pump_on=True)], ato_config=dict(_ATO_CONFIG))
    api._http_send = AsyncMock(return_value={"ok": False, "json": {"port_index": 0}})
    assert await api.ato_stop() == {"ok": False, "json": {"port_index": 0}}
    await api.set_ato_config({"auto_fill": False})
    assert api.ato_dashboard() == _ato_port(1, is_pump_on=True)
    assert api.ato_config() == _ATO_CONFIG


@pytest.mark.asyncio
async def test_installing_a_port_as_ato_shows_the_module_at_once() -> None:
    """``POST /port/<n>/install`` with type ``ato``: the port becomes the module."""
    api = _api([_plain_port(0), _plain_port(1, "unknown")])
    await api.http_send("/port/1/install", {"uid": ATO_UID, "type": "ato"}, "post")

    dash = api.dashboard_port(1)
    assert dash["type"] == "ato"
    assert dash["uid"] == ATO_UID
    # The on/off state of a plain port means nothing for the module
    assert "state" not in dash
    assert api.port_config(1)["type"] == "ato"
    assert api.ato_port_number() == 1
    # The other port is untouched
    assert api.dashboard_port(0) == _plain_port(0)


@pytest.mark.asyncio
async def test_installing_a_plain_port_keeps_its_state_and_has_no_uid() -> None:
    api = _api([_plain_port(0), _plain_port(1, "unknown")])
    await api.http_send("/port/1/install", {"type": "other"}, "post")
    dash = api.dashboard_port(1)
    assert dash["type"] == "other"
    assert dash["state"] == "off"
    assert "uid" not in dash


@pytest.mark.asyncio
async def test_installing_ato_on_a_port_the_dashboard_does_not_list() -> None:
    """Only `/ports/config` knows the port: nothing to set on the dashboard."""
    api = _api([_plain_port(0)])
    _set_source(
        api, "/ports/config", [_port_config(0, "other"), _port_config(1, "unknown")]
    )
    api.clear_cache()
    await api.http_send("/port/1/install", {"uid": ATO_UID, "type": "ato"}, "post")
    assert api.port_config(1)["type"] == "ato"
    assert api.dashboard_port(1) is None
    assert api.dashboard_port(0) == _plain_port(0)


# ===========================================================================
# ReefControlAPI — installing the module
# ===========================================================================


@pytest.mark.asyncio
async def test_install_ato_port_sends_the_app_sequence() -> None:
    api = _api([_plain_port(0), _plain_port(1, "unknown")], answer=dict(_ATO_CONFIG))

    result = await api.install_ato_port(1, ATO_UID, 20000, 150, 40)

    assert result is not None
    assert result["ok"] is True
    assert _sent(api) == [
        call(BASE + "/port/1/install", {"uid": ATO_UID, "type": "ato"}, "post"),
        call(BASE + "/ato/update-volume", {"volume": 20000}, "post"),
        call(
            BASE + "/ato/configuration",
            {
                "volume_left": 20000,
                "port_index": 1,
                "hose": {"length": 150, "height": 40},
                "auto_fill": True,
                "notify": True,
                "rvm_enabled": True,
            },
            "put",
        ),
        # The module's port gets its name and the hub's button, taken from
        # the other port
        call(
            BASE + "/ports/config",
            [
                {
                    "number": 1,
                    "name": "ATO Module",
                    "type": "ato",
                    "is_btn_assigned": True,
                },
                {"number": 0, "is_btn_assigned": False},
            ],
            "put",
        ),
    ]
    # The module is polled from now on, and read back at once
    assert ReefControlAPI.ATO_CONFIG in _source_names(api)
    assert api.fetch_config.await_args_list == [
        call(ReefControlAPI.ATO_CONFIG),
        call("/ports/config"),
    ]
    # Optimistic: the port shows as the module before any read-back
    assert api.ato_port_number() == 1
    assert api.port_config(1)["name"] == "ATO Module"
    assert api.port_config(1)["is_btn_assigned"] is True
    assert api.port_config(0)["is_btn_assigned"] is False


@pytest.mark.asyncio
async def test_install_ato_port_without_volume_monitoring() -> None:
    """No reservoir volume is declared when it is not monitored."""
    api = _api([_plain_port(0, "unknown")])
    await api.install_ato_port(
        0,
        ATO_UID,
        20000,
        100,
        0,
        auto_fill=False,
        volume_monitor=False,
        notify=False,
        port_count=1,
    )
    sent = _sent(api)
    assert [c.args[0] for c in sent] == [
        BASE + "/port/0/install",
        BASE + "/ato/configuration",
        BASE + "/ports/config",
    ]
    assert sent[1].args[1] == {
        "volume_left": 20000,
        "port_index": 0,
        "hose": {"length": 100, "height": 0},
        "auto_fill": False,
        "notify": False,
        "rvm_enabled": False,
    }
    # A Lite hub has a single port: no other port to take the button from
    assert sent[2].args[1] == [
        {"number": 0, "name": "ATO Module", "type": "ato", "is_btn_assigned": True}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("refusal", [None, {"ok": False, "status": 503}])
async def test_install_ato_port_stops_when_the_install_is_refused(
    refusal: Any,
) -> None:
    api = _api([_plain_port(0), _plain_port(1, "unknown")])
    api._http_send = AsyncMock(return_value=refusal)

    assert await api.install_ato_port(1, ATO_UID, 20000, 150, 40) == refusal

    assert len(_sent(api)) == 1
    api.fetch_config.assert_not_awaited()
    assert ReefControlAPI.ATO_CONFIG not in _source_names(api)
    assert api.ato_port_number() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("refusal", [None, {"ok": False, "status": 400}])
async def test_install_ato_port_stops_when_the_configuration_is_refused(
    refusal: Any,
) -> None:
    api = _api([_plain_port(0), _plain_port(1, "unknown")])
    accepted = {"ok": True, "json": {}}
    api._http_send = AsyncMock(side_effect=[accepted, accepted, refusal])

    assert await api.install_ato_port(1, ATO_UID, 20000, 150, 40) == refusal

    # Install, volume, configuration — the ports are not renamed
    assert [c.args[0] for c in _sent(api)] == [
        BASE + "/port/1/install",
        BASE + "/ato/update-volume",
        BASE + "/ato/configuration",
    ]
    api.fetch_config.assert_not_awaited()


# ===========================================================================
# ReefControlAPI — settings
# ===========================================================================


@pytest.mark.asyncio
async def test_set_ato_config_without_module_sends_nothing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    api = _api([_plain_port(0)])
    with caplog.at_level(logging.WARNING):
        assert await api.set_ato_config({"auto_fill": False}) is None
    api._http_send.assert_not_awaited()
    assert "No ATO module installed" in caplog.text


@pytest.mark.asyncio
async def test_set_ato_hose_resends_the_other_dimension() -> None:
    api = _api([_ato_port(1)], ato_config=dict(_ATO_CONFIG))
    await api.set_ato_hose(length_cm=200)
    await api.set_ato_hose(height_cm=0)
    await api.set_ato_hose(length_cm=300, height_cm=120)
    assert [c.args[1] for c in _sent(api)] == [
        {"hose": {"length": 200, "height": 40}, "port_index": 1},
        # 0 is a height (pump level with the tank), not "unchanged"
        {"hose": {"length": 150, "height": 0}, "port_index": 1},
        {"hose": {"length": 300, "height": 120}, "port_index": 1},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("config", [None, "", {"hose": None}, {"hose": {}}])
async def test_set_ato_hose_without_a_cached_hose_falls_back_to_zero(
    config: Any,
) -> None:
    api = _api([_ato_port(1)], ato_config=config)
    await api.set_ato_hose(length_cm=200)
    assert _sent(api)[0].args[1] == {
        "hose": {"length": 200, "height": 0},
        "port_index": 1,
    }


@pytest.mark.asyncio
async def test_set_ato_flow_rate_keeps_the_speed_override() -> None:
    api = _api([_ato_port(1)], ato_config=dict(_ATO_CONFIG))
    await api.set_ato_flow_rate(1500.4)
    # 0 or less: back to the pump's default
    await api.set_ato_flow_rate(0)
    await api.set_ato_flow_rate(-5)
    assert [c.args[1] for c in _sent(api)] == [
        {
            "pump_override": {"speed_override": 80, "flow_rate_override": 1500},
            "port_index": 1,
        },
        {
            "pump_override": {"speed_override": 80, "flow_rate_override": -1},
            "port_index": 1,
        },
        {
            "pump_override": {"speed_override": 80, "flow_rate_override": -1},
            "port_index": 1,
        },
    ]
    assert all(c.args[0] == BASE + "/ato/configuration" for c in _sent(api))
    assert all(c.args[2] == "put" for c in _sent(api))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config",
    [
        None,
        {"pump_override": None},
        {"pump_override": {}},
        {"pump_override": {"speed_override": "fast"}},
        {"pump_override": {"speed_override": True}},
    ],
)
async def test_set_ato_flow_rate_without_a_usable_speed_override(config: Any) -> None:
    api = _api([_ato_port(1)], ato_config=config)
    await api.set_ato_flow_rate(800)
    assert _sent(api)[0].args[1] == {
        "pump_override": {"speed_override": 0, "flow_rate_override": 800},
        "port_index": 1,
    }


# ===========================================================================
# ReefControlCoordinator
# ===========================================================================


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="CTL123",
        data={CONFIG_FLOW_HW_MODEL: "RSCONTROLPRO"},
        options={},
        unique_id="ctl-ato",
    )
    entry.add_to_hass(hass)
    return entry


def _coordinator(
    api: Any, hass: Any = None, entry: Any = None, port_count: int = 2
) -> Any:
    """A ReefControlCoordinator on ``api``, built without network I/O."""
    coord: Any = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = api
    coord._title = "CTL123"  # `serial` returns the title
    coord.port_count = port_count
    coord._hass = hass if hass is not None else MagicMock()
    coord._entry = entry if entry is not None else MagicMock(entry_id="entry-ato")
    coord.async_request_refresh = AsyncMock()
    coord.async_update_listeners = MagicMock()
    return coord


def test_coordinator_ato_read_helpers() -> None:
    api = _api(
        [_plain_port(0), _ato_port(1, today_volume=120)],
        ato_config=dict(_ATO_CONFIG),
    )
    coord = _coordinator(api)

    assert coord.ato_port_number() == 1
    assert coord.ato_is_port(1) is True
    assert coord.ato_is_port(0) is False

    assert coord.ato_config() == _ATO_CONFIG
    assert coord.ato_config_value("auto_fill") is True
    assert coord.ato_config_value("hose", "length") == 150
    # Absent, or a path through something that is no object
    assert coord.ato_config_value("missing") is None
    assert coord.ato_config_value("hose", "length", "unit") is None
    assert coord.ato_config_value("missing", "deeper") is None

    assert coord.ato_port_value(1, "today_volume") == 120
    assert coord.ato_port_value(1, "missing") is None
    # Another port never shows the module's values, even a field it has
    assert coord.ato_port_value(0, "name") is None


def test_coordinator_ato_read_helpers_without_module() -> None:
    coord = _coordinator(_api([_plain_port(0)]))
    assert coord.ato_port_number() is None
    assert coord.ato_is_port(0) is False
    assert coord.ato_config() is None
    assert coord.ato_config_value("auto_fill") is None
    assert coord.ato_port_value(0, "mode") is None
    assert coord.ato_status(0) is None


@pytest.mark.parametrize(
    ("mode", "status"),
    [
        ("auto", "ok"),
        ("off", "ok"),
        *[(fault, fault) for fault in ReefControlAPI.ATO_FAULT_MODES],
    ],
)
def test_coordinator_ato_status(mode: str, status: str) -> None:
    coord = _coordinator(_api([_plain_port(0), _ato_port(1, mode=mode)]))
    assert coord.ato_status(1) == status
    assert coord.ato_status(0) is None


def test_coordinator_ato_status_without_a_reported_mode() -> None:
    port = _ato_port(1)
    del port["mode"]
    assert _coordinator(_api([port])).ato_status(1) is None


def test_coordinator_ato_probes_and_free_ports() -> None:
    coord = _coordinator(_api([_plain_port(0), _plain_port(1, "unknown")]))
    # Only the ATO probes, without their type
    assert coord.ato_probes() == [{"uid": ATO_UID, "name": "ATO"}]
    # Port 0 is installed (a plain device): only port 1 can take the module
    assert coord.ato_free_ports() == [1]

    lite = _coordinator(_api([_plain_port(0, "unknown")]), port_count=1)
    assert lite.ato_free_ports() == [0]

    full = _coordinator(_api([_plain_port(0), _ato_port(1)]))
    assert full.ato_free_ports() == []


@pytest.mark.asyncio
async def test_coordinator_install_ato_port_accepted() -> None:
    api = _api([_plain_port(0), _plain_port(1, "unknown")], answer=dict(_ATO_CONFIG))
    coord = _coordinator(api)

    ok = await coord.async_install_ato_port(
        1, ATO_UID, 20000, 150, 40, auto_fill=False, volume_monitor=False
    )

    assert ok is True
    sent = _sent(api)
    assert [c.args[0] for c in sent] == [
        BASE + "/port/1/install",
        BASE + "/ato/configuration",
        BASE + "/ports/config",
    ]
    assert sent[1].args[1]["auto_fill"] is False
    assert sent[1].args[1]["rvm_enabled"] is False
    # The hub's port count decides which ports give the button away
    assert sent[2].args[1][1:] == [{"number": 0, "is_btn_assigned": False}]
    # Remembered, so the tracking does not reload on top of the caller
    assert coord._ato_port_seen == 1
    coord.async_update_listeners.assert_called_once()
    coord.async_request_refresh.assert_awaited_once_with(config=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("refusal", [None, {"ok": False}])
async def test_coordinator_install_ato_port_refused(refusal: Any) -> None:
    api = _api([_plain_port(0), _plain_port(1, "unknown")])
    api._http_send = AsyncMock(return_value=refusal)
    coord = _coordinator(api)

    assert await coord.async_install_ato_port(1, ATO_UID, 20000, 150, 40) is False

    # Nothing was installed: the tracking keeps what it knew
    assert not hasattr(coord, "_ato_port_seen")
    # Still refreshed, to show what the hub really holds
    coord.async_update_listeners.assert_called_once()
    coord.async_request_refresh.assert_awaited_once_with(config=True)


@pytest.mark.asyncio
async def test_coordinator_ato_setters_write_then_refresh() -> None:
    api = _api([_plain_port(0), _ato_port(1)], ato_config=dict(_ATO_CONFIG))
    coord = _coordinator(api)

    await coord.async_set_ato_config({"auto_fill": False})
    await coord.async_set_ato_hose(length_cm=200)
    await coord.async_set_ato_hose(height_cm=10)
    # L/min on the entity, mL/min on the wire
    await coord.async_set_ato_flow_rate(1.5)
    await coord.async_update_ato_volume(7000)
    await coord.async_ato_resume()
    await coord.async_ato_manual_pump()
    await coord.async_ato_stop()

    assert [
        (c.args[0].removeprefix(BASE), c.args[1], c.args[2]) for c in _sent(api)
    ] == [
        ("/ato/configuration", {"auto_fill": False, "port_index": 1}, "put"),
        (
            "/ato/configuration",
            {"hose": {"length": 200, "height": 40}, "port_index": 1},
            "put",
        ),
        (
            "/ato/configuration",
            {"hose": {"length": 150, "height": 10}, "port_index": 1},
            "put",
        ),
        (
            "/ato/configuration",
            {
                "pump_override": {"speed_override": 80, "flow_rate_override": 1500},
                "port_index": 1,
            },
            "put",
        ),
        ("/ato/update-volume", {"volume": 7000}, "post"),
        ("/ato/resume", {}, "post"),
        ("/ato/manual-pump", {}, "post"),
        ("/ato/stop", {}, "post"),
    ]
    # Each write shows its optimistic outcome, then is read back
    assert coord.async_update_listeners.call_count == 8
    assert coord.async_request_refresh.await_count == 8
    assert coord.ato_port_value(1, "volume_left") == 7000
    assert coord.ato_port_value(1, "is_pump_on") is False


# -- The module's entities follow it across ports ---------------------------


def _mk(
    reg: er.EntityRegistry, entry: MockConfigEntry, domain: str, unique_id: str
) -> str:
    ent = reg.async_get_or_create(
        domain, DOMAIN, unique_id, config_entry=cast(Any, entry)
    )
    return ent.entity_id


def _module_entities(
    reg: er.EntityRegistry, entry: MockConfigEntry, port: int
) -> list[str]:
    """Registry entries of the module's entities on a port (real keys)."""
    return [
        _mk(reg, entry, "sensor", f"CTL123_port_{port}_ato_status"),
        _mk(reg, entry, "sensor", f"CTL123_port_{port}_today_volume"),
        _mk(reg, entry, "sensor", f"CTL123_port_{port}_volume_left"),
        _mk(reg, entry, "sensor", f"CTL123_port_{port}_last_pump_on_cause"),
        _mk(reg, entry, "binary_sensor", f"CTL123_port_{port}_is_pump_on"),
        _mk(reg, entry, "binary_sensor", f"CTL123_port_{port}_ato_fault"),
        _mk(reg, entry, "button", f"CTL123_port_{port}_ato_manual_pump"),
        _mk(reg, entry, "number", f"CTL123_port_{port}_ato_hose_length"),
        _mk(reg, entry, "switch", f"CTL123_port_{port}_ato_auto_fill"),
    ]


def _present(reg: er.EntityRegistry, entity_ids: list[str]) -> list[bool]:
    return [reg.async_get(e) is not None for e in entity_ids]


@pytest.mark.asyncio
async def test_purge_ato_entities_removes_only_the_module_entities(
    hass: HomeAssistant,
) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)
    on_port_0 = _module_entities(reg, entry, 0)
    on_port_1 = _module_entities(reg, entry, 1)
    kept = [
        # The port's own entities are not the module's
        _mk(reg, entry, "text", "CTL123_port_1_name"),
        _mk(reg, entry, "switch", "CTL123_port_1_on_off"),
        _mk(reg, entry, "sensor", "CTL123_probe_ato_0xa70_value"),
        # Not this hub's serial
        _mk(reg, entry, "sensor", "OTHER_port_1_ato_status"),
    ]
    coord = _coordinator(_api([_ato_port(0)]), hass, entry)

    # The module is on port 0: only what port 1 left behind goes
    assert coord.purge_ato_entities(keep_port=0) == len(on_port_1)
    assert _present(reg, on_port_1) == [False] * len(on_port_1)
    assert _present(reg, on_port_0) == [True] * len(on_port_0)
    assert _present(reg, kept) == [True] * len(kept)

    # No module left at all
    assert coord.purge_ato_entities() == len(on_port_0)
    assert _present(reg, on_port_0) == [False] * len(on_port_0)
    assert _present(reg, kept) == [True] * len(kept)

    # Nothing left to remove
    assert coord.purge_ato_entities() == 0


def _show_ports(api: Any, ports: list[Any] | None) -> None:
    """What the next dashboard read reports."""
    _set_source(api, "/dashboard", None if ports is None else {"ports": ports})
    api.clear_cache()


@pytest.fixture
def reloads(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Entry ids a reload was scheduled for (the reload itself is not run)."""
    scheduled: list[str] = []
    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", scheduled.append)
    return scheduled


@pytest.mark.asyncio
async def test_track_ato_module_waits_for_the_ports(
    hass: HomeAssistant, reloads: list[str]
) -> None:
    """A failed dashboard read is no proof the module is gone: never purge."""
    entry = _entry(hass)
    reg = er.async_get(hass)
    entities = _module_entities(reg, entry, 1)
    api = _api(None)
    coord = _coordinator(api, hass, entry)

    coord._track_ato_module()
    assert not hasattr(coord, "_ato_port_seen")

    # Known, then unreadable: what was seen is kept, nothing is purged
    _show_ports(api, [_plain_port(0), _ato_port(1)])
    coord._track_ato_module()
    assert coord._ato_port_seen == 1
    _show_ports(api, None)
    coord._track_ato_module()
    assert coord._ato_port_seen == 1
    assert _present(reg, entities) == [True] * len(entities)
    assert reloads == []


@pytest.mark.asyncio
async def test_track_ato_module_first_read_only_records(
    hass: HomeAssistant, reloads: list[str]
) -> None:
    """At startup the entities were just built at setup: nothing to do."""
    entry = _entry(hass)
    reg = er.async_get(hass)
    entities = _module_entities(reg, entry, 1)
    coord = _coordinator(_api([_plain_port(0), _ato_port(1)]), hass, entry)

    coord._track_ato_module()
    assert coord._ato_port_seen == 1
    # Unchanged at the next refresh
    coord._track_ato_module()

    assert _present(reg, entities) == [True] * len(entities)
    assert reloads == []


@pytest.mark.asyncio
async def test_track_ato_module_first_read_without_module(
    hass: HomeAssistant, reloads: list[str]
) -> None:
    """No module is a state of its own (None), distinct from "not read"."""
    entry = _entry(hass)
    coord = _coordinator(_api([_plain_port(0)]), hass, entry)
    coord._track_ato_module()
    assert coord._ato_port_seen is None
    assert reloads == []


@pytest.mark.asyncio
async def test_track_ato_module_uninstalled_removes_its_entities(
    hass: HomeAssistant, reloads: list[str]
) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)
    entities = _module_entities(reg, entry, 1)
    port_name = _mk(reg, entry, "text", "CTL123_port_1_name")
    api = _api([_plain_port(0), _ato_port(1)])
    coord = _coordinator(api, hass, entry)
    coord._track_ato_module()

    # Uninstalled from the app, the card or Home Assistant
    _show_ports(api, [_plain_port(0), _plain_port(1, "unknown")])
    coord._track_ato_module()

    assert coord._ato_port_seen is None
    assert _present(reg, entities) == [False] * len(entities)
    assert reg.async_get(port_name) is not None
    # Removing the registry entries is enough: no reload
    assert reloads == []


@pytest.mark.asyncio
async def test_track_ato_module_installed_elsewhere_reloads(
    hass: HomeAssistant, reloads: list[str]
) -> None:
    """A module installed from the app gets its entities through a reload."""
    entry = _entry(hass)
    api = _api([_plain_port(0), _plain_port(1, "unknown")])
    coord = _coordinator(api, hass, entry)
    coord._track_ato_module()
    assert reloads == []

    _show_ports(api, [_plain_port(0), _ato_port(1)])
    coord._track_ato_module()

    assert coord._ato_port_seen == 1
    assert reloads == [entry.entry_id]


@pytest.mark.asyncio
async def test_track_ato_module_moved_purges_then_reloads(
    hass: HomeAssistant, reloads: list[str]
) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)
    old = _module_entities(reg, entry, 1)
    api = _api([_plain_port(0, "unknown"), _ato_port(1)])
    coord = _coordinator(api, hass, entry)
    coord._track_ato_module()

    _show_ports(api, [_ato_port(0), _plain_port(1, "unknown")])
    coord._track_ato_module()

    assert coord._ato_port_seen == 0
    assert _present(reg, old) == [False] * len(old)
    assert reloads == [entry.entry_id]


@pytest.mark.asyncio
async def test_installing_from_home_assistant_does_not_reload_twice(
    hass: HomeAssistant, reloads: list[str]
) -> None:
    """The options flow reloads the entry itself after the install."""
    entry = _entry(hass)
    api = _api([_plain_port(0), _plain_port(1, "unknown")], answer=dict(_ATO_CONFIG))
    coord = _coordinator(api, hass, entry)
    coord._track_ato_module()

    assert await coord.async_install_ato_port(1, ATO_UID, 20000, 150, 40) is True
    coord._track_ato_module()

    assert reloads == []


@pytest.mark.asyncio
async def test_update_tracks_the_ato_module(monkeypatch: pytest.MonkeyPatch) -> None:
    data = {"sources": []}
    monkeypatch.setattr(
        ReefBeatCoordinator, "_async_update_data", AsyncMock(return_value=data)
    )
    coord = _coordinator(_api([_plain_port(0), _ato_port(1)]))
    coord._sync_calibration_maintenance = AsyncMock()

    assert await coord._async_update_data() is data
    assert coord._ato_port_seen == 1


@pytest.mark.asyncio
async def test_update_survives_a_failing_ato_tracking(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Tracking the module must never cost the hub its refresh."""
    data = {"sources": []}
    monkeypatch.setattr(
        ReefBeatCoordinator, "_async_update_data", AsyncMock(return_value=data)
    )
    coord = _coordinator(_api([_ato_port(1)]))
    coord._sync_calibration_maintenance = AsyncMock()
    coord._track_ato_module = MagicMock(side_effect=RuntimeError("registry gone"))

    with caplog.at_level(logging.DEBUG):
        assert await coord._async_update_data() is data

    coord._track_ato_module.assert_called_once()
    assert "ATO module tracking failed" in caplog.text


# ===========================================================================
# Setup — entities of a module removed while Home Assistant was stopped
# ===========================================================================


async def _setup_hub(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    entry: MockConfigEntry,
    api: Any,
) -> bool:
    coord = _coordinator(api, hass, entry)
    coord.async_setup = AsyncMock()
    monkeypatch.setattr(integration, "_build_coordinator", lambda h, e: coord)
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    monkeypatch.setattr(integration, "_migrate_head_device_names", AsyncMock())
    return await integration.async_setup_entry(hass, cast(Any, entry))


@pytest.mark.asyncio
async def test_setup_purges_the_entities_of_a_module_no_longer_there(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)
    stale = _module_entities(reg, entry, 0)
    current = _module_entities(reg, entry, 1)
    port_name = _mk(reg, entry, "text", "CTL123_port_0_name")

    # The module now sits on port 1; port 0 was reinstalled as a plain port
    api = _api([_plain_port(0), _ato_port(1)])
    assert await _setup_hub(hass, monkeypatch, entry, api) is True

    assert _present(reg, stale) == [False] * len(stale)
    assert _present(reg, current) == [True] * len(current)
    assert reg.async_get(port_name) is not None


@pytest.mark.asyncio
async def test_setup_without_module_purges_every_module_entity(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)
    stale = _module_entities(reg, entry, 1)

    api = _api([_plain_port(0), _plain_port(1, "unknown")])
    assert await _setup_hub(hass, monkeypatch, entry, api) is True

    assert _present(reg, stale) == [False] * len(stale)


@pytest.mark.asyncio
async def test_setup_keeps_the_module_entities_while_the_ports_are_unknown(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dashboard that could not be read must not wipe the module."""
    entry = _entry(hass)
    reg = er.async_get(hass)
    entities = _module_entities(reg, entry, 1)

    assert await _setup_hub(hass, monkeypatch, entry, _api(None)) is True

    assert _present(reg, entities) == [True] * len(entities)


# ===========================================================================
# Options flow — "Install the ATO module"
# ===========================================================================


def _flow(hass: HomeAssistant, coordinator: Any) -> config_flow.OptionsFlowHandler:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ctl",
        data={CONFIG_FLOW_HW_MODEL: "RSCONTROLPRO"},
        options={"keep": "me"},
        unique_id="ctl-ato-flow",
    )
    entry.add_to_hass(hass)
    if coordinator is not None:
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    flow = config_flow.OptionsFlowHandler(cast(Any, entry))
    flow.hass = hass
    flow.handler = entry.entry_id
    flow.flow_id = "test-flow"
    flow.context = {}
    return flow


def _flow_coordinator(
    probes: list[dict[str, str]] | None = None,
    ports: list[int] | None = None,
    module_port: int | None = None,
) -> Any:
    coordinator = MagicMock()
    coordinator.ato_port_number.return_value = module_port
    coordinator.ato_probes.return_value = (
        [{"uid": ATO_UID, "name": "ATO"}] if probes is None else probes
    )
    coordinator.ato_free_ports.return_value = [0, 1] if ports is None else ports
    coordinator.async_install_ato_port = AsyncMock(return_value=True)
    return coordinator


_USER_INPUT: dict[str, Any] = {
    CONFIG_FLOW_ATO_PORT: "1",
    CONFIG_FLOW_ATO_PROBE: ATO_UID,
    CONFIG_FLOW_ATO_VOLUME: 20,
    CONFIG_FLOW_ATO_HOSE_LENGTH: 150,
    CONFIG_FLOW_ATO_HOSE_HEIGHT: 40,
    CONFIG_FLOW_ATO_AUTO_FILL: True,
    CONFIG_FLOW_ATO_VOLUME_MONITOR: False,
}


@pytest.mark.asyncio
async def test_menu_offers_the_ato_install_when_it_is_possible(
    hass: HomeAssistant,
) -> None:
    res = cast(dict[str, Any], await _flow(hass, _flow_coordinator()).async_step_init())
    assert res["type"] == FlowResultType.MENU
    assert OPTIONS_MENU_INSTALL_ATO in res["menu_options"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "coordinator",
    [
        # A module is installed already (the hub has one at most)
        _flow_coordinator(module_port=0),
        # No ATO probe to drive it
        _flow_coordinator(probes=[]),
        # Every port is taken
        _flow_coordinator(ports=[]),
        # Entry not loaded
        None,
    ],
    ids=["module-installed", "no-ato-probe", "no-free-port", "not-loaded"],
)
async def test_menu_hides_the_ato_install_when_it_cannot_succeed(
    hass: HomeAssistant, coordinator: Any
) -> None:
    res = cast(dict[str, Any], await _flow(hass, coordinator).async_step_init())
    assert res["type"] == FlowResultType.MENU
    assert OPTIONS_MENU_INSTALL_ATO not in res["menu_options"]
    # The probe management entries stay
    assert "add_probe" in res["menu_options"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("coordinator", "reason"),
    [
        (None, "no_ato_probe"),
        (_flow_coordinator(probes=[]), "no_ato_probe"),
        (_flow_coordinator(ports=[]), "no_free_port"),
    ],
    ids=["not-loaded", "no-ato-probe", "no-free-port"],
)
async def test_install_ato_aborts_when_it_cannot_succeed(
    hass: HomeAssistant, coordinator: Any, reason: str
) -> None:
    res = cast(
        dict[str, Any],
        await _flow(hass, coordinator).async_step_install_ato(dict(_USER_INPUT)),
    )
    assert res["type"] == FlowResultType.ABORT
    assert res["reason"] == reason
    if coordinator is not None:
        coordinator.async_install_ato_port.assert_not_awaited()


@pytest.mark.asyncio
async def test_install_ato_form_offers_the_free_ports_and_ato_probes(
    hass: HomeAssistant,
) -> None:
    coordinator = _flow_coordinator(
        probes=[{"uid": ATO_UID, "name": "ATO"}, {"uid": "0xB2", "name": "Spare"}],
        ports=[1],
    )
    res = cast(dict[str, Any], await _flow(hass, coordinator).async_step_install_ato())

    assert res["type"] == FlowResultType.FORM
    assert res["step_id"] == "install_ato"
    assert res["errors"] == {}
    schema = res["data_schema"]
    # Defaults: the first free port and probe, 20 L, a 1 m level hose
    assert schema({}) == {
        CONFIG_FLOW_ATO_PORT: "1",
        CONFIG_FLOW_ATO_PROBE: ATO_UID,
        CONFIG_FLOW_ATO_VOLUME: 20.0,
        CONFIG_FLOW_ATO_HOSE_LENGTH: 100.0,
        CONFIG_FLOW_ATO_HOSE_HEIGHT: 0.0,
        CONFIG_FLOW_ATO_AUTO_FILL: True,
        CONFIG_FLOW_ATO_VOLUME_MONITOR: True,
    }
    assert schema({CONFIG_FLOW_ATO_PROBE: "0xB2"})[CONFIG_FLOW_ATO_PROBE] == "0xB2"
    # Port 0 is taken, and a hose shorter than 50 cm is refused
    for invalid in (
        {CONFIG_FLOW_ATO_PORT: "0"},
        {CONFIG_FLOW_ATO_PROBE: "0xNOPE"},
        {CONFIG_FLOW_ATO_HOSE_LENGTH: 10},
        {CONFIG_FLOW_ATO_HOSE_HEIGHT: 300},
        {CONFIG_FLOW_ATO_VOLUME: 501},
    ):
        with pytest.raises(Exception):
            schema(invalid)
    coordinator.async_install_ato_port.assert_not_awaited()


@pytest.mark.asyncio
async def test_install_ato_success_installs_then_reloads(
    hass: HomeAssistant, reloads: list[str]
) -> None:
    coordinator = _flow_coordinator()
    flow = _flow(hass, coordinator)

    res = cast(dict[str, Any], await flow.async_step_install_ato(dict(_USER_INPUT)))

    assert res["type"] == FlowResultType.CREATE_ENTRY
    # The options are kept as they were
    assert res["data"] == {"keep": "me"}
    # Litres on the form, millilitres for the hub; the port as a number
    coordinator.async_install_ato_port.assert_awaited_once_with(
        1, ATO_UID, 20000.0, 150.0, 40.0, auto_fill=True, volume_monitor=False
    )
    # So the module's entities are built
    assert reloads == [flow.handler]


@pytest.mark.asyncio
async def test_install_ato_refused_shows_the_error(
    hass: HomeAssistant, reloads: list[str]
) -> None:
    coordinator = _flow_coordinator()
    coordinator.async_install_ato_port = AsyncMock(return_value=False)

    res = cast(
        dict[str, Any],
        await _flow(hass, coordinator).async_step_install_ato(dict(_USER_INPUT)),
    )

    assert res["type"] == FlowResultType.FORM
    assert res["step_id"] == "install_ato"
    assert res["errors"] == {"base": "ato_install_failed"}
    assert reloads == []


@pytest.mark.asyncio
async def test_install_ato_error_is_handled(
    hass: HomeAssistant, reloads: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    coordinator = _flow_coordinator()
    coordinator.async_install_ato_port = AsyncMock(side_effect=RuntimeError("boom"))

    res = cast(
        dict[str, Any],
        await _flow(hass, coordinator).async_step_install_ato(dict(_USER_INPUT)),
    )

    assert res["type"] == FlowResultType.FORM
    assert res["errors"] == {"base": "ato_install_failed"}
    assert "ATO module install failed" in caplog.text
    assert reloads == []
