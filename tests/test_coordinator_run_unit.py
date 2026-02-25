from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.coordinator as coord
from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
)


def _make_entry(*, title: str, ip: str, hw_model: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={
            CONFIG_FLOW_IP_ADDRESS: ip,
            CONFIG_FLOW_HW_MODEL: hw_model,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
    )


@dataclass
class _FakeRunAPI:
    fetched_config: int = 0
    pushed: list[tuple[str, str, int | None]] = field(default_factory=list)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)

    get_data_map: dict[str, Any] = field(default_factory=dict)

    async def fetch_config(self, _config_path: str | None = None) -> None:
        self.fetched_config += 1

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map[name]

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))
        self.get_data_map[name] = value

    async def push_values(
        self,
        source: str = "/configuration",
        method: str = "put",
        pump: int | None = None,
    ) -> None:
        self.pushed.append((source, method, pump))


@pytest.fixture(autouse=True)
def _patch_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        coord, "async_get_clientsession", lambda _hass: object(), raising=True
    )
    monkeypatch.setattr(
        coord, "ReefRunAPI", lambda *_a, **_k: _FakeRunAPI(), raising=True
    )


@pytest.mark.asyncio
async def test_run_set_pump_intensity_updates_current_segment(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_entry(title="RUN", ip="192.0.2.10", hw_model="RSRUN")
    run = coord.ReefRunCoordinator(hass, cast(Any, entry))

    # Patch datetime.now() so current time picks the second program (st=600).
    class _FixedDateTime:
        @classmethod
        def now(cls):  # type: ignore[no-untyped-def]
            class _Now:
                hour = 10
                minute = 30

            return _Now()

    monkeypatch.setattr(coord, "datetime", _FixedDateTime, raising=True)

    schedule_path = "$.sources[?(@.name=='/pump/settings')].data.pump_1.schedule"
    schedule = [
        {"st": 0, "ti": 1},
        {"st": 600, "ti": 2},
        {"st": 900, "ti": 3},
    ]

    api = _FakeRunAPI(get_data_map={schedule_path: schedule})
    run.my_api = cast(Any, api)

    # Avoid waiting/refreshing through DataUpdateCoordinator.
    run.async_request_refresh = AsyncMock()  # type: ignore[assignment]

    await run.set_pump_intensity(1, 55)

    assert api.fetched_config == 1
    assert schedule[1]["ti"] == 55

    assert api.set_calls[-1][0] == schedule_path
    assert api.pushed == [("/pump/settings", "put", 1)]
    run.async_request_refresh.assert_awaited()


def test_run_pump_device_info_pump_id_zero_returns_base_info(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_entry(title="RUN", ip="192.0.2.10", hw_model="RSRUN")
    run = coord.ReefRunCoordinator(hass, cast(Any, entry))

    base_info = {
        "identifiers": {(DOMAIN, "IDENT")},
        "manufacturer": "Red Sea",
        "model": "RSRUN",
        "via_device": (DOMAIN, "PARENT"),
        "name": "RUN",
    }

    monkeypatch.setattr(
        type(run),
        "device_info",
        property(lambda _self: base_info),
        raising=True,
    )

    assert run.pump_device_info(0) == base_info
