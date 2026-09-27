"""Event-bus listener lifecycle of the coordinators.

A coordinator is rebuilt on every setup attempt (ConfigEntryNotReady retries,
reloads). Its bus listeners must go with it, otherwise each attempt leaves one
more listener firing on a dead instance.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea as integration
from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
)
from custom_components.redsea.coordinator import (
    ReefBeatCloudLinkedCoordinator,
    ReefBeatCoordinator,
)
from custom_components.redsea.reefbeat.cloud import InvalidAuth


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Device",
        data={
            CONFIG_FLOW_IP_ADDRESS: "192.0.2.1",
            CONFIG_FLOW_HW_MODEL: "RSRUN",
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
    )


def _count(hass: HomeAssistant, event: Any) -> int:
    return hass.bus.async_listeners().get(event, 0)


@pytest.mark.asyncio
async def test_listen_is_released_by_unload(hass: HomeAssistant) -> None:
    coordinator = ReefBeatCoordinator(hass, cast(Any, _entry()))
    handler = MagicMock()

    coordinator._listen("redsea_test_event", handler)
    assert _count(hass, "redsea_test_event") == 1

    coordinator.unload()
    coordinator.unload()  # idempotent
    assert _count(hass, "redsea_test_event") == 0

    hass.bus.async_fire("redsea_test_event")
    await hass.async_block_till_done()
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_rebuilt_cloud_linked_coordinators_do_not_pile_up(
    hass: HomeAssistant,
) -> None:
    before = _count(hass, EVENT_HOMEASSISTANT_STARTED)

    # Three failed setup attempts, each releasing its coordinator.
    for _ in range(3):
        coordinator = ReefBeatCloudLinkedCoordinator(hass, cast(Any, _entry()))
        assert _count(hass, EVENT_HOMEASSISTANT_STARTED) == before + 1
        coordinator.unload()

    assert _count(hass, EVENT_HOMEASSISTANT_STARTED) == before


class _FailingCoordinator:
    def __init__(self, error: Exception) -> None:
        self._error = error
        self.unload = MagicMock()

    async def async_setup(self) -> None:
        raise self._error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "not_ready"),
    [
        (RuntimeError("Initialization failed, is your device on?"), True),
        (InvalidAuth("bad credentials"), False),
    ],
)
async def test_failed_setup_releases_coordinator(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    not_ready: bool,
) -> None:
    coordinator = _FailingCoordinator(error)
    monkeypatch.setattr(integration, "_build_coordinator", lambda _h, _e: coordinator)
    entry = _entry()

    if not_ready:
        with pytest.raises(ConfigEntryNotReady):
            await integration.async_setup_entry(hass, cast(Any, entry))
    else:
        assert await integration.async_setup_entry(hass, cast(Any, entry)) is False

    coordinator.unload.assert_called_once_with()


@pytest.mark.asyncio
async def test_release_swallows_unload_errors(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator = _FailingCoordinator(RuntimeError("down"))
    coordinator.unload.side_effect = RuntimeError("teardown")
    monkeypatch.setattr(integration, "_build_coordinator", lambda _h, _e: coordinator)

    # The setup outcome is not masked by a teardown failure.
    with pytest.raises(ConfigEntryNotReady, match="down"):
        await integration.async_setup_entry(hass, cast(Any, _entry()))
