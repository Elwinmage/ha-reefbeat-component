from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
    LED_BLUE_INTERNAL_NAME,
    LED_WHITE_INTERNAL_NAME,
)
from custom_components.redsea.coordinator import (
    ReefLedCoordinator,
    ReefLedG2Coordinator,
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
class _FakeAPI:
    get_data_map: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.get_data_map[name] = value


@pytest.mark.asyncio
async def test_led_set_data_updates_wb_and_manual_trick(hass: HomeAssistant) -> None:
    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED50")
    coordinator = ReefLedCoordinator(hass, cast(Any, entry))

    wb_calls: list[bool] = []
    ki_calls: int = 0

    class _LedAPI(_FakeAPI):
        def __init__(self) -> None:
            super().__init__(get_data_map={})
            self.data = {"local": {"manual_trick": {}}}

        def update_light_wb(self) -> None:
            wb_calls.append(True)

        def update_light_ki(self) -> None:
            nonlocal ki_calls
            ki_calls += 1

    coordinator.my_api = cast(Any, _LedAPI())

    coordinator.set_data(str(LED_WHITE_INTERNAL_NAME), 10)
    coordinator.set_data(str(LED_BLUE_INTERNAL_NAME), 20)
    assert len(wb_calls) == 2

    coordinator.set_data("$.local.manual_trick.foo", "bar")
    assert coordinator.my_api.data["local"]["manual_trick"]["foo"] == "bar"
    assert ki_calls == 1


@pytest.mark.asyncio
async def test_led_misc_helpers_and_g2_set_data_passthrough(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry(title="LED", ip="192.0.2.10", hw_model="RSLED50")
    led = ReefLedCoordinator(hass, cast(Any, entry))

    calls: dict[str, Any] = {"force": [], "post": []}

    class _LedAPI(_FakeAPI):
        daily_prog = {"x": 1}

        def __init__(self) -> None:
            super().__init__()
            self._g1 = False

        def force_status_update(self, state: bool = False) -> None:
            calls["force"].append(state)

        async def post_specific(self, source: str) -> None:
            calls["post"].append(source)

    led.my_api = cast(Any, _LedAPI())

    led.force_status_update(True)
    assert calls["force"] == [True]

    assert led.daily_prog() == {"x": 1}
    await led.post_specific("/timer")
    assert calls["post"] == ["/timer"]

    assert led.is_g1 is False

    g2 = ReefLedG2Coordinator(hass, cast(Any, entry))

    set_calls: list[tuple[str, Any]] = []

    class _G2API(_FakeAPI):
        def set_data(self, name: str, value: Any) -> None:
            set_calls.append((name, value))

    g2.my_api = cast(Any, _G2API())
    g2.set_data("$.x", 123)
    assert set_calls == [("$.x", 123)]
