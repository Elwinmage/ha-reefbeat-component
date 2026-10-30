"""JSONL logs of Poseidon: debug (every frame), spy and shadow strategies.

Frame records use the format of the CLI's ProxyLogger (``kind``
publish/control), so the logs of both tools can be read the same way. The
spy file adds ``http`` (a request sent to the device), ``compare`` (see
strategy.py) and ``mark`` (strategy or pause changed) records, all with the
same clock. Files rotate by size, and are only created on their first
record. Writing happens in a logging QueueListener thread: the event loop
never waits on the disk.

The payloads are written in clear: the options screen says so. The
answers of the HTTP requests (``response``) are written too, to tell what a
pushed value is in the polled sources, with two exceptions: the answer of
``/cloud`` never (it holds the device keys), and any key, secret, password
or token inside the others is masked. An answer equal to the previous one of
the same request is not repeated (``response_unchanged``).
"""

from __future__ import annotations

import json
import logging
import queue
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from typing import Any

from homeassistant.util import dt as dt_util

from .crypto import decrypt_payload
from .mqtt import PACKET_PUBLISH, MqttFrame
from .relay import UP

MAX_BYTES = 10 * 1024 * 1024
BACKUPS = 5
FILE_NAME = "poseidon.jsonl"

PACKET_NAMES = {
    1: "CONNECT",
    2: "CONNACK",
    3: "PUBLISH",
    4: "PUBACK",
    8: "SUBSCRIBE",
    9: "SUBACK",
    12: "PINGREQ",
    13: "PINGRESP",
    14: "DISCONNECT",
}
DIRECTIONS = {UP: "DEVICE → CLOUD"}
DOWN_LABEL = "CLOUD → DEVICE"
HTTP_LABEL = "HA → DEVICE"


def frame_record(
    hwid: str, direction: str, frame: MqttFrame, api_secret: str = ""
) -> dict[str, Any]:
    """The JSONL record of one frame, its payload decrypted when possible."""
    record: dict[str, Any] = {
        "ts": dt_util.now().isoformat(),
        "direction": DIRECTIONS.get(direction, DOWN_LABEL),
        "hwid": hwid,
    }
    if frame.packet_type != PACKET_PUBLISH:
        record.update(
            kind="control",
            packet=PACKET_NAMES.get(frame.packet_type, f"TYPE{frame.packet_type}"),
        )
        return record
    topic, payload = frame.parse_publish()
    raw = payload.decode("utf-8", errors="replace")
    encrypted = "." in raw and len(raw) > 20
    decrypted: Any = None
    if encrypted and len(api_secret) == 16:
        try:
            decrypted = decrypt_payload(raw, api_secret)
        except Exception as err:
            record["error"] = str(err)
    record.update(
        kind="publish",
        topic=topic,
        qos=frame.qos,
        size=len(payload),
        encrypted=encrypted,
        decrypted=decrypted,
        raw=raw,
    )
    return record


# Endpoints whose answer is never written: /cloud holds api_key/api_secret
SECRET_ENDPOINTS: frozenset[str] = frozenset({"/cloud"})
# Keys masked in the written answers (and parts of key names)
SECRET_KEYS: frozenset[str] = frozenset({"api_key", "api_secret", "psk"})
SECRET_PARTS: tuple[str, ...] = ("password", "secret", "token", "passwd")
MASK = "***"


def _secret_key(key: Any) -> bool:
    name = str(key).lower()
    return name in SECRET_KEYS or any(part in name for part in SECRET_PARTS)


def redact(value: Any) -> Any:
    """The value with every secret masked (keys of dicts, at any depth)."""
    if isinstance(value, dict):
        return {
            k: (MASK if _secret_key(k) and v not in (None, "") else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def http_record(
    hwid: str,
    request: dict[str, Any],
    seen: dict[tuple[str, str, str], str] | None = None,
) -> dict[str, Any]:
    """The JSONL record of an HTTP request sent to a device.

    Args:
        hwid: the device
        request: the request as notify_http reports it (``response`` is
            its decoded answer)
        seen: last answer written per (hwid, method, endpoint), updated:
            an answer equal to it is not written again
    """
    fields = {k: v for k, v in request.items() if k != "response"}
    record: dict[str, Any] = {
        "ts": dt_util.now().isoformat(),
        "kind": "http",
        "direction": HTTP_LABEL,
        "hwid": hwid,
        **fields,
    }
    response = request.get("response")
    endpoint = str(request.get("endpoint") or "")
    if endpoint in SECRET_ENDPOINTS:
        if response is not None:
            record["response_omitted"] = "device keys"
        return record
    if response is None:
        return record
    masked = redact(response)
    if seen is not None:
        key = (hwid, str(request.get("method") or ""), endpoint)
        digest = json.dumps(masked, sort_keys=True, default=str)
        if seen.get(key) == digest:
            record["response_unchanged"] = True
            return record
        seen[key] = digest
    record["response"] = masked
    return record


def mark_record(hwid: str, event: str, value: Any) -> dict[str, Any]:
    """A change worth seeing between the records (strategy, pause)."""
    return {
        "ts": dt_util.now().isoformat(),
        "kind": "mark",
        "hwid": hwid,
        "event": event,
        "value": value,
    }


class DebugLog:
    """A rotated JSONL file written off the event loop."""

    def __init__(self, directory: Path, file_name: str = FILE_NAME) -> None:
        self.path = directory / file_name
        self._logger = logging.getLogger(f"{__name__}.{Path(file_name).stem}")
        self._logger.propagate = False
        self._logger.setLevel(logging.INFO)
        self._listener: QueueListener | None = None
        self._queue_handler: QueueHandler | None = None

    @property
    def running(self) -> bool:
        return self._listener is not None

    def start(self) -> None:
        """Open the file (blocking: run it in the executor)."""
        if self._listener is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            self.path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUPS,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        records: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
        self._queue_handler = QueueHandler(records)
        self._logger.addHandler(self._queue_handler)
        self._listener = QueueListener(records, file_handler)
        self._listener.start()

    def stop(self) -> None:
        """Flush and close the file (blocking: run it in the executor)."""
        listener, self._listener = self._listener, None
        if self._queue_handler is not None:
            self._logger.removeHandler(self._queue_handler)
            self._queue_handler = None
        if listener is not None:
            listener.stop()
            for handler in listener.handlers:
                handler.close()

    def write(self, record: dict[str, Any]) -> None:
        """Queue one record (never blocks)."""
        if self._listener is not None:
            self._logger.info(json.dumps(record, ensure_ascii=False, default=str))
