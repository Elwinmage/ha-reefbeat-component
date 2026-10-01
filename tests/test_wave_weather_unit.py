"""ReefWave GPS weather: settings, Open-Meteo parsing, speeds, program."""

from __future__ import annotations

import copy
from datetime import date
from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.redsea import wave_weather as W


def _forecast(wind: list[Any] | None = None, **daily: Any) -> dict[str, Any]:
    hours = [f"2026-10-01T{h:02d}:00" for h in range(24)]
    return {
        "timezone": "Pacific/Tahiti",
        "daily": {
            "sunrise": daily.get("sunrise", ["2026-10-01T06:00"]),
            "sunset": daily.get("sunset", ["2026-10-01T18:00"]),
        },
        "hourly": {
            "time": hours,
            "wind_speed_10m": wind if wind is not None else [h * 2 for h in range(24)],
        },
    }


def _marine(current: list[Any]) -> dict[str, Any]:
    return {
        "hourly": {
            "time": [f"2026-10-01T{h:02d}:00" for h in range(24)],
            "ocean_current_velocity": current,
        }
    }


BASE = [
    {
        "st": 0,
        "wave_uid": "night",
        "name": "nuit",
        "type": "re",
        "frt": 10,
        "rrt": 2,
        "fti": 100,
        "rti": 50,
        "direction": "fw",
        "start": 0,
    },
    {"st": 600, "wave_uid": "nw", "name": "No", "type": "nw", "direction": "fw"},
    {
        "st": 630,
        "wave_uid": "rs",
        "name": "RS",
        "type": "ra",
        "fti": 0,
        "rti": 20,
        "direction": "alt",
    },
]


# -- Settings ------------------------------------------------------------------


def test_settings() -> None:
    s = W.WaveWeatherSettings.from_dict(
        {
            "enabled": 1,
            "location": " 1, 2 ",
            "source": "current",
            "scale": 999,
            "day_min": -5,
            "day_max": 150,
            "night_min": "12.4",
            "offset": -80,
            "tolerance": 99,
            "bogus": 1,
            "night_max": "x",
        }
    )
    assert s.enabled is True
    assert s.location == "1, 2"
    assert s.source == "current"
    assert s.scale == W.SCALE_MAX
    assert (s.day_min, s.day_max, s.night_min, s.night_max) == (0, 100, 12, 40)
    assert s.offset == W.OFFSET_MIN
    assert s.tolerance == W.TOLERANCE_MAX
    with pytest.raises(ValueError):
        s.set("source", "tide")
    assert W.WaveWeatherSettings.from_dict(None) == W.WaveWeatherSettings()
    # Scale: the source's default unless set
    s.set("scale", 0)
    assert s.scale_of() == W.DEFAULT_SCALE["current"]
    s.set("scale", 12)
    assert s.scale_of() == 12
    assert s.as_dict()["scale"] == 12


@pytest.mark.asyncio
async def test_store(hass: HomeAssistant) -> None:
    store = W.WaveWeatherStore(hass, "s1")
    await store.async_load()
    assert store.base == [] and store.result == {} and store.last_success is None
    told: list[int] = []
    remove = store.async_add_listener(lambda: told.append(1))
    store.settings.enabled = True
    store.base = [{"st": 0}]
    store.result = {"status": "ok"}
    store.last_success = "2026-10-01"
    await store.async_save()
    assert told == [1]
    remove()
    remove()
    await store.async_save()
    assert told == [1]
    again = W.WaveWeatherStore(hass, "s1")
    await again.async_load()
    assert again.settings.enabled is True
    assert again.base == [{"st": 0}]
    assert again.result == {"status": "ok"}
    assert again.last_success == "2026-10-01"
    assert again.due(date(2026, 10, 1)) is False
    assert again.due(date(2026, 10, 2)) is True
    again.settings.enabled = False
    assert again.due(date(2026, 10, 2)) is False

    # Junk stored
    junk = W.WaveWeatherStore(hass, "s2")
    await junk._store.async_save(
        {"settings": None, "result": "x", "base": "x", "last_success": 3}
    )
    await junk.async_load()
    assert junk.result == {} and junk.base == [] and junk.last_success is None
    await junk._store.async_save({"base": [{"st": 1}, "x"]})
    await junk.async_load()
    assert junk.base == [{"st": 1}]


# -- Weather -------------------------------------------------------------------


def test_params_and_parsing() -> None:
    assert W.forecast_params(1.23456, 2)["latitude"] == "1.2346"
    assert W.marine_params(1, 2)["hourly"] == "ocean_current_velocity"
    day = W.parse_place_day(_forecast(), _marine([0.5] * 24))
    assert day is not None
    assert (day.sunrise, day.sunset, day.timezone) == (360, 1080, "Pacific/Tahiti")
    assert day.wind[3] == 6.0
    assert day.current[0] == 0.5
    # No marine answer, gaps, junk values and stamps
    payload = _forecast(wind=[None, True, "x", 4.0])
    payload["hourly"]["time"][2] = "junk"
    payload["hourly"]["time"][3] = "2026-10-01Tab"
    day = W.parse_place_day(payload)
    assert day is not None
    assert day.wind[:4] == [None, None, None, None]
    assert day.current == [None] * 24
    assert W.hourly_values("x", "k") == [None] * 24
    # Unusable days
    assert W.parse_place_day("x") is None
    assert W.parse_place_day(_forecast(sunrise=[None])) is None
    assert W.parse_place_day(_forecast(sunset=["2026-10-01T05:00"])) is None
    assert W.parse_place_day({"daily": {}}) is None


def test_speeds() -> None:
    day = W.PlaceDay(
        sunrise=360,
        sunset=1080,
        wind=[None, 10.0] + [40.0] * 22,
        current=[None] * 24,
    )
    assert W.is_day(day, 5) is False and W.is_day(day, 6) is True
    assert W.is_day(day, 18) is False
    s = W.WaveWeatherSettings()
    values, fallback = W.place_speeds(day, s)
    assert values[0] == 10.0 and fallback is False  # gap filled
    # Current asked, none there: the wind stands in
    s.source = "current"
    assert W.place_speeds(day, s)[1] is True
    day.current = [1.0] * 24
    assert W.place_speeds(day, s) == ([1.0] * 24, False)
    assert W._fill([None, None]) == [0.0, 0.0]

    s = W.WaveWeatherSettings(day_min=30, day_max=80, night_min=10, night_max=40)
    assert W.speed_of(0, True, s, 40) == 30
    assert W.speed_of(80, True, s, 40) == 80
    assert W.speed_of(20, False, s, 40) == 25
    assert W.speed_of(20, False, s, 0) == 10
    assert W.round_speed(57.4) == 57 and W.round_speed(130) == 100
    assert W.round_speed(-3) == 0
    assert W.with_offset(50, -10) == 45
    speeds = W.hourly_speeds(day, W.WaveWeatherSettings(offset=-10))
    assert speeds[0] == 16  # night, 10 km/h of 40: 17.5, -10 %: 15.75
    assert speeds[12] == 72  # day, full scale: 80, -10 %
    assert W.hourly_speeds(day, W.WaveWeatherSettings(offset=-10), 0)[12] == 80


def test_weather_program() -> None:
    assert W.weather_program([], [50] * 24) == []
    speeds = [20] * 6 + [60] * 18
    out = W.weather_program(copy.deepcopy(BASE), speeds)
    # 00:00 – 06:00 alike: one interval; then hourly at 60 merged too
    assert [i["st"] for i in out] == [0, 360, 600, 630]
    assert out[0]["fti"] == 20 and out[0]["rti"] == 10  # reverse keeps its share
    assert "start" not in out[0]
    assert out[1]["fti"] == 60 and out[1]["rti"] == 30
    assert out[2] == BASE[1]  # no wave untouched
    # A wave without forward intensity: the reverse one is the speed
    assert out[3]["fti"] == 60 and out[3]["rti"] == 60
    # A base that does not start at midnight is read from its first interval
    late = [dict(BASE[0], st=120)]
    assert W.weather_program(late, [50] * 24)[0]["st"] == 0
    # Starts beyond the day are left out
    beyond = [dict(BASE[0]), dict(BASE[0], st=2000, fti=10)]
    assert all(i["st"] < 1440 for i in W.weather_program(beyond, [50] * 24))
    assert W._num("x", 3) == 3


def test_weather_program_merges_close_speeds() -> None:
    wave = [dict(BASE[0])]
    # 20, 22, 24, 23 stay within 5 points: one interval at their mean;
    # 40 starts another; 41, 43 join it; 60 does not
    speeds = [20, 22, 24, 23, 40, 41, 43, 60] + [60] * 16
    out = W.weather_program(wave, speeds)
    assert [(i["st"], i["fti"]) for i in out] == [(0, 22), (240, 41), (420, 60)]
    # Without tolerance, only equal speeds merge
    exact = W.weather_program(wave, speeds, 0)
    assert [i["st"] // 60 for i in exact] == [0, 1, 2, 3, 4, 5, 6, 7]
    # A wide tolerance: the whole day is one interval
    assert len(W.weather_program(wave, speeds, 50)) == 1
    # The mean is weighted by the length of the pieces (a base start at 00:30)
    halves = [dict(BASE[0]), dict(BASE[0], st=30)]
    merged = W.weather_program(halves, [10, 13] + [13] * 22, 5)
    assert len(merged) == 1 and merged[0]["fti"] == 13
    # Another wave never merges, whatever the speeds
    two = [dict(BASE[0]), dict(BASE[2], st=60, fti=100, rti=50)]
    assert len(W.weather_program(two, [30] * 24)) == 2
    # No wave pieces merge whatever the speeds
    still = [dict(BASE[1], st=0)]
    assert W.weather_program(still, list(range(24))) == [dict(BASE[1], st=0)]


# -- Running -------------------------------------------------------------------


class _Pump:
    def __init__(self, hass: HomeAssistant, hwid: str, program: Any = None) -> None:
        self.model_id = hwid
        self.title = "WAVE-" + hwid
        self.wave_weather = W.WaveWeatherStore(hass, "p-" + hwid)
        self.program = copy.deepcopy(program if program is not None else BASE)
        self.written: list[Any] = []
        self.group: list[dict[str, Any]] = []
        self.fail = False

    def program_intervals(self) -> list[dict[str, Any]]:
        return self.program

    async def _write_local(self, intervals: list[dict[str, Any]]) -> None:
        if self.fail:
            raise RuntimeError("pump away")
        self.written.append(intervals)

    def wave_group(self) -> list[dict[str, Any]]:
        return self.group or [
            {"hwid": self.model_id, "name": self.title, "coordinator": self}
        ]


def _fetcher(forecast: Any = None, marine: Any = None, fail_marine: bool = False):
    calls: list[str] = []

    async def fetch(url: str, params: dict[str, str]) -> Any:
        calls.append(url)
        if url == W.MARINE_URL:
            if fail_marine:
                raise RuntimeError("no sea")
            return marine
        return forecast if forecast is not None else _forecast()

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


@pytest.mark.asyncio
async def test_fetch_place_day(hass: HomeAssistant) -> None:
    fetch = _fetcher(marine=_marine([1.0] * 24))
    day = await W.fetch_place_day(fetch, 1, 2, "current")
    assert day.current[0] == 1.0
    assert fetch.calls == [W.OPEN_METEO_URL, W.MARINE_URL]  # type: ignore[attr-defined]
    day = await W.fetch_place_day(_fetcher(fail_marine=True), 1, 2, "current")
    assert day.current == [None] * 24
    day = await W.fetch_place_day(_fetcher(), 1, 2, "wind")
    with pytest.raises(W.WaveWeatherError):
        await W.fetch_place_day(_fetcher(forecast={"x": 1}), 1, 2, "wind")


def test_place_of(hass: HomeAssistant) -> None:
    s = W.WaveWeatherSettings()
    assert W.place_of(hass, s) == (
        float(hass.config.latitude),
        float(hass.config.longitude),
    )
    s.location = "-16.05, -145.66"
    assert W.place_of(hass, s) == (-16.05, -145.66)
    s.location = "nowhere"
    with pytest.raises(W.WaveWeatherError):
        W.place_of(hass, s)
    assert W.store_of(object()) is None


@pytest.mark.asyncio
async def test_apply(hass: HomeAssistant) -> None:
    pump = _Pump(hass, "hw1")
    # Off: nothing
    assert (await W.apply_wave_weather(hass, pump, _fetcher()))["status"] == "error"
    assert (await W.apply_wave_weather(hass, object()))["status"] == "error"
    store = pump.wave_weather
    store.settings.enabled = True
    store.base = copy.deepcopy(BASE)
    result = await W.apply_wave_weather(hass, pump, _fetcher())
    assert result["status"] == "ok"
    assert result["sunrise"] == "06:00" and result["sunset"] == "18:00"
    assert len(result["hours"]) == 24 and len(result["speeds"]) == 24
    assert result["intervals"] == len(pump.written[0])
    assert store.last_success is not None
    assert store.result is result
    # No base program: refused, told
    store.base = []
    result = await W.apply_wave_weather(hass, pump, _fetcher())
    assert result["status"] == "error" and "no program" in result["error"]
    # A pump that does not answer
    store.base = copy.deepcopy(BASE)
    pump.fail = True
    result = await W.apply_wave_weather(hass, pump, _fetcher())
    assert result == {"status": "error", "error": "pump away"}
    # An error without a message
    pump.fail = False
    store.settings.location = "nowhere"

    async def _boom(url: str, params: Any) -> Any:
        raise RuntimeError

    store.settings.location = ""
    result = await W.apply_wave_weather(hass, pump, _boom)
    assert result == {"status": "error", "error": "RuntimeError"}


@pytest.mark.asyncio
async def test_preview(hass: HomeAssistant) -> None:
    pump = _Pump(hass, "hw1")
    other = _Pump(hass, "hw2")
    other.wave_weather.settings.offset = -10
    pump.group = [
        {"hwid": "hw1", "name": "A", "coordinator": pump},
        {"hwid": "hw2", "name": "B", "coordinator": other},
        {"hwid": "hw3", "name": "C", "coordinator": None},
    ]
    result = await W.preview_wave_weather(
        hass, pump, {"day_max": 100, "enabled": True}, {"hw1": 5}, _fetcher()
    )
    assert result["status"] == "ok"
    assert [p["offset"] for p in result["pumps"]] == [5, -10, 0]
    assert result["settings"]["day_max"] == 100
    assert result["settings"]["enabled"] is False
    assert pump.wave_weather.settings.day_max == 80  # nothing kept
    bad = await W.preview_wave_weather(hass, pump, {"source": "x"}, None, _fetcher())
    assert bad["status"] == "error"
    away = await W.preview_wave_weather(
        hass, pump, None, None, _fetcher(forecast={"x": 1})
    )
    assert away["status"] == "error"
    assert (await W.preview_wave_weather(hass, object()))["status"] == "error"


@pytest.mark.asyncio
async def test_mode_and_save(hass: HomeAssistant) -> None:
    pump = _Pump(hass, "hw1")
    other = _Pump(hass, "hw2")
    pump.group = other.group = [
        {"hwid": "hw1", "name": "A", "coordinator": pump},
        {"hwid": "hw2", "name": "B", "coordinator": other},
        {"hwid": "hw3", "name": "C", "coordinator": None},
    ]
    fetch = _fetcher()
    monkey = pytest.MonkeyPatch()
    monkey.setattr(W, "_open_meteo", lambda _hass: fetch)
    try:
        result = await W.save_wave_weather(
            hass,
            pump,
            {"location": "1, 2", "day_max": 90, "offset": 30, "enabled": False},
            {"hw2": -10},
            True,
        )
        assert result["status"] == "ok"
        for p in (pump, other):
            store = p.wave_weather
            assert store.settings.enabled is True
            assert store.settings.location == "1, 2"
            assert store.settings.day_max == 90
            assert store.base == BASE  # its own program kept aside
            assert len(p.written) == 1
        # The offset is each pump's own: not shared
        assert pump.wave_weather.settings.offset == 0
        assert other.wave_weather.settings.offset == -10
        # Saved again while on: the weather is made again, the base kept
        pump.program = [{"st": 0, "type": "nw"}]
        await W.save_wave_weather(hass, pump, None, None, True)
        assert pump.wave_weather.base == BASE
        assert len(pump.written) == 2
        # The base edited (program editor): the weather follows it
        assert await W.base_changed(hass, pump, [dict(BASE[0], fti=50)]) is True
        assert pump.wave_weather.base[0]["fti"] == 50
        # Off: each pump gets its own program back
        result = await W.save_wave_weather(hass, pump, None, None, False)
        assert result == {"status": "ok", "enabled": False}
        assert pump.written[-1] == [dict(BASE[0], fti=50)]
        assert other.written[-1] == BASE
        assert pump.wave_weather.base == [] and not pump.wave_weather.settings.enabled
        assert await W.base_changed(hass, pump, BASE) is False
        # Off and staying off: nothing written
        count = len(pump.written)
        await W.set_wave_weather_mode(hass, pump, False)
        assert len(pump.written) == count
        # Off with no base kept: nothing to write back
        pump.wave_weather.settings.enabled = True
        await W.set_wave_weather_mode(hass, pump, False)
        assert len(pump.written) == count
        # Refusals
        bad = await W.save_wave_weather(hass, pump, {"source": "x"}, None, True)
        assert bad["status"] == "error"
        bad = await W.save_wave_weather(hass, pump, None, {"hw1": "x"}, True)
        assert bad["status"] == "error"
        assert (await W.save_wave_weather(hass, object(), None, None, True))[
            "status"
        ] == "error"
        assert (await W.set_wave_weather_mode(hass, object(), True))[
            "status"
        ] == "error"
        assert await W.base_changed(hass, object(), BASE) is False
    finally:
        monkey.undo()
