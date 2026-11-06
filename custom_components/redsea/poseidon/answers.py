"""Messages of the commands of the ReefBeat app, relayed by Poseidon.

In Poseidon mode, the app (or the cloud) writes to a device over MQTT, not
HTTP: the ``last_message`` / ``last_alert_message`` sensors, which come from
the answers to the HTTP pushes of Home Assistant, would never see them.

The device answers each command on ``command-response`` with the uuid of the
command, an HTTP status and the body it would have answered over HTTP::

    command          {"uuid": "...", "method": "POST", "url": "/head/2/settings", ...}
    command-response {"uuid": "...", "status": 200,
                      "body": {"success": true, "message": "head settings successfully saved"}}

The command is kept until its answer comes (``ANSWER_WAIT_S`` at most); the
answer of a write is then recorded like the answer to a push of Home
Assistant, with the ``reefbeat`` origin. The reads of the app (GET) carry no
message: they are not recorded.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, Final

# How long a command waits for its answer (seconds)
ANSWER_WAIT_S: Final[float] = 60.0
# Commands waiting at most (a device that never answers keeps none)
PENDING_MAX: Final[int] = 100


def _suffix(topic: str) -> str:
    return topic.rsplit("/", 1)[-1] if topic.startswith("device/") else ""


class RelayedCommands:
    """The write commands of the app waiting for the answer of their device."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        # (hwid, uuid) -> (method, path, sent at)
        self._pending: OrderedDict[tuple[str, str], tuple[str, str, float]] = (
            OrderedDict()
        )

    def __len__(self) -> int:
        return len(self._pending)

    def _expire(self) -> None:
        limit = self._clock() - ANSWER_WAIT_S
        while self._pending:
            key, (_, _, sent) = next(iter(self._pending.items()))
            if sent >= limit and len(self._pending) <= PENDING_MAX:
                break
            del self._pending[key]

    def sent(self, hwid: str, topic: str, message: Any) -> None:
        """A frame relayed to a device: kept when it is a write command."""
        if _suffix(topic) != "command" or not isinstance(message, dict):
            return
        uuid, method, url = (message.get(k) for k in ("uuid", "method", "url"))
        if not (isinstance(uuid, str) and isinstance(method, str)):
            return
        if not isinstance(url, str) or method.upper() == "GET":
            return
        self._pending[(hwid, uuid)] = (method.upper(), url, self._clock())
        self._pending.move_to_end((hwid, uuid))
        self._expire()

    def answered(
        self, hwid: str, topic: str, message: Any
    ) -> tuple[str, str, Any, Any] | None:
        """A frame of a device: (method, path, status, body) when it answers
        a kept command, None otherwise."""
        if _suffix(topic) != "command-response" or not isinstance(message, dict):
            return None
        self._expire()
        uuid = message.get("uuid")
        if not isinstance(uuid, str):
            return None
        command = self._pending.pop((hwid, uuid), None)
        if command is None:
            return None
        method, path, _ = command
        return method, path, message.get("status"), message.get("body")

    def clear(self) -> None:
        self._pending.clear()
