from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.redsea.entity import ReefBeatRestoreEntity
from custom_components.redsea.number import (
    ReefLedNumberEntity,
    ReefLedNumberEntityDescription,
)
from tests._number_test_fakes import FakeCoordinator, FakeLedPostSpecific


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
async def test_led_async_set_native_value_post_specific_and_fallback(hass: Any) -> None:
    # post_specific supported
    led1 = FakeLedPostSpecific(hass=hass)
    desc1 = ReefLedNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.x",
        post_specific="/acclimation",
        native_min_value=0,
        native_max_value=10,
        native_step=1,
    )
    ent1 = ReefLedNumberEntity(cast(Any, led1), desc1)
    ent1.hass = hass
    ent1.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await ent1.async_set_native_value(2)
    assert led1.posted == ["/acclimation"]

    # post_specific not supported -> fallback to push_values(post)
    led2 = FakeCoordinator(hass=hass)
    desc2 = ReefLedNumberEntityDescription(
        key="y",
        translation_key="y",
        value_name="$.y",
        post_specific="/timer",
        native_min_value=0,
        native_max_value=10,
        native_step=1,
    )
    ent2 = ReefLedNumberEntity(cast(Any, led2), desc2)
    ent2.hass = hass
    ent2.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await ent2.async_set_native_value(3)
    assert led2.pushed and led2.pushed[-1][0][1] == "post"


@pytest.mark.asyncio
async def test_led_post_specific_none_uses_post_push(hass: Any) -> None:
    led = FakeCoordinator(hass=hass)
    desc = ReefLedNumberEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.x",
        post_specific=None,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
    )
    ent = ReefLedNumberEntity(cast(Any, led), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await ent.async_set_native_value(1)
    assert led.pushed and led.pushed[-1][0][1] == "post"
