"""ReefControl with probes, paired with a ReefControl Power (spy run of
2026-11-02: the probes installed, set up and calibrated in the app)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from custom_components.redsea.poseidon import anomalies as an
from custom_components.redsea.poseidon.mergers import (
    merge_reef_control,
    merge_reef_control_telemetry,
    merge_reef_power,
)
from custom_components.redsea.poseidon.relay import UP
from tests.test_poseidon_mergers_unit import _coordinator as _power_coordinator

FIXTURE = json.loads(
    (
        Path(__file__).parent / "fixtures" / "poseidon" / "rscontrol_probes_spy.json"
    ).read_text(encoding="utf-8")
)
CONTROL = "reef-control"
HWID = FIXTURE["hwid"]
POWER_HWID = FIXTURE["power_hwid"]


def _topic(suffix: str, family: str = CONTROL, hwid: str = HWID) -> str:
    return f"device/{family}/{hwid}/{suffix}"


def _coordinator(dashboard: Any = None) -> Any:
    dashboard = copy.deepcopy(
        FIXTURE["dashboard_before"] if dashboard is None else dashboard
    )
    sources = [
        {"name": "/dashboard", "type": "data", "data": dashboard},
        {"name": "/mode", "type": "data", "data": {"mode": dashboard.get("mode")}},
    ]
    return SimpleNamespace(my_api=SimpleNamespace(data={"sources": sources}))


def _dashboard(coordinator: Any) -> dict[str, Any]:
    return coordinator.my_api.data["sources"][0]["data"]


def _probe(coordinator: Any, probe_type: str) -> dict[str, Any]:
    return next(p for p in _dashboard(coordinator)["probes"] if p["type"] == probe_type)


# -- catalogue -----------------------------------------------------------------------------


def test_recorded_run_has_no_anomaly() -> None:
    for event in FIXTURE["events"]:
        if event["kind"] != "poll":
            topic = _topic(event["kind"])
            assert an.check_frame(CONTROL, UP, 3, topic, event["payload"], HWID) == []
    for state in FIXTURE["states"]:
        found = an.check_frame(CONTROL, UP, 3, _topic("state"), state["payload"], HWID)
        assert found == [], state["ts"]
    for command in FIXTURE["commands"]:
        assert an.check_frame(CONTROL, "down", 3, _topic("command"), command) == []
    for suffix, payload in FIXTURE["other_topics"].items():
        assert an.check_frame(CONTROL, UP, 3, _topic(suffix), payload, HWID) == []
    for state in FIXTURE["power_states"]:
        topic = _topic("state", "reef-power", POWER_HWID)
        assert an.check_frame("reef-power", UP, 3, topic, state["payload"]) == []
    delete = {"method": "DELETE", "url": "/sensor", "body": None}
    topic = _topic("command", "reef-power", POWER_HWID)
    assert an.check_frame("reef-power", "down", 3, topic, delete) == []


def test_unknown_command_and_state_are_told() -> None:
    command = {"method": "POST", "url": "/port/1/install", "body": {"type": "ato"}}
    [found] = an.check_frame(CONTROL, "down", 3, _topic("command"), command)
    assert found.details == ("POST /port/*/install",)
    state = {"specific_attributes": {"buzzer": {"active": True}}}
    [found] = an.check_frame(CONTROL, UP, 3, _topic("state"), state, HWID)
    assert found.details == ("+specific_attributes.buzzer.active:bool",)


# -- telemetry and probe events ------------------------------------------------------------

_CATEGORIES = ("name", "status", "level", "temp_level", "detected", "water_level")
_READINGS = ("value", "ec", "ppt", "sg", "temp_value")


def test_replay_matches_the_polls() -> None:
    """Every poll after the probes were set up, against what the telemetry
    and the probe events told before it."""
    coordinator = _coordinator()
    polls = readings = off = 0
    for event in FIXTURE["events"]:
        payload = event["payload"]
        if event["kind"] == "telemetry":
            merge_reef_control_telemetry(coordinator, _topic("telemetry"), payload)
            continue
        if event["kind"] == "probe":
            assert merge_reef_control(coordinator, _topic("probe"), payload)
            continue
        polls += 1
        merged = {p["uid"]: p for p in _dashboard(coordinator)["probes"]}
        for polled in payload["probes"]:
            probe = merged[polled["uid"]]
            for field in _CATEGORIES:
                assert probe.get(field) == polled.get(field), (event["ts"], field)
            for field in _READINGS:
                if field in polled:
                    readings += 1
                    off += probe.get(field) != polled[field]
    assert polls == 7
    # The readings a poll catches between two telemetries (and an offset
    # changed): a few
    assert off / readings < 0.2


def test_ec_value_is_the_one_of_its_unit() -> None:
    coordinator = _coordinator()
    ec = _probe(coordinator, "ec")
    assert ec["measurement_unit"] == "ppt"
    telemetry = {"probes": [{"type": "ec", "uid": ec["uid"], "ec": 53.0, "ppt": 35.0}]}
    merge_reef_control_telemetry(coordinator, _topic("telemetry"), telemetry)
    assert (ec["ec"], ec["ppt"], ec["value"]) == (53.0, 35.0, 35.0)
    event = {
        "type": "ec",
        "uid": ec["uid"],
        "properties": {"status": "calibration", "value": 30.6, "unit": "ppt"},
    }
    assert merge_reef_control(coordinator, _topic("probe"), event)
    assert (ec["value"], ec["ppt"], ec["status"]) == (30.6, 30.6, "calibration")
    assert "unit" not in ec


def test_ato_level_is_its_water_level() -> None:
    coordinator = _coordinator()
    ato = _probe(coordinator, "ato")
    event = {
        "type": "ato",
        "uid": ato["uid"],
        "properties": {"status": "auto", "temp_value": 23.4, "level": "above"},
    }
    assert merge_reef_control(coordinator, _topic("probe"), event)
    assert ato["water_level"] == "above" and "level" not in ato


def test_probe_not_polled_yet() -> None:
    coordinator = _coordinator()
    before = copy.deepcopy(_dashboard(coordinator))
    # Being installed: its uid is not known yet (0x00000)
    event = {"type": "ph", "uid": "0x00000", "properties": {"status": "setup"}}
    assert not merge_reef_control(coordinator, _topic("probe"), event)
    assert not merge_reef_control(coordinator, _topic("probe"), "junk")
    probe = {"type": "ph", "uid": "0x00000", "properties": "junk"}
    assert not merge_reef_control(coordinator, _topic("probe"), probe)
    telemetry = {"probes": [{"type": "ph", "uid": "0x00000", "value": 8.1}, "junk"]}
    merge_reef_control_telemetry(coordinator, _topic("telemetry"), telemetry)
    assert _dashboard(coordinator) == before
    # No probe polled at all
    coordinator = _coordinator({"mode": "auto", "probes": "junk"})
    assert not merge_reef_control(coordinator, _topic("probe"), event)


# -- states --------------------------------------------------------------------------------


def _state(**fields: Any) -> dict[str, Any]:
    return {"specific_attributes": fields}


def test_link_with_the_power() -> None:
    coordinator = _coordinator()
    link = {"state": "paired_connected", "hwid": POWER_HWID, "internet_connected": True}
    state = _state(cable_connected=True, connected_device=link)
    assert merge_reef_control(coordinator, _topic("state"), state)
    assert _dashboard(coordinator)["connected_device"] == link
    assert merge_reef_control(
        coordinator, _topic("state"), _state(connected_device=None)
    )
    assert _dashboard(coordinator)["connected_device"] is None


def test_states_merged_or_read_again() -> None:
    coordinator = _coordinator()
    # Mode, leak mode
    assert merge_reef_control(coordinator, _topic("state"), _state(mode="auto"))
    assert merge_reef_control(
        coordinator, _topic("state"), _state(leak={"mode": "manual"})
    )
    assert _dashboard(coordinator)["leak"] == {"mode": "manual"}
    # Pushed on connection: nothing polled
    assert merge_reef_control(
        coordinator, _topic("state"), _state(timezone=60, is_factory_reset=False)
    )
    assert merge_reef_control(coordinator, _topic("state"), {"attributes": {}})
    # A probe or a port installed, set up: read again
    for state in (
        _state(probes=[{"type": "ph", "uid": "0x00B39"}]),
        _state(probes_settings=[]),
        _state(ports_settings=[]),
        _state(device_settings={"leak": {"buzzer": True}}),
        _state(mode="auto", ports=[]),
    ):
        assert not merge_reef_control(coordinator, _topic("state"), state)
    assert not merge_reef_control(coordinator, _topic("state"), "junk")
    # Without a leak object polled, its mode cannot be written
    coordinator = _coordinator({"mode": "auto", "probes": []})
    assert not merge_reef_control(
        coordinator, _topic("state"), _state(leak={"mode": "auto"})
    )
    # Nothing polled at all
    empty = SimpleNamespace(my_api=SimpleNamespace(data={"sources": []}))
    assert not merge_reef_control(empty, _topic("state"), _state(mode="auto"))


def test_recorded_states() -> None:
    coordinator = _coordinator()
    verdicts = {
        json.dumps(sorted(s["payload"].get("specific_attributes", {}))): (
            merge_reef_control(coordinator, _topic("state"), s["payload"])
        )
        for s in FIXTURE["states"]
    }
    assert verdicts['["cable_connected", "connected_device"]'] is True
    assert verdicts['["probes"]'] is False
    assert verdicts['["probes_settings"]'] is False


# -- the ReefControl Power -----------------------------------------------------------------


def test_power_linked_and_probe_removed() -> None:
    power = _power_coordinator()
    dashboard = next(
        s["data"] for s in power.my_api.data["sources"] if s["name"] == "/dashboard"
    )
    dashboard["temperature"] = {"value": 25.5, "uid": "0x000F7"}
    topic = _topic("state", "reef-power", POWER_HWID)
    verdicts = [
        merge_reef_power(power, topic, s["payload"]) for s in FIXTURE["power_states"]
    ]
    # The probe removed: merged, nothing left to read
    removed = next(
        i
        for i, s in enumerate(FIXTURE["power_states"])
        if "temperature" in s["payload"].get("specific_attributes", {})
    )
    assert verdicts[removed] is True
    assert dashboard["temperature"] is None
    # Paired with the ReefControl: as /dashboard tells it
    assert dashboard["connected_device"] == {
        "type": "control",
        "hwid": HWID,
        "status": "connected",
        "internet_connected": True,
    }
    # A probe installed: read again
    installed = {
        "specific_attributes": {
            "device_settings": {"temperature": {"uid": "0x000F7"}},
            "temperature": {"is_setup": False, "uid": "0x000F7"},
        }
    }
    assert not merge_reef_power(power, topic, installed)
    set_up = {"specific_attributes": {"device_settings": {"temp_hysteresis": 0.5}}}
    assert not merge_reef_power(power, topic, set_up)
