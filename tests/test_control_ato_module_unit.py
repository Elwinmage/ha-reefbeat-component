"""ATO module of the RSCONTROL hub (the Red Sea ATO kit on a 12V port).

Covers the API sequence captured from the app installing the kit on port 1,
the module's settings writes, their optimistic updates, the dynamic
``/ato/configuration`` source, the coordinator wrappers and the
``install_ato`` options-flow step.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
from custom_components.redsea.reefbeat.api import ReefBeatAPI
from custom_components.redsea.reefbeat.control import ReefControlAPI

ATO = ReefControlAPI.ATO_CONFIG

# /dashboard.ports once the app installed the kit on port 1 (captured)
_ATO_PORT: dict[str, Any] = {
    "number": 1,
    "name": "ATO Module",
    "type": "ato",
    "mode": "missing_pump",
    "user_config_mode": "auto",
    "auto_fill": True,
    "temp_log_enabled": True,
    "uid": "0x0024E",
    "today_volume": 0,
    "is_pump_on": False,
    "last_pump_on_cause": "unknown",
    "volume_left": 50000,
    "consumption": 0,
}
_OTHER_PORT: dict[str, Any] = {
    "number": 0,
    "name": "S1",
    "mode": "off",
    "type": "other",
    "state": "unknown",
    "user_config_mode": "off",
    "consumption": 0,
}
_SETUP_PORT: dict[str, Any] = {
    "number": 1,
    "name": "S2",
    "mode": "setup",
    "type": "unknown",
    "state": "unknown",
    "user_config_mode": "setup",
    "consumption": 0,
}
# GET /ato/configuration (captured, debug block trimmed)
_ATO_CONF: dict[str, Any] = {
    "auto_fill": True,
    "port_index": 1,
    "rvm_enabled": True,
    "notify": True,
    "temp_log_enabled": True,
    "hose": {"height": 220, "length": 459},
    "pump_override": {"speed_override": 0, "flow_rate_override": 0},
}


def _api(
    ports: list[dict[str, Any]] | None = None, conf: dict[str, Any] | None = None
) -> Any:
    api = ReefControlAPI.__new__(ReefControlAPI)
    sources: list[dict[str, Any]] = [
        {
            "name": "/dashboard",
            "type": "data",
            "data": {
                "probes": [],
                "ports": [dict(p) for p in (ports or [_OTHER_PORT, _ATO_PORT])],
            },
        },
        {"name": "/ports/config", "type": "config", "data": []},
    ]
    if conf is not None:
        sources.append({"name": ATO, "type": "config", "data": conf})
    api.data = {"sources": sources}
    api._data_db = {}
    api._base_url = "http://test"
    api.quick_refresh = "/dashboard"
    api._live_config_update = True
    api.http_send = AsyncMock(return_value={"ok": True, "json": {}})
    api.fetch_config = AsyncMock()
    return api


def _names(api: Any) -> set[str]:
    return {s["name"] for s in api.data["sources"]}


# ---------------------------------------------------------------------------
# API — install
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_install_ato_port_follows_the_app() -> None:
    api = _api([_OTHER_PORT, _SETUP_PORT])
    await api.install_ato_port(1, "0x0024E", 50000, 460, 220)
    assert api.http_send.await_args_list == [
        call("/port/1/install", {"uid": "0x0024E", "type": "ato"}, "post"),
        call("/ato/update-volume", {"volume": 50000}, "post"),
        call(
            ATO,
            {
                "volume_left": 50000,
                "port_index": 1,
                "hose": {"length": 460, "height": 220},
                "auto_fill": True,
                "notify": True,
                "rvm_enabled": True,
            },
            "put",
        ),
        call(
            "/ports/config",
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
    api.fetch_config.assert_has_awaits([call(ATO), call("/ports/config")])


@pytest.mark.asyncio
async def test_install_ato_port_lite_without_volume_monitoring() -> None:
    api = _api([_SETUP_PORT])
    await api.install_ato_port(
        0, "0xA", 0, 100, 0, auto_fill=False, volume_monitor=False, port_count=1
    )
    paths = [c.args[0] for c in api.http_send.await_args_list]
    assert paths == ["/port/0/install", ATO, "/ports/config"]
    assert api.http_send.await_args_list[1].args[1]["rvm_enabled"] is False
    assert api.http_send.await_args_list[2].args[1] == [
        {"number": 0, "name": "ATO Module", "type": "ato", "is_btn_assigned": True}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("refused_at", [0, 2])
async def test_install_ato_port_stops_when_refused(refused_at: int) -> None:
    api = _api([_OTHER_PORT, _SETUP_PORT])
    answers: list[Any] = [{"ok": True}] * 4
    answers[refused_at] = {"ok": False}
    api.http_send = AsyncMock(side_effect=answers)
    result = await api.install_ato_port(1, "0xA", 1000, 100, 0)
    assert result == {"ok": False}
    assert api.http_send.await_count == refused_at + 1
    api.fetch_config.assert_not_awaited()


# ---------------------------------------------------------------------------
# API — /ato/configuration source
# ---------------------------------------------------------------------------


def test_ato_source_follows_the_module() -> None:
    api = _api()
    assert api.ato_port_number() == 1
    assert api._reconcile_ato_source() is True
    assert ATO in _names(api)
    # Already there
    assert api._reconcile_ato_source() is False
    api.data["sources"][0]["data"]["ports"] = [_OTHER_PORT, _SETUP_PORT]
    assert api.ato_port_number() is None
    assert api._reconcile_ato_source() is False
    assert ATO not in _names(api)


def test_ato_port_number_ignores_junk() -> None:
    api = _api()
    api.data["sources"][0]["data"]["ports"] = ["junk", {"type": "ato"}]
    assert api.ato_port_number() is None
    api.data["sources"][0]["data"]["ports"] = None
    assert api.ato_port_number() is None
    assert api.ato_dashboard() is None


@pytest.mark.asyncio
async def test_fetch_data_reads_the_new_ato_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    monkeypatch.setattr(ReefBeatAPI, "fetch_data", AsyncMock(return_value={}))
    api._sync_port_schedules = AsyncMock()
    api._read_new_leaks = AsyncMock()
    api._refresh_config_on_probe_install = AsyncMock()
    await api.fetch_data()
    api.fetch_config.assert_awaited_once_with(ATO)
    # Registered: not read again on the next poll
    await api.fetch_data()
    api.fetch_config.assert_awaited_once_with(ATO)


def test_ato_config_and_dashboard() -> None:
    api = _api(conf=dict(_ATO_CONF))
    assert api.ato_config() == _ATO_CONF
    assert api.ato_dashboard()["uid"] == "0x0024E"
    assert api.dashboard_port(0)["name"] == "S1"
    assert _api().ato_config() is None


# ---------------------------------------------------------------------------
# API — settings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_ato_config_adds_the_port() -> None:
    api = _api()
    await api.set_ato_config({"auto_fill": False})
    api.http_send.assert_awaited_once_with(
        ATO, {"auto_fill": False, "port_index": 1}, "put"
    )


@pytest.mark.asyncio
async def test_set_ato_config_without_module_sends_nothing() -> None:
    api = _api([_OTHER_PORT, _SETUP_PORT])
    assert await api.set_ato_config({"notify": False}) is None
    api.http_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_ato_hose_resends_the_other_dimension() -> None:
    api = _api(conf=dict(_ATO_CONF))
    await api.set_ato_hose(length_cm=300)
    await api.set_ato_hose(height_cm=100)
    assert [c.args[1]["hose"] for c in api.http_send.await_args_list] == [
        {"length": 300, "height": 220},
        {"length": 459, "height": 100},
    ]
    # Not read yet: 0 for the unknown one
    api = _api()
    await api.set_ato_hose(length_cm=200)
    assert api.http_send.await_args.args[1]["hose"] == {"length": 200, "height": 0}


@pytest.mark.asyncio
async def test_set_ato_flow_rate() -> None:
    conf = dict(_ATO_CONF, pump_override={"speed_override": 7})
    api = _api(conf=conf)
    await api.set_ato_flow_rate(500.4)
    await api.set_ato_flow_rate(0)
    assert [c.args[1]["pump_override"] for c in api.http_send.await_args_list] == [
        {"speed_override": 7, "flow_rate_override": 500},
        {"speed_override": 7, "flow_rate_override": -1},
    ]
    api = _api(conf=dict(_ATO_CONF, pump_override={"speed_override": "x"}))
    await api.set_ato_flow_rate(1200)
    assert api.http_send.await_args.args[1]["pump_override"] == {
        "speed_override": 0,
        "flow_rate_override": 1200,
    }


@pytest.mark.asyncio
async def test_ato_actions() -> None:
    api = _api()
    await api.update_ato_volume(1234.6)
    await api.ato_resume()
    await api.ato_manual_pump()
    await api.ato_stop()
    assert api.http_send.await_args_list == [
        call("/ato/update-volume", {"volume": 1235}, "post"),
        call("/ato/resume", {}, "post"),
        call("/ato/manual-pump", {}, "post"),
        call("/ato/stop", {}, "post"),
    ]


# ---------------------------------------------------------------------------
# API — optimistic updates
# ---------------------------------------------------------------------------


def test_mirror_configuration_answer() -> None:
    api = _api(conf=dict(_ATO_CONF))
    answer = dict(_ATO_CONF, auto_fill=False)
    api._mirror_write(
        ATO, {"auto_fill": False, "port_index": 1}, "put", {"json": answer}
    )
    assert api.ato_config()["auto_fill"] is False
    assert api.ato_dashboard()["auto_fill"] is False
    # An answer without the configuration keeps the cached one
    api._mirror_write(ATO, {"temp_log_enabled": False}, "put", {"json": {"ok": 1}})
    assert api.ato_config() == answer
    assert api.ato_dashboard()["temp_log_enabled"] is False
    # A body that is not an object changes nothing on the dashboard
    api._mirror_write(ATO, None, "put", {})


def test_mirror_volume_resume_stop() -> None:
    api = _api()
    dash = api.ato_dashboard()
    api._mirror_write("/ato/update-volume", {"volume": 1000}, "post", {})
    assert dash["volume_left"] == 1000
    api._mirror_write("/ato/update-volume", {"volume": "x"}, "post", {})
    assert dash["volume_left"] == 1000
    api._mirror_write("/ato/resume", {}, "post", {})
    assert dash["mode"] == "auto"
    dash["mode"] = "auto"
    dash["user_config_mode"] = "off"
    api._mirror_write("/ato/resume", {}, "post", {})
    assert dash["mode"] == "auto"
    dash["is_pump_on"] = True
    api._mirror_write("/ato/stop", {}, "post", {})
    assert dash["is_pump_on"] is False
    # Untracked ATO write
    api._mirror_write("/ato/manual-pump", {}, "post", {})


def test_mirror_without_module() -> None:
    api = _api([_OTHER_PORT, _SETUP_PORT])
    api._mirror_write("/ato/resume", {}, "post", {})
    api._mirror_write("/ato/update-volume", {"volume": 1}, "post", {})
    assert api.dashboard_port(1)["mode"] == "setup"


def test_mirror_ato_port_install() -> None:
    api = _api([_OTHER_PORT, _SETUP_PORT])
    api._mirror_write("/port/1/install", {"uid": "0xA", "type": "ato"}, "post", {})
    port = api.dashboard_port(1)
    assert port["type"] == "ato"
    assert port["uid"] == "0xA"
    assert "state" not in port
    assert api.ato_port_number() == 1
    # A port not listed on the dashboard
    api._mirror_write("/port/5/install", {"uid": "0xA", "type": "ato"}, "post", {})


def test_default_probe_names() -> None:
    assert ReefControlAPI._ato_probe_name("0x0024E") == "ATO Temp. 24E"
    assert ReefControlAPI._leak_probe_name("0x00000") == "Leak 0"


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------


def _coordinator(api: Any) -> Any:
    from custom_components.redsea.coordinator import ReefControlCoordinator

    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = api
    coord.port_count = 2
    coord.async_request_refresh = AsyncMock()  # type: ignore[method-assign]
    coord.async_update_listeners = MagicMock()  # type: ignore[method-assign]
    return coord


def test_coordinator_ato_reads() -> None:
    api = _api(conf=dict(_ATO_CONF))
    api.data["sources"][0]["data"]["probes"] = [
        {"type": "ato", "uid": "0x0024E", "name": "Temp. osmolateur 24E"},
        {"type": "ec", "uid": "0x007BF", "name": "EC"},
    ]
    coord = _coordinator(api)
    assert coord.ato_port_number() == 1
    assert coord.ato_is_port(1) and not coord.ato_is_port(0)
    assert coord.ato_config() == _ATO_CONF
    assert coord.ato_config_value("hose", "length") == 459
    assert coord.ato_config_value("hose", "length", "x") is None
    assert coord.ato_port_value(1, "volume_left") == 50000
    assert coord.ato_port_value(0, "volume_left") is None
    assert coord.ato_status(1) == "missing_pump"
    assert coord.ato_status(0) is None
    api.dashboard_port(1)["mode"] = "auto"
    assert coord.ato_status(1) == "ok"
    assert coord.ato_probes() == [{"uid": "0x0024E", "name": "Temp. osmolateur 24E"}]
    # Both ports installed (other, ato)
    assert coord.ato_free_ports() == []


def test_coordinator_ato_free_ports() -> None:
    api = _api([_OTHER_PORT, _SETUP_PORT])
    coord = _coordinator(api)
    assert coord.ato_free_ports() == [1]


@pytest.mark.asyncio
async def test_coordinator_ato_writes() -> None:
    api = MagicMock(
        install_ato_port=AsyncMock(return_value={"ok": True}),
        set_ato_config=AsyncMock(),
        set_ato_hose=AsyncMock(),
        set_ato_flow_rate=AsyncMock(),
        update_ato_volume=AsyncMock(),
        ato_resume=AsyncMock(),
        ato_manual_pump=AsyncMock(),
        ato_stop=AsyncMock(),
    )
    coord = _coordinator(api)
    assert await coord.async_install_ato_port(1, "0xA", 1000, 100, 0) is True
    api.install_ato_port.assert_awaited_once_with(
        1, "0xA", 1000, 100, 0, auto_fill=True, volume_monitor=True, port_count=2
    )
    coord.async_request_refresh.assert_awaited_with(config=True)
    api.install_ato_port.return_value = None
    assert await coord.async_install_ato_port(1, "0xA", 1000, 100, 0) is False

    await coord.async_set_ato_config({"notify": False})
    await coord.async_set_ato_hose(length_cm=200)
    await coord.async_set_ato_flow_rate(0.5)
    await coord.async_update_ato_volume(2000)
    await coord.async_ato_resume()
    await coord.async_ato_manual_pump()
    await coord.async_ato_stop()
    api.set_ato_config.assert_awaited_once_with({"notify": False})
    api.set_ato_hose.assert_awaited_once_with(200, None)
    api.set_ato_flow_rate.assert_awaited_once_with(500)
    api.update_ato_volume.assert_awaited_once_with(2000)
    api.ato_resume.assert_awaited_once()
    api.ato_manual_pump.assert_awaited_once()
    api.ato_stop.assert_awaited_once()


# ---------------------------------------------------------------------------
# Options flow — install_ato
# ---------------------------------------------------------------------------


def _flow(hass: Any, coordinator: Any) -> config_flow.OptionsFlowHandler:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ctl",
        data={CONFIG_FLOW_HW_MODEL: "RSCONTROLPRO"},
        options={},
        unique_id="ctl-ato-of",
    )
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    flow = config_flow.OptionsFlowHandler(cast(Any, entry))
    flow.hass = hass
    flow.handler = entry.entry_id
    flow.flow_id = "test-flow"
    flow.context = {}
    return flow


@pytest.fixture(autouse=True)
def _no_reload(monkeypatch: pytest.MonkeyPatch, hass: Any) -> None:
    monkeypatch.setattr(
        hass.config_entries, "async_schedule_reload", lambda *a, **k: None
    )


def _hub(port: int | None = None) -> Any:
    coordinator = MagicMock()
    coordinator.ato_port_number = MagicMock(return_value=port)
    coordinator.ato_probes = MagicMock(
        return_value=[{"uid": "0x0024E", "name": "ATO Temp. 24E"}]
    )
    coordinator.ato_free_ports = MagicMock(return_value=[1])
    coordinator.async_install_ato_port = AsyncMock(return_value=True)
    return coordinator


_INPUT: dict[str, Any] = {
    CONFIG_FLOW_ATO_PORT: "1",
    CONFIG_FLOW_ATO_PROBE: "0x0024E",
    CONFIG_FLOW_ATO_VOLUME: 50,
    CONFIG_FLOW_ATO_HOSE_LENGTH: 460,
    CONFIG_FLOW_ATO_HOSE_HEIGHT: 220,
    CONFIG_FLOW_ATO_AUTO_FILL: True,
    CONFIG_FLOW_ATO_VOLUME_MONITOR: True,
}


@pytest.mark.asyncio
async def test_menu_offers_ato_install_when_possible(hass: Any) -> None:
    menu = cast(dict[str, Any], await _flow(hass, _hub()).async_step_init())
    assert OPTIONS_MENU_INSTALL_ATO in menu["menu_options"]
    # Already installed
    menu = cast(dict[str, Any], await _flow(hass, _hub(1)).async_step_init())
    assert OPTIONS_MENU_INSTALL_ATO not in menu["menu_options"]


@pytest.mark.asyncio
async def test_install_ato_form_then_success(hass: Any) -> None:
    hub = _hub()
    flow = _flow(hass, hub)
    form = cast(dict[str, Any], await flow.async_step_install_ato())
    assert form["type"] == FlowResultType.FORM
    assert form["step_id"] == "install_ato"
    res = cast(dict[str, Any], await flow.async_step_install_ato(dict(_INPUT)))
    assert res["type"] == FlowResultType.CREATE_ENTRY
    hub.async_install_ato_port.assert_awaited_once_with(
        1, "0x0024E", 50000.0, 460.0, 220.0, auto_fill=True, volume_monitor=True
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["refused", "raises"])
async def test_install_ato_failure_shows_error(hass: Any, failure: str) -> None:
    hub = _hub()
    if failure == "refused":
        hub.async_install_ato_port = AsyncMock(return_value=False)
    else:
        hub.async_install_ato_port = AsyncMock(side_effect=RuntimeError("boom"))
    res = cast(
        dict[str, Any], await _flow(hass, hub).async_step_install_ato(dict(_INPUT))
    )
    assert res["type"] == FlowResultType.FORM
    assert res["errors"] == {"base": "ato_install_failed"}


@pytest.mark.asyncio
async def test_install_ato_aborts(hass: Any) -> None:
    hub = _hub()
    hub.ato_probes = MagicMock(return_value=[])
    res = cast(dict[str, Any], await _flow(hass, hub).async_step_install_ato())
    assert res["reason"] == "no_ato_probe"

    hub = _hub()
    hub.ato_free_ports = MagicMock(return_value=[])
    res = cast(dict[str, Any], await _flow(hass, hub).async_step_install_ato())
    assert res["reason"] == "no_free_port"

    flow = _flow(hass, _hub())
    hass.data[DOMAIN].pop(flow.handler)
    res = cast(dict[str, Any], await flow.async_step_install_ato())
    assert res["reason"] == "no_ato_probe"


def test_status_options_match_the_api() -> None:
    from custom_components.redsea.sensor import _ATO_STATUS_OPTIONS

    assert _ATO_STATUS_OPTIONS == ["ok", *ReefControlAPI.ATO_FAULT_MODES]


# ---------------------------------------------------------------------------
# Removing the module's entities with its port
# ---------------------------------------------------------------------------


def test_ato_port_entity_port() -> None:
    from custom_components.redsea.probe_entities import ato_port_entity_port

    for key in (
        "port_1_ato_status",
        "port_1_ato_volume_left",
        "port_1_ato_hose_length",
        "port_1_today_volume",
        "port_1_volume_left",
        "port_1_last_pump_on_cause",
        "port_1_is_pump_on",
    ):
        assert ato_port_entity_port(key) == 1
    for key in ("port_1_state", "port_1_mode", "port_1_delete", "probe_ato_x_y"):
        assert ato_port_entity_port(key) is None


def _registered(hass: Any, entry: MockConfigEntry) -> dict[str, str]:
    from homeassistant.helpers import entity_registry as er

    reg = er.async_get(hass)
    ids: dict[str, str] = {}
    for unique_id in (
        "CTL_port_1_ato_status",
        "CTL_port_1_is_pump_on",
        "CTL_port_1_ato_auto_fill",
        "CTL_port_1_state",
        "CTL_port_0_ato_status",
        "OTHER_port_1_ato_status",
    ):
        ids[unique_id] = reg.async_get_or_create(
            "sensor", DOMAIN, unique_id, config_entry=cast(Any, entry)
        ).entity_id
    return ids


def _hub_coordinator(hass: Any, api: Any, entry: MockConfigEntry) -> Any:
    coord = _coordinator(api)
    coord._hass = hass
    coord._entry = entry
    coord._title = "CTL"
    return coord


def _present(hass: Any, ids: dict[str, str]) -> set[str]:
    from homeassistant.helpers import entity_registry as er

    reg = er.async_get(hass)
    return {uid for uid, eid in ids.items() if reg.async_get(eid) is not None}


def _ctl_entry(hass: Any, unique_id: str) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="CTL",
        data={CONFIG_FLOW_HW_MODEL: "RSCONTROLPRO"},
        unique_id=unique_id,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.asyncio
async def test_purge_ato_entities(hass: Any) -> None:
    entry = _ctl_entry(hass, "ctl-purge")
    ids = _registered(hass, entry)
    coord = _hub_coordinator(hass, _api(), entry)
    # The module on port 1: only port 0's leftovers go
    assert coord.purge_ato_entities(keep_port=1) == 1
    assert "CTL_port_0_ato_status" not in _present(hass, ids)
    # No module: every one of them goes, nothing else
    assert coord.purge_ato_entities() == 3
    assert _present(hass, ids) == {"CTL_port_1_state", "OTHER_port_1_ato_status"}


@pytest.mark.asyncio
async def test_track_ato_module(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    entry = _ctl_entry(hass, "ctl-track")
    ids = _registered(hass, entry)
    reload = MagicMock()
    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", reload)
    api = _api()
    coord = _hub_coordinator(hass, api, entry)

    # First read: remembered, nothing done
    coord._track_ato_module()
    assert coord._ato_port_seen == 1
    coord._track_ato_module()
    assert len(_present(hass, ids)) == 6
    reload.assert_not_called()

    # Ports not read: nothing changes
    ports = api.data["sources"][0]["data"]["ports"]
    api.data["sources"][0]["data"]["ports"] = None
    coord._track_ato_module()
    assert coord._ato_port_seen == 1

    # Port uninstalled (from the app, say): the module's entities go
    api.data["sources"][0]["data"]["ports"] = [_OTHER_PORT, _SETUP_PORT]
    coord._track_ato_module()
    assert coord._ato_port_seen is None
    assert _present(hass, ids) == {"CTL_port_1_state", "OTHER_port_1_ato_status"}
    reload.assert_not_called()

    # Installed again: a reload builds its entities
    api.data["sources"][0]["data"]["ports"] = ports
    coord._track_ato_module()
    reload.assert_called_once_with(entry.entry_id)


@pytest.mark.asyncio
async def test_delete_port_removes_the_module_entities(hass: Any) -> None:
    entry = _ctl_entry(hass, "ctl-del-ato")
    ids = _registered(hass, entry)
    api = _api()
    api.fetch_config = AsyncMock()
    coord = _hub_coordinator(hass, api, entry)
    coord._track_ato_module()
    # DELETE /port/1, mirrored at once in the cache (type back to unknown)
    api.http_send = AsyncMock(
        side_effect=lambda action, payload, method: (
            api._mirror_write(action, payload, method, {"ok": True}) or {"ok": True}
        )
    )
    await coord.delete_port(1)
    assert _present(hass, ids) == {"CTL_port_1_state", "OTHER_port_1_ato_status"}


@pytest.mark.asyncio
async def test_install_does_not_reload_twice(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _ctl_entry(hass, "ctl-install-ato")
    reload = MagicMock()
    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", reload)
    api = _api([_OTHER_PORT, _SETUP_PORT])
    api.http_send = AsyncMock(
        side_effect=lambda action, payload, method: (
            api._mirror_write(action, payload, method, {"ok": True}) or {"ok": True}
        )
    )
    coord = _hub_coordinator(hass, api, entry)
    coord._track_ato_module()
    assert coord._ato_port_seen is None
    assert await coord.async_install_ato_port(1, "0xA", 1000, 100, 0) is True
    assert coord._ato_port_seen == 1
    # The refresh after it: the options flow reloads, not the tracking
    coord._track_ato_module()
    reload.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_tracks_the_module_and_survives_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from custom_components.redsea.coordinator import ReefBeatCloudLinkedCoordinator

    monkeypatch.setattr(
        ReefBeatCloudLinkedCoordinator,
        "_async_update_data",
        AsyncMock(return_value={"ok": 1}),
    )
    coord = _coordinator(_api())
    coord._title = "CTL"
    coord._sync_calibration_maintenance = AsyncMock()
    coord._track_ato_module = MagicMock()
    assert await coord._async_update_data() == {"ok": 1}
    coord._track_ato_module.assert_called_once()
    coord._track_ato_module = MagicMock(side_effect=RuntimeError)
    assert await coord._async_update_data() == {"ok": 1}


@pytest.mark.asyncio
async def test_setup_purges_the_entities_of_a_module_gone(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Uninstalled while Home Assistant was stopped: purged at setup."""
    import custom_components.redsea as integration

    entry = _ctl_entry(hass, "ctl-setup-ato")
    ids = _registered(hass, entry)
    api = _api([_OTHER_PORT, _SETUP_PORT])
    coord = _hub_coordinator(hass, api, entry)
    coord.async_setup = AsyncMock()
    coord.get_data = api.get_data
    monkeypatch.setattr(integration, "_build_coordinator", lambda h, e: coord)
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    monkeypatch.setattr(integration, "_migrate_head_device_names", AsyncMock())

    assert await integration.async_setup_entry(hass, cast(Any, entry)) is True
    assert _present(hass, ids) == {"CTL_port_1_state", "OTHER_port_1_ato_status"}
