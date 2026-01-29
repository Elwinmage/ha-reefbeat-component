from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.redsea.entity import ReefBeatRestoreEntity
from custom_components.redsea.number import (
    ReefRunNumberEntity,
    ReefRunNumberEntityDescription,
)
from tests._number_test_fakes import FakeCoordinator, FakeRunWithPumpIntensity


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


@pytest.mark.asyncio
async def test_run_async_set_native_value_preview_early_return(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)
    desc = ReefRunNumberEntityDescription(
        key="preview_pump_1_intensity",
        translation_key="preview_speed",
        value_name="$.pv",
        pump=1,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    )
    ent = ReefRunNumberEntity(cast(Any, device), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await ent.async_set_native_value(33)
    assert device.pushed == []


@pytest.mark.asyncio
async def test_run_async_set_native_value_uses_set_pump_intensity_when_supported(
    hass: Any,
) -> None:
    device = FakeRunWithPumpIntensity(hass=hass)
    desc = ReefRunNumberEntityDescription(
        key="pump_1_intensity",
        translation_key="speed",
        value_name="$.int",
        pump=1,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    )
    ent = ReefRunNumberEntity(cast(Any, device), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await ent.async_set_native_value(50)
    assert device.set_intensity_calls == [(1, 50)]
    assert device.pushed and device.pushed[-1][0][0] == "/pump/settings"


@pytest.mark.asyncio
async def test_run_async_set_native_value_falls_back_to_push_values(hass: Any) -> None:
    device = FakeCoordinator(hass=hass)
    desc = ReefRunNumberEntityDescription(
        key="pump_2_intensity",
        translation_key="speed",
        value_name="$.int",
        pump=2,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    )
    ent = ReefRunNumberEntity(cast(Any, device), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await ent.async_set_native_value(40)
    assert device.pushed


@pytest.mark.asyncio
async def test_run_async_added_to_hass_sets_per_pump_device_info(hass: Any) -> None:
    # device = FakeCoordinator(hass=hass)
    device = FakeRunWithPumpIntensity(hass=hass)
    desc = ReefRunNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        pump=2,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
    )
    ent = ReefRunNumberEntity(cast(Any, device), desc)
    ent.hass = hass
    await ent.async_added_to_hass()

    assert ent.device_info is not None
    di = cast(DeviceInfo, ent.device_info)
    identifiers = cast(set[tuple[str, str]], di.get("identifiers") or set())

    assert any("SERIAL_pump_2" in serial for _d, serial in identifiers)


@pytest.mark.asyncio
async def test_run_supported_device_non_intensity_key_pushes_with_pump(
    hass: Any,
) -> None:
    device = FakeRunWithPumpIntensity(hass=hass)
    desc = ReefRunNumberEntityDescription(
        key="something_else",
        translation_key="x",
        value_name="$.v",
        pump=1,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
    )
    ent = ReefRunNumberEntity(cast(Any, device), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await ent.async_set_native_value(11)
    assert device.pushed and device.pushed[-1][1].get("pump") == 1
