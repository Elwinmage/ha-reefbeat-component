"""Unit tests for the probe/temperature methods added to ``ReefControlAPI`` and
``ReefPowerAPI``.

Both APIs are built offline (``__new__`` + a seeded ``data`` bag) so the real
JSONPath engine resolves reads/writes; the network boundary (``http_send`` and
the base ``fetch_data``) is mocked. This covers the dynamic per-probe source
reconciliation, the offset getters/setters, install/delete, and the
buzzer/notify/enable path selection.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, call

import pytest

from custom_components.redsea.reefbeat.api import ReefBeatAPI
from custom_components.redsea.reefbeat.control import ReefControlAPI
from custom_components.redsea.reefbeat.power import (
    _TEMPERATURE_CONFIG_DEFAULTS,
    ReefPowerAPI,
)


def _control_api(
    probes: list[dict[str, Any]] | None = None,
    extra_sources: list[dict[str, Any]] | None = None,
) -> Any:
    api = ReefControlAPI.__new__(ReefControlAPI)
    sources: list[dict[str, Any]] = [
        {"name": "/dashboard", "type": "data", "data": {"probes": probes or []}}
    ]
    if extra_sources:
        sources.extend(extra_sources)
    api.data = {"sources": sources}
    api._data_db = {}
    api._base_url = "http://test"
    api.quick_refresh = None
    api._live_config_update = True
    api.http_send = AsyncMock(return_value={"json": {}})
    return api


def _power_api(temperature: Any = None) -> Any:
    api = ReefPowerAPI.__new__(ReefPowerAPI)
    api.data = {
        "sources": [
            {"name": "/dashboard", "type": "data", "data": {"temperature": temperature}}
        ]
    }
    api._data_db = {}
    api._base_url = "http://test"
    api.quick_refresh = None
    api._live_config_update = True
    api.http_send = AsyncMock(return_value={"json": {}})
    return api


def _source_names(api: Any) -> set[str]:
    return {s["name"] for s in api.data["sources"]}


# ===========================================================================
# ReefControlAPI
# ===========================================================================


def test_offset_source_name() -> None:
    assert (
        ReefControlAPI._offset_source_name("0xT")
        == "/probe/offset?type=temperature&uid=0xT"
    )


def test_probe_offset_reads_dynamic_source() -> None:
    api = _control_api(
        probes=[{"type": "temperature", "uid": "0xT"}],
        extra_sources=[
            {
                "name": "/probe/offset?type=temperature&uid=0xT",
                "type": "config",
                "data": {"offset": 0.3},
            }
        ],
    )
    assert api.probe_offset("0xT") == 0.3


@pytest.mark.asyncio
async def test_set_and_reset_probe_offset() -> None:
    api = _control_api()
    await api.set_probe_offset("0xT", 0.5)
    api.http_send.assert_awaited_with(
        "/probe/offset?type=temperature&uid=0xT", {"offset": 0.5}, "post"
    )
    await api.reset_probe_offset("0xT")
    api.http_send.assert_awaited_with(
        "/probe/offset?type=temperature&uid=0xT", None, "delete"
    )


@pytest.mark.asyncio
async def test_install_probe_success_stops_ble() -> None:
    api = _control_api()
    api.http_send = AsyncMock(return_value={"json": {"uid": "0xNEW", "success": True}})
    await api.install_probe("ph")
    assert api.http_send.await_count == 2
    api.http_send.assert_awaited_with("/ble/off?type=ph&uid=0xNEW", {}, "post")


@pytest.mark.asyncio
async def test_install_probe_no_uid_single_call() -> None:
    api = _control_api()
    api.http_send = AsyncMock(return_value={"json": {"success": False}})
    await api.install_probe("ph")
    assert api.http_send.await_count == 1


@pytest.mark.asyncio
async def test_delete_probe() -> None:
    api = _control_api()
    await api.delete_probe("ph", "0xP")
    api.http_send.assert_awaited_with("/probe?type=ph&uid=0xP", None, "delete")


def test_probe_config_path_variants() -> None:
    leak = ReefControlAPI.probe_config_path("leak", "0xL", "buzzer", "leak")
    assert leak == "$.sources[?(@.name=='/leak/config')].data.buzzer"

    temp = ReefControlAPI.probe_config_path("ato", "0xA", "buzzer", "temp")
    assert temp.endswith(".temp.buzzer")

    top = ReefControlAPI.probe_config_path("ph", "0xP", "notify", "top")
    assert top.endswith("].notify")


def test_buzzer_and_notify_paths_pick_location() -> None:
    api = _control_api()
    # ato buzzer nests under temp:{}, leak lives in /leak/config, ph is top-level.
    assert api.buzzer_path("ato", "0xA").endswith(".temp.buzzer")
    assert "/leak/config" in api.buzzer_path("leak", "0xL")
    assert api.notify_path("ph", "0xP").endswith("].notify")


@pytest.mark.asyncio
async def test_set_probe_buzzer_notify_flag_locations() -> None:
    api = _control_api()

    # leak -> PUT /leak/config partial body
    await api.set_probe_buzzer("leak", "0xL", True)
    api.http_send.assert_awaited_with("/leak/config", {"buzzer": True}, "put")

    # ato buzzer -> temp-nested body on /probe/config
    await api.set_probe_buzzer("ato", "0xA", False)
    args = api.http_send.await_args
    assert args.args[0] == "/probe/config"
    assert args.args[1] == [{"type": "ato", "uid": "0xA", "temp": {"buzzer": False}}]

    # ph notify -> top-level flag on /probe/config
    await api.set_probe_notify("ph", "0xP", True)
    args = api.http_send.await_args
    assert args.args[1] == [{"type": "ph", "uid": "0xP", "notify": True}]


@pytest.mark.asyncio
async def test_set_probe_enabled_toggles_method() -> None:
    api = _control_api()
    await api.set_probe_enabled("ph", "0xP", True)  # enabled -> DELETE
    api.http_send.assert_awaited_with("/probe/disable?type=ph&uid=0xP", None, "delete")
    await api.set_probe_enabled("ph", "0xP", False)  # disabled -> POST
    api.http_send.assert_awaited_with("/probe/disable?type=ph&uid=0xP", None, "post")


def test_reconcile_probe_offset_sources_adds_and_removes() -> None:
    api = _control_api(
        probes=[
            {"type": "temperature", "uid": "0xT"},
            {"type": "leak", "uid": "0xL"},
        ],
        extra_sources=[
            # A stale offset source for a probe that no longer exists -> removed.
            {
                "name": "/probe/offset?type=temperature&uid=0xOLD",
                "type": "config",
                "data": "",
            }
        ],
    )
    api._reconcile_probe_offset_sources()
    names = _source_names(api)
    assert "/probe/offset?type=temperature&uid=0xT" in names
    assert "/leak/config" in names
    assert "/probe/offset?type=temperature&uid=0xOLD" not in names

    # Second call is a no-op (wanted == existing) — early return branch.
    before = list(api.data["sources"])
    api._reconcile_probe_offset_sources()
    assert api.data["sources"] == before


@pytest.mark.asyncio
async def test_control_fetch_data_reconciles(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _control_api(probes=[{"type": "temperature", "uid": "0xT"}])
    monkeypatch.setattr(ReefBeatAPI, "fetch_data", AsyncMock(return_value={"ok": 1}))
    result = await api.fetch_data()
    assert result == {"ok": 1}
    # The dynamic offset source was registered during reconciliation.
    assert "/probe/offset?type=temperature&uid=0xT" in _source_names(api)


# ===========================================================================
# ReefPowerAPI
# ===========================================================================


def test_power_temperature_offset_reads_source() -> None:
    api = _power_api(temperature=25.0)
    api.data["sources"].append(
        {"name": "/temperature/config", "type": "data", "data": {"offset": -0.2}}
    )
    assert api.temperature_offset() == -0.2


@pytest.mark.asyncio
async def test_power_set_reset_offset() -> None:
    api = _power_api()
    await api.set_temperature_offset(0.4)
    api.http_send.assert_awaited_with("/probe/offset", {"offset": 0.4}, "post")
    await api.reset_temperature_offset()
    api.http_send.assert_awaited_with("/probe/offset", None, "delete")


@pytest.mark.asyncio
async def test_power_install_temperature_success_and_remove() -> None:
    api = _power_api()
    api.http_send = AsyncMock(return_value={"json": {"uid": "0xNEW"}})
    api.fetch_config = AsyncMock()  # avoid a real GET for the polled sources
    await api.install_temperature()

    # 3 calls: sensor/install, ble/off, then the temperature/config seed —
    # probe-info is polled via fetch_config, not http_send, so it does not
    # add to this count.
    assert api.http_send.await_count == 3
    api.http_send.assert_any_call("/ble/off", {"type": "temperature"}, "post")
    api.http_send.assert_any_call(
        "/temperature/config", dict(_TEMPERATURE_CONFIG_DEFAULTS), "put"
    )
    # Polled once for the one-shot install info, once more each to read back
    # the values just seeded into /temperature/config and the (still empty)
    # /temperature/subscriptions — the dashboard is stale at this point in
    # the flow (not yet re-fetched), so reconciliation alone would not have
    # registered them in time for this refresh.
    assert api.fetch_config.await_args_list == [
        call("/temperature-probe-info"),
        call("/temperature/config"),
        call("/temperature/subscriptions"),
    ]
    # The one-shot info source used to poll it is not left registered, but
    # both temperature sources now are (as "data" sources), ready to read.
    assert "/temperature-probe-info" not in _source_names(api)
    for name in ("/temperature/config", "/temperature/subscriptions"):
        source = next(s for s in api.data["sources"] if s["name"] == name)
        assert source["type"] == "data"

    # A second install (e.g. after a swap) with the sources already
    # registered (a prior dashboard refresh had already reconciled them in)
    # must not add them twice.
    api.http_send = AsyncMock(return_value={"json": {"uid": "0xNEW2"}})
    api.fetch_config = AsyncMock()
    await api.install_temperature()
    for name in ("/temperature/config", "/temperature/subscriptions"):
        assert sum(1 for s in api.data["sources"] if s["name"] == name) == 1

    api.http_send = AsyncMock(return_value={"json": {}})
    api.fetch_config = AsyncMock()
    await api.install_temperature()  # no uid -> single call, nothing seeded
    assert api.http_send.await_count == 1
    api.fetch_config.assert_not_awaited()

    await api.remove_temperature()
    api.http_send.assert_awaited_with("/sensor", None, "delete")


@pytest.mark.asyncio
async def test_power_remove_temperature_drops_sources_immediately() -> None:
    """remove_temperature() must not wait for the next refresh's
    reconciliation (gated on /dashboard.temperature, which can lag) to stop
    polling /temperature/config and /temperature/subscriptions — otherwise
    they keep getting requested (and erroring, once the probe is gone) for
    a while after the removal.
    """
    api = _power_api(temperature=25.0)
    api.data["sources"].extend(
        [
            {"name": "/temperature/config", "type": "data", "data": {"offset": 0}},
            {"name": "/temperature/subscriptions", "type": "data", "data": {}},
        ]
    )
    api.http_send = AsyncMock(return_value={"json": {}})

    await api.remove_temperature()

    assert "/temperature/config" not in _source_names(api)
    assert "/temperature/subscriptions" not in _source_names(api)


@pytest.mark.asyncio
async def test_power_remove_temperature_tolerates_already_absent_sources() -> None:
    """No prior install (or already removed) -> nothing to drop, no crash."""
    api = _power_api()
    api.http_send = AsyncMock(return_value={"json": {}})
    await api.remove_temperature()
    assert "/temperature/config" not in _source_names(api)
    assert "/temperature/subscriptions" not in _source_names(api)


def test_power_reconcile_temperature_sources_add_and_remove() -> None:
    # Probe present but sources missing -> both added as "data" sources
    # (not "config"), so they refresh on every poll regardless of
    # live_config_update.
    api = _power_api(temperature=25.0)
    api._reconcile_temperature_sources()
    for name in ("/temperature/config", "/temperature/subscriptions"):
        assert name in _source_names(api)
        source = next(s for s in api.data["sources"] if s["name"] == name)
        assert source["type"] == "data"

    # Probe absent but sources present -> both removed (no probe -> the
    # endpoints 404, so they must not be registered).
    api2 = _power_api(temperature=None)
    api2.data["sources"].extend(
        [
            {"name": "/temperature/config", "type": "data", "data": ""},
            {"name": "/temperature/subscriptions", "type": "data", "data": ""},
        ]
    )
    api2._reconcile_temperature_sources()
    for name in ("/temperature/config", "/temperature/subscriptions"):
        assert name not in _source_names(api2)


@pytest.mark.asyncio
async def test_power_fetch_data_reconciles(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _power_api(temperature=25.0)
    monkeypatch.setattr(ReefBeatAPI, "fetch_data", AsyncMock(return_value={"ok": 2}))
    result = await api.fetch_data()
    assert result == {"ok": 2}
    assert "/temperature/config" in _source_names(api)
    assert "/temperature/subscriptions" in _source_names(api)


def test_power_temperature_offset_survives_probe_swap() -> None:
    """A physical probe swap (remove then re-pair) must never leak a stale
    reading: RSPOWER has at most one temperature probe, so the offset entity
    is keyed by the hub's serial (not a probe uid) and never recreated — the
    ``/temperature/config`` source is explicitly volatile-marked precisely so
    this read is safe across a swap, without any rename/history logic.
    """
    api = _power_api(temperature=25.0)
    api.data["sources"].append(
        {"name": "/temperature/config", "type": "data", "data": {"offset": 0.3}}
    )
    assert api.temperature_offset() == 0.3

    # Probe unplugged: reconciliation (run by fetch_data on every refresh)
    # drops the config source. The very next read must return None, not the
    # cached 0.3 — proving the path is not positionally cached.
    api.data["sources"] = [
        s for s in api.data["sources"] if s["name"] != "/temperature/config"
    ]
    api.data["sources"][0]["data"]["temperature"] = None  # /dashboard entry
    api._reconcile_temperature_sources()
    assert api.temperature_offset() is None

    # A different probe is paired in its place: reconciliation re-adds the
    # source and the very next read must return its (different) fresh value,
    # not the stale None from the moment before.
    api.data["sources"][0]["data"]["temperature"] = 24.0
    api._reconcile_temperature_sources()
    new_source = next(
        s for s in api.data["sources"] if s["name"] == "/temperature/config"
    )
    new_source["data"] = {"offset": -0.6}
    assert api.temperature_offset() == -0.6
