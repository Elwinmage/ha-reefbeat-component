"""ReefLED week program following the weather of a place.

The user picks a place (GPS coordinates or a map link, the Home Assistant
home by default) and a period: the week that has just passed (measured
weather) or the week to come (forecast). The weather of each day comes from
Open-Meteo (no API key) and becomes the program of the lamp for the same
weekday:

- the day lasts from the place's sunrise to its sunset, at the place's own
  clock, or anchored on the tank's clock (sunrise, sunset, or both: the
  place's day is then stretched to fit);
- the intensity follows the sun actually received (hourly shortwave
  radiation), between the user's minimum and maximum;
- the colour is the one of the lamp's current program, taken at the same
  moment of the day (its white/blue balance on a G1, its colour temperature
  on a G2), so only the light's timing and strength change;
- the lamp's clouds are set on the cloudy hours of the day;
- the moon keeps its place after the sunset.

The weather mode is a switch: turned on, the lamp's own ("standard")
programs are kept aside and the weather week is sent at once, then fetched
again every few days (3 to 15, set by the user) and whenever a setting
changes; turned off, the standard programs are written back. There is no
step to validate.

Everything that depends on the weather is pure (and tested) here.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import re
import time
from collections.abc import Callable, Coroutine
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

PERIOD_LAST_WEEK = "last_week"
PERIOD_NEXT_WEEK = "next_week"
PERIODS = [PERIOD_NEXT_WEEK, PERIOD_LAST_WEEK]

# How the place's day is set on the tank's clock
ANCHOR_PLACE = "place"
ANCHOR_SUNRISE = "sunrise"
ANCHOR_SUNSET = "sunset"
ANCHOR_BOTH = "both"
ANCHORS = [ANCHOR_PLACE, ANCHOR_SUNRISE, ANCHOR_SUNSET, ANCHOR_BOTH]

# Shortwave radiation of a full sun, W/m²: the maximum intensity
FULL_SUN_WM2 = 1000.0
# Most points of a generated channel (the Red Sea programs use up to 7)
MAX_POINTS = 8
# Cloud cover from which an hour counts as cloudy, %
CLOUDY_COVER = 40.0
# Shortest day kept, minutes
MIN_DAY = 60
# Default colour temperature of a G2 without a program
DEFAULT_KELVIN = 15000

# Name of the generated program on the lamp
PROGRAM_NAME = "Weather"

# Days between two weather fetches (the user's choice, within these bounds)
REFRESH_DAYS_MIN = 3
REFRESH_DAYS_MAX = 15
REFRESH_DAYS_DEFAULT = 7
# Seconds after the last changed setting before the week is sent again (the
# settings are often changed one after the other)
WEATHER_SETTLE_SECONDS = 30
# A changed setting shows its week at once (after this pause, for the
# settings changed in a row), the lamp is written once they settle
WEATHER_SHOW_SECONDS = 1

# Cloud intensities of the lamp (ReefBeat app: CloudsIntensity), with their
# cloud and clear durations, and the mean cover they stand for
CLOUD_LEVELS: list[tuple[float, str, int, int]] = [
    (60.0, "Low", 3, 7),
    (80.0, "Medium", 4, 6),
    (101.0, "High", 6, 4),
]

# Seconds between two requests written to a lamp: a ReefLED takes time to
# handle a command, and answers late (or not at all) to one sent too soon
WRITE_DELAY_S = 2.0

# Colour temperatures a colour profile may hold (see WeatherSettings.colors)
KELVIN_MIN = 8000
KELVIN_MAX = 23000

STORAGE_VERSION = 1
STORAGE_KEY_TPL = "redsea.led_weather.{entry_id}"


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------


@dataclass
class WeatherSettings:
    """What the user chose, with the guard rails of the generated program."""

    enabled: bool = False
    period: str = PERIOD_NEXT_WEEK
    # "lat, lon", a map link, or empty for the Home Assistant home
    location: str = ""
    min_intensity: int = 0
    max_intensity: int = 100
    anchor: str = ANCHOR_PLACE
    # Tank times of the sunrise and the sunset, "HH:MM" (anchored days)
    sunrise: str = "10:00"
    sunset: str = "22:00"
    clouds: bool = True
    # Days between two weather fetches
    refresh_days: int = REFRESH_DAYS_DEFAULT
    # Colour of the weather days chosen by the user, per weekday ("1".."7"):
    # [{"at": moment of the day 0..1 (rise..set), "k": colour temperature}].
    # A weekday without one takes the colour of the lamp's own program.
    colors: dict[str, list[dict[str, float]]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> WeatherSettings:
        """Settings from their stored form, invalid values left at default."""
        out = cls()
        if not isinstance(data, dict):
            return out
        for key, value in data.items():
            if hasattr(out, key):
                try:
                    out.set(key, value)
                except (TypeError, ValueError):
                    _LOGGER.warning("Ignored weather setting %s=%r", key, value)
        return out

    def set(self, key: str, value: Any) -> None:
        """Change one setting, checked.

        @raise ValueError: unknown key or invalid value
        """
        if key in ("enabled", "clouds"):
            setattr(self, key, bool(value))
        elif key == "period":
            if value not in PERIODS:
                raise ValueError(f"period must be one of {PERIODS}")
            self.period = value
        elif key == "anchor":
            if value not in ANCHORS:
                raise ValueError(f"anchor must be one of {ANCHORS}")
            self.anchor = value
        elif key in ("min_intensity", "max_intensity"):
            setattr(self, key, max(0, min(100, round(float(value)))))
        elif key == "refresh_days":
            days = round(float(value))
            self.refresh_days = max(REFRESH_DAYS_MIN, min(REFRESH_DAYS_MAX, days))
        elif key in ("sunrise", "sunset"):
            if parse_hhmm(str(value)) is None:
                raise ValueError(f"{key} must be HH:MM")
            setattr(self, key, str(value)[:5])
        elif key == "location":
            self.location = str(value or "").strip()
        elif key == "colors":
            self.colors = parse_colors(value)
        else:
            raise ValueError(f"unknown setting {key}")

    def as_dict(self) -> dict[str, Any]:
        """Stored form."""
        return asdict(self)


def parse_colors(value: Any) -> dict[str, list[dict[str, float]]]:
    """Colour profiles of the weather days, checked (see WeatherSettings).

    @raise ValueError: not {weekday: [{at, k}]}
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("colors must be {weekday: [{at, k}]}")
    out: dict[str, list[dict[str, float]]] = {}
    for day, points in value.items():
        if str(day) not in {str(n) for n in range(1, 8)} or not isinstance(
            points, list
        ):
            raise ValueError("colors must be {weekday: [{at, k}]}")
        profile = [
            {
                "at": max(0.0, min(1.0, float(p["at"]))),
                "k": max(KELVIN_MIN, min(KELVIN_MAX, round(float(p["k"])))),
            }
            for p in points
        ]
        if profile:
            out[str(day)] = sorted(profile, key=lambda p: p["at"])
    return out


def profile_kelvin(profile: list[dict[str, float]], share: float) -> int:
    """Colour temperature of a colour profile at a moment of the day."""
    if share <= profile[0]["at"]:
        return int(profile[0]["k"])
    for a, b in itertools.pairwise(profile):
        # A pair at the same moment is never met here: the first check, or
        # the pair before it, holds that moment
        if a["at"] <= share <= b["at"] and b["at"] > a["at"]:
            ratio = (share - a["at"]) / (b["at"] - a["at"])
            return round(a["k"] + (b["k"] - a["k"]) * ratio)
    return int(profile[-1]["k"])


class WeatherStore:
    """Persistent weather settings of one lamp, its standard programs kept
    aside while in weather mode, and the last generation."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TPL.format(entry_id=entry_id)
        )
        self.settings = WeatherSettings()
        # Summary of the last generation (see apply_weather), or its error
        self.result: dict[str, Any] = {}
        # Standard programs of each lamp (see backup_lamp), by lamp
        self.backup: dict[str, Any] = {}
        # Day of the last successful fetch, ISO
        self.last_success: str | None = None
        # Told of a changed setting (not the mode, not the frequency): the
        # week is then generated again
        self.on_settings_change: Callable[[str], None] | None = None
        # A week being written to the lamps: {"done": days, "total": days}
        self.writing: dict[str, int] | None = None
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        """Read the stored settings, programs and result."""
        raw = await self._store.async_load() or {}
        self.settings = WeatherSettings.from_dict(raw.get("settings"))
        result = raw.get("result")
        self.result = result if isinstance(result, dict) else {}
        backup = raw.get("backup")
        self.backup = backup if isinstance(backup, dict) else {}
        last = raw.get("last_success")
        self.last_success = last if isinstance(last, str) else None

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "settings": self.settings.as_dict(),
                "result": self.result,
                "backup": self.backup,
                "last_success": self.last_success,
            }
        )
        for listener in list(self._listeners):
            listener()

    async def async_set(self, key: str, value: Any) -> None:
        """Change one setting and save it (see WeatherSettings.set)."""
        self.settings.set(key, value)
        await self._async_save()
        if (
            self.settings.enabled
            and key not in ("enabled", "refresh_days")
            and self.on_settings_change is not None
        ):
            self.on_settings_change(key)

    async def async_update(self, values: dict[str, Any]) -> None:
        """Change several settings at once, saved once, the week not made
        again (the caller sends it: see save_weather). The mode is left.

        @raise ValueError: an unknown key or an invalid value (nothing kept)
        """
        settings = WeatherSettings.from_dict(self.settings.as_dict())
        for key, value in values.items():
            if key != "enabled":
                settings.set(key, value)
        self.settings = settings
        await self._async_save()

    async def async_set_mode(self, enabled: bool, backup: dict[str, Any]) -> None:
        """Enter or leave the weather mode, with the standard programs."""
        self.settings.enabled = enabled
        self.backup = backup
        if not enabled:
            self.result = {}
            self.last_success = None
        await self._async_save()

    def due(self, today: date) -> bool:
        """Whether the weather should be fetched again (every refresh_days)."""
        if not self.settings.enabled:
            return False
        if self.last_success is None:
            return True
        try:
            last = date.fromisoformat(self.last_success)
        except ValueError:
            return True
        return (today - last).days >= self.settings.refresh_days

    async def async_set_result(self, result: dict[str, Any]) -> None:
        """Keep the summary of a generation."""
        self.result = result
        await self._async_save()

    @callback
    def set_writing(self, done: int | None, total: int = 0) -> None:
        """Progress of a week being written (None once written); not saved."""
        self.writing = None if done is None else {"done": done, "total": total}
        for listener in list(self._listeners):
            listener()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Be told of every change; returns the function removing it."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove


# -----------------------------------------------------------------------------
# Location and times
# -----------------------------------------------------------------------------

_NUM = r"(-?\d{1,3}(?:\.\d+)?)"
_LOCATION_PATTERNS = [
    # Google Maps: .../@43.6045,1.4440,12z
    re.compile(r"@" + _NUM + r"," + _NUM),
    # ?q=, ?ll=, ?query=, ?center= (Google, Apple, Bing...)
    re.compile(
        r"[?&](?:q|ll|query|center|daddr)=" + _NUM + r"\s*(?:,|%2C)\s*" + _NUM,
        re.IGNORECASE,
    ),
    # OpenStreetMap: ?mlat=..&mlon=.. or #map=12/43.6/1.44
    re.compile(r"mlat=" + _NUM + r"&mlon=" + _NUM),
    re.compile(r"#map=\d+(?:\.\d+)?/" + _NUM + r"/" + _NUM),
    # geo: URI
    re.compile(r"^geo:" + _NUM + r"," + _NUM, re.IGNORECASE),
    # Plain "lat, lon" / "lat lon" / "lat;lon"
    re.compile(r"^\s*" + _NUM + r"\s*[,; ]\s*" + _NUM + r"\s*$"),
]


def parse_location(
    text: str, default: tuple[float, float] | None
) -> tuple[float, float] | None:
    """Coordinates from what the user typed.

    Accepts "lat, lon", a geo: URI or a Google Maps / OpenStreetMap / Apple
    Maps link; empty means the Home Assistant home.
    @return (latitude, longitude), None when not understood
    """
    text = (text or "").strip()
    if not text:
        return default
    for pattern in _LOCATION_PATTERNS:
        match = pattern.search(text)
        if match:
            lat, lon = float(match.group(1)), float(match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
            return None
    return None


def parse_hhmm(text: str) -> int | None:
    """Minutes of an "HH:MM" (or "HH:MM:SS") time, None when invalid."""
    match = re.match(r"^\s*(\d{1,2}):(\d{2})(?::\d{2})?\s*$", text or "")
    if not match:
        return None
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours > 23 or minutes > 59:
        return None
    return hours * 60 + minutes


def hhmm(minutes: float) -> str:
    """ "HH:MM" of minutes of a day (wrapping over midnight)."""
    m = round(minutes) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def week_dates(period: str, today: date) -> list[date]:
    """Days whose weather makes the program: the last or the next seven."""
    if period == PERIOD_LAST_WEEK:
        return [today - timedelta(days=n) for n in range(7, 0, -1)]
    return [today + timedelta(days=n) for n in range(1, 8)]


# -----------------------------------------------------------------------------
# Weather
# -----------------------------------------------------------------------------


@dataclass
class DayWeather:
    """Weather of one day at the place, on the place's own clock."""

    day: date
    sunrise: int
    sunset: int
    # Seconds of sunshine and of daylight
    sunshine: float = 0.0
    daylight: float = 0.0
    # Hourly values (Open-Meteo): the radiation is the mean of the hour
    # before n o'clock, the cloud cover the one at n o'clock
    radiation: list[float] = field(default_factory=lambda: [0.0] * 24)
    cloud_cover: list[float] = field(default_factory=lambda: [0.0] * 24)


def open_meteo_params(lat: float, lon: float, dates: list[date]) -> dict[str, str]:
    """Query of the Open-Meteo forecast API (also serves the past days)."""
    return {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "daily": "sunrise,sunset,sunshine_duration,daylight_duration",
        "hourly": "shortwave_radiation,cloud_cover",
        "timezone": "auto",
        "start_date": min(dates).isoformat(),
        "end_date": max(dates).isoformat(),
    }


def _minute_of(iso: Any) -> int | None:
    """Minutes of the day of an ISO local time ("2026-09-22T06:03")."""
    if not isinstance(iso, str) or "T" not in iso:
        return None
    return parse_hhmm(iso.split("T", 1)[1])


def parse_weather(payload: Any) -> list[DayWeather]:
    """Days of an Open-Meteo answer; days without a sunrise are left out."""
    if not isinstance(payload, dict):
        return []
    daily = payload.get("daily") or {}
    hourly = payload.get("hourly") or {}
    hours: dict[str, dict[str, list[float]]] = {}
    for n, stamp in enumerate(hourly.get("time") or []):
        if not isinstance(stamp, str) or "T" not in stamp:
            continue
        day, clock = stamp.split("T", 1)
        hour = int(clock[:2])
        rows = hours.setdefault(
            day, {"radiation": [0.0] * 24, "cloud_cover": [0.0] * 24}
        )
        for key, src in (
            ("radiation", "shortwave_radiation"),
            ("cloud_cover", "cloud_cover"),
        ):
            values = hourly.get(src) or []
            value = values[n] if n < len(values) else None
            rows[key][hour] = float(value) if isinstance(value, (int, float)) else 0.0

    def _at(key: str, n: int) -> Any:
        values = daily.get(key) or []
        return values[n] if n < len(values) else None

    out: list[DayWeather] = []
    for n, day in enumerate(daily.get("time") or []):
        rise = _minute_of(_at("sunrise", n))
        set_ = _minute_of(_at("sunset", n))
        if rise is None or set_ is None or set_ <= rise:
            continue
        rows = hours.get(day, {})
        out.append(
            DayWeather(
                day=date.fromisoformat(day),
                sunrise=rise,
                sunset=set_,
                sunshine=float(_at("sunshine_duration", n) or 0),
                daylight=float(_at("daylight_duration", n) or 0),
                radiation=rows.get("radiation", [0.0] * 24),
                cloud_cover=rows.get("cloud_cover", [0.0] * 24),
            )
        )
    return out


def _hourly_at(values: list[float], minute: float) -> float:
    """Hourly mean at a minute: each mean stands at the middle of its hour."""
    centers = [(h * 60 - 30, v) for h, v in enumerate(values)]
    if minute <= centers[0][0]:
        return centers[0][1]
    for (m0, v0), (m1, v1) in itertools.pairwise(centers):
        if m0 <= minute <= m1:
            return v0 + (v1 - v0) * (minute - m0) / (m1 - m0)
    return centers[-1][1]


# -----------------------------------------------------------------------------
# Program
# -----------------------------------------------------------------------------


def time_mapper(
    settings: WeatherSettings, rise: int, set_: int
) -> Callable[[float], float]:
    """Tank minute of a place minute, as the user anchored the day."""
    tank_rise = parse_hhmm(settings.sunrise)
    tank_set = parse_hhmm(settings.sunset)
    if settings.anchor == ANCHOR_SUNRISE and tank_rise is not None:
        return lambda m: m + (tank_rise - rise)
    if settings.anchor == ANCHOR_SUNSET and tank_set is not None:
        return lambda m: m + (tank_set - set_)
    if (
        settings.anchor == ANCHOR_BOTH
        and tank_rise is not None
        and tank_set is not None
    ):
        end = tank_set if tank_set > tank_rise else tank_set + 1440
        scale = (end - tank_rise) / (set_ - rise)
        return lambda m: tank_rise + (m - rise) * scale
    return lambda m: float(m)


def channel_value(channel: Any, minute: float) -> float:
    """Level of a program channel at a minute (0 outside its window)."""
    if not isinstance(channel, dict):
        return 0.0
    try:
        rise = float(channel["rise"])
        set_ = float(channel["set"])
    except (KeyError, TypeError, ValueError):
        return 0.0
    if minute <= rise or minute >= set_:
        return 0.0
    pts = [(rise, 0.0)]
    for p in channel.get("points") or []:
        try:
            level = p["i"] if "i" in p else p["i1"]
            pts.append((rise + float(p["t"]), float(level)))
        except (KeyError, TypeError, ValueError):
            continue
    pts.append((set_, 0.0))
    pts.sort(key=lambda x: x[0])
    for (m0, v0), (m1, v1) in itertools.pairwise(pts):
        if m0 <= minute <= m1:
            return v0 if m1 == m0 else v0 + (v1 - v0) * (minute - m0) / (m1 - m0)
    return 0.0  # pragma: no cover - rise < minute < set lies within a pair


def _window(*channels: Any) -> tuple[float, float] | None:
    """From the first rise to the last set of some channels."""
    rises: list[float] = []
    sets: list[float] = []
    for ch in channels:
        if isinstance(ch, dict) and "rise" in ch and "set" in ch:
            rises.append(float(ch["rise"]))
            sets.append(float(ch["set"]))
    if not rises or max(sets) <= min(rises):
        return None
    return min(rises), max(sets)


def white_blue_balance(program: dict[str, Any], share: float) -> tuple[float, float]:
    """White and blue shares (the brighter at 1) of a G1 program at a moment.

    @param share: moment of its day, 0 at the first rise, 1 at the last set
    Where the program is dark, the nearest lit moment gives the balance;
    without a program, white and blue are equal.
    """
    window = _window(program.get("white"), program.get("blue"))
    if window is None:
        return 1.0, 1.0
    rise, set_ = window
    for step in range(51):
        for s in (share - step / 50, share + step / 50):
            if not 0 <= s <= 1:
                continue
            m = rise + s * (set_ - rise)
            white = channel_value(program.get("white"), m)
            blue = channel_value(program.get("blue"), m)
            top = max(white, blue)
            if top > 0:
                return white / top, blue / top
    return 1.0, 1.0


def kelvin_at(program: dict[str, Any], share: float) -> int:
    """Colour temperature of a G2 program at a moment of its day."""
    color = program.get("color")
    if not isinstance(color, dict):
        return DEFAULT_KELVIN
    pts: list[tuple[float, float]] = []
    for p in color.get("points") or []:
        try:
            pts.append((float(p["t"]), float(p.get("k1", p.get("k")))))
        except (KeyError, TypeError, ValueError):
            continue
    if not pts:
        return DEFAULT_KELVIN
    pts.sort(key=lambda x: x[0])
    span = float(color.get("set", 0)) - float(color.get("rise", 0))
    t = share * span
    if t <= pts[0][0]:
        return int(pts[0][1])
    for (t0, k0), (t1, k1) in itertools.pairwise(pts):
        if t0 <= t <= t1:
            return round(k0 if t1 == t0 else k0 + (k1 - k0) * (t - t0) / (t1 - t0))
    return int(pts[-1][1])


def sample_minutes(rise: float, set_: float) -> list[float]:
    """Moments of the points of a day: about hourly, at most MAX_POINTS."""
    count = max(1, min(MAX_POINTS, int((set_ - rise) // 60)))
    return [rise + (set_ - rise) * (n + 1) / (count + 1) for n in range(count)]


def intensity_of(radiation: float, settings: WeatherSettings) -> int:
    """Lamp intensity of a sun, within the user's bounds."""
    low = min(settings.min_intensity, settings.max_intensity)
    high = max(settings.min_intensity, settings.max_intensity)
    share = max(0.0, min(1.0, radiation / FULL_SUN_WM2))
    return round(low + (high - low) * share)


def clouds_of(
    weather: DayWeather,
    mapper: Callable[[float], float],
    rise: int,
    set_: int,
) -> dict[str, Any] | None:
    """Lamp clouds on the cloudy hours of the day (tank timeline)."""
    # Open-Meteo gives the cover at each hour: it stands for the half hours
    # around it
    cloudy: list[tuple[int, float]] = []
    for hour, cover in enumerate(weather.cloud_cover):
        if weather.sunrise <= hour * 60 <= weather.sunset and cover >= CLOUDY_COVER:
            cloudy.append((hour, cover))
    if not cloudy:
        return None
    start = max(rise, round(mapper(cloudy[0][0] * 60 - 30)))
    end = min(set_, round(mapper(cloudy[-1][0] * 60 + 30)))
    if end <= start:
        return None
    mean = sum(c for _, c in cloudy) / len(cloudy)
    for limit, name, cloud, clear in CLOUD_LEVELS:
        if mean < limit:
            return {
                "from": start,
                "to": end,
                "intensity": name,
                "cloud_duration": cloud,
                "no_cloud_duration": clear,
            }
    return None  # pragma: no cover - the last level takes every cover


def build_day(
    weather: DayWeather,
    current: dict[str, Any] | None,
    settings: WeatherSettings,
    g2: bool,
    to_white_blue: Callable[[int], tuple[float, float]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    """Program of a day from its weather, in the lamp's format.

    @param current: the lamp's program of that weekday on the day's own
                    timeline (its colours and its moon are kept), or None
    @param to_white_blue: white and blue shares of a colour temperature on
                    this lamp (G1), used by a colour chosen by the user
                    (settings.colors) in place of the program's
    @return the program (day timeline: white/blue/moon or color/moon), the
            clouds (or None) and a summary of the day
    """
    current = current if isinstance(current, dict) else {}
    mapper = time_mapper(settings, weather.sunrise, weather.sunset)
    rise = round(mapper(weather.sunrise))
    set_ = round(mapper(weather.sunset))
    # The day starts within the tank's day and lasts at least MIN_DAY
    rise = max(0, min(rise, 1440 - MIN_DAY))
    set_ = max(rise + MIN_DAY, min(set_, rise + 1440))
    span = set_ - rise

    levels: list[tuple[int, int, float]] = []
    for m in sample_minutes(weather.sunrise, weather.sunset):
        share = (m - weather.sunrise) / (weather.sunset - weather.sunrise)
        level = intensity_of(_hourly_at(weather.radiation, m), settings)
        levels.append((round(share * span), level, share))

    profile = settings.colors.get(str(weather.day.isoweekday()))
    program: dict[str, Any] = {}
    if g2:
        points: list[dict[str, int]] = []
        for t, level, share in levels:
            kelvin = (
                profile_kelvin(profile, share) if profile else kelvin_at(current, share)
            )
            points.append(
                {"t": t, "i1": level, "i2": level, "k1": kelvin, "k2": kelvin}
            )
        program["color"] = {"rise": rise, "set": set_, "points": points}
        old_window = _window(current.get("color"))
    else:
        if profile and to_white_blue is not None:
            balance = [
                to_white_blue(profile_kelvin(profile, share)) for _, _, share in levels
            ]
        else:
            balance = [white_blue_balance(current, share) for _, _, share in levels]
        for key, n in (("white", 0), ("blue", 1)):
            program[key] = {
                "rise": rise,
                "set": set_,
                "points": [
                    {"t": t, "i": round(level * balance[k][n])}
                    for k, (t, level, _) in enumerate(levels)
                ],
            }
        old_window = _window(current.get("white"), current.get("blue"))

    # The moon keeps its place after the sunset
    moon = current.get("moon")
    if isinstance(moon, dict) and "rise" in moon and "set" in moon:
        shift = set_ - (old_window[1] if old_window else set_)
        program["moon"] = {
            **moon,
            "rise": int(moon["rise"] + shift),
            "set": int(moon["set"] + shift),
        }

    clouds = clouds_of(weather, mapper, rise, set_) if settings.clouds else None
    daytime = weather.cloud_cover[weather.sunrise // 60 : weather.sunset // 60 + 1]
    summary = {
        "date": weather.day.isoformat(),
        "weekday": weather.day.isoweekday(),
        "place_sunrise": hhmm(weather.sunrise),
        "place_sunset": hhmm(weather.sunset),
        "sunrise": hhmm(rise),
        "sunset": hhmm(set_),
        "sunshine_hours": round(weather.sunshine / 3600, 1),
        "cloud_cover": round(sum(daytime) / len(daytime)),
        "max_intensity": max((level for _, level, _ in levels), default=0),
        # The lamp's clouds of the day (window and intensity) and its program,
        # on the day's own timeline, for the card's charts
        "clouds": (
            {k: clouds[k] for k in ("from", "to", "intensity")} if clouds else None
        ),
        "program": program,
    }
    return program, clouds, summary


def day_offset(weekday: int) -> int:
    """Start of a weekday on the lamp's weekly timeline."""
    return (weekday - 1) * 1440


def normalize_program(data: Any, weekday: int) -> dict[str, Any] | None:
    """A lamp's /auto/<day> program on the day's own timeline."""
    if not isinstance(data, dict):
        return None
    offset = day_offset(weekday)
    out: dict[str, Any] = {}
    for key, ch in data.items():
        if isinstance(ch, dict) and "rise" in ch and "set" in ch:
            try:
                rise = float(ch["rise"])
            except (TypeError, ValueError):
                continue
            if rise >= offset:
                ch = {**ch, "rise": ch["rise"] - offset, "set": ch["set"] - offset}
        out[key] = ch
    return out


def device_program(
    program: dict[str, Any], weekday: int, clouds: dict[str, Any] | None, g2: bool
) -> dict[str, Any]:
    """Body of POST /auto/<day>: the program on the weekly timeline.

    A G2 carries its clouds in it (from, to, intensity), as the app sends it.
    """
    offset = day_offset(weekday)
    out: dict[str, Any] = {
        key: {**ch, "rise": ch["rise"] + offset, "set": ch["set"] + offset}
        for key, ch in program.items()
    }
    if g2 and clouds:
        out["clouds"] = {
            "from": clouds["from"] + offset,
            "to": clouds["to"] + offset,
            "intensity": clouds["intensity"],
        }
    return out


def device_clouds(clouds: dict[str, Any], weekday: int) -> dict[str, Any]:
    """Body of POST /clouds/<day> (G1), on the weekly timeline."""
    offset = day_offset(weekday)
    return {**clouds, "from": clouds["from"] + offset, "to": clouds["to"] + offset}


# -----------------------------------------------------------------------------
# Generation
# -----------------------------------------------------------------------------


class WeatherError(Exception):
    """The week could not be generated (message for the user)."""


def lamp_key(led: Any) -> str:
    """Key of a lamp in the store (its serial)."""
    return str(getattr(led, "serial", "") or "lamp")


def backup_lamp(led: Any) -> dict[str, Any]:
    """The lamp's standard week, as it holds it: program, clouds and name."""
    week: dict[str, Any] = {}
    for weekday in range(1, 8):
        week[str(weekday)] = {
            "auto": led.get_data(f"$.sources[?(@.name=='/auto/{weekday}')].data", True),
            "clouds": led.get_data(
                f"$.sources[?(@.name=='/clouds/{weekday}')].data", True
            ),
            "name": led.get_data(
                f"$.sources[?(@.name=='/preset_name/{weekday}')].data.name", True
            ),
        }
    return week


def standard_program(
    store: WeatherStore, led: Any, weekday: int
) -> dict[str, Any] | None:
    """The lamp's standard program of a weekday, on the day's own timeline:
    the one kept aside in weather mode, else the one it holds."""
    kept = (store.backup.get(lamp_key(led)) or {}).get(str(weekday)) or {}
    data = kept.get("auto")
    if data is None:
        data = led.get_data(f"$.sources[?(@.name=='/auto/{weekday}')].data", True)
    return normalize_program(data, weekday)


def supports(led: Any, path: str) -> bool:
    """Whether a lamp answers an endpoint: its source was read.

    Some lamps (RSLED90, older firmwares, simulators) have no per-day
    /preset_name/<day> or /clouds/<day>: writing them only gives a 404.
    """
    data = led.get_data(f"$.sources[?(@.name=='{path}')].data", True)
    return data is not None and data != ""


def _is_clouds(clouds: Any) -> bool:
    return isinstance(clouds, dict) and "from" in clouds and "to" in clouds


def _mirror(led: Any, result: Any, path: str, data: Any) -> None:
    """Keep what the lamp accepted in its cached data, before the read-back.

    A week takes a few seconds to write: the entities show each day as soon
    as the lamp took it, rather than all at once at the end.
    """
    if not (isinstance(result, dict) and result.get("ok")):
        return
    query = f"$.sources[?(@.name=='{path}')].data"
    if led.get_data(query, True) is None:
        return
    led.my_api.set_data(query, data)


async def _paced(api: Any, path: str, payload: Any, method: str = "post") -> Any:
    """Send a request to a lamp, then leave it WRITE_DELAY_S to handle it."""
    res = await api.http_send(path, payload, method)
    await asyncio.sleep(WRITE_DELAY_S)
    return res


async def _send_days(
    led: Any,
    days: list[tuple[int, str | None, dict[str, Any], dict[str, Any] | None]],
    progress: Callable[[], None] | None = None,
) -> None:
    """Write days to a lamp: names, programs with their clouds, then apply.

    Each day is (weekday, name or None, body of POST /auto/<day> (a G2's
    clouds inside), G1 clouds of POST /clouds/<day> or None).

    The app's order would be names, clouds, programs; but a lamp checks
    clouds against the program it holds, and a program against the clouds
    it holds ("Cloud period is outside the preset [rise:set] interval", a
    500), so a new program with a shorter day could never be written. Each
    G1 day is therefore cleared of its clouds first, then gets its program,
    then its new clouds. An endpoint the lamp does not answer is left out
    (see supports()). The requests are paced (WRITE_DELAY_S), and
    ``progress`` told after each day.
    """
    api = led.my_api
    g2 = not led.is_g1
    for weekday, name, _body, _clouds in days:
        if name and supports(led, f"/preset_name/{weekday}"):
            res = await _paced(api, f"/preset_name/{weekday}", {"name": name})
            _mirror(led, res, f"/preset_name/{weekday}", {"name": name})
    for weekday, _name, body, clouds in days:
        own_clouds = not g2 and supports(led, f"/clouds/{weekday}")
        held = led.get_data(f"$.sources[?(@.name=='/clouds/{weekday}')].data", True)
        if own_clouds and _is_clouds(held):
            res = await _paced(api, f"/clouds/{weekday}", {}, "delete")
            _mirror(led, res, f"/clouds/{weekday}", {})
        res = await _paced(api, f"/auto/{weekday}", body)
        _mirror(led, res, f"/auto/{weekday}", body)
        if own_clouds and _is_clouds(clouds):
            res = await _paced(api, f"/clouds/{weekday}", clouds)
            _mirror(led, res, f"/clouds/{weekday}", clouds)
        # Day by day: the entities (and the card) follow the writing
        update = getattr(led, "async_update_listeners", None)
        if callable(update):
            update()
        if progress is not None:
            progress()
    await _paced(api, "/auto/apply", {})
    # Read the new programs back, for the entities and the card
    await led.async_request_refresh(config=True)


async def restore_lamp(
    led: Any, week: dict[str, Any], progress: Callable[[], None] | None = None
) -> None:
    """Write a lamp's standard week back (see _send_days)."""
    g2 = not led.is_g1
    days: list[tuple[int, str | None, dict[str, Any], dict[str, Any] | None]] = []
    for weekday, day in sorted(week.items()):
        program = day.get("auto")
        if not isinstance(program, dict):
            continue
        body = dict(program)
        clouds = day.get("clouds")
        if g2 and _is_clouds(clouds):
            body["clouds"] = {
                k: clouds[k] for k in ("from", "to", "intensity") if k in clouds
            }
        days.append(
            (
                int(weekday),
                day.get("name") or None,
                body,
                None if g2 or not _is_clouds(clouds) else clouds,
            )
        )
    await _send_days(led, days, progress)


async def generate_week(
    hass: HomeAssistant,
    device: Any,
    store: WeatherStore,
    fetch: Callable[[str, dict[str, str]], Any],
    today: date,
    result: dict[str, Any],
    settings: WeatherSettings | None = None,
) -> list[tuple[Any, list[Any], bool]]:
    """Make the week from the weather, for each lamp, without writing it.

    @param result: filled with the place and the summary of each day
    @param settings: settings to use instead of the stored ones (a preview)
    @return for each lamp: (lamp, [(weekday, program, clouds)], is a G2)
    @raise WeatherError, or the error of the fetch
    """
    settings = settings or store.settings
    home = (hass.config.latitude, hass.config.longitude)
    place = parse_location(settings.location, home)
    if place is None:
        raise WeatherError(f"Location not understood: {settings.location}")
    dates = week_dates(settings.period, today)
    payload = await fetch(OPEN_METEO_URL, open_meteo_params(*place, dates))
    days = parse_weather(payload)
    if not days:
        raise WeatherError("No weather for this place and period")
    result.update(
        {
            "latitude": place[0],
            "longitude": place[1],
            "timezone": (payload or {}).get("timezone"),
        }
    )
    summaries: list[dict[str, Any]] = []
    writes: list[tuple[Any, list[Any], bool]] = []
    for led in device.weather_targets():
        g2 = not led.is_g1
        plans = []
        for weather in days:
            weekday = weather.day.isoweekday()
            program, clouds, summary = build_day(
                weather,
                standard_program(store, led, weekday),
                settings,
                g2,
                None if g2 else white_blue_of(led),
            )
            plans.append((weekday, program, clouds))
            if led is device.weather_targets()[0]:
                summaries.append(summary)
        writes.append((led, plans, g2))
    result.update({"status": "ok", "days": summaries})
    return writes


def white_blue_of(led: Any) -> Callable[[int], tuple[float, float]]:
    """White and blue shares (the brighter at 1) of a colour on a G1 lamp,
    from its own conversion table."""

    def convert(kelvin: int) -> tuple[float, float]:
        try:
            wb = led.my_api.kelvin_to_white_and_blue(kelvin, 100)
            white, blue = float(wb["white"]), float(wb["blue"])
        except Exception:  # no table: equal channels
            return 1.0, 1.0
        top = max(white, blue)
        return (white / top, blue / top) if top > 0 else (1.0, 1.0)

    return convert


def _result_head(store: WeatherStore, now_iso: str) -> dict[str, Any]:
    return {
        "updated": now_iso,
        "period": store.settings.period,
        "anchor": store.settings.anchor,
    }


def _failed(result: dict[str, Any], err: Exception) -> None:
    if isinstance(err, WeatherError):
        result.update({"status": "error", "error": str(err)})
        return
    _LOGGER.exception("ReefLED weather program failed")
    result.update({"status": "error", "error": str(err) or type(err).__name__})


async def apply_weather(
    hass: HomeAssistant,
    device: Any,
    store: WeatherStore,
    fetch: Callable[[str, dict[str, str]], Any],
    today: date,
    now_iso: str,
    background: Callable[[Coroutine[Any, Any, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Generate the week from the weather and write it to the lamp(s).

    @param device: the lamp's coordinator (a virtual LED writes each of its
                   lamps, each in its own format)
    @param fetch: coroutine function(url, params) -> Open-Meteo JSON
    @param background: runs the writing of the lamps apart (e.g.
                       hass.async_create_task): the week is then returned as
                       soon as it is made and shown, "sent" false
    @return the summary kept by the store (also on error)
    """
    result = _result_head(store, now_iso)
    try:
        writes = await generate_week(hass, device, store, fetch, today, result)
        store.last_success = today.isoformat()
        # Shown at once (weather_program sensor, the card's charts): writing
        # the week to the lamps takes a few seconds more
        result["sent"] = False
        await store.async_set_result(dict(result))
    except Exception as err:  # weather, network...
        _failed(result, err)
        await store.async_set_result(result)
        return result
    if background is not None:
        background(_write_week(store, writes, dict(result)))
        return result
    return await _write_week(store, writes, result)


async def _write_week(
    store: WeatherStore,
    writes: list[tuple[Any, list[Any], bool]],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Write a generated week to the lamps, then keep it as sent.

    The progress (days written) is shown while it lasts (store.writing).
    """
    progress = _progress(store, sum(len(plans) for _, plans, _ in writes))
    try:
        for led, plans, g2 in writes:
            await _write(led, plans, g2, progress)
        result["sent"] = True
    except Exception as err:  # the lamp
        _failed(result, err)
    finally:
        store.set_writing(None)
    await store.async_set_result(result)
    return result


def _progress(store: WeatherStore, total: int) -> Callable[[], None]:
    """Count the days written, told to the store (see WeatherStore.writing)."""
    done = [0]
    store.set_writing(0, total)

    def advance() -> None:
        done[0] += 1
        store.set_writing(done[0], total)

    return advance


async def publish_weather(
    hass: HomeAssistant,
    device: Any,
    fetch: Callable[[str, dict[str, str]], Any] | None = None,
) -> dict[str, Any]:
    """Show the week the settings now make (weather_program sensor), before
    it is written: the lamp is written once the settings settle (see
    run_weather). Weather mode only.

    @return the summary kept by the store, "sent" false
    """
    store = getattr(device, "weather", None)
    if not isinstance(store, WeatherStore):
        return {"status": "error", "error": "Not a ReefLED"}
    if not store.settings.enabled:
        return {"status": "error", "error": "Weather mode is off"}
    now = dt_util.now()
    result = _result_head(store, now.isoformat())
    try:
        await generate_week(
            hass, device, store, fetch or _open_meteo(hass), now.date(), result
        )
    except Exception as err:  # weather, network...
        _failed(result, err)
    result["sent"] = False
    await store.async_set_result(result)
    return result


async def preview_weather(
    hass: HomeAssistant,
    device: Any,
    fetch: Callable[[str, dict[str, str]], Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The week the weather would make now, and the lamp's own week, for the
    card's editor: nothing is written nor kept, whatever the mode.

    @param settings: settings being edited, over the stored ones
    @return the summary of apply_weather() (days with their program), plus
            "standard": {weekday: program} of the first lamp, on each day's
            own timeline (the week kept aside in weather mode), and
            "settings": the settings used
    """
    store = getattr(device, "weather", None)
    if not isinstance(store, WeatherStore):
        return {"status": "error", "error": "Not a ReefLED"}
    now = dt_util.now()
    used = WeatherSettings.from_dict(store.settings.as_dict())
    result = _result_head(store, now.isoformat())
    lamp = device.weather_targets()[0]
    result["standard"] = {
        str(weekday): standard_program(store, lamp, weekday) for weekday in range(1, 8)
    }
    try:
        for key, value in (settings or {}).items():
            if key != "enabled":
                used.set(key, value)
        result.update({"period": used.period, "anchor": used.anchor})
        await generate_week(
            hass,
            device,
            store,
            fetch or _open_meteo(hass),
            now.date(),
            result,
            used,
        )
    except ValueError as err:  # a setting typed wrong
        result.update({"status": "error", "error": str(err)})
    except Exception as err:  # weather, network...
        _failed(result, err)
    result["settings"] = used.as_dict()
    return result


async def save_weather(
    hass: HomeAssistant,
    device: Any,
    settings: dict[str, Any] | None,
    enabled: bool,
    wait: bool = False,
) -> dict[str, Any]:
    """Save the card's editor: the settings, then the mode, the lamp written
    once (the weather week, the lamp's own week back, or nothing when off
    and staying off).

    Optimistic: the settings and the mode are kept, and the week made and
    shown, before the answer; the lamp is written after it, in the
    background (a few seconds).
    @param wait: write the lamp before answering (the card then writes a
                 day of its own over the lamp's week)
    @return the summary kept by the store, or an error
    """
    store = getattr(device, "weather", None)
    if not isinstance(store, WeatherStore):
        return {"status": "error", "error": "Not a ReefLED"}
    try:
        if settings:
            await store.async_update(settings)
    except ValueError as err:
        return {"status": "error", "error": str(err)}
    background = None if wait else hass.async_create_task
    if enabled:
        if not store.settings.enabled:
            backup = {
                lamp_key(led): backup_lamp(led) for led in device.weather_targets()
            }
            await store.async_set_mode(True, backup)
        now = dt_util.now()
        return await apply_weather(
            hass,
            device,
            store,
            _open_meteo(hass),
            now.date(),
            now.isoformat(),
            background,
        )
    if store.settings.enabled:
        backup = dict(store.backup)
        await store.async_set_mode(False, {})
        restore = _restore_all(device, backup, store)
        if background is not None:
            background(restore)
        else:
            await restore
    return {"status": "ok", "enabled": False}


async def _restore_all(
    device: Any, backup: dict[str, Any], store: WeatherStore | None = None
) -> None:
    """Write each lamp's own week back (see restore_lamp), the progress
    shown by the store when given."""
    weeks = [
        (led, week)
        for led in device.weather_targets()
        if isinstance(week := backup.get(lamp_key(led)), dict)
    ]
    progress = _progress(store, sum(len(week) for _, week in weeks)) if store else None
    try:
        for led, week in weeks:
            await restore_lamp(led, week, progress)
    finally:
        if store is not None:
            store.set_writing(None)


def _open_meteo(hass: HomeAssistant) -> Callable[[str, dict[str, str]], Any]:
    """Coroutine function reading an Open-Meteo answer."""
    session = async_get_clientsession(hass)

    async def fetch(url: str, params: dict[str, str]) -> Any:
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    return fetch


async def _write(
    led: Any,
    plans: list[tuple[int, dict[str, Any], dict[str, Any] | None]],
    g2: bool,
    progress: Callable[[], None] | None = None,
) -> None:
    """Send the weather week to a lamp (see _send_days), named as the app
    names programs: a G1 one with a stamp, a G2 one bare."""
    name = PROGRAM_NAME if g2 else f"{PROGRAM_NAME}-{int(time.time() * 1000)}"
    await _send_days(
        led,
        [
            (
                weekday,
                name,
                device_program(program, weekday, clouds, g2),
                None if g2 or not clouds else device_clouds(clouds, weekday),
            )
            for weekday, program, clouds in plans
        ],
        progress,
    )


async def run_weather(hass: HomeAssistant, device: Any) -> dict[str, Any]:
    """Generate and send the week of a lamp in weather mode now."""
    store = getattr(device, "weather", None)
    if not isinstance(store, WeatherStore):
        return {"status": "error", "error": "Not a ReefLED"}
    if not store.settings.enabled:
        return {"status": "error", "error": "Weather mode is off"}
    now = dt_util.now()
    return await apply_weather(
        hass, device, store, _open_meteo(hass), now.date(), now.isoformat()
    )


async def set_weather_mode(hass: HomeAssistant, device: Any, enabled: bool) -> None:
    """Switch a lamp between its standard programs and the weather.

    On: the standard week of each lamp is kept aside, then the weather week
    is sent at once. Off: the standard week is written back.
    """
    store: WeatherStore = device.weather
    if enabled == store.settings.enabled:
        return
    if enabled:
        backup = {lamp_key(led): backup_lamp(led) for led in device.weather_targets()}
        await store.async_set_mode(True, backup)
        await run_weather(hass, device)
        return
    await _restore_all(device, store.backup, store)
    await store.async_set_mode(False, {})
