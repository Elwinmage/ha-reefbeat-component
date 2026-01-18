from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.select as platform
from custom_components.redsea.const import DOMAIN
from tests._select_test_fakes import FakeMatCoordinator


@pytest.mark.asyncio
async def test_async_setup_entry_mat_adds_two_select_entities(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        platform, "ReefMatCoordinator", FakeMatCoordinator, raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="mat", data={}, unique_id="mat")
    entry.add_to_hass(hass)

    device = FakeMatCoordinator(hass=hass, serial="MAT", _data={})
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[tuple[list[Any], bool]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append((list(new_entities), update_before_add))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    entities, update_before_add = added[0]
    assert update_before_add is True
    assert len(entities) == 2
