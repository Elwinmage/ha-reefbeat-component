"""A socket of a ReefControl Power removed, a 12V port of the ReefControl
installed and scheduled in the app (spy run of 2026-11-02 21:14-21:23)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from custom_components.redsea.poseidon import anomalies as an
from custom_components.redsea.poseidon.mergers import (
    merge_reef_control,
    merge_reef_power,
    merge_reef_power_telemetry,
)
from custom_components.redsea.poseidon.relay import UP

FIXTURE = json.loads(
    (
        Path(__file__).parent / "fixtures" / "poseidon" / "rscontrol_ports_spy.json"
    ).read_text(encoding="utf-8")
)
HWID = FIXTURE["hwid"]
POWER_HWID = FIXTURE["power_hwid"]
CONTROL = FIXTURE["control"]
POWER = FIXTURE["power"]


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


def _topic(family: str, hwid: str, suffix: str) -> str:
    return f"device/{family}/{hwid}/{suffix}"


def test_recorded_run_has_no_anomaly() -> None:
    for family, hwid, side in (
        ("reef-control", HWID, CONTROL),
        ("reef-power", POWER_HWID, POWER),
    ):
        for state in side["states"]:
            topic = _topic(family, hwid, "state")
            assert an.check_frame(family, UP, 3, topic, state["payload"], hwid) == []
        for command in side["commands"]:
            topic = _topic(family, hwid, "command")
            assert an.check_frame(family, "down", 3, topic, command) == [], command
    for telemetry in POWER["telemetry"]:
        topic = _topic("reef-power", POWER_HWID, "telemetry")
        assert an.check_frame("reef-power", UP, 3, topic, telemetry, POWER_HWID) == []


def test_port_installed_then_set_up() -> None:
    coordinator = _coordinator(CONTROL["before"])
    topic = _topic("reef-control", HWID, "state")
    verdicts = [
        merge_reef_control(coordinator, topic, state["payload"])
        for state in CONTROL["states"]
    ]
    # Installed (another type than polled): read again; then its settings
    # and its mode, merged once read again
    assert verdicts[0] is False
    coordinator = _coordinator(
        {
            "/dashboard": CONTROL["after"]["/dashboard"],
            "/ports/config": CONTROL["before"]["/ports/config"],
        }
    )
    _data(coordinator, "/dashboard")["ports"][0].update(
        {"name": "S1", "mode": "off", "state": "unknown", "user_config_mode": "off"}
    )
    _data(coordinator, "/ports/config")[0]["type"] = "other"
    for state in CONTROL["states"]:
        merge_reef_control(coordinator, topic, state["payload"])
    port = _data(coordinator, "/dashboard")["ports"][0]
    polled = CONTROL["after"]["/dashboard"]["ports"][0]
    for field in ("name", "mode", "state", "user_config_mode", "type"):
        assert port[field] == polled[field], field
    configured = _data(coordinator, "/ports/config")[0]
    assert (configured["name"], configured["user_config_mode"]) == (
        polled["name"],
        "schedule",
    )


def test_port_without_config_polled() -> None:
    coordinator = _coordinator({"/dashboard": CONTROL["after"]["/dashboard"]})
    state = {
        "specific_attributes": {
            "ports_settings": [
                {"type": "other", "name": "Led", "number": 0, "enabled": True},
                "junk",
            ]
        }
    }
    topic = _topic("reef-control", HWID, "state")
    assert merge_reef_control(coordinator, topic, state)
    assert _data(coordinator, "/dashboard")["ports"][0]["name"] == "Led"


def test_socket_removed_from_the_power() -> None:
    # Its sockets as /sockets/config tells them: driven by nothing else
    pushed = next(
        s["payload"]["specific_attributes"]["sockets"]
        for s in POWER["states"]
        if "sockets" in s["payload"]["specific_attributes"]
    )
    config = {
        "sockets": [
            {"number": int(n), "power_detector_enabled": False, "sensor": None}
            for n in pushed
        ]
    }
    coordinator = _coordinator({**POWER["before"], "/sockets/config": config})
    topic = _topic("reef-power", POWER_HWID, "state")
    for state in POWER["states"]:
        merge_reef_power(coordinator, topic, state["payload"])
    telemetry_topic = _topic("reef-power", POWER_HWID, "telemetry")
    for telemetry in POWER["telemetry"]:
        merge_reef_power_telemetry(coordinator, telemetry_topic, telemetry)
    socket = _data(coordinator, "/dashboard")["sockets"][1]
    polled = POWER["after"]["/dashboard"]["sockets"][1]
    for field in ("name", "mode", "prev_mode", "user_config_mode", "state"):
        assert socket[field] == polled[field], field
    # null pushed for a socket in setup mode, 0 polled
    assert POWER["telemetry"][0]["sockets"]["1"]["consumption"] is None
    assert socket["consumption"] == polled["consumption"] == 0


def test_port_switched_by_its_schedule() -> None:
    """At 23:00:00 the schedule of the port switched it on: a state, the
    next poll (23:00:41) telling the same; its consumption is pushed by
    nothing."""
    coordinator = _coordinator(
        {
            "/dashboard": CONTROL["after"]["/dashboard"],
            "/ports/config": CONTROL["before"]["/ports/config"],
        }
    )
    state = {
        "specific_attributes": {
            "ports": [
                {
                    "type": "other",
                    "number": 0,
                    "is_setup": True,
                    "mode": "schedule",
                    "state": "on",
                    "last_installation_date": 1793654332,
                },
                {"type": "unknown", "number": 1, "last_installation_date": None},
            ]
        }
    }
    topic = _topic("reef-control", HWID, "state")
    assert an.check_frame("reef-control", UP, 3, topic, state, HWID) == []
    assert merge_reef_control(coordinator, topic, state)
    port = _data(coordinator, "/dashboard")["ports"][0]
    assert (port["mode"], port["state"]) == ("schedule", "on")
