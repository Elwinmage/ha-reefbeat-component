"""Guard of a new connection (cloud write commands held back) and the
reconnection of a device that never showed up at the relay (poseidon)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from custom_components.redsea.const import DOMAIN
from custom_components.redsea.poseidon import const
from custom_components.redsea.poseidon import manager as manager_mod
from custom_components.redsea.poseidon.crypto import encrypt_payload
from custom_components.redsea.poseidon.mqtt import (
    MqttFrame,
    MqttStreamParser,
    encode_publish,
)
from custom_components.redsea.poseidon.relay import DOWN, Relay, Traffic
from tests._poseidon_fakes import HWID, SECRET
from tests.test_poseidon_relay_unit import _Sink, _Source
from tests.test_poseidon_spy_unit import RELAY_URL, _logs, _poseidon

COMMAND_TOPIC = f"device/reef-wave/{HWID}/command"
PING = b"\xd0\x00"  # PINGRESP


def _command(method: str, url: str, topic: str = COMMAND_TOPIC) -> bytes:
    body = {"uuid": "u", "hwid": HWID, "method": method, "url": url, "body": None}
    return encode_publish(topic, encrypt_payload(body, SECRET).encode())


def _frame(packet: bytes) -> MqttFrame:
    [frame] = MqttStreamParser().feed(packet)
    return frame


# -- frames on the wire -------------------------------------------------------------


def test_encode_is_the_wire_format() -> None:
    for packet in (
        PING,
        _command("POST", "/auto"),
        b"\x30" + bytes([200, 1]) + b"x" * 200,
    ):
        frames = MqttStreamParser().feed(packet)
        assert b"".join(f.encode() for f in frames) == packet


# -- relay ------------------------------------------------------------------------------


async def test_guard_holds_back_what_the_filter_refuses(monkeypatch: Any) -> None:
    relay = Relay(0)
    seen: list[tuple[str, int]] = []

    def _filter(hwid: str, frame: MqttFrame) -> bool:
        seen.append((hwid, frame.packet_type))
        if frame.packet_type != 3:
            return True
        return b"keep" in frame.body or frame.parse_publish()[0] != COMMAND_TOPIC

    relay.down_filter = _filter
    kept = encode_publish(COMMAND_TOPIC, b"keep")
    dropped = encode_publish(COMMAND_TOPIC, b"drop")
    other = encode_publish(f"device/reef-wave/{HWID}/state", b"x")
    sink = _Sink()
    # The dropped one arrives in two pieces
    source = _Source(kept + dropped[:3], dropped[3:] + PING + other, b"")
    await relay._pump(source, sink, HWID, DOWN, guard_until=1e18)  # type: ignore[arg-type]
    assert sink.data == kept + PING + other
    assert [t for _, t in seen] == [3, 3, 13, 3]


async def test_guard_ends_and_buffered_bytes_are_not_lost(monkeypatch: Any) -> None:
    relay = Relay(0)
    relay.down_filter = lambda hwid, frame: True
    clock = iter([0.0, 100.0, 100.0])
    relay.clock = lambda: next(clock)
    packet = _command("POST", "/auto")
    sink = _Sink()
    # Half a frame under guard, the rest once it ended: piped verbatim
    source = _Source(packet[:5], packet[5:] + PING, b"")
    await relay._pump(source, sink, HWID, DOWN, guard_until=50.0)  # type: ignore[arg-type]
    assert sink.data == packet + PING


async def test_guard_filter_error_forwards() -> None:
    relay = Relay(0)

    def _boom(hwid: str, frame: MqttFrame) -> bool:
        raise RuntimeError("boom")

    relay.down_filter = _boom
    sink = _Sink()
    await relay._pump(_Source(PING, b""), sink, HWID, DOWN, guard_until=1e18)  # type: ignore[arg-type]
    assert sink.data == PING
    # Without a filter, nothing is held back
    relay.down_filter = None
    assert relay._keep(HWID, _frame(PING))


# -- manager: guard -------------------------------------------------------------------


def _guarded(hass: HomeAssistant, options: dict[str, Any] | None = None) -> Any:
    poseidon, _ = _poseidon(hass, options)
    poseidon._apply_polling()
    return poseidon


async def test_write_commands_are_held_back(hass: HomeAssistant) -> None:
    poseidon = _guarded(hass)
    _logs(poseidon)
    spy_writes: list[dict[str, Any]] = []
    poseidon.spy_log.write = spy_writes.append  # type: ignore[method-assign]
    assert poseidon.relay.down_filter == poseidon._guard_down
    assert poseidon._guard_down(HWID, _frame(_command("GET", "/auto")))
    assert not poseidon._guard_down(HWID, _frame(_command("POST", "/mode")))
    assert not poseidon._guard_down(HWID, _frame(_command("put", "/manual")))
    # Encrypted otherwise than usual: unreadable, held back too
    odd = encode_publish(COMMAND_TOPIC, b"SGVsbG8gd29ybGQgZW5jcnlwdGVk")
    assert not poseidon._guard_down(HWID, _frame(odd))
    # What is no command of the cloud passes
    assert poseidon._guard_down(HWID, _frame(PING))
    state = encode_publish(f"device/reef-wave/{HWID}/state", b"x")
    assert poseidon._guard_down(HWID, _frame(state))
    group = encode_publish("group/reef-wave/g/command", b"x")
    assert poseidon._guard_down(HWID, _frame(group))
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"{const.ISSUE_GUARD}_{HWID}")
    assert issue is not None and issue.translation_key == const.ISSUE_GUARD
    placeholders = issue.translation_placeholders or {}
    assert placeholders["count"] == "3"
    assert placeholders["seconds"] == str(int(const.CONNECT_GUARD_S))
    assert "`POST /mode`" in placeholders["commands"]
    assert "`PUT /manual`" in placeholders["commands"]
    assert "(unreadable command)" in placeholders["commands"]
    assert [r["event"] for r in spy_writes] == ["guard_blocked"] * 3
    # Poseidon stopped: the issue goes
    poseidon.async_clear_issues()
    assert (
        ir.async_get(hass).async_get_issue(DOMAIN, f"{const.ISSUE_GUARD}_{HWID}")
        is None
    )


async def test_guard_in_debug_mode_and_unknown_device(hass: HomeAssistant) -> None:
    poseidon = _guarded(hass, {const.CONF_DEBUG: True})
    debug: list[dict[str, Any]] = []
    poseidon.debug_log.write = debug.append  # type: ignore[method-assign]
    assert not poseidon._guard_down("someone", _frame(_command("PUT", "/x")))
    assert [r["value"] for r in debug] == ["(unreadable command)"]


async def test_guard_turned_off(hass: HomeAssistant) -> None:
    poseidon = _guarded(hass, {const.CONF_CONNECT_GUARD: False})
    assert not poseidon.connect_guard
    assert poseidon._guard_down(HWID, _frame(_command("POST", "/auto/init")))


# -- manager: reconnection ------------------------------------------------------------


class _Http:
    def __init__(self, ok: bool = True) -> None:
        self.calls: list[str] = []
        self.ok = ok

    async def set_cloud(self, url: str, api_key: str, api_secret: str) -> bool:
        self.calls.append(url)
        return self.ok


def _absent(
    hass: HomeAssistant, monkeypatch: Any, ok: bool = True
) -> tuple[Any, _Http]:
    poseidon = _guarded(hass)
    http = _Http(ok)
    poseidon.http = lambda ip: http

    async def _no_sleep(_s: float) -> None:
        return None

    monkeypatch.setattr(manager_mod.asyncio, "sleep", _no_sleep)
    poseidon._started_at = dt_util.utcnow() - timedelta(minutes=10)
    return poseidon, http


async def test_never_seen_device_is_made_to_reconnect(
    hass: HomeAssistant, monkeypatch: Any
) -> None:
    poseidon, http = _absent(hass, monkeypatch)
    assert poseidon.in_poseidon(poseidon.cached_cloud(HWID))
    await poseidon._reconnect_absent()
    # Pointed back at Red Sea, then at the relay again
    assert http.calls == [const.NORMAL_MQTT_URL, RELAY_URL]
    # It has RECONNECT_AFTER_S again before the next try
    await poseidon._reconnect_absent()
    assert len(http.calls) == 2
    # At most RECONNECT_MAX tries
    for _ in range(const.RECONNECT_MAX + 1):
        poseidon._switched_at[HWID] = dt_util.utcnow() - timedelta(minutes=10)
        await poseidon._reconnect_absent()
    assert len(http.calls) == 2 * const.RECONNECT_MAX
    # It showed up: counted from scratch
    poseidon.relay.traffic[HWID] = Traffic(last_up=dt_util.utcnow())
    await poseidon._reconnect_absent()
    assert HWID not in poseidon._reconnects


async def test_reconnection_that_fails(hass: HomeAssistant, monkeypatch: Any) -> None:
    poseidon, http = _absent(hass, monkeypatch, ok=False)
    await poseidon._reconnect_absent()
    # Not reachable: not pointed at the relay a second time
    assert http.calls == [const.NORMAL_MQTT_URL]
    assert poseidon._reconnects[HWID] == 1


async def test_no_reconnection_when_not_due(
    hass: HomeAssistant, monkeypatch: Any
) -> None:
    poseidon, http = _absent(hass, monkeypatch)
    # Just switched: it has RECONNECT_AFTER_S
    poseidon._switched_at[HWID] = dt_util.utcnow()
    await poseidon._reconnect_absent()
    # Paused, or out of Poseidon mode: left alone
    poseidon._switched_at.clear()
    poseidon.paused.add(HWID)
    await poseidon._reconnect_absent()
    poseidon.paused.clear()
    monkeypatch.setattr(poseidon, "in_poseidon", lambda cloud: False)
    await poseidon._reconnect_absent()
    assert http.calls == []
    # The refresh tick does it
    monkeypatch.undo()


async def test_switch_restarts_the_wait(hass: HomeAssistant, monkeypatch: Any) -> None:
    poseidon, _ = _absent(hass, monkeypatch)
    poseidon._reconnects[HWID] = 2
    monkeypatch.setattr(poseidon, "device_keys", lambda c: poseidon.keystore.get(HWID))
    monkeypatch.setattr(poseidon, "_refresh_cloud", _noop)
    assert await poseidon.async_switch(HWID, True)
    assert HWID in poseidon._switched_at and HWID not in poseidon._reconnects


async def _noop(*args: Any) -> None:
    return None


async def test_known_restores_raise_no_issue(hass: HomeAssistant) -> None:
    poseidon = _guarded(hass)  # a reef-wave
    marks: list[dict[str, Any]] = []
    poseidon.spy_log.write = marks.append  # type: ignore[method-assign]
    restore = ("/group", "/auto/init", "/auto", "/auto/complete", "/auto/apply")
    for url in restore:
        assert not poseidon._guard_down(HWID, _frame(_command("POST", url)))
    issue_id = f"{const.ISSUE_GUARD}_{HWID}"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    assert [m["known_restore"] for m in marks] == [True] * len(restore)
    # What it would have written is kept in the mark
    assert marks[0]["command"]["url"] == "/group"
    # Another family: the same URL is no known restore
    poseidon.keystore.devices[HWID].type = "reef-dosing"
    assert not poseidon._guard_down(HWID, _frame(_command("POST", "/auto")))
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
    assert not poseidon._guard_down(HWID, _frame(_command("POST", "/food-head")))
    assert poseidon._guarded[HWID] == ["POST /auto"]
