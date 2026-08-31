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


@pytest.mark.asyncio
async def test_ato_push_values_puts_buzzer(monkeypatch: pytest.MonkeyPatch) -> None:
    """The leak buzzer rides along with `auto_fill` on the same PUT."""
    api = ReefATOAPI(
        ip="192.0.2.60",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    # The buzzer is read from /dashboard even though it is written to
    # /configuration, so the value has to be seeded there.
    api.set_data("$.sources[?(@.name=='/configuration')].data", {"auto_fill": True})
    api.set_data(
        "$.sources[?(@.name=='/dashboard')].data",
        {"leak_sensor": {"buzzer_enabled": False, "enabled": True}},
    )

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/configuration", "put")

    assert sent == [
        (
            "http://192.0.2.60/configuration",
            {
                "auto_fill": True,
                "buzzer": {"enabled": False},
                "leak": {"sensor_enabled": True},
            },
            "put",
        )
    ]


@pytest.mark.asyncio
async def test_ato_push_values_omits_unknown_leak_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A device that never reported the leak settings must not be sent nulls.

    The firmware merges partial configurations, so leaving the key out keeps
    the current device setting; sending `{"enabled": null}` would clear it.
    """
    api = ReefATOAPI(
        ip="192.0.2.60",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    # /dashboard never reported a leak_sensor: nothing to send.
    api.set_data("$.sources[?(@.name=='/configuration')].data", {"auto_fill": False})

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values("/configuration", "put")

    assert sent == [("http://192.0.2.60/configuration", {"auto_fill": False}, "put")]


def test_ato_configuration_is_a_polled_data_source() -> None:
    """`/configuration` must be polled, not fetched on demand.

    It holds `auto_fill`, which appears nowhere on `/dashboard`: as a "config"
    source it would only be read at startup and on `fetch_config`, so a change
    made from the Red Sea app would sit stale in Home Assistant.
    """
    api = ReefATOAPI(
        ip="192.0.2.60",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    sources = {s["name"]: s["type"] for s in api.data["sources"]}
    assert sources["/configuration"] == "data"
    assert sources["/dashboard"] == "data"

    # The fetch_config button still has sources to refresh, so it keeps its
    # meaning for the rest of the device.
    assert "config" in sources.values()
