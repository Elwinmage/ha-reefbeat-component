from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from custom_components.redsea.reefbeat.ato import ReefATOAPI


@dataclass
class _FakeSession:
    """Minimal aiohttp session stub for unit tests."""


@pytest.mark.asyncio
async def test_ato_resume_posts(monkeypatch: pytest.MonkeyPatch) -> None:
    api = ReefATOAPI(
        ip="192.0.2.60",
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

    await api.resume()

    assert sent == [("http://192.0.2.60/resume", None, "post")]


@pytest.mark.asyncio
async def test_ato_push_values_puts_auto_fill(monkeypatch: pytest.MonkeyPatch) -> None:
    api = ReefATOAPI(
        ip="192.0.2.60",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    # The ATO wrapper creates the /configuration source with `data=""`.
    # Seed it to a dict first so JSONPath updates work.
    api.set_data("$.sources[?(@.name=='/configuration')].data", {"auto_fill": True})

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/configuration", "put")

    assert sent == [("http://192.0.2.60/configuration", {"auto_fill": True}, "put")]


@pytest.mark.asyncio
async def test_ato_set_volume_left_posts_volume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefATOAPI(
        ip="192.0.2.60",
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

    await api.set_volume_left(1234)

    assert sent == [("http://192.0.2.60/update-volume", {"volume": 1234}, "post")]
