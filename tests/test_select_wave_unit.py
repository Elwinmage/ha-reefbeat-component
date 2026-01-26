from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.select as platform
from custom_components.redsea.const import DOMAIN
from tests._select_test_fakes import FakeCoordinator, FakeWaveCoordinator


@pytest.mark.asyncio
async def test_async_setup_entry_wave_adds_preview_type_and_direction_selects(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        platform, "ReefWaveCoordinator", FakeWaveCoordinator, raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="wave", data={}, unique_id="wave")
    entry.add_to_hass(hass)

    # Values are wave ids used by const.WAVE_TYPES and const.WAVE_DIRECTIONS
    device = FakeWaveCoordinator(
        hass=hass,
        serial="WAVE",
        _data={
            "$.sources[?(@.name=='/preview')].data.type": "nw",
            "$.sources[?(@.name=='/preview')].data.direction": "fw",
        },
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    assert len(added[0]) == 2


@pytest.mark.asyncio
async def test_reefwave_select_translates_and_updates_listeners(
    hass: HomeAssistant,
) -> None:
    from custom_components.redsea.select import (
        ReefWaveSelectEntity,
        ReefWaveSelectEntityDescription,
    )

    i18n_options = [
        {"id": "pulse", "en": "Pulse", "fr": "Impulsion"},
    ]

    device = FakeCoordinator(hass=hass, _data={"$.wave": "pulse"})
    desc = ReefWaveSelectEntityDescription(
        key="wave",
        translation_key="wave",
        value_name="$.wave",
        options=["Pulse"],
        i18n_options=i18n_options,
    )
    ent = ReefWaveSelectEntity(cast(Any, device), desc)

    assert ent.current_option == "Pulse"

    # Device update path writes HA state with translated value.
    wrote: list[str] = []

    def _write() -> None:
        wrote.append(cast(str, ent.current_option))

    ent.async_write_ha_state = _write  # type: ignore[method-assign]

    device.set_data("$.wave", "pulse")
    ent._handle_device_update()

    # Coordinator update path forwards to device update.
    ent._handle_coordinator_update()

    assert wrote == ["Pulse", "Pulse"]

    # Selecting an option translates back to the id and only updates listeners.
    device.updated_listeners = 0
    device.set_data("$.wave", "pulse")

    await ent.async_select_option("Pulse")

    assert device.get_data("$.wave") == "pulse"
    assert device.updated_listeners == 1
