"""Unit tests for on-demand probe readings (``GET /probe?type&uid``).

Covers the RSControl API mapping onto the cached ``/dashboard.probes``,
the coordinator wrappers (RSControl probes and RSPower local temperature),
and the per-probe "read now" buttons, which skip the post-press refresh.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

import custom_components.redsea.button as button_mod
from custom_components.redsea.coordinator import (
    ReefControlCoordinator,
    ReefPowerCoordinator,
)
from custom_components.redsea.reefbeat.control import ReefControlAPI
from custom_components.redsea.reefbeat.fusion import is_probe_disconnected
from custom_components.redsea.reefbeat.power import ReefPowerAPI

# Payloads captured from a real RSCONTROLPRO.
EC_READING = {
    "name": "Salinity temp",
    "status": "connected",
    "ec": 0,
    "ppt": 0,
    "sg": 0,
    "temperature": {"value": 28.7},
}
PH_READING = {
    "name": "pH",
    "value": 8.111217498779297,
    "status": "connected",
    "temperature": {"value": 28},
}
ORP_READING = {"name": "ORP", "status": "connected", "value": 165}
ATO_READING = {
    "name": "ATO",
    "ato_sensor_status": "below",
    "status": "connected",
    "temperature": {"value": 28.2},
}
LEAK_READING = {"name": "Leak", "ec": 2, "status": "connected", "leak_status": "dry"}
TEMP_READING = {"name": "Temperature", "status": "connected", "value": 28.5677}


def _control_api(probes: list[dict[str, Any]] | Any) -> Any:
    api = ReefControlAPI.__new__(ReefControlAPI)
    api.data = {
        "sources": [{"name": "/dashboard", "type": "data", "data": {"probes": probes}}]
    }
    api._data_db = {}
    api._base_url = "http://test"
    return api


# ===========================================================================
# probe_reading_updates
# ===========================================================================


@pytest.mark.parametrize(
    ("ptype", "payload", "unit", "expected"),
    [
        (
            "ec",
            EC_READING,
            "ppt",
            {
                "status": "connected",
                "temp_value": 28.7,
                "ec": 0,
                "ppt": 0,
                "sg": 0,
                "value": 0,
            },
        ),
        # Unknown displayed unit: raw forms updated, `value` left alone.
        (
            "EC",
            EC_READING,
            None,
            {"status": "connected", "temp_value": 28.7, "ec": 0, "ppt": 0, "sg": 0},
        ),
        (
            "ph",
            PH_READING,
            None,
            {"status": "connected", "value": 8.111217498779297, "temp_value": 28},
        ),
        ("orp", ORP_READING, None, {"status": "connected", "value": 165}),
        (
            "ato",
            ATO_READING,
            None,
            {"status": "connected", "temp_value": 28.2, "water_level": "below"},
        ),
        ("leak", LEAK_READING, None, {"status": "connected", "detected": False}),
        (
            "leak",
            {"leak_status": "WET"},
            None,
            {"detected": True},
        ),
        # Unknown leak state: `detected` untouched.
        ("leak", {"leak_status": "maybe"}, None, {}),
        ("temperature", TEMP_READING, None, {"status": "connected", "value": 28.5677}),
        # Ill-typed fields are ignored (bool is not a number).
        (
            "ph",
            {"value": True, "status": 1, "temperature": {"value": "x"}},
            None,
            {},
        ),
        ("ato", {"ato_sensor_status": None}, None, {}),
    ],
)
def test_probe_reading_updates(
    ptype: str, payload: dict[str, Any], unit: str | None, expected: dict[str, Any]
) -> None:
    assert ReefControlAPI.probe_reading_updates(ptype, payload, unit) == expected


# ===========================================================================
# read_probe
# ===========================================================================


@pytest.mark.asyncio
async def test_read_probe_patches_cached_dashboard_entry() -> None:
    probes = [
        {"type": "ph", "uid": "0x00B39", "value": 8.0, "temp_value": 25},
        {"type": "ec", "uid": "0x00B39", "value": 35, "measurement_unit": "ppt"},
    ]
    api = _control_api(probes)
    api.http_get = AsyncMock(
        return_value={"ok": True, "status": 200, "json": EC_READING}
    )

    assert await api.read_probe("ec", "0x00B39") is True

    api.http_get.assert_awaited_once_with("/probe?type=ec&uid=0x00B39")
    # Same uid, other type: untouched.
    assert probes[0]["value"] == 8.0
    assert probes[1]["value"] == 0
    assert probes[1]["temp_value"] == 28.7
    assert probes[1]["status"] == "connected"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result",
    [
        None,
        {"ok": False, "status": 503},
        {"ok": True, "status": 200, "json": ["not", "a", "dict"]},
    ],
)
async def test_read_probe_failed_request(result: Any) -> None:
    probes = [{"type": "orp", "uid": "0x1", "value": 100}]
    api = _control_api(probes)
    api.http_get = AsyncMock(return_value=result)

    assert await api.read_probe("orp", "0x1") is False
    assert probes[0]["value"] == 100


@pytest.mark.asyncio
@pytest.mark.parametrize("probes", [[], "garbage", ["garbage"]])
async def test_read_probe_unknown_probe(probes: Any) -> None:
    api = _control_api(probes)
    api.http_get = AsyncMock(return_value={"ok": True, "json": ORP_READING})

    assert await api.read_probe("orp", "0x1") is False


@pytest.mark.asyncio
async def test_read_probe_without_usable_fields() -> None:
    probes = [{"type": "orp", "uid": "0x1", "value": 100}]
    api = _control_api(probes)
    api.http_get = AsyncMock(return_value={"ok": True, "json": {"name": "ORP"}})

    assert await api.read_probe("orp", "0x1") is False
    assert probes[0] == {"type": "orp", "uid": "0x1", "value": 100}


# ===========================================================================
# Coordinators
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("updated", "notified"), [(True, 1), (False, 0)])
async def test_control_coordinator_read_probe(updated: bool, notified: int) -> None:
    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = MagicMock()
    coord.my_api.read_probe = AsyncMock(return_value=updated)
    coord.async_update_listeners = MagicMock()

    await coord.async_read_probe("ph", "0x2")

    coord.my_api.read_probe.assert_awaited_once_with("ph", "0x2")
    assert coord.async_update_listeners.call_count == notified


@pytest.mark.asyncio
@pytest.mark.parametrize(("updated", "notified"), [(True, 1), (False, 0)])
async def test_power_coordinator_get_temperature(updated: bool, notified: int) -> None:
    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = MagicMock()
    coord.my_api.get_current_temperature = AsyncMock(return_value=updated)
    coord.async_update_listeners = MagicMock()

    await coord.get_current_temperature()

    coord.my_api.get_current_temperature.assert_awaited_once()
    assert coord.async_update_listeners.call_count == notified


# ===========================================================================
# RSPower local temperature (GET /temperature)
# ===========================================================================


def _power_api(temperature: Any) -> Any:
    api = ReefPowerAPI.__new__(ReefPowerAPI)
    api.data = {
        "sources": [
            {"name": "/dashboard", "type": "data", "data": {"temperature": temperature}}
        ]
    }
    api._data_db = {}
    api._base_url = "http://test"
    return api


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        # Payload captured from a real RSPOWER.
        ({"temperature": 28.636499404907227}, {"value": 28.636499404907227}),
        ({"temperature": 25}, {"value": 25}),
        ({"temperature": True}, {}),
        ({"temperature": "25.4"}, {}),
        ({"temperature": {"value": 25.4}}, {}),
        ({"temperature": None}, {}),
        ({}, {}),
        (["not", "a", "dict"], {}),
        (None, {}),
    ],
)
def test_temperature_reading_updates(payload: Any, expected: dict[str, Any]) -> None:
    assert ReefPowerAPI.temperature_reading_updates(payload) == expected


@pytest.mark.asyncio
async def test_power_reading_merges_into_dashboard_object() -> None:
    cached = {"value": 24.0, "status": "connected", "level": "acceptable", "uid": "x"}
    api = _power_api(cached)
    api.http_get = AsyncMock(
        return_value={"ok": True, "status": 200, "json": {"temperature": 25.4}}
    )

    assert await api.get_current_temperature() is True

    api.http_get.assert_awaited_once_with("/temperature")
    # Merged in place: the rest of the object is kept.
    assert api.data["sources"][0]["data"]["temperature"] is cached
    assert cached == {
        "value": 25.4,
        "status": "connected",
        "level": "acceptable",
        "uid": "x",
    }


@pytest.mark.asyncio
async def test_power_reading_keeps_bare_float_shape() -> None:
    api = _power_api(24.0)
    api.http_get = AsyncMock(return_value={"ok": True, "json": {"temperature": 25.4}})

    assert await api.get_current_temperature() is True
    assert api.data["sources"][0]["data"]["temperature"] == 25.4


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cached", "result"),
    [
        # No local probe known: nothing is created.
        (None, {"ok": True, "json": {"temperature": 25.4}}),
        # Unexpected cached shape.
        ("n/a", {"ok": True, "json": {"temperature": 25.4}}),
        # Failed or unusable requests.
        ({"value": 24.0}, None),
        ({"value": 24.0}, {"ok": False, "status": 503}),
        ({"value": 24.0}, {"ok": True, "json": {"temperature": None}}),
    ],
)
async def test_power_reading_not_applied(cached: Any, result: Any) -> None:
    api = _power_api(cached)
    api.http_get = AsyncMock(return_value=result)

    assert await api.get_current_temperature() is False
    assert api.data["sources"][0]["data"]["temperature"] == cached


# ===========================================================================
# Buttons
# ===========================================================================


class _FakeDevice:
    serial = "SERIAL"
    device_info: Any = None

    def __init__(self, probes: Any) -> None:
        self._probes = probes
        self.async_read_probe = AsyncMock()
        self.async_request_refresh = AsyncMock()
        self.probe_is_connected = MagicMock(return_value=True)

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self._probes


def test_control_probe_read_buttons_one_per_probe() -> None:
    device = _FakeDevice(
        [
            {"type": "ato", "uid": "0x0024E", "name": "ATO"},
            {"type": "ato", "uid": "0x0024F", "name": "ATO"},
            {"type": "ph", "uid": None},
            "garbage",
        ]
    )
    descs = button_mod._control_probe_read_buttons(cast(Any, device))

    assert [d.key for d in descs] == [
        "probe_ato_0x0024e_get_value",
        "probe_ato_0x0024f_get_value",
    ]
    assert all(d.translation_key == "probe_get_value" for d in descs)
    assert all(d.refresh_after is False for d in descs)
    # Same-type probes sharing a name are disambiguated.
    assert [
        cast(dict[str, str], d.translation_placeholders)["probe"] for d in descs
    ] == [
        "ATO",
        "ATO #2",
    ]
    assert descs[0].exists_fn(cast(Any, device)) is True


def test_control_probe_read_buttons_without_probes() -> None:
    assert button_mod._control_probe_read_buttons(cast(Any, _FakeDevice(None))) == ()


@pytest.mark.asyncio
async def test_probe_read_button_press_skips_refresh() -> None:
    device = _FakeDevice([{"type": "ec", "uid": "0x007BF", "name": "Salinity"}])
    desc = button_mod._control_probe_read_buttons(cast(Any, device))[0]
    entity = button_mod.ReefBeatButtonEntity(cast(Any, device), desc)

    await entity.async_press()

    device.async_read_probe.assert_awaited_once_with("ec", "0x007BF")
    device.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_power_get_temperature_button_skips_refresh() -> None:
    desc = next(d for d in button_mod.POWER_BUTTONS if d.key == "get_temperature")
    assert desc.refresh_after is False

    device = MagicMock()
    device.serial = "SERIAL"
    device.get_current_temperature = AsyncMock()
    device.async_request_refresh = AsyncMock()
    entity = button_mod.ReefBeatButtonEntity(device, desc)

    await entity.async_press()

    device.get_current_temperature.assert_awaited_once()
    device.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_other_buttons_still_refresh_after_press() -> None:
    desc = button_mod.ReefBeatButtonEntityDescription(
        key="k", translation_key="k", press_fn=None
    )
    device = MagicMock()
    device.serial = "SERIAL"
    device.async_request_refresh = AsyncMock()
    entity = button_mod.ReefBeatButtonEntity(device, desc)

    await entity.async_press()

    device.async_request_refresh.assert_awaited_once()


# ===========================================================================
# Unplugged probes (the hub answers 503 to every per-probe request)
# ===========================================================================


@pytest.mark.parametrize(
    ("probe", "expected"),
    [
        ({"status": "disconnected"}, True),
        ({"status": "Not_Connected"}, True),
        ({"status": "offline"}, True),
        ({"status": "connected"}, False),
        ({"status": "disabled"}, False),
        ({"status": None}, False),
        ({}, False),
        ("garbage", False),
    ],
)
def test_is_probe_disconnected(probe: Any, expected: bool) -> None:
    assert is_probe_disconnected(probe) is expected


def test_offset_source_dropped_while_probe_unplugged() -> None:
    probes: list[dict[str, Any]] = [
        {"type": "temperature", "uid": "0x000F7", "status": "disconnected"},
        {"type": "temperature", "uid": "0x00842", "status": "connected"},
    ]
    api = _control_api(probes)
    api.data["sources"].append(
        {
            "name": "/probe/offset?type=temperature&uid=0x000F7",
            "type": "config",
            "data": {"offset": 0.2},
        }
    )

    api._reconcile_probe_offset_sources()
    names = {s["name"] for s in api.data["sources"]}
    assert "/probe/offset?type=temperature&uid=0x000F7" not in names
    assert "/probe/offset?type=temperature&uid=0x00842" in names

    # Plugged back in: the source is registered again.
    probes[0]["status"] = "connected"
    api._reconcile_probe_offset_sources()
    names = {s["name"] for s in api.data["sources"]}
    assert "/probe/offset?type=temperature&uid=0x000F7" in names


@pytest.mark.parametrize(
    ("probes", "expected"),
    [
        ([{"type": "temperature", "uid": "0x1", "status": "connected"}], True),
        ([{"type": "temperature", "uid": "0x1"}], True),
        ([{"type": "temperature", "uid": "0x1", "status": "disconnected"}], False),
        ([{"type": "ph", "uid": "0x1", "status": "connected"}], False),
        ([], False),
    ],
)
def test_coordinator_probe_is_connected(
    probes: list[dict[str, Any]], expected: bool
) -> None:
    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = _control_api(probes)

    assert coord.probe_is_connected("temperature", "0x1") is expected


def test_probe_read_button_unavailable_while_unplugged() -> None:
    device = _FakeDevice([{"type": "temperature", "uid": "0x000F7", "name": "T"}])
    device.probe_is_connected.return_value = False
    desc = button_mod._control_probe_read_buttons(cast(Any, device))[0]

    assert desc.available_fn is not None
    assert desc.available_fn(cast(Any, device)) is False
    device.probe_is_connected.assert_called_once_with("temperature", "0x000F7")
