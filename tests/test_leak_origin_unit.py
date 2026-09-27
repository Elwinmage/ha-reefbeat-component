"""Where the water of a ReefSense leak probe comes from.

``/dashboard`` only says whether a leak probe is wet (``detected``). The
origin is in the probe's own reading, ``GET /probe?type=leak&uid=…``:
``{"name", "ec", "status", "leak_status"}`` with ``leak_status`` one of
``dry`` / ``aquarium_water_leak`` / ``rodi_water_leak`` (the ReefBeat app's
ControlLeakStatus). The reading is kept apart from the dashboard, the probe
is read on its own as soon as it turns wet, and two sensors expose it.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.redsea.coordinator import ReefControlCoordinator
from custom_components.redsea.reefbeat.api import ReefBeatAPI
from custom_components.redsea.reefbeat.control import ReefControlAPI
from custom_components.redsea.sensor import _build_probe_descriptions


def _api(probes: Any) -> Any:
    api = ReefControlAPI.__new__(ReefControlAPI)
    api.data = {
        "sources": [{"name": "/dashboard", "type": "data", "data": {"probes": probes}}]
    }
    api._data_db = {}
    api._base_url = "http://test"
    api.quick_refresh = None
    api._live_config_update = False
    return api


def _leak(detected: Any, uid: str = "0x0032B") -> dict[str, Any]:
    return {"type": "leak", "uid": uid, "name": "Leak 32B", "detected": detected}


# ── Reading ──────────────────────────────────────────────────────────────────


def test_reading_turns_the_origin_into_detected() -> None:
    wet = ReefControlAPI.probe_reading_updates(
        "leak", {"leak_status": "aquarium_water_leak", "status": "connected"}
    )
    assert wet == {"status": "connected", "detected": True}
    assert ReefControlAPI.probe_reading_updates(
        "leak", {"leak_status": "rodi_water_leak"}
    ) == {"detected": True}
    assert ReefControlAPI.probe_reading_updates("leak", {"leak_status": "dry"}) == {
        "detected": False
    }


@pytest.mark.asyncio
async def test_read_probe_keeps_the_origin() -> None:
    """Captured on a real hub: a dry leak probe."""
    api = _api([_leak(False)])
    api.http_get = AsyncMock(
        return_value={
            "ok": True,
            "json": {
                "name": "Leak 32B",
                "ec": 2,
                "status": "connected",
                "leak_status": "dry",
            },
        }
    )
    assert await api.read_probe("leak", "0x0032B") is True
    assert api.leak_conductivity("0x0032B") == 2.0
    # Survives the next dashboard poll, which replaces the probe entry
    api.data["sources"][0]["data"] = {"probes": [_leak(True)]}
    api._leak_readings()["0x0032B"]["leak_status"] = "rodi_water_leak"
    assert api.leak_status("0x0032B") == "rodi_water_leak"


# ── Status ───────────────────────────────────────────────────────────────────


def test_leak_status() -> None:
    api = _api([_leak(False)])
    assert api.leak_status("0x0032B") == "dry"
    assert api.leak_status("0xOTHER") is None
    api.data["sources"][0]["data"] = {"probes": [_leak(True)]}
    # Wet, not read yet
    assert api.leak_status("0x0032B") is None
    api._leak_readings()["0x0032B"] = {"leak_status": "aquarium_water_leak"}
    assert api.leak_status("0x0032B") == "aquarium_water_leak"
    # A stale dry reading says nothing about a new leak
    api._leak_readings()["0x0032B"] = {"leak_status": "dry"}
    assert api.leak_status("0x0032B") is None
    api.data["sources"][0]["data"] = {"probes": [_leak("maybe")]}
    assert api.leak_status("0x0032B") is None


def test_leak_conductivity() -> None:
    api = _api([_leak(False)])
    assert api.leak_conductivity("0x0032B") is None
    api._leak_readings()["0x0032B"] = {"ec": "x"}
    assert api.leak_conductivity("0x0032B") is None
    api._leak_readings()["0x0032B"] = {"ec": 1540}
    assert api.leak_conductivity("0x0032B") == 1540.0


# ── Reading on a new leak ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_wet_probe_is_read_once_per_leak() -> None:
    api = _api([_leak(True), {"type": "ph", "uid": "0x1"}, "junk"])
    api.read_probe = AsyncMock(return_value=True)
    await api._read_new_leaks()
    await api._read_new_leaks()
    api.read_probe.assert_awaited_once_with("leak", "0x0032B")
    # Dried, then wet again: a new leak, read again
    api.data["sources"][0]["data"] = {"probes": [_leak(False)]}
    await api._read_new_leaks()
    api.data["sources"][0]["data"] = {"probes": [_leak(True)]}
    await api._read_new_leaks()
    assert api.read_probe.await_count == 2


@pytest.mark.asyncio
async def test_no_probe_list_reads_nothing() -> None:
    api = _api(None)
    api.read_probe = AsyncMock()
    await api._read_new_leaks()
    api.read_probe.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_data_reads_new_leaks(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _api([_leak(True)])
    monkeypatch.setattr(ReefBeatAPI, "fetch_data", AsyncMock(return_value={"ok": 1}))
    api.read_probe = AsyncMock(return_value=True)
    assert await api.fetch_data() == {"ok": 1}
    api.read_probe.assert_awaited_once_with("leak", "0x0032B")


# ── Entities ─────────────────────────────────────────────────────────────────


def test_leak_probe_sensors() -> None:
    descs = {d.key: d for d in _build_probe_descriptions(_leak(False))}
    status = descs["probe_leak_0x0032b_leak_status"]
    conductivity = descs["probe_leak_0x0032b_conductivity"]
    assert status.translation_key == "probe_leak_status"
    assert status.options == ["dry", "aquarium_water_leak", "rodi_water_leak"]
    assert conductivity.translation_key == "probe_leak_conductivity"

    device = MagicMock()
    device.leak_status.return_value = "aquarium_water_leak"
    device.leak_conductivity.return_value = 1540.0
    assert status.value_fn(device) == "aquarium_water_leak"
    assert conductivity.value_fn(device) == 1540.0
    device.leak_status.assert_called_with("0x0032B")


def test_coordinator_delegates_to_the_api() -> None:
    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = MagicMock()
    coord.my_api.leak_status.return_value = "dry"
    coord.my_api.leak_conductivity.return_value = 2.0
    assert coord.leak_status("0x1") == "dry"
    assert coord.leak_conductivity("0x1") == 2.0
