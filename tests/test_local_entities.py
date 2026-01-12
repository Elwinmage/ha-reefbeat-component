
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN


async def _assert_device_has_entities(hass: HomeAssistant, identifier: str) -> None:
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    dev = next((d for d in dev_reg.devices.values() if (DOMAIN, identifier) in d.identifiers), None)
    assert dev is not None

    ents = [e for e in ent_reg.entities.values() if e.device_id == dev.id]
    assert len(ents) >= 1


async def test_local_mat_has_entities(hass: HomeAssistant, local_mat_config_entry: MockConfigEntry) -> None:
    local_mat_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(local_mat_config_entry.entry_id)
    await hass.async_block_till_done()
    await _assert_device_has_entities(hass, "345f452d8ad8")


async def test_local_ato_has_entities(hass: HomeAssistant, local_ato_config_entry: MockConfigEntry) -> None:
    local_ato_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(local_ato_config_entry.entry_id)
    await hass.async_block_till_done()
    await _assert_device_has_entities(hass, "8813bf644294")
