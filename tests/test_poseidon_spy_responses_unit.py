"""Spy file: HTTP answers, origin of the requests, pause, comparisons."""

from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.redsea.poseidon import const, strategy
from custom_components.redsea.poseidon import manager as manager_mod
from custom_components.redsea.poseidon.crypto import encrypt_payload
from custom_components.redsea.poseidon.debug import MASK, http_record, redact
from custom_components.redsea.poseidon.mqtt import (
    MqttFrame,
    encode_publish,
)
from custom_components.redsea.poseidon.relay import UP, Traffic
from custom_components.redsea.reefbeat import api as api_mod
from tests._poseidon_fakes import HWID, SECRET
from tests.test_poseidon_spy_unit import _logs, _poseidon

# -- answers in the spy records ------------------------------------------------


def test_http_record_writes_the_answer_once_until_it_changes() -> None:
    seen: dict[tuple[str, str, str], str] = {}
    req = {"method": "GET", "endpoint": "/dashboard", "response": {"mode": "auto"}}
    first = http_record(HWID, req, seen)
    assert first["response"] == {"mode": "auto"}
    assert "response_unchanged" not in first
    again = http_record(HWID, req, seen)
    assert "response" not in again and again["response_unchanged"] is True
    changed = http_record(HWID, {**req, "response": {"mode": "off"}}, seen)
    assert changed["response"] == {"mode": "off"}
    # Another endpoint, method or device is another answer
    other = http_record(HWID, {**req, "endpoint": "/mode"}, seen)
    assert other["response"] == {"mode": "auto"}
    other_dev = http_record("other", req, seen)
    assert other_dev["response"] == {"mode": "auto"}


def test_http_record_never_writes_the_keys() -> None:
    cloud = http_record(
        HWID,
        {"method": "GET", "endpoint": "/cloud", "response": {"api_key": "K"}},
        {},
    )
    assert "response" not in cloud
    assert cloud["response_omitted"] == "device keys"
    wifi = http_record(
        HWID,
        {
            "method": "GET",
            "endpoint": "/wifi",
            "response": {"ssid": "home", "password": "pw", "nets": [{"psk": "x"}]},
        },
        {},
    )
    assert wifi["response"] == {
        "ssid": "home",
        "password": MASK,
        "nets": [{"psk": MASK}],
    }


def test_http_record_without_answer_or_cache() -> None:
    record = http_record(HWID, {"method": "GET", "endpoint": "/mode"})
    assert "response" not in record and "response_unchanged" not in record
    no_cache = http_record(HWID, {"method": "GET", "endpoint": "/m", "response": 1})
    assert no_cache["response"] == 1
    cloud_failed = http_record(HWID, {"method": "GET", "endpoint": "/cloud"}, {})
    assert "response_omitted" not in cloud_failed


def test_redact() -> None:
    assert redact({"api_secret": "s", "Token_x": "t", "name": "n"}) == {
        "api_secret": MASK,
        "Token_x": MASK,
        "name": "n",
    }
    # Empty secrets stay as they are: telling "no password" is useful
    assert redact({"password": "", "secret": None}) == {
        "password": "",
        "secret": None,
    }
    assert redact([1, "a", {"key": "v"}]) == [1, "a", {"key": "v"}]


async def test_spy_file_gets_the_answers(hass: HomeAssistant) -> None:
    poseidon, _ = _poseidon(hass)
    spy, _ = _logs(poseidon)
    poseidon._apply_polling()
    remove = api_mod.add_http_observer(poseidon._on_http)
    try:
        for _ in range(2):
            api_mod.notify_http(
                "192.0.2.10", "get", "/dashboard", 200, 0.0, response={"a": 1}
            )
        api_mod.notify_http(
            "192.0.2.10", "get", "/cloud", 200, 0.0, response={"api_key": "K"}
        )
    finally:
        remove()
    http = [r for r in spy if r["kind"] == "http"]
    assert http[0]["response"] == {"a": 1}
    assert http[1]["response_unchanged"] is True
    assert "response" not in http[2] and "K" not in str(http[2])
    # A new spy run starts with whole answers again
    poseidon.async_set_strategy(HWID, const.STRATEGY_SHADOW)
    poseidon._apply_polling()
    poseidon.async_set_strategy(HWID, const.STRATEGY_SPY)
    poseidon._apply_polling()
    remove = api_mod.add_http_observer(poseidon._on_http)
    try:
        api_mod.notify_http(
            "192.0.2.10", "get", "/dashboard", 200, 0.0, response={"a": 1}
        )
    finally:
        remove()
    assert [r for r in spy if r["kind"] == "http"][-1]["response"] == {"a": 1}


# -- origin -----------------------------------------------------------------------


def test_http_origin_labels_the_requests_of_a_block() -> None:
    seen: list[dict[str, Any]] = []
    remove = api_mod.add_http_observer(seen.append)
    try:
        api_mod.notify_http("h", "get", "/a", 200, 0.0)
        with api_mod.http_origin("poseidon"):
            api_mod.notify_http("h", "get", "/b", 200, 0.0)
            # An explicit origin wins
            api_mod.notify_http("h", "get", "/c", 200, 0.0, origin="other")
        api_mod.notify_http("h", "get", "/d", 200, 0.0)
    finally:
        remove()
    assert [r["origin"] for r in seen] == [
        "integration",
        "poseidon",
        "other",
        "integration",
    ]
    assert seen[0]["response"] is None


async def test_cloud_reads_of_poseidon_are_labelled(hass: HomeAssistant) -> None:
    poseidon, coordinator = _poseidon(hass)
    seen: list[dict[str, Any]] = []

    async def _fetch(source: str) -> None:
        api_mod.notify_http("192.0.2.10", "get", source, 200, 0.0)

    coordinator.fetch_config = _fetch  # type: ignore[method-assign]
    remove = api_mod.add_http_observer(seen.append)
    try:
        await poseidon._refresh_cloud(coordinator)
        api_mod.notify_http("192.0.2.10", "get", "/mode", 200, 0.0)
    finally:
        remove()
    assert [(r["endpoint"], r["origin"]) for r in seen] == [
        ("/cloud", "poseidon"),
        ("/mode", "integration"),
    ]


# -- pause ------------------------------------------------------------------------


def test_pause_cancels_the_refresh_already_scheduled() -> None:
    class _Coordinator:
        update_interval: timedelta | None = timedelta(seconds=60)
        cancelled = 0

        def _async_unsub_refresh(self) -> None:
            self.cancelled += 1

    control = strategy.PollControl()
    coordinator = _Coordinator()
    control.set(HWID, coordinator, timedelta(minutes=5))
    assert coordinator.cancelled == 0  # a slower poll keeps its next one
    control.set(HWID, coordinator, None)
    assert coordinator.update_interval is None and coordinator.cancelled == 1
    # A coordinator without the helper is left alone
    bare: Any = type("Bare", (), {"update_interval": timedelta(seconds=1)})()
    control.set("other", bare, None)
    assert bare.update_interval is None


# -- comparisons ------------------------------------------------------------------


def test_compare_drops_the_state_wrapper() -> None:
    leaves = [
        ("/dashboard", "sockets.0.mode", "on"),
        ("/sockets/config", "0.name", "Init"),
        ("/dashboard", "mode", "auto"),
    ]
    pushed = {
        "specific_attributes": {
            "sockets": {"0": {"mode": "on", "name": "Other"}},
            "mode": "auto",
            "feed_schedule": None,
        }
    }
    result = {r["path"]: r for r in strategy.compare(pushed, leaves)}
    # Paths are reported as pushed
    mode = result["specific_attributes.sockets.0.mode"]
    assert mode["verdict"] == "same" and "via" not in mode["matches"][0]
    # Matched on a shorter suffix: told
    name = result["specific_attributes.sockets.0.name"]
    assert name["verdict"] == "differs"
    assert name["matches"][0]["via"] == "0.name"
    assert result["specific_attributes.mode"]["verdict"] == "same"
    assert result["specific_attributes.feed_schedule"]["verdict"] == "unknown"


def test_compare_never_matches_a_single_segment_left_over() -> None:
    leaves = [("/x", "mode", "auto")]
    result = strategy.compare({"a": {"b": {"mode": "auto"}}}, leaves)
    # "a.b.mode" may go down to "b.mode", never to "mode" alone
    assert result[0]["verdict"] == "unknown"
    assert strategy.compare({"mode": "auto"}, leaves)[0]["verdict"] == "same"
    assert strategy.compare({"specific_attributes": 1}, leaves) == []


# -- telemetry and safety polling ---------------------------------------------------


def _state_frame(payload: Any, topic: str) -> MqttFrame:
    """A PUBLISH frame of any size (variable remaining length)."""
    packet = encode_publish(topic, encrypt_payload(payload, SECRET).encode())
    index = 1
    while packet[index] & 0x80:
        index += 1
    return MqttFrame(packet[0] >> 4, packet[0] & 0x0F, packet[index + 1 :])


FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "poseidon" / "rspower_spy.json").read_text(
        encoding="utf-8"
    )
)
TELEMETRY = next(e for e in FIXTURE["events"] if e["kind"] == "telemetry")["payload"]
POWER_TOPIC = f"device/reef-power/{HWID}/telemetry"


def _power(hass: HomeAssistant, strategy_name: str) -> tuple[Any, Any, list, list]:
    poseidon, coordinator = _poseidon(
        hass, {const.CONF_DEVICE_STRATEGIES: {HWID: strategy_name}}
    )
    poseidon.keystore.devices[HWID].type = "reef-power"
    cast(Any, coordinator.my_api).data["sources"] = [
        {"name": name, "type": "data", "data": copy.deepcopy(data)}
        for name, data in FIXTURE["answers_before"].items()
    ]
    spy, shadow = _logs(poseidon)
    poseidon._apply_polling()
    return poseidon, coordinator, spy, shadow


def _dashboard(coordinator: Any) -> dict[str, Any]:
    return next(
        s["data"]
        for s in coordinator.my_api.data["sources"]
        if s["name"] == "/dashboard"
    )


def _telemetry(consumption: float) -> dict[str, Any]:
    payload = copy.deepcopy(TELEMETRY)
    payload["sockets"]["3"]["consumption"] = consumption
    return payload


async def test_spy_compares_the_last_telemetry_only(hass: HomeAssistant) -> None:
    poseidon, coordinator, spy, _ = _power(hass, const.STRATEGY_SPY)
    for watts in (1.0, 2.0, 3.0):
        poseidon._on_frame(HWID, UP, _state_frame(_telemetry(watts), POWER_TOPIC))
    # Spy merges nothing
    assert _dashboard(coordinator)["sockets"][3]["consumption"] != 3.0
    coordinator.async_update_listeners()
    compares = [r for r in spy if r["kind"] == "compare"]
    assert len(compares) == 1 and compares[0]["topic"] == POWER_TOPIC
    pushed = {v["path"]: v["pushed"] for v in compares[0]["values"]}
    assert pushed["sockets.3.consumption"] == 3.0


async def test_shadow_merges_the_telemetry(hass: HomeAssistant) -> None:
    poseidon, coordinator, _, shadow = _power(hass, const.STRATEGY_SHADOW)
    poseidon._on_frame(HWID, UP, _state_frame(_telemetry(7.0), POWER_TOPIC))
    assert _dashboard(coordinator)["sockets"][3]["consumption"] == 7.0
    coordinator.async_update_listeners()
    assert shadow[-1]["kind"] == "compare" and shadow[-1]["merged"] is True
    assert shadow[-1]["summary"]["differs"] == 0


async def test_poseidon_merges_the_telemetry_and_polls_hourly(
    hass: HomeAssistant,
) -> None:
    poseidon, coordinator, _, _ = _power(hass, const.STRATEGY_POSEIDON)
    # Every changing value is pushed: a safety poll only
    assert coordinator.update_interval == timedelta(
        minutes=const.DEFAULT_SAFETY_MINUTES
    )
    poseidon._on_frame(HWID, UP, _state_frame(_telemetry(9.0), POWER_TOPIC))
    assert _dashboard(coordinator)["sockets"][3]["consumption"] == 9.0
    assert coordinator.refreshes == []  # a telemetry never asks for a poll
    # A temperature probe appears: back to the reduced polling
    _dashboard(coordinator)["temperature"] = 25.0
    poseidon._apply_polling()
    assert coordinator.update_interval == timedelta(
        minutes=const.DEFAULT_REDUCED_MINUTES
    )


async def test_safety_polling_option(hass: HomeAssistant) -> None:
    poseidon, coordinator, _, _ = _power(hass, const.STRATEGY_POSEIDON)
    hass.config_entries.async_update_entry(
        poseidon.entry,
        options={
            **poseidon.entry.options,
            const.CONF_SAFETY_MINUTES: 240,
            const.CONF_REDUCED_MINUTES: 5,
        },
    )
    poseidon._apply_polling()
    assert coordinator.update_interval == timedelta(minutes=240)
    # Never more often than the reduced polling
    hass.config_entries.async_update_entry(
        poseidon.entry,
        options={
            **poseidon.entry.options,
            const.CONF_SAFETY_MINUTES: 5,
            const.CONF_REDUCED_MINUTES: 30,
        },
    )
    poseidon._apply_polling()
    assert coordinator.update_interval == timedelta(minutes=30)


async def test_telemetry_of_a_family_without_merger(hass: HomeAssistant) -> None:
    poseidon, coordinator = _poseidon(hass)  # reef-wave: no telemetry merger
    spy, _ = _logs(poseidon)
    poseidon._apply_polling()
    topic = f"device/reef-wave/{HWID}/telemetry"
    poseidon._on_frame(HWID, UP, _state_frame({"speed": 1}, topic))
    coordinator.async_update_listeners()
    # Recorded as a frame, never compared
    assert [r["kind"] for r in spy if r["kind"] == "compare"] == []
    # And no comparison for a device out of Poseidon mode
    poseidon._on_telemetry("unknown", topic, {})


async def test_other_topics_are_neither_merged_nor_compared(
    hass: HomeAssistant,
) -> None:
    poseidon, coordinator, _, shadow = _power(hass, const.STRATEGY_SHADOW)
    before = copy.deepcopy(_dashboard(coordinator))
    topic = f"device/reef-power/{HWID}/command-response"
    poseidon._on_frame(HWID, UP, _state_frame(_telemetry(42.0), topic))
    coordinator.async_update_listeners()
    # A command answer is no pushed state: nothing merged, nothing compared
    assert _dashboard(coordinator) == before
    assert [r for r in shadow if r["kind"] == "compare"] == []


# -- /cloud read now and then while the device talks to the relay ------------------


async def test_cloud_read_spaced_while_talking(
    hass: HomeAssistant, monkeypatch: Any
) -> None:
    poseidon, coordinator = _poseidon(hass)
    clock = {"now": 1000.0}
    monkeypatch.setattr(manager_mod.time, "monotonic", lambda: clock["now"])
    # First tick: never read yet
    await poseidon._refresh_tick()
    assert coordinator.fetched == ["/cloud"]
    # Quiet device (no traffic): read on every tick
    clock["now"] += 60
    await poseidon._refresh_tick()
    assert len(coordinator.fetched) == 2
    # Talking to the relay: no more read until the safety interval
    poseidon.relay.traffic[HWID] = Traffic(last_up=dt_util.utcnow())
    assert poseidon.talking(HWID)
    for _ in range(5):
        clock["now"] += 60
        await poseidon._refresh_tick()
    assert len(coordinator.fetched) == 2
    clock["now"] += const.DEFAULT_SAFETY_MINUTES * 60
    poseidon.relay.traffic[HWID] = Traffic(last_down=dt_util.utcnow())
    await poseidon._refresh_tick()
    assert len(coordinator.fetched) == 3
    # Gone quiet for more than TALKING_S: read on the next tick
    clock["now"] += 60
    poseidon.relay.traffic[HWID] = Traffic(
        last_up=dt_util.utcnow() - timedelta(seconds=const.TALKING_S + 1)
    )
    assert not poseidon.talking(HWID)
    await poseidon._refresh_tick()
    assert len(coordinator.fetched) == 4


async def test_not_talking_out_of_poseidon_mode(hass: HomeAssistant) -> None:
    poseidon, coordinator = _poseidon(hass)
    poseidon.relay.traffic[HWID] = Traffic(last_up=dt_util.utcnow())
    coordinator.cloud = {"url": "mqtt.reefbeat.cloud:8883"}
    assert not poseidon.talking(HWID)
    poseidon.relay.traffic[HWID] = Traffic()
    assert not poseidon.talking("unknown")
