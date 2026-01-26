from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
)
from custom_components.redsea.coordinator import ReefMatCoordinator


def _make_entry(*, title: str, ip: str, hw_model: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={
            CONFIG_FLOW_IP_ADDRESS: ip,
            CONFIG_FLOW_HW_MODEL: hw_model,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
    )


@pytest.mark.asyncio
async def test_mat_new_roll_delegates(hass: HomeAssistant) -> None:
    entry = _make_entry(title="MAT", ip="192.0.2.10", hw_model="RSMAT")
    mat = ReefMatCoordinator(hass, cast(Any, entry))

    class _MatAPI:
        def __init__(self) -> None:
            self.rolls = 0

        async def new_roll(self) -> None:
            self.rolls += 1

    api = _MatAPI()
    mat.my_api = cast(Any, api)

    await mat.new_roll()

    assert api.rolls == 1
