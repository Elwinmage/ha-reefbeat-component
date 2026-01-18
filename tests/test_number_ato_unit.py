from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.redsea.entity import ReefBeatRestoreEntity
from custom_components.redsea.number import (
    ReefATOVolumeLeftNumberEntity,
    ReefBeatNumberEntityDescription,
)
from tests._number_test_fakes import FakeAtoWithVolumeLeft, FakeCoordinator


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
