"""ReefDose: catalogue and mergers of its pushed messages (poseidon)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from custom_components.redsea.poseidon import anomalies as an
from custom_components.redsea.poseidon import strategy
from custom_components.redsea.poseidon.mergers import (
    merge_reef_dosing,
    merge_reef_dosing_telemetry,
)
from custom_components.redsea.poseidon.relay import UP

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "poseidon" / "rsdose_spy.json").read_text(
        encoding="utf-8"
    )
)
HWID = FIXTURE["hwid"]
DOSING = "reef-dosing"


def _coordinator(answers: dict[str, Any] | None = None) -> Any:
    polled: dict[str, Any] = copy.deepcopy(
        FIXTURE["answers_before"] if answers is None else answers
    )
    sources = [
        {"name": name, "type": "data", "data": data} for name, data in polled.items()
    ]
    return SimpleNamespace(my_api=SimpleNamespace(data={"sources": sources}))


def _data(coordinator: Any, name: str) -> Any:
    return next(
        s["data"] for s in coordinator.my_api.data["sources"] if s["name"] == name
    )


def _answers(coordinator: Any) -> dict[str, Any]:
    return {s["name"]: s["data"] for s in coordinator.my_api.data["sources"]}


def _topic(suffix: str) -> str:
    return f"device/{DOSING}/{HWID}/{suffix}"


# -- catalogue ------------------------------------------------------------------------


def test_recorded_run_has_no_anomaly() -> None:
    for state in FIXTURE["states"]:
        assert an.check_frame(DOSING, UP, 3, _topic("state"), state, HWID) == []
    for telemetry in FIXTURE["telemetry"]:
        assert an.check_frame(DOSING, UP, 3, _topic("telemetry"), telemetry) == []
    for command in FIXTURE["commands"]:
        direction = UP if command["kind"] == "command-response" else "down"
        topic = _topic(command["kind"])
        assert an.check_frame(DOSING, direction, 3, topic, command["payload"]) == []


def test_new_firmware_task_is_no_anomaly() -> None:
    telemetry = copy.deepcopy(FIXTURE["telemetry"][0])
    telemetry["task_watermark"]["NewTask"] = 1000
    assert an.check_frame(DOSING, UP, 3, _topic("telemetry"), telemetry) == []
    telemetry["heads"]["1"]["new_counter"] = 1
    [found] = an.check_frame(DOSING, UP, 3, _topic("telemetry"), telemetry)
    assert found.details == ("+heads.*.new_counter:number",)


def test_unknown_dosing_command() -> None:
    command = {"method": "POST", "url": "/head/2/manual", "body": {"volume": 1}}
    [found] = an.check_frame(DOSING, "down", 3, _topic("command"), command)
    assert found.details == ("POST /head/*/manual",)


def test_rolling_log_topic_is_known() -> None:
    log = {"length": 0.7, "advance_cause": "ec_sensor"}
    topic = "device/reef-mat/0000aaaa0003/rolling-log"
    assert an.check_frame("reef-mat", UP, 3, topic, log) == []


# -- telemetry --------------------------------------------------------------------------


def test_registered() -> None:
    assert strategy.MERGERS[DOSING] is merge_reef_dosing
    assert strategy.TELEMETRY_MERGERS[DOSING] is merge_reef_dosing_telemetry
    # The dosing queue is pushed by nothing
    assert DOSING not in strategy.FULLY_PUSHED


def test_recorded_telemetry_matches_the_polls() -> None:
    coordinator = _coordinator()
    before = copy.deepcopy(_answers(coordinator))
    for telemetry in FIXTURE["telemetry"]:
        assert merge_reef_dosing_telemetry(coordinator, "", telemetry) is True
    after = _answers(coordinator)
    # Nothing was dosed during the run: the merged sources are the polled
    # ones (rounding included), but for the wifi signal
    before["/wifi"] = after["/wifi"]
    assert after == before


def test_telemetry_of_a_dose() -> None:
    coordinator = _coordinator()
    telemetry = copy.deepcopy(FIXTURE["telemetry"][-1])
    head = telemetry["heads"]["2"]
    head.update(
        auto_dosed_today=74.99812,
        manual_dosed_today=1.04,
        doses_today=6,
        container_volume=562.5627,
        remaining_days=2,
        stock_level="low",
        missed_dose={"missed_volume": 12.5, "total_volume": 12.5},
    )
    telemetry["mode"] = "maintenance"
    telemetry["wifi_signal"] = -70
    assert merge_reef_dosing_telemetry(coordinator, "", telemetry) is True
    dashboard = _data(coordinator, "/dashboard")["heads"]["2"]
    assert dashboard["auto_dosed_today"] == 75.0
    assert dashboard["manual_dosed_today"] == 1.0
    assert dashboard["doses_today"] == 6
    assert dashboard["remaining_days"] == 2
    assert dashboard["missed_dose"] == {"missed_volume": 12.5, "total_volume": 12.5}
    settings = _data(coordinator, "/head/2/settings")
    assert settings["container_volume"] == 562.5627
    assert settings["today_auto_dosed_volume"] == 75.0
    assert _data(coordinator, "/mode")["mode"] == "maintenance"
    assert _data(coordinator, "/wifi")["signal_dBm"] == -70
    # The pushed message is not shared with the cache
    head["missed_dose"]["missed_volume"] = 0
    assert dashboard["missed_dose"]["missed_volume"] == 12.5


def test_telemetry_without_anything_polled() -> None:
    assert merge_reef_dosing_telemetry(_coordinator({}), "", {"heads": {}}) is False
    assert merge_reef_dosing_telemetry(_coordinator(), "", "junk") is False
    odd = {"heads": {"1": "junk", "9": {"auto_dosed_today": 1}}, "wifi_signal": "x"}
    assert merge_reef_dosing_telemetry(_coordinator(), "", odd) is False
    # Nothing to round in what is no number
    coordinator = _coordinator()
    merge_reef_dosing_telemetry(
        coordinator, "", {"heads": {"1": {"auto_dosed_today": None}}}
    )
    assert _data(coordinator, "/dashboard")["heads"]["1"]["auto_dosed_today"] is None


# -- states -------------------------------------------------------------------------------


def test_recorded_states_match_the_polls() -> None:
    coordinator = _coordinator()
    before = copy.deepcopy(_answers(coordinator))
    full, battery, settings, timezone = FIXTURE["states"]
    # Its heads tell their schedules without their intervals: merged, and
    # read again all the same
    assert merge_reef_dosing(coordinator, "", full) is False
    assert merge_reef_dosing(coordinator, "", battery) is True
    assert merge_reef_dosing(coordinator, "", settings) is True
    # Only what nothing polls: read again (poseidon strategy)
    assert merge_reef_dosing(coordinator, "", timezone) is False
    assert _answers(coordinator) == before


def test_state_of_new_settings() -> None:
    coordinator = _coordinator()
    pushed = {
        "specific_attributes": {
            "mode": "off",
            "battery_level": "low",
            "stock_alert_days": 7,
            "device_settings": {"shortcut_off_delay": 30, "bundled_heads": True},
            "heads": {
                "3": {
                    "state": "off",
                    "show": False,
                    "supplement": {"name": "Other", "short_name": "O"},
                },
                "x": "junk",
            },
        }
    }
    assert merge_reef_dosing(coordinator, "", pushed) is True
    assert _data(coordinator, "/mode")["mode"] == "off"
    dashboard = _data(coordinator, "/dashboard")
    assert dashboard["battery_level"] == "low" and dashboard["bundled_heads"] is True
    assert dashboard["heads"]["3"]["state"] == "off"
    device = _data(coordinator, "/device-settings")
    assert device["stock_alert_days"] == 7 and device["shortcut_off_delay"] == 30
    head = _data(coordinator, "/head/3/settings")
    assert head["state"] == "off" and head["show"] is False
    # Only the pushed fields of the supplement change
    assert head["supplement"]["name"] == "Other"
    assert head["supplement"]["uid"] == "f524734e-8651-496e-b09b-640b40fc8bab"


def test_new_schedule_is_read_again() -> None:
    for change in ({"dd": 25}, {"nd": 4}, {"schedule_type": "single"}, {"days": [1]}):
        coordinator = _coordinator()
        head = {"state": "on", **change}
        pushed = {"specific_attributes": {"heads": {"1": head}}}
        assert merge_reef_dosing(coordinator, "", pushed) is False, change
        # What can be merged still is
        assert _data(coordinator, "/dashboard")["heads"]["1"]["state"] == "on"


def test_schedule_never_read() -> None:
    answers = copy.deepcopy(FIXTURE["answers_before"])
    del answers["/head/1/settings"]["schedule"]
    pushed = {"specific_attributes": {"heads": {"1": {"dd": 20.7}}}}
    assert merge_reef_dosing(_coordinator(answers), "", pushed) is False
    # A supplement in a settings never read
    answers["/head/1/settings"].pop("supplement")
    coordinator = _coordinator(answers)
    pushed = {"specific_attributes": {"heads": {"1": {"supplement": {"uid": "u"}}}}}
    assert merge_reef_dosing(coordinator, "", pushed) is True
    assert _data(coordinator, "/head/1/settings")["supplement"] == {"uid": "u"}


def test_state_without_anything_polled() -> None:
    assert merge_reef_dosing(_coordinator(), "", "junk") is False
    assert merge_reef_dosing(_coordinator(), "", {"specific_attributes": 1}) is False
    pushed = {"specific_attributes": {"mode": "auto", "heads": {"1": {"state": "on"}}}}
    assert merge_reef_dosing(_coordinator({}), "", pushed) is False


def test_an_interval_moved_is_read_again() -> None:
    # Same type, dose, number of doses and days as polled: only the intervals
    # moved, which no state tells
    coordinator = _coordinator()
    settings = _data(coordinator, "/head/1/settings")
    schedule = settings["schedule"]
    head = {
        "schedule_type": schedule["type"],
        "dd": schedule["dd"],
        "days": schedule["days"],
        "nd": _data(coordinator, "/dashboard")["heads"]["1"]["daily_doses"],
    }
    pushed = {"specific_attributes": {"heads": {"1": head}}}
    assert merge_reef_dosing(coordinator, "", pushed) is False


def test_unknown_fields_are_read_again() -> None:
    for pushed in (
        {"specific_attributes": {"mode": "auto", "new_setting": 1}},
        {"specific_attributes": {"mode": "auto", "device_settings": {"other": 1}}},
        {"specific_attributes": {"heads": {"1": {"state": "on", "other": 1}}}},
    ):
        coordinator = _coordinator()
        assert merge_reef_dosing(coordinator, "", pushed) is False, pushed
    # What is known to tell nothing polled is no reason to read again
    pushed = {"specific_attributes": {"mode": "auto", "ntp_sync": True}}
    assert merge_reef_dosing(_coordinator(), "", pushed) is True
