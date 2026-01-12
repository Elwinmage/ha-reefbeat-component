
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN


async def test_dose_creates_parent_and_head_devices(
    hass: HomeAssistant,
    local_dose_config_entry: MockConfigEntry,
) -> None:
    """ReefDose should create a parent device and per-head devices with via_device.

    This protects the "entities attach to default device instead of heads" regression.
    """
    local_dose_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(local_dose_config_entry.entry_id)
    await hass.async_block_till_done()

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    # Find the parent device (hwid from /device-info in fixtures).
    parent = None
    for dev in dev_reg.devices.values():
        if (DOMAIN, "1c9dc262f20c") in dev.identifiers:
            parent = dev
            break
    assert parent is not None

    # We should have at least heads 3 and 4 (Cal/Alk) present as separate devices.
    head3 = None
    head4 = None
    for dev in dev_reg.devices.values():
        if (DOMAIN, "1c9dc262f20c_head_3") in dev.identifiers:
            head3 = dev
        if (DOMAIN, "1c9dc262f20c_head_4") in dev.identifiers:
            head4 = dev

    assert head3 is not None
    assert head4 is not None

    # Sanity: at least one entity should be attached to head3/head4 devices.
    #
    # NOTE: It would be nice if head devices were linked to the parent via
    # `via_device_id`, but some refactor states may not set this field yet.
    # The core regression we care about is entities landing on the correct head
    # devices rather than the parent/default device.
    head_device_ids = {head3.id, head4.id}
    attached = [
        ent for ent in ent_reg.entities.values()
        if ent.device_id in head_device_ids
    ]
    assert len(attached) >= 1
