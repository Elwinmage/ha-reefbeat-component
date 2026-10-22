"""Listening port of the relay: which ones are free."""

from __future__ import annotations

import socket

from .const import DEFAULT_PORT, PORT_SCAN_LAST, RESERVED_PORTS


def port_free(port: int) -> bool:
    """Whether the relay could listen on ``port`` right now.

    Binding is tested on the wildcard address, as the relay does. It only
    sees what listens at this moment on this host: a service started later
    on the same port is caught when the relay starts (see the repair issue).
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("", port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def find_free_port(first: int = DEFAULT_PORT, last: int = PORT_SCAN_LAST) -> int | None:
    """First free port from ``first`` to ``last``, standard MQTT ports skipped."""
    for port in range(first, last + 1):
        if port in RESERVED_PORTS:
            continue
        if port_free(port):
            return port
    return None


def local_ip() -> str:
    """Address of this host on the network leading to the Internet.

    A UDP "connection" sends nothing: it only makes the kernel pick the
    outgoing interface. Falls back to the loopback address.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()
