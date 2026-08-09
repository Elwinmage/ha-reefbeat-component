"""Unit tests for ReefRunCoordinator calibration and pump management methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.coordinator as coord
from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
    REFRESH_DEVICE_DELAY,
)


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
    run, api = _make_run(hass, None)
    run._schedule_entry_reload = lambda: None

    await run.delete_pump(1)
    assert api.delete_pump_calls == [1]


@pytest.mark.asyncio
async def test_configure_pump(hass: HomeAssistant) -> None:
    run = coord.ReefRunCoordinator(hass, cast(Any, _make_entry()))
    api = _FakeRunAPI()
    run.my_api = cast(Any, api)

    await run.configure_pump(2, "DC Skimmer 900", "rsk-900", "skimmer")
    assert api.configure_pump_calls == [(2, "DC Skimmer 900", "rsk-900", "skimmer")]


# -- detect_and_add_pump ------------------------------------------------------


class _DetectionAPI(_FakeRunAPI):
    """Fake API returning a configurable detection payload."""

    def __init__(self, detection: dict[str, Any] | None) -> None:
        super().__init__()
        self._detection = detection
        self.fetch_config_calls: int = 0

    async def detect_pump(self, pump: int) -> dict[str, Any] | None:
        self.detect_pump_calls.append(pump)
        return self._detection

    async def fetch_config(self, config_path: str | None = None) -> None:
        self.fetch_config_calls += 1

    async def fetch_data(self) -> dict[str, Any]:
        return {}


def _make_run(
    hass: HomeAssistant, detection: dict[str, Any] | None
) -> tuple[Any, _DetectionAPI]:
    """Build a ReefRun coordinator recording refreshes instead of running them."""
    run = cast(Any, coord.ReefRunCoordinator(hass, cast(Any, _make_entry())))
    api = _DetectionAPI(detection)
    run.my_api = cast(Any, api)
    # Record refreshes instead of sleeping and hitting the network
    refreshes: list[dict[str, Any]] = []
    run.refreshes = refreshes

    async def _refresh(
        source: str | None = None,
        config: bool = False,
        wait: int = REFRESH_DEVICE_DELAY,
    ) -> None:
        refreshes.append({"config": config, "wait": wait})

    run.async_request_refresh = _refresh
    return run, api


@pytest.mark.parametrize(
    ("pump_type", "model", "expected"),
    [
        ("skimmer", "rsk-300", "DC Skimmer 300"),
        ("skimmer", "rsk-900", "DC Skimmer 900"),
        ("return", "return-12000", "ReefRun 12000"),
        # Unexpected model strings are used as-is rather than mangled
        ("skimmer", "weird-model", "weird-model"),
        ("return", "weird-model", "weird-model"),
    ],
)
def test_default_pump_name(pump_type: str, model: str, expected: str) -> None:
    assert coord.ReefRunCoordinator.default_pump_name(pump_type, model) == expected


@pytest.mark.asyncio
async def test_detect_and_add_pump_configures_the_detected_pump(
    hass: HomeAssistant,
) -> None:
    run, api = _make_run(hass, {"type": "skimmer", "model": "rsk-900"})
    reloads: list[bool] = []
    run._schedule_entry_reload = lambda: reloads.append(True)

    result = await run.detect_and_add_pump(2)

    assert result == {"type": "skimmer", "model": "rsk-900"}
    assert api.detect_pump_calls == [2]
    assert api.configure_pump_calls == [(2, "DC Skimmer 900", "rsk-900", "skimmer")]
    # A "data" refresh is required: fetch_config() would not reload /dashboard,
    # and it must leave the device time to apply the PUT
    assert run.refreshes == [{"config": True, "wait": REFRESH_DEVICE_DELAY}]
    assert reloads == [True]


@pytest.mark.asyncio
async def test_detect_and_add_pump_without_detection(hass: HomeAssistant) -> None:
    run, api = _make_run(hass, None)

    assert await run.detect_and_add_pump(1) is None
    assert api.configure_pump_calls == []


@pytest.mark.parametrize(
    "detection",
    [
        {},
        {"type": "skimmer"},
        {"model": "rsk-300"},
        {"type": "unknown", "model": "unknown"},
        {"type": "skimmer", "model": "unknown"},
    ],
)
@pytest.mark.asyncio
async def test_detect_and_add_pump_with_unusable_detection(
    hass: HomeAssistant, detection: dict[str, Any]
) -> None:
    run, api = _make_run(hass, detection)

    assert await run.detect_and_add_pump(1) is None
    assert api.configure_pump_calls == []


@pytest.mark.asyncio
async def test_schedule_entry_reload_is_best_effort(hass: HomeAssistant) -> None:
    """An entry that cannot be reloaded must not break the add sequence."""
    run, _api = _make_run(hass, {"type": "skimmer", "model": "rsk-300"})

    # The mock entry is not registered in hass: reloading raises, and is swallowed
    run._schedule_entry_reload()

    assert await run.detect_and_add_pump(1) == {"type": "skimmer", "model": "rsk-300"}


@pytest.mark.asyncio
async def test_delete_pump_refreshes_and_reloads(hass: HomeAssistant) -> None:
    """Deleting a pump must not wait for the next scan interval."""
    run, api = _make_run(hass, None)
    reloads: list[bool] = []
    run._schedule_entry_reload = lambda: reloads.append(True)

    await run.delete_pump(2)

    assert api.delete_pump_calls == [2]
    assert run.refreshes == [{"config": True, "wait": REFRESH_DEVICE_DELAY}]
    assert reloads == [True]
