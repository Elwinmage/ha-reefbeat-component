"""ReefMat and ReefLED: mergers of their pushed messages (poseidon)."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any, cast

from homeassistant.core import HomeAssistant

from custom_components.redsea.const import LEDS_CONV
from custom_components.redsea.poseidon import anomalies as an
from custom_components.redsea.poseidon import const, strategy
from custom_components.redsea.poseidon.mergers import (
    merge_reef_lights_telemetry,
    merge_reef_mat,
    merge_reef_mat_telemetry,
)
from custom_components.redsea.poseidon.relay import UP
from custom_components.redsea.reefbeat.led import _make_interpolator
from tests._poseidon_fakes import HWID
from tests.test_poseidon_events_unit import LIGHTS_TELEMETRY, MAT_TELEMETRY
from tests.test_poseidon_spy_responses_unit import _state_frame
from tests.test_poseidon_spy_unit import _poseidon
from tests.test_reefbeat_led_unit import _make_led_api

# As polled on the RSMAT of the spy run of 2026-10-30
MAT_ANSWERS: dict[str, Any] = {
    "/mode": {"mode": "auto"},
    "/wifi": {"signal_dBm": -50},
    "/dashboard": {
        "mode": "auto",
        "is_advancing": False,
        "last_advance_cause": "ec_sensor",
        "roll_level": "full",
        "days_till_end_of_roll": 14,
        "internal_ec_average": 0,
        "setup_date": "2026-09-12T22:30:15Z",
        "cumulative_steps": 8239,
        "lifetime_steps": 124960,
        "today_usage": 25.6,
        "daily_average_usage": 64.2,
        "total_usage": 2568.3,
        "remaining_length": 930.1,
        "material": {"name": "New Roll", "external_diameter": 11.1},
    },
}
LED_MANUAL = {
    "white": 0,
    "white_full": 0,
    "white_pwm": 0,
    "blue": 0,
    "blue_full": 0,
    "blue_pwm": 0,
    "moon": 0,
    "fan": 0,
    "temperature": 18.1,
}
LED_ANSWERS: dict[str, Any] = {
    "/mode": {"mode": "auto"},
    "/wifi": {"signal_dBm": -50},
    "/manual": copy.deepcopy(LED_MANUAL),
    "/dashboard": {
        "mode": "auto",
        "acclimation": {"enabled": False, "current_intensity_factor": 100},
        "moon_phase": {"enabled": True, "intensity": 14},
        "manual": copy.deepcopy(LED_MANUAL),
        "current_program": {"active_preset": 6, "name": "Perso-1"},
    },
}


def _coordinator(answers: dict[str, Any]) -> Any:
    sources = [
        {"name": name, "type": "data", "data": copy.deepcopy(data)}
        for name, data in answers.items()
    ]
    return SimpleNamespace(my_api=SimpleNamespace(data={"sources": sources}))


def _data(coordinator: Any, name: str) -> Any:
    return next(
        s["data"] for s in coordinator.my_api.data["sources"] if s["name"] == name
    )


def _topic(family: str, suffix: str) -> str:
    return f"device/{family}/{HWID}/{suffix}"


def test_registered() -> None:
    assert strategy.MERGERS["reef-mat"] is merge_reef_mat
    assert strategy.TELEMETRY_MERGERS["reef-mat"] is merge_reef_mat_telemetry
    assert strategy.TELEMETRY_MERGERS["reef-lights"] is merge_reef_lights_telemetry
    # Their live readings are pushed by nothing
    assert "reef-mat" not in strategy.FULLY_PUSHED
    assert "reef-lights" not in strategy.FULLY_PUSHED
    assert strategy.merges_on("reef-mat", _topic("reef-mat", "rolling-log"))
    assert not strategy.merges_on("reef-mat", _topic("reef-mat", "telemetry"))
    assert not strategy.merges_on("reef-dosing", _topic("reef-dosing", "rolling-log"))


# -- ReefMat -----------------------------------------------------------------------------


def test_mat_advance() -> None:
    coordinator = _coordinator(MAT_ANSWERS)
    dashboard = _data(coordinator, "/dashboard")
    started = {
        "specific_attributes": {"is_advancing": True, "internal_ec_average": 305}
    }
    assert merge_reef_mat(coordinator, _topic("reef-mat", "state"), started) is True
    assert dashboard["is_advancing"] is True
    # The average of the advance is no live reading: not merged
    assert dashboard["internal_ec_average"] == 0
    log = {"length": 0.67, "advance_cause": "ec_sensor", "internal_ec_average": 305}
    assert merge_reef_mat(coordinator, _topic("reef-mat", "rolling-log"), log) is True
    done = {
        "specific_attributes": {
            "is_advancing": False,
            "today_usage": 26.275999069213867,
            "total_usage": 2569.0078125,
            "internal_ec_average": 279,
            "remaining_length": 929.4910278320312,
            "cumulative_steps": 8242,
            "lifetime_steps": 124963,
        }
    }
    assert merge_reef_mat(coordinator, _topic("reef-mat", "state"), done) is True
    # As the device answers them: truncated, never rounded up
    assert dashboard["today_usage"] == 26.2
    assert dashboard["total_usage"] == 2569.0
    assert dashboard["remaining_length"] == 929.4
    assert (dashboard["cumulative_steps"], dashboard["lifetime_steps"]) == (
        8242,
        124963,
    )
    assert dashboard["is_advancing"] is False


def test_mat_manual_advance() -> None:
    coordinator = _coordinator(MAT_ANSWERS)
    started = {
        "specific_attributes": {
            "is_advancing": True,
            "last_advance_cause": "manual_advance",
            "internal_ec_average": 0,
        }
    }
    merge_reef_mat(coordinator, _topic("reef-mat", "state"), started)
    dashboard = _data(coordinator, "/dashboard")
    assert dashboard["last_advance_cause"] == "manual_advance"
    # The next advance by the EC sensor is only told by its rolling-log
    log = {"advance_cause": "ec_sensor"}
    merge_reef_mat(coordinator, _topic("reef-mat", "rolling-log"), log)
    assert dashboard["last_advance_cause"] == "ec_sensor"


def test_mat_nothing_to_merge() -> None:
    coordinator = _coordinator(MAT_ANSWERS)
    rolling = _topic("reef-mat", "rolling-log")
    assert merge_reef_mat(coordinator, rolling, {"length": 1}) is False
    assert merge_reef_mat(coordinator, rolling, "junk") is False
    state = _topic("reef-mat", "state")
    assert merge_reef_mat(coordinator, state, {"specific_attributes": 1}) is False
    assert (
        merge_reef_mat(coordinator, state, {"specific_attributes": {"x": 1}}) is False
    )
    assert merge_reef_mat(_coordinator({}), state, {"specific_attributes": {}}) is False


def test_mat_telemetry() -> None:
    coordinator = _coordinator(MAT_ANSWERS)
    telemetry = dict(MAT_TELEMETRY, today_usage=26.99279, material_name="Other roll")
    telemetry["mode"] = "maintenance"
    assert merge_reef_mat_telemetry(coordinator, "", telemetry) is True
    dashboard = _data(coordinator, "/dashboard")
    assert dashboard["today_usage"] == 26.9
    assert dashboard["daily_average_usage"] == 64.3
    assert dashboard["remaining_length"] == 936.6
    assert dashboard["days_till_end_of_roll"] == 14
    assert dashboard["material"]["name"] == "Other roll"
    # Told with "Z" by /dashboard
    assert dashboard["setup_date"] == "2026-09-12T22:30:15Z"
    assert _data(coordinator, "/mode")["mode"] == "maintenance"
    assert _data(coordinator, "/wifi")["signal_dBm"] == MAT_TELEMETRY["wifi_signal"]
    # Another offset is kept as is
    merge_reef_mat_telemetry(
        coordinator, "", {"setup_date": "2026-09-12T22:30:15+02:00"}
    )
    assert dashboard["setup_date"] == "2026-09-12T22:30:15+02:00"


def test_mat_telemetry_without_anything_polled() -> None:
    assert merge_reef_mat_telemetry(_coordinator({}), "", MAT_TELEMETRY) is False
    assert merge_reef_mat_telemetry(_coordinator(MAT_ANSWERS), "", "junk") is False
    # Nothing to truncate in what is no number, no signal that is no number
    coordinator = _coordinator(MAT_ANSWERS)
    merge_reef_mat_telemetry(
        coordinator, "", {"today_usage": None, "wifi_signal": True}
    )
    assert _data(coordinator, "/dashboard")["today_usage"] is None
    assert _data(coordinator, "/wifi")["signal_dBm"] == -50


# -- ReefLED -----------------------------------------------------------------------------


def test_lights_telemetry() -> None:
    coordinator = _coordinator(LED_ANSWERS)
    telemetry = copy.deepcopy(LIGHTS_TELEMETRY)
    telemetry.update(
        {
            "intensities": {"white": 0, "blue": 75, "moon": 0, "uv": 5},
            "fan-speed": 78,
            "temperature": 41.8,
            "moonphase": 15,
            "acclimation": 90,
            "active-program": "Perso-2",
            "mode": "manual",
        }
    )
    assert merge_reef_lights_telemetry(coordinator, "", telemetry) is True
    for manual in (
        _data(coordinator, "/manual"),
        _data(coordinator, "/dashboard")["manual"],
    ):
        assert (manual["blue"], manual["fan"], manual["temperature"]) == (75, 78, 41.8)
        # What is pushed by nothing stays as polled; no channel added
        assert manual["blue_full"] == 0 and manual["blue_pwm"] == 0
        assert "uv" not in manual
    dashboard = _data(coordinator, "/dashboard")
    assert dashboard["moon_phase"]["intensity"] == 15
    assert dashboard["acclimation"]["current_intensity_factor"] == 90
    assert dashboard["current_program"]["name"] == "Perso-2"
    assert dashboard["mode"] == "manual"
    assert _data(coordinator, "/mode")["mode"] == "manual"


def test_lights_telemetry_derives_the_colour_of_a_g1() -> None:
    coordinator = _coordinator(LED_ANSWERS)
    derived: list[str] = []
    api = coordinator.my_api
    api.update_light_wb = lambda: derived.append("wb")
    # A G2 has its own kelvin and intensity
    api._g1 = False
    assert merge_reef_lights_telemetry(coordinator, "", LIGHTS_TELEMETRY) is True
    assert derived == []
    api._g1 = True
    assert merge_reef_lights_telemetry(coordinator, "", LIGHTS_TELEMETRY) is True
    assert derived == ["wb"]
    # Nothing of /manual pushed: nothing to derive
    merge_reef_lights_telemetry(coordinator, "", {"moonphase": 3})
    assert derived == ["wb"]


def test_lights_telemetry_g1_kelvin_from_white_and_blue() -> None:
    api = _make_led_api(hw="RSLED160")
    conv = next(c for c in LEDS_CONV if c["name"] == "RSLED160")
    api._wb_to_kelvin = _make_interpolator(
        [float(v) for v in conv["white_blue"]], [float(v) for v in conv["kelvin"]]
    )
    api.add_source("/manual", "data", {"white": 0, "blue": 0, "moon": 0})
    assert api._g1
    # Kelvin and intensity of the last poll, while the program ramps up
    api.data["local"]["manual_trick"] = {"kelvin": 9000, "intensity": 95}
    coordinator = SimpleNamespace(my_api=api)
    # As pushed by a RSLED160 in auto mode, an evening
    telemetry = {"intensities": {"white": 32, "blue": 94, "moon": 0}}
    assert merge_reef_lights_telemetry(coordinator, "", telemetry) is True
    trick = api.data["local"]["manual_trick"]
    assert 21000 < trick["kelvin"] < 21400 and trick["intensity"] == 94


def test_lights_telemetry_without_anything_polled() -> None:
    assert merge_reef_lights_telemetry(_coordinator({}), "", LIGHTS_TELEMETRY) is False
    assert merge_reef_lights_telemetry(_coordinator(LED_ANSWERS), "", "junk") is False
    answers = copy.deepcopy(LED_ANSWERS)
    answers["/dashboard"] = {"manual": "junk", "moon_phase": None}
    del answers["/manual"], answers["/mode"], answers["/wifi"]
    assert (
        merge_reef_lights_telemetry(_coordinator(answers), "", {"moonphase": 1})
        is False
    )


# -- catalogue -----------------------------------------------------------------------------


def test_power_connection_state_and_metrics() -> None:
    state = {
        "attributes": {"system": {"name": "RSPOWER6-0000000000"}},
        "specific_attributes": {
            "mode": "auto",
            "device_setup_date": 1766281705,
            "factory_reset_time": 1787236648,
            "active_shortcut": "no_shortcut",
            "feeding_type": "manual",
            "device_settings": {
                "feed_schedule_shortcut_code": "no_shortcut",
                "temp_hysteresis": 0.5,
                "temperature": None,
            },
            "temperature": None,
            "connected_device": None,
            "initial": False,
            "is_factory_reset": False,
            "timezone": 120,
        },
    }
    assert (
        an.check_frame("reef-power", UP, 3, _topic("reef-power", "state"), state) == []
    )
    wave = copy.deepcopy(an.CATALOGS["reef-wave"].telemetry)
    assert "metrics.res" in wave


# -- in the manager --------------------------------------------------------------------------


async def test_rolling_log_is_merged_by_the_manager(hass: HomeAssistant) -> None:
    poseidon, coordinator = _poseidon(
        hass, {const.CONF_DEVICE_STRATEGIES: {HWID: const.STRATEGY_POSEIDON}}
    )
    poseidon.keystore.devices[HWID].type = "reef-mat"
    poseidon._apply_polling()
    cast(Any, coordinator.my_api).data["sources"] = [
        {"name": n, "type": "data", "data": copy.deepcopy(d)}
        for n, d in MAT_ANSWERS.items()
    ]
    log = {"advance_cause": "manual_advance"}
    poseidon._on_frame(HWID, UP, _state_frame(log, _topic("reef-mat", "rolling-log")))
    await hass.async_block_till_done()
    assert _data(coordinator, "/dashboard")["last_advance_cause"] == "manual_advance"
    # Merged: no read needed
    assert coordinator.refreshes == []


def test_mat_settings_changed_in_the_app() -> None:
    answers = copy.deepcopy(MAT_ANSWERS)
    answers["/configuration"] = {"auto_advance": True, "schedule_enable": False}
    answers["/dashboard"]["auto_advance"] = True
    coordinator = _coordinator(answers)
    pushed = {
        "specific_attributes": {
            "auto_advance": False,
            "internal_ec_average": 0,
            "device_settings": {"auto_advance": False, "schedule_enable": False},
        }
    }
    assert merge_reef_mat(coordinator, _topic("reef-mat", "state"), pushed) is True
    assert _data(coordinator, "/dashboard")["auto_advance"] is False
    assert _data(coordinator, "/configuration")["auto_advance"] is False
    # A setting /configuration does not have, or a configuration never read:
    # read again
    pushed["specific_attributes"]["device_settings"]["position"] = "right"
    assert merge_reef_mat(coordinator, _topic("reef-mat", "state"), pushed) is False
    no_config = _coordinator(MAT_ANSWERS)
    assert merge_reef_mat(no_config, _topic("reef-mat", "state"), pushed) is False
    unknown = {"specific_attributes": {"is_advancing": True, "new_field": 1}}
    assert merge_reef_mat(coordinator, _topic("reef-mat", "state"), unknown) is False
