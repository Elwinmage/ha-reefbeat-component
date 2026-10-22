"""Poseidon watchdog: keys, and the is_alive session served by the relay
itself (real sockets on the loopback)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from custom_components.redsea.poseidon import watchdog
from custom_components.redsea.poseidon.crypto import decrypt_payload, encrypt_payload
from custom_components.redsea.poseidon.mqtt import (
    CONNACK_OK,
    PACKET_PUBLISH,
    PINGRESP,
    MqttFrame,
    MqttStreamParser,
    encode_publish,
    encode_remaining_length,
    encode_string,
)
from custom_components.redsea.poseidon.relay import Relay
from custom_components.redsea.poseidon.watchdog import (
    TOPIC_REQUEST,
    TOPIC_RESPONSE,
    WATCHDOG_USERNAME,
    WatchdogSession,
    generate_key,
    valid_key,
)
from tests._poseidon_fakes import connect_packet

LOCAL = "127.0.0.1"
KEY = "abcdefghij012345"


def _packet(header: int, body: bytes) -> bytes:
    return bytes([header]) + encode_remaining_length(len(body)) + body


def _subscribe(packet_id: bytes, *topics: str) -> bytes:
    body = packet_id + b"".join(encode_string(t) + b"\x00" for t in topics)
    return _packet(0x82, body)


def _publish_qos1(topic: str, packet_id: bytes, payload: bytes) -> bytes:
    return _packet(0x32, encode_string(topic) + packet_id + payload)


def _request(request: Any, key: str = KEY) -> bytes:
    return encrypt_payload(request, key).encode("ascii")


def _answer(request: dict[str, Any]) -> dict[str, Any]:
    return {"id": request["id"], "ok": True, "devices": {}}


def test_keys() -> None:
    key = generate_key()
    assert valid_key(key) and key.isalnum()
    assert generate_key() != key
    assert not valid_key("") and not valid_key("short")
    # Bytes are what count: 16 characters of which one is not ASCII
    assert not valid_key("é" + "a" * 15)


def test_respond() -> None:
    key = KEY
    session = WatchdogSession(lambda: key, _answer)
    response = session.respond(_request({"id": "r1", "minutes": 5}).decode())
    assert response is not None
    assert decrypt_payload(response, KEY) == {"id": "r1", "ok": True, "devices": {}}
    # Not encrypted with the key, or not a request: no answer
    assert session.respond("garbage") is None
    assert session.respond(_request({"id": "r1"}, "x" * 16).decode()) is None
    assert session.respond(_request({"no": "id"}).decode()) is None
    assert session.respond(_request(["a", "list"]).decode()) is None
    # No key set: never answered
    key = ""
    assert session.respond(_request({"id": "r1"}).decode()) is None


async def _read_frames(reader: asyncio.StreamReader, count: int) -> list[MqttFrame]:
    parser = MqttStreamParser()
    frames: list[MqttFrame] = []
    while len(frames) < count:
        data = await asyncio.wait_for(reader.read(1024), 2)
        assert data, f"closed after {frames}"
        frames.extend(parser.feed(data))
    return frames


@pytest.fixture
async def relay(socket_enabled: Any) -> Any:
    relay = Relay(0, upstream_host=LOCAL, upstream_port=1)
    relay.local_handlers[WATCHDOG_USERNAME] = WatchdogSession(lambda: KEY, _answer)
    await relay.async_start()
    yield relay
    await relay.async_stop()


async def test_session_through_the_relay(relay: Relay) -> None:
    reader, writer = await asyncio.open_connection(LOCAL, relay.bound_port)
    # The CONNECT and a SUBSCRIBE in one write: what follows the CONNECT is
    # served too
    writer.write(
        connect_packet(WATCHDOG_USERNAME, "x", "wd")
        + _subscribe(b"\x00\x07", TOPIC_RESPONSE, "other/#")
    )
    await writer.drain()
    connack, suback = await _read_frames(reader, 2)
    assert _packet(0x20, connack.body) == CONNACK_OK
    assert (suback.packet_type, suback.body) == (9, b"\x00\x07\x00\x00")

    # A request at QoS 1: acknowledged, then answered with the same id
    writer.write(_publish_qos1(TOPIC_REQUEST, b"\x01\x02", _request({"id": "r1"})))
    await writer.drain()
    puback, response = await _read_frames(reader, 2)
    assert (puback.packet_type, puback.body) == (4, b"\x01\x02")
    assert response.packet_type == PACKET_PUBLISH
    topic, payload = response.parse_publish()
    assert topic == TOPIC_RESPONSE
    assert decrypt_payload(payload.decode(), KEY)["id"] == "r1"

    # Ignored without an answer: another topic, a request that does not
    # decrypt, a packet type with nothing to say; a ping still answers
    writer.write(
        encode_publish("other/topic", b"{}")
        + encode_publish(TOPIC_REQUEST, b"not encrypted")
        + _packet(0x40, b"\x00\x01")  # PUBACK from the client
        + b"\xc0\x00"  # PINGREQ
    )
    await writer.drain()
    (pong,) = await _read_frames(reader, 1)
    assert _packet(0xD0, pong.body) == PINGRESP

    # DISCONNECT ends the session
    writer.write(b"\xe0\x00")
    await writer.drain()
    assert await asyncio.wait_for(reader.read(1024), 2) == b""
    writer.close()
    # A watchdog is no device: no traffic recorded
    assert relay.traffic == {}


async def test_session_closed_by_the_watchdog(relay: Relay) -> None:
    reader, writer = await asyncio.open_connection(LOCAL, relay.bound_port)
    writer.write(connect_packet(WATCHDOG_USERNAME, client_id="wd"))
    await writer.drain()
    assert await asyncio.wait_for(reader.readexactly(4), 2) == CONNACK_OK
    writer.close()
    await writer.wait_closed()
    await asyncio.sleep(0.05)


async def test_silent_session_times_out(
    relay: Relay, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(watchdog, "IDLE_TIMEOUT_S", 0.05)
    reader, writer = await asyncio.open_connection(LOCAL, relay.bound_port)
    writer.write(connect_packet(WATCHDOG_USERNAME, client_id="wd"))
    await writer.drain()
    assert await asyncio.wait_for(reader.readexactly(4), 2) == CONNACK_OK
    # Closed by the relay once idle
    assert await asyncio.wait_for(reader.read(1024), 2) == b""
    writer.close()
