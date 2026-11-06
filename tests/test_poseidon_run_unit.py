"""ReefRun in Poseidon mode: catalogue, merger and redsea_notification event
(spy runs of 2026-11-03: the skimmer calibrated, then its cup full)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.redsea.poseidon import anomalies as an
from custom_components.redsea.poseidon import const, strategy
from custom_components.redsea.poseidon.events import (
    EVENT_NOTIFICATION,
    notification_event,
)
from custom_components.redsea.poseidon.mergers import (
    merge_reef_run,
    merge_reef_run_telemetry,
)
from custom_components.redsea.poseidon.relay import UP
from tests._poseidon_fakes import HWID as FAKE_HWID
from tests.test_poseidon_spy_responses_unit import _state_frame
from tests.test_poseidon_spy_unit import _poseidon

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "poseidon" / "rsrun_spy.json").read_text(
        encoding="utf-8"
    )
)
RUN = "reef-run"
HWID = FIXTURE["hwid"]
STATE = f"device/{RUN}/{HWID}/state"
TELEMETRY = f"device/{RUN}/{HWID}/telemetry"
FULL_CUP = {"pump": 2, "hwid": HWID, "type": "full_cup_warning", "sub-type": 2}


def _coordinator(answers: dict[str, Any] | None = None) -> Any:
    polled = copy.deepcopy(FIXTURE["answers_before"] if answers is None else answers)
    sources = [
        {"name": name, "type": "data", "data": data} for name, data in polled.items()
    ]
    sources.append(
        {
            "name": "/pump/shortcuts",
            "type": "config",
            "data": {"pump_1": {"emergency": False}, "pump_2": {"emergency": False}},
        }
    )
    return SimpleNamespace(my_api=SimpleNamespace(data={"sources": sources}))


def _data(coordinator: Any, name: str) -> Any:
    return next(
        s["data"] for s in coordinator.my_api.data["sources"] if s["name"] == name
    )


def _state(ts: str) -> dict[str, Any]:
    return next(s["payload"] for s in FIXTURE["states"] if s["ts"] == ts)


def _pumps(state: dict[str, Any], **pump_2: Any) -> dict[str, Any]:
    result = copy.deepcopy(state)
    result["specific_attributes"]["pumps"]["2"].update(pump_2)
    return result


# -- catalogue ---------------------------------------------------------------------------


def test_recorded_run_has_no_anomaly() -> None:
    for state in FIXTURE["states"]:
        assert an.check_frame(RUN, UP, 3, STATE, state["payload"], HWID) == []
    assert an.check_frame(RUN, UP, 3, STATE, FIXTURE["connection"], HWID) == []
    for telemetry in FIXTURE["telemetry"]:
        assert an.check_frame(RUN, UP, 3, TELEMETRY, telemetry["payload"], HWID) == []
    command = f"device/{RUN}/{HWID}/command"
    for method, url in (("POST", "/pump/2/reset-state"), ("PUT", "/v2/pump/settings")):
        message = {"uuid": "u", "method": method, "url": url, "body": {}}
        assert an.check_frame(RUN, "down", 3, command, message) == []
    notification = f"device/{RUN}/{HWID}/notification"
    assert an.check_frame(RUN, UP, 3, notification, FULL_CUP, HWID) == []


def test_new_fields_are_told() -> None:
    telemetry = copy.deepcopy(FIXTURE["telemetry"][0]["payload"])
    telemetry["pumps"]["2"]["flow"] = 1
    [found] = an.check_frame(RUN, UP, 3, TELEMETRY, telemetry, HWID)
    assert found.details == ("+pumps.*.flow:number",)
    message = {"uuid": "u", "method": "POST", "url": "/pump/2/feed", "body": {}}
    [found] = an.check_frame(RUN, "down", 3, f"device/{RUN}/{HWID}/command", message)
    assert (found.kind, found.details) == (an.KIND_COMMAND, ("POST /pump/*/feed",))


# -- merger ------------------------------------------------------------------------------


def test_registered() -> None:
    assert strategy.MERGERS[RUN] is merge_reef_run
    assert strategy.TELEMETRY_MERGERS[RUN] is merge_reef_run_telemetry
    assert strategy.reads_on(RUN, f"device/{RUN}/{HWID}/notification")
    # is_internet_connected is pushed by nothing
    assert RUN not in strategy.FULLY_PUSHED


def test_full_cup_merged_as_polled() -> None:
    """15:07:23 the cup is full: the state, then the telemetry, tell what the
    next poll (15:07:37) does."""
    coordinator = _coordinator()
    assert merge_reef_run(coordinator, STATE, _state("15:07:23")) is True
    telemetry = next(t for t in FIXTURE["telemetry"] if t["ts"] == "15:08:09")
    assert merge_reef_run_telemetry(coordinator, TELEMETRY, telemetry["payload"])
    polled = FIXTURE["answers_after_full_cup"]["/dashboard"]
    dashboard = _data(coordinator, "/dashboard")
    for number in ("pump_1", "pump_2"):
        for field in ("state", "intensity", "missing_pump", "schedule_enabled"):
            assert dashboard[number][field] == polled[number][field], field
    assert dashboard["pump_2"]["state"] == "full-cup"
    # Back to work
    assert merge_reef_run(coordinator, STATE, _state("15:14:23")) is True
    assert dashboard["pump_2"]["state"] == "operational"


def test_intensity_of_a_state_is_not_merged() -> None:
    """The state tells the intensity of the schedule (100), the dashboard the
    real one of a skimmer driven by its EC sensor (35)."""
    coordinator = _coordinator()
    _data(coordinator, "/dashboard")["pump_2"]["intensity"] = 35
    assert merge_reef_run(coordinator, STATE, _state("15:07:23"))
    assert _data(coordinator, "/dashboard")["pump_2"]["intensity"] == 35


def test_schedule_and_settings() -> None:
    coordinator = _coordinator()
    state = _pumps(
        _state("15:07:23"),
        schedule_enabled=False,
        schedule=[{"st": 0, "ti": 91, "pd": 0}],
    )
    assert merge_reef_run(coordinator, STATE, state)
    settings = _data(coordinator, "/pump/settings")
    assert settings["pump_2"]["schedule"] == [{"st": 0, "ti": 91, "pd": 0}]
    assert settings["pump_2"]["schedule_enabled"] is False
    assert _data(coordinator, "/dashboard")["pump_2"]["schedule_enabled"] is False
    # Overskimming threshold changed in the app (16:04)
    settings_state = copy.deepcopy(_state("14:57:53"))
    settings_state["specific_attributes"]["device_settings"]["overskimming"] = {
        "enabled": True,
        "threshold": 60,
    }
    assert merge_reef_run(coordinator, STATE, settings_state)
    assert settings["overskimming"] == {"enabled": True, "threshold": 60}
    assert "overskimming" not in _data(coordinator, "/dashboard")


def test_end_of_a_calibration_reads_again() -> None:
    """14:57-14:58: the skimmer calibrated; its new dates are in
    /calibration, pushed by nothing."""
    coordinator = _coordinator()
    verdicts = {
        s["ts"]: merge_reef_run(coordinator, STATE, s["payload"])
        for s in FIXTURE["states"]
        if s["ts"] < "15:00:00"
    }
    assert verdicts["14:57:37"] is True
    assert _data(coordinator, "/dashboard")["pump_2"]["state"] in (
        "calibration",
        "operational",
    )
    # Out of calibration: read again
    assert verdicts["14:57:59"] is False
    assert verdicts["14:58:03"] is True
    assert verdicts["14:58:26"] is False


def test_telemetry_leaves_a_calibration_to_the_state() -> None:
    coordinator = _coordinator()
    assert merge_reef_run(coordinator, STATE, _state("14:57:37"))
    telemetry = copy.deepcopy(FIXTURE["telemetry"][0]["payload"])
    telemetry["pumps"]["2"]["state"] = "operational"
    telemetry["pumps"]["2"]["temperature"] = 3
    assert merge_reef_run_telemetry(coordinator, TELEMETRY, telemetry)
    pump = _data(coordinator, "/dashboard")["pump_2"]
    assert (pump["state"], pump["temperature"]) == ("calibration", 3)


def test_telemetry_merged() -> None:
    coordinator = _coordinator()
    telemetry = copy.deepcopy(FIXTURE["telemetry"][-1]["payload"])
    telemetry.update(mode="maintenance", wifi_signal=-70)
    telemetry["pumps"]["1"]["intensity"] = 42
    assert merge_reef_run_telemetry(coordinator, TELEMETRY, telemetry)
    assert _data(coordinator, "/mode")["mode"] == "maintenance"
    assert _data(coordinator, "/dashboard")["mode"] == "maintenance"
    assert _data(coordinator, "/dashboard")["pump_1"]["intensity"] == 42
    assert _data(coordinator, "/wifi")["signal_dBm"] == -70


def test_connection_reads_again() -> None:
    coordinator = _coordinator()
    assert merge_reef_run(coordinator, STATE, FIXTURE["connection"]) is False
    # What it told is merged all the same
    shortcuts = FIXTURE["connection"]["specific_attributes"]["shortcuts"]
    assert _data(coordinator, "/pump/shortcuts")["pump_1"] == shortcuts["pump_1"]


def test_what_cannot_be_merged() -> None:
    assert merge_reef_run(_coordinator(), STATE, "junk") is False
    assert merge_reef_run(_coordinator(), STATE, {"attributes": {}}) is False
    assert merge_reef_run_telemetry(_coordinator(), TELEMETRY, "junk") is False
    # Nothing polled yet
    assert merge_reef_run(_coordinator({}), STATE, _state("15:07:23")) is False
    state = _state("14:57:53")
    assert merge_reef_run(_coordinator({}), STATE, state) is False
    assert merge_reef_run(_coordinator({"/dashboard": {}}), STATE, state) is False
    # A pump never polled, an unknown key, a field of a pump nothing knows
    odd = copy.deepcopy(_state("15:07:23"))
    odd["specific_attributes"]["pumps"]["3"] = {"state": "operational"}
    assert merge_reef_run(_coordinator(), STATE, odd) is False
    odd = dict(_state("15:07:23"))
    odd = {"specific_attributes": {**odd["specific_attributes"], "new": 1}}
    assert merge_reef_run(_coordinator(), STATE, odd) is False
    assert (
        merge_reef_run(_coordinator(), STATE, _pumps(_state("15:07:23"), x=1)) is False
    )
    for key in ("pumps", "device_settings", "shortcuts"):
        state = {"specific_attributes": {key: "junk"}}
        assert merge_reef_run(_coordinator(), STATE, state) is False
    no_settings = {
        k: v for k, v in FIXTURE["answers_before"].items() if k != "/pump/settings"
    }
    assert merge_reef_run(_coordinator(no_settings), STATE, _state("15:07:23")) is False
    shortcuts = {"specific_attributes": {"shortcuts": {"pump_9": {}}}}
    assert merge_reef_run(_coordinator(), STATE, shortcuts) is False
    odd_telemetry = {"pumps": {"1": "junk", "9": {"state": "x"}}, "mode": 1}
    assert merge_reef_run_telemetry(_coordinator(), TELEMETRY, odd_telemetry) is False


# -- redsea_notification -----------------------------------------------------------------


def test_notification_event_data() -> None:
    assert notification_event(RUN, FULL_CUP) == {
        "device_type": RUN,
        "pump": 2,
        "type": "full_cup_warning",
        "sub_type": 2,
    }
    leak = {"probe": "Leak", "hwid": "x", "type": "aquarium_water_leak", "sub-type": 1}
    assert notification_event("reef-control", leak) == {
        "device_type": "reef-control",
        "probe": "Leak",
        "type": "aquarium_water_leak",
        "sub_type": 1,
    }
    assert notification_event(RUN, "junk") is None
    assert notification_event(RUN, {"pump": 2}) is None


async def test_notification_fires_the_event(hass: HomeAssistant) -> None:
    poseidon, _ = _poseidon(
        hass, {const.CONF_DEVICE_STRATEGIES: {FAKE_HWID: const.STRATEGY_POSEIDON}}
    )
    poseidon.keystore.devices[FAKE_HWID].type = RUN
    poseidon._apply_polling()
    reads: list[str] = []
    poseidon._read_again = lambda hwid, _c: reads.append(hwid)  # type: ignore[method-assign]
    events: list[Any] = []
    hass.bus.async_listen(EVENT_NOTIFICATION, events.append)
    topic = f"device/{RUN}/{FAKE_HWID}/notification"
    poseidon._on_frame(
        FAKE_HWID, UP, _state_frame(dict(FULL_CUP, hwid=FAKE_HWID), topic)
    )
    await hass.async_block_till_done()
    [event] = events
    assert event.data["type"] == "full_cup_warning"
    assert event.data["pump"] == 2 and event.data["sub_type"] == 2
    assert event.data["device_type"] == RUN
    assert "hwid" not in event.data and "device_id" in event.data and event.data["name"]
    # A pump to reconnect is pushed by nothing else: read again
    assert reads == [FAKE_HWID]
    # Not a notification
    poseidon._fire_notification(FAKE_HWID, RUN, "junk")
    await hass.async_block_till_done()
    assert len(events) == 1
    await poseidon.async_stop()
