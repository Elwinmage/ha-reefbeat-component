"""Mergers of pushed states (poseidon/mergers.py), on recorded spy data."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from custom_components.redsea.poseidon import strategy
from custom_components.redsea.poseidon.mergers import merge_reef_power

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "poseidon" / "rspower_spy.json").read_text(
        encoding="utf-8"
    )
)
TOPIC = "device/reef-power/0000aaaa0001/state"


def _coordinator(answers: dict[str, Any] | None = None) -> Any:
    polled: dict[str, Any] = copy.deepcopy(answers or FIXTURE["answers_before"])
    sources = [
        {"name": name, "type": "data", "data": data} for name, data in polled.items()
    ]
    return SimpleNamespace(my_api=SimpleNamespace(data={"sources": sources}))


def _data(coordinator: Any, name: str) -> Any:
    for source in coordinator.my_api.data["sources"]:
        if source["name"] == name:
            return source["data"]
    raise KeyError(name)


def test_registered_for_reef_power() -> None:
    assert strategy.MERGERS["reef-power"] is merge_reef_power
    coordinator = _coordinator()
    assert strategy.merge_state(
        "reef-power", coordinator, TOPIC, FIXTURE["states"][0]["payload"]
    )


def test_recorded_run_gives_the_polled_dashboard() -> None:
    """Every state of the run merged: the sockets read as /dashboard did after."""
    coordinator = _coordinator()
    for state in FIXTURE["states"]:
        merge_reef_power(coordinator, TOPIC, state["payload"])
    after = FIXTURE["dashboard_after"]
    merged = _data(coordinator, "/dashboard")
    assert merged["mode"] == after["mode"] == "auto"
    assert merged["previous_mode"] == after["previous_mode"] == "off"
    for polled in after["sockets"]:
        socket = next(s for s in merged["sockets"] if s["number"] == polled["number"])
        for field in ("name", "mode", "prev_mode", "enabled", "user_config_mode"):
            assert socket[field] == polled[field], (polled["number"], field)
    # Socket 5 went off -> on (toggle) -> schedule, then was renamed
    socket5 = merged["sockets"][5]
    assert (socket5["mode"], socket5["name"]) == ("schedule", "tototest")
    assert _data(coordinator, "/sockets/config")["sockets"][5]["name"] == "tototest"
    assert _data(coordinator, "/socket/5/config/schedule") == {
        "intervals": [{"time": 0, "duration": 839}, {"time": 840, "duration": 241}]
    }
    assert _data(coordinator, "/socket/0/config/schedule") == {"intervals": None}


def test_mode_off_and_back() -> None:
    coordinator = _coordinator()
    assert merge_reef_power(
        coordinator, TOPIC, {"specific_attributes": {"mode": "off"}}
    )
    assert _data(coordinator, "/mode") == {"mode": "off"}
    dashboard = _data(coordinator, "/dashboard")
    assert (dashboard["mode"], dashboard["previous_mode"]) == ("off", "auto")
    merge_reef_power(coordinator, TOPIC, {"specific_attributes": {"mode": "off"}})
    assert dashboard["previous_mode"] == "auto"  # unchanged mode: kept
    merge_reef_power(coordinator, TOPIC, {"specific_attributes": {"mode": "auto"}})
    assert (dashboard["mode"], dashboard["previous_mode"]) == ("auto", "off")


def test_unknown_socket_state_is_not_merged() -> None:
    coordinator = _coordinator()
    dashboard = _data(coordinator, "/dashboard")
    assert dashboard["sockets"][1]["state"] == "standby"
    merge_reef_power(
        coordinator,
        TOPIC,
        {"specific_attributes": {"sockets": {"1": {"state": "unknown"}}}},
    )
    assert dashboard["sockets"][1]["state"] == "standby"
    merge_reef_power(
        coordinator, TOPIC, {"specific_attributes": {"sockets": {"1": {"state": "on"}}}}
    )
    assert dashboard["sockets"][1]["state"] == "on"


def test_config_only_fields_go_to_sockets_config() -> None:
    coordinator = _coordinator()
    merge_reef_power(
        coordinator,
        TOPIC,
        {"specific_attributes": {"sockets": {"2": {"power_detector_enabled": True}}}},
    )
    assert _data(coordinator, "/sockets/config")["sockets"][2]["power_detector_enabled"]
    assert (
        "power_detector_enabled" not in _data(coordinator, "/dashboard")["sockets"][2]
    )


def test_nothing_known_is_not_merged() -> None:
    coordinator = _coordinator()
    assert not merge_reef_power(
        coordinator, TOPIC, {"specific_attributes": {"feed_schedule": None}}
    )
    assert not merge_reef_power(coordinator, TOPIC, {"other": 1})
    assert not merge_reef_power(coordinator, TOPIC, "junk")
    # Bad keys and values are skipped
    assert not merge_reef_power(
        coordinator,
        TOPIC,
        {
            "specific_attributes": {
                "sockets": {"x": {"mode": "on"}, "1": "junk", "9": {"mode": "on"}},
                "schedule": {"1": "junk", "2": {"other": 1}, "9": {"intervals": []}},
            }
        },
    )


def test_sources_not_read_yet() -> None:
    # A device whose config sources were never read: data is ""
    coordinator = _coordinator(
        {"/mode": "", "/dashboard": "", "/socket/1/config/schedule": ""}
    )
    state = {
        "specific_attributes": {
            "mode": "off",
            "sockets": {"1": {"mode": "on"}},
            "schedule": {"1": {"intervals": [{"time": 0, "duration": 5}]}},
        }
    }
    assert merge_reef_power(coordinator, TOPIC, state)
    # Only the schedule could be written: it is its whole answer
    assert _data(coordinator, "/mode") == ""
    assert _data(coordinator, "/socket/1/config/schedule") == {
        "intervals": [{"time": 0, "duration": 5}]
    }
    # The pushed list is copied, not shared
    state["specific_attributes"]["schedule"]["1"]["intervals"].append({})
    assert len(_data(coordinator, "/socket/1/config/schedule")["intervals"]) == 1
    # No API at all
    assert not merge_reef_power(SimpleNamespace(), TOPIC, state)


# -- telemetry and socket states ------------------------------------------------

from datetime import datetime

from custom_components.redsea.poseidon import mergers

TELEMETRY_TOPIC = "device/reef-power/0000aaaa0001/telemetry"


def _replay(monkeypatch: Any) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Replay the recorded run: (ts, merged /dashboard, polled /dashboard) at
    every poll. The coordinator starts from the answers read at the start."""
    coordinator = _coordinator()
    clock = {"now": 0.0}
    monkeypatch.setattr(mergers.time, "monotonic", lambda: clock["now"])
    checks = []
    for event in FIXTURE["events"]:
        clock["now"] = datetime.fromisoformat(event["ts"]).timestamp()
        if event["kind"] == "telemetry":
            mergers.merge_reef_power_telemetry(
                coordinator, TELEMETRY_TOPIC, event["payload"]
            )
        elif event["kind"] == "state":
            merge_reef_power(coordinator, TOPIC, event["payload"])
        else:
            # The socket states move with the clock between two telemetries
            mergers.derive_power_socket_states(coordinator)
            checks.append(
                (
                    event["ts"],
                    copy.deepcopy(_data(coordinator, "/dashboard")),
                    event["payload"],
                )
            )
    return checks


def test_replay_matches_every_polled_dashboard(monkeypatch: Any) -> None:
    """Every value a poll of /dashboard told, the pushed messages told too."""
    checks = _replay(monkeypatch)
    assert len(checks) == 10
    socket_fields = (
        "name",
        "mode",
        "prev_mode",
        "enabled",
        "user_config_mode",
        "state",
    )
    for ts, merged, polled in checks:
        for field in ("mode", "battery_level", "temperature"):
            assert merged[field] == polled[field], (ts, field)
        for polled_socket in polled["sockets"]:
            socket = merged["sockets"][polled_socket["number"]]
            for field in socket_fields:
                assert socket[field] == polled_socket[field], (
                    ts,
                    polled_socket["number"],
                    field,
                )


def test_replay_consumption_follows_the_telemetry(monkeypatch: Any) -> None:
    """The consumption comes every 60 s: a poll right after a change may be
    ahead. Seen once in the run: 10 s after the strip was turned on again,
    the poll read 17.5 W where the last telemetry (strip off) said 0."""
    checks = _replay(monkeypatch)
    # The first poll and the first telemetry came the same second: same value
    ts, merged, polled = checks[0]
    assert merged["sockets"][3]["consumption"] == polled["sockets"][3]["consumption"]
    late = []
    for ts, merged, polled in checks:
        for socket in polled["sockets"]:
            gap = abs(
                merged["sockets"][socket["number"]]["consumption"]
                - socket["consumption"]
            )
            if gap >= 1:
                late.append((ts[11:19], socket["number"]))
    assert late == [("15:06:46", 3)]


def test_telemetry_merge(monkeypatch: Any) -> None:
    coordinator = _coordinator()
    coordinator.my_api.data["sources"].append(
        {"name": "/wifi", "type": "data", "data": {"signal_dBm": -50}}
    )
    telemetry = copy.deepcopy(
        next(e for e in FIXTURE["events"] if e["kind"] == "telemetry")
    )["payload"]
    telemetry["sockets"]["3"]["consumption"] = 42.0
    telemetry["sockets"]["2"]["mode"] = "off"
    telemetry["sockets"]["2"]["prev_mode"] = "on"
    telemetry["battery_level"] = "low"
    assert mergers.merge_reef_power_telemetry(coordinator, TELEMETRY_TOPIC, telemetry)
    dashboard = _data(coordinator, "/dashboard")
    assert dashboard["sockets"][3]["consumption"] == 42.0
    assert (dashboard["sockets"][2]["mode"], dashboard["sockets"][2]["prev_mode"]) == (
        "off",
        "on",
    )
    assert _data(coordinator, "/sockets/config")["sockets"][2]["mode"] == "off"
    assert dashboard["battery_level"] == "low"
    assert _data(coordinator, "/wifi")["signal_dBm"] == telemetry["wifi_signal"]
    assert mergers.device_now(coordinator) is not None
    assert not mergers.merge_reef_power_telemetry(coordinator, TELEMETRY_TOPIC, "junk")


def test_telemetry_with_bad_values() -> None:
    coordinator = _coordinator()
    assert not mergers.merge_reef_power_telemetry(
        SimpleNamespace(), TELEMETRY_TOPIC, {"local_time": "bad"}
    )
    mergers.merge_reef_power_telemetry(
        coordinator,
        TELEMETRY_TOPIC,
        {
            "local_time": 3,
            "sockets": {"x": {}, "1": "junk", "9": {"mode": "on"}},
            "wifi_signal": "?",
        },
    )
    assert mergers.device_now(coordinator) is None


def _clocked(minute: int, intervals: Any, mode: str = "schedule") -> Any:
    coordinator = _coordinator()
    _data(coordinator, "/dashboard")["sockets"][1]["mode"] = mode
    _data(coordinator, "/socket/1/config/schedule")["intervals"] = intervals
    local = datetime.fromisoformat("2026-10-29T00:00:00+02:00").replace(
        hour=minute // 60, minute=minute % 60
    )
    setattr(coordinator, mergers.CLOCK_ATTR, (local, mergers.time.monotonic()))
    return coordinator


def test_socket_state_from_its_schedule() -> None:
    iv = [{"time": 480, "duration": 60}]
    for minute, expected in (
        (479, "standby"),
        (480, "on"),
        (539, "on"),
        (540, "standby"),
    ):
        coordinator = _clocked(minute, iv)
        mergers.derive_power_socket_states(coordinator)
        assert _data(coordinator, "/dashboard")["sockets"][1]["state"] == expected, (
            minute
        )
    # An interval past midnight
    coordinator = _clocked(30, [{"time": 1380, "duration": 120}])
    mergers.derive_power_socket_states(coordinator)
    assert _data(coordinator, "/dashboard")["sockets"][1]["state"] == "on"
    # No interval at all
    coordinator = _clocked(30, None)
    mergers.derive_power_socket_states(coordinator)
    assert _data(coordinator, "/dashboard")["sockets"][1]["state"] == "standby"
    # Not in schedule mode: unknown, as the device tells
    coordinator = _clocked(500, iv, mode="on")
    assert mergers.derive_power_socket_states(coordinator)
    assert _data(coordinator, "/dashboard")["sockets"][1]["state"] == "unknown"


def test_socket_state_left_alone() -> None:
    iv = [{"time": 0, "duration": 1439}]
    # Device turned off: the states are its own business
    coordinator = _clocked(500, iv)
    _data(coordinator, "/dashboard")["mode"] = "off"
    assert not mergers.derive_power_socket_states(coordinator)
    # A socket driven by a sensor or a power detector
    coordinator = _clocked(500, iv)
    _data(coordinator, "/sockets/config")["sockets"][1]["sensor"] = {"type": "temp"}
    mergers.derive_power_socket_states(coordinator)
    assert _data(coordinator, "/dashboard")["sockets"][1]["state"] == "standby"
    # Schedule never read, or no clock yet
    coordinator = _clocked(500, iv)
    _data(coordinator, "/socket/1/config/schedule").clear()
    mergers.derive_power_socket_states(coordinator)
    assert _data(coordinator, "/dashboard")["sockets"][1]["state"] == "standby"
    assert not mergers.derive_power_socket_states(_coordinator())
    # Bad intervals are skipped
    coordinator = _clocked(500, [{"time": "x"}, "junk", {"duration": 3}])
    mergers.derive_power_socket_states(coordinator)
    assert _data(coordinator, "/dashboard")["sockets"][1]["state"] == "standby"


def test_power_fully_pushed() -> None:
    coordinator = _coordinator()
    assert mergers.power_fully_pushed(coordinator)
    assert strategy.fully_pushed("reef-power", coordinator)
    assert not strategy.fully_pushed("reef-wave", coordinator)
    # A temperature probe: its value is not merged yet
    _data(coordinator, "/dashboard")["temperature"] = 25.1
    assert not mergers.power_fully_pushed(coordinator)
    coordinator = _coordinator()
    _data(coordinator, "/sockets/config")["sockets"][4]["power_detector_enabled"] = True
    assert not mergers.power_fully_pushed(coordinator)
    assert not mergers.power_fully_pushed(_coordinator({"/dashboard": ""}))
    assert not mergers.power_fully_pushed(_coordinator({"/dashboard": {"sockets": []}}))


def test_fully_pushed_never_raises(monkeypatch: Any) -> None:
    def _boom(_c: Any) -> bool:
        raise RuntimeError("boom")

    monkeypatch.setitem(strategy.FULLY_PUSHED, "reef-power", _boom)
    assert not strategy.fully_pushed("reef-power", _coordinator())


def test_merge_telemetry_registry() -> None:
    assert strategy.is_telemetry_topic(TELEMETRY_TOPIC)
    assert not strategy.is_telemetry_topic(TOPIC)
    assert not strategy.merge_telemetry(
        "reef-wave", _coordinator(), TELEMETRY_TOPIC, {}
    )
    assert strategy.merge_telemetry(
        "reef-power", _coordinator(), TELEMETRY_TOPIC, {"battery_level": "high"}
    )


def test_comparisons_keep_the_last_telemetry_only() -> None:
    comparisons = strategy.Comparisons()
    written: list[dict[str, Any]] = []
    for value in (1, 2, 3):
        comparisons.add(
            "h", TELEMETRY_TOPIC, {"v": value}, written.append, latest_only=True
        )
    comparisons.add("h", TOPIC, {"s": 1}, written.append)
    comparisons.add("h", TOPIC, {"s": 2}, written.append)
    assert [p.payload for p in comparisons.pending["h"]] == [
        {"v": 3},
        {"s": 1},
        {"s": 2},
    ]


def test_socket_without_number_or_config_is_left_alone() -> None:
    iv = [{"time": 0, "duration": 1440}]
    coordinator = _clocked(600, iv)
    sockets = _data(coordinator, "/dashboard")["sockets"]
    # A socket without a number, one missing from /sockets/config
    sockets.append({"name": "odd", "mode": "schedule", "state": "standby"})
    sockets.append({"number": 99, "mode": "schedule", "state": "standby"})
    assert mergers._socket_driven_elsewhere(coordinator, "1") is True
    assert mergers._socket_driven_elsewhere(coordinator, 99) is True
    mergers.derive_power_socket_states(coordinator)
    assert sockets[-2]["state"] == "standby"
    assert sockets[-1]["state"] == "standby"
