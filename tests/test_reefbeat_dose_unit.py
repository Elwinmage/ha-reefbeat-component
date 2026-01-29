from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from custom_components.redsea.reefbeat.dose import ReefDoseAPI


@dataclass
class _FakeSession:
    """Minimal aiohttp session stub for unit tests."""


@pytest.mark.asyncio
async def test_dose_unknown_head_count_sets_empty_head_dict() -> None:
    api = ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=3,
    )
    local = api.data.get("local")
    assert isinstance(local, dict)
    assert "head" in local


@pytest.mark.asyncio
async def test_dose_init_coerces_local_to_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    # Hit the branch where ReefDoseAPI sees a non-dict `local`.
    from custom_components.redsea.reefbeat import dose as dose_mod

    orig_init = dose_mod.ReefBeatAPI.__init__

    def _init(self: Any, ip: str, live: bool, session: Any) -> None:
        orig_init(self, ip, live, session)
        self.data["local"] = "oops"

    monkeypatch.setattr(dose_mod.ReefBeatAPI, "__init__", _init)

    api = dose_mod.ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=2,
    )
    assert isinstance(api.data.get("local"), dict)


@pytest.mark.asyncio
async def test_dose_press_with_head_sends_manual_dose_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=2,
    )

    # Override manual_dose in local cache
    api.set_data("$.local.head.1.manual_dose", 9)

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.press("manual", head=1)

    assert sent == [
        (
            "http://192.0.2.40/head/1/manual",
            {"manual_dose_scheduled": True, "volume": 9},
            "post",
        )
    ]


@pytest.mark.asyncio
async def test_dose_press_without_head_posts_empty_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=2,
    )

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.press("reset", head=None)

    assert sent == [("http://192.0.2.40/reset", {}, "post")]


@pytest.mark.asyncio
async def test_dose_calibration_end_setup_enables_bundle_when_supported_uid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=2,
    )

    # Populate existing sources created by ReefDoseAPI/base API
    api.set_data(
        "$.sources[?(@.name=='/head/1/settings')].data",
        {"supplement": {"uid": "6b7d2c15-0d25-4447-b089-854ef6ba99f2"}},
    )
    api.set_data("$.sources[?(@.name=='/dashboard')].data", {"bundled_heads": False})

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.calibration("end-setup", head=1, param={})

    assert sent[0] == ("http://192.0.2.40/head/1/end-setup", {}, "post")
    assert sent[1] == (
        "http://192.0.2.40/bundle/settings",
        {"bundled_heads": True, "auto_fill_schedule": False},
        "put",
    )


@pytest.mark.asyncio
async def test_dose_push_values_head_strips_bundle_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=2,
    )

    api.set_data(
        "$.sources[?(@.name=='/head/1/settings')].data",
        {"supplement": 1, "is_food_head": True, "food_delay": 1, "keep": 123},
    )
    api.set_data("$.sources[?(@.name=='/dashboard')].data", {"bundled_heads": True})

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values(head=1)

    assert sent == [("http://192.0.2.40/head/1/settings", {"keep": 123}, "put")]


@pytest.mark.asyncio
async def test_dose_set_bundle_posts_to_bundle_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=2,
    )

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.set_bundle({"step": 1})

    assert sent == [("http://192.0.2.40/bundle/setup", {"step": 1}, "post")]


@pytest.mark.asyncio
async def test_dose_push_values_head_payload_none_returns_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=2,
    )

    api.set_data("$.sources[?(@.name=='/head/1/settings')].data", None)

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values(head=1)
    assert sent == []


@pytest.mark.asyncio
async def test_dose_push_values_source_payload_none_returns_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=2,
    )

    api.set_data("$.sources[?(@.name=='/device-settings')].data", None)

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values(source="/device-settings")
    assert sent == []


@pytest.mark.asyncio
async def test_dose_push_values_source_success(monkeypatch: pytest.MonkeyPatch) -> None:
    api = ReefDoseAPI(
        ip="192.0.2.40",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
        heads_nb=2,
    )

    api.set_data("$.sources[?(@.name=='/device-settings')].data", {"x": 1})

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "put"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.push_values(source="/device-settings", method="put")
    assert sent == [("http://192.0.2.40/device-settings", {"x": 1}, "put")]
