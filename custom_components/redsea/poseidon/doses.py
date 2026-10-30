"""History of the doses of the ReefDose in Poseidon mode.

Each ``redsea_dose`` event (events.py) is also kept here, per device and
head, for ``DOSE_HISTORY_DAYS`` days and at most ``DOSE_HISTORY_MAX``
entries, in a ``helpers.storage.Store`` (``.storage/redsea_poseidon_doses``):
the history survives the restarts and the purges of the recorder. The last
dose of each head is the state of its ``poseidon_last_dose`` sensor; the
``redsea.get_doses`` action returns the history.

Entries are dicts::

    {"hwid": "...", "head": 2, "supplement": "...", "brand": "...",
     "dose_type": "scheduled", "volume": 12.487,
     "started_at": "2026-10-30T10:28:45+01:00",
     "ended_at": "2026-10-30T10:29:04+01:00", "duration_s": 19.0}
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

STORAGE_VERSION: Final[int] = 1
STORAGE_KEY: Final[str] = "redsea_poseidon_doses"
DOSE_HISTORY_DAYS: Final[int] = 30
DOSE_HISTORY_MAX: Final[int] = 5000
# Delay before writing the file after a change (seconds)
SAVE_DELAY: Final[int] = 30

# What an entry keeps of an event
FIELDS: Final[tuple[str, ...]] = (
    "head",
    "supplement",
    "brand",
    "dose_type",
    "volume",
    "started_at",
    "ended_at",
    "duration_s",
)


def ended_at(entry: dict[str, Any]) -> datetime | None:
    """When a dose ended, None when unreadable."""
    value = entry.get("ended_at")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


class DoseHistory:
    """Persistent history of the doses of every ReefDose."""

    def __init__(
        self,
        hass: HomeAssistant,
        days: int = DOSE_HISTORY_DAYS,
        max_entries: int = DOSE_HISTORY_MAX,
    ) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._entries: list[dict[str, Any]] = []
        self._loaded = False
        self.days = days
        self.max_entries = max_entries

    async def async_load(self) -> None:
        """Load the kept doses (once)."""
        if self._loaded:
            return
        raw = await self._store.async_load() or {}
        entries = raw.get("entries", []) if isinstance(raw, dict) else []
        self._entries = [
            e
            for e in entries
            if isinstance(e, dict) and isinstance(e.get("hwid"), str) and ended_at(e)
        ]
        self._loaded = True
        if self._prune():
            self._schedule_save()

    @callback
    def _schedule_save(self) -> None:
        self._store.async_delay_save(lambda: {"entries": self._entries}, SAVE_DELAY)

    def _prune(self) -> bool:
        before = len(self._entries)
        limit = datetime.now(UTC) - timedelta(days=self.days)
        kept = [e for e in self._entries if (t := ended_at(e)) and t >= limit]
        if len(kept) > self.max_entries:
            kept = kept[-self.max_entries :]
        self._entries = kept
        return len(kept) != before

    @callback
    def add(self, hwid: str, event: dict[str, Any]) -> None:
        """Keep the dose of a redsea_dose event."""
        entry = {"hwid": hwid, **{name: event.get(name) for name in FIELDS}}
        if ended_at(entry) is None:
            return
        self._entries.append(entry)
        self._entries.sort(
            key=lambda e: ended_at(e) or datetime.min.replace(tzinfo=UTC)
        )
        self._prune()
        self._schedule_save()

    def entries(
        self,
        hwid: str,
        head: int | None = None,
        days: float | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """The doses of a device (of one head), newest first."""
        since = datetime.now(UTC) - timedelta(days=days) if days else None
        result: list[dict[str, Any]] = []
        for entry in reversed(self._entries):
            if entry.get("hwid") != hwid:
                continue
            if head is not None and entry.get("head") != head:
                continue
            if since is not None and (ended_at(entry) or since) < since:
                continue
            result.append({k: v for k, v in entry.items() if k != "hwid"})
            if limit and len(result) >= limit:
                break
        return result

    def last(self, hwid: str, head: int) -> dict[str, Any] | None:
        """The last dose of a head."""
        found = self.entries(hwid, head, limit=1)
        return found[0] if found else None
