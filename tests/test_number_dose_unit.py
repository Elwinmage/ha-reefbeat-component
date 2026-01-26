from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.redsea.entity import ReefBeatRestoreEntity
from custom_components.redsea.number import (
    ReefDoseNumberEntity,
    ReefDoseNumberEntityDescription,
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


def test_dose_device_info_head_zero_keeps_base() -> None:
    device = FakeCoordinator()
    desc = ReefDoseNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        head=0,
        native_min_value=0,
        native_max_value=1,
        native_step=1,
    )
    ent = ReefDoseNumberEntity(cast(Any, device), desc)
    assert ent.device_info == device.device_info


def test_dose_device_info_head_extends_identifiers_and_name() -> None:
    device = FakeCoordinator()
    desc = ReefDoseNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        head=2,
        native_min_value=0,
        native_max_value=1,
        native_step=1,
    )
    ent = ReefDoseNumberEntity(cast(Any, device), desc)

    assert ent.device_info is not None
    di = cast(DeviceInfo, ent.device_info)
    identifiers = cast(set[tuple[str, str]], di.get("identifiers") or set())
    assert ("redsea", "SERIAL_head_2") in identifiers
    assert di.get("name") == "Device head 2"


@pytest.mark.asyncio
async def test_dose_async_added_to_hass_head_zero_returns_early(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)
    desc = ReefDoseNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        head=0,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
    )
    ent = ReefDoseNumberEntity(cast(Any, device), desc)
    ent.hass = hass

    await ent.async_added_to_hass()

    assert ent.device_info == device.device_info


@pytest.mark.asyncio
async def test_dose_async_set_native_value_pushes_head_and_root(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)

    head_desc = ReefDoseNumberEntityDescription(
        key="x",
        translation_key="daily_dose",
        value_name="$.v",
        head=1,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
    )
    head_ent = ReefDoseNumberEntity(cast(Any, device), head_desc)
    head_ent.hass = hass
    head_ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await head_ent.async_set_native_value(5.0)
    assert device.pushed and device.pushed[-1][1].get("head") == 1

    device.pushed.clear()

    root_desc = ReefDoseNumberEntityDescription(
        key="y",
        translation_key="stock_alert_days",
        value_name="$.root",
        head=0,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
    )
    root_ent = ReefDoseNumberEntity(cast(Any, device), root_desc)
    root_ent.hass = hass
    root_ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await root_ent.async_set_native_value(2.0)
    assert device.pushed and device.pushed[-1][0][0] == "/device-settings"


@pytest.mark.asyncio
async def test_dose_async_set_native_value_calibration_does_not_push_head(
    hass: Any,
) -> None:
    device = FakeCoordinator(hass=hass)

    desc = ReefDoseNumberEntityDescription(
        key="cal",
        translation_key="calibration_dose_value",
        value_name="$.v",
        head=1,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
    )
    ent = ReefDoseNumberEntity(cast(Any, device), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await ent.async_set_native_value(4.5)
    assert device.pushed == []


@pytest.mark.asyncio
async def test_dose_async_added_to_hass_sets_per_head_device_info(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)
    desc = ReefDoseNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        head=1,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
    )
    ent = ReefDoseNumberEntity(cast(Any, device), desc)
    ent.hass = hass

    await ent.async_added_to_hass()

    assert ent.device_info is not None
    di = cast(DeviceInfo, ent.device_info)
    identifiers = cast(set[tuple[str, str]], di.get("identifiers") or set())
    assert ("redsea", "SERIAL_head_1") in identifiers
