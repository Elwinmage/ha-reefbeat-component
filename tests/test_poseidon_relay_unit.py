"""Poseidon relay: real sockets on the loopback, a fake Red Sea broker."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import pytest

from custom_components.redsea.poseidon import const
from custom_components.redsea.poseidon.relay import DOWN, UP, Relay
from tests._poseidon_fakes import HWID, connect_packet

LOCAL = "127.0.0.1"


class Broker:
    """Fake upstream: records what it receives, answers a CONNACK."""

    def __init__(self) -> None:
        self.received = b""
        self.got_data = asyncio.Event()
        self.server: asyncio.Server | None = None
        self.writers: list[asyncio.StreamWriter] = []

    async def start(self) -> int:
        self.server = await asyncio.start_server(self._handle, LOCAL, 0)
        return int(self.server.sockets[0].getsockname()[1])

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self.writers.append(writer)
        with contextlib.suppress(Exception):
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                self.received += data
                self.got_data.set()
                writer.write(b"\x20\x02\x00\x00")  # CONNACK
                await writer.drain()
        writer.close()

    async def stop(self) -> None:
        for writer in self.writers:
            writer.close()
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()


@pytest.fixture
async def broker(socket_enabled: Any) -> Any:
    b = Broker()
    yield b
    await b.stop()


async def _relay(broker: Broker, **kwargs: Any) -> Relay:
    port = await broker.start()
    relay = Relay(0, upstream_host=LOCAL, upstream_port=port, **kwargs)
    await relay.async_start()
    return relay


async def test_relays_both_ways_and_identifies(broker: Broker) -> None:
    connects: list[tuple[str, dict[str, str]]] = []
    traffic: list[tuple[str, str]] = []
    relay = await _relay(
        broker,
        on_connect=lambda h, f: connects.append((h, f)),
        on_traffic=lambda h, d: traffic.append((h, d)),
    )
    assert relay.running and relay.bound_port > 0
    reader, writer = await asyncio.open_connection(LOCAL, relay.bound_port)
    packet = connect_packet(f"reef-wave-{HWID}", "the-key")
    # The CONNECT in two pieces: it is only forwarded once complete
    writer.write(packet[:3])
    await writer.drain()
    await asyncio.sleep(0.05)
    writer.write(packet[3:])
    await writer.drain()
    assert await asyncio.wait_for(reader.readexactly(4), 2) == b"\x20\x02\x00\x00"
    await asyncio.wait_for(broker.got_data.wait(), 2)
    assert broker.received == packet
    # More bytes after the CONNECT go through untouched
    broker.got_data.clear()
    writer.write(b"\xc0\x00")
    await writer.drain()
    await asyncio.wait_for(broker.got_data.wait(), 2)
    assert broker.received.endswith(b"\xc0\x00")

    assert connects == [
        (
            HWID,
            {
                "client_id": "dev",
                "username": f"reef-wave-{HWID}",
                "password": "the-key",
            },
        )
    ]
    seen = relay.traffic[HWID]
    assert seen.last_up is not None and seen.last_down is not None
    assert (HWID, UP) in traffic and (HWID, DOWN) in traffic

    writer.close()
    await relay.async_stop()
    assert not relay.running
    await relay.async_stop()  # twice: nothing left to stop


async def test_unknown_login_is_relayed_without_identity(broker: Broker) -> None:
    connects: list[Any] = []
    relay = await _relay(broker, on_connect=lambda h, f: connects.append(h))
    reader, writer = await asyncio.open_connection(LOCAL, relay.bound_port)
    writer.write(connect_packet("nohyphen"))
    await writer.drain()
    assert await asyncio.wait_for(reader.readexactly(4), 2)
    assert connects == [] and relay.traffic == {}
    writer.close()
    await relay.async_stop()


async def test_closed_before_connect(broker: Broker) -> None:
    relay = await _relay(broker)
    _reader, writer = await asyncio.open_connection(LOCAL, relay.bound_port)
    writer.write(b"\x10")  # half a header
    await writer.drain()
    writer.close()
    await asyncio.sleep(0.1)
    assert broker.received == b""
    await relay.async_stop()


async def test_upstream_unreachable(
    socket_enabled: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(const, "UPSTREAM_TIMEOUT_S", 1)
    # A port nobody listens on
    probe = await asyncio.start_server(lambda r, w: None, LOCAL, 0)
    dead = int(probe.sockets[0].getsockname()[1])
    probe.close()
    await probe.wait_closed()
    relay = Relay(0, upstream_host=LOCAL, upstream_port=dead)
    await relay.async_start()
    reader, writer = await asyncio.open_connection(LOCAL, relay.bound_port)
    writer.write(connect_packet(f"reef-run-{HWID}"))
    await writer.drain()
    # The relay hangs up
    assert await asyncio.wait_for(reader.read(10), 2) == b""
    writer.close()
    await relay.async_stop()


async def test_connect_timeout(broker: Broker, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(const, "CONNECT_TIMEOUT_S", 0.1)
    relay = await _relay(broker)
    reader, writer = await asyncio.open_connection(LOCAL, relay.bound_port)
    # Says nothing: dropped after the timeout
    assert await asyncio.wait_for(reader.read(10), 2) == b""
    writer.close()
    await relay.async_stop()


async def test_stop_closes_open_sessions(broker: Broker) -> None:
    relay = await _relay(broker)
    reader, writer = await asyncio.open_connection(LOCAL, relay.bound_port)
    writer.write(connect_packet(f"reef-wave-{HWID}"))
    await writer.drain()
    await asyncio.wait_for(reader.readexactly(4), 2)
    await relay.async_stop()
    assert await asyncio.wait_for(reader.read(10), 2) == b""
    writer.close()


async def test_port_taken(socket_enabled: Any) -> None:
    holder = await asyncio.start_server(lambda r, w: None, None, 0, reuse_address=False)
    port = int(holder.sockets[0].getsockname()[1])
    try:
        relay = Relay(port)
        with pytest.raises(OSError):
            await relay.async_start()
        assert relay.bound_port == port
    finally:
        holder.close()
        await holder.wait_closed()


class _Source:
    """Stands for a StreamReader: chunks in order, then an end or an error."""

    def __init__(self, *chunks: bytes | BaseException) -> None:
        self.chunks = list(chunks)

    async def read(self, _n: int) -> bytes:
        chunk = self.chunks.pop(0)
        if isinstance(chunk, BaseException):
            raise chunk
        return chunk


class _Sink:
    """Stands for a StreamWriter: records what it is given."""

    def __init__(self) -> None:
        self.data = b""
        self.closed = False

    def write(self, data: bytes) -> None:
        self.data += data

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize("end", [b"", ConnectionResetError("reset")])
async def test_pump_until_closed_with_frames_logged(end: bytes | BaseException) -> None:
    frames: list[tuple[str, str, int]] = []
    relay = Relay(0, on_frame=lambda h, d, f: frames.append((h, d, f.packet_type)))
    relay.log_frames = True
    sink = _Sink()
    await relay._pump(_Source(b"\xc0\x00", end), sink, HWID, DOWN)  # type: ignore[arg-type]
    # Copied, parsed for the debug log, the sink closed at the end
    assert sink.data == b"\xc0\x00" and sink.closed
    assert frames == [(HWID, DOWN, 12)]
    assert relay.traffic[HWID].last_down is not None


async def test_pump_without_identity_records_nothing() -> None:
    relay = Relay(0)
    sink = _Sink()
    await relay._pump(_Source(b"\xc0\x00", b""), sink, "", UP)  # type: ignore[arg-type]
    assert sink.data == b"\xc0\x00" and relay.traffic == {}
