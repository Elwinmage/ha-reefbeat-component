"""ReefWave day program following the weather of a place (GPS mode).

As for the ReefLEDs, the user picks a place (GPS coordinates or a map link,
the Home Assistant home by default). Every day, the speed of the place's
water comes from Open-Meteo (no API key):

- "wind": the hourly wind speed at 10 m (forecast API), everywhere;
- "current": the hourly ocean current velocity (marine API), where the sea
  model covers the place (the wind is used when it does not).

That speed becomes the speed of the pump, hour by hour, between four bounds
set by the user: the slowest and the fastest speed by day (from the place's
sunrise to its sunset) and by night. A speed of the place at or over the
scale (km/h, set by the user) gives the fastest speed of the period, a still
water the slowest.

Each pump of a group can run a little slower or faster than the others: its
offset (percent of the speed, e.g. -10 for the second pump).

The program of the pump keeps its waves (type, shape, direction): only the
intensities follow the weather. The pump's own program (its "base") is kept
aside when the mode is turned on, cut into hours, and each hour gets the
forward intensity of the weather, the reverse one keeping its share of the
forward one. Turned off, the base is written back.

The weather program is written to the pump itself (local /auto handshake):
the cloud keeps the base program. It is made again every night, at once
when a setting changes, and when the base program is edited (the program
editor saves the base, the weather then follows it).

Everything that depends on the weather is pure (and tested) here.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .led_weather import OPEN_METEO_URL, _open_meteo, hhmm, parse_location

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

SOURCE_WIND = "wind"
SOURCE_CURRENT = "current"
SOURCES = [SOURCE_WIND, SOURCE_CURRENT]

# Speed of the place giving the fastest speed of the pump, km/h, by source
DEFAULT_SCALE = {SOURCE_WIND: 40.0, SOURCE_CURRENT: 2.0}
SCALE_MAX = 200.0

# Offset of a pump, percent of the speed
OFFSET_MIN = -50
OFFSET_MAX = 50

# Following hours of the same wave whose speeds stay within this spread
# (percent points) make one interval, at their mean speed
DEFAULT_TOLERANCE = 5
TOLERANCE_MAX = 30

MINUTES_PER_DAY = 24 * 60

# Settings shared by the pumps of a group (the offset is each pump's own)
SHARED_KEYS = (
    "location",
    "source",
    "scale",
    "day_min",
    "day_max",
    "night_min",
    "night_max",
    "tolerance",
)

STORAGE_VERSION = 1
STORAGE_KEY_TPL = "redsea.wave_weather.{entry_id}"


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------


@dataclass
class WaveWeatherSettings:
    """What the user chose for a pump."""

    enabled: bool = False
    # "lat, lon", a map link, or empty for the Home Assistant home
    location: str = ""
    source: str = SOURCE_WIND
    # Speed of the place giving the fastest speed (km/h); 0: the default
    scale: float = 0.0
    day_min: int = 30
    day_max: int = 80
    night_min: int = 10
    night_max: int = 40
    # Spread of speeds merged into one interval (percent points)
    tolerance: int = DEFAULT_TOLERANCE
    # This pump's speed against the weather, percent (-10: 10 % slower)
    offset: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> WaveWeatherSettings:
        """Settings from their stored form, invalid values left at default."""
        out = cls()
        if not isinstance(data, dict):
            return out
        for key, value in data.items():
            try:
                out.set(key, value)
            except (TypeError, ValueError):
                _LOGGER.warning("Ignored wave weather setting %s=%r", key, value)
        return out

    def set(self, key: str, value: Any) -> None:
        """Change one setting, checked.

        @raise ValueError: unknown key or invalid value
        """
        if key == "enabled":
            self.enabled = bool(value)
        elif key == "location":
            self.location = str(value or "").strip()
        elif key == "source":
            if value not in SOURCES:
                raise ValueError(f"source must be one of {SOURCES}")
            self.source = value
        elif key == "scale":
            self.scale = max(0.0, min(SCALE_MAX, round(float(value), 1)))
        elif key in ("day_min", "day_max", "night_min", "night_max"):
            setattr(self, key, max(0, min(100, round(float(value)))))
        elif key == "tolerance":
            self.tolerance = max(0, min(TOLERANCE_MAX, round(float(value))))
        elif key == "offset":
            self.offset = max(OFFSET_MIN, min(OFFSET_MAX, round(float(value))))
        else:
            raise ValueError(f"unknown setting {key}")

    def scale_of(self) -> float:
        """Speed of the place giving the fastest speed (km/h)."""
        return self.scale if self.scale > 0 else DEFAULT_SCALE[self.source]

    def as_dict(self) -> dict[str, Any]:
        """Stored form."""
        return asdict(self)


class WaveWeatherStore:
    """Persistent weather settings of one pump, its own program kept aside
    while in weather mode, and the last generation."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TPL.format(entry_id=entry_id)
        )
        self.settings = WaveWeatherSettings()
        # Summary of the last generation (see apply_wave_weather)
        self.result: dict[str, Any] = {}
        # The pump's own program (its intervals), kept aside in weather mode
        self.base: list[dict[str, Any]] = []
        # Day of the last weather program written, ISO
        self.last_success: str | None = None
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        """Read the stored settings, base program and result."""
        raw = await self._store.async_load() or {}
        self.settings = WaveWeatherSettings.from_dict(raw.get("settings"))
        result = raw.get("result")
        self.result = result if isinstance(result, dict) else {}
        base = raw.get("base")
        self.base = (
            [dict(i) for i in base if isinstance(i, dict)]
            if isinstance(base, list)
            else []
        )
        last = raw.get("last_success")
        self.last_success = last if isinstance(last, str) else None

    async def async_save(self) -> None:
        """Save everything, and tell the listeners (entities)."""
        await self._store.async_save(
            {
                "settings": self.settings.as_dict(),
                "result": self.result,
                "base": self.base,
                "last_success": self.last_success,
            }
        )
        for listener in list(self._listeners):
            listener()

    def due(self, today: date) -> bool:
        """Whether today's weather program is still to be written."""
        return self.settings.enabled and self.last_success != today.isoformat()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Be told of every change; returns the function removing it."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove


# -----------------------------------------------------------------------------
# Weather
# -----------------------------------------------------------------------------


@dataclass
class PlaceDay:
    """Today's water speed at the place, hour by hour, on its own clock."""

    sunrise: int
    sunset: int
    # km/h, hour 0..23 (None: no value)
    wind: list[float | None]
    current: list[float | None]
    timezone: str = ""


def forecast_params(lat: float, lon: float) -> dict[str, str]:
    """Query of the Open-Meteo forecast API: today's wind, sunrise, sunset."""
    return {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "hourly": "wind_speed_10m",
        "daily": "sunrise,sunset",
        "timezone": "auto",
        "forecast_days": "1",
    }


def marine_params(lat: float, lon: float) -> dict[str, str]:
    """Query of the Open-Meteo marine API: today's ocean current."""
    return {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "hourly": "ocean_current_velocity",
        "timezone": "auto",
        "forecast_days": "1",
    }


def _minute_of(iso: Any) -> int | None:
    """Minutes of the day of an ISO local time ("2026-09-22T06:03")."""
    if not isinstance(iso, str) or "T" not in iso:
        return None
    clock = iso.split("T", 1)[1]
    try:
        return int(clock[:2]) * 60 + int(clock[3:5])
    except ValueError:
        return None


def hourly_values(payload: Any, key: str) -> list[float | None]:
    """24 hourly values of an Open-Meteo answer (None where missing)."""
    out: list[float | None] = [None] * 24
    if not isinstance(payload, dict):
        return out
    hourly = payload.get("hourly") or {}
    values = hourly.get(key) or []
    for n, stamp in enumerate(hourly.get("time") or []):
        minute = _minute_of(stamp)
        if minute is None or n >= len(values):
            continue
        value = values[n]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[minute // 60] = float(value)
    return out


def parse_place_day(forecast: Any, marine: Any = None) -> PlaceDay | None:
    """Today at the place, None without a sunrise / sunset."""
    if not isinstance(forecast, dict):
        return None
    daily = forecast.get("daily") or {}
    rise = _minute_of((daily.get("sunrise") or [None])[0])
    set_ = _minute_of((daily.get("sunset") or [None])[0])
    if rise is None or set_ is None or set_ <= rise:
        return None
    return PlaceDay(
        sunrise=rise,
        sunset=set_,
        wind=hourly_values(forecast, "wind_speed_10m"),
        current=hourly_values(marine, "ocean_current_velocity"),
        timezone=str(forecast.get("timezone") or ""),
    )


def is_day(day: PlaceDay, hour: int) -> bool:
    """Whether the middle of an hour is between the sunrise and the sunset."""
    middle = hour * 60 + 30
    return day.sunrise <= middle < day.sunset


def _fill(values: list[float | None]) -> list[float]:
    """Hourly values with the gaps filled by the nearest value before (or
    after, at the start of the day); zeros when there is none at all."""
    known = [v for v in values if v is not None]
    if not known:
        return [0.0] * len(values)
    out: list[float] = []
    last = known[0]
    for value in values:
        if value is not None:
            last = value
        out.append(last)
    return out


def place_speeds(
    day: PlaceDay, settings: WaveWeatherSettings
) -> tuple[list[float], bool]:
    """The place's speeds used, and whether the wind stood in for a
    current the sea model does not give there."""
    if settings.source == SOURCE_CURRENT:
        if any(v is not None for v in day.current):
            return _fill(day.current), False
        return _fill(day.wind), True
    return _fill(day.wind), False


def round_speed(value: float) -> int:
    """A speed rounded, kept between 0 and 100."""
    return max(0, min(100, round(value)))


def speed_of(
    value: float, day_time: bool, settings: WaveWeatherSettings, scale: float
) -> float:
    """Speed of the pump (before its offset) for a speed of the place."""
    low, high = (
        (settings.day_min, settings.day_max)
        if day_time
        else (settings.night_min, settings.night_max)
    )
    share = max(0.0, min(1.0, value / scale)) if scale > 0 else 0.0
    return low + (high - low) * share


def with_offset(speed: float, offset: int) -> int:
    """A pump's own speed: the weather's one with its offset, rounded."""
    return round_speed(speed * (1 + offset / 100))


def hourly_speeds(
    day: PlaceDay, settings: WaveWeatherSettings, offset: int | None = None
) -> list[int]:
    """Speed of a pump for each hour of the day.

    @param offset: the pump's offset (its settings' by default)
    """
    values, _fallback = place_speeds(day, settings)
    scale = settings.scale_of()
    own = settings.offset if offset is None else offset
    return [
        with_offset(speed_of(values[h], is_day(day, h), settings, scale), own)
        for h in range(24)
    ]


# -----------------------------------------------------------------------------
# Program
# -----------------------------------------------------------------------------


def _active(base: list[dict[str, Any]], minute: int) -> dict[str, Any]:
    """Interval of a program running at a minute of the day."""
    current = base[0]
    for interval in base[1:]:
        if int(interval.get("st", 0)) <= minute:
            current = interval
        else:
            break
    return current


def _num(value: Any, default: float) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return default


def weather_program(
    base: list[dict[str, Any]],
    speeds: list[int],
    tolerance: int = DEFAULT_TOLERANCE,
) -> list[dict[str, Any]]:
    """The pump's program with the intensities of the weather.

    Each hour (and each interval of the base) is a piece running the wave of
    the base at that time at the hour's speed. Following pieces of the same
    wave whose speeds stay within the tolerance make one interval, at their
    mean speed (weighted by their length): a calm night is one interval,
    not eight. Its forward intensity is that speed, its reverse one keeps
    its share of the forward one. "No wave" stays as it is.
    @param base: the pump's own program (intervals)
    @param speeds: the speed of each hour
    @param tolerance: spread of speeds merged (percent points)
    """
    if not base:
        return []
    base = sorted((dict(i) for i in base), key=lambda i: int(_num(i.get("st"), 0)))
    starts = sorted(
        st
        for st in {int(_num(i.get("st"), 0)) for i in base}
        | {h * 60 for h in range(24)}
        if st < MINUTES_PER_DAY
    )
    # Runs of pieces: [start, wave, [(speed, length), ...]]
    runs: list[tuple[int, dict[str, Any], list[tuple[int, int]]]] = []
    for n, st in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else MINUTES_PER_DAY
        wave = {k: v for k, v in _active(base, st).items() if k not in ("st", "start")}
        piece = (speeds[st // 60], end - st)
        if runs and runs[-1][1] == wave:
            pieces = runs[-1][2]
            spread = [p[0] for p in pieces] + [piece[0]]
            if wave.get("type") == "nw" or max(spread) - min(spread) <= tolerance:
                pieces.append(piece)
                continue
        runs.append((st, wave, [piece]))
    out: list[dict[str, Any]] = []
    for st, wave, pieces in runs:
        interval = {**wave, "st": st}
        if wave.get("type") != "nw":
            length = sum(p[1] for p in pieces)
            speed = round_speed(sum(p[0] * p[1] for p in pieces) / length)
            fti = _num(wave.get("fti"), 0)
            rti = _num(wave.get("rti"), 0)
            interval["fti"] = speed
            interval["rti"] = (
                max(0, min(100, round(rti * speed / fti))) if fti > 0 else speed
            )
        out.append(interval)
    return out


# -----------------------------------------------------------------------------
# Running
# -----------------------------------------------------------------------------


class WaveWeatherError(Exception):
    """The weather could not be had (the message is shown as is)."""


async def fetch_place_day(
    fetch: Callable[[str, dict[str, str]], Any],
    lat: float,
    lon: float,
    source: str,
) -> PlaceDay:
    """Today's weather at a place.

    @raise WaveWeatherError: no answer the program can be made from
    """
    forecast = await fetch(OPEN_METEO_URL, forecast_params(lat, lon))
    marine = None
    if source == SOURCE_CURRENT:
        try:
            marine = await fetch(MARINE_URL, marine_params(lat, lon))
        except Exception as err:
            _LOGGER.debug("No ocean current at %s, %s: %s", lat, lon, err)
    day = parse_place_day(forecast, marine)
    if day is None:
        raise WaveWeatherError("No sunrise / sunset for this place today")
    return day


def place_of(hass: HomeAssistant, settings: WaveWeatherSettings) -> tuple[float, float]:
    """Coordinates of the settings' place.

    @raise WaveWeatherError: a place that is not understood
    """
    home = (float(hass.config.latitude), float(hass.config.longitude))
    place = parse_location(settings.location, home)
    if place is None:
        raise WaveWeatherError(f"Place not understood: {settings.location}")
    return place


def summary(
    day: PlaceDay,
    settings: WaveWeatherSettings,
    place: tuple[float, float],
    now_iso: str,
) -> dict[str, Any]:
    """What a generation is shown with: the place, its day, each hour."""
    values, fallback = place_speeds(day, settings)
    scale = settings.scale_of()
    return {
        "status": "ok",
        "updated": now_iso,
        "latitude": place[0],
        "longitude": place[1],
        "timezone": day.timezone,
        "source": settings.source,
        "fallback": fallback,
        "scale": scale,
        "sunrise": hhmm(day.sunrise),
        "sunset": hhmm(day.sunset),
        "hours": [
            {
                "hour": h,
                "value": round(values[h], 2),
                "day": is_day(day, h),
                "speed": round(speed_of(values[h], is_day(day, h), settings, scale)),
            }
            for h in range(24)
        ],
    }


def _error(err: Exception) -> dict[str, Any]:
    if not isinstance(err, WaveWeatherError):
        _LOGGER.exception("ReefWave weather program failed")
    return {"status": "error", "error": str(err) or type(err).__name__}


def store_of(pump: Any) -> WaveWeatherStore | None:
    """Weather store of a pump, None for anything else."""
    store = getattr(pump, "wave_weather", None)
    return store if isinstance(store, WaveWeatherStore) else None


async def apply_wave_weather(
    hass: HomeAssistant,
    pump: Any,
    fetch: Callable[[str, dict[str, str]], Any] | None = None,
) -> dict[str, Any]:
    """Make today's weather program of a pump in weather mode and write it.

    @return the summary kept by the store (also on error)
    """
    store = store_of(pump)
    if store is None or not store.settings.enabled:
        return {"status": "error", "error": "Weather mode is off"}
    now = dt_util.now()
    settings = store.settings
    try:
        place = place_of(hass, settings)
        day = await fetch_place_day(
            fetch or _open_meteo(hass), place[0], place[1], settings.source
        )
        result = summary(day, settings, place, now.isoformat())
        speeds = hourly_speeds(day, settings)
        result["speeds"] = speeds
        result["offset"] = settings.offset
        program = weather_program(store.base, speeds, settings.tolerance)
        if not program:
            raise WaveWeatherError("The pump has no program to follow the weather")
        result["intervals"] = len(program)
        await pump._write_local([dict(i) for i in program])
        store.last_success = now.date().isoformat()
    except Exception as err:  # weather, network, pump
        result = _error(err)
    store.result = result
    await store.async_save()
    return result


async def preview_wave_weather(
    hass: HomeAssistant,
    pump: Any,
    settings: dict[str, Any] | None = None,
    offsets: dict[str, Any] | None = None,
    fetch: Callable[[str, dict[str, str]], Any] | None = None,
) -> dict[str, Any]:
    """Today's speeds the weather would give, for the card's editor: nothing
    is written nor kept.

    @param settings: settings being edited, over the stored ones
    @param offsets: offsets being edited, by hwid, over the pumps' own
    @return the summary of the day, plus "pumps": [{hwid, name, offset,
            speeds}] for each pump of the group, and "settings"
    """
    store = store_of(pump)
    if store is None:
        return {"status": "error", "error": "Not a ReefWave"}
    used = WaveWeatherSettings.from_dict(store.settings.as_dict())
    result: dict[str, Any]
    try:
        for key, value in (settings or {}).items():
            if key != "enabled":
                used.set(key, value)
        place = place_of(hass, used)
        day = await fetch_place_day(
            fetch or _open_meteo(hass), place[0], place[1], used.source
        )
        result = summary(day, used, place, dt_util.now().isoformat())
        result["pumps"] = [
            {
                "hwid": m["hwid"],
                "name": m["name"],
                "offset": (offset := offset_of(m, offsets)),
                "speeds": hourly_speeds(day, used, offset),
            }
            for m in pump.wave_group()
        ]
    except ValueError as err:  # a setting typed wrong
        result = {"status": "error", "error": str(err)}
    except Exception as err:  # weather, network
        result = _error(err)
    result["settings"] = used.as_dict()
    return result


def offset_of(member: dict[str, Any], offsets: dict[str, Any] | None) -> int:
    """Offset of a pump of the group: the one edited, else its own."""
    edited = (offsets or {}).get(member["hwid"])
    if edited is not None:
        holder = WaveWeatherSettings()
        holder.set("offset", edited)
        return holder.offset
    store = store_of(member.get("coordinator"))
    return store.settings.offset if store is not None else 0


async def set_wave_weather_mode(
    hass: HomeAssistant, pump: Any, enabled: bool
) -> dict[str, Any]:
    """Switch a pump between its own program and the weather.

    On: its program is kept aside (the base), then the weather program is
    written. Off: the base is written back.
    """
    store = store_of(pump)
    if store is None:
        return {"status": "error", "error": "Not a ReefWave"}
    if enabled:
        if not store.settings.enabled:
            store.base = [dict(i) for i in pump.program_intervals()]
            store.settings.enabled = True
        return await apply_wave_weather(hass, pump)
    if store.settings.enabled:
        base = [dict(i) for i in store.base]
        store.settings.enabled = False
        store.base = []
        store.result = {}
        store.last_success = None
        await store.async_save()
        if base:
            await pump._write_local(base)
    return {"status": "ok", "enabled": False}


async def save_wave_weather(
    hass: HomeAssistant,
    pump: Any,
    settings: dict[str, Any] | None,
    offsets: dict[str, Any] | None,
    enabled: bool,
) -> dict[str, Any]:
    """Save the card's editor for the pump's whole group: the shared
    settings and the mode go to every pump, each its own offset; each pump
    is then written (weather program, or its own back).

    @return the summary of this pump (or an error)
    """
    if store_of(pump) is None:
        return {"status": "error", "error": "Not a ReefWave"}
    shared = {k: v for k, v in (settings or {}).items() if k in SHARED_KEYS}
    try:
        checked = WaveWeatherSettings.from_dict(None)
        for key, value in shared.items():
            checked.set(key, value)
        for value in (offsets or {}).values():
            checked.set("offset", value)
    except (TypeError, ValueError) as err:
        return {"status": "error", "error": str(err)}
    # The group always holds the pump itself (see wave_group)
    members = [m for m in pump.wave_group() if store_of(m.get("coordinator"))]
    mine: dict[str, Any] = {}
    for member in members:
        target = member["coordinator"]
        store = store_of(target)
        assert store is not None
        for key, value in shared.items():
            store.settings.set(key, value)
        edited = (offsets or {}).get(member["hwid"])
        if edited is not None:
            store.settings.set("offset", edited)
        await store.async_save()
        if enabled and store.settings.enabled:
            result = await apply_wave_weather(hass, target)
        else:
            result = await set_wave_weather_mode(hass, target, enabled)
        if target is pump:
            mine = result
    return mine


async def base_changed(
    hass: HomeAssistant, pump: Any, intervals: list[dict[str, Any]]
) -> bool:
    """The pump's own program was edited: in weather mode it becomes the
    base and the weather program is made from it.

    @return whether the pump is in weather mode (its program then rewritten)
    """
    store = store_of(pump)
    if store is None or not store.settings.enabled:
        return False
    store.base = [dict(i) for i in intervals]
    await store.async_save()
    await apply_wave_weather(hass, pump)
    return True
