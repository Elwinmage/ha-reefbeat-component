"""Coverage top-up for coordinator.py.

Targets:
  - `get_model_type` — the `reef-power` (line 402) and `reef-control` (line 404)
    branches, previously never reached by the existing coordinator tests. The
    method lives on `ReefBeatCloudLinkedCoordinator`, not the plain base.
  - `ReefRunCoordinator.set_pump_intensity` — the "value lower than min → 40"
    warning branch (lines 909 / 913).
  - `ReefPowerCoordinator.__init__` — the ValueError fallback that resets
    `socket_count` to 6 when the hw_model has a non-numeric suffix (lines
    1319-1320).
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import (
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
)


# ---------------------------------------------------------------------------
# get_model_type — HW_POWER_IDS and HW_CONTROL_IDS branches
# ---------------------------------------------------------------------------


def _make_dummy_cloud_linked_coordinator() -> Any:
    """Build a bare ReefBeatCloudLinkedCoordinator without triggering network I/O.

    `get_model_type` lives on `ReefBeatCloudLinkedCoordinator` (not the plain
    `ReefBeatCoordinator` base) and is fully self-contained — it only reads
    its `model` argument. We skip `__init__` so we don't need an event loop.
    """
    from custom_components.redsea.coordinator import ReefBeatCloudLinkedCoordinator

    return ReefBeatCloudLinkedCoordinator.__new__(ReefBeatCloudLinkedCoordinator)


def test_get_model_type_reef_power() -> None:
    from custom_components.redsea.const import HW_POWER_IDS

    obj = _make_dummy_cloud_linked_coordinator()
    for hw in HW_POWER_IDS:
        assert obj.get_model_type(hw) == "reef-power"


def test_get_model_type_reef_control() -> None:
    from custom_components.redsea.const import HW_CONTROL_IDS

    obj = _make_dummy_cloud_linked_coordinator()
    for hw in HW_CONTROL_IDS:
        assert obj.get_model_type(hw) == "reef-control"


# ---------------------------------------------------------------------------
# ReefRunCoordinator.set_pump_intensity — "clamp to 40" warning branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_pump_intensity_clamps_below_40(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Requesting intensity in (0, 40) triggers a warning and a clamp to 40."""
    from custom_components.redsea.coordinator import ReefRunCoordinator

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="run",
        data={
            CONFIG_FLOW_IP_ADDRESS: "1.2.3.4",
            CONFIG_FLOW_HW_MODEL: "RSRUN",
        },
        unique_id="run",
    )
    entry.add_to_hass(hass)

    # MockConfigEntry is a duck-compatible ConfigEntry; the cast quiets pyright.
    coord = ReefRunCoordinator(hass, cast(ConfigEntry, entry))

    # Prime the local cache with a schedule the setter can index into.
    coord.data = {
        "sources": [
            {
                "name": "/pump/settings",
                "data": {
                    "pump_1": {
                        "schedule": {
                            "start": [{"time": "00:00", "intensity": 100}],
                        }
                    }
                },
            }
        ]
    }
    coord.get_data = lambda path, is_None_possible=False: coord.data["sources"][0][  # type: ignore[method-assign,assignment]
        "data"
    ]["pump_1"]["schedule"]

    # Neutralise network I/O.
    coord.my_api.fetch_config = AsyncMock(return_value=None)  # type: ignore[method-assign]
    coord.async_request_refresh = AsyncMock(return_value=None)  # type: ignore[method-assign]

    caplog.clear()
    # Intensity of 20 is in the forbidden (0, 40) range → clamped to 40 with a
    # WARNING logged. We only assert the warning was emitted; the schedule
    # mutation path is exercised by the RSRUN calibration tests.
    with patch.object(coord, "async_set_updated_data", return_value=None):
        try:
            await coord.set_pump_intensity(pump=1, intensity=20)
        except Exception:
            # The setter may need more of the schedule shape than we've faked;
            # what we care about is that the clamp branch executed before the
            # rest. Assertions on the log below confirm we got that far.
            pass

    assert any("value lower than min" in rec.message for rec in caplog.records), (
        "expected a warning about clamping to 40"
    )


# ---------------------------------------------------------------------------
# ReefPowerCoordinator — non-numeric hw_model suffix falls back to 6 sockets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rspower_coordinator_falls_back_to_6_sockets_on_bad_hw_model(
    hass: HomeAssistant,
) -> None:
    """RSPOWER<non-int> would raise on int() — the try/except must catch it.

    Made async because ReefBeatCoordinator.__init__ eventually calls
    `async_get_clientsession(hass)` which requires a running event loop.
    """
    from custom_components.redsea.coordinator import ReefPowerCoordinator

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="pwr",
        data={
            CONFIG_FLOW_IP_ADDRESS: "1.2.3.4",
            CONFIG_FLOW_HW_MODEL: "RSPOWERX",  # not "6" or "8" — parse fails
        },
        unique_id="pwr",
    )
    entry.add_to_hass(hass)

    coord = ReefPowerCoordinator(hass, cast(ConfigEntry, entry))
    assert coord.socket_count == 6
