from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from custom_components.redsea.const import (
    MAT_MAX_ROLL_DIAMETERS,
    MAT_MIN_ROLL_DIAMETER,
    MAT_ROLL_THICKNESS,
    MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME,
)
from custom_components.redsea.reefbeat.mat import ReefMatAPI


@dataclass
class _FakeSession:
    """Minimal aiohttp session stub for unit tests."""


def test_mat_as_float_coercions() -> None:
    assert ReefMatAPI._as_float(True, 1.0) == 1.0
    assert ReefMatAPI._as_float(False, 1.0) == 1.0
    assert ReefMatAPI._as_float(3, 1.0) == 3.0
    assert ReefMatAPI._as_float(3.5, 1.0) == 3.5
    assert ReefMatAPI._as_float("x", 1.0) == 1.0


@pytest.mark.asyncio
async def test_mat_new_roll_new_roll_uses_model_max_diameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefMatAPI(
        ip="192.0.2.50",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    # Add /configuration source with a known model
    model = next(iter(MAT_MAX_ROLL_DIAMETERS.keys()))
    api.set_data("$.sources[?(@.name=='/configuration')].data", {"model": model})

    # diameter at min -> "New Roll"
    api.set_data(MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME, float(MAT_MIN_ROLL_DIAMETER))

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.new_roll()

    expected = {
        "external_diameter": float(MAT_MAX_ROLL_DIAMETERS[model]),
        "name": "New Roll",
        "thickness": MAT_ROLL_THICKNESS,
        "is_partial": False,
    }
    assert sent == [("http://192.0.2.50/new-roll", expected, "post")]


@pytest.mark.asyncio
async def test_mat_new_roll_started_roll_uses_provided_diameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefMatAPI(
        ip="192.0.2.50",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    api.set_data("$.sources[?(@.name=='/configuration')].data", {"model": "unknown"})
    api.set_data(MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME, 42)

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(
        url: str, payload: Any = None, method: str = "post"
    ) -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.new_roll()

    expected = {
        "external_diameter": 42.0,
        "name": "Started Roll",
        "thickness": MAT_ROLL_THICKNESS,
        "is_partial": True,
    }
    assert sent == [("http://192.0.2.50/new-roll", expected, "post")]


@pytest.mark.asyncio
async def test_mat_init_coerces_local_to_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    # Hit the branch where ReefMatAPI sees a non-dict `local`.
    from custom_components.redsea.reefbeat import mat as mat_mod

    orig_init = mat_mod.ReefBeatAPI.__init__

    def _init(self: Any, ip: str, live: bool, session: Any) -> None:
        orig_init(self, ip, live, session)
        self.data["local"] = "oops"

    monkeypatch.setattr(mat_mod.ReefBeatAPI, "__init__", _init)

    api = ReefMatAPI(
        ip="192.0.2.50",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )
    assert isinstance(api.data.get("local"), dict)


@pytest.mark.asyncio
async def test_mat_new_roll_unknown_model_returns_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReefMatAPI(
        ip="192.0.2.50",
        live_config_update=False,
        session=cast(Any, _FakeSession()),
    )

    # Force "new roll" path and unknown model.
    api.set_data("$.sources[?(@.name=='/configuration')].data.model", "unknown")
    api.set_data(MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME, float(MAT_MIN_ROLL_DIAMETER))

    sent: list[tuple[str, Any, str]] = []

    async def _fake_http_send(url: str, payload: Any = None, method: str = "post") -> Any:
        sent.append((url, payload, method))
        return None

    monkeypatch.setattr(api, "_http_send", _fake_http_send)

    await api.new_roll()

    assert sent == []
