from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from conftest import read_device_endpoint
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN


async def _assert_device_has_entities(hass: HomeAssistant, identifier: str) -> None:
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    dev = next(
        (d for d in dev_reg.devices.values() if (DOMAIN, identifier) in d.identifiers),
        None,
    )
    assert dev is not None

    ents = [e for e in ent_reg.entities.values() if e.device_id == dev.id]
    assert len(ents) >= 1


@pytest.mark.parametrize(
    ("entry_fixture", "profile"),
    [
        ("local_mat_config_entry", "MAT"),
        ("local_ato_config_entry", "ATO"),
        ("local_dose_config_entry", "DOSE4"),
        ("local_dose2_config_entry", "DOSE2"),
        ("local_run_config_entry", "RUN"),
        ("local_wave_config_entry", "WAVE"),
        ("local_led_config_entry", "LED"),
    ],
)
async def test_local_device_profiles_have_entities(
    hass: HomeAssistant,
    request: pytest.FixtureRequest,
    devices_dir: Path,
    entry_fixture: str,
    profile: str,
) -> None:
    entry: MockConfigEntry = request.getfixturevalue(entry_fixture)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    device_info = cast(
        dict[str, Any], read_device_endpoint(devices_dir, profile, "/device-info")
    )
    identifier = str(device_info.get("hwid") or device_info.get("id") or "unknown")
    await _assert_device_has_entities(hass, identifier)
