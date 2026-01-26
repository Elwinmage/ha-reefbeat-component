from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.redsea.entity import ReefBeatRestoreEntity
from custom_components.redsea.number import (
    ReefBeatNumberEntityDescription,
    ReefWaveNumberEntity,
)
from tests._number_test_fakes import FakeCoordinator


@pytest.fixture(autouse=True)
def _patch_base(monkeypatch: Any) -> None:
    async def _noop_async_added_to_hass(self: Any) -> None:
        return

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_async_added_to_hass
    )
    monkeypatch.setattr(
        CoordinatorEntity, "_handle_coordinator_update", lambda self: None
    )


def test_wave_handle_device_update_su_limits_and_none_value(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)

    desc = ReefBeatNumberEntityDescription(
        key="wave_preview_wave_duration",
        translation_key="x",
        value_name="$.val",
        native_min_value=0,
        native_max_value=10,
        native_step=1,
    )
    ent = ReefWaveNumberEntity(cast(Any, device), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    device.get_data_map["$.sources[?(@.name=='/preview')].data.type"] = "su"
    device.get_data_map["$.val"] = None

    ent._handle_device_update()
    assert ent._attr_available is False
    assert ent.native_value is None
    assert ent.native_min_value == 0.5
    assert ent.native_max_value == 5.9
    assert ent.native_step == 0.1


def test_wave_handle_device_update_non_su_int_coercion(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)

    desc = ReefBeatNumberEntityDescription(
        key="wave_preview_wave_duration",
        translation_key="x",
        value_name="$.val",
        native_min_value=1.0,
        native_max_value=9.0,
        native_step=1.0,
    )
    ent = ReefWaveNumberEntity(cast(Any, device), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    device.get_data_map["$.sources[?(@.name=='/preview')].data.type"] = "xx"
    device.get_data_map["$.val"] = 7.9

    ent._handle_device_update()
    assert ent._attr_available is True
    assert ent.native_value == 7


def test_wave_handle_coordinator_update_delegates(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)
    desc = ReefBeatNumberEntityDescription(
        key="wave_preview_wave_duration",
        translation_key="x",
        value_name="$.val",
        native_min_value=1.0,
        native_max_value=9.0,
        native_step=1.0,
    )
    ent = ReefWaveNumberEntity(cast(Any, device), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    device.get_data_map["$.sources[?(@.name=='/preview')].data.type"] = "xx"
    device.get_data_map["$.val"] = 3

    ent._handle_coordinator_update()
    assert ent.native_value == 3
