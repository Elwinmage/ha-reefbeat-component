"""ReefControl in Poseidon mode: telemetry catalogue and merger (spy run of
2026-11-01, a ReefControl still in setup mode)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from custom_components.redsea.poseidon import anomalies as an
from custom_components.redsea.poseidon import strategy
from custom_components.redsea.poseidon.mergers import merge_reef_control_telemetry
from custom_components.redsea.poseidon.relay import UP

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "poseidon" / "rscontrol_spy.json").read_text(
        encoding="utf-8"
    )
)
CONTROL = "reef-control"
HWID = FIXTURE["hwid"]
TOPIC = f"device/{CONTROL}/{HWID}/telemetry"


def _coordinator(answers: dict[str, Any] | None = None) -> Any:
    polled = copy.deepcopy(FIXTURE["answers_before"] if answers is None else answers)
    sources = [
        {"name": name, "type": "data", "data": data} for name, data in polled.items()
    ]
    return SimpleNamespace(my_api=SimpleNamespace(data={"sources": sources}))


def _data(coordinator: Any, name: str) -> Any:
    return next(
        s["data"] for s in coordinator.my_api.data["sources"] if s["name"] == name
    )


# -- catalogue ---------------------------------------------------------------------------


def test_recorded_telemetry_has_no_anomaly() -> None:
    assert FIXTURE["telemetry"]
    for telemetry in FIXTURE["telemetry"]:
        assert an.check_frame(CONTROL, UP, 3, TOPIC, telemetry, HWID) == []


def test_fields_of_a_probe_are_told() -> None:
    # Not seen yet: the first telemetry with a probe tells its fields
    telemetry = dict(
        FIXTURE["telemetry"][0], probes=[{"uid": "u", "type": "temp", "value": 25.1}]
    )
    [found] = an.check_frame(CONTROL, UP, 3, TOPIC, telemetry, HWID)
    assert found.level == an.LEVEL_TELEMETRY
    assert found.details == (
        "+probes.*.type:str",
        "+probes.*.uid:str",
        "+probes.*.value:number",
    )
    missing = {k: v for k, v in FIXTURE["telemetry"][0].items() if k != "probes"}
    [found] = an.check_frame(CONTROL, UP, 3, TOPIC, missing, HWID)
    assert found.details == ("-probes",)
    # States and commands are not checked yet
    state = f"device/{CONTROL}/{HWID}/state"
    assert an.check_frame(CONTROL, UP, 3, state, {"x": 1}, HWID) == []


# -- merger ------------------------------------------------------------------------------


def test_registered() -> None:
    assert strategy.TELEMETRY_MERGERS[CONTROL] is merge_reef_control_telemetry
    # Every pushed state reads the device again
    assert CONTROL not in strategy.MERGERS
    assert CONTROL not in strategy.FULLY_PUSHED


def test_recorded_telemetry_matches_the_polls() -> None:
    coordinator = _coordinator()
    before = copy.deepcopy(FIXTURE["answers_before"])
    for telemetry in FIXTURE["telemetry"]:
        assert merge_reef_control_telemetry(coordinator, TOPIC, telemetry) is True
    # Only the signal moved, as the next poll of /wifi tells
    assert _data(coordinator, "/dashboard") == before["/dashboard"]
    assert _data(coordinator, "/mode") == before["/mode"]
    wifi = _data(coordinator, "/wifi")
    assert wifi["signal_dBm"] == FIXTURE["telemetry"][-1]["wifi_signal"]
    assert {k: v for k, v in wifi.items() if k != "signal_dBm"} == {
        k: v for k, v in before["/wifi"].items() if k != "signal_dBm"
    }


def test_mode_out_of_setup() -> None:
    coordinator = _coordinator()
    telemetry = dict(FIXTURE["telemetry"][0], mode="auto")
    assert merge_reef_control_telemetry(coordinator, TOPIC, telemetry) is True
    assert _data(coordinator, "/mode")["mode"] == "auto"
    assert _data(coordinator, "/dashboard")["mode"] == "auto"
    # The ports keep theirs: not in the telemetry
    assert {p["mode"] for p in _data(coordinator, "/dashboard")["ports"]} == {"setup"}


def test_nothing_to_merge() -> None:
    assert merge_reef_control_telemetry(_coordinator(), TOPIC, "junk") is False
    assert (
        merge_reef_control_telemetry(_coordinator({}), TOPIC, {"mode": "auto"}) is False
    )
    # A mode that is no string, no signal
    assert (
        merge_reef_control_telemetry(_coordinator(), TOPIC, {"mode": 1, "probes": []})
        is False
    )
