"""Unit tests for ReefRunCoordinator calibration and pump management methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant

import custom_components.redsea.coordinator as coord
from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry


def _make_entry(*, title: str = "RUN", ip: str = "192.0.2.10") -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={
            CONFIG_FLOW_IP_ADDRESS: ip,
            CONFIG_FLOW_HW_MODEL: "RSRUN",
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
    )


@dataclass
class _FakeRunAPI:
    """Fake API that records all calls for assertion."""

    calibration_start_calls: list[int] = field(default_factory=list)
    calibration_skim_called: int = 0
    calibration_cup_called: int = 0
    calibration_end_called: int = 0
    detect_pump_calls: list[int] = field(default_factory=list)
    delete_pump_calls: list[int] = field(default_factory=list)
    configure_pump_calls: list[tuple[int, str, str, str]] = field(default_factory=list)

    # Required by coordinator base class
    live_config_update: bool = False

    def set_live_config_update(self, enabled: bool) -> None:
        self.live_config_update = enabled

    async def calibration_start(self, point: int = 2) -> None:
        self.calibration_start_calls.append(point)

    async def calibration_skim(self) -> None:
        self.calibration_skim_called += 1

    async def calibration_cup(self) -> None:
        self.calibration_cup_called += 1

    async def calibration_end(self) -> None:
        self.calibration_end_called += 1

    async def detect_pump(self, pump: int) -> dict[str, Any] | None:
        self.detect_pump_calls.append(pump)
        return {"type": "skimmer", "model": "rsk-300"}

    async def delete_pump(self, pump: int) -> None:
        self.delete_pump_calls.append(pump)

    async def configure_pump(
        self, pump: int, name: str, model: str, pump_type: str
    ) -> None:
        self.configure_pump_calls.append((pump, name, model, pump_type))


@pytest.fixture(autouse=True)
def _patch_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        coord, "async_get_clientsession", lambda _hass: object(), raising=True
    )
    monkeypatch.setattr(
        coord, "ReefRunAPI", lambda *_a, **_k: _FakeRunAPI(), raising=True
    )


@pytest.mark.asyncio
async def test_calibration_start(hass: HomeAssistant) -> None:
    run = coord.ReefRunCoordinator(hass, cast(Any, _make_entry()))
    api = _FakeRunAPI()
    run.my_api = cast(Any, api)

    await run.calibration_start(2)
    assert api.calibration_start_calls == [2]


@pytest.mark.asyncio
async def test_calibration_skim(hass: HomeAssistant) -> None:
    run = coord.ReefRunCoordinator(hass, cast(Any, _make_entry()))
    api = _FakeRunAPI()
    run.my_api = cast(Any, api)

    await run.calibration_skim()
    assert api.calibration_skim_called == 1


@pytest.mark.asyncio
async def test_calibration_cup(hass: HomeAssistant) -> None:
    run = coord.ReefRunCoordinator(hass, cast(Any, _make_entry()))
    api = _FakeRunAPI()
    run.my_api = cast(Any, api)

    await run.calibration_cup()
    assert api.calibration_cup_called == 1


@pytest.mark.asyncio
async def test_calibration_end(hass: HomeAssistant) -> None:
    run = coord.ReefRunCoordinator(hass, cast(Any, _make_entry()))
    api = _FakeRunAPI()
    run.my_api = cast(Any, api)

    await run.calibration_end()
    assert api.calibration_end_called == 1


@pytest.mark.asyncio
async def test_detect_pump(hass: HomeAssistant) -> None:
    run = coord.ReefRunCoordinator(hass, cast(Any, _make_entry()))
    api = _FakeRunAPI()
    run.my_api = cast(Any, api)

    result = await run.detect_pump(2)
    assert api.detect_pump_calls == [2]
    assert result == {"type": "skimmer", "model": "rsk-300"}


@pytest.mark.asyncio
async def test_delete_pump(hass: HomeAssistant) -> None:
    run = coord.ReefRunCoordinator(hass, cast(Any, _make_entry()))
    api = _FakeRunAPI()
    run.my_api = cast(Any, api)

    await run.delete_pump(1)
    assert api.delete_pump_calls == [1]


@pytest.mark.asyncio
async def test_configure_pump(hass: HomeAssistant) -> None:
    run = coord.ReefRunCoordinator(hass, cast(Any, _make_entry()))
    api = _FakeRunAPI()
    run.my_api = cast(Any, api)

    await run.configure_pump(2, "DC Skimmer 900", "rsk-900", "skimmer")
    assert api.configure_pump_calls == [(2, "DC Skimmer 900", "rsk-900", "skimmer")]
