"""Poseidon: crypto, MQTT parsing, ports and the device type table."""

from __future__ import annotations

import socket
from typing import Any

import pytest

from custom_components.redsea.poseidon import const, crypto, mqtt, ports
from tests._poseidon_fakes import SECRET, connect_packet

# ── crypto ──────────────────────────────────────────────────────────────────


def test_crypto_round_trip() -> None:
    payload = {"hwid": "x", "body": {"a": 1}}
    encrypted = crypto.encrypt_payload(payload, SECRET)
    assert "." in encrypted
    assert crypto.decrypt_payload(encrypted, SECRET) == payload
    # A non-JSON text comes back as text
    assert (
        crypto.decrypt_payload(crypto.encrypt_payload("hello", SECRET), SECRET)
        == "hello"
    )


def test_crypto_accepts_unpadded_base64() -> None:
    encrypted = crypto.encrypt_payload({"k": "v"}, SECRET)
    ciphertext, iv = encrypted.split(".")
    assert crypto.decrypt_payload(ciphertext.rstrip("=") + "." + iv, SECRET) == {
        "k": "v"
    }


@pytest.mark.parametrize(
    "encrypted",
    [
        "no-dot",
        "a.b.c",
        # IV of 8 bytes
        "AAAAAAAAAAAAAAAAAAAAAA==.AAAAAAAAAAA=",
        # ciphertext not a multiple of 16
        "AAAA.AAAAAAAAAAAAAAAAAAAAAA==",
    ],
)
def test_crypto_rejects_malformed(encrypted: str) -> None:
    with pytest.raises(ValueError):
        crypto.decrypt_payload(encrypted, SECRET)


def test_crypto_rejects_bad_key() -> None:
    with pytest.raises(ValueError):
        crypto.encrypt_payload({"a": 1}, "short")


# ── MQTT ────────────────────────────────────────────────────────────────────


def test_connect_round_trip_and_split_chunks() -> None:
    packet = connect_packet("reef-wave-083A8D2BE9EC", "pw", "cid")
    parser = mqtt.MqttStreamParser()
    # Arrives in pieces: nothing until it is complete
    assert parser.feed(packet[:1]) == []
    assert parser.feed(packet[1:5]) == []
    frames = parser.feed(packet[5:] + b"\xc0\x00")  # + a PINGREQ
    assert [f.packet_type for f in frames] == [mqtt.PACKET_CONNECT, 12]
    fields = frames[0].parse_connect()
    assert fields == {
        "client_id": "cid",
        "username": "reef-wave-083A8D2BE9EC",
        "password": "pw",
    }
    assert mqtt.hwid_from_username(fields["username"]) == "083a8d2be9ec"


def test_connect_without_credentials_and_with_will() -> None:
    frame = mqtt.MqttStreamParser().feed(mqtt.build_connect_packet("c"))[0]
    assert frame.parse_connect() == {"client_id": "c"}

    def string(value: bytes) -> bytes:
        return len(value).to_bytes(2, "big") + value

    # Will flag, then username: the will topic and message are skipped
    body = (
        b"\x00\x04MQTT\x04"
        + bytes([0x02 | 0x04 | 0x80])
        + b"\x00\x3c"
        + string(b"c")
        + string(b"will/topic")
        + string(b"bye")
        + string(b"reef-run-aabbccddeeff")
    )
    frame = mqtt.MqttFrame(packet_type=1, flags=0, body=body)
    assert frame.parse_connect()["username"] == "reef-run-aabbccddeeff"


@pytest.mark.parametrize(
    "body",
    [
        b"\x00",  # truncated protocol name
        b"\x00\x04MQTT\x04\xc2\x00\x3c\x00\x09short",  # client id longer than the body
        b"\x00\x04MQTT\x04\x02\x00\x3c",  # no room for the client id length
    ],
)
def test_malformed_connect_gives_nothing(body: bytes) -> None:
    assert mqtt.MqttFrame(packet_type=1, flags=0, body=body).parse_connect() == {}


def test_publish_with_and_without_packet_id() -> None:
    topic = b"device/reef-wave/x/state"
    body0 = len(topic).to_bytes(2, "big") + topic + b"payload"
    assert mqtt.MqttFrame(3, 0, body0).parse_publish() == (topic.decode(), b"payload")
    body1 = len(topic).to_bytes(2, "big") + topic + b"\x00\x01" + b"payload"
    frame = mqtt.MqttFrame(3, 0x02, body1)
    assert frame.qos == 1
    assert frame.parse_publish() == (topic.decode(), b"payload")


def test_long_remaining_length() -> None:
    assert mqtt.encode_remaining_length(0) == b"\x00"
    assert mqtt.encode_remaining_length(321) == b"\xc1\x02"
    payload = b"x" * 321
    packet = b"\x30" + mqtt.encode_remaining_length(len(payload)) + payload
    parser = mqtt.MqttStreamParser()
    # Header cut inside the length field
    assert parser.feed(packet[:2]) == []
    frames = parser.feed(packet[2:])
    assert len(frames) == 1 and frames[0].body == payload


def test_corrupt_length_stops_parsing() -> None:
    # Five continuation bytes: not a valid MQTT length, the parser waits
    parser = mqtt.MqttStreamParser()
    assert parser.feed(b"\x30\xff\xff\xff\xff\xff") == []


def test_hwid_from_username() -> None:
    assert mqtt.hwid_from_username("nohyphen") == ""
    assert mqtt.hwid_from_username("reef-lights-AA") == "aa"


# ── ports ───────────────────────────────────────────────────────────────────


def test_port_free_and_taken(socket_enabled: Any) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    sock.listen(1)
    taken = sock.getsockname()[1]
    try:
        assert ports.port_free(taken) is False
    finally:
        sock.close()
    assert ports.port_free(taken) is True


def test_find_free_port_skips_reserved_and_taken(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tried: list[int] = []

    def fake_free(port: int) -> bool:
        tried.append(port)
        return port == 1886

    monkeypatch.setattr(ports, "port_free", fake_free)
    assert ports.find_free_port(1883, 1890) == 1886
    assert 1883 not in tried and tried == [1884, 1885, 1886]
    monkeypatch.setattr(ports, "port_free", lambda port: False)
    assert ports.find_free_port(1884, 1885) is None


def test_local_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSock:
        def __init__(self, fail: bool) -> None:
            self.fail = fail

        def connect(self, addr: Any) -> None:
            if self.fail:
                raise OSError("no route")

        def getsockname(self) -> tuple[str, int]:
            return ("192.0.2.5", 1234)

        def close(self) -> None:
            pass

    monkeypatch.setattr(ports.socket, "socket", lambda *a: FakeSock(False))
    assert ports.local_ip() == "192.0.2.5"
    monkeypatch.setattr(ports.socket, "socket", lambda *a: FakeSock(True))
    assert ports.local_ip() == "127.0.0.1"


# ── device types ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("model", "device_type"),
    [
        ("RSWAVE45", "reef-wave"),
        ("rsled160", "reef-lights"),
        ("RSCONTROL", "reef-control"),
        ("RSATO+", "reef-ato"),
        ("XYZ", ""),
    ],
)
def test_type_from_model(model: str, device_type: str) -> None:
    assert const.type_from_model(model) == device_type
