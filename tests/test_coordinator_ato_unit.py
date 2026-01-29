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
from custom_components.redsea.coordinator import ReefATOCoordinator


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
async def test_ato_delegate_methods(hass: HomeAssistant) -> None:
    entry = _make_entry(title="ATO", ip="192.0.2.10", hw_model="RSATO+")
    ato = ReefATOCoordinator(hass, cast(Any, entry))

    class _AtoAPI:
        def __init__(self) -> None:
            self.volumes: list[int] = []
            self.resumed = 0

        async def set_volume_left(self, volume_ml: int) -> None:
            self.volumes.append(volume_ml)

        async def resume(self) -> None:
            self.resumed += 1

    api = _AtoAPI()
    ato.my_api = cast(Any, api)

    await ato.set_volume_left(123)
    await ato.resume()

    assert api.volumes == [123]
    assert api.resumed == 1
