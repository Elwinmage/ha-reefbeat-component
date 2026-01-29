from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.redsea.button import (
    ReefBeatButtonEntity,
    ReefBeatButtonEntityDescription,
)


@dataclass
class _FakeDevice:
    serial: str = "SERIAL"
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "SERIAL")})
    )


@pytest.mark.asyncio
async def test_reefbeat_button_entity_async_press_sync_fn_called() -> None:
    device = _FakeDevice()
    called: list[str] = []

    def _press_fn(_: Any) -> None:
        called.append("ok")

    desc = ReefBeatButtonEntityDescription(
        key="k",
        translation_key="k",
        press_fn=_press_fn,
    )

    entity = ReefBeatButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert called == ["ok"]


@pytest.mark.asyncio
async def test_reefbeat_button_entity_async_press_awaitable_fn_awaited() -> None:
    device = _FakeDevice()
    called: list[str] = []

    async def _press_fn(_: Any) -> None:
        called.append("ok")

    desc = ReefBeatButtonEntityDescription(
        key="k",
        translation_key="k",
        press_fn=_press_fn,
    )

    entity = ReefBeatButtonEntity(cast(Any, device), desc)
    await entity.async_press()

    assert called == ["ok"]
