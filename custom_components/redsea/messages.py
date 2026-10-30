"""History of the messages and alerts of a ReefBeat device.

Every push answered by a device can carry a message (``last_message``
sensor) or end in an alert (``last_alert_message`` sensor). The sensors only
show the last one; this module keeps them all, for a configurable number of
days and up to a configurable number of entries, in a
``helpers.storage.Store`` (one JSON file per config entry, under
``.storage/redsea_messages_<entry_id>``).

The store lives in ``hass.data[MESSAGES_DATA]`` rather than on the
coordinator: a config entry reload (options change, IP change, ...) builds a
new coordinator but keeps the same store, so no entry is lost between the
old coordinator's last push and the new one's first.

Entries are dicts::

    {"ts": "2026-10-29T08:30:00+00:00", "type": "last_message",
     "text": "...", "method": "post", "path": "/mode", "status": 200}
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import MESSAGE_HISTORY_DAYS, MESSAGE_HISTORY_MAX

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION: Final[int] = 1
STORAGE_KEY_TPL: Final[str] = "redsea_messages_{entry_id}"
# hass.data key of the stores, by config entry id
MESSAGES_DATA: Final[str] = "redsea_messages"
# Delay before writing the file after a change (seconds): a burst of pushes
# (a schedule written head by head) gives one write.
SAVE_DELAY: Final[int] = 10
# Longest text kept for one entry: an alert can be a whole HTML error page
MAX_TEXT_LENGTH: Final[int] = 1000


def _parse_ts(value: Any) -> datetime | None:
    """Datetime of an entry's ISO timestamp, None when unreadable."""
    if not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


class MessageStore:
    """Persistent message history of one config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        days: int = MESSAGE_HISTORY_DAYS,
        max_entries: int = MESSAGE_HISTORY_MAX,
    ) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TPL.format(entry_id=entry_id)
        )
        self._entries: list[dict[str, Any]] = []
        self._loaded = False
        self.days = days
        self.max_entries = max_entries

    # -- loading / saving ----------------------------------------------------

    async def async_load(self) -> None:
        """Load the persisted history (no-op if already loaded)."""
        if self._loaded:
            return
        raw = await self._store.async_load() or {}
        entries = raw.get("entries", [])
        self._entries = [
            e for e in entries if isinstance(e, dict) and _parse_ts(e.get("ts"))
        ]
        self._loaded = True
        if self._prune():
            self._schedule_save()

    def _data_to_save(self) -> dict[str, Any]:
        return {"entries": self._entries}

    @callback
    def _schedule_save(self) -> None:
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    async def async_remove(self) -> None:
        """Delete the file (config entry removed)."""
        self._entries = []
        await self._store.async_remove()

    # -- settings --------------------------------------------------------------

    @callback
    def configure(self, days: int, max_entries: int) -> None:
        """Apply new retention settings (options flow)."""
        self.days = max(1, int(days))
        self.max_entries = max(1, int(max_entries))
        if self._prune():
            self._schedule_save()

    def _prune(self) -> bool:
        """Drop the entries too old or too many; True when some were."""
        before = len(self._entries)
        limit = datetime.now(UTC) - timedelta(days=self.days)
        kept = [
            e for e in self._entries if (ts := _parse_ts(e.get("ts"))) and ts >= limit
        ]
        if len(kept) > self.max_entries:
            kept = kept[-self.max_entries :]
        self._entries = kept
        return len(kept) != before

    # -- entries ---------------------------------------------------------------

    @callback
    def add(self, entry: dict[str, Any]) -> None:
        """Record one message / alert (called by the API, in the event loop)."""
        item = dict(entry)
        text = str(item.get("text", ""))
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH] + "…"
        item["text"] = text
        self._entries.append(item)
        self._prune()
        self._schedule_save()

    def entries(
        self,
        msg_type: str | None = None,
        days: float | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Entries, newest first.

        Args:
            msg_type: only this kind (last_message / last_alert_message);
                None or "All" for both
            days: only the entries of the last `days` days
            limit: at most this many entries
        """
        since = datetime.now(UTC) - timedelta(days=days) if days else None
        result: list[dict[str, Any]] = []
        for entry in reversed(self._entries):
            if msg_type and msg_type != "All" and entry.get("type") != msg_type:
                continue
            if since is not None:
                ts = _parse_ts(entry.get("ts"))
                if ts is None or ts < since:
                    continue
            result.append(dict(entry))
            if limit and len(result) >= limit:
                break
        return result

    @callback
    def clear(self, msg_type: str | None = None) -> None:
        """Forget the entries of one kind, or all of them."""
        if msg_type and msg_type != "All":
            self._entries = [e for e in self._entries if e.get("type") != msg_type]
        else:
            self._entries = []
        self._schedule_save()


async def async_get_message_store(
    hass: HomeAssistant, entry_id: str, days: int, max_entries: int
) -> MessageStore:
    """The store of a config entry, created and loaded on first use.

    Kept across reloads of the entry (see module docstring).
    """
    stores: dict[str, MessageStore] = hass.data.setdefault(MESSAGES_DATA, {})
    store = stores.get(entry_id)
    if store is None:
        store = MessageStore(hass, entry_id, days, max_entries)
        await store.async_load()
        stores[entry_id] = store
    else:
        store.configure(days, max_entries)
    return store


async def async_remove_message_store(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the history of a removed config entry."""
    store = hass.data.get(MESSAGES_DATA, {}).pop(entry_id, None)
    if store is None:
        store = MessageStore(hass, entry_id)
    await store.async_remove()
