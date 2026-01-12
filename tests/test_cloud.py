
from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN


async def test_setup_cloud_entry(hass: HomeAssistant, cloud_config_entry: MockConfigEntry) -> None:
    """Cloud entry should set up and expose aquarium/device payloads in coordinator data."""
    cloud_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(cloud_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][cloud_config_entry.entry_id]

    # We don't assert exact structure, but we expect the captured dump to be loaded.
    aquariums = coordinator.get_data("$.sources[?(@.name=='/aquarium')].data", True)
    devices = coordinator.get_data("$.sources[?(@.name=='/device')].data", True)

    assert isinstance(aquariums, list)
    assert len(aquariums) >= 1
    assert isinstance(devices, list)
    assert len(devices) >= 1
