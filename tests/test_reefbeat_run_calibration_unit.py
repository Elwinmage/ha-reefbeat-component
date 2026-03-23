"""Unit tests for ReefRunAPI calibration and pump management methods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from custom_components.redsea.reefbeat.run import ReefRunAPI


@dataclass
class _FakeSession:
    """Minimal aiohttp session stub for unit tests."""


def _make_api(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ReefRunAPI, list[tuple[str, Any, str]]]:
    """Create a ReefRunAPI with a fake _http_send that records calls."""
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )
    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)
    return api, sent


# -- Calibration tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_calibration_start_default_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, sent = _make_api(monkeypatch)
    await api.calibration_start()
    assert sent == [("http://192.0.2.30/calibration/2", {}, "post")]


@pytest.mark.asyncio
async def test_calibration_start_custom_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, sent = _make_api(monkeypatch)
    await api.calibration_start(point=1)
    assert sent == [("http://192.0.2.30/calibration/1", {}, "post")]


@pytest.mark.asyncio
async def test_calibration_skim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, sent = _make_api(monkeypatch)
    await api.calibration_skim()
    assert sent == [("http://192.0.2.30/calibration/skim", {}, "post")]


@pytest.mark.asyncio
async def test_calibration_cup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, sent = _make_api(monkeypatch)
    await api.calibration_cup()
    assert sent == [("http://192.0.2.30/calibration/cup", {}, "post")]


@pytest.mark.asyncio
async def test_calibration_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, sent = _make_api(monkeypatch)
    await api.calibration_end()
    assert sent == [("http://192.0.2.30/calibration", None, "delete")]


# -- Pump detection tests -----------------------------------------------------


@pytest.mark.asyncio
async def test_detect_pump_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    async def _fake_http_get(access_path: str) -> dict[str, Any] | None:
        return {"ok": True, "json": {"type": "skimmer", "model": "rsk-300"}}

    monkeypatch.setattr(api, "http_get", _fake_http_get)
    result = await api.detect_pump(2)
    assert result == {"type": "skimmer", "model": "rsk-300"}


@pytest.mark.asyncio
async def test_detect_pump_failure_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    async def _fake_http_get(access_path: str) -> dict[str, Any] | None:
        return None

    monkeypatch.setattr(api, "http_get", _fake_http_get)
    result = await api.detect_pump(1)
    assert result is None


@pytest.mark.asyncio
async def test_detect_pump_not_ok_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    async def _fake_http_get(access_path: str) -> dict[str, Any] | None:
        return {"ok": False, "status": 500}

    monkeypatch.setattr(api, "http_get", _fake_http_get)
    result = await api.detect_pump(1)
    assert result is None


# -- Pump delete / configure tests --------------------------------------------


@pytest.mark.asyncio
async def test_delete_pump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, sent = _make_api(monkeypatch)
    await api.delete_pump(2)
    assert sent == [("http://192.0.2.30/pump/2/settings", None, "delete")]


@pytest.mark.asyncio
async def test_configure_pump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, sent = _make_api(monkeypatch)
    await api.configure_pump(1, "My Return", "return-12000", "return")
    assert len(sent) == 1
    url, payload, method = sent[0]
    assert url == "http://192.0.2.30/pump/settings"
    assert method == "put"
    assert payload == {
        "pump_1": {"name": "My Return", "model": "return-12000", "type": "return"}
    }


# -- Source registration tests ------------------------------------------------


def test_calibration_source_registered() -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )
    sources = [s["name"] for s in api.data["sources"]]
    assert "/calibration" in sources


def test_shortcuts_source_registered() -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )
    sources = [s["name"] for s in api.data["sources"]]
    assert "/pump/shortcuts" in sources
