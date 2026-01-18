from __future__ import annotations

from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.switch import ReefBeatSwitchEntity
from tests._switch_test_fakes import FakeCoordinator


class _AtoDevice(FakeCoordinator):
    pass


@pytest.mark.asyncio
async def test_switch_async_setup_entry_ato_adds_ato_switches_and_common(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(platform, "ReefATOCoordinator", _AtoDevice, raising=True)

    # Ensure the cloud coordinator isinstance() doesn't short-circuit COMMON switches.
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ato", data={}, unique_id="ato")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _AtoDevice()

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    entities = added[0]

    assert entities
    assert all(isinstance(e, ReefBeatSwitchEntity) for e in entities)
