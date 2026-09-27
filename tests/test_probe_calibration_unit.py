"""Multi-point calibration of RSCONTROL pH and EC probes.

The steps follow the ReefBeat app (``BaseControlProbeCalibrationActivity``):
enter, then per point start it and poll its status, then exit. Driven by a
card through the ``redsea.probe_calibration`` service.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.redsea.coordinator import ReefControlCoordinator
from custom_components.redsea.reefbeat.control import ReefControlAPI


def _api() -> Any:
    api = ReefControlAPI.__new__(ReefControlAPI)
    api.data = {"sources": []}
    api._data_db = {}
    api._base_url = "http://test"
    api.http_send = AsyncMock(return_value={"ok": True, "status": 200, "json": {}})
    api.http_get = AsyncMock(
        return_value={
            "ok": True,
            "status": 200,
            "json": {
                "calibration_status": "in_progress",
                "time_left": 42,
                "stability_progress": "65",
            },
        }
    )
    return api


# ── API ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enter_sends_the_time(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _api()
    monkeypatch.setattr("time.time", lambda: 1790434790.6)
    result = await api.probe_calibration("enter", "ph", "0x00B39")
    api.http_send.assert_awaited_once_with(
        "/probe/calibration-enter?type=ph&uid=0x00B39", {"time": 1790434790}, "post"
    )
    assert result == {"ok": True, "status_code": 200, "json": {}}


@pytest.mark.asyncio
async def test_ph_point_carries_the_rated_temperature() -> None:
    api = _api()
    await api.probe_calibration("point", "ph", "0x1", "mid", 7.01, 25.0)
    api.http_send.assert_awaited_once_with(
        "/probe/calibration-point-start?type=ph&uid=0x1",
        {"point": "MID", "solution_value": 7.01, "solution_rated_temp": 25},
        "post",
    )


@pytest.mark.asyncio
async def test_ec_point_has_no_rated_temperature() -> None:
    api = _api()
    await api.probe_calibration("point", "ec", "0x2", "MID", 53.1)
    api.http_send.assert_awaited_once_with(
        "/probe/calibration-point-start?type=ec&uid=0x2",
        {"point": "MID", "solution_value": 53.1},
        "post",
    )


@pytest.mark.asyncio
async def test_malformed_point_is_refused() -> None:
    api = _api()
    assert (await api.probe_calibration("point", "ph", "0x1", "TOP", 7.0))["ok"] is (
        False
    )
    assert (await api.probe_calibration("point", "ph", "0x1", "MID", None))[
        "ok"
    ] is False
    api.http_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_status_and_exit() -> None:
    api = _api()
    status = await api.probe_calibration("status", "ec", "0x2")
    api.http_get.assert_awaited_once_with("/probe/calibration-status?type=ec&uid=0x2")
    assert status["json"]["time_left"] == 42
    await api.probe_calibration("exit", "ec", "0x2")
    api.http_send.assert_awaited_once_with(
        "/probe/calibration-exit?type=ec&uid=0x2", {}, "post"
    )


@pytest.mark.asyncio
async def test_unknown_action_and_no_answer() -> None:
    api = _api()
    assert (await api.probe_calibration("dance", "ph", "0x1"))["ok"] is False
    api.http_send = AsyncMock(return_value=None)
    assert await api.probe_calibration("exit", "ph", "0x1") == {
        "ok": False,
        "status_code": None,
        "json": None,
    }


# ── Coordinator ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_coordinator_reads_back_on_exit() -> None:
    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = MagicMock()
    coord.my_api.probe_calibration = AsyncMock(return_value={"ok": True})
    coord.async_request_refresh = AsyncMock()

    assert await coord.async_probe_calibration("status", "ph", "0x1") == {"ok": True}
    coord.async_request_refresh.assert_not_awaited()

    await coord.async_probe_calibration("point", "ph", "0x1", "HIGH", 10.0, 25)
    coord.my_api.probe_calibration.assert_awaited_with(
        "point", "ph", "0x1", "HIGH", 10.0, 25
    )

    await coord.async_probe_calibration("exit", "ph", "0x1")
    coord.async_request_refresh.assert_awaited_once_with(config=True)


# ── Service ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_probe_calibration_service(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    import custom_components.redsea as redsea_init

    handlers: dict[str, Any] = {}

    def _async_register(
        self: Any, domain: str, service: str, service_func: Any, *a: Any, **k: Any
    ) -> None:
        handlers[f"{domain}.{service}"] = service_func

    monkeypatch.setattr(
        type(hass.services), "async_register", _async_register, raising=True
    )
    assert await redsea_init.async_setup(hass, {}) is True
    handler = handlers[f"{redsea_init.DOMAIN}.probe_calibration"]

    class _Hub:
        async_probe_calibration = AsyncMock(return_value={"ok": True})

    monkeypatch.setattr(redsea_init, "ReefControlCoordinator", _Hub)
    hub = _Hub()
    hass.data.setdefault(redsea_init.DOMAIN, {})["entry"] = hub
    hass.data[redsea_init.DOMAIN]["other"] = object()

    async def call(**data: Any) -> Any:
        return await handler(SimpleNamespace(data=data))

    base = {"device_id": "entry", "probe_type": "ph", "probe_uid": "0x1"}
    assert await call(**base, action="point", point="MID", solution_value=7.0) == {
        "ok": True
    }
    hub.async_probe_calibration.assert_awaited_once_with(
        "point", "ph", "0x1", "MID", 7.0, None
    )

    assert (await call(**{**base, "device_id": "other"}, action="enter"))["ok"] is False
    assert (await call(device_id="entry", probe_type="ph", action="enter"))[
        "ok"
    ] is False
    assert (await call(**base, action="dance"))["ok"] is False

    hub.async_probe_calibration.side_effect = RuntimeError
    assert await call(**base, action="exit") == {
        "ok": False,
        "error": "request failed",
    }
