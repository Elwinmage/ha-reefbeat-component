from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.select as platform
from custom_components.redsea.const import DOMAIN
from tests._select_test_fakes import FakeLedCoordinator


@pytest.mark.asyncio
async def test_async_setup_entry_led_adds_mode_select(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Any of these types should match the LED branch.
    monkeypatch.setattr(
        platform, "ReefLedCoordinator", FakeLedCoordinator, raising=True
    )
    monkeypatch.setattr(
        platform, "ReefLedG2Coordinator", FakeLedCoordinator, raising=True
    )
    monkeypatch.setattr(
        platform, "ReefVirtualLedCoordinator", FakeLedCoordinator, raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="led", data={}, unique_id="led")
    entry.add_to_hass(hass)

    device = FakeLedCoordinator(hass=hass, serial="LED", _data={"$.x": "y"})
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    assert len(added[0]) == 1
