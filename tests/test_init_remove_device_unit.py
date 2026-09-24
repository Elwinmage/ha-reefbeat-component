"""Coverage for ``async_remove_config_entry_device`` (UI device deletion)."""

from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea as integration
from custom_components.redsea.const import DOMAIN


def _setup(hass: Any) -> tuple[MockConfigEntry, dr.DeviceEntry]:
    entry = MockConfigEntry(domain=DOMAIN, title="run", unique_id="run-remove")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "RUN123_pump_1")}
    )
    return entry, device


@pytest.mark.asyncio
async def test_empty_device_can_be_removed(hass: Any) -> None:
    entry, device = _setup(hass)

    assert await integration.async_remove_config_entry_device(
        hass, cast(Any, entry), device
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("disabled", [False, True])
async def test_device_with_entities_is_kept(hass: Any, disabled: bool) -> None:
    entry, device = _setup(hass)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        "RUN123_pump_1_speed",
        config_entry=cast(Any, entry),
        device_id=device.id,
        disabled_by=er.RegistryEntryDisabler.USER if disabled else None,
    )

    assert not await integration.async_remove_config_entry_device(
        hass, cast(Any, entry), device
    )
