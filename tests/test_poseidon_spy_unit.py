"""Poseidon strategies per device: spy (frames, HTTP, pause), shadow, poseidon."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.poseidon import const, strategy
from custom_components.redsea.poseidon.crypto import encrypt_payload
from custom_components.redsea.poseidon.debug import http_record, mark_record
from custom_components.redsea.poseidon.keystore import DeviceKeys
from custom_components.redsea.poseidon.manager import Poseidon
from custom_components.redsea.poseidon.mqtt import MqttFrame, encode_publish
from custom_components.redsea.poseidon.relay import UP
from custom_components.redsea.reefbeat import api as api_mod
from tests._poseidon_fakes import HWID, SECRET, FakeCoordinator

DOMAIN = "redsea"
RELAY_URL = "192.0.2.1:1884"
STATE_TOPIC = f"device/reef-wave/{HWID}/state"


class PolledCoordinator(FakeCoordinator):
    """A coordinator with what the strategies use."""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.update_interval: timedelta | None = timedelta(seconds=30)
        self.listeners: list[Any] = []
        self.refreshes: list[int] = []
        self.my_api = type("Api", (), {"data": {"sources": []}})()

    def async_add_listener(self, listener: Any) -> Any:
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)

    def async_update_listeners(self) -> None:
        for listener in list(self.listeners):
            listener()

    async def async_request_refresh(self, wait: int = 0, **kwargs: Any) -> None:
        self.refreshes.append(wait)


def _poseidon(
    hass: HomeAssistant, options: dict[str, Any] | None = None, **kwargs: Any
) -> tuple[Poseidon, PolledCoordinator]:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Poseidon",
        unique_id="poseidon",
        data={"poseidon": True, "port": 1884, "host": "192.0.2.1"},
        options=options or {},
    )
    entry.add_to_hass(hass)
    coordinator = PolledCoordinator(cloud={"url": RELAY_URL}, **kwargs)
    hass.data[DOMAIN] = {"dev": coordinator}
    poseidon = Poseidon(hass, entry)
    poseidon.keystore.devices[HWID] = DeviceKeys(
        hwid=HWID, api_key="key", api_secret=SECRET, ip="192.0.2.10", type="reef-wave"
    )
    # The fake messages of the tests are anomalies: never look them up
    poseidon.anomalies.search_enabled = lambda: False
    return poseidon, coordinator


def _logs(poseidon: Poseidon) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    spy: list[dict[str, Any]] = []
    shadow: list[dict[str, Any]] = []
    poseidon.spy_log.write = spy.append  # type: ignore[method-assign]
    poseidon.shadow_log.write = shadow.append  # type: ignore[method-assign]
    return spy, shadow


def _state_frame(payload: Any, topic: str = STATE_TOPIC) -> MqttFrame:
    packet = encode_publish(topic, encrypt_payload(payload, SECRET).encode())
    # Fixed header: type/flags byte, one length byte (short packets)
    return MqttFrame(packet[0] >> 4, packet[0] & 0x0F, packet[2:])


def test_strategy_of(hass: HomeAssistant) -> None:
    poseidon, _ = _poseidon(hass)
    assert poseidon.default_strategy == const.STRATEGY_SPY
    assert poseidon.strategy_of(HWID) == const.STRATEGY_SPY
    # Earlier option values
    poseidon, _ = _poseidon(hass, {const.CONF_STRATEGY: "reduced"})
    assert poseidon.default_strategy == const.STRATEGY_POSEIDON
    poseidon, _ = _poseidon(
        hass,
        {
            const.CONF_STRATEGY: "bogus",
            const.CONF_DEVICE_STRATEGIES: {HWID: "shadow", "bb": "bogus"},
        },
    )
    assert poseidon.strategy_of(HWID) == const.STRATEGY_SHADOW
    assert poseidon.strategy_of("bb") == const.STRATEGY_SPY
    poseidon, _ = _poseidon(hass, {const.CONF_DEVICE_STRATEGIES: "junk"})
    assert poseidon.strategy_of(HWID) == const.STRATEGY_SPY


async def test_set_strategy(hass: HomeAssistant) -> None:
    poseidon, _ = _poseidon(hass, {const.CONF_DEBUG: True})
    poseidon.async_set_strategy(HWID, const.STRATEGY_POSEIDON)
    assert poseidon.entry.options == {
        const.CONF_DEBUG: True,
        const.CONF_DEVICE_STRATEGIES: {HWID: const.STRATEGY_POSEIDON},
    }
    with pytest.raises(ValueError):
        poseidon.async_set_strategy(HWID, "normal")


async def test_spy_records_frames_http_and_comparisons(hass: HomeAssistant) -> None:
    poseidon, coordinator = _poseidon(hass)
    spy, shadow = _logs(poseidon)
    poseidon._apply_polling()
    assert poseidon.active == {HWID: const.STRATEGY_SPY}
    assert spy == [mark_record(HWID, "strategy", "spy") | {"ts": spy[0]["ts"]}]
    assert poseidon.relay.log_frames is True
    assert coordinator.update_interval == timedelta(seconds=30)
    # Every frame both ways, and the pushed state compared at the next poll
    poseidon._on_frame(HWID, UP, _state_frame({"mode": "auto"}))
    poseidon._on_frame(HWID, "down", MqttFrame(13, 0, b""))
    assert [r["kind"] for r in spy[1:]] == ["publish", "control"]
    assert spy[1]["decrypted"] == {"mode": "auto"}
    coordinator.async_update_listeners()
    assert spy[3]["kind"] == "compare" and spy[3]["merged"] is False
    # HTTP requests to the device; other hosts ignored
    api_mod.notify_http("192.0.2.10", "get", "/mode", 200, 0.0)  # no observer yet
    remove = api_mod.add_http_observer(poseidon._on_http)
    try:
        api_mod.notify_http("192.0.2.10", "post", "/mode", 200, 0.0, {"m": 1})
        api_mod.notify_http("192.0.2.99", "get", "/mode", 200, 0.0)
    finally:
        remove()
        remove()  # already removed
    assert len(spy) == 5
    assert spy[4]["kind"] == "http" and spy[4]["method"] == "POST"
    assert spy[4]["endpoint"] == "/mode" and spy[4]["payload"] == {"m": 1}
    assert spy[4]["origin"] == "integration" and spy[4]["hwid"] == HWID
    assert shadow == []


def test_observer_failure_is_contained() -> None:
    def _broken(record: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    remove = api_mod.add_http_observer(_broken)
    try:
        api_mod.notify_http("h", "get", "/x", 0, 0.0)
    finally:
        remove()


def test_http_record() -> None:
    record = http_record(HWID, {"method": "GET", "endpoint": "/mode"})
    assert record["kind"] == "http" and record["direction"] == "HA → DEVICE"


async def test_pause(hass: HomeAssistant) -> None:
    poseidon, coordinator = _poseidon(hass)
    spy, _ = _logs(poseidon)
    with pytest.raises(ValueError):
        poseidon.async_set_paused(HWID, True)  # not active yet
    poseidon._apply_polling()
    poseidon.async_set_paused(HWID, True)
    poseidon.async_set_paused(HWID, True)  # unchanged
    assert coordinator.update_interval is None
    assert spy[-1]["event"] == "poll_paused" and spy[-1]["value"] is True
    # No /cloud read either while paused
    await poseidon._refresh_tick()
    assert coordinator.fetched == []
    poseidon.async_set_paused(HWID, False)
    await hass.async_block_till_done()
    assert coordinator.update_interval == timedelta(seconds=30)
    assert coordinator.refreshes == [0]  # the next poll scheduled again
    # A pause ends with the spy strategy
    poseidon.async_set_paused(HWID, True)
    poseidon.async_set_strategy(HWID, const.STRATEGY_SHADOW)
    poseidon._apply_polling()
    assert poseidon.paused == set()
    assert coordinator.update_interval == timedelta(seconds=30)


async def test_shadow_without_and_with_merger(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    poseidon, coordinator = _poseidon(
        hass, {const.CONF_DEVICE_STRATEGIES: {HWID: const.STRATEGY_SHADOW}}
    )
    spy, shadow = _logs(poseidon)
    poseidon._apply_polling()
    # No frame in the spy file for a shadow device
    poseidon._on_frame(HWID, UP, _state_frame({"mode": "auto"}))
    assert [r["kind"] for r in spy] == ["mark"]
    coordinator.async_update_listeners()
    assert shadow[0]["kind"] == "compare" and shadow[0]["merged"] is False
    # A family with a merger: entities told, the comparison waits for a poll
    merged: list[Any] = []
    monkeypatch.setitem(
        strategy.MERGERS,
        "reef-wave",
        lambda c, topic, payload: merged.append(payload) or True,
    )
    poseidon._on_frame(HWID, UP, _state_frame({"mode": "x"}))
    assert merged == [{"mode": "x"}] and len(shadow) == 1
    coordinator.async_update_listeners()
    assert shadow[1]["merged"] is True
    assert coordinator.update_interval == timedelta(seconds=30)


async def test_poseidon_strategy(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    poseidon, coordinator = _poseidon(
        hass,
        {
            const.CONF_STRATEGY: const.STRATEGY_POSEIDON,
            const.CONF_REDUCED_MINUTES: 7,
        },
    )
    spy, shadow = _logs(poseidon)
    poseidon._apply_polling()
    assert coordinator.update_interval == timedelta(minutes=7)
    # Without a merger, a pushed state refreshes the device (throttled)
    poseidon._on_frame(HWID, UP, _state_frame({"mode": "auto"}))
    poseidon._on_frame(HWID, UP, _state_frame({"mode": "auto"}))
    # Telemetry and frames that do not decrypt trigger nothing
    poseidon._on_frame(
        HWID, UP, _state_frame({"t": 1}, f"device/reef-wave/{HWID}/telemetry")
    )
    packet = encode_publish(STATE_TOPIC, b"not.encrypted-at-all-really")
    poseidon._on_frame(HWID, UP, MqttFrame(3, 0, packet[2:]))
    await hass.async_block_till_done()
    assert coordinator.refreshes == [const.PUSH_REFRESH_WAIT_S]
    # With a merger: no refresh
    monkeypatch.setitem(strategy.MERGERS, "reef-wave", lambda c, t, p: True)
    poseidon._push_refresh.clear()
    poseidon._on_frame(HWID, UP, _state_frame({"mode": "auto"}))
    await hass.async_block_till_done()
    assert coordinator.refreshes == [const.PUSH_REFRESH_WAIT_S]
    assert shadow == [] and [r["kind"] for r in spy] == ["mark"]
    # Back in normal mode: own polling back, listeners gone
    coordinator.cloud = {"url": const.NORMAL_MQTT_URL}
    poseidon._apply_polling()
    assert coordinator.update_interval == timedelta(seconds=30)
    assert coordinator.listeners == [] and poseidon.active == {}
    assert spy[-1]["event"] == "strategy" and spy[-1]["value"] is None


async def test_on_state_ignored(hass: HomeAssistant) -> None:
    poseidon, coordinator = _poseidon(hass)
    # Not in Poseidon mode: nothing done
    poseidon._on_state(HWID, STATE_TOPIC, {"mode": "auto"})
    assert poseidon.comparisons.pending == {}
    poseidon._apply_polling()
    hass.data[DOMAIN] = {}
    poseidon._on_state(HWID, STATE_TOPIC, {"mode": "auto"})
    assert poseidon.comparisons.pending == {}
    # The poll listener of a coordinator gone
    coordinator.async_update_listeners()


async def test_stop_gives_polling_back(hass: HomeAssistant) -> None:
    poseidon, coordinator = _poseidon(hass)
    poseidon.relay.async_start = AsyncMock()  # type: ignore[method-assign]
    poseidon.relay.async_stop = AsyncMock()  # type: ignore[method-assign]
    keys = poseidon.keystore.devices[HWID]
    await poseidon.async_start()
    assert poseidon._unsub_http is not None
    # The keystore was loaded again (empty store)
    poseidon.keystore.devices[HWID] = keys
    poseidon._apply_polling()
    poseidon.async_set_paused(HWID, True)
    await poseidon.async_stop()
    await hass.async_block_till_done()
    assert poseidon._unsub_http is None
    assert coordinator.update_interval == timedelta(seconds=30)
    assert coordinator.refreshes == [0]
    assert coordinator.listeners == [] and poseidon.paused == set()


async def test_entities(hass: HomeAssistant) -> None:
    from types import SimpleNamespace

    from custom_components.redsea.poseidon.switch_entity import (
        PoseidonPollPauseSwitch,
        PoseidonStrategySelect,
        PoseidonSwitch,
    )

    poseidon, _ = _poseidon(hass)
    device: Any = SimpleNamespace(id="dev")
    switch = PoseidonSwitch(poseidon, HWID, device)
    pause = PoseidonPollPauseSwitch(poseidon, HWID, device)
    select = PoseidonStrategySelect(poseidon, HWID, device)
    assert switch.unique_id == f"poseidon_{HWID}"
    assert pause.unique_id == f"poseidon_poll_pause_{HWID}"
    assert select.unique_id == f"poseidon_strategy_{HWID}"
    assert select.options == ["spy", "shadow", "poseidon"]
    assert select.available and select.current_option == "spy"
    # The pause only exists for an active spy device
    assert not pause.available
    poseidon._apply_polling()
    assert pause.available and not pause.is_on
    await pause.async_turn_on()
    assert pause.is_on
    await pause.async_turn_off()
    assert not pause.is_on
    await select.async_select_option("poseidon")
    assert select.current_option == "poseidon"


async def test_entity_adders(hass: HomeAssistant) -> None:
    from homeassistant.helpers import device_registry as dr

    poseidon, _ = _poseidon(hass)
    owner = MockConfigEntry(domain="test", data={})
    owner.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=owner.entry_id, identifiers={(DOMAIN, HWID)}
    )
    switches: list[Any] = []
    selects: list[Any] = []
    poseidon.async_set_switch_adder(switches.append)
    poseidon.async_set_entity_adder("select", selects.append)
    poseidon.async_add_new_switches()
    assert switches == [{HWID: device}] and selects == [{HWID: device}]
    assert poseidon._switched == {HWID}


async def test_device_http_reports_requests(hass: HomeAssistant) -> None:
    import aiohttp

    from custom_components.redsea.poseidon.device_http import DeviceHttp

    class _Resp:
        status = 200

        async def __aenter__(self) -> _Resp:
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def text(self) -> str:
            return "{}"

        async def json(self, content_type: Any = None) -> Any:
            return {}

    class _Session:
        def get(self, url: str) -> Any:
            if url.endswith("/fail"):
                raise aiohttp.ClientError("down")
            return _Resp()

        def post(self, url: str, json: Any = None) -> Any:
            return _Resp()

    seen: list[dict[str, Any]] = []
    remove = api_mod.add_http_observer(seen.append)
    try:
        http = DeviceHttp(_Session(), "192.0.2.10")  # type: ignore[arg-type]
        assert await http.get_json("/cloud") == {}
        assert await http.get_json("/fail") is None
        assert await http.write_json("/cloud/enable", {"api_secret": SECRET})
    finally:
        remove()
    assert [(r["method"], r["endpoint"], r["status"]) for r in seen] == [
        ("GET", "/cloud", 200),
        ("GET", "/fail", 0),
        ("POST", "/cloud/enable", 200),
    ]
    assert {r["origin"] for r in seen} == {"poseidon"}
    # Payloads of Poseidon's own requests carry keys: never reported
    assert all(r["payload"] is None for r in seen)


def test_frame_record_of_a_payload_that_does_not_decrypt() -> None:
    from custom_components.redsea.poseidon.debug import frame_record
    from custom_components.redsea.poseidon.mqtt import MqttStreamParser

    (frame,) = MqttStreamParser().feed(
        encode_publish("reef-wave/state", b"not.base64-at-all-but-long-enough")
    )
    record = frame_record(HWID, UP, frame, SECRET)
    assert record["kind"] == "publish" and record["error"]


def test_debug_log_started_twice(tmp_path: Path) -> None:
    from custom_components.redsea.poseidon.debug import DebugLog

    log = DebugLog(tmp_path / "logs")
    log.start()
    listener = log._listener
    log.start()  # already open: kept as is
    assert log._listener is listener and log.running
    log.write({"kind": "mark"})
    log.stop()
    assert not log.running
    assert (tmp_path / "logs" / "poseidon.jsonl").read_text(encoding="utf-8")
