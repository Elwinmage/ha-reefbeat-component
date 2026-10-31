"""Group topics, events (dosing-log) and the telemetry catalogues of the
ReefMat, ReefLED and ReefWave (poseidon)."""

from __future__ import annotations

import base64
import json
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.redsea.poseidon import anomalies as an
from custom_components.redsea.poseidon import const, strategy
from custom_components.redsea.poseidon.crypto import decode_plain
from custom_components.redsea.poseidon.debug import frame_record
from custom_components.redsea.poseidon.mqtt import MqttFrame, encode_publish
from custom_components.redsea.poseidon.relay import UP
from tests._poseidon_fakes import HWID
from tests.test_poseidon_spy_responses_unit import _state_frame
from tests.test_poseidon_spy_unit import _poseidon

# As sent by a ReefWave of a group (spy run of 2026-10-30)
GROUP_SYNC = "eyJtZXRob2QiOiJwb3N0IiwidXJsIjoiL2dyb3VwL3N5bmMifQAAAAAAAAAAAAAA"
GROUP_TOPIC = "group/reef-wave/00000000-0000-0000-0000-000000000001"

MAT_TELEMETRY = {
    "mode": "auto",
    "active_shortcut": "no_shortcut",
    "roll_level": "full",
    "days_till_end_of_roll": 14,
    "today_usage": 19.2,
    "daily_average_usage": 64.3,
    "total_usage": 2561.9,
    "remaining_length": 936.6,
    "cumulative_steps": 8212,
    "setup_date": "2026-09-12T22:30:15+00:00",
    "material_name": "New Roll",
    "material_start_diameter": 11.1,
    "material_start_length": 3498.5,
    "maxavg_ec_ext": 0,
    "maxavg_ec_int": 0,
    "lifetime_steps": 124933,
    "max_motor_current": 0,
    "local_time": "2026-10-30T08:33:54+01:00",
    "utc_time": "2026-10-30T07:33:54Z",
    "hwid": HWID,
    "wifi_signal": -51,
    "free_heap": 49636,
    "metrics": {"wifi_sig": -49, "ping": 39},
}
LIGHTS_TELEMETRY = {
    "active_shortcut": "no_shortcut",
    "hwid": HWID,
    "intensities": {"white": 0, "blue": 0, "moon": 0},
    "temperature": 18.1,
    "overheat-reduction-factor": 100,
    "fan-speed": 0,
    "active-program": "Perso-1",
    "clouds": 0,
    "acclimation": 100,
    "moonphase": 14,
    "mode": "auto",
    "local_time": "2026-10-30T08:46:26+01:00",
    "utc_time": "2026-10-30T07:46:26Z",
    "wifi_signal": -54,
    "free_heap": 54606,
    "metrics": {"ping": 8},
}
WAVE_TELEMETRY = {
    "mode": "auto",
    "active_shortcut": "no_shortcut",
    "controlling-mode": "reef-beat",
    "uptime": "D:017-H:01-m:41-s:11",
    "active-wave": {"wave_uid": "u", "type": "nw", "name": "No Wave", "st": 0},
    "local_time": "2026-10-30T08:47:10+01:00",
    "utc_time": "2026-10-30T07:47:10Z",
    "hwid": HWID,
    "wifi_signal": -42,
    "free_heap": 51630,
    "metrics": {"ping": -18},
}


def _topic(family: str, suffix: str) -> str:
    return f"device/{family}/{HWID}/{suffix}"


# -- payloads sent in clear -----------------------------------------------------------


def test_decode_plain() -> None:
    assert decode_plain(GROUP_SYNC) == {"method": "post", "url": "/group/sync"}
    text = base64.b64encode(b'{"a": 1}').decode().rstrip("=")
    assert decode_plain(text) == {"a": 1}
    # Encrypted (ciphertext.iv), binary, not an object, empty
    assert decode_plain("abc.def") is None
    assert decode_plain(base64.b64encode(b"\xff\xfe\x00").decode()) is None
    assert decode_plain(base64.b64encode(b"[1, 2]").decode()) is None
    assert decode_plain(base64.b64encode(b"not json").decode()) is None
    assert decode_plain("  ") is None


def test_frame_record_of_a_payload_in_clear() -> None:
    packet = encode_publish(GROUP_TOPIC, GROUP_SYNC.encode())
    record = frame_record(HWID, UP, MqttFrame(3, 0, packet[2:]), "")
    assert record["encrypted"] is False
    assert record["decrypted"] == {"method": "post", "url": "/group/sync"}


# -- topics ------------------------------------------------------------------------------


def test_group_topics() -> None:
    sync = {"method": "post", "url": "/group/sync"}
    for direction in (UP, "down"):
        assert an.check_frame("reef-wave", direction, 3, GROUP_TOPIC, sync) == []
    # Not decoded: nothing to check
    assert an.check_frame("reef-wave", UP, 3, GROUP_TOPIC, None) == []
    other = {"method": "post", "url": "/group/leave", "hwid": HWID}
    [found] = an.check_frame("reef-wave", UP, 3, GROUP_TOPIC, other, HWID)
    assert (found.level, found.topic, found.details) == (
        2,
        "group",
        ("POST /group/leave",),
    )
    assert found.sample["hwid"] == "<…>"


def test_event_topics_are_known() -> None:
    log = {"head": 2, "dose_type": "manual", "volume": 1.03}
    assert (
        an.check_frame("reef-dosing", UP, 3, _topic("reef-dosing", "dosing-log"), log)
        == []
    )


# -- telemetry catalogues ------------------------------------------------------------------


def test_telemetry_catalogues() -> None:
    for family, telemetry in (
        ("reef-mat", MAT_TELEMETRY),
        ("reef-lights", LIGHTS_TELEMETRY),
        ("reef-wave", WAVE_TELEMETRY),
    ):
        topic = _topic(family, "telemetry")
        assert an.check_frame(family, UP, 3, topic, telemetry) == [], family
        # Their states and commands are not checked yet
        assert an.check_frame(family, UP, 3, _topic(family, "state"), {"x": 1}) == []
        command = {"method": "POST", "url": "/anything"}
        assert (
            an.check_frame(family, "down", 3, _topic(family, "command"), command) == []
        )


def test_metrics_after_a_disconnection() -> None:
    # Pushed once after a loss of wifi, broker, internet, or a restart
    for name in ("mqtt_dis", "res", "wifi_dis", "int_dis"):
        telemetry = dict(MAT_TELEMETRY, metrics={"wifi_sig": -50, name: 1})
        topic = _topic("reef-mat", "telemetry")
        assert an.check_frame("reef-mat", UP, 3, topic, telemetry) == [], name
    # A string is not a count
    telemetry = dict(MAT_TELEMETRY, metrics={"int_dis": "1"})
    [found] = an.check_frame(
        "reef-mat", UP, 3, _topic("reef-mat", "telemetry"), telemetry
    )
    assert found.details == ("~metrics.int_dis:str",)


def test_object_of_any_shape_is_still_required() -> None:
    other_channels = dict(LIGHTS_TELEMETRY, intensities={"uv": 1, "violet": 2})
    topic = _topic("reef-lights", "telemetry")
    assert an.check_frame("reef-lights", UP, 3, topic, other_channels) == []
    missing = {k: v for k, v in LIGHTS_TELEMETRY.items() if k != "intensities"}
    [found] = an.check_frame("reef-lights", UP, 3, topic, missing)
    assert found.details == ("-intensities",)


# -- events in the manager -----------------------------------------------------------------


def test_reads_on() -> None:
    assert strategy.reads_on("reef-dosing", _topic("reef-dosing", "dosing-log"))
    assert not strategy.reads_on("reef-dosing", _topic("reef-dosing", "state"))
    assert not strategy.reads_on("reef-wave", _topic("reef-wave", "dosing-log"))


def _dosing(hass: HomeAssistant, strategy_name: str) -> tuple[Any, Any]:
    poseidon, coordinator = _poseidon(
        hass, {const.CONF_DEVICE_STRATEGIES: {HWID: strategy_name}}
    )
    poseidon.keystore.devices[HWID].type = "reef-dosing"
    poseidon._apply_polling()
    return poseidon, coordinator


async def test_dosing_log_reads_the_device_again(hass: HomeAssistant) -> None:
    poseidon, coordinator = _dosing(hass, const.STRATEGY_POSEIDON)
    log = {"head": 2, "dose_type": "manual", "volume": 1.03}
    frame = _state_frame(log, _topic("reef-dosing", "dosing-log"))
    poseidon._on_frame(HWID, UP, frame)
    # Throttled like the pushed states
    poseidon._on_frame(HWID, UP, frame)
    await hass.async_block_till_done()
    assert coordinator.refreshes == [const.PUSH_REFRESH_WAIT_S]
    # Not for a device out of Poseidon mode
    poseidon._on_event("unknown", _topic("reef-dosing", "dosing-log"))


async def test_dosing_log_in_spy_keeps_the_polling(hass: HomeAssistant) -> None:
    poseidon, coordinator = _dosing(hass, const.STRATEGY_SPY)
    log = {"head": 2, "dose_type": "auto", "volume": 12.5}
    poseidon._on_frame(HWID, UP, _state_frame(log, _topic("reef-dosing", "dosing-log")))
    await hass.async_block_till_done()
    assert coordinator.refreshes == []


async def test_group_frames_are_decoded_and_checked(hass: HomeAssistant) -> None:
    poseidon, _ = _poseidon(hass)  # a reef-wave
    poseidon._apply_polling()
    written: list[dict[str, Any]] = []
    poseidon.anomalies.write = written.append
    poseidon.anomalies.search_enabled = lambda: False
    other = base64.b64encode(json.dumps({"method": "post", "url": "/group/x"}).encode())
    for raw in (GROUP_SYNC.encode(), other):
        packet = encode_publish(GROUP_TOPIC, raw)
        poseidon._on_frame(HWID, UP, MqttFrame(3, 0, packet[2:]))
    await hass.async_block_till_done()
    assert [r["details"] for r in written] == [["POST /group/x"]]


async def test_reads_include_the_config_and_none_is_lost(hass: HomeAssistant) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    poseidon, coordinator = _dosing(hass, const.STRATEGY_POSEIDON)
    calls: list[dict[str, Any]] = []

    async def _refresh(**kwargs: Any) -> None:
        calls.append(kwargs)

    coordinator.async_request_refresh = _refresh
    poseidon._read_again(HWID, coordinator)
    # Sooner than PUSH_REFRESH_MIN_S: one more read at the end of the delay,
    # not two
    poseidon._read_again(HWID, coordinator)
    poseidon._read_again(HWID, coordinator)
    await hass.async_block_till_done()
    assert calls == [{"wait": const.PUSH_REFRESH_WAIT_S, "config": True}]
    poseidon._push_refresh[HWID] -= const.PUSH_REFRESH_MIN_S
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=const.PUSH_REFRESH_MIN_S + 1)
    )
    await hass.async_block_till_done()
    assert len(calls) == 2 and not poseidon._pending_reads
    # Stopped: what waits is cancelled
    poseidon._read_again(HWID, coordinator)
    assert poseidon._pending_reads
    await poseidon.async_stop()
    assert not poseidon._pending_reads


async def test_dosers_are_read_again_after_midnight(hass: HomeAssistant) -> None:
    poseidon, _ = _dosing(hass, const.STRATEGY_POSEIDON)
    reads: list[str] = []
    poseidon._read_again = lambda hwid, _c: reads.append(hwid)  # type: ignore[method-assign]
    poseidon._midnight_read()
    assert reads == [HWID]
    # Paused, spy mode, another family, no coordinator: not read
    poseidon.paused.add(HWID)
    poseidon._midnight_read()
    poseidon.paused.discard(HWID)
    poseidon.active[HWID] = const.STRATEGY_SPY
    poseidon._midnight_read()
    poseidon.active[HWID] = const.STRATEGY_POSEIDON
    poseidon.keystore.devices[HWID].type = "reef-wave"
    poseidon._midnight_read()
    poseidon.keystore.devices[HWID].type = "reef-dosing"
    poseidon.coordinator = lambda _hwid: None  # type: ignore[method-assign]
    poseidon._midnight_read()
    assert reads == [HWID]


async def test_midnight_read_is_scheduled(hass: HomeAssistant) -> None:
    from unittest.mock import AsyncMock, patch

    poseidon, _ = _dosing(hass, const.STRATEGY_POSEIDON)
    with (
        patch.object(poseidon, "async_load", AsyncMock()),
        patch.object(poseidon.relay, "async_start", AsyncMock()),
        patch.object(poseidon.relay, "async_stop", AsyncMock()),
        patch(
            "custom_components.redsea.poseidon.manager.async_track_time_change"
        ) as track,
    ):
        await poseidon.async_start()
        kwargs = track.call_args.kwargs
        assert (kwargs["hour"], kwargs["minute"]) == const.MIDNIGHT_READ_AT
        await poseidon.async_stop()
        track.return_value.assert_called_once()
        assert poseidon._unsub_midnight is None
        # Stopped twice
        await poseidon.async_stop()
