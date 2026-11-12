"""Tests for the RSDOSE per-head calibration maintenance task.

The calibration reminder is one task per head, and its last-reset date is
synced from the head's native ``last_calibrated`` epoch
(ReefDoseCoordinator._sync_calibration_maintenance), moving forward only.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.coordinator import ReefDoseCoordinator
from custom_components.redsea.maintenance import (
    DOSE_CALIBRATION_TASK,
    TASKS,
    MaintenanceStore,
)


def test_dose_calibration_is_per_head() -> None:
    """Both RSDOSE models expose the calibration task per head."""
    for model in ("RSDOSE2", "RSDOSE4"):
        cal = [t for t in TASKS[model] if t.key == DOSE_CALIBRATION_TASK]
        assert len(cal) == 1
        assert cal[0].applies_to_sub == "head"


def _fake_dose(
    store: MaintenanceStore | None, epochs: dict[int, int], heads_nb: int | None = None
) -> ReefDoseCoordinator:
    """A minimal stand-in exposing only what _sync_calibration_maintenance uses.

    Cast to ReefDoseCoordinator so the unbound method can be called on it.
    """

    def get_data(path: str, is_None_possible: bool = False) -> Any:
        for head, ts in epochs.items():
            if f"/head/{head}/settings" in path and "last_calibrated" in path:
                return ts
        return None

    fake = SimpleNamespace(
        serial="SER",
        heads_nb=heads_nb if heads_nb is not None else len(epochs),
        maintenance=store,
        get_data=get_data,
    )
    return cast(ReefDoseCoordinator, fake)


async def test_sync_dates_each_head_from_last_calibrated(hass: Any) -> None:
    store = MaintenanceStore(hass, "entry_dose")
    await store.async_load()

    epochs = {1: 1762537564, 2: 1700000000}
    await ReefDoseCoordinator._sync_calibration_maintenance(_fake_dose(store, epochs))

    for head, ts in epochs.items():
        assert store.get_last_reset("SER", head, DOSE_CALIBRATION_TASK) == (
            datetime.datetime.fromtimestamp(ts, tz=datetime.UTC)
        )


async def test_sync_never_moves_back(hass: Any) -> None:
    store = MaintenanceStore(hass, "entry_dose")
    await store.async_load()

    recent = 1762537564
    await ReefDoseCoordinator._sync_calibration_maintenance(
        _fake_dose(store, {1: recent})
    )
    # An older date reported later must not rewind the reminder.
    await ReefDoseCoordinator._sync_calibration_maintenance(_fake_dose(store, {1: 1}))
    assert store.get_last_reset("SER", 1, DOSE_CALIBRATION_TASK) == (
        datetime.datetime.fromtimestamp(recent, tz=datetime.UTC)
    )


async def test_sync_ignores_missing_or_bad_dates(hass: Any) -> None:
    store = MaintenanceStore(hass, "entry_dose")
    await store.async_load()

    # get_data returns None for every head (empty epochs), two heads.
    await ReefDoseCoordinator._sync_calibration_maintenance(
        _fake_dose(store, {}, heads_nb=2)
    )
    assert store.get_last_reset("SER", 1, DOSE_CALIBRATION_TASK) is None

    # No store attached: no-op, no crash.
    await ReefDoseCoordinator._sync_calibration_maintenance(
        _fake_dose(None, {}, heads_nb=1)
    )


@pytest.mark.parametrize("bad", ["", "n/a", None])
async def test_sync_skips_non_integer(hass: Any, bad: Any) -> None:
    store = MaintenanceStore(hass, "entry_dose")
    await store.async_load()
    fake = cast(
        ReefDoseCoordinator,
        SimpleNamespace(
            serial="SER", heads_nb=1, maintenance=store, get_data=lambda *a, **k: bad
        ),
    )
    await ReefDoseCoordinator._sync_calibration_maintenance(fake)
    assert store.get_last_reset("SER", 1, DOSE_CALIBRATION_TASK) is None


class _FakeAPI:
    """Minimal my_api so the base coordinator refresh runs."""

    def __init__(self) -> None:
        self.fetch_failures: tuple[int, int] = (0, 0)

    async def fetch_data(self) -> dict[str, Any]:
        return {}

    def get_data(
        self, name: str, is_None_possible: bool = False, cached: bool = True
    ) -> Any:
        return None


async def test_sync_failure_does_not_break_refresh(
    hass: Any, local_dose_config_entry: MockConfigEntry
) -> None:
    """A failing calibration sync is swallowed; the refresh still completes."""
    coordinator = ReefDoseCoordinator(hass, cast(Any, local_dose_config_entry))
    coordinator.my_api = cast(Any, _FakeAPI())
    with patch.object(
        ReefDoseCoordinator,
        "_sync_calibration_maintenance",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        res = await coordinator._async_update_data()
    assert res is not None
