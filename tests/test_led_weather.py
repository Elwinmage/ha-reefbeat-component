"""Tests of the ReefLED week program following the weather (led_weather.py)."""

from __future__ import annotations

from datetime import date, time
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.redsea import led_weather as W
from custom_components.redsea import led_weather_entities as E

# One day of Open-Meteo at Fiji, trimmed: sun from 06:00 to 18:00, a cloudy
# afternoon
HOURS = [f"2026-09-22T{h:02d}:00" for h in range(24)]
RADIATION = (
    [0.0] * 7
    + [200.0, 500.0, 800.0, 1000.0, 1000.0, 900.0]
    + [
        300.0,
        250.0,
        200.0,
        150.0,
        50.0,
    ]
    + [0.0] * 6
)
COVER = [0.0] * 13 + [70.0, 80.0, 90.0, 90.0, 60.0] + [10.0] * 6
PAYLOAD = {
    "timezone": "Pacific/Fiji",
    "daily": {
        "time": ["2026-09-22"],
        "sunrise": ["2026-09-22T06:00"],
        "sunset": ["2026-09-22T18:00"],
        "sunshine_duration": [30600.0],
        "daylight_duration": [43200.0],
    },
    "hourly": {
        "time": HOURS,
        "shortwave_radiation": RADIATION,
        "cloud_cover": COVER,
    },
}

# The lamp's current programs (day timeline)
G1_PROGRAM = {
    "white": {"rise": 600, "set": 1200, "points": [{"t": 120, "i": 50}]},
    "blue": {"rise": 600, "set": 1200, "points": [{"t": 120, "i": 100}]},
    "moon": {"rise": 1230, "set": 1400, "points": [{"t": 60, "i": 10}]},
}
G2_PROGRAM = {
    "color": {
        "rise": 540,
        "set": 1260,
        "points": [
            {"t": 60, "i1": 60, "i2": 60, "k1": 14000, "k2": 14000},
            {"t": 660, "i1": 50, "i2": 50, "k1": 23000, "k2": 23000},
        ],
    },
}


def _weather() -> W.DayWeather:
    return W.parse_weather(PAYLOAD)[0]


# -----------------------------------------------------------------------------
# Settings and store
# -----------------------------------------------------------------------------


def test_settings_are_checked() -> None:
    s = W.WeatherSettings()
    s.set("period", "last_week")
    s.set("anchor", "both")
    s.set("min_intensity", 120.4)
    s.set("max_intensity", -3)
    s.set("sunrise", "09:30:00")
    s.set("location", "  43.6, 1.44 ")
    s.set("enabled", 1)
    assert (s.period, s.anchor, s.min_intensity, s.max_intensity) == (
        "last_week",
        "both",
        100,
        0,
    )
    assert (s.sunrise, s.location, s.enabled) == ("09:30", "43.6, 1.44", True)
    for key, value in (
        ("period", "tomorrow"),
        ("anchor", "noon"),
        ("sunset", "25:00"),
        ("colour", 1),
    ):
        with pytest.raises(ValueError):
            s.set(key, value)
    back = W.WeatherSettings.from_dict({**s.as_dict(), "period": "bad", "x": 1})
    assert back.period == "next_week"  # invalid: default kept
    assert back.anchor == "both"
    assert W.WeatherSettings.from_dict(None) == W.WeatherSettings()


@pytest.mark.asyncio
async def test_store_saves_and_notifies(hass: HomeAssistant) -> None:
    store = W.WeatherStore(hass, "e1")
    await store.async_load()
    calls: list[int] = []
    remove = store.async_add_listener(lambda: calls.append(1))
    await store.async_set("max_intensity", 80)
    await store.async_set_result({"status": "ok"})
    assert calls == [1, 1]
    remove()
    remove()  # twice: harmless
    await store.async_set("clouds", False)
    assert calls == [1, 1]

    again = W.WeatherStore(hass, "e1")
    await again.async_load()
    assert again.settings.max_intensity == 80
    assert again.settings.clouds is False
    assert again.result == {"status": "ok"}


# -----------------------------------------------------------------------------
# Location, times, weather
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", (1.0, 2.0)),
        ("-17.71, 178.06", (-17.71, 178.06)),
        ("-17.71 178.06", (-17.71, 178.06)),
        ("https://www.google.com/maps/@-17.7134,178.0650,12z", (-17.7134, 178.065)),
        ("https://maps.google.com/?q=43.6,1.44", (43.6, 1.44)),
        ("https://maps.apple.com/?ll=43.6%2C1.44", (43.6, 1.44)),
        ("https://www.openstreetmap.org/?mlat=43.6&mlon=1.44", (43.6, 1.44)),
        ("https://www.openstreetmap.org/#map=12/43.6/1.44", (43.6, 1.44)),
        ("geo:43.6,1.44", (43.6, 1.44)),
        ("91, 10", None),
        ("somewhere", None),
    ],
)
def test_parse_location(text: str, expected: Any) -> None:
    assert W.parse_location(text, (1.0, 2.0)) == expected


def test_times_and_dates() -> None:
    assert W.parse_hhmm("6:05") == 365
    assert W.parse_hhmm("24:00") is None
    assert W.parse_hhmm("") is None
    assert W.hhmm(1445) == "00:05"
    today = date(2026, 9, 29)
    assert W.week_dates("next_week", today)[0] == date(2026, 9, 30)
    assert W.week_dates("last_week", today) == [date(2026, 9, d) for d in range(22, 29)]
    params = W.open_meteo_params(-17.7, 178.0, W.week_dates("last_week", today))
    assert params["start_date"] == "2026-09-22"
    assert params["end_date"] == "2026-09-28"
    assert params["timezone"] == "auto"


def test_parse_weather() -> None:
    day = _weather()
    assert (day.day, day.sunrise, day.sunset) == (date(2026, 9, 22), 360, 1080)
    assert day.radiation[10] == 1000.0
    assert day.cloud_cover[15] == 90.0
    assert W.parse_weather(None) == []
    # A day without its sun is left out; odd hours are ignored
    odd = {
        "daily": {"time": ["2026-09-22", "2026-09-23"], "sunrise": ["x"]},
        "hourly": {"time": ["bad", HOURS[1]], "shortwave_radiation": ["x"]},
    }
    assert W.parse_weather(odd) == []
    short = {
        "daily": {
            "time": ["2026-09-22"],
            "sunrise": ["2026-09-22T06:00"],
            "sunset": ["2026-09-22T18:00"],
        }
    }
    assert W.parse_weather(short)[0].radiation == [0.0] * 24


def test_hourly_values_are_interpolated() -> None:
    values = [float(h) for h in range(24)]
    assert W._hourly_at(values, -100) == 0.0
    assert W._hourly_at(values, 90) == 2.0  # middle of the 2nd hour mean
    assert W._hourly_at(values, 1500) == 23.0


# -----------------------------------------------------------------------------
# Program
# -----------------------------------------------------------------------------


def test_time_mapper_anchors() -> None:
    s = W.WeatherSettings(sunrise="11:00", sunset="22:00")
    assert W.time_mapper(s, 360, 1080)(720) == 720
    s.anchor = "sunrise"
    assert W.time_mapper(s, 360, 1080)(360) == 660
    s.anchor = "sunset"
    assert W.time_mapper(s, 360, 1080)(1080) == 1320
    s.anchor = "both"
    both = W.time_mapper(s, 360, 1080)
    assert (both(360), both(1080), both(720)) == (660, 1320, 990)
    # A sunset before the sunrise is the next day's
    s.sunset = "02:00"
    assert W.time_mapper(s, 360, 1080)(1080) == 1560
    s.sunrise = "bad"
    assert W.time_mapper(s, 360, 1080)(500) == 500


def test_channel_values_and_colours() -> None:
    white = G1_PROGRAM["white"]
    assert W.channel_value(white, 600) == 0
    assert W.channel_value(white, 720) == 50
    assert W.channel_value(white, 660) == 25
    assert W.channel_value(None, 700) == 0
    assert W.channel_value({"rise": "x"}, 700) == 0
    assert W.channel_value({"rise": 0, "set": 100, "points": [{"x": 1}]}, 50) == 0
    same = {"rise": 0, "set": 100, "points": [{"t": 50, "i": 10}, {"t": 50, "i": 30}]}
    assert W.channel_value(same, 50) == 10
    # G1: white at half the blue all day long
    assert W.white_blue_balance(G1_PROGRAM, 0.5) == (0.5, 1.0)
    # At the edges the program is dark: the nearest lit moment gives it
    assert W.white_blue_balance(G1_PROGRAM, 0.0) == (0.5, 1.0)
    assert W.white_blue_balance({}, 0.3) == (1.0, 1.0)
    dark = {"white": {"rise": 0, "set": 100, "points": []}}
    assert W.white_blue_balance(dark, 0.3) == (1.0, 1.0)
    # G2: colour along the day
    assert W.kelvin_at(G2_PROGRAM, 0.0) == 14000
    assert W.kelvin_at(G2_PROGRAM, 1.0) == 23000
    assert W.kelvin_at(G2_PROGRAM, 0.5) == 18500
    assert W.kelvin_at({}, 0.5) == W.DEFAULT_KELVIN
    assert W.kelvin_at({"color": {"points": [{"t": "x"}]}}, 0.5) == W.DEFAULT_KELVIN
    twin = {"color": {"rise": 0, "set": 100, "points": [{"t": 50, "k": 9000}] * 2}}
    assert W.kelvin_at(twin, 0.5) == 9000


def test_samples_and_intensity() -> None:
    assert len(W.sample_minutes(360, 1080)) == W.MAX_POINTS
    assert W.sample_minutes(360, 400) == [380.0]
    s = W.WeatherSettings(min_intensity=20, max_intensity=80)
    assert W.intensity_of(0, s) == 20
    assert W.intensity_of(500, s) == 50
    assert W.intensity_of(2000, s) == 80
    # Bounds typed the wrong way round still work
    assert (
        W.intensity_of(1000, W.WeatherSettings(min_intensity=90, max_intensity=10))
        == 90
    )


def test_build_day_g1() -> None:
    s = W.WeatherSettings(min_intensity=10, max_intensity=90)
    program, clouds, summary = W.build_day(_weather(), G1_PROGRAM, s, False)
    white, blue = program["white"], program["blue"]
    # Place's clock: 06:00 to 18:00
    assert (white["rise"], white["set"]) == (360, 1080)
    assert len(blue["points"]) == W.MAX_POINTS
    # The white keeps half the blue; the midday sun reaches the maximum
    peak = max(p["i"] for p in blue["points"])
    assert 80 <= peak <= 90
    for w, b in zip(white["points"], blue["points"]):
        assert abs(w["i"] - b["i"] / 2) <= 1
    # The moon keeps its place after the sunset (it was 30 min after)
    assert program["moon"]["rise"] == 1080 + 30
    # Cloudy afternoon: 13:00 to 17:00, each hour standing for its half
    # hours around (78 % on average)
    assert clouds is not None
    assert (clouds["from"], clouds["to"]) == (750, 1050)
    assert clouds["intensity"] == "Medium"
    assert (clouds["cloud_duration"], clouds["no_cloud_duration"]) == (4, 6)
    assert summary["sunrise"] == "06:00"
    assert summary["clouds"] == {"from": 750, "to": 1050, "intensity": "Medium"}
    assert summary["program"] is program
    assert summary["sunshine_hours"] == 8.5
    assert summary["max_intensity"] == peak


def test_build_day_g2_anchored_without_clouds() -> None:
    s = W.WeatherSettings(anchor="sunrise", sunrise="11:00", clouds=False)
    program, clouds, summary = W.build_day(_weather(), G2_PROGRAM, s, True)
    color = program["color"]
    assert (color["rise"], color["set"]) == (660, 1380)
    assert color["points"][0]["k1"] < color["points"][-1]["k1"]
    assert all(p["i1"] == p["i2"] for p in color["points"])
    assert "moon" not in program
    assert clouds is None
    assert summary["place_sunrise"] == "06:00"
    assert summary["sunrise"] == "11:00"


def test_build_day_bounds_and_without_program() -> None:
    # A very late sunrise still leaves a whole day in the tank's day
    s = W.WeatherSettings(anchor="sunrise", sunrise="23:50")
    program, _clouds, _summary = W.build_day(_weather(), None, s, False)
    assert program["white"]["rise"] == 1440 - W.MIN_DAY
    assert program["white"]["set"] > program["white"]["rise"]
    assert "moon" not in program
    # Without a program the white and the blue are equal
    assert program["white"]["points"] == program["blue"]["points"]


def test_clouds_levels() -> None:
    day = _weather()
    identity = W.time_mapper(W.WeatherSettings(), 360, 1080)
    day.cloud_cover = [0.0] * 12 + [45.0, 50.0] + [0.0] * 10
    assert (W.clouds_of(day, identity, 360, 1080) or {})["intensity"] == "Low"
    day.cloud_cover = [0.0] * 12 + [70.0, 75.0] + [0.0] * 10
    assert (W.clouds_of(day, identity, 360, 1080) or {})["intensity"] == "Medium"
    day.cloud_cover = [0.0] * 24
    assert W.clouds_of(day, identity, 360, 1080) is None
    # A window squeezed to nothing
    day.cloud_cover = [0.0] * 12 + [70.0] + [0.0] * 11
    assert W.clouds_of(day, identity, 800, 1080) is None
    day.cloud_cover = [0.0] * 12 + [95.0] * 2 + [0.0] * 10
    assert (W.clouds_of(day, identity, 360, 1080) or {})["intensity"] == "High"


def test_device_formats() -> None:
    program = {"white": {"rise": 360, "set": 1080, "points": []}}
    out = W.device_program(program, 3, None, False)
    assert out["white"]["rise"] == 360 + 2880
    clouds = {"from": 700, "to": 800, "intensity": "Low", "cloud_duration": 3}
    g2 = W.device_program({"color": {"rise": 1, "set": 2}}, 2, clouds, True)
    assert g2["clouds"] == {"from": 2140, "to": 2240, "intensity": "Low"}
    assert W.device_clouds(clouds, 2)["cloud_duration"] == 3
    assert W.device_clouds(clouds, 2)["from"] == 2140
    assert W.normalize_program(None, 1) is None
    raw = {
        "white": {"rise": 2100, "set": 2500},
        "blue": {"rise": "x", "set": 1},
        "moon": {"rise": 100, "set": 200},
        "other": 1,
    }
    assert W.normalize_program(raw, 2) == {
        "white": {"rise": 660, "set": 1060},
        "moon": {"rise": 100, "set": 200},
        "other": 1,
    }


# -----------------------------------------------------------------------------
# Generation and writing
# -----------------------------------------------------------------------------


class _Api:
    def __init__(self) -> None:
        self.sent: list[tuple[str, Any, str]] = []

    async def http_send(self, path: str, payload: Any, method: str) -> None:
        self.sent.append((path, payload, method))


class _Led:
    def __init__(self, g1: bool, programs: dict[int, Any]) -> None:
        self.is_g1 = g1
        self.programs = programs
        self.my_api = _Api()
        self.refreshed = 0
        # Endpoints the lamp answers besides /auto/<day>
        self.answers = True

    def get_data(self, path: str, _none: bool = False) -> Any:
        if "/auto/" in path:
            return self.programs.get(int(path.split("/auto/")[1][0]))
        return {"name": "x"} if self.answers else ""

    async def async_request_refresh(self, config: bool = False) -> None:
        self.refreshed += 1


class _Device:
    def __init__(self, *leds: _Led) -> None:
        self.leds = list(leds)

    def weather_targets(self) -> list[_Led]:
        return self.leds


def _week_payload(dates: list[date]) -> dict[str, Any]:
    daily = {k: [] for k in PAYLOAD["daily"]}
    hourly = {"time": [], "shortwave_radiation": [], "cloud_cover": []}
    for d in dates:
        iso = d.isoformat()
        daily["time"].append(iso)
        daily["sunrise"].append(f"{iso}T06:00")
        daily["sunset"].append(f"{iso}T18:00")
        daily["sunshine_duration"].append(30600.0)
        daily["daylight_duration"].append(43200.0)
        hourly["time"] += [f"{iso}T{h:02d}:00" for h in range(24)]
        hourly["shortwave_radiation"] += RADIATION
        hourly["cloud_cover"] += COVER
    return {"timezone": "Pacific/Fiji", "daily": daily, "hourly": hourly}


@pytest.mark.asyncio
async def test_apply_weather_writes_the_week(hass: HomeAssistant) -> None:
    store = W.WeatherStore(hass, "w1")
    await store.async_set("location", "-17.7, 178.0")
    today = date(2026, 9, 29)
    dates = W.week_dates("next_week", today)
    asked: list[Any] = []

    async def fetch(url: str, params: dict[str, str]) -> Any:
        asked.append((url, params))
        return _week_payload(dates)

    g1 = _Led(True, {3: {**G1_PROGRAM}})
    g2 = _Led(False, {})
    result = await W.apply_weather(
        hass, _Device(g1, g2), store, fetch, today, "2026-09-29T00:10:00"
    )
    assert result["status"] == "ok"
    assert (result["latitude"], result["longitude"]) == (-17.7, 178.0)
    assert result["timezone"] == "Pacific/Fiji"
    assert [d["weekday"] for d in result["days"]] == [3, 4, 5, 6, 7, 1, 2]
    assert store.result == result
    assert asked[0][0] == W.OPEN_METEO_URL
    assert asked[0][1]["start_date"] == "2026-09-30"

    # G1: names (stamped), then each day's program and its clouds, then apply
    paths = [p for p, _, _ in g1.my_api.sent]
    assert paths[:7] == [f"/preset_name/{d}" for d in (3, 4, 5, 6, 7, 1, 2)]
    assert paths[7:9] == ["/auto/3", "/clouds/3"]
    assert paths[-1] == "/auto/apply"
    assert g1.my_api.sent[0][1]["name"].startswith("Weather-")
    auto3 = g1.my_api.sent[7][1]
    assert auto3["white"]["rise"] == 360 + 2 * 1440
    assert auto3["moon"]["rise"] == 1080 + 30 + 2 * 1440
    assert g1.refreshed == 1

    # G2: bare name, no /clouds, clouds in the program
    assert g2.my_api.sent[0][1] == {"name": "Weather"}
    assert not any(p.startswith("/clouds") for p, _, _ in g2.my_api.sent)
    auto = next(x for x in g2.my_api.sent if x[0] == "/auto/3")[1]
    assert auto["clouds"]["intensity"] == "Medium"


@pytest.mark.asyncio
async def test_apply_weather_clear_days_remove_g1_clouds(hass: HomeAssistant) -> None:
    store = W.WeatherStore(hass, "w2")
    await store.async_set("clouds", False)
    today = date(2026, 9, 29)
    dates = W.week_dates("last_week", today)
    await store.async_set("period", "last_week")

    async def fetch(url: str, params: dict[str, str]) -> Any:
        return _week_payload(dates)

    class _Cloudy(_Led):
        """A lamp holding clouds on every day."""

        def get_data(self, path: str, _none: bool = False) -> Any:
            if "/clouds/" in path:
                return {"from": 1, "to": 2, "intensity": "Low"}
            return super().get_data(path, _none)

    led = _Cloudy(True, {})
    hass.config.latitude, hass.config.longitude = 44.84, -0.58
    result = await W.apply_weather(hass, _Device(led), store, fetch, today, "now")
    assert result["latitude"] == 44.84  # the HA home
    sent = led.my_api.sent
    # The held clouds go before the program; none come back
    at = sent.index(("/clouds/1", {}, "delete"))
    assert sent[at + 1][0] == "/auto/1"
    assert not [x for x in sent if x[0].startswith("/clouds") and x[2] == "post"]


@pytest.mark.asyncio
async def test_apply_weather_errors(hass: HomeAssistant) -> None:
    store = W.WeatherStore(hass, "w3")
    today = date(2026, 9, 29)

    async def empty(url: str, params: dict[str, str]) -> Any:
        return {}

    async def broken(url: str, params: dict[str, str]) -> Any:
        raise ConnectionError("offline")

    async def odd(url: str, params: dict[str, str]) -> Any:
        raise RuntimeError()

    led = _Led(True, {})
    await store.async_set("location", "nowhere")
    res = await W.apply_weather(hass, _Device(led), store, empty, today, "now")
    assert res == {
        "updated": "now",
        "period": "next_week",
        "anchor": "place",
        "status": "error",
        "error": "Location not understood: nowhere",
    }
    await store.async_set("location", "")
    res = await W.apply_weather(hass, _Device(led), store, empty, today, "now")
    assert res["error"] == "No weather for this place and period"
    res = await W.apply_weather(hass, _Device(led), store, broken, today, "now")
    assert res["error"] == "offline"
    res = await W.apply_weather(hass, _Device(led), store, odd, today, "now")
    assert res["error"] == "RuntimeError"
    assert led.my_api.sent == []
    assert store.result["status"] == "error"


@pytest.mark.asyncio
async def test_run_weather(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert await W.run_weather(hass, object()) == {
        "status": "error",
        "error": "Not a ReefLED",
    }

    class _Resp:
        async def __aenter__(self) -> _Resp:
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        async def json(self) -> Any:
            return {"answer": 42}

    class _Session:
        def get(self, url: str, **kwargs: Any) -> _Resp:
            self.asked = (url, kwargs)
            return _Resp()

    session = _Session()
    monkeypatch.setattr(W, "async_get_clientsession", lambda _hass: session)
    seen: dict[str, Any] = {}

    async def _apply(
        hass: Any, device: Any, store: Any, fetch: Any, today: Any, now: Any
    ) -> Any:
        seen["answer"] = await fetch("url", {"a": "b"})
        seen["today"] = today
        return {"status": "ok"}

    monkeypatch.setattr(W, "apply_weather", _apply)
    device = SimpleNamespace(weather=W.WeatherStore(hass, "w4"))
    device.weather.settings.enabled = True
    assert await W.run_weather(hass, device) == {"status": "ok"}
    assert seen["answer"] == {"answer": 42}
    assert session.asked[1]["params"] == {"a": "b"}


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


class _Coordinator:
    serial = "LED1"
    device_info = {"identifiers": {("redsea", "LED1")}}

    def __init__(self, store: W.WeatherStore) -> None:
        self.weather = store


@pytest.mark.asyncio
async def test_weather_entities(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = W.WeatherStore(hass, "w5")
    device = _Coordinator(store)
    assert E.weather_entities(object(), "switch") == []
    assert E.weather_entities(device, "light") == []
    by_key = {
        e._key: e
        for platform in (
            "switch",
            "select",
            "text",
            "number",
            "time",
            "sensor",
        )
        for e in E.weather_entities(device, platform)
    }
    assert len(by_key) == 11
    assert "weather_apply" not in by_key  # no step to validate
    for entity in by_key.values():
        entity.hass = hass
        entity.async_write_ha_state = lambda: None  # type: ignore[method-assign]
    sync = by_key["weather_sync"]
    assert sync.unique_id == "LED1_weather_sync"
    assert sync.translation_key == "weather_sync"
    assert sync.extra_state_attributes == {"reef_role": "weather_sync"}

    modes: list[bool] = []

    async def _mode(hass: Any, dev: Any, enabled: bool) -> None:
        modes.append(enabled)
        store.settings.enabled = enabled

    monkeypatch.setattr(E, "set_weather_mode", _mode)
    await sync.async_added_to_hass()
    await sync.async_turn_on()
    assert sync.is_on is True
    await sync.async_turn_off()
    assert modes == [True, False]
    assert sync.entity_category is None  # the mode, not a setting
    clouds = by_key["weather_clouds"]
    await clouds.async_turn_off()
    assert store.settings.clouds is False
    await clouds.async_turn_on()
    assert clouds.is_on is True
    await sync.async_will_remove_from_hass()
    await sync.async_will_remove_from_hass()  # already removed

    period = by_key["weather_period"]
    assert period.options == ["next_week", "last_week"]
    await period.async_select_option("last_week")
    assert period.current_option == "last_week"

    location = by_key["weather_location"]
    await location.async_set_value("geo:1,2")
    assert location.native_value == "geo:1,2"

    low = by_key["weather_min_intensity"]
    await low.async_set_native_value(15.0)
    assert low.native_value == 15.0
    assert low.native_unit_of_measurement == "%"
    days = by_key["weather_refresh_days"]
    assert (days.native_min_value, days.native_max_value) == (3, 15)
    assert days.native_unit_of_measurement == "d"
    await days.async_set_native_value(20)
    assert days.native_value == 15

    rise = by_key["weather_sunrise"]
    await rise.async_set_value(time(9, 45))
    assert rise.native_value == time(9, 45)
    store.settings.sunrise = "bad"
    assert rise.native_value is None

    sensor = by_key["weather_program"]
    assert sensor.native_value is None
    await store.async_set_result({"status": "ok", "days": [1]})
    assert sensor.native_value == "ok"
    assert sensor.extra_state_attributes == {
        "days": [1],
        "writing": None,
        "reef_role": "weather_program",
    }
    # A week being written: its progress (not saved)
    store.set_writing(2, 7)
    assert sensor.extra_state_attributes["writing"] == {"done": 2, "total": 7}
    store.set_writing(None)
    assert sensor.extra_state_attributes["writing"] is None


# -----------------------------------------------------------------------------
# Weather mode: standard programs kept aside and written back
# -----------------------------------------------------------------------------


class _StdLed(_Led):
    """A lamp holding its standard week: programs, clouds and names."""

    def __init__(self, g1: bool, serial: str) -> None:
        super().__init__(g1, {})
        self.serial = serial

    def get_data(self, path: str, _none: bool = False) -> Any:
        if "/auto/" in path:
            day = int(path.split("/auto/")[1][0])
            offset = (day - 1) * 1440
            if self.is_g1:
                return {
                    k: {**v, "rise": v["rise"] + offset, "set": v["set"] + offset}
                    for k, v in G1_PROGRAM.items()
                }
            return {
                "color": {
                    **G2_PROGRAM["color"],
                    "rise": 540 + offset,
                    "set": 1260 + offset,
                }
            }
        day = int(path.split("/")[2].split("'")[0])
        if "/clouds/" in path:
            return {"from": 700, "to": 800, "intensity": "Low"} if day == 1 else {}
        return f"Std-{day}"


def test_settings_refresh_days_and_due() -> None:
    s = W.WeatherSettings()
    s.set("refresh_days", 1)
    assert s.refresh_days == 3
    s.set("refresh_days", 40.2)
    assert s.refresh_days == 15


@pytest.mark.asyncio
async def test_store_due_and_setting_changes(hass: HomeAssistant) -> None:
    store = W.WeatherStore(hass, "m1")
    today = date(2026, 9, 29)
    assert store.due(today) is False  # standard mode
    changes: list[str] = []
    store.on_settings_change = changes.append
    await store.async_set("location", "1, 2")
    assert changes == []  # not in weather mode
    await store.async_set_mode(True, {"LED1": {"1": {}}})
    assert store.due(today) is True  # never fetched
    await store.async_set("location", "3, 4")
    await store.async_set("refresh_days", 5)
    await store.async_set("enabled", True)
    assert changes == ["location"]
    store.last_success = "2026-09-26"
    assert store.due(today) is False
    store.last_success = "2026-09-24"
    assert store.due(today) is True
    store.last_success = "bad"
    assert store.due(today) is True
    store.on_settings_change = None
    await store.async_set("anchor", "both")
    # Kept across restarts; leaving the mode forgets the week and the result
    store.last_success = "2026-09-24"
    await store.async_set_result({"status": "ok"})
    again = W.WeatherStore(hass, "m1")
    await again.async_load()
    assert again.backup == {"LED1": {"1": {}}}
    assert again.last_success == "2026-09-24"
    await again.async_set_mode(False, {})
    assert (again.backup, again.result, again.last_success) == ({}, {}, None)


def test_backup_and_standard_program() -> None:
    led = _StdLed(True, "L1")
    week = W.backup_lamp(led)
    assert week["1"]["name"] == "Std-1"
    assert week["1"]["clouds"] == {"from": 700, "to": 800, "intensity": "Low"}
    assert week["3"]["auto"]["white"]["rise"] == 600 + 2880
    assert W.lamp_key(led) == "L1"
    assert W.lamp_key(object()) == "lamp"


@pytest.mark.asyncio
async def test_standard_program_prefers_the_week_kept_aside(
    hass: HomeAssistant,
) -> None:
    store = W.WeatherStore(hass, "m2")
    led = _StdLed(True, "L1")
    # Nothing kept: the lamp's own
    assert W.standard_program(store, led, 3) == G1_PROGRAM
    kept = {"white": {"rise": 2880 + 100, "set": 2880 + 200, "points": []}}
    store.backup = {"L1": {"3": {"auto": kept}}}
    assert W.standard_program(store, led, 3) == {
        "white": {"rise": 100, "set": 200, "points": []}
    }


@pytest.mark.asyncio
async def test_weather_mode_on_and_off(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = W.WeatherStore(hass, "m3")
    g1 = _StdLed(True, "G1")
    g2 = _StdLed(False, "G2")
    device = _Device(g1, g2)
    device.weather = store  # type: ignore[attr-defined]
    runs: list[Any] = []

    async def _run(hass: Any, dev: Any) -> Any:
        runs.append(dev)
        return {}

    monkeypatch.setattr(W, "run_weather", _run)
    await W.set_weather_mode(hass, device, True)
    assert store.settings.enabled is True
    assert set(store.backup) == {"G1", "G2"}
    assert runs == [device]  # the weather week at once
    await W.set_weather_mode(hass, device, True)  # already on
    assert runs == [device]

    await W.set_weather_mode(hass, device, False)
    assert store.settings.enabled is False
    assert store.backup == {}
    # G1: names, then each day: held clouds removed, program, its clouds
    sent = g1.my_api.sent
    assert sent[0] == ("/preset_name/1", {"name": "Std-1"}, "post")
    assert sent[7] == ("/clouds/1", {}, "delete")
    assert sent[8][0] == "/auto/1"
    assert sent[8][1]["white"]["rise"] == 600
    assert sent[9] == (
        "/clouds/1",
        {"from": 700, "to": 800, "intensity": "Low"},
        "post",
    )
    # Day 2 holds no clouds and gets none
    assert [x[0] for x in sent[10:12]] == ["/auto/2", "/auto/3"]
    assert sent[-1] == ("/auto/apply", {}, "post")
    assert g1.refreshed == 1
    # G2: its clouds go with the program
    auto1 = next(x for x in g2.my_api.sent if x[0] == "/auto/1")[1]
    assert auto1["clouds"] == {"from": 700, "to": 800, "intensity": "Low"}
    auto2 = next(x for x in g2.my_api.sent if x[0] == "/auto/2")[1]
    assert "clouds" not in auto2
    await W.set_weather_mode(hass, device, False)  # already off
    assert len(g1.my_api.sent) == len(sent)


@pytest.mark.asyncio
async def test_restore_skips_what_was_not_there(hass: HomeAssistant) -> None:
    led = _StdLed(True, "L")
    await W.restore_lamp(led, {"1": {"auto": None, "clouds": None, "name": None}})
    assert led.my_api.sent == [("/auto/apply", {}, "post")]


@pytest.mark.asyncio
async def test_run_weather_only_in_weather_mode(hass: HomeAssistant) -> None:
    device = SimpleNamespace(weather=W.WeatherStore(hass, "m4"))
    assert await W.run_weather(hass, device) == {
        "status": "error",
        "error": "Weather mode is off",
    }


@pytest.mark.asyncio
async def test_endpoints_the_lamp_does_not_answer_are_left_out(
    hass: HomeAssistant,
) -> None:
    """A lamp without /preset_name/<day> nor /clouds/<day> only gets /auto."""
    led = _Led(True, {})
    led.answers = False
    assert W.supports(led, "/clouds/1") is False
    plans: list[tuple[int, dict[str, Any], dict[str, Any] | None]] = [
        (1, {"white": {"rise": 1, "set": 2}}, {"from": 1, "to": 2})
    ]
    await W._write(led, plans, False)
    assert [p for p, _, _ in led.my_api.sent] == ["/auto/1", "/auto/apply"]
    week = {"1": {"auto": {"white": {}}, "clouds": {"from": 1, "to": 2}, "name": "S"}}
    led.my_api.sent.clear()
    await W.restore_lamp(led, week)
    assert [p for p, _, _ in led.my_api.sent] == ["/auto/1", "/auto/apply"]


@pytest.mark.asyncio
async def test_week_shown_before_the_lamp_is_written(hass: HomeAssistant) -> None:
    """The generated week is published first, then written day by day."""
    store = W.WeatherStore(hass, "early")
    today = date(2026, 9, 29)
    dates = W.week_dates("next_week", today)

    async def fetch(url: str, params: dict[str, str]) -> Any:
        return _week_payload(dates)

    seen: list[Any] = []

    class _Accepting(_Led):
        """A lamp taking every write, with a cached copy of its sources."""

        def __init__(self) -> None:
            super().__init__(True, {})
            self.cache: dict[str, Any] = {"/auto/3": {"old": 1}}
            self.updates = 0
            api = self.my_api
            led = self

            async def send(path: str, payload: Any, method: str) -> Any:
                # The week is already published when the lamp is written
                seen.append(store.result.get("status"))
                api.sent.append((path, payload, method))
                return {"ok": path != "/auto/4"}

            api.http_send = send  # type: ignore[method-assign]
            api.set_data = lambda query, data: led.cache.__setitem__(  # type: ignore[attr-defined]
                query.split("'")[1], data
            )

        def get_data(self, path: str, _none: bool = False) -> Any:
            if "/auto/" in path or "/clouds/" in path:
                return self.cache.get(path.split("'")[1])
            return super().get_data(path, _none)

        def async_update_listeners(self) -> None:
            self.updates += 1

    led = _Accepting()
    result = await W.apply_weather(hass, _Device(led), store, fetch, today, "now")
    assert result["status"] == "ok"
    assert seen and set(seen) == {"ok"}
    # Accepted days are kept at once; a refused one waits for the read-back
    assert "white" in led.cache["/auto/3"]
    assert "/auto/4" not in led.cache
    assert led.updates == 7


@pytest.mark.asyncio
async def test_preview_writes_nothing(hass: HomeAssistant) -> None:
    """The week the weather would make, with the lamp's own week."""
    store = W.WeatherStore(hass, "preview")
    today = date(2026, 9, 29)

    async def fetch(url: str, params: dict[str, str]) -> Any:
        return _week_payload(W.week_dates("next_week", today))

    led = _Led(True, {3: {**G1_PROGRAM}})
    device = _Device(led)
    device.weather = store  # type: ignore[attr-defined]
    result = await W.preview_weather(hass, device, fetch)
    assert result["status"] == "ok"
    assert len(result["days"]) == 7
    assert result["days"][0]["program"]["white"]["rise"] == 360
    assert result["standard"]["3"]["white"]["rise"] == G1_PROGRAM["white"]["rise"]
    assert result["standard"]["1"] is None
    # Nothing written nor kept
    assert led.my_api.sent == []
    assert store.result == {}

    async def broken(url: str, params: dict[str, str]) -> Any:
        raise ConnectionError("offline")

    failed = await W.preview_weather(hass, device, broken)
    assert failed["status"] == "error" and "standard" in failed
    assert await W.preview_weather(hass, SimpleNamespace()) == {
        "status": "error",
        "error": "Not a ReefLED",
    }


@pytest.mark.asyncio
async def test_open_meteo_fetch(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Resp:
        async def __aenter__(self) -> Any:
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        async def json(self) -> Any:
            return {"ok": 1}

    class _Session:
        def get(self, url: str, **kw: Any) -> Any:
            return _Resp()

    monkeypatch.setattr(W, "async_get_clientsession", lambda _hass: _Session())
    assert await W._open_meteo(hass)("u", {}) == {"ok": 1}


@pytest.mark.asyncio
async def test_publish_shows_the_week_without_writing(hass: HomeAssistant) -> None:
    store = W.WeatherStore(hass, "publish")
    today = dt_util.now().date()

    async def fetch(url: str, params: dict[str, str]) -> Any:
        return _week_payload(W.week_dates("next_week", today))

    led = _Led(True, {})
    device = _Device(led)
    device.weather = store  # type: ignore[attr-defined]
    assert (await W.publish_weather(hass, device, fetch))["error"] == (
        "Weather mode is off"
    )
    await store.async_set_mode(True, {})
    result = await W.publish_weather(hass, device, fetch)
    assert result["status"] == "ok" and result["sent"] is False
    assert store.result == result
    assert led.my_api.sent == []
    assert store.last_success is None

    async def broken(url: str, params: dict[str, str]) -> Any:
        raise ConnectionError("offline")

    failed = await W.publish_weather(hass, device, broken)
    assert failed["status"] == "error"
    assert await W.publish_weather(hass, SimpleNamespace()) == {
        "status": "error",
        "error": "Not a ReefLED",
    }
    # Written: sent
    written = await W.apply_weather(hass, device, store, fetch, today, "now")
    assert written["sent"] is True


@pytest.mark.asyncio
async def test_preview_with_the_settings_being_edited(hass: HomeAssistant) -> None:
    store = W.WeatherStore(hass, "edit")
    today = dt_util.now().date()

    async def fetch(url: str, params: dict[str, str]) -> Any:
        return _week_payload(W.week_dates("next_week", today))

    device = _Device(_Led(True, {}))
    device.weather = store  # type: ignore[attr-defined]
    result = await W.preview_weather(
        hass,
        device,
        fetch,
        {"anchor": "sunrise", "sunrise": "11:00", "enabled": True},
    )
    assert result["status"] == "ok"
    assert result["anchor"] == "sunrise"
    assert result["days"][0]["sunrise"] == "11:00"
    assert result["settings"]["sunrise"] == "11:00"
    # Nothing kept
    assert store.settings.anchor == "place"
    assert store.settings.enabled is False
    wrong = await W.preview_weather(hass, device, fetch, {"anchor": "noon"})
    assert wrong["status"] == "error" and "anchor" in wrong["error"]
    assert wrong["settings"]["anchor"] == "place"


@pytest.mark.asyncio
async def test_save_weather(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Saved and shown at once, the lamp written in the background."""
    store = W.WeatherStore(hass, "save")
    led = _Led(True, {3: {**G1_PROGRAM}})
    device = _Device(led)
    device.weather = store  # type: ignore[attr-defined]
    today = dt_util.now().date()

    async def fetch(url: str, params: dict[str, str]) -> Any:
        return _week_payload(W.week_dates("next_week", today))

    monkeypatch.setattr(W, "_open_meteo", lambda _hass: fetch)
    changed: list[str] = []
    store.on_settings_change = changed.append

    # On: the settings, the mode and the week at once; the lamp after
    result = await W.save_weather(
        hass, device, {"anchor": "both", "max_intensity": 70}, True
    )
    assert (store.settings.anchor, store.settings.max_intensity) == ("both", 70)
    assert changed == []  # not through the settle delay
    assert store.settings.enabled is True
    assert result["status"] == "ok" and result["sent"] is False
    assert store.backup  # the lamp's own week kept aside
    await hass.async_block_till_done()
    assert store.result["sent"] is True
    assert any(p.startswith("/auto/") for p, _, _ in led.my_api.sent)

    # Already on: sent again, here waiting for the lamp
    led.my_api.sent.clear()
    waited = await W.save_weather(hass, device, None, True, wait=True)
    assert waited["sent"] is True and led.my_api.sent

    # Off: the lamp's own week back, in the background or waited for
    led.my_api.sent.clear()
    assert await W.save_weather(hass, device, {}, False) == {
        "status": "ok",
        "enabled": False,
    }
    assert store.settings.enabled is False and store.backup == {}
    await hass.async_block_till_done()
    restored = {p: body for p, body, _ in led.my_api.sent}
    assert restored["/auto/3"]["white"]["rise"] == G1_PROGRAM["white"]["rise"]
    await W.save_weather(hass, device, None, True)
    await hass.async_block_till_done()
    led.my_api.sent.clear()
    await W.save_weather(hass, device, None, False, wait=True)
    assert led.my_api.sent  # already written
    led.my_api.sent.clear()
    await W.save_weather(hass, device, None, False)  # already off: nothing
    await hass.async_block_till_done()
    assert led.my_api.sent == []

    assert await W.save_weather(hass, device, {"period": "x"}, True) == {
        "status": "error",
        "error": f"period must be one of {W.PERIODS}",
    }
    assert store.settings.period == "next_week"  # nothing kept
    assert await W.save_weather(hass, SimpleNamespace(), None, True) == {
        "status": "error",
        "error": "Not a ReefLED",
    }


@pytest.mark.asyncio
async def test_write_failing_is_told(hass: HomeAssistant) -> None:
    store = W.WeatherStore(hass, "fail")
    today = dt_util.now().date()

    async def fetch(url: str, params: dict[str, str]) -> Any:
        return _week_payload(W.week_dates("next_week", today))

    class _Broken(_Led):
        async def async_request_refresh(self, config: bool = False) -> None:
            raise ConnectionError("lamp gone")

    result = await W.apply_weather(
        hass, _Device(_Broken(True, {})), store, fetch, today, "now"
    )
    assert result["status"] == "error" and "lamp gone" in result["error"]
    assert store.result == result


async def test_weather_entity_follows_the_group_store(hass: HomeAssistant) -> None:
    """A lamp joining (or leaving) a group shows its group's weather program."""
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    from custom_components.redsea.const import (
        SIGNAL_GROUP_MEMBER_GONE,
        SIGNAL_GROUP_MEMBER_READY,
    )

    own = W.WeatherStore(hass, "w-own")
    group = W.WeatherStore(hass, "w-group")
    device = _Coordinator(own)
    (clouds,) = [
        e for e in E.weather_entities(device, "switch") if e._key == "weather_clouds"
    ]
    clouds.hass = hass
    writes: list[int] = []
    clouds.async_write_ha_state = lambda: writes.append(1)  # type: ignore[method-assign]
    await clouds.async_added_to_hass()

    # Another device loaded, the lamp's store unchanged: nothing to follow
    async_dispatcher_send(hass, SIGNAL_GROUP_MEMBER_READY, "other")
    await hass.async_block_till_done()
    assert writes == []

    # The lamp's group loaded: its store is followed
    device.weather = group
    async_dispatcher_send(hass, SIGNAL_GROUP_MEMBER_READY, "group")
    await hass.async_block_till_done()
    assert writes == [1]
    await own.async_set("clouds", False)
    assert writes == [1]
    await group.async_set("clouds", False)
    assert writes == [1, 1]
    assert clouds.is_on is False

    # The group unloaded: back to the lamp's own
    device.weather = own
    async_dispatcher_send(hass, SIGNAL_GROUP_MEMBER_GONE, "group")
    await hass.async_block_till_done()
    await group.async_set("clouds", True)
    assert writes == [1, 1, 1]
    await clouds.async_will_remove_from_hass()
    # Already unsubscribed: following a store again is harmless
    clouds._unsub = None
    device.weather = group
    clouds._follow_store("group")


# -----------------------------------------------------------------------------
# Colours chosen by the user, pacing and progress of the writing
# -----------------------------------------------------------------------------


def test_colour_profiles() -> None:
    assert W.parse_colors(None) == {}
    assert W.parse_colors(
        {3: [{"at": 1.5, "k": 30000}, {"at": -1, "k": "9000"}], "4": []}
    ) == {"3": [{"at": 0.0, "k": 9000}, {"at": 1.0, "k": W.KELVIN_MAX}]}
    for bad in ([], {"8": []}, {"1": {}}, {"1": [{"at": 0}]}, {"1": [{"k": 1}]}):
        with pytest.raises((ValueError, KeyError, TypeError)):
            W.parse_colors(bad)
    settings = W.WeatherSettings()
    settings.set("colors", {"2": [{"at": 0.5, "k": 12000}]})
    assert W.WeatherSettings.from_dict(settings.as_dict()).colors == {
        "2": [{"at": 0.5, "k": 12000}]
    }
    with pytest.raises(ValueError):
        settings.set("colors", "red")

    profile = [
        {"at": 0.2, "k": 10000},
        {"at": 0.2, "k": 11000},
        {"at": 0.6, "k": 20000},
    ]
    assert W.profile_kelvin(profile, 0.0) == 10000
    assert W.profile_kelvin(profile, 0.4) == 15500
    assert W.profile_kelvin(profile, 1.0) == 20000
    # Two colours at the same moment: the first one
    assert W.profile_kelvin([{"at": 0.0, "k": 9000}, {"at": 0.0, "k": 12000}], 0.0) == (
        9000
    )


def test_build_day_with_the_user_colours() -> None:
    weekday = str(_weather().day.isoweekday())
    colors = {weekday: [{"at": 0.0, "k": 9000}, {"at": 1.0, "k": 21000}]}
    s = W.WeatherSettings(colors=colors)
    program, _clouds, _summary = W.build_day(_weather(), G2_PROGRAM, s, True)
    kelvins = [p["k1"] for p in program["color"]["points"]]
    assert kelvins == sorted(kelvins) and 9000 < kelvins[0] < kelvins[-1] < 21000
    # G1: the lamp's own conversion of each colour
    program, _clouds, _summary = W.build_day(
        _weather(), G1_PROGRAM, s, False, lambda k: (1.0, 0.5)
    )
    for w, b in zip(program["white"]["points"], program["blue"]["points"]):
        assert abs(w["i"] / 2 - b["i"]) <= 1
    # Without a conversion: the colours of the lamp's program (half white)
    program, _clouds, _summary = W.build_day(_weather(), G1_PROGRAM, s, False)
    for w, b in zip(program["white"]["points"], program["blue"]["points"]):
        assert abs(w["i"] - b["i"] / 2) <= 1
    # Another weekday: its own colours kept
    other = W.WeatherSettings(colors={"8" if weekday == "7" else "7": []})
    assert (
        W.build_day(_weather(), G2_PROGRAM, other, True)[0]
        == W.build_day(_weather(), G2_PROGRAM, W.WeatherSettings(), True)[0]
    )


def test_white_blue_of_a_lamp() -> None:
    def lamp(answer: Any) -> Any:
        def convert(kelvin: int, intensity: int) -> Any:
            if isinstance(answer, Exception):
                raise answer
            return answer

        return SimpleNamespace(my_api=SimpleNamespace(kelvin_to_white_and_blue=convert))

    assert W.white_blue_of(lamp({"white": 50, "blue": 100}))(12000) == (0.5, 1.0)
    assert W.white_blue_of(lamp({"white": 0, "blue": 0}))(12000) == (1.0, 1.0)
    assert W.white_blue_of(lamp(RuntimeError("no table")))(12000) == (1.0, 1.0)


@pytest.mark.asyncio
async def test_writing_is_paced_and_its_progress_shown(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    pauses: list[float] = []

    async def _sleep(delay: float) -> None:
        pauses.append(delay)

    monkeypatch.setattr(W, "WRITE_DELAY_S", 2.0)
    monkeypatch.setattr(W.asyncio, "sleep", _sleep)
    store = W.WeatherStore(hass, "progress")
    seen: list[Any] = []
    store.async_add_listener(lambda: seen.append(store.writing))
    led = _Led(True, {})
    led.answers = False
    day = {"white": {"rise": 1, "set": 2}}
    await W._write_week(store, [(led, [(1, day, None), (2, day, None)], False)], {})
    # /auto/1, /auto/2 and /auto/apply, each followed by the pause
    assert pauses == [2.0, 2.0, 2.0]
    progress = [w for w in seen if w is not None]
    assert progress == [
        {"done": 0, "total": 2},
        {"done": 1, "total": 2},
        {"done": 2, "total": 2},
    ]
    assert store.writing is None

    # The lamp's own week written back: the same
    seen.clear()
    week = {"1": {"auto": day, "clouds": None, "name": None}}
    await W._restore_all(_Device(led), {W.lamp_key(led): week}, store)
    assert [w for w in seen if w is not None][-1] == {"done": 1, "total": 1}
    assert store.writing is None
