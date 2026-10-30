"""Just enough MQTT 3.1.1 to follow a device connection.

The relay forwards the bytes untouched; this only parses a copy, so a
malformed frame can never break the tunnel. Ported from
``reefbeat_god_mode.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

PACKET_CONNECT = 1
PACKET_PUBLISH = 3


@dataclass
class MqttFrame:
    """One decoded MQTT control packet."""

    packet_type: int
    flags: int
    body: bytes

    @property
    def qos(self) -> int:
        return (self.flags >> 1) & 0x03

    def encode(self) -> bytes:
        """The packet as sent on the wire."""
        return (
            bytes([(self.packet_type << 4) | self.flags])
            + encode_remaining_length(len(self.body))
            + self.body
        )

    def parse_publish(self) -> tuple[str, bytes]:
        """Split a PUBLISH body into (topic, payload)."""
        topic_len = int.from_bytes(self.body[0:2], "big")
        topic = self.body[2 : 2 + topic_len].decode("utf-8", errors="replace")
        offset = 2 + topic_len
        if self.qos > 0:
            offset += 2  # packet identifier
        return topic, self.body[offset:]

    def parse_connect(self) -> dict[str, str]:
        """Identity fields of a CONNECT: client_id, username, password.

        A device logs in as ``<type>-<hwid>`` with its ``api_key`` as
        password.
        """
        body = self.body
        try:
            proto_len = int.from_bytes(body[0:2], "big")
            offset = 2 + proto_len + 1  # protocol name, level
            connect_flags = body[offset]
            offset += 1 + 2  # flags, keepalive

            def read_string(pos: int) -> tuple[str, int]:
                if pos + 2 > len(body):
                    raise IndexError(pos)
                length = int.from_bytes(body[pos : pos + 2], "big")
                if pos + 2 + length > len(body):
                    raise IndexError(pos)
                value = body[pos + 2 : pos + 2 + length].decode(
                    "utf-8", errors="replace"
                )
                return value, pos + 2 + length

            fields: dict[str, str] = {}
            fields["client_id"], offset = read_string(offset)
            if connect_flags & 0x04:  # will flag: topic then message
                _, offset = read_string(offset)
                _, offset = read_string(offset)
            if connect_flags & 0x80:
                fields["username"], offset = read_string(offset)
            if connect_flags & 0x40:
                fields["password"], offset = read_string(offset)
            return fields
        except IndexError:
            return {}


class MqttStreamParser:
    """Incremental extractor: fed with TCP chunks, yields complete frames."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[MqttFrame]:
        self.buffer.extend(data)
        frames: list[MqttFrame] = []
        while len(self.buffer) >= 2:
            # Variable-length "remaining length" field
            multiplier, value, index = 1, 0, 1
            while True:
                if index >= len(self.buffer) or index > 4:
                    return frames  # incomplete header
                byte = self.buffer[index]
                value += (byte & 0x7F) * multiplier
                index += 1
                if not byte & 0x80:
                    break
                multiplier *= 128
            total = index + value
            if len(self.buffer) < total:
                break  # packet not fully arrived
            header = self.buffer[0]
            frames.append(
                MqttFrame(
                    packet_type=header >> 4,
                    flags=header & 0x0F,
                    body=bytes(self.buffer[index:total]),
                )
            )
            del self.buffer[:total]
        return frames


def hwid_from_username(username: str) -> str:
    """Hardware id of a device login ``<type>-<hwid>``, "" when not one."""
    if "-" not in username:
        return ""
    return username.rsplit("-", 1)[-1].lower()


def encode_remaining_length(length: int) -> bytes:
    """MQTT variable-length encoding of a packet's remaining length."""
    out = b""
    while True:
        byte = length % 128
        length //= 128
        out += bytes([byte | (0x80 if length > 0 else 0)])
        if length == 0:
            return out


def build_connect_packet(
    client_id: str, username: str = "", password: str = ""
) -> bytes:
    """A minimal MQTT 3.1.1 CONNECT (clean session, keepalive 60)."""

    def string(value: str) -> bytes:
        raw = value.encode("utf-8")
        return len(raw).to_bytes(2, "big") + raw

    flags = 0x02
    if username:
        flags |= 0x80
    if password:
        flags |= 0x40
    body = b"\x00\x04MQTT\x04" + bytes([flags]) + b"\x00\x3c" + string(client_id)
    if username:
        body += string(username)
    if password:
        body += string(password)
    return b"\x10" + encode_remaining_length(len(body)) + body


PACKET_SUBSCRIBE = 8
PACKET_PINGREQ = 12
PACKET_DISCONNECT = 14

CONNACK_OK = b"\x20\x02\x00\x00"
PINGRESP = b"\xd0\x00"


def encode_string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return len(raw).to_bytes(2, "big") + raw


def encode_publish(topic: str, payload: bytes) -> bytes:
    """A QoS 0 PUBLISH."""
    body = encode_string(topic) + payload
    return b"\x30" + encode_remaining_length(len(body)) + body


def encode_puback(packet_id: bytes) -> bytes:
    return b"\x40\x02" + packet_id


def encode_suback(frame: MqttFrame) -> bytes:
    """SUBACK of a SUBSCRIBE, every filter granted at QoS 0."""
    body = frame.body
    packet_id, offset, granted = body[0:2], 2, b""
    while offset + 2 <= len(body):
        length = int.from_bytes(body[offset : offset + 2], "big")
        offset += 2 + length + 1
        granted += b"\x00"
    payload = packet_id + granted
    return b"\x90" + encode_remaining_length(len(payload)) + payload


def publish_packet_id(frame: MqttFrame) -> bytes:
    """Packet identifier of a QoS 1/2 PUBLISH."""
    topic_len = int.from_bytes(frame.body[0:2], "big")
    return frame.body[2 + topic_len : 4 + topic_len]
