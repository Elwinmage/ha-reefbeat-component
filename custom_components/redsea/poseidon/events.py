"""Home Assistant events built from what the devices push (poseidon).

``redsea_dose``: a ReefDose pushes a ``dosing-log`` when a dose ends (a
telemetry with the new volumes comes 1 to 2 s before it). Nothing is pushed
when it starts: for a dose of the dosing queue, its start is the time the
queue gave it (seconds after the local midnight of the device); a dose
missing from the queue (manual, from the app) has no start.

Seen on RSDOSE4 3.0.1 (spy runs of 2026-10-30): ten doses, 4 to 17 s each.
After a reconnection, a device may push the same ``dosing-log`` twice: the
events are deduplicated (device, head, local time).
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Any

from .mergers import _data, _source

EVENT_DOSE = "redsea_dose"
# How far before its end the start of a dose is looked for in the queue
MAX_DOSE_S = 600
# Doses remembered against duplicates
SEEN_MAX = 100


def _parse(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _short_name(coordinator: Any, head: int) -> str:
    """The short name of the supplement of a head, as the queue tells it."""
    settings = _data(coordinator, f"/head/{head}/settings")
    supplement = settings.get("supplement") if settings else None
    name = supplement.get("short_name") if isinstance(supplement, dict) else None
    return name.strip() if isinstance(name, str) else ""


def dose_start(coordinator: Any, head: int, ended: datetime) -> datetime | None:
    """When a dose that ended at ``ended`` (device local time) started, from
    the dosing queue polled before it; None when it is not there."""
    # A list: not what _data gives
    source = _source(coordinator, "/dosing-queue")
    queue = source.get("data") if source is not None else None
    short = _short_name(coordinator, head)
    if not isinstance(queue, list) or not short:
        return None
    midnight = ended.replace(hour=0, minute=0, second=0, microsecond=0)
    best: datetime | None = None
    for entry in queue:
        if not isinstance(entry, dict) or not isinstance(entry.get("time"), int):
            continue
        if str(entry.get("head", "")).strip() != short:
            continue
        start = midnight + timedelta(seconds=entry["time"])
        if timedelta(0) <= ended - start <= timedelta(seconds=MAX_DOSE_S) and (
            best is None or start > best
        ):
            best = start
    return best


def dose_event(coordinator: Any, payload: Any) -> dict[str, Any] | None:
    """The data of a ``redsea_dose`` event for a pushed dosing-log, None when
    it is not one."""
    if not isinstance(payload, dict) or not isinstance(payload.get("head"), int):
        return None
    ended = _parse(payload.get("local_time"))
    if ended is None:
        return None
    head = payload["head"]
    started = dose_start(coordinator, head, ended)
    volume = payload.get("volume")
    return {
        "head": head,
        "supplement": payload.get("supplement_name"),
        "brand": payload.get("brand_name"),
        "dose_type": payload.get("dose_type"),
        "volume": round(volume, 3) if isinstance(volume, (int, float)) else None,
        "started_at": started.isoformat() if started else None,
        "ended_at": ended.isoformat(),
        "duration_s": (ended - started).total_seconds() if started else None,
    }


class DoseEvents:
    """Remembers the doses already told (a dosing-log may come twice)."""

    def __init__(self) -> None:
        self._seen: deque[tuple[str, int, str]] = deque(maxlen=SEEN_MAX)

    def first_time(self, hwid: str, payload: dict[str, Any]) -> bool:
        key = (hwid, int(payload.get("head") or 0), str(payload.get("local_time")))
        if key in self._seen:
            return False
        self._seen.append(key)
        return True
