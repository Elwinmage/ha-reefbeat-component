from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.redsea.const import (
    ATO_TANK_VOLUME_DEFAULT,
    ATO_TANK_VOLUME_INTERNAL_NAME,
    ATO_TANK_VOLUME_MAX,
    ATO_TANK_VOLUME_MIN,
    ATO_TANK_VOLUME_STEP,
)
from custom_components.redsea.entity import ReefBeatRestoreEntity
from custom_components.redsea.number import (
    ReefATOTankVolumeNumberEntity,
    ReefATOVolumeLeftNumberEntity,
    ReefBeatNumberEntity,
    ReefBeatNumberEntityDescription,
)
from tests._number_test_fakes import FakeAtoWithVolumeLeft, FakeCoordinator


async def _async_return(value: Any) -> Any:
    return value


def _tank_desc() -> ReefBeatNumberEntityDescription:
    return ReefBeatNumberEntityDescription(
        key="ato_tank_volume",
        translation_key="ato_tank_volume",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        native_min_value=ATO_TANK_VOLUME_MIN,
        native_max_value=ATO_TANK_VOLUME_MAX,
        native_step=ATO_TANK_VOLUME_STEP,
        value_name=ATO_TANK_VOLUME_INTERNAL_NAME,
    )


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
async def test_ato_volume_left_uses_capability_or_fallback(hass: Any) -> None:
    dev1 = FakeAtoWithVolumeLeft(hass=hass)
    desc = ReefBeatNumberEntityDescription(
        key="ato_volume_left",
        translation_key="ato_volume_left",
        value_name="$.ato",
        native_min_value=0,
        native_max_value=10000,
        native_step=1,
    )
    ent1 = ReefATOVolumeLeftNumberEntity(cast(Any, dev1), desc)
    ent1.hass = hass

    await ent1.async_set_native_value(1234)
    assert dev1.set_volume_left_calls == [1234]

    dev2 = FakeCoordinator(hass=hass)
    ent2 = ReefATOVolumeLeftNumberEntity(cast(Any, dev2), desc)
    ent2.hass = hass

    await ent2.async_set_native_value(10)
    assert dev2.set_calls[-1] == ("$.ato", 10)
    assert dev2.pushed


@pytest.mark.asyncio
async def test_ato_tank_volume_is_local_only(hass: Any) -> None:
    """The capacity is declared by the user; nothing is sent to the device."""
    dev = FakeCoordinator(hass=hass)
    ent = ReefATOTankVolumeNumberEntity(cast(Any, dev), _tank_desc())
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[method-assign]

    await ent.async_set_native_value(120)

    assert ent.native_value == 120
    assert not dev.pushed, "the RSATO+ has no endpoint for its container size"
    assert dev.set_calls[-1] == (ATO_TANK_VOLUME_INTERNAL_NAME, 120)


@pytest.mark.asyncio
async def test_ato_tank_volume_bounds(hass: Any) -> None:
    dev = FakeCoordinator(hass=hass)
    ent = ReefATOTankVolumeNumberEntity(cast(Any, dev), _tank_desc())

    assert ent.native_min_value == ATO_TANK_VOLUME_MIN == 5
    assert ent.native_max_value == ATO_TANK_VOLUME_MAX == 300
    assert ent.native_step == ATO_TANK_VOLUME_STEP == 1
    assert ent.native_unit_of_measurement == UnitOfVolume.LITERS


@pytest.mark.asyncio
async def test_ato_tank_volume_defaults_when_nothing_restored(
    hass: Any, monkeypatch: Any
) -> None:
    """First start: no stored state, so the default is seeded."""
    dev = FakeCoordinator(hass=hass)
    ent = ReefATOTankVolumeNumberEntity(cast(Any, dev), _tank_desc())
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[method-assign]

    async def _restore_nothing(self: Any) -> None:
        self._attr_native_value = None

    monkeypatch.setattr(ReefBeatNumberEntity, "async_added_to_hass", _restore_nothing)

    await ent.async_added_to_hass()

    assert ent.native_value == ATO_TANK_VOLUME_DEFAULT
    assert dev.set_calls[-1] == (
        ATO_TANK_VOLUME_INTERNAL_NAME,
        ATO_TANK_VOLUME_DEFAULT,
    )


@pytest.mark.asyncio
async def test_ato_tank_volume_keeps_restored_value(
    hass: Any, monkeypatch: Any
) -> None:
    """A restored value must not be replaced by the default."""
    dev = FakeCoordinator(hass=hass)
    ent = ReefATOTankVolumeNumberEntity(cast(Any, dev), _tank_desc())
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[method-assign]

    async def _restore_42(self: Any) -> None:
        self._attr_native_value = 42.0

    monkeypatch.setattr(ReefBeatNumberEntity, "async_added_to_hass", _restore_42)

    await ent.async_added_to_hass()

    assert ent.native_value == 42.0


def test_ato_local_key_is_seeded() -> None:
    """`jsonpath.update()` cannot create a missing key, so it must pre-exist."""
    from jsonpath_ng.ext import parse

    seeded = {"local": {"use_cloud_api": None, "tank_volume": None}}
    parse(ATO_TANK_VOLUME_INTERNAL_NAME).update(seeded, 120.0)
    assert seeded["local"]["tank_volume"] == 120.0

    unseeded: dict[str, Any] = {"local": {"use_cloud_api": None}}
    parse(ATO_TANK_VOLUME_INTERNAL_NAME).update(unseeded, 120.0)
    assert "tank_volume" not in unseeded["local"]
