from __future__ import annotations

from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.switch import (
    ReefBeatSwitchEntity,
    SaveStateSwitchEntity,
    SaveStateSwitchEntityDescription,
)
from tests._switch_test_fakes import FakeCoordinator


class _CloudLinkedDevice(FakeCoordinator):
    def cloud_link(self) -> Any:
        return True


@pytest.mark.asyncio
async def test_save_state_switch_sets_local_cache_and_icons(hass: Any) -> None:
    device = FakeCoordinator()

    desc = SaveStateSwitchEntityDescription(
        key="use_cloud_api",
        translation_key="use_cloud_api",
        icon="mdi:cloud",
        icon_off="mdi:cloud-off",
    )

    entity = SaveStateSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()
    assert device.set_calls[-1] == ("$.local.use_cloud_api", False)
    assert entity.icon == "mdi:cloud-off"

    await entity.async_turn_on()
    assert device.set_calls[-1] == ("$.local.use_cloud_api", True)
    assert entity.icon == "mdi:cloud"

    assert entity.device_info == device.device_info

    device.get_data_map["$.local.use_cloud_api"] = True
    await entity.async_added_to_hass()
    assert entity.is_on is True


@pytest.mark.asyncio
async def test_save_state_switch_async_added_to_hass_sets_available_when_previously_unavailable(
    hass: Any,
) -> None:
    device = FakeCoordinator(last_update_success=False)

    desc = SaveStateSwitchEntityDescription(
        key="use_cloud_api",
        translation_key="use_cloud_api",
        icon="mdi:cloud",
        icon_off="mdi:cloud-off",
    )

    entity = SaveStateSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    # Force the first restore/availability branch.
    entity._attr_available = False
    entity._attr_is_on = False

    await entity.async_added_to_hass()

    assert entity.available is True
    assert entity.icon == "mdi:cloud-off"


@pytest.mark.asyncio
async def test_switch_async_setup_entry_cloud_linked_adds_save_state_and_common(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ensure the cloud coordinator isinstance() doesn't short-circuit COMMON switches.
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="cloud", data={}, unique_id="cloud")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _CloudLinkedDevice()

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    entities = added[0]

    assert any(isinstance(e, SaveStateSwitchEntity) for e in entities)
    assert any(isinstance(e, ReefBeatSwitchEntity) for e in entities)
