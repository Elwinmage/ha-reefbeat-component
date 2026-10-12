"""Tests of the dose regulation of the ReefDose heads (dose_regulation.py)."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea import dose_regulation as R
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.coordinator import ReefControlCoordinator
from custom_components.redsea.maintenance import (
    CALIBRATION_TASKS,
    REFRACTOMETER_TASK,
    MaintenanceStore,
)

T0 = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures" / "devices"


def DD(head: int) -> str:
    return f"$.sources[?(@.name=='/head/{head}/settings')].data.schedule.dd"


def ENABLED(head: int) -> str:
    return f"$.sources[?(@.name=='/head/{head}/settings')].data.schedule_enabled"


BUNDLE = "$.sources[?(@.name=='/dashboard')].data.bundled_heads"


def SUPPLEMENT(head: int) -> str:
    return f"$.sources[?(@.name=='/head/{head}/settings')].data.supplement.uid"


def put_brine(doser: Any, head: int = 1) -> None:
    """The brine supplement on a head (the only one regulated on salinity)."""
    doser.data[SUPPLEMENT(head)] = R.BRINE_SUPPLEMENT_UID


LOG = "$.sources[?(@.name=='/daily-log')].data"


class FakeAPI:
    def __init__(self) -> None:
        self.fetched: list[str | None] = []

    async def fetch_config(self, path: str | None = None) -> None:
        self.fetched.append(path)


class FakeDoser:
    """The few things the regulator reads and calls on a ReefDose coordinator."""

    title = "Doser"
    serial = "SER"
    model_id = "HWID"

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.my_api = FakeAPI()
        self.pushed: list[int | None] = []
        self.doses: list[tuple[int, float]] = []
        self.dose_ok = True
        self.refreshes = 0
        self.listeners: list[Any] = []

    def get_data(self, path: str, is_None_possible: bool = False) -> Any:
        return self.data.get(path)

    def set_data(self, path: str, value: Any) -> None:
        self.data[path] = value

    async def push_values(
        self,
        source: str = "/configuration",
        method: str = "put",
        head: int | None = None,
    ) -> None:
        self.pushed.append(head)

    async def async_request_refresh(self, *args: Any, **kwargs: Any) -> None:
        self.refreshes += 1

    async def manual_dose(self, head: int, volume: float) -> bool:
        self.doses.append((head, volume))
        return self.dose_ok

    def head_device_info(self, head: int) -> dict[str, Any]:
        return {"identifiers": {(DOMAIN, f"HWID_head_{head}")}, "name": f"head {head}"}

    def async_add_listener(self, listener: Any) -> Any:
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)


class Clock:
    def __init__(self, at: datetime = T0) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at

    def advance(self, **kwargs: float) -> datetime:
        self.at += timedelta(**kwargs)
        return self.at


async def _regulator(
    hass: HomeAssistant, heads: tuple[int, ...] = (1, 2)
) -> tuple[R.DoseRegulator, FakeDoser, Clock]:
    store = R.RegulationStore(hass, "entry", heads)
    await store.async_load()
    doser = FakeDoser()
    regulator = R.DoseRegulator(hass, doser, store)
    clock = Clock()
    regulator.now = clock  # type: ignore[method-assign]
    return regulator, doser, clock


# =============================================================================
# Settings
# =============================================================================


def test_settings_mode_brings_the_parameter() -> None:
    settings = R.HeadSettings()
    settings.set("mode", "brine")
    assert (settings.parameter, settings.target, settings.tolerance) == (
        "salinity",
        35.0,
        0.3,
    )
    settings.set("mode", "assisted")
    assert settings.parameter == "kh" and settings.target == 8.0
    settings.set("parameter", "ca")
    assert settings.target == 430.0 and settings.tolerance == 10.0
    # Same parameter again: the user's target is kept
    settings.set("target", 440)
    settings.set("parameter", "ca")
    assert settings.target == 440.0
    settings.set("mode", "off")
    assert settings.parameter == "ca"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("mode", "auto"),
        ("parameter", "zinc"),
        ("salinity_source", 3),
        ("nope", 1),
        ("target", "abc"),
        ("target", -1),
        ("brine_max_rise", 5),
        ("potency", math.nan),
    ],
)
def test_settings_are_checked(key: str, value: Any) -> None:
    with pytest.raises(ValueError):
        R.HeadSettings().set(key, value)


def test_parameter_must_match_the_mode() -> None:
    settings = R.HeadSettings()
    with pytest.raises(ValueError):
        settings.set("parameter", "salinity")
    settings.set("mode", "brine")
    with pytest.raises(ValueError):
        settings.set("parameter", "kh")


def test_settings_round_trip_and_bad_values() -> None:
    settings = R.HeadSettings()
    settings.set("mode", "brine")
    settings.set("salinity_source", "sensor.x")
    again = R.HeadSettings.from_dict(settings.as_dict())
    assert again == settings
    assert R.HeadSettings.from_dict(None) == R.HeadSettings()
    # A bad stored value is dropped, the rest kept
    mixed = R.HeadSettings.from_dict({"target": "x", "potency": 0.2})
    assert mixed.potency == 0.2 and mixed.target == 8.0


# =============================================================================
# Units
# =============================================================================


def test_pss78() -> None:
    # Standard seawater: ratio 1 at 15 °C is 35 by definition
    assert R.pss78(42.914, 15.0) == pytest.approx(35.0, abs=0.001)
    # Red Sea's calibration point: ~53 mS/cm at 25 °C is ~35 ppt
    assert R.pss78(53.0) == pytest.approx(34.98, abs=0.05)


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("35.2", "ppt", 35.2),
        (35, "‰", 35.0),
        (35, "PSU", 35.0),
        (53.0, "mS/cm", 34.98),
        (53000.0, "µS/cm", 34.98),
        (1.0264, "SG", 35.0),
        (1.0264, None, 35.0),
        (35, "", None),
        ("abc", "ppt", None),
        (math.inf, "ppt", None),
        (35, "°C", None),
    ],
)
def test_to_ppt(value: Any, unit: str | None, expected: float | None) -> None:
    result = R.to_ppt(value, unit)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected, abs=0.05)


def test_salinity_units_supported() -> None:
    assert R.salinity_unit_supported("ppt")
    assert R.salinity_unit_supported("mS/cm")
    assert R.salinity_unit_supported("SG")
    assert not R.salinity_unit_supported("°C")
    assert not R.salinity_unit_supported(None)


# =============================================================================
# Volumes
# =============================================================================


def test_dosed_between_whole_and_partial_days() -> None:
    now = T0 + timedelta(days=7)
    # 7 days at 20 mL from 10:00 to 10:00: 140 mL
    assert R.dosed_between(T0, now, {}, 20.0, now) == pytest.approx(140.0)
    # A logged day replaces the fallback
    daily = {"2026-10-03": 10.0}
    assert R.dosed_between(T0, now, daily, 20.0, now) == pytest.approx(130.0)
    # The doser's volume of today is partial: all of it by 10:00 counts
    daily_today = {"2026-10-08": 5.0}
    assert R.dosed_between(
        now - timedelta(hours=5), now, daily_today, 20.0, now
    ) == pytest.approx(2.5)
    assert R.dosed_between(now, T0, {}, 20.0, now) == 0.0


def test_effect_per_ml() -> None:
    assert R.effect_per_ml(0.1, 100.0) == pytest.approx(0.1)
    assert R.effect_per_ml(0.1, 200.0) == pytest.approx(0.05)


def test_daily_log_volumes_of_the_fixture() -> None:
    payload = json.loads((FIXTURES / "DOSE4" / "daily-log" / "data").read_text())
    volumes = R.daily_log_volumes(payload, [1, 4])
    assert len(volumes[1]) == 7
    assert volumes[1]["2025-11-21"] == pytest.approx(3.309072)
    assert volumes[4]["2025-11-18"] == pytest.approx(109.0639)


def test_daily_log_volumes_bad_payloads() -> None:
    assert R.daily_log_volumes(None, [1]) == {1: {}}
    assert R.daily_log_volumes({"daily": "x"}, [1]) == {1: {}}
    payload = {"daily": [1, {"date": "x"}, {"date": 0, "1": -1, "2": 3}]}
    assert R.daily_log_volumes(payload, [1, 2]) == {1: {}, 2: {"1970-01-01": 3.0}}


# =============================================================================
# Assisted mode
# =============================================================================


def _m(days: float, value: float, suspect: bool = False) -> R.Measurement:
    return R.Measurement(T0 + timedelta(days=days), "kh", value, suspect=suspect)


def _dosed_20(start: datetime, end: datetime) -> float:
    return R.dosed_between(start, end, {}, 20.0, T0 + timedelta(days=60))


def test_consumption_worked_example() -> None:
    # 100 L, 0.1 dKH/mL/100 L: 1 mL raises 0.1 dKH; 20 mL/day = +2 dKH/day.
    # KH went 8.0 -> 7.3 in 7 days: consumption (14 + 0.7) / 7 = 2.1 dKH/day
    consumption = R.estimate_consumption([_m(0, 8.0), _m(7, 7.3)], _dosed_20, 0.1)
    assert consumption == pytest.approx(2.1)


def test_consumption_weights_and_skips() -> None:
    assert R.estimate_consumption([_m(0, 8.0)], _dosed_20, 0.1) is None
    # Too close together: unusable
    assert R.estimate_consumption([_m(0, 8.0), _m(0.1, 8.0)], _dosed_20, 0.1) is None
    # A suspect measurement is left out
    values = [_m(0, 8.0), _m(7, 3.0, suspect=True), _m(14, 7.3 - 0.7)]
    assert R.estimate_consumption(values, _dosed_20, 0.1) == pytest.approx(2.1)
    # Recent intervals weigh more: 2.0 then 2.2 dKH/day, weights 4.9 and 7
    # -> (2.0 * 4.9 + 2.2 * 7) / 11.9 = 2.1176
    values = [_m(0, 8.0), _m(7, 8.0 + 14.0 - 2.0 * 7), _m(14, 8.0 + 14.0 - 2.2 * 7)]
    result = R.estimate_consumption(values, _dosed_20, 0.1)
    assert result == pytest.approx(2.1176, abs=1e-4)


def test_is_suspect() -> None:
    previous = _m(0, 8.0)
    at = T0 + timedelta(days=7)
    # Predicted 8.0 + 14 - 14.7 = 7.3
    assert not R.is_suspect(previous, 7.5, at, 2.1, 140.0, 0.1, 0.2)
    assert R.is_suspect(previous, 8.2, at, 2.1, 140.0, 0.1, 0.2)
    assert not R.is_suspect(previous, 12.0, at, None, 140.0, 0.1, 0.2)
    assert not R.is_suspect(previous, 12.0, at, 2.1, 140.0, 0.1, 0.0)


def _assisted(**changes: Any) -> R.HeadSettings:
    settings = R.HeadSettings()
    settings.set("mode", "assisted")
    settings.set("target", 8.4)
    for key, value in changes.items():
        settings.set(key, value)
    return settings


def test_proposal_worked_example() -> None:
    # Maintenance 2.1 / 0.1 = 21 mL; gap 1.1 dKH over 3 days = 0.367/day
    # = 3.67 mL; 24.67 mL capped at +20 % of 20 mL = 24 mL
    proposal = R.compute_proposal(_assisted(), 7.3, 20.0, 2.1, 0.1, T0)
    assert proposal.maintenance == pytest.approx(21.0)
    assert proposal.correction == pytest.approx(3.67, abs=0.01)
    assert proposal.dose == 24.0 and proposal.limited
    # Without the cap: 24.7
    proposal = R.compute_proposal(_assisted(max_change_pct=50), 7.3, 20.0, 2.1, 0.1, T0)
    assert proposal.dose == 24.7 and not proposal.limited


def test_proposal_cases() -> None:
    settings = _assisted()
    # No consumption yet: the current dose holds, plus the correction
    first = R.compute_proposal(settings, 8.0, 20.0, None, 0.1, T0)
    assert first.maintenance == 20.0 and first.dose == pytest.approx(21.3)
    # Inside the tolerance: no correction
    steady = R.compute_proposal(settings, 8.3, 20.0, 2.0, 0.1, T0)
    assert steady.correction == 0 and steady.dose == 20.0
    # The correction per day is capped (KH: 0.5 dKH/day)
    far = R.compute_proposal(_assisted(max_change_pct=100), 4.0, 20.0, 2.0, 0.1, T0)
    assert far.correction == pytest.approx(5.0)
    # Never negative; no current dose: no relative cap
    high = R.compute_proposal(settings, 12.0, 0.0, -1.0, 0.1, T0)
    assert high.dose == 0.0
    # Within what the doser accepts
    huge = R.compute_proposal(settings, 8.4, 0.0, 100.0, 0.1, T0)
    assert huge.dose == R.MAX_DAILY_DOSE_ML


def test_proposal_worth_it() -> None:
    base = R.compute_proposal(_assisted(), 8.4, 20.0, 2.0, 0.1, T0)
    assert not R.proposal_worth_it(base)
    base.dose = 21.5
    assert R.proposal_worth_it(base)
    base.current = 0
    assert R.proposal_worth_it(base)
    base.dose = 0
    assert not R.proposal_worth_it(base)


def test_measurement_and_proposal_round_trip() -> None:
    measurement = R.Measurement(T0, "salinity", 35.1, "refractometer", True, 34.9)
    assert R.Measurement.from_dict(measurement.as_dict()) == measurement
    for bad in (None, {"at": "x", "parameter": "kh", "value": 1}, {"value": "x"}):
        assert R.Measurement.from_dict(bad) is None
    assert (
        R.Measurement.from_dict({"at": T0.isoformat(), "parameter": "zinc", "value": 1})
        is None
    )
    proposal = R.compute_proposal(_assisted(), 7.3, 20.0, None, 0.1, T0)
    assert R.Proposal.from_dict(proposal.as_dict()) == proposal
    with_consumption = R.compute_proposal(_assisted(), 7.3, 20.0, 2.1, 0.1, T0)
    assert R.Proposal.from_dict(with_consumption.as_dict()) == with_consumption
    assert R.Proposal.from_dict(None) is None
    assert R.Proposal.from_dict({"at": "x"}) is None
    assert R.Proposal.from_dict({"at": T0.isoformat()}) is None


# =============================================================================
# Brine
# =============================================================================


def test_brine_conversions() -> None:
    # 200 L at 100 g/L: 0.1 ppt is 20.5 g of salt, i.e. 205 mL
    assert R.ppt_to_ml(0.1, 200.0, 100.0) == pytest.approx(205.0)
    assert R.ml_to_ppt(205.0, 200.0, 100.0) == pytest.approx(0.1)


def test_estimate_loss() -> None:
    # Day 2 got 205 mL (+0.1 ppt) and rose by 0.05: 0.05 ppt/day lost
    avgs = {"2026-10-01": 35.0, "2026-10-02": 35.05, "2026-10-04": 35.0}
    daily = {"2026-10-02": 205.0, "2026-10-04": 0.0}
    assert R.estimate_loss(avgs, daily, 200.0, 100.0) == pytest.approx(0.05)
    # Gaps and days without volume are skipped
    assert R.estimate_loss({"2026-10-01": 35.0}, {}, 200.0, 100.0) is None
    assert (
        R.estimate_loss({"2026-10-01": 35.0, "2026-10-02": 35.0}, {}, 200.0, 100.0)
        is None
    )
    # Never negative
    rising = {"2026-10-01": 35.0, "2026-10-02": 35.5}
    assert R.estimate_loss(rising, {"2026-10-02": 0.0}, 200.0, 100.0) == 0.0


def _brine(**changes: Any) -> R.HeadSettings:
    settings = R.HeadSettings()
    settings.set("mode", "brine")
    for key, value in changes.items():
        settings.set(key, value)
    return settings


def test_brine_plan() -> None:
    # 0.5 ppt short over 3 days: 0.167 ppt/day in 200 L = 34.2 g of salt,
    # 170.8 mL of the default 200 g/L brine
    assert _brine().brine_concentration == 200.0
    plan = R.brine_plan(_brine(), 34.5, None, 200.0, prudent=False)
    assert plan.need_ppt == pytest.approx(0.1667, abs=1e-4)
    assert plan.ml_per_day == pytest.approx(170.8, abs=0.1)
    weaker = R.brine_plan(_brine(brine_concentration=100), 34.5, None, 200.0, False)
    assert weaker.ml_per_day == pytest.approx(341.7, abs=0.1)
    assert not plan.capped
    # Prudent: half of the max rise (0.25)
    far = R.brine_plan(_brine(), 33.0, 0.05, 200.0, prudent=True)
    assert far.need_ppt == 0.25 and far.capped
    # Too salty: the loss is not compensated while the excess lasts
    salty = R.brine_plan(_brine(), 36.0, 0.05, 200.0, prudent=False)
    assert salty.need_ppt == 0.0
    # On target: only the loss
    steady = R.brine_plan(_brine(), 35.1, 0.05, 200.0, prudent=False)
    assert steady.need_ppt == pytest.approx(0.05)


def test_slot_dose() -> None:
    assert R.slot_dose(0.0, 12, 0.5) == (0.0, 0.0)
    # 6 mL/day in 12 doses: 0.5 mL carried, then dosed
    assert R.slot_dose(6.0, 12, 0.0) == (0.0, 0.5)
    dose, carry = R.slot_dose(6.0, 12, 0.5)
    assert dose == 1.0 and carry == pytest.approx(0.0)
    dose, carry = R.slot_dose(341.7, 12, 0.0)
    assert dose == 28.4 and carry == pytest.approx(0.075, abs=1e-3)


def test_parse_dt() -> None:
    assert R.parse_dt(None) is None
    assert R.parse_dt("x") is None
    assert R.parse_dt("2026-10-01T10:00:00") == T0
    assert R.parse_dt(T0.isoformat()) == T0


# =============================================================================
# Store
# =============================================================================


def test_head_state_round_trip_and_prune() -> None:
    state = R.HeadState.empty()
    state.settings.set("mode", "brine")
    state.daily = {"2026-01-01": 5.0, "2026-09-30": 6.0}
    state.measurements = [R.Measurement(T0, "salinity", 35.0)]
    state.proposal = R.compute_proposal(_assisted(), 7.3, 20.0, None, 0.1, T0)
    state.history = [{"at": "x"}] * 60
    state.samples = [(T0.timestamp(), 35.0)]
    state.day_sums = {f"2026-09-{d:02d}": (35.0, 1) for d in range(1, 21)}
    state.carry = 0.3
    state.next_slot = T0
    state.last_check = T0
    state.recal_since = T0
    state.deviation = "too_low"
    state.deviation_since = T0
    state.last_good_sample = T0
    again = R.HeadState.from_dict(state.as_dict())
    assert again.as_dict() == state.as_dict()
    state.prune(T0)
    assert list(state.daily) == ["2026-09-30"]
    assert len(state.history) == 50
    assert len(state.day_sums) == R.DAY_STATS_KEPT


def test_head_state_from_garbage() -> None:
    assert R.HeadState.from_dict(None).status == "off"
    state = R.HeadState.from_dict(
        {
            "daily": {"a": "x", "b": 2},
            "measurements": [None],
            "history": "x",
            "brine": {
                "samples": [[1, "x"], [1, 2, 3], [1.0, 35.0]],
                "day_sums": {"d": [1], "e": [35.0, 1]},
                "carry": "x",
                "deviation": 3,
            },
        }
    )
    assert state.daily == {"b": 2.0}
    assert state.samples == [(1.0, 35.0)]
    assert state.day_sums == {"e": (35.0, 1)}
    assert state.carry == 0.0 and state.deviation is None and state.history == []


async def test_store_saves_reloads_and_notifies(hass: HomeAssistant) -> None:
    store = R.RegulationStore(hass, "e1", [1, 2])
    await store.async_load()
    calls: list[int] = []
    remove = store.async_add_listener(lambda: calls.append(1))
    store.heads[1].settings.set("mode", "assisted")
    await store.async_save()
    store.async_delay_save()
    assert calls == [1, 1]
    remove()
    remove()
    store.notify()
    assert calls == [1, 1]
    again = R.RegulationStore(hass, "e1", [1, 2])
    await again.async_load()
    assert again.heads[1].settings.mode == "assisted"
    assert again.heads[2].settings.mode == "off"


# =============================================================================
# Regulator: assisted mode
# =============================================================================


async def test_assisted_flow(hass: HomeAssistant) -> None:
    regulator, doser, clock = await _regulator(hass)
    doser.data[DD(1)] = 20
    await regulator.async_set(1, "mode", "assisted")
    assert regulator.head_state(1).status == "not_configured"
    assert regulator.head_state(1).details["missing"] == ["tank_volume", "potency"]
    await regulator.async_set(1, "potency", 0.1)
    await regulator.async_set(1, "tank_volume", 100)
    await regulator.async_set(1, "target", 8.4)
    assert regulator.head_state(1).status == "waiting_data"

    # First test: the current dose is assumed to hold, plus a correction
    result = await regulator.async_record(1, 8.0)
    state = regulator.head_state(1)
    assert result == {"recorded": True, "suspect": False}
    assert state.status == "proposal" and state.proposal is not None
    assert state.proposal.dose == pytest.approx(21.3)
    assert doser.my_api.fetched[-1] == R.DAILY_LOG

    await regulator.async_dismiss(1)
    assert state.proposal is None and state.status == "in_range"
    assert state.history[-1]["action"] == "dismissed"
    # Nothing pending: nothing to apply or dismiss
    assert await regulator.async_apply(1) is None
    await regulator.async_dismiss(1)
    assert len(state.history) == 1

    # A week later: consumption 2.1 dKH/day, dose 24 mL (capped +20 %)
    clock.advance(days=7)
    await regulator.async_record(1, 7.3)
    assert state.proposal is not None and state.proposal.dose == 24.0
    assert state.details["last_proposal"]["consumption"] == pytest.approx(2.1)
    assert await regulator.async_apply(1) == 24.0
    assert doser.data[DD(1)] == 24 and doser.pushed == [1] and doser.refreshes == 1
    assert state.history[-1] == {
        "at": clock().isoformat(),
        "from": 20.0,
        "to": 24.0,
        "action": "applied",
    }
    assert state.status == "in_range"


async def test_assisted_suspect_then_confirmed(hass: HomeAssistant) -> None:
    regulator, doser, clock = await _regulator(hass)
    doser.data[DD(1)] = 20
    await regulator.async_set(1, "mode", "assisted")
    await regulator.async_set(1, "potency", 0.1)
    await regulator.async_set(1, "tank_volume", 100)
    await regulator.async_record(1, 8.0)
    clock.advance(days=7)
    await regulator.async_record(1, 7.3)
    # Predicted 7.3 + 14 - 14.7 = 6.6: 9.0 is far off
    clock.advance(days=7)
    result = await regulator.async_record(1, 9.0)
    state = regulator.head_state(1)
    assert result["suspect"] and state.status == "retest_suggested"
    assert state.proposal is None
    # The retest agrees: the jump was real
    clock.advance(hours=1)
    result = await regulator.async_record(1, 9.1)
    assert not result["suspect"]
    assert not any(m.suspect for m in state.measurements)
    assert state.status in ("proposal", "in_range")


async def test_assisted_other_parameter_and_garbage(hass: HomeAssistant) -> None:
    regulator, _doser, _clock = await _regulator(hass)
    await regulator.async_set(1, "mode", "assisted")
    await regulator.async_set(1, "potency", 0.1)
    await regulator.async_set(1, "tank_volume", 100)
    # Another parameter: kept, no proposal
    await regulator.async_record(1, 420.0, "ca")
    state = regulator.head_state(1)
    assert state.proposal is None and state.status == "waiting_data"
    with pytest.raises(ValueError):
        await regulator.async_record(1, 1.0, "zinc")
    # The typed-in value is used when none is given; no dose set: proposal
    # from the correction only
    await regulator.async_set(1, "measurement", 7.0)
    await regulator.async_record(1)
    assert state.measurements[-1].value == 7.0
    assert state.proposal is not None and state.proposal.current == 0.0


async def test_assisted_without_volume_proposes_nothing(hass: HomeAssistant) -> None:
    regulator, _doser, _clock = await _regulator(hass)
    await regulator.async_set(1, "mode", "assisted")
    regulator._propose(1)
    assert regulator.head_state(1).proposal is None
    await regulator.async_set(1, "potency", 0.1)
    await regulator.async_set(1, "tank_volume", 100)
    regulator._propose(1)  # no measurement yet
    assert regulator.head_state(1).proposal is None


async def test_bundle_regulates_head_1_on_calcium_only(hass: HomeAssistant) -> None:
    regulator, doser, _clock = await _regulator(hass)
    await regulator.async_set(1, "mode", "assisted")
    await regulator.async_set(1, "parameter", "mg")
    await regulator.async_set(2, "mode", "assisted")
    doser.data[BUNDLE] = True
    # Set before the bundle: head 2 and a head 1 on another parameter wait
    regulator.refresh_status(1)
    regulator.refresh_status(2)
    assert regulator.head_state(1).status == "bundle"
    assert regulator.head_state(2).status == "bundle"
    # Only head 1, in assisted mode, on the calcium
    with pytest.raises(ValueError):
        await regulator.async_set(2, "mode", "assisted")
    with pytest.raises(ValueError):
        await regulator.async_set(1, "mode", "brine")
    with pytest.raises(ValueError):
        await regulator.async_set(1, "parameter", "kh")
    await regulator.async_set(1, "mode", "assisted")
    state = regulator.head_state(1)
    assert state.settings.parameter == "ca"
    assert state.status == "not_configured"
    # Turning a head off is always possible
    await regulator.async_set(2, "mode", "off")
    assert regulator.head_state(2).status == "off"
    # A brine head is not run while bundled
    put_brine(doser)
    with pytest.raises(ValueError, match="assisted mode only"):
        await regulator.async_set(1, "mode", "brine")
    regulator.head_state(1).settings.mode = "brine"
    await regulator._async_tick()
    assert regulator.head_state(1).status == "bundle"


async def test_daily_log_sync(hass: HomeAssistant) -> None:
    regulator, doser, clock = await _regulator(hass, (1, 4))
    await regulator.async_sync_daily_log()
    assert regulator.head_state(1).daily == {}
    clock.at = datetime(2025, 11, 21, 12, tzinfo=timezone.utc)
    doser.data[LOG] = json.loads(
        (FIXTURES / "DOSE4" / "daily-log" / "data").read_text()
    )
    await regulator.async_sync_daily_log()
    assert len(regulator.head_state(4).daily) == 7


async def test_scheduled_dose(hass: HomeAssistant) -> None:
    regulator, doser, _clock = await _regulator(hass)
    doser.data[DD(1)] = 12
    assert regulator.scheduled_dose(1) == 12
    doser.data[ENABLED(1)] = False
    assert regulator.scheduled_dose(1) == 0


# =============================================================================
# Regulator: tank volume
# =============================================================================


def test_cloud_volume_l() -> None:
    assert R.cloud_volume_l({"net_water_volume": 330, "water_volume": 400}) == 330.0
    assert R.cloud_volume_l({"net_water_volume": 0, "water_volume": 400}) == 400.0
    assert R.cloud_volume_l(
        {"net_water_volume": 100, "measuring_unit": "gallons"}
    ) == pytest.approx(378.5)
    assert R.cloud_volume_l({}) is None


REEFTANK_UID = "aq1_water_volume"


async def test_reeftank_volume(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea import websocket

    regulator, _doser, _clock = await _regulator(hass)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    regulator.device._entry = entry  # type: ignore[attr-defined]
    dev_reg = dr.async_get(hass)
    doser = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "HWID")}
    )
    head = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "HWID_head_2")}
    )
    aquariums: list[dict[str, Any]] = [
        {"uid": "cloud-1", "device_ids": [doser.id], "net_water_volume": 300}
    ]
    monkeypatch.setattr(websocket, "cloud_aquariums", lambda hass: aquariums)
    ent_reg = er.async_get(hass)
    tank = ent_reg.async_get_or_create(
        "sensor", "reeftank", REEFTANK_UID, suggested_object_id="tank_water_volume"
    )
    # Other reeftank sensors and integrations are ignored
    ent_reg.async_get_or_create(
        "sensor", "reeftank", "aq1_fish", suggested_object_id="tank_fish"
    )
    hass.states.async_set("sensor.tank_fish", "8", {"device_ids": [doser.id]})
    ent_reg.async_get_or_create(
        "sensor", "other", REEFTANK_UID, suggested_object_id="other_volume"
    )
    hass.states.async_set("sensor.other_volume", "999", {"device_ids": [doser.id]})

    def tank_state(value: str, **attributes: Any) -> None:
        hass.states.async_set(tank.entity_id, value, attributes)

    # Registered but no state yet: the cloud volume
    assert regulator.volume(1) == (300.0, "cloud")
    tank_state("425", device_ids=["someone_else"], cloud=None)
    assert regulator.volume(1) == (300.0, "cloud")
    # A head placed on the aquarium's views
    tank_state("425", device_ids=[head.id])
    assert regulator.volume(1) == (425.0, "reeftank")
    # The doser itself placed
    tank_state("426", device_ids=[doser.id])
    assert regulator.volume(1) == (426.0, "reeftank")
    # Linked to the doser's cloud aquarium only
    tank_state("427", cloud={"provider": "redsea", "uid": "cloud-1"})
    assert regulator.volume(1) == (427.0, "reeftank")
    tank_state("427", cloud={"provider": "other", "uid": "cloud-1"})
    assert regulator.volume(1) == (300.0, "cloud")
    # Unknown, unset or zero volume: the cloud volume
    for value in ("unknown", "0", "nan"):
        tank_state(value, device_ids=[doser.id])
        assert regulator.volume(1) == (300.0, "cloud")
    # Without cloud aquarium, reeftank still works through the devices
    aquariums.clear()
    tank_state("428", device_ids=[doser.id], cloud={"provider": "redsea", "uid": "x"})
    assert regulator.volume(1) == (428.0, "reeftank")
    # The user's value wins
    await regulator.async_set(1, "tank_volume", 250)
    assert regulator.volume(1) == (250.0, "user")


async def test_cloud_volume(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea import websocket

    regulator, _doser, _clock = await _regulator(hass)
    assert regulator.volume(1) == (None, None)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    regulator.device._entry = entry  # type: ignore[attr-defined]
    assert regulator.volume(1) == (None, None)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "HWID")}
    )
    aquariums: list[dict[str, Any]] = [
        {"device_ids": ["other"], "net_water_volume": 50},
        {
            "device_ids": [device.id],
            "net_water_volume": 100,
            "measuring_unit": "gallons",
        },
    ]
    monkeypatch.setattr(websocket, "cloud_aquariums", lambda hass: aquariums)
    assert regulator.volume(1) == (378.5, "cloud")
    aquariums[1] = {
        "device_ids": [device.id],
        "net_water_volume": None,
        "water_volume": 300,
    }
    assert regulator.volume(1) == (300.0, "cloud")
    aquariums[1] = {"device_ids": [device.id]}
    assert regulator.volume(1) == (None, None)
    await regulator.async_set(1, "tank_volume", 250)
    assert regulator.volume(1) == (250.0, "user")


# =============================================================================
# Regulator: brine
# =============================================================================


SENSOR = "sensor.tank_salinity"


async def _brine_regulator(
    hass: HomeAssistant, salinity: str = "34.5"
) -> tuple[R.DoseRegulator, FakeDoser, Clock]:
    regulator, doser, clock = await _regulator(hass)
    put_brine(doser)
    hass.states.async_set(SENSOR, salinity, {"unit_of_measurement": "ppt"})
    await regulator.async_set(1, "mode", "brine")
    await regulator.async_set(1, "salinity_source", SENSOR)
    await regulator.async_set(1, "tank_volume", 200)
    await regulator.async_set(1, "brine_concentration", 100)
    return regulator, doser, clock


SCHEDULE = "$.sources[?(@.name=='/head/1/settings')].data.schedule_enabled"


async def test_brine_mode_stops_the_head_schedule(hass: HomeAssistant) -> None:
    """The brine is dosed by Home Assistant alone: its schedule goes off."""
    regulator, doser, _ = await _regulator(hass)
    put_brine(doser)
    doser.data[SCHEDULE] = True
    await regulator.async_set(1, "mode", "brine")
    assert doser.data[SCHEDULE] is False
    assert doser.pushed == [1]
    assert doser.refreshes == 1
    # Already off: nothing pushed again
    await regulator.async_set(1, "mode", "off")
    await regulator.async_set(1, "mode", "brine")
    assert doser.pushed == [1]
    # Leaving the brine mode leaves the schedule alone
    await regulator.async_set(1, "mode", "off")
    assert doser.data[SCHEDULE] is False


async def _ticks(regulator: R.DoseRegulator, clock: Clock, count: int) -> None:
    for _ in range(count):
        clock.advance(minutes=10)
        await regulator._async_tick()


async def test_brine_flow(hass: HomeAssistant) -> None:
    regulator, doser, clock = await _brine_regulator(hass)
    state = regulator.head_state(1)
    # Sampled as soon as the sensor is chosen
    assert state.status == "waiting_data"
    assert state.details["samples"] == 1
    assert state.details["samples_needed"] == R.MIN_SAMPLES
    await _ticks(regulator, clock, 4)
    assert state.status == "waiting_data" and doser.doses == []
    await _ticks(regulator, clock, 1)
    # 0.5 ppt short, never checked (prudent: max 0.25 ppt/day): 0.167
    # ppt/day = 341.7 mL/day, 12 doses of 28.4 mL
    assert state.status == "regulating"
    assert state.details["prudent"] is True
    assert state.details["plan_ml_day"] == pytest.approx(341.7)
    assert doser.doses == [(1, 28.4)]
    assert state.details["last_dose"]["ml"] == 28.4
    # Not due again before 2 hours
    await _ticks(regulator, clock, 3)
    assert len(doser.doses) == 1
    await _ticks(regulator, clock, 9)
    assert len(doser.doses) == 2
    # Switched back on by the user, the head's own schedule doses part of
    # it already
    doser.data[SCHEDULE] = True
    doser.data[DD(1)] = 341.7
    clock.advance(hours=2)
    await regulator._async_tick()
    assert len(doser.doses) == 2
    # A refused dose is kept for the next slot
    doser.data[DD(1)] = 0
    doser.dose_ok = False
    carry = state.carry
    clock.advance(hours=2)
    await regulator._async_tick()
    assert state.carry == pytest.approx(carry + 28.47, abs=0.01)


async def test_brine_glitch_and_day_rollover(hass: HomeAssistant) -> None:
    regulator, doser, clock = await _brine_regulator(hass)
    await _ticks(regulator, clock, 6)
    state = regulator.head_state(1)
    hass.states.async_set(SENSOR, "38.0", {"unit_of_measurement": "ppt"})
    await _ticks(regulator, clock, 1)
    # The first sample, then 6 ticks: the glitch is not kept
    assert len(state.samples) == 7
    fetched = len(doser.my_api.fetched)
    clock.advance(days=1)
    await regulator._async_tick()
    assert len(doser.my_api.fetched) == fetched + 1


async def test_brine_source_lost(hass: HomeAssistant) -> None:
    regulator, _doser, clock = await _brine_regulator(hass)
    await _ticks(regulator, clock, 6)
    state = regulator.head_state(1)
    events: list[Any] = []
    hass.bus.async_listen(R.EVENT_ALARM, events.append)
    hass.states.async_set(SENSOR, "unavailable")
    await _ticks(regulator, clock, 4)
    assert state.status == "source_unavailable" and state.alarm is None
    await _ticks(regulator, clock, 12)
    assert state.alarm == "source_unavailable"
    await hass.async_block_till_done()
    assert events[0].data == {
        "device": "Doser",
        "serial": "SER",
        "head": 1,
        "alarm": "source_unavailable",
    }


async def test_brine_sensor_never_readable(hass: HomeAssistant) -> None:
    regulator, doser, _clock = await _regulator(hass)
    put_brine(doser)
    await regulator.async_set(1, "mode", "brine")
    await regulator.async_set(1, "tank_volume", 200)
    assert regulator.head_state(1).details["missing"] == ["salinity_source"]
    await regulator.async_set(1, "salinity_source", "sensor.nothing")
    assert regulator.head_state(1).status == "source_unavailable"
    assert regulator.read_salinity(2) is None


def _fresh_samples(regulator: R.DoseRegulator, clock: Clock, ppt: float) -> None:
    state = regulator.head_state(1)
    state.samples = [(clock().timestamp(), ppt)] * R.MIN_SAMPLES
    state.last_good_sample = clock()


async def test_brine_too_salty(hass: HomeAssistant) -> None:
    regulator, doser, clock = await _brine_regulator(hass)
    state = regulator.head_state(1)
    _fresh_samples(regulator, clock, 36.0)
    regulator.refresh_status(1)
    assert state.status == "too_salty" and state.alarm is None
    clock.advance(hours=25)
    _fresh_samples(regulator, clock, 36.0)
    regulator.refresh_status(1)
    assert state.alarm == "too_salty"
    # No brine while too salty
    await regulator._async_tick()
    assert doser.doses == []
    # Back on target: the deviation ends
    _fresh_samples(regulator, clock, 35.0)
    regulator.refresh_status(1)
    assert state.status == "regulating" and state.deviation is None


async def test_brine_cannot_compensate_keeps_dosing(hass: HomeAssistant) -> None:
    regulator, doser, clock = await _brine_regulator(hass)
    state = regulator.head_state(1)
    _fresh_samples(regulator, clock, 34.0)
    regulator.refresh_status(1)
    assert state.status == "regulating"
    clock.advance(days=3)
    _fresh_samples(regulator, clock, 34.0)
    regulator.refresh_status(1)
    assert state.status == "cannot_compensate"
    assert state.alarm == "cannot_compensate"
    assert state.details["capped"] is True
    hass.states.async_set(SENSOR, "34.0", {"unit_of_measurement": "ppt"})
    await regulator._async_tick()
    assert len(doser.doses) == 1


async def test_brine_loss_from_days(hass: HomeAssistant) -> None:
    regulator, _doser, clock = await _brine_regulator(hass)
    state = regulator.head_state(1)
    state.day_sums = {
        "2026-09-29": (35.0 * 10, 10),
        "2026-09-30": (35.05 * 10, 10),
        "2026-10-01": (99.0, 1),  # today: left out
    }
    state.daily = {"2026-09-30": 205.0}
    assert regulator.loss(1) == pytest.approx(0.05)
    await regulator.async_set(1, "tank_volume", 0)
    assert regulator.loss(1) is None
    assert clock() == T0


async def test_refractometer_check(hass: HomeAssistant) -> None:
    regulator, _doser, clock = await _brine_regulator(hass)
    state = regulator.head_state(1)
    result = await regulator.async_record(1, 34.8)
    assert result == {
        "recorded": True,
        "checked": True,
        "within": True,
        "probe": 34.5,
        "gap": -0.3,
    }
    assert state.last_check == clock() and not regulator.prudent(1)
    assert state.measurements[-1].source == "refractometer"
    # Out of tolerance: recalibration needed, the regulation pauses
    clock.advance(days=30)
    result = await regulator.async_record(1, 36.0)
    assert result["within"] is False
    assert state.status == "recalibration_required"
    assert state.alarm == "recalibration_required"
    # A good check clears it
    clock.advance(hours=1)
    await regulator.async_record(1, 34.6)
    assert state.recal_since is None
    # Not sampled for 30 days: the regulation starts over
    await regulator._async_tick()
    assert state.status == "waiting_data"
    # No probe reading: recorded, not checked
    hass.states.async_set(SENSOR, "unavailable")
    result = await regulator.async_record(1, 35.0)
    assert result == {"recorded": True, "checked": False}


async def test_refractometer_check_drives_the_probe_tasks(hass: HomeAssistant) -> None:
    regulator, _doser, clock = await _regulator(hass)
    maintenance = MaintenanceStore(hass, "control")
    await maintenance.async_load()
    control = MagicMock(spec=ReefControlCoordinator)
    control.serial = "CTRL"
    control.maintenance = maintenance
    control.get_data.return_value = [
        "junk",
        {"uid": "0x0032B", "type": "ph"},
        {"uid": "zz", "type": "ec"},
        {"uid": "0x0032B", "type": "ec"},
    ]
    # Another hub first: its probes are not the source
    another = MagicMock(spec=ReefControlCoordinator)
    another.serial = "OTHER"
    hass.data.setdefault(DOMAIN, {})["another"] = another
    hass.data[DOMAIN]["control"] = control
    hass.data[DOMAIN]["doser"] = object()
    ent_reg = er.async_get(hass)
    probe = ent_reg.async_get_or_create(
        "sensor", DOMAIN, "CTRL_probe_ec_0x0032b_ppt", suggested_object_id="ctrl_ppt"
    )
    other = ent_reg.async_get_or_create(
        "sensor", "other", "x", suggested_object_id="other_ppt"
    )
    for entity_id in (probe.entity_id, other.entity_id):
        hass.states.async_set(entity_id, "34.5", {"unit_of_measurement": "ppt"})
    put_brine(regulator.device)
    await regulator.async_set(1, "mode", "brine")
    await regulator.async_set(1, "tank_volume", 200)
    await regulator.async_set(1, "salinity_source", probe.entity_id)
    sub_id = int("0x0032B", 16)

    await regulator.async_record(1, 34.7)
    assert maintenance.get_last_reset("CTRL", sub_id, REFRACTOMETER_TASK) == clock()

    clock.advance(days=1)
    await regulator.async_record(1, 37.0)
    state = regulator.head_state(1)
    assert state.status == "recalibration_required"
    # Calibrating the probe with a solution clears it
    await maintenance.async_record_reset(
        "CTRL", sub_id, CALIBRATION_TASKS["ec"], clock() + timedelta(minutes=5)
    )
    regulator.refresh_status(1)
    assert state.recal_since is None

    # A probe whose uid cannot be parsed, a sensor of another integration
    control.get_data.return_value = [{"uid": "zz", "type": "ec"}]
    zz = ent_reg.async_get_or_create("sensor", DOMAIN, "CTRL_probe_ec_zz_ppt")
    await regulator.async_set(1, "salinity_source", zz.entity_id)
    assert regulator._probe_of_source(1) is None
    await regulator.async_set(1, "salinity_source", other.entity_id)
    assert regulator._probe_of_source(1) is None
    control.get_data.return_value = None
    await regulator.async_set(1, "salinity_source", probe.entity_id)
    assert regulator._probe_of_source(1) is None
    assert not regulator._probe_calibrated_since(1, clock())
    # A probe without maintenance store
    control.get_data.return_value = [{"uid": "0x0032B", "type": "ec"}]
    control.maintenance = None
    assert not regulator._probe_calibrated_since(1, clock())
    await regulator._async_reset_probe_check()


async def test_start_and_stop(hass: HomeAssistant) -> None:
    regulator, doser, _clock = await _regulator(hass)
    await regulator.async_start()
    assert doser.my_api.fetched == [R.DAILY_LOG]
    assert regulator._unsubs
    assert len(doser.listeners) == 1
    regulator.async_stop()
    assert not regulator._unsubs
    assert doser.listeners == []
    # The real clock
    assert R.DoseRegulator.now(regulator).tzinfo is not None


async def test_supplement_change_seen_at_once(hass: HomeAssistant) -> None:
    """The brine put on a head after start: its modes and status follow on
    the next read of the doser, without waiting for a regulation change."""
    regulator, doser, _clock = await _regulator(hass)
    await regulator.async_set(1, "mode", "assisted")
    await regulator.async_start()
    notified: list[bool] = []
    regulator.store.async_add_listener(lambda: notified.append(True))
    (listener,) = doser.listeners
    # Nothing changed on the doser: nothing to tell
    listener()
    assert notified == []
    put_brine(doser)
    listener()
    assert notified == [True]
    assert regulator.modes(1) == ["off", "brine"]
    assert regulator.head_state(1).status == "not_configured"
    assert regulator.head_state(1).details == {"missing": ["supplement"]}
    listener()
    assert notified == [True]
    regulator.async_stop()


async def test_assisted_review_cases(hass: HomeAssistant) -> None:
    regulator, doser, clock = await _regulator(hass)
    doser.data[DD(1)] = 20
    await regulator.async_set(1, "mode", "assisted")
    await regulator.async_set(1, "potency", 0.1)
    await regulator.async_set(1, "tank_volume", 100)
    await regulator.async_record(1, 8.0)
    state = regulator.head_state(1)
    # A new target makes a new proposal at once
    await regulator.async_set(1, "target", 8.0)
    assert state.proposal is None and state.status == "in_range"
    await regulator.async_set(1, "target", 8.6)
    assert state.proposal is not None and state.proposal.target == 8.6

    clock.advance(days=7)
    await regulator.async_record(1, 7.3)
    clock.advance(days=7)
    await regulator.async_record(1, 9.0)
    assert state.status == "retest_suggested"
    # A test of another parameter afterwards does not lift the doubt
    clock.advance(hours=1)
    await regulator.async_record(1, 420.0, "ca")
    regulator._propose(1)
    assert state.proposal is None

    # A back-dated result is not checked against a later one
    result = await regulator.async_record(1, 20.0, "kh", T0 - timedelta(days=1))
    assert result["suspect"] is False
    assert state.measurements[0].value == 20.0


async def test_tick_refreshes_assisted_heads(hass: HomeAssistant) -> None:
    regulator, _doser, _clock = await _regulator(hass)
    await regulator.async_set(1, "mode", "assisted")
    await regulator.async_set(1, "potency", 0.1)
    state = regulator.head_state(1)
    assert state.status == "not_configured"
    # The volume becomes known (here set behind the regulator's back)
    state.settings.tank_volume = 100
    await regulator._async_tick()
    assert state.status == "waiting_data"


async def test_brine_only_with_the_brine_supplement(hass: HomeAssistant) -> None:
    from custom_components.redsea.supplements_list import SUPPLEMENTS

    # The brine of the regulation is the one of the supplement list
    assert any(s["uid"] == R.BRINE_SUPPLEMENT_UID for s in SUPPLEMENTS)
    regulator, doser, clock = await _regulator(hass)
    assert regulator.modes(1) == ["off", "assisted"]
    with pytest.raises(ValueError, match="brine supplement"):
        await regulator.async_set(1, "mode", "brine")
    put_brine(doser)
    assert regulator.modes(1) == ["off", "brine"]
    with pytest.raises(ValueError, match="not available"):
        await regulator.async_set(1, "mode", "assisted")
    await regulator.async_set(1, "mode", "brine")
    # The brine is removed from the head: the regulation stops
    doser.data[SUPPLEMENT(1)] = "null"
    hass.states.async_set(SENSOR, "34.5", {"unit_of_measurement": "ppt"})
    await regulator.async_set(1, "salinity_source", SENSOR)
    state = regulator.head_state(1)
    assert state.status == "not_configured"
    assert state.details == {"missing": ["supplement"]}
    clock.advance(minutes=10)
    await regulator._async_tick()
    assert state.samples == [] and doser.doses == []
    # Turning it off is always possible
    await regulator.async_set(1, "mode", "off")
    assert state.status == "off"
