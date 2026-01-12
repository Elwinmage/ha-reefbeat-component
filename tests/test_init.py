
from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN


@pytest.mark.parametrize(
    "entry_fixture",
    ["local_ato_config_entry", "local_mat_config_entry", "local_dose_config_entry"],
)
async def test_setup_and_unload_local_entries(
    hass: HomeAssistant, request: pytest.FixtureRequest, entry_fixture: str
) -> None:
    """Each local config entry should set up and unload cleanly."""
    entry: MockConfigEntry = request.getfixturevalue(entry_fixture)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Coordinator is stored under hass.data[DOMAIN][entry_id]
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data.get(DOMAIN, {})
