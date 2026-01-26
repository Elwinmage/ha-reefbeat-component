from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from custom_components.redsea.reefbeat.run import ReefRunAPI


@dataclass
class _FakeSession:
    """Minimal aiohttp session stub for unit tests."""


@pytest.mark.asyncio
async def test_run_push_values_pump_wraps_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    # Seed payload for the existing /pump/settings source created by ReefRunAPI
    api.set_data(
        "$.sources[?(@.name=='/pump/settings')].data",
        {"pump_1": {"ti": 1}, "pump_2": {"ti": 2}},
    )

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/pump/settings", method="put", pump=2)

    assert sent == [("http://192.0.2.30/pump/settings", {"pump_2": {"ti": 2}}, "put")]


@pytest.mark.asyncio
async def test_run_push_values_no_pump_strips_pump_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    # The code reads from /pump/settings regardless of requested source
    api.set_data(
        "$.sources[?(@.name=='/pump/settings')].data",
        {"pump_1": {"ti": 1}, "pump_2": {"ti": 2}, "foo": "bar"},
    )

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/pump/settings", method="put", pump=None)

    assert sent == [("http://192.0.2.30/pump/settings", {"foo": "bar"}, "put")]


@pytest.mark.asyncio
async def test_run_push_values_other_source_uses_generic_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    api.add_source("/x", "data", {"a": 1})

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/x", method="post")

    assert sent == [("http://192.0.2.30/x", {"a": 1}, "post")]


@pytest.mark.asyncio
async def test_run_push_values_non_dict_payload_returns_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    # Seed pump/settings to a non-dict, so the error branch triggers.
    api.set_data("$.sources[?(@.name=='/pump/settings')].data", "oops")

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/pump/settings")

    assert sent == []


@pytest.mark.asyncio
async def test_run_push_values_unknown_source_payload_none_returns_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefRunAPI(
        ip="192.0.2.30",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/does-not-exist")
    assert sent == []
