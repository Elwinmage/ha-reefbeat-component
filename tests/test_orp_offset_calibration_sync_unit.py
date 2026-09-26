"""ORP offset and calibration reminders dated by the hub.

Captured on a real RSCONTROLPRO:

- ``GET /probe/offset?type=orp&uid=…`` -> ``{"offset", "last_adjustment_date"}``;
- ``POST /probe/offset`` on an ORP probe *adds* the posted value to the
  current offset (1 + 35 -> 36, 36 + 20 -> 56, 56 - 55 -> 1), and the
  readings include it;
- pH and EC carry ``last_adjustment_date`` in ``/dashboard.probes`` (null
  until calibrated), ORP does not.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.redsea.coordinator import (
    ReefBeatCloudLinkedCoordinator,
    ReefControlCoordinator,
)
from custom_components.redsea.maintenance import (
    CALIBRATION_TASKS,
    MaintenanceStore,
    probe_sub_id,
)
from custom_components.redsea.reefbeat.control import ReefControlAPI
from custom_components.redsea.reefbeat.power import ReefPowerAPI

_ORP = "/probe/offset?type=orp&uid=0x0071F"


def _api(probes: Any = None, sources: list[dict[str, Any]] | None = None) -> Any:
    api = ReefControlAPI.__new__(ReefControlAPI)
    api.data = {
        "sources": [
            {"name": "/dashboard", "type": "data", "data": {"probes": probes or []}},
            *(sources or []),
        ]
    }
    api._data_db = {}
    api._base_url = "http://test"
    api.quick_refresh = None
    api._live_config_update = False
    return api


def _offset_source(offset: Any, date: Any = 1790416038) -> dict[str, Any]:
    return {
        "name": _ORP,
        "type": "config",
        "data": {"offset": offset, "last_adjustment_date": date},
    }


# ── Offset sources ───────────────────────────────────────────────────────────


def test_offset_source_name_per_type() -> None:
    assert ReefControlAPI._offset_source_name("0x1") == (
        "/probe/offset?type=temperature&uid=0x1"
    )
    assert ReefControlAPI._offset_source_name("0x0071F", "orp") == _ORP


def test_orp_probe_gets_its_offset_source() -> None:
    api = _api([{"type": "orp", "uid": "0x0071F", "status": "auto"}])
    api.add_source = MagicMock()
    api.remove_source = MagicMock()
    api._reconcile_probe_offset_sources()
    api.add_source.assert_called_once_with(_ORP, "config", "")


@pytest.mark.asyncio
async def test_deleting_an_orp_probe_drops_its_source() -> None:
    api = _api(sources=[_offset_source(0)])
    api.http_send = AsyncMock(return_value={"ok": True})
    api.remove_source = MagicMock()
    await api.delete_probe("orp", "0x0071F")
    api.remove_source.assert_called_once_with(_ORP)


# ── Moving an offset ─────────────────────────────────────────────────────────


class _Hub:
    """/probe/offset of a hub: adds (or replaces) the posted value."""

    def __init__(self, api: Any, offset: float, adds: bool = True) -> None:
        self.api = api
        self.offset = offset
        self.adds = adds
        self.posts: list[Any] = []

    async def fetch_config(self, name: str) -> None:
        for source in self.api.data["sources"]:
            if source["name"] == name:
                source["data"] = {"offset": self.offset, "last_adjustment_date": 1}

    async def http_send(self, action: str, payload: Any, method: str) -> Any:
        self.posts.append(payload["offset"])
        value = payload["offset"]
        self.offset = self.offset + value if self.adds else value
        return {"ok": True}


def _hub(api: Any, offset: float, adds: bool = True) -> _Hub:
    hub = _Hub(api, offset, adds)
    api.fetch_config = hub.fetch_config
    api.http_send = hub.http_send
    return hub


@pytest.mark.asyncio
async def test_shift_posts_the_correction() -> None:
    """Captured: offset 1, POST 35 -> 36."""
    api = _api(sources=[_offset_source(1)])
    hub = _hub(api, 1)
    await api.shift_offset(_ORP, _ORP, 34.6, 0)
    assert hub.posts == [35]
    assert hub.offset == 36


@pytest.mark.asyncio
async def test_shift_corrects_a_hub_that_replaces() -> None:
    api = _api(sources=[_offset_source(0.5)])
    hub = _hub(api, 0.5, adds=False)
    await api.shift_offset(_ORP, _ORP, 0.34, 1)
    assert hub.posts == [0.3, 0.8]
    assert hub.offset == 0.8


@pytest.mark.asyncio
async def test_shift_from_zero_needs_no_check() -> None:
    """From 0, adding and replacing end the same."""
    api = _api(sources=[_offset_source(0)])
    hub = _hub(api, 0, adds=False)
    await api.shift_offset(_ORP, _ORP, 36, 0)
    assert hub.posts == [36]


@pytest.mark.asyncio
async def test_shift_refused_stops() -> None:
    api = _api(sources=[_offset_source(1)])
    api.fetch_config = AsyncMock()
    api.http_send = AsyncMock(return_value={"ok": False})
    await api.shift_offset(_ORP, _ORP, 5, 0)
    api.fetch_config.assert_awaited_once_with(_ORP)
    api.http_send.assert_awaited_once_with(_ORP, {"offset": 5}, "post")


# ── Calibration dates ────────────────────────────────────────────────────────


def test_calibration_dates() -> None:
    api = _api(
        [
            {"type": "ph", "uid": "0x00B39", "last_adjustment_date": 1790000000},
            {"type": "ec", "uid": "0x007BF", "last_adjustment_date": None},
            {"type": "orp", "uid": "0x0071F"},
        ],
        [_offset_source(36)],
    )
    assert api.calibration_date("ph", "0x00B39") == 1790000000.0
    assert api.calibration_date("ec", "0x007BF") is None
    assert api.calibration_date("orp", "0x0071F") == 1790416038.0
    assert api.calibration_date("ph", "0xGONE") is None
    assert api.calibration_date("orp", "0xGONE") is None


def test_zero_calibration_date_means_never() -> None:
    api = _api(sources=[_offset_source(0, 0)])
    assert api.calibration_date("orp", "0x0071F") is None


# ── Store ────────────────────────────────────────────────────────────────────


def _store() -> Any:
    store = MaintenanceStore.__new__(MaintenanceStore)
    store._data = {}
    store._listeners = {}
    store._async_save = AsyncMock()
    return store


@pytest.mark.asyncio
async def test_record_reset_only_moves_forward() -> None:
    store = _store()
    listener = MagicMock()
    store.async_add_listener("S", 1, "t", listener)
    when = datetime(2026, 9, 26, 9, 0, tzinfo=timezone.utc)

    assert await store.async_record_reset("S", 1, "t", when) is True
    assert store.get_last_reset("S", 1, "t") == when
    listener.assert_called_once()

    assert await store.async_record_reset("S", 1, "t", when) is False
    earlier = when - timedelta(days=3)
    assert await store.async_record_reset("S", 1, "t", earlier) is False
    assert store.get_last_reset("S", 1, "t") == when
    assert store._async_save.await_count == 1


# ── Coordinator ──────────────────────────────────────────────────────────────


def _coord(probes: list[Any], api: Any) -> Any:
    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = api
    coord._title = "SER"  # also the serial
    coord._probes = lambda: probes  # type: ignore[method-assign]
    return coord


def test_calibration_tasks_cover_the_dated_probes() -> None:
    assert set(CALIBRATION_TASKS) == {"ph", "ec", "orp"}


@pytest.mark.asyncio
async def test_sync_dates_the_calibration_tasks() -> None:
    probes: list[Any] = [
        {"type": "ph", "uid": "0x00B39"},
        {"type": "orp", "uid": "0x0071F"},
        {"type": "ec", "uid": "0x007BF"},  # never calibrated
        {"type": "ph", "uid": "NOTHEX"},
        {"type": "temperature", "uid": "0x1"},
        {"type": "ph"},
        "junk",
    ]
    dates = {"0x00B39": 1790000000.0, "0x0071F": 1790416038.0, "NOTHEX": 1.0}
    api = MagicMock()
    api.calibration_date.side_effect = lambda _t, uid: dates.get(uid)
    coord = _coord(probes, api)
    coord.maintenance = MagicMock()
    coord.maintenance.async_record_reset = AsyncMock()

    await coord._sync_calibration_maintenance()

    calls = coord.maintenance.async_record_reset.await_args_list
    assert [c.args[:3] for c in calls] == [
        ("SER", probe_sub_id("0x00B39"), "control_probe_calibration_ph"),
        ("SER", probe_sub_id("0x0071F"), "control_probe_calibration_orp"),
    ]
    assert calls[1].args[3] == datetime.fromtimestamp(1790416038, tz=timezone.utc)


@pytest.mark.asyncio
async def test_sync_without_store_does_nothing() -> None:
    api = MagicMock()
    coord = _coord([{"type": "ph", "uid": "0x1"}], api)
    await coord._sync_calibration_maintenance()
    api.calibration_date.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_runs_the_sync_and_survives_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ReefBeatCloudLinkedCoordinator,
        "_async_update_data",
        AsyncMock(return_value={"ok": 1}),
    )
    coord = _coord([], MagicMock())
    coord._sync_calibration_maintenance = AsyncMock()
    assert await coord._async_update_data() == {"ok": 1}
    coord._sync_calibration_maintenance.assert_awaited_once()

    coord._sync_calibration_maintenance = AsyncMock(side_effect=RuntimeError)
    assert await coord._async_update_data() == {"ok": 1}


# ── Calibration against a reference ──────────────────────────────────────────


def _probe_api(ptype: str, value: Any, offset: Any = 1) -> Any:
    name = f"/probe/offset?type={ptype}&uid=0x1"
    return _api(
        [{"type": ptype, "uid": "0x1", "value": value}],
        [{"name": name, "type": "config", "data": {"offset": offset}}],
    )


@pytest.mark.asyncio
async def test_calibrate_orp_against_a_solution() -> None:
    """Captured: reading 165 with offset 1, solution 200 -> POST 35 -> 36."""
    api = _probe_api("orp", 165)
    api.read_probe = AsyncMock(return_value=True)
    hub = _hub(api, 1)
    await api.calibrate_probe("orp", "0x1", 200)
    api.read_probe.assert_awaited_once_with("orp", "0x1")
    assert hub.posts == [35]
    assert hub.offset == 36
    assert api.dashboard_probe("orp", "0x1")["value"] == 200


@pytest.mark.asyncio
async def test_calibrate_embedded_temperature() -> None:
    """Captured: EC temp_value 30.1, offset 0, POST 0.9 -> 31.0."""
    name = "/probe/offset?type=ec&uid=0x1"
    api = _api(
        [{"type": "ec", "uid": "0x1", "value": 0, "temp_value": 30.1}],
        [{"name": name, "type": "config", "data": {"offset": 0}}],
    )
    api.read_probe = AsyncMock(return_value=True)
    hub = _hub(api, 0)
    await api.calibrate_probe("ec", "0x1", 31.0)
    assert hub.posts == [0.9]
    probe = api.dashboard_probe("ec", "0x1")
    assert probe["temp_value"] == 31.0
    assert probe["value"] == 0


def test_embedded_temperature_offset_sources() -> None:
    api = _api(
        [
            {"type": "ph", "uid": "0xB39", "status": "auto"},
            {"type": "ato", "uid": "0xA1", "status": "auto"},
        ]
    )
    api.add_source = MagicMock()
    api.remove_source = MagicMock()
    api._reconcile_probe_offset_sources()
    added = {c.args[0] for c in api.add_source.call_args_list}
    assert added == {
        "/probe/offset?type=ph&uid=0xB39",
        "/probe/offset?type=ato&uid=0xA1",
    }


def test_temperature_offset_date_is_not_a_calibration() -> None:
    """The pH temperature offset's date must not date the pH calibration."""
    api = _api(
        [{"type": "ph", "uid": "0x1", "last_adjustment_date": None}],
        [
            {
                "name": "/probe/offset?type=ph&uid=0x1",
                "type": "config",
                "data": {"offset": 2, "last_adjustment_date": 1790434790},
            }
        ],
    )
    assert api.calibration_date("ph", "0x1") is None


@pytest.mark.asyncio
async def test_calibrate_temperature_to_a_tenth() -> None:
    api = _probe_api("temperature", 25.43, offset=0.2)
    api.read_probe = AsyncMock(return_value=True)
    hub = _hub(api, 0.2)
    await api.calibrate_probe("temperature", "0x1", 25.1)
    assert hub.posts == [-0.3]
    assert hub.offset == pytest.approx(-0.1)
    assert api.dashboard_probe("temperature", "0x1")["value"] == 25.1


@pytest.mark.asyncio
async def test_calibrate_refused_keeps_the_reading() -> None:
    api = _probe_api("orp", 165)
    api.read_probe = AsyncMock(return_value=True)
    api.fetch_config = AsyncMock()
    api.http_send = AsyncMock(return_value={"ok": False})
    await api.calibrate_probe("orp", "0x1", 200)
    assert api.dashboard_probe("orp", "0x1")["value"] == 165


@pytest.mark.asyncio
async def test_calibrate_probe_gone_meanwhile() -> None:
    api = _probe_api("orp", 165)
    api.read_probe = AsyncMock(return_value=True)

    async def _gone(*_args: Any) -> Any:
        api.data["sources"][0]["data"]["probes"] = []
        return {"ok": True}

    api.shift_offset = _gone
    assert await api.calibrate_probe("orp", "0x1", 200) == {"ok": True}


@pytest.mark.asyncio
async def test_calibrate_without_reading_posts_nothing() -> None:
    api = _probe_api("orp", None)
    api.read_probe = AsyncMock(return_value=True)
    api.http_send = AsyncMock()
    assert await api.calibrate_probe("orp", "0x1", 200) is None
    api.read_probe = AsyncMock(return_value=False)
    api.data["sources"][0]["data"]["probes"][0]["value"] = 165
    assert await api.calibrate_probe("orp", "0x1", 200) is None
    api.data["sources"][0]["data"]["probes"] = []
    api.read_probe = AsyncMock(return_value=True)
    assert await api.calibrate_probe("orp", "0x1", 200) is None
    api.http_send.assert_not_awaited()


# ── Probe reinstalled elsewhere ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_probe_config_read_again_on_install() -> None:
    probe = {"type": "orp", "uid": "0x0071F", "last_installation_date": 1789800576}
    api = _api([probe, "junk", {"type": "ph"}])
    api.fetch_config = AsyncMock()

    # First poll: the config was just read with it
    await api._refresh_config_on_probe_install()
    await api._refresh_config_on_probe_install()
    api.fetch_config.assert_not_awaited()

    # Reinstalled from the app: new date
    probe["last_installation_date"] = 1790414202
    await api._refresh_config_on_probe_install()
    api.fetch_config.assert_awaited_once_with("/probe/config")

    # A new probe
    api.data["sources"][0]["data"]["probes"].append(
        {"type": "ph", "uid": "0x00B39", "last_installation_date": 1}
    )
    await api._refresh_config_on_probe_install()
    assert api.fetch_config.await_count == 2

    # A probe removed: nothing to read
    api.data["sources"][0]["data"]["probes"] = [probe]
    await api._refresh_config_on_probe_install()
    assert api.fetch_config.await_count == 2


@pytest.mark.asyncio
async def test_no_probe_list_no_config_read() -> None:
    api = _api()
    api.data["sources"][0]["data"] = {}
    api.fetch_config = AsyncMock()
    await api._refresh_config_on_probe_install()
    await api._refresh_config_on_probe_install()
    api.fetch_config.assert_not_awaited()


# ── RSPower local temperature ────────────────────────────────────────────────


def _power(temperature: Any, offset: Any = 0.2) -> Any:
    api = ReefPowerAPI.__new__(ReefPowerAPI)
    api.data = {
        "sources": [
            {
                "name": "/dashboard",
                "type": "data",
                "data": {"temperature": temperature},
            },
            {"name": "/temperature/config", "type": "data", "data": {"offset": offset}},
        ]
    }
    api._data_db = {}
    api._base_url = "http://test"
    api.quick_refresh = None
    api._live_config_update = False
    return api


class _PowerHub:
    """RSPower: /probe/offset adds; read back in /temperature/config."""

    def __init__(self, api: Any, offset: float) -> None:
        self.api = api
        self.offset = offset
        self.actions: list[tuple[str, Any]] = []
        self.fetched: list[str] = []
        api.fetch_config = self.fetch_config
        api.http_send = self.http_send

    async def fetch_config(self, name: str) -> None:
        self.fetched.append(name)
        if name == "/temperature/config":
            self.api.data["sources"][1]["data"] = {"offset": self.offset}

    async def http_send(self, action: str, payload: Any, method: str) -> Any:
        self.actions.append((action, payload))
        self.offset += payload["offset"]
        return {"ok": True}


def test_local_temperature_shapes() -> None:
    assert _power({"value": 25.4, "status": "connected"}).local_temperature() == 25.4
    assert _power(24.0).local_temperature() == 24.0
    assert _power(None).local_temperature() is None
    assert _power({"value": None}).local_temperature() is None


@pytest.mark.asyncio
async def test_power_calibrate_temperature() -> None:
    api = _power({"value": 25.6, "status": "connected"})
    hub = _PowerHub(api, 0.2)
    await api.calibrate_temperature(25.2)
    assert hub.fetched[0] == "/dashboard"
    assert hub.actions == [("/probe/offset", {"offset": -0.4})]
    assert hub.offset == pytest.approx(-0.2)
    assert api.local_temperature() == 25.2


@pytest.mark.asyncio
async def test_power_calibrate_old_firmware_shape() -> None:
    api = _power(25.6)
    hub = _PowerHub(api, 0)
    await api.calibrate_temperature(25.0)
    assert hub.actions == [("/probe/offset", {"offset": -0.6})]
    # A bare float is left for the next poll to replace
    assert api.local_temperature() == 25.6


@pytest.mark.asyncio
async def test_power_calibrate_without_reading() -> None:
    api = _power(None)
    hub = _PowerHub(api, 0)
    assert await api.calibrate_temperature(25.0) is None
    assert hub.actions == []


@pytest.mark.asyncio
async def test_power_calibrate_refused() -> None:
    api = _power({"value": 25.6})
    api.fetch_config = AsyncMock()
    api.http_send = AsyncMock(return_value=None)
    assert await api.calibrate_temperature(25.2) is None
    assert api.local_temperature() == 25.6


# ── Retired entities ─────────────────────────────────────────────────────────


def test_retired_entities_are_purged(monkeypatch: pytest.MonkeyPatch) -> None:
    import custom_components.redsea as integration

    entries = [
        MagicMock(unique_id=f"SER_{key}", entity_id=f"number.{key}")
        for key in (
            "probe_orp_0x0071f_offset",
            "probe_temperature_0x000f7_offset",
            "temperature_offset",
            "probe_orp_0x0071f_calibration",
            "fusion_threshold",
        )
    ]
    entries.append(MagicMock(unique_id="OTHER_temperature_offset", entity_id="x"))
    registry = MagicMock()
    monkeypatch.setattr(integration.er, "async_get", lambda _hass: registry)
    monkeypatch.setattr(
        integration.er, "async_entries_for_config_entry", lambda _r, _id: entries
    )
    coordinator = MagicMock(serial="SER")
    integration._purge_retired_entities(MagicMock(), MagicMock(), coordinator)
    removed = [c.args[0] for c in registry.async_remove.call_args_list]
    assert removed == [
        "number.probe_orp_0x0071f_offset",
        "number.probe_temperature_0x000f7_offset",
        "number.temperature_offset",
    ]
