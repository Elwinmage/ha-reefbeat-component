"""Server side of the watchdog: ``is_alive``, answered by the relay itself.

The watchdog connects to the relay port, the very path devices use, with the
reserved login ``poseidon-watchdog``. The relay serves that session itself,
as a minimal MQTT broker:

    poseidon/is_alive           {"id", "ts", "minutes"}       (watchdog -> relay)
    poseidon/is_alive/response  {"id", "ts", "ok", "devices"} (relay -> watchdog)

Both payloads are encrypted like the devices' ones (AES-128-CBC), with the
16-character watchdog key of the Poseidon options. The key never goes on the
wire: being able to encrypt the request is the authentication, and a request
that does not decrypt gets no answer. The response repeats the request id,
so an old response cannot be replayed.

``ok`` is true when at least one device exchanged frames with Red Sea in
both directions within ``minutes``: a single device under maintenance never
makes the watchdog switch everyone back.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import string
from collections.abc import Callable
from typing import Any

from . import const
from .crypto import decrypt_payload, encrypt_payload
from .mqtt import (
    CONNACK_OK,
    PACKET_DISCONNECT,
    PACKET_PINGREQ,
    PACKET_PUBLISH,
    PACKET_SUBSCRIBE,
    PINGRESP,
    MqttStreamParser,
    encode_puback,
    encode_publish,
    encode_suback,
    publish_packet_id,
)

_LOGGER = logging.getLogger(__name__)

WATCHDOG_USERNAME = "poseidon-watchdog"
TOPIC_REQUEST = "poseidon/is_alive"
TOPIC_RESPONSE = "poseidon/is_alive/response"
KEY_LENGTH = 16
# A silent watchdog session is closed after this (it pings every minute)
IDLE_TIMEOUT_S = 300.0


def generate_key() -> str:
    """A new watchdog key: 16 letters and digits."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(KEY_LENGTH))


def valid_key(key: str) -> bool:
    return len(key.encode("utf-8")) == KEY_LENGTH


class WatchdogSession:
    """One watchdog connection, served locally."""

    def __init__(
        self,
        key: Callable[[], str],
        answer: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Create the handler.

        Args:
            key: the current watchdog key ("" when none is set).
            answer: builds the response to a decrypted request.
        """
        self._key = key
        self._answer = answer

    async def __call__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, preface: bytes
    ) -> None:
        parser = MqttStreamParser()
        # The CONNECT was read by the relay; anything after it is kept
        frames = parser.feed(preface)[1:]
        writer.write(CONNACK_OK)
        await writer.drain()
        try:
            while True:
                for frame in frames:
                    if frame.packet_type == PACKET_DISCONNECT:
                        return
                    reply = self._reply(frame)
                    if reply:
                        writer.write(reply)
                        await writer.drain()
                data = await asyncio.wait_for(
                    reader.read(const.READ_CHUNK), IDLE_TIMEOUT_S
                )
                if not data:
                    return
                frames = parser.feed(data)
        except (OSError, TimeoutError):
            return
        finally:
            with contextlib.suppress(Exception):
                writer.close()

    def _reply(self, frame: Any) -> bytes:
        if frame.packet_type == PACKET_PINGREQ:
            return PINGRESP
        if frame.packet_type == PACKET_SUBSCRIBE:
            return encode_suback(frame)
        if frame.packet_type != PACKET_PUBLISH:
            return b""
        out = encode_puback(publish_packet_id(frame)) if frame.qos else b""
        topic, payload = frame.parse_publish()
        if topic != TOPIC_REQUEST:
            return out
        response = self.respond(payload.decode("utf-8", errors="replace"))
        if response is None:
            return out
        return out + encode_publish(TOPIC_RESPONSE, response.encode("ascii"))

    def respond(self, encrypted: str) -> str | None:
        """Encrypted response to an encrypted request, None when it is not one."""
        key = self._key()
        if not valid_key(key):
            return None
        try:
            request = decrypt_payload(encrypted, key)
        except Exception:
            _LOGGER.debug("Poseidon watchdog: request dropped (does not decrypt)")
            return None
        if not isinstance(request, dict) or not request.get("id"):
            return None
        return encrypt_payload(self._answer(request), key)
