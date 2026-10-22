"""The Poseidon relay: a transparent MQTT proxy to the Red Sea broker.

A device in Poseidon mode connects here instead of ``mqtt.reef-beat.com``.
For each connection the relay reads the CONNECT (to know which device it
is), opens one connection to the Red Sea broker, replays the CONNECT and
then pipes the bytes verbatim both ways. The cloud still authenticates the
device and the official app keeps working; the frames are only parsed on a
copy.

Ported from ``reefbeat_god_mode.py`` (``MqttRelay``, ``RelaySession``), with
threads replaced by asyncio.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.util import dt as dt_util

from . import const
from .mqtt import PACKET_CONNECT, MqttFrame, MqttStreamParser, hwid_from_username

_LOGGER = logging.getLogger(__name__)

# A session served by the relay itself instead of being relayed (the
# watchdog): called with the reader, the writer and the CONNECT bytes
LocalHandler = Callable[
    [asyncio.StreamReader, asyncio.StreamWriter, bytes], Awaitable[None]
]

# Directions of the traffic
UP = "up"  # device -> Red Sea
DOWN = "down"  # Red Sea -> device


@dataclass
class Traffic:
    """Last frames of one device through the relay."""

    last_up: datetime | None = None
    last_down: datetime | None = None


class Relay:
    """Listening TCP relay."""

    def __init__(
        self,
        port: int,
        upstream_host: str = const.UPSTREAM_HOST,
        upstream_port: int = const.UPSTREAM_PORT,
        on_connect: Callable[[str, dict[str, str]], None] | None = None,
        on_traffic: Callable[[str, str], None] | None = None,
        on_frame: Callable[[str, str, MqttFrame], None] | None = None,
    ) -> None:
        """Create the relay.

        Args:
            port: listening port.
            on_connect: called with the hwid and the CONNECT fields of each
                identified device.
            on_traffic: called with the hwid and the direction of every
                chunk relayed for an identified device.
            on_frame: called with the hwid, the direction and every frame
                relayed, while ``log_frames`` is set (debug mode).
        """
        self.port = port
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self._on_connect = on_connect
        self._on_traffic = on_traffic
        self._on_frame = on_frame
        # Debug mode: frames are handed to on_frame
        self.log_frames = False
        # Logins served locally (reserved usernames), see LocalHandler
        self.local_handlers: dict[str, LocalHandler] = {}
        self._server: asyncio.Server | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self.traffic: dict[str, Traffic] = {}

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def bound_port(self) -> int:
        """Port actually listened on (the configured one, or the one picked
        for port 0)."""
        if self._server is None or not self._server.sockets:
            return self.port
        return int(self._server.sockets[0].getsockname()[1])

    async def async_start(self) -> None:
        """Listen on every address; raises OSError when the port is taken."""
        self._server = await asyncio.start_server(
            self._handle, host=None, port=self.port, reuse_address=True
        )
        _LOGGER.info("Poseidon relay listening on port %s", self.port)

    async def async_stop(self) -> None:
        """Stop listening and close every relayed connection."""
        server, self._server = self._server, None
        if server is not None:
            server.close()
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        if server is not None:
            with contextlib.suppress(Exception):
                await server.wait_closed()

    def _track(self, task: asyncio.Task[None]) -> None:
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._track(task)
        upstream: asyncio.StreamWriter | None = None
        try:
            preface, hwid, fields = await self._read_connect(reader)
            if not preface:
                return
            local = self.local_handlers.get(fields.get("username", ""))
            if local is not None:
                await local(reader, writer, preface)
                return
            up_reader, upstream = await asyncio.wait_for(
                asyncio.open_connection(self.upstream_host, self.upstream_port),
                const.UPSTREAM_TIMEOUT_S,
            )
            if hwid and self._on_connect is not None:
                self._on_connect(hwid, fields)
            upstream.write(preface)
            await upstream.drain()
            self._seen(hwid, UP)
            for frame in MqttStreamParser().feed(preface):
                self._frame(hwid, UP, frame)
            await asyncio.gather(
                self._pump(reader, upstream, hwid, UP),
                self._pump(up_reader, writer, hwid, DOWN),
            )
        except (OSError, TimeoutError) as err:
            _LOGGER.debug("Poseidon relay connection closed: %s", err)
        finally:
            for sink in (upstream, writer):
                if sink is not None:
                    with contextlib.suppress(Exception):
                        sink.close()

    async def _read_connect(
        self, reader: asyncio.StreamReader
    ) -> tuple[bytes, str, dict[str, str]]:
        """Bytes up to the CONNECT, with the device it identifies."""
        parser = MqttStreamParser()
        preface = b""
        async with asyncio.timeout(const.CONNECT_TIMEOUT_S):
            while True:
                chunk = await reader.read(const.READ_CHUNK)
                if not chunk:
                    return b"", "", {}
                preface += chunk
                for frame in parser.feed(chunk):
                    if frame.packet_type == PACKET_CONNECT:
                        fields = frame.parse_connect()
                        hwid = hwid_from_username(fields.get("username", ""))
                        return preface, hwid, fields

    async def _pump(
        self,
        source: asyncio.StreamReader,
        sink: asyncio.StreamWriter,
        hwid: str,
        direction: str,
    ) -> None:
        """Copy bytes one way until either side closes, parsing a copy."""
        parser = MqttStreamParser()
        try:
            while True:
                data = await source.read(const.READ_CHUNK)
                if not data:
                    break
                sink.write(data)
                await sink.drain()
                self._seen(hwid, direction)
                for frame in parser.feed(data):
                    self._frame(hwid, direction, frame)
        except (OSError, ConnectionError):
            pass
        finally:
            with contextlib.suppress(Exception):
                sink.close()

    def _seen(self, hwid: str, direction: str) -> None:
        if not hwid:
            return
        traffic = self.traffic.setdefault(hwid, Traffic())
        if direction == UP:
            traffic.last_up = dt_util.utcnow()
        else:
            traffic.last_down = dt_util.utcnow()
        if self._on_traffic is not None:
            self._on_traffic(hwid, direction)

    def _frame(self, hwid: str, direction: str, frame: MqttFrame) -> None:
        if self.log_frames and self._on_frame is not None:
            self._on_frame(hwid, direction, frame)
