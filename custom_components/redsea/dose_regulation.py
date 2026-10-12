"""Dose regulation of the ReefDose heads.

Two regulation modes per head, chosen with the ``regulation_mode`` select:

- ``assisted``: the user sets a target (e.g. KH 8.4 dKH) and records a test
  result from time to time. From the measurements and the volumes actually
  dosed in between, the consumption of the tank is estimated and a new daily
  dose is *proposed*. Nothing reaches the doser until the user applies it.
- ``brine``: the head holds a brine (salt dissolved in water, g/L). A
  salinity sensor (an RSCONTROL EC probe or any Home Assistant sensor) is
  sampled every few minutes and Home Assistant sends small manual doses to
  keep the salinity on target. Manual doses rather than the head's own
  schedule: when Home Assistant is down nothing is dosed, which is the safe
  side (salinity then drifts down slowly).

Volumes dosed come from the doser's ``/daily-log`` (the last 7 days, per
head), merged into a local store that keeps up to ``HISTORY_DAYS`` days.

Brine safety:

- a monthly refractometer check (a maintenance task of the RSCONTROL EC
  probe) is recorded as a ``salinity`` measurement; out of tolerance, the
  probe must be calibrated again (with a calibration solution) and the
  regulation pauses until then;
- without a check for ``PRUDENT_AFTER_DAYS`` days the salinity rise allowed
  per day is halved;
- alarms (binary sensor + ``redsea_dose_regulation_alarm`` event) when the
  salinity cannot be brought back to target, when it is too high (brine
  cannot lower it), when the sensor is lost and when a recalibration is due.

Layout of this module:

- catalogue of parameters and per-head settings,
- pure helpers (unit conversions, volume accounting, proposal, brine
  controller): no Home Assistant import is needed to call them,
- ``RegulationStore``: persistence (one file per doser),
- ``DoseRegulator``: wiring with Home Assistant (timers, device I/O).
"""

from __future__ import annotations

import logging
import math
import statistics
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, timedelta, timezone
from itertools import pairwise
from typing import Any, Final, cast

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

STORAGE_VERSION: Final[int] = 1
STORAGE_KEY_TPL: Final[str] = "redsea_dose_regulation_{entry_id}"

# Name of the regulator attribute on a ReefDose coordinator
REGULATOR_ATTR: Final[str] = "regulation"
# Bundled heads (Red Sea Complete Reef Care): the daily dose of head 1 (Part
# 1, calcium & magnesium) is set from a weekly calcium test; the doser
# derives the other heads from the bundle ratios (Part 2 x2, Parts 3-4 x0.5)
BUNDLE_HEAD: Final[int] = 1
BUNDLE_PARAMETER: Final[str] = "ca"
# The brine supplement (supplements_list.py): the only one regulated on the
# salinity, and it is regulated on nothing else
BRINE_SUPPLEMENT_UID: Final[str] = "b99739a8-bced-420e-bbdb-86ccd14524fd"
# Source of the doser holding the volumes dosed over the last 7 days
DAILY_LOG: Final[str] = "/daily-log"
# The reeftank integration (optional): its aquariums' water volume sensors
REEFTANK_DOMAIN: Final[str] = "reeftank"
REEFTANK_VOLUME_KEY: Final[str] = "water_volume"
LITERS_PER_GALLON: Final[float] = 3.78541

# Event fired when a head enters an alarm state
EVENT_ALARM: Final[str] = "redsea_dose_regulation_alarm"

MODES: Final[list[str]] = ["off", "assisted", "brine"]

# Days of dosed volumes and measurements kept in the store
HISTORY_DAYS: Final[int] = 180
# Measurements used to estimate the consumption (most recent intervals)
CONSUMPTION_INTERVALS: Final[int] = 5
# Weight of an interval relative to the next, more recent, one
RECENCY_DECAY: Final[float] = 0.7
# A measurement this many tolerances away from the prediction is suspect
SUSPECT_FACTOR: Final[float] = 3.0
# Shortest interval between two measurements used for an estimate (days)
MIN_INTERVAL_DAYS: Final[float] = 0.5
# Largest daily dose the doser accepts (mL), see number.py daily_dose
MAX_DAILY_DOSE_ML: Final[float] = 300.0
# A proposal this close (relative) to the current dose is not worth applying
PROPOSAL_DEADBAND: Final[float] = 0.05

# Brine: seawater density used to turn a salinity (g/kg) into grams of salt
SEAWATER_DENSITY: Final[float] = 1.025
# Smallest manual dose the doser delivers reliably (mL)
MIN_MANUAL_DOSE_ML: Final[float] = 1.0
# Sampling of the salinity sensor
SAMPLE_INTERVAL: Final[timedelta] = timedelta(minutes=10)
# Window of the salinity average driving the regulation
AVERAGE_WINDOW: Final[timedelta] = timedelta(hours=24)
# Samples needed in the window before the first dose
MIN_SAMPLES: Final[int] = 6
# Plausible salinities (ppt); anything else is a sensor fault
SALINITY_RANGE: Final[tuple[float, float]] = (20.0, 45.0)
# A sample this far (ppt) from the running average is a glitch
MAX_JUMP_PPT: Final[float] = 2.0
# The last good sample must be this recent for the sensor to count as alive
SOURCE_TIMEOUT: Final[timedelta] = timedelta(minutes=30)
# Lost sensor for this long raises the alarm
SOURCE_ALARM_AFTER: Final[timedelta] = timedelta(hours=2)
# Salinity too low despite the doses for this long: cannot compensate
CANNOT_COMPENSATE_AFTER: Final[timedelta] = timedelta(days=3)
# Salinity too high for this long raises the alarm
TOO_SALTY_ALARM_AFTER: Final[timedelta] = timedelta(hours=24)
# Without a refractometer check for this long, the allowed rise is halved
PRUDENT_AFTER_DAYS: Final[int] = 45
# Days of salt loss estimates combined
LOSS_DAYS: Final[int] = 7
# Daily averages kept for the loss estimate
DAY_STATS_KEPT: Final[int] = 14

# Units of the salinity read as ppt as-is (lowercase)
_PPT_UNITS: Final[frozenset[str]] = frozenset({"ppt", "‰", "psu", "g/l", "g/kg"})


@dataclass(frozen=True, slots=True)
class Parameter:
    """A water parameter a head can regulate.

    ``max_rate`` is the largest correction per day (in ``unit``) the
    regulation asks for, whatever the gap to the target.
    """

    unit: str
    target: float
    tolerance: float
    max_rate: float
    step: float


PARAMETERS: Final[dict[str, Parameter]] = {
    "kh": Parameter("dKH", 8.0, 0.2, 0.5, 0.01),
    "ca": Parameter("ppm", 430.0, 10.0, 20.0, 1.0),
    "mg": Parameter("ppm", 1350.0, 30.0, 50.0, 1.0),
    "k": Parameter("ppm", 400.0, 10.0, 20.0, 1.0),
    "no3": Parameter("ppm", 5.0, 1.0, 2.0, 0.1),
    "po4": Parameter("ppm", 0.05, 0.02, 0.03, 0.01),
    "salinity": Parameter("ppt", 35.0, 0.3, 0.5, 0.1),
}

# Options of the parameter select (same order as PARAMETERS)
PARAMETER_OPTIONS: Final[list[str]] = ["kh", "ca", "mg", "k", "no3", "po4", "salinity"]
# Parameters offered in assisted mode (salinity is the brine mode's)
ASSISTED_PARAMETERS: Final[list[str]] = [p for p in PARAMETERS if p != "salinity"]

STATUSES: Final[list[str]] = [
    "off",
    "bundle",
    "not_configured",
    "waiting_data",
    "in_range",
    "proposal",
    "retest_suggested",
    "regulating",
    "too_salty",
    "cannot_compensate",
    "source_unavailable",
    "recalibration_required",
]

ALARMS: Final[list[str]] = [
    "too_salty",
    "cannot_compensate",
    "source_unavailable",
    "recalibration_required",
]


def _as_dict(value: Any) -> dict[str, Any] | None:
    """The value as a JSON object, None if it is not one."""
    return cast(dict[str, Any], value) if isinstance(value, dict) else None


def _as_list(value: Any) -> list[Any]:
    """The value as a JSON array, empty if it is not one."""
    return cast(list[Any], value) if isinstance(value, list) else []


def _pair(value: Any) -> tuple[float, float] | None:
    """A stored pair of numbers, None if it is not one."""
    items: list[Any] = (
        list(cast(tuple[Any, ...], value))
        if isinstance(value, tuple)
        else _as_list(value)
    )
    if len(items) != 2 or not all(isinstance(x, (int, float)) for x in items):
        return None
    return float(items[0]), float(items[1])


# =============================================================================
# Settings
# =============================================================================

# Bounds of the numeric settings: (min, max)
SETTING_BOUNDS: Final[dict[str, tuple[float, float]]] = {
    "target": (0.0, 2000.0),
    "potency": (0.0, 1000.0),
    "tolerance": (0.0, 500.0),
    "tank_volume": (0.0, 20000.0),
    "max_change_pct": (5.0, 100.0),
    "correction_days": (1.0, 14.0),
    "brine_concentration": (10.0, 350.0),
    "brine_max_rise": (0.1, 1.0),
    "brine_doses_per_day": (1.0, 24.0),
    "salinity_check_tolerance": (0.1, 3.0),
    "measurement": (0.0, 2000.0),
}


@dataclass(slots=True)
class HeadSettings:
    """Regulation settings of one head.

    ``potency`` is how much one mL raises the parameter in 100 L of water
    (unit of the parameter / mL / 100 L), as printed on most supplements.
    ``tank_volume`` 0 means "found automatically" (see DoseRegulator.volume).
    ``measurement`` is the value typed in before pressing "record".
    """

    mode: str = "off"
    parameter: str = "kh"
    target: float = PARAMETERS["kh"].target
    potency: float = 0.0
    tolerance: float = PARAMETERS["kh"].tolerance
    tank_volume: float = 0.0
    max_change_pct: float = 20.0
    correction_days: float = 3.0
    brine_concentration: float = 200.0
    brine_max_rise: float = 0.5
    brine_doses_per_day: float = 12.0
    salinity_check_tolerance: float = 1.0
    salinity_source: str = ""
    measurement: float = 0.0

    @classmethod
    def from_dict(cls, raw: Any) -> HeadSettings:
        """Settings read back from the store; unknown or bad values dropped."""
        settings = cls()
        data = _as_dict(raw)
        if data is None:
            return settings
        for f in fields(cls):
            if f.name not in data:
                continue
            try:
                settings.set(f.name, data[f.name], reset_parameter=False)
            except ValueError:
                _LOGGER.debug("Dropping stored setting %s=%r", f.name, data[f.name])
        return settings

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def set(self, key: str, value: Any, reset_parameter: bool = True) -> None:
        """Change one setting, checked.

        Choosing another parameter (or the brine mode, which regulates the
        salinity) brings the target and tolerance of that parameter, unless
        ``reset_parameter`` is False (reading the store back).

        @raise ValueError: unknown key or invalid value
        """
        if key == "mode":
            if value not in MODES:
                raise ValueError(f"unknown mode {value!r}")
            self.mode = value
            if reset_parameter:
                if value == "brine" and self.parameter != "salinity":
                    self._use_parameter("salinity")
                elif value == "assisted" and self.parameter == "salinity":
                    self._use_parameter("kh")
            return
        if key == "parameter":
            if value not in PARAMETERS:
                raise ValueError(f"unknown parameter {value!r}")
            # The brine regulates the salinity, and only the brine does
            if reset_parameter and (self.mode == "brine") != (value == "salinity"):
                raise ValueError(f"parameter {value!r} not allowed in {self.mode} mode")
            if reset_parameter and value != self.parameter:
                self._use_parameter(value)
            else:
                self.parameter = value
            return
        if key == "salinity_source":
            if not isinstance(value, str):
                raise ValueError("salinity_source must be an entity id")
            self.salinity_source = value
            return
        if key not in SETTING_BOUNDS:
            raise ValueError(f"unknown setting {key!r}")
        try:
            number = float(value)
        except (TypeError, ValueError) as err:
            raise ValueError(f"{key} must be a number") from err
        low, high = SETTING_BOUNDS[key]
        if not math.isfinite(number) or not low <= number <= high:
            raise ValueError(f"{key} must be within [{low}, {high}]")
        setattr(self, key, number)

    def _use_parameter(self, parameter: str) -> None:
        param = PARAMETERS[parameter]
        self.parameter = parameter
        self.target = param.target
        self.tolerance = param.tolerance


# =============================================================================
# Pure helpers: salinity units
# =============================================================================


def pss78(conductivity_ms_cm: float, temperature_c: float = 25.0) -> float:
    """Practical salinity (PSS-78) of a conductivity at a temperature.

    Reef probes report a conductivity compensated to 25 °C, hence the
    default. Pressure is neglected (surface water).
    """
    a = (0.0080, -0.1692, 25.3851, 14.0941, -7.0261, 2.7081)
    b = (0.0005, -0.0056, -0.0066, -0.0375, 0.0636, -0.0144)
    c = (0.6766097, 2.00564e-2, 1.104259e-4, -6.9698e-7, 1.0031e-9)
    t = temperature_c
    ratio = conductivity_ms_cm / 42.914
    rt = sum(ci * t**i for i, ci in enumerate(c))
    root = math.sqrt(max(ratio / rt, 0.0))
    salinity = sum(ai * root**i for i, ai in enumerate(a))
    delta = (
        (t - 15) / (1 + 0.0162 * (t - 15)) * sum(bi * root**i for i, bi in enumerate(b))
    )
    return salinity + delta


def sg_to_ppt(specific_gravity: float) -> float:
    """Salinity of a specific gravity at 25 °C (1.0264 -> 35 ppt).

    Linear in the reef range, which is all that is needed here.
    """
    return (specific_gravity - 1.0) * 1000.0 * 35.0 / 26.4


def to_ppt(value: Any, unit: str | None) -> float | None:
    """Salinity in ppt of a sensor value in its unit, None if unknown."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    u = (unit or "").strip().lower()
    if u in _PPT_UNITS:
        return number
    if u == "ms/cm":
        return pss78(number)
    if u in ("µs/cm", "us/cm"):
        return pss78(number / 1000.0)
    if u in ("sg", "") and 1.0 < number < 1.1:
        return sg_to_ppt(number)
    return None


def salinity_unit_supported(unit: str | None) -> bool:
    """Whether a sensor with this unit can drive the brine regulation."""
    u = (unit or "").strip().lower()
    return u in _PPT_UNITS or u in ("ms/cm", "µs/cm", "us/cm", "sg")


# =============================================================================
# Pure helpers: dosed volumes
# =============================================================================


def dosed_between(
    start: datetime,
    end: datetime,
    daily: dict[str, float],
    fallback_ml: float,
    now: datetime,
) -> float:
    """Volume (mL) dosed between two instants.

    ``daily`` maps ISO dates to the volume dosed that day; a day missing
    from it counts ``fallback_ml`` (the daily dose then set). Each day is
    taken in proportion of the part of it inside the interval. The doser's
    volume of the current day is partial: it is spread over the elapsed
    part of the day only.
    """
    if end <= start:
        return 0.0
    tz = start.tzinfo
    total = 0.0
    day = start.date()
    while day <= end.date():
        day_start = datetime.combine(day, datetime.min.time(), tz)
        day_end = day_start + timedelta(days=1)
        span = day_end - day_start
        logged = daily.get(day.isoformat())
        if logged is not None and day == now.date():
            span = max(now - day_start, timedelta(seconds=1))
        overlap = min(end, day_end) - max(start, day_start)
        if overlap.total_seconds() > 0:
            volume = fallback_ml if logged is None else logged
            total += volume * min(overlap / span, 1.0)
        day += timedelta(days=1)
    return total


def cloud_volume_l(aquarium: dict[str, Any]) -> float | None:
    """Net water volume (L) of a ReefBeat cloud aquarium, else its gross
    volume; converted when the account counts in gallons."""
    for key in ("net_water_volume", "water_volume"):
        value = aquarium.get(key)
        if isinstance(value, (int, float)) and value > 0:
            unit = str(aquarium.get("measuring_unit") or "").lower()
            liters = value * LITERS_PER_GALLON if "gallon" in unit else value
            return round(float(liters), 1)
    return None


def effect_per_ml(potency: float, volume_l: float) -> float:
    """Rise of the parameter in the tank for one mL dosed."""
    return potency * 100.0 / volume_l


# =============================================================================
# Pure helpers: assisted mode
# =============================================================================


@dataclass(slots=True)
class Measurement:
    """A test result. ``suspect``: kept aside until confirmed."""

    at: datetime
    parameter: str
    value: float
    source: str = "manual"
    suspect: bool = False
    # Brine checks: the probe's salinity at the time of the check
    probe_value: float | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "at": self.at.isoformat(),
            "parameter": self.parameter,
            "value": self.value,
            "source": self.source,
        }
        if self.suspect:
            out["suspect"] = True
        if self.probe_value is not None:
            out["probe_value"] = self.probe_value
        return out

    @classmethod
    def from_dict(cls, raw: Any) -> Measurement | None:
        data = _as_dict(raw)
        if data is None:
            return None
        at = parse_dt(data.get("at"))
        parameter = data.get("parameter")
        try:
            value = float(data.get("value"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if at is None or not isinstance(parameter, str) or parameter not in PARAMETERS:
            return None
        probe = data.get("probe_value")
        return cls(
            at=at,
            parameter=parameter,
            value=value,
            source=str(data.get("source") or "manual"),
            suspect=bool(data.get("suspect", False)),
            probe_value=float(probe) if isinstance(probe, (int, float)) else None,
        )


def estimate_consumption(
    measurements: list[Measurement],
    dosed: Callable[[datetime, datetime], float],
    effect: float,
) -> float | None:
    """Consumption of the tank (unit/day) from consecutive measurements.

    Between two measurements: consumption = (rise due to the doses - rise
    measured) / days. The last ``CONSUMPTION_INTERVALS`` intervals are
    averaged, each weighted by its length and by how recent it is.
    Returns None without a usable interval.
    """
    usable = sorted((m for m in measurements if not m.suspect), key=lambda m: m.at)
    pairs = list(pairwise(usable))[-CONSUMPTION_INTERVALS:]
    weighted = 0.0
    weights = 0.0
    for rank, (first, second) in enumerate(reversed(pairs)):
        days = (second.at - first.at).total_seconds() / 86400.0
        if days < MIN_INTERVAL_DAYS:
            continue
        raised = dosed(first.at, second.at) * effect
        consumption = (raised - (second.value - first.value)) / days
        weight = days * RECENCY_DECAY**rank
        weighted += consumption * weight
        weights += weight
    if weights == 0:
        return None
    return weighted / weights


def is_suspect(
    previous: Measurement,
    value: float,
    at: datetime,
    consumption: float | None,
    dosed_ml: float,
    effect: float,
    tolerance: float,
) -> bool:
    """Whether a new result is far from what the history predicts."""
    if consumption is None or tolerance <= 0:
        return False
    days = (at - previous.at).total_seconds() / 86400.0
    predicted = previous.value + dosed_ml * effect - consumption * days
    return abs(value - predicted) > SUSPECT_FACTOR * tolerance


@dataclass(slots=True)
class Proposal:
    """A daily dose proposed in assisted mode, all volumes in mL/day."""

    dose: float
    current: float
    maintenance: float
    correction: float
    consumption: float | None
    measured: float
    target: float
    at: datetime
    # The proposal hit the max change per proposal
    limited: bool = False

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["at"] = self.at.isoformat()
        return out

    @classmethod
    def from_dict(cls, raw: Any) -> Proposal | None:
        data = _as_dict(raw)
        if data is None:
            return None
        at = parse_dt(data.get("at"))
        if at is None:
            return None
        try:
            return cls(
                dose=float(data["dose"]),
                current=float(data["current"]),
                maintenance=float(data["maintenance"]),
                correction=float(data["correction"]),
                consumption=(
                    float(data["consumption"])
                    if data.get("consumption") is not None
                    else None
                ),
                measured=float(data["measured"]),
                target=float(data["target"]),
                at=at,
                limited=bool(data.get("limited", False)),
            )
        except (KeyError, TypeError, ValueError):
            return None


def compute_proposal(
    settings: HeadSettings,
    measured: float,
    current_dose: float,
    consumption: float | None,
    effect: float,
    at: datetime,
) -> Proposal:
    """New daily dose: what the tank consumes, plus a correction.

    - maintenance: the dose matching the consumption; without an estimate
      yet, the current dose is assumed to hold the parameter;
    - correction: the gap to the target spread over ``correction_days``,
      capped to the parameter's ``max_rate`` per day, nothing inside the
      tolerance;
    - the new dose moves at most ``max_change_pct`` from the current one
      (when there is one), and stays within what the doser accepts.
    """
    param = PARAMETERS[settings.parameter]
    if consumption is None:
        maintenance = current_dose
    else:
        maintenance = max(consumption, 0.0) / effect
    error = settings.target - measured
    rate = 0.0
    if abs(error) > settings.tolerance:
        rate = error / settings.correction_days
        rate = max(-param.max_rate, min(param.max_rate, rate))
    correction = rate / effect
    dose = max(maintenance + correction, 0.0)
    limited = False
    if current_dose > 0:
        span = current_dose * settings.max_change_pct / 100.0
        bounded = max(current_dose - span, min(current_dose + span, dose))
        limited = not math.isclose(bounded, dose)
        dose = bounded
    dose = round(min(dose, MAX_DAILY_DOSE_ML), 1)
    return Proposal(
        dose=dose,
        current=current_dose,
        maintenance=round(maintenance, 2),
        correction=round(correction, 2),
        consumption=None if consumption is None else round(consumption, 4),
        measured=measured,
        target=settings.target,
        at=at,
        limited=limited,
    )


def proposal_worth_it(proposal: Proposal) -> bool:
    """Whether the proposed dose differs enough from the current one."""
    if proposal.current <= 0:
        return proposal.dose > 0
    return abs(proposal.dose - proposal.current) > PROPOSAL_DEADBAND * proposal.current


# =============================================================================
# Pure helpers: brine mode
# =============================================================================


def ppt_to_ml(ppt: float, volume_l: float, concentration_g_l: float) -> float:
    """Brine volume (mL) raising the salinity of the tank by ``ppt``."""
    grams = ppt * volume_l * SEAWATER_DENSITY
    return grams / concentration_g_l * 1000.0


def ml_to_ppt(ml: float, volume_l: float, concentration_g_l: float) -> float:
    """Salinity rise (ppt) of ``ml`` of brine in the tank."""
    grams = ml / 1000.0 * concentration_g_l
    return grams / (volume_l * SEAWATER_DENSITY)


def estimate_loss(
    day_avgs: dict[str, float],
    day_ml: dict[str, float],
    volume_l: float,
    concentration_g_l: float,
) -> float | None:
    """Salt lost by the tank (ppt/day): added by the brine minus the rise.

    Uses consecutive days having both an average salinity and a dosed
    volume; the median of the last ``LOSS_DAYS`` makes one bad day
    harmless. Never negative (brine cannot remove salt).
    """
    days = sorted(day_avgs)
    losses: list[float] = []
    for previous, current in pairwise(days):
        if date.fromisoformat(current) - date.fromisoformat(previous) != timedelta(
            days=1
        ):
            continue
        if current not in day_ml:
            continue
        added = ml_to_ppt(day_ml[current], volume_l, concentration_g_l)
        losses.append(added - (day_avgs[current] - day_avgs[previous]))
    if not losses:
        return None
    return max(statistics.median(losses[-LOSS_DAYS:]), 0.0)


@dataclass(slots=True)
class BrinePlan:
    """What the brine regulation needs for the coming day."""

    need_ppt: float  # salinity to add per day, after the caps
    raw_need_ppt: float  # before the caps
    ml_per_day: float  # brine to dose per day, all doses
    capped: bool


def brine_plan(
    settings: HeadSettings,
    average: float,
    loss: float | None,
    volume_l: float,
    prudent: bool,
) -> BrinePlan:
    """Daily need: the salt lost, plus a share of the gap to the target.

    Too salty: only the loss is compensated, reduced by the excess, so the
    salinity comes down with the losses (brine cannot remove salt).
    """
    error = settings.target - average
    base = loss or 0.0
    correction = 0.0
    if abs(error) > settings.tolerance:
        correction = error / settings.correction_days
    raw = base + correction
    cap = settings.brine_max_rise * (0.5 if prudent else 1.0)
    need = max(0.0, min(raw, cap))
    return BrinePlan(
        need_ppt=need,
        raw_need_ppt=raw,
        ml_per_day=ppt_to_ml(need, volume_l, settings.brine_concentration),
        capped=raw > cap,
    )


def slot_dose(
    ml_per_day: float, doses_per_day: float, carry: float
) -> tuple[float, float]:
    """Dose of one slot and the carry to the next.

    Doses under ``MIN_MANUAL_DOSE_ML`` are carried until they add up; a dose
    is rounded down to 0.1 mL (the doser's step), the rest carried.
    """
    if ml_per_day <= 0:
        return 0.0, 0.0
    wanted = ml_per_day / doses_per_day + carry
    if wanted < MIN_MANUAL_DOSE_ML:
        return 0.0, wanted
    dose = math.floor(wanted * 10.0) / 10.0
    return dose, wanted - dose


# =============================================================================
# Misc helpers
# =============================================================================


def parse_dt(value: Any) -> datetime | None:
    """Aware datetime of an ISO-8601 string, None if invalid."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def daily_log_volumes(
    payload: Any, heads: Iterable[int]
) -> dict[int, dict[str, float]]:
    """Per head, the volumes of the doser's ``/daily-log``, by ISO date.

    The doser dates each day with the epoch of its midnight (UTC).
    """
    out: dict[int, dict[str, float]] = {head: {} for head in heads}
    data = _as_dict(payload)
    for item in _as_list(data.get("daily") if data else None):
        day = _as_dict(item)
        stamp = day.get("date") if day else None
        if day is None or not isinstance(stamp, (int, float)):
            continue
        iso = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
        for head, volumes in out.items():
            volume = day.get(str(head))
            if isinstance(volume, (int, float)) and volume >= 0:
                volumes[iso] = float(volume)
    return out


# =============================================================================
# Persistence
# =============================================================================


@dataclass(slots=True)
class HeadState:
    """Everything stored for one head."""

    settings: HeadSettings
    # ISO date -> mL dosed that day (all doses of the head)
    daily: dict[str, float]
    measurements: list[Measurement]
    proposal: Proposal | None
    # Applied or dismissed proposals: {"at", "from", "to", "action"}
    history: list[dict[str, Any]]
    # Brine regulation
    samples: list[tuple[float, float]]  # (epoch, ppt) over AVERAGE_WINDOW
    day_sums: dict[str, tuple[float, int]]  # ISO date -> (sum ppt, count)
    carry: float
    next_slot: datetime | None
    last_check: datetime | None
    recal_since: datetime | None
    # Since when the current deviation (too low / too high / no sensor) lasts
    deviation: str | None
    deviation_since: datetime | None
    last_good_sample: datetime | None
    # Last computed state, shown by the entities
    status: str
    alarm: str | None
    details: dict[str, Any]

    @classmethod
    def empty(cls) -> HeadState:
        return cls(
            settings=HeadSettings(),
            daily={},
            measurements=[],
            proposal=None,
            history=[],
            samples=[],
            day_sums={},
            carry=0.0,
            next_slot=None,
            last_check=None,
            recal_since=None,
            deviation=None,
            deviation_since=None,
            last_good_sample=None,
            status="off",
            alarm=None,
            details={},
        )

    @classmethod
    def from_dict(cls, raw: Any) -> HeadState:
        state = cls.empty()
        data = _as_dict(raw)
        if data is None:
            return state
        state.settings = HeadSettings.from_dict(data.get("settings"))
        daily = _as_dict(data.get("daily")) or {}
        state.daily = {
            k: float(v) for k, v in daily.items() if isinstance(v, (int, float))
        }
        state.measurements = [
            m
            for m in (
                Measurement.from_dict(r) for r in _as_list(data.get("measurements"))
            )
            if m is not None
        ]
        state.proposal = Proposal.from_dict(data.get("proposal"))
        state.history = [
            h for h in (_as_dict(i) for i in _as_list(data.get("history"))) if h
        ]
        brine = _as_dict(data.get("brine")) or {}
        state.samples = [
            (float(p[0]), float(p[1]))
            for p in (_pair(i) for i in _as_list(brine.get("samples")))
            if p is not None
        ]
        state.day_sums = {
            k: (p[0], int(p[1]))
            for k, p in (
                (k, _pair(v))
                for k, v in (_as_dict(brine.get("day_sums")) or {}).items()
            )
            if p is not None
        }
        carry = brine.get("carry")
        state.carry = float(carry) if isinstance(carry, (int, float)) else 0.0
        state.next_slot = parse_dt(brine.get("next_slot"))
        state.last_check = parse_dt(brine.get("last_check"))
        state.recal_since = parse_dt(brine.get("recal_since"))
        deviation = brine.get("deviation")
        state.deviation = deviation if isinstance(deviation, str) else None
        state.deviation_since = parse_dt(brine.get("deviation_since"))
        state.last_good_sample = parse_dt(brine.get("last_good_sample"))
        return state

    def as_dict(self) -> dict[str, Any]:
        def iso(value: datetime | None) -> str | None:
            return value.isoformat() if value is not None else None

        return {
            "settings": self.settings.as_dict(),
            "daily": self.daily,
            "measurements": [m.as_dict() for m in self.measurements],
            "proposal": self.proposal.as_dict() if self.proposal else None,
            "history": self.history,
            "brine": {
                "samples": [list(s) for s in self.samples],
                "day_sums": {k: list(v) for k, v in self.day_sums.items()},
                "carry": self.carry,
                "next_slot": iso(self.next_slot),
                "last_check": iso(self.last_check),
                "recal_since": iso(self.recal_since),
                "deviation": self.deviation,
                "deviation_since": iso(self.deviation_since),
                "last_good_sample": iso(self.last_good_sample),
            },
        }

    def prune(self, now: datetime) -> None:
        """Drop what is older than the history kept."""
        oldest = (now - timedelta(days=HISTORY_DAYS)).date().isoformat()
        self.daily = {k: v for k, v in self.daily.items() if k >= oldest}
        limit = now - timedelta(days=HISTORY_DAYS)
        self.measurements = [m for m in self.measurements if m.at >= limit]
        self.history = self.history[-50:]
        kept_days = sorted(self.day_sums)[-DAY_STATS_KEPT:]
        self.day_sums = {k: self.day_sums[k] for k in kept_days}


class RegulationStore:
    """Persistent regulation state of the heads of one doser."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, heads: Iterable[int]
    ) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TPL.format(entry_id=entry_id)
        )
        self.heads: dict[int, HeadState] = {head: HeadState.empty() for head in heads}
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        raw = await self._store.async_load() or {}
        stored = _as_dict(raw.get("heads")) or {}
        for head in self.heads:
            self.heads[head] = HeadState.from_dict(stored.get(str(head)))

    def _data(self) -> dict[str, Any]:
        return {"heads": {str(h): s.as_dict() for h, s in self.heads.items()}}

    async def async_save(self) -> None:
        await self._store.async_save(self._data())
        self.notify()

    @callback
    def async_delay_save(self) -> None:
        """Save a bit later (frequent changes: samples, daily volumes)."""
        self._store.async_delay_save(self._data, 60)
        self.notify()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    def notify(self) -> None:
        for listener in list(self._listeners):
            listener()


# =============================================================================
# Home Assistant wiring
# =============================================================================


# Settings changing the proposal of the assisted mode
_PROPOSAL_SETTINGS: Final[frozenset[str]] = frozenset(
    {
        "target",
        "potency",
        "tolerance",
        "tank_volume",
        "max_change_pct",
        "correction_days",
        "parameter",
    }
)


class DoseRegulator:
    """Regulation of the heads of one ReefDose coordinator."""

    def __init__(
        self, hass: HomeAssistant, device: Any, store: RegulationStore
    ) -> None:
        self.hass = hass
        self.device = device
        self.store = store
        self._unsubs: list[CALLBACK_TYPE] = []
        self._last_day: date | None = None
        # Supplement uid of each head, as last seen on the doser
        self._supplements: dict[int, Any] = {}

    # ---- lifecycle -------------------------------------------------------

    async def async_start(self) -> None:
        """Read the dosed volumes, then sample the sensors every few minutes."""
        await self.async_sync_daily_log()
        for head in self.store.heads:
            self._supplements[head] = self._supplement_uid(head)
            self.refresh_status(head)
        self._unsubs.append(
            async_track_time_interval(self.hass, self._async_tick, SAMPLE_INTERVAL)
        )
        self._unsubs.append(self.device.async_add_listener(self._device_updated))

    def _supplement_uid(self, head: int) -> Any:
        return self.device.get_data(
            f"$.sources[?(@.name=='/head/{head}/settings')].data.supplement.uid",
            True,
        )

    @callback
    def _device_updated(self) -> None:
        """The doser was read: a head whose supplement changed (brine put
        on or taken off) offers other modes, its status follows at once
        rather than at the next change of the regulation."""
        changed = False
        for head in self.store.heads:
            uid = self._supplement_uid(head)
            if uid != self._supplements.get(head):
                self._supplements[head] = uid
                self.refresh_status(head)
                changed = True
        if changed:
            self.store.notify()

    @callback
    def async_stop(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()

    def now(self) -> datetime:
        return dt_util.now()

    # ---- device ----------------------------------------------------------

    def head_state(self, head: int) -> HeadState:
        return self.store.heads[head]

    def bundled(self) -> bool:
        return bool(
            self.device.get_data(
                "$.sources[?(@.name=='/dashboard')].data.bundled_heads", True
            )
        )

    def current_dose(self, head: int) -> float:
        """Daily dose set on the head (mL), 0 if unknown."""
        value = self.device.get_data(
            f"$.sources[?(@.name=='/head/{head}/settings')].data.schedule.dd", True
        )
        return float(value) if isinstance(value, (int, float)) else 0.0

    def is_brine_head(self, head: int) -> bool:
        """Whether the head holds the brine supplement."""
        return self._supplement_uid(head) == BRINE_SUPPLEMENT_UID

    def modes(self, head: int) -> list[str]:
        """Regulation modes offered by a head, after its supplement: the
        brine head is regulated on the salinity, the others on a test."""
        return ["off", "brine"] if self.is_brine_head(head) else ["off", "assisted"]

    def scheduled_dose(self, head: int) -> float:
        """Daily dose the head doses by itself (0 when its schedule is off)."""
        enabled = self.device.get_data(
            f"$.sources[?(@.name=='/head/{head}/settings')].data.schedule_enabled",
            True,
        )
        return self.current_dose(head) if enabled is not False else 0.0

    async def async_sync_daily_log(self) -> None:
        """Merge the doser's last 7 days of dosed volumes into the store."""
        await self.device.my_api.fetch_config(DAILY_LOG)
        payload = self.device.get_data(
            f"$.sources[?(@.name=='{DAILY_LOG}')].data", True
        )
        if not isinstance(payload, dict):
            _LOGGER.debug("%s: %s unavailable", self.device.title, DAILY_LOG)
            return
        volumes = daily_log_volumes(payload, self.store.heads)
        now = self.now()
        for head, days in volumes.items():
            state = self.store.heads[head]
            state.daily.update(days)
            state.prune(now)
        await self.store.async_save()

    async def _async_stop_schedule(self, head: int) -> None:
        """Switch the head's own schedule off: in brine mode Home Assistant
        doses the whole plan with manual doses, nothing else doses the brine.
        Leaving the brine mode does not switch it back on, that is the user's
        call."""
        path = f"$.sources[?(@.name=='/head/{head}/settings')].data.schedule_enabled"
        if self.device.get_data(path, True) is False:
            return
        self.device.set_data(path, False)
        await self.device.push_values(source="/configuration", head=head)
        await self.device.async_request_refresh()

    async def async_apply_dose(self, head: int, dose: float) -> None:
        """Set the head's daily dose on the doser."""
        self.device.set_data(
            f"$.sources[?(@.name=='/head/{head}/settings')].data.schedule.dd",
            int(dose) if float(dose).is_integer() else dose,
        )
        await self.device.push_values(source="/configuration", head=head)
        await self.device.async_request_refresh()

    # ---- tank volume -----------------------------------------------------

    def volume(self, head: int) -> tuple[float | None, str | None]:
        """Water volume (L) and where it comes from.

        The user's value wins; else the volume of the reeftank aquarium of
        the doser; else the net water volume of its ReefBeat cloud aquarium.
        """
        settings = self.store.heads[head].settings
        if settings.tank_volume > 0:
            return settings.tank_volume, "user"
        aquarium = self._cloud_aquarium()
        reeftank = self.reeftank_volume(aquarium)
        if reeftank is not None:
            return reeftank, "reeftank"
        cloud = cloud_volume_l(aquarium) if aquarium is not None else None
        if cloud is not None:
            return cloud, "cloud"
        return None, None

    def reeftank_volume(self, aquarium: dict[str, Any] | None) -> float | None:
        """Volume (L) of the reeftank aquarium holding the doser.

        Read from the ``water_volume`` sensors of the reeftank integration
        (an optional integration: nothing is imported from it). An
        aquarium holds the doser when the doser or one of its heads is
        placed on its views, or when it is linked to the doser's ReefBeat
        cloud aquarium.
        """
        devices = {
            entry.id
            for entry in (
                self._device_entry(self.device.model_id),
                *(
                    self._device_entry(f"{self.device.model_id}_head_{head}")
                    for head in self.store.heads
                ),
            )
            if entry is not None
        }
        cloud_uid = aquarium.get("uid") if aquarium else None
        for entity in er.async_get(self.hass).entities.values():
            if entity.platform != REEFTANK_DOMAIN or not str(entity.unique_id).endswith(
                f"_{REEFTANK_VOLUME_KEY}"
            ):
                continue
            state = self.hass.states.get(entity.entity_id)
            if state is None:
                continue
            try:
                value = float(state.state)
            except ValueError:
                continue
            if not math.isfinite(value) or value <= 0:
                continue
            placed = _as_list(state.attributes.get("device_ids"))
            cloud = _as_dict(state.attributes.get("cloud")) or {}
            linked = (
                cloud_uid is not None
                and cloud.get("provider") == DOMAIN
                and cloud.get("uid") == cloud_uid
            )
            if linked or devices.intersection(placed):
                return round(value, 1)
        return None

    def _cloud_aquarium(self) -> dict[str, Any] | None:
        """The ReefBeat cloud aquarium holding the doser, if any."""
        from .websocket import cloud_aquariums

        entry = self._device_entry(self.device.model_id)
        if entry is None:
            return None
        for aquarium in cloud_aquariums(self.hass):
            if entry.id in aquarium.get("device_ids", []):
                return aquarium
        return None

    def _device_entry(self, ident: str) -> dr.DeviceEntry | None:
        """Device registry entry of the doser or of one of its heads."""
        dev_reg = dr.async_get(self.hass)
        identifier = (DOMAIN, ident)
        config_entry = getattr(self.device, "_entry", None)
        lookup = getattr(dev_reg, "async_get_device_by_identifier", None)
        if lookup is None:  # pragma: no cover - Home Assistant < 2026.10
            return dev_reg.async_get_device(identifiers={identifier})
        if config_entry is None:
            return None
        return lookup(identifier, config_entry.entry_id)

    # ---- settings --------------------------------------------------------

    async def async_set(self, head: int, key: str, value: Any) -> None:
        """Change a setting of a head, then recompute its state."""
        state = self.store.heads[head]
        if key == "mode" and value not in self.modes(head):
            raise ValueError(
                "brine mode needs the brine supplement on the head"
                if value == "brine"
                else f"{value} mode is not available with the head's supplement"
            )
        bundled = self.bundled()
        if bundled:
            self._check_bundle(head, key, value)
        state.settings.set(key, value)
        if bundled and key == "mode" and value == "assisted":
            state.settings.set("parameter", BUNDLE_PARAMETER)
        if key == "mode":
            state.proposal = None
            state.carry = 0.0
            state.next_slot = None
            state.deviation = None
            state.deviation_since = None
        if key in _PROPOSAL_SETTINGS and state.settings.mode == "assisted":
            self._propose(head)
        if key == "mode" and value == "brine":
            await self._async_stop_schedule(head)
        if key == "salinity_source":
            # Another sensor: the samples of the former one mean nothing
            state.samples = []
        if key in ("mode", "salinity_source") and self._brine_runs(head):
            # First sample now rather than at the next tick
            self._sample(head, self.now())
        if key != "measurement":
            self.refresh_status(head)
        await self.store.async_save()

    @staticmethod
    def _check_bundle(head: int, key: str, value: Any) -> None:
        """Bundled heads: only head 1 (Part 1) is set, in assisted mode on
        the calcium; the doser derives the other heads from the bundle
        ratios.

        @raise ValueError: a setting a bundle does not allow
        """
        if key == "mode" and value != "off":
            if head != BUNDLE_HEAD:
                raise ValueError(f"bundled heads: only head {BUNDLE_HEAD} is regulated")
            if value != "assisted":
                raise ValueError("bundled heads: assisted mode only")
        if key == "parameter" and value != BUNDLE_PARAMETER:
            raise ValueError("bundled heads: the calcium is regulated")

    def _bundle_allows(self, head: int) -> bool:
        """Whether a head's regulation runs while the heads are bundled."""
        settings = self.store.heads[head].settings
        return (
            head == BUNDLE_HEAD
            and settings.mode == "assisted"
            and settings.parameter == BUNDLE_PARAMETER
        )

    # ---- measurements ----------------------------------------------------

    async def async_record(
        self,
        head: int,
        value: float | None = None,
        parameter: str | None = None,
        at: datetime | None = None,
    ) -> dict[str, Any]:
        """Record a test result for a head and react to it.

        - assisted mode: the consumption is estimated again and a new dose
          proposed;
        - brine mode, salinity: a refractometer check of the probe.
        """
        state = self.store.heads[head]
        settings = state.settings
        if value is None:
            value = settings.measurement
        parameter = parameter or settings.parameter
        if parameter not in PARAMETERS:
            raise ValueError(f"unknown parameter {parameter!r}")
        at = at or self.now()
        await self.async_sync_daily_log()

        if parameter == "salinity" and settings.mode == "brine":
            result = self._check_refractometer(head, float(value), at)
        else:
            result = self._record_test(head, float(value), parameter, at)
        state.prune(self.now())
        self.refresh_status(head)
        await self.store.async_save()
        if result.get("checked") and result.get("within"):
            await self._async_reset_probe_check()
        return result

    def _record_test(
        self, head: int, value: float, parameter: str, at: datetime
    ) -> dict[str, Any]:
        state = self.store.heads[head]
        settings = state.settings
        measurement = Measurement(at=at, parameter=parameter, value=value)
        result: dict[str, Any] = {"recorded": True, "suspect": False}
        same = [m for m in state.measurements if m.parameter == parameter]
        volume, _ = self.volume(head)
        regulated = settings.mode == "assisted" and parameter == settings.parameter
        previous = max(same, key=lambda m: m.at) if same else None
        # A back-dated result is not checked against a later one
        if (
            regulated
            and previous is not None
            and previous.at < at
            and volume
            and settings.potency > 0
        ):
            effect = effect_per_ml(settings.potency, volume)
            dosed = self._dosed_fn(head)
            if previous.suspect and abs(previous.value - value) <= settings.tolerance:
                # Confirmed by a second test: the jump is real
                previous.suspect = False
            else:
                consumption = estimate_consumption(same, dosed, effect)
                measurement.suspect = is_suspect(
                    previous,
                    value,
                    at,
                    consumption,
                    dosed(previous.at, at),
                    effect,
                    settings.tolerance,
                )
        result["suspect"] = measurement.suspect
        state.measurements.append(measurement)
        state.measurements.sort(key=lambda m: m.at)
        if regulated:
            self._propose(head)
        return result

    def _dosed_fn(self, head: int) -> Callable[[datetime, datetime], float]:
        state = self.store.heads[head]
        fallback = self.current_dose(head)
        now = self.now()

        def dosed(start: datetime, end: datetime) -> float:
            return dosed_between(start, end, state.daily, fallback, now)

        return dosed

    def _propose(self, head: int) -> None:
        """Propose a new daily dose from the last valid measurement."""
        state = self.store.heads[head]
        settings = state.settings
        volume, _ = self.volume(head)
        if not volume or settings.potency <= 0:
            state.proposal = None
            return
        tested = [m for m in state.measurements if m.parameter == settings.parameter]
        same = [m for m in tested if not m.suspect]
        # The last test is in doubt: wait for the retest
        if not same or tested[-1].suspect:
            state.proposal = None
            return
        effect = effect_per_ml(settings.potency, volume)
        consumption = estimate_consumption(same, self._dosed_fn(head), effect)
        proposal = compute_proposal(
            settings,
            same[-1].value,
            self.current_dose(head),
            consumption,
            effect,
            self.now(),
        )
        state.proposal = proposal if proposal_worth_it(proposal) else None
        state.details = {"last_proposal": proposal.as_dict()}

    async def async_apply(self, head: int) -> float | None:
        """Send the pending proposal to the doser."""
        state = self.store.heads[head]
        proposal = state.proposal
        if proposal is None:
            return None
        await self.async_apply_dose(head, proposal.dose)
        state.history.append(
            {
                "at": self.now().isoformat(),
                "from": proposal.current,
                "to": proposal.dose,
                "action": "applied",
            }
        )
        state.proposal = None
        self.refresh_status(head)
        await self.store.async_save()
        return proposal.dose

    async def async_dismiss(self, head: int) -> None:
        """Forget the pending proposal."""
        state = self.store.heads[head]
        if state.proposal is not None:
            state.history.append(
                {
                    "at": self.now().isoformat(),
                    "from": state.proposal.current,
                    "to": state.proposal.dose,
                    "action": "dismissed",
                }
            )
        state.proposal = None
        self.refresh_status(head)
        await self.store.async_save()

    # ---- brine: refractometer check -------------------------------------

    def _check_refractometer(
        self, head: int, value: float, at: datetime
    ) -> dict[str, Any]:
        state = self.store.heads[head]
        settings = state.settings
        probe = self.read_salinity(head)
        measurement = Measurement(
            at=at,
            parameter="salinity",
            value=value,
            source="refractometer",
            probe_value=None if probe is None else round(probe, 2),
        )
        state.measurements.append(measurement)
        state.measurements.sort(key=lambda m: m.at)
        if probe is None:
            return {"recorded": True, "checked": False}
        gap = probe - value
        within = abs(gap) <= settings.salinity_check_tolerance
        if within:
            state.last_check = at
            state.recal_since = None
        else:
            state.recal_since = at
        return {
            "recorded": True,
            "checked": True,
            "within": within,
            "probe": round(probe, 2),
            "gap": round(gap, 2),
        }

    def _probe_of_source(self, head: int) -> tuple[Any, int] | None:
        """RSCONTROL coordinator and probe sub_id behind the source sensor."""
        from .coordinator import ReefControlCoordinator
        from .maintenance import probe_sub_id

        source = self.store.heads[head].settings.salinity_source
        entry = er.async_get(self.hass).async_get(source) if source else None
        if entry is None or entry.platform != DOMAIN or not entry.unique_id:
            return None
        for coordinator in self.hass.data.get(DOMAIN, {}).values():
            if not isinstance(coordinator, ReefControlCoordinator):
                continue
            prefix = f"{coordinator.serial}_probe_ec_"
            if not entry.unique_id.startswith(prefix):
                continue
            probes = coordinator.get_data(
                "$.sources[?(@.name=='/dashboard')].data.probes", True
            )
            for item in _as_list(probes):
                probe = _as_dict(item) or {}
                uid = probe.get("uid")
                if not isinstance(uid, str) or probe.get("type") != "ec":
                    continue
                key = "".join(c for c in uid.lower() if c.isalnum())
                if entry.unique_id.startswith(f"{prefix}{key}_"):
                    try:
                        return coordinator, probe_sub_id(uid)
                    except ValueError:
                        return None
        return None

    async def _async_reset_probe_check(self) -> None:
        """Mark the refractometer check of the source probe done."""
        from .maintenance import REFRACTOMETER_TASK

        for head, state in self.store.heads.items():
            if state.settings.mode != "brine" or state.last_check is None:
                continue
            found = self._probe_of_source(head)
            store = getattr(found[0], "maintenance", None) if found else None
            if found is None or store is None:
                continue
            await store.async_record_reset(
                found[0].serial, found[1], REFRACTOMETER_TASK, state.last_check
            )

    def _probe_calibrated_since(self, head: int, since: datetime) -> bool:
        """Whether the source probe was calibrated after ``since``."""
        from .maintenance import CALIBRATION_TASKS

        found = self._probe_of_source(head)
        store = getattr(found[0], "maintenance", None) if found else None
        if found is None or store is None:
            return False
        last = store.get_last_reset(found[0].serial, found[1], CALIBRATION_TASKS["ec"])
        return last is not None and last > since

    # ---- brine: sampling and dosing -------------------------------------

    def read_salinity(self, head: int) -> float | None:
        """Current salinity (ppt) of the head's source sensor."""
        source = self.store.heads[head].settings.salinity_source
        state = self.hass.states.get(source) if source else None
        if state is None:
            return None
        ppt = to_ppt(state.state, state.attributes.get("unit_of_measurement"))
        if ppt is None or not SALINITY_RANGE[0] <= ppt <= SALINITY_RANGE[1]:
            return None
        return ppt

    def average(self, head: int) -> float | None:
        samples = self.store.heads[head].samples
        if len(samples) < MIN_SAMPLES:
            return None
        return statistics.fmean(ppt for _, ppt in samples)

    def _sample(self, head: int, now: datetime) -> None:
        state = self.store.heads[head]
        ppt = self.read_salinity(head)
        horizon = (now - AVERAGE_WINDOW).timestamp()
        state.samples = [s for s in state.samples if s[0] >= horizon]
        if ppt is None:
            return
        current = self.average(head)
        if current is not None and abs(ppt - current) > MAX_JUMP_PPT:
            _LOGGER.debug("Head %s: salinity glitch %.2f ignored", head, ppt)
            return
        state.samples.append((now.timestamp(), ppt))
        state.last_good_sample = now
        day = now.date().isoformat()
        total, count = state.day_sums.get(day, (0.0, 0))
        state.day_sums[day] = (total + ppt, count + 1)

    def loss(self, head: int) -> float | None:
        state = self.store.heads[head]
        volume, _ = self.volume(head)
        if not volume:
            return None
        today = self.now().date().isoformat()
        avgs = {
            day: total / count
            for day, (total, count) in state.day_sums.items()
            if count and day != today
        }
        return estimate_loss(
            avgs, state.daily, volume, state.settings.brine_concentration
        )

    def prudent(self, head: int) -> bool:
        last = self.store.heads[head].last_check
        return last is None or self.now() - last > timedelta(days=PRUDENT_AFTER_DAYS)

    async def _async_tick(self, _now: Any = None) -> None:
        """Every few minutes: sample, roll the day over, dose when due."""
        now = self.now()
        if self._last_day is not None and now.date() != self._last_day:
            await self.async_sync_daily_log()
        self._last_day = now.date()
        changed = False
        for head, state in self.store.heads.items():
            if state.settings.mode == "assisted":
                # The cloud volume may only be known once set up
                self.refresh_status(head)
                continue
            if not self._brine_runs(head):
                self.refresh_status(head)
                continue
            self._sample(head, now)
            changed = True
            self.refresh_status(head)
            # Unable to catch up: keep dosing at the cap all the same
            if state.status in ("regulating", "cannot_compensate") and (
                state.next_slot is None or now >= state.next_slot
            ):
                await self._async_dose_slot(head, now)
        if changed:
            self.store.async_delay_save()

    def _brine_runs(self, head: int) -> bool:
        """Whether the brine regulation of a head runs."""
        return (
            self.store.heads[head].settings.mode == "brine"
            and not self.bundled()
            and self.is_brine_head(head)
        )

    async def _async_dose_slot(self, head: int, now: datetime) -> None:
        state = self.store.heads[head]
        settings = state.settings
        plan = state.details.get("plan_ml_day", 0.0)
        # Doses of the head's own schedule are already on their way
        remaining = max(plan - self.scheduled_dose(head), 0.0)
        dose, carry = slot_dose(remaining, settings.brine_doses_per_day, state.carry)
        state.next_slot = now + timedelta(hours=24.0 / settings.brine_doses_per_day)
        if dose <= 0:
            state.carry = carry
            return
        ok = await self.device.manual_dose(head, dose)
        if ok:
            state.carry = carry
            state.details["last_dose"] = {"at": now.isoformat(), "ml": dose}
            _LOGGER.debug("Head %s: brine dose %.1f mL", head, dose)
        else:
            # Not dosed: keep it for the next slot
            state.carry = carry + dose
            _LOGGER.warning("%s head %s: brine dose refused", self.device.title, head)

    # ---- status ----------------------------------------------------------

    def refresh_status(self, head: int) -> None:
        """Compute the status, the alarm and the details of a head."""
        state = self.store.heads[head]
        previous_alarm = state.alarm
        if state.settings.mode == "off":
            status, alarm, details = "off", None, {}
        elif self.bundled() and not self._bundle_allows(head):
            status, alarm, details = "bundle", None, {}
        elif state.settings.mode not in self.modes(head):
            # The supplement changed under the regulation (brine removed,
            # or put on a head regulated on a test)
            status, alarm, details = "not_configured", None, {"missing": ["supplement"]}
        elif state.settings.mode == "assisted":
            status, alarm, details = self._assisted_status(head)
        else:
            status, alarm, details = self._brine_status(head)
        state.status = status
        state.alarm = alarm
        state.details = {
            **details,
            **{k: v for k, v in state.details.items() if k == "last_dose"},
        }
        if alarm is not None and alarm != previous_alarm:
            self.hass.bus.async_fire(
                EVENT_ALARM,
                {
                    "device": self.device.title,
                    "serial": self.device.serial,
                    "head": head,
                    "alarm": alarm,
                },
            )

    def _missing(self, head: int) -> list[str]:
        settings = self.store.heads[head].settings
        missing: list[str] = []
        if self.volume(head)[0] is None:
            missing.append("tank_volume")
        if settings.mode == "assisted" and settings.potency <= 0:
            missing.append("potency")
        if settings.mode == "brine" and not settings.salinity_source:
            missing.append("salinity_source")
        return missing

    def _assisted_status(self, head: int) -> tuple[str, str | None, dict[str, Any]]:
        state = self.store.heads[head]
        missing = self._missing(head)
        if missing:
            return "not_configured", None, {"missing": missing}
        same = [
            m for m in state.measurements if m.parameter == state.settings.parameter
        ]
        details = {k: v for k, v in state.details.items() if k == "last_proposal"}
        if not same:
            return "waiting_data", None, details
        if same[-1].suspect:
            return "retest_suggested", None, details
        if state.proposal is not None:
            return "proposal", None, details
        return "in_range", None, details

    def _brine_status(self, head: int) -> tuple[str, str | None, dict[str, Any]]:
        state = self.store.heads[head]
        settings = state.settings
        now = self.now()
        missing = self._missing(head)
        if missing:
            return "not_configured", None, {"missing": missing}
        prudent = self.prudent(head)
        details: dict[str, Any] = {"prudent": prudent}
        if state.recal_since is not None:
            if self._probe_calibrated_since(head, state.recal_since):
                state.recal_since = None
            else:
                return "recalibration_required", "recalibration_required", details
        alive = (
            state.last_good_sample is not None
            and now - state.last_good_sample <= SOURCE_TIMEOUT
        )
        # Lost after working, or never readable
        if not alive and (state.samples or self.read_salinity(head) is None):
            since = self._deviation(state, "source_unavailable", now)
            alarm = "source_unavailable" if now - since >= SOURCE_ALARM_AFTER else None
            return "source_unavailable", alarm, details
        average = self.average(head)
        if average is None:
            details.update(
                {"samples": len(state.samples), "samples_needed": MIN_SAMPLES}
            )
            return "waiting_data", None, details
        volume, _ = self.volume(head)
        assert volume is not None  # checked by _missing
        loss = self.loss(head)
        plan = brine_plan(settings, average, loss, volume, prudent)
        details.update(
            {
                "average": round(average, 2),
                "loss_ppt_day": None if loss is None else round(loss, 3),
                "need_ppt_day": round(plan.need_ppt, 3),
                "plan_ml_day": round(plan.ml_per_day, 1),
                "capped": plan.capped,
            }
        )
        error = settings.target - average
        if error < -settings.tolerance:
            since = self._deviation(state, "too_salty", now)
            alarm = "too_salty" if now - since >= TOO_SALTY_ALARM_AFTER else None
            return "too_salty", alarm, details
        if error > settings.tolerance:
            since = self._deviation(state, "too_low", now)
            if now - since >= CANNOT_COMPENSATE_AFTER:
                return "cannot_compensate", "cannot_compensate", details
            return "regulating", None, details
        state.deviation = None
        state.deviation_since = None
        return "regulating", None, details

    @staticmethod
    def _deviation(state: HeadState, kind: str, now: datetime) -> datetime:
        """Since when the deviation ``kind`` lasts (starts it if new)."""
        if state.deviation != kind or state.deviation_since is None:
            state.deviation = kind
            state.deviation_since = now
        return state.deviation_since
