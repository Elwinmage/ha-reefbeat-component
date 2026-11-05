"""ReefWave in Poseidon mode: catalogue and merger (spy runs of 2026-10-30
to 2026-11-03, a RSWAVE45 0.10.0 in a group of pumps)."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

from custom_components.redsea.poseidon import anomalies as an
from custom_components.redsea.poseidon import strategy
from custom_components.redsea.poseidon.mergers import (
    merge_reef_wave,
    merge_reef_wave_telemetry,
    wave_fully_pushed,
)
from custom_components.redsea.poseidon.relay import UP

WAVE = "reef-wave"
HWID = "0000aaaa0008"
STATE = f"device/{WAVE}/{HWID}/state"
TELEMETRY = f"device/{WAVE}/{HWID}/telemetry"
AUTO = {
    "uid": "c1cedc73",
    "intervals": [
        {
            "wave_uid": "w-night",
            "type": "re",
            "name": "Nuit",
            "frt": 10,
            "rrt": 2,
            "fti": 100,
            "rti": 60,
            "st": 0,
            "direction": "fw",
        },
        {
            "wave_uid": "w-day",
            "type": "ra",
            "name": "Journee",
            "frt": 10,
            "rrt": 2,
            "fti": 100,
            "rti": 60,
            "st": 750,
            "direction": "alt",
        },
    ],
}
ANSWERS: dict[str, Any] = {
    "/mode": {"mode": "auto"},
    "/wifi": {"signal_dBm": -43},
    "/auto": AUTO,
    "/device-settings": {"shortcut_off_delay": 300},
}
# 2026-11-03 16:04
TELEMETRY_PAYLOAD = {
    "mode": "auto",
    "active_shortcut": "no_shortcut",
    "controlling-mode": "reef-beat",
    "uptime": "D:004-H:06-m:08-s:11",
    "active-wave": {
        "wave_uid": "w-day",
        "type": "ra",
        "name": "Journee",
        "frt": 10,
        "rrt": 2,
        "fti": 100,
        "rti": 60,
        "st": 750,
        "direction": "alt",
    },
    "local_time": "2026-11-03T16:04:31+01:00",
    "utc_time": "2026-11-03T15:04:31Z",
    "hwid": HWID,
    "wifi_signal": -45,
    "free_heap": 52970,
    "metrics": {"ping": 6},
}
CONNECTION = {
    "attributes": {"system": {"hw_type": WAVE, "hw_model": "RSWAVE45"}},
    "specific_attributes": {
        "mode": "auto",
        "active_shortcut": "no_shortcut",
        "controlling-mode": "reef-beat",
        "schedule": {"hash": "4ffd98e1", "uid": "53b88406"},
        "scheduled_feeding": {"hash": "aa", "setup": True},
        "feeding_type": "manual",
        "timezone": 60,
    },
}


def _coordinator(answers: dict[str, Any] | None = None) -> Any:
    polled = copy.deepcopy(ANSWERS if answers is None else answers)
    sources = [
        {"name": name, "type": "data", "data": data} for name, data in polled.items()
    ]
    return SimpleNamespace(my_api=SimpleNamespace(data={"sources": sources}))


def _data(coordinator: Any, name: str) -> Any:
    return next(
        s["data"] for s in coordinator.my_api.data["sources"] if s["name"] == name
    )


def _state(**fields: Any) -> dict[str, Any]:
    return {"specific_attributes": fields}


# -- catalogue ---------------------------------------------------------------------------


def test_recorded_frames_have_no_anomaly() -> None:
    assert an.check_frame(WAVE, UP, 3, TELEMETRY, TELEMETRY_PAYLOAD, HWID) == []
    for state in (
        CONNECTION,
        _state(mode="off"),
        _state(schedule={"hash": "462a5a49", "uid": "2e41cda9"}),
        _state(device_settings={"shortcut_off_delay": 300}),
        _state(ntp_sync=True),
    ):
        assert an.check_frame(WAVE, UP, 3, STATE, state, HWID) == []
    command = f"device/{WAVE}/{HWID}/command"
    for key in ("POST /auto/init", "POST /auto", "POST /auto/apply", "POST /group"):
        method, url = key.split(" ")
        message = {"uuid": "u", "method": method, "url": url, "body": {}}
        assert an.check_frame(WAVE, "down", 3, command, message) == []


def test_new_things_are_told() -> None:
    [found] = an.check_frame(WAVE, UP, 3, STATE, _state(speed=1), HWID)
    assert found.details == ("+specific_attributes.speed:number",)
    message = {"uuid": "u", "method": "POST", "url": "/manual", "body": {}}
    [found] = an.check_frame(WAVE, "down", 3, f"device/{WAVE}/{HWID}/command", message)
    assert (found.kind, found.details) == (an.KIND_COMMAND, ("POST /manual",))


# -- merger ------------------------------------------------------------------------------


def test_registered() -> None:
    assert strategy.MERGERS[WAVE] is merge_reef_wave
    assert strategy.TELEMETRY_MERGERS[WAVE] is merge_reef_wave_telemetry
    assert strategy.FULLY_PUSHED[WAVE] is wave_fully_pushed
    assert strategy.fully_pushed(WAVE, _coordinator())
    # Never polled yet
    assert not strategy.fully_pushed(WAVE, _coordinator({"/mode": {"mode": "auto"}}))
    # A family without merger yet
    assert not strategy.merge_state("reef-ato", _coordinator(), STATE, {})
    assert not strategy.merge_telemetry("reef-ato", _coordinator(), TELEMETRY, {})


def test_telemetry() -> None:
    coordinator = _coordinator()
    telemetry = dict(TELEMETRY_PAYLOAD, mode="off")
    del telemetry["active-wave"]
    assert merge_reef_wave_telemetry(coordinator, TELEMETRY, telemetry) is True
    assert _data(coordinator, "/mode") == {"mode": "off"}
    assert _data(coordinator, "/wifi")["signal_dBm"] == -45
    # The program is not touched
    assert _data(coordinator, "/auto") == AUTO
    assert merge_reef_wave_telemetry(coordinator, TELEMETRY, "junk") is False
    assert merge_reef_wave_telemetry(_coordinator({}), TELEMETRY, telemetry) is False


def test_feeding_switches_the_mode() -> None:
    """12:30:10 "off", 12:32:10 "auto": each switch pushed at once."""
    coordinator = _coordinator()
    assert merge_reef_wave(coordinator, STATE, _state(mode="off")) is True
    assert _data(coordinator, "/mode")["mode"] == "off"
    assert merge_reef_wave(coordinator, STATE, _state(mode="auto")) is True
    assert _data(coordinator, "/mode")["mode"] == "auto"


def test_settings_merged() -> None:
    coordinator = _coordinator()
    state = _state(device_settings={"shortcut_off_delay": 120})
    assert merge_reef_wave(coordinator, STATE, state) is True
    assert _data(coordinator, "/device-settings") == {"shortcut_off_delay": 120}
    # Nothing polled to merge into
    assert merge_reef_wave(_coordinator({}), STATE, _state(ntp_sync=True)) is True


def test_what_reads_again() -> None:
    # A program written: its intervals are not pushed
    schedule = _state(schedule={"hash": "6bf9720e", "uid": "d5f78158"})
    assert merge_reef_wave(_coordinator(), STATE, schedule) is False
    # Connection, the feeding program, an unknown key
    assert merge_reef_wave(_coordinator(), STATE, CONNECTION) is False
    feeding = _state(scheduled_feeding={"hash": "aa", "setup": True})
    assert merge_reef_wave(_coordinator(), STATE, feeding) is False
    assert merge_reef_wave(_coordinator(), STATE, _state(mode="auto", x=1)) is False
    # A mode or settings with nothing polled, or odd
    assert merge_reef_wave(_coordinator({}), STATE, _state(mode="off")) is False
    assert merge_reef_wave(_coordinator(), STATE, _state(mode=1)) is False
    for settings in ("junk", {"other": 1}):
        state = _state(device_settings=settings)
        assert merge_reef_wave(_coordinator(), STATE, state) is False
    state = _state(device_settings={"shortcut_off_delay": 1})
    assert merge_reef_wave(_coordinator({"/mode": {}}), STATE, state) is False
    assert merge_reef_wave(_coordinator(), STATE, "junk") is False
    assert merge_reef_wave(_coordinator(), STATE, {"other": {}}) is False
