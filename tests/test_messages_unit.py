"""Message / alert history (messages.py) and the get_messages service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from homeassistant.core import HomeAssistant

import custom_components.redsea as redsea_init
from custom_components.redsea import messages as msgs
from custom_components.redsea.const import DOMAIN


def _entry(kind: str, text: str, age_days: float = 0) -> dict[str, Any]:
    ts = datetime.now(UTC) - timedelta(days=age_days)
    return {
        "ts": ts.isoformat(timespec="seconds"),
        "type": kind,
        "text": text,
        "method": "post",
        "path": "/mode",
        "status": 200,
    }


@pytest.mark.asyncio
class TestMessageStore:
    async def test_add_and_list_newest_first(self, hass: HomeAssistant) -> None:
        store = msgs.MessageStore(hass, "e1")
        await store.async_load()
        store.add(_entry("last_message", "a"))
        store.add(_entry("last_alert_message", "b"))
        store.add(_entry("last_message", "c"))

        assert [e["text"] for e in store.entries()] == ["c", "b", "a"]
        assert [e["text"] for e in store.entries("last_message")] == ["c", "a"]
        assert [e["text"] for e in store.entries("All", limit=2)] == ["c", "b"]

    async def test_identical_messages_are_all_kept(self, hass: HomeAssistant) -> None:
        store = msgs.MessageStore(hass, "e2")
        await store.async_load()
        for _ in range(3):
            store.add(_entry("last_message", "same"))
        assert len(store.entries()) == 3

    async def test_retention_by_age_and_count(self, hass: HomeAssistant) -> None:
        store = msgs.MessageStore(hass, "e3", days=10, max_entries=3)
        await store.async_load()
        store.add(_entry("last_message", "old", age_days=20))
        assert store.entries() == []

        for i in range(5):
            store.add(_entry("last_message", str(i)))
        assert [e["text"] for e in store.entries()] == ["4", "3", "2"]

        store.configure(10, 2)
        assert [e["text"] for e in store.entries()] == ["4", "3"]

    async def test_days_filter(self, hass: HomeAssistant) -> None:
        store = msgs.MessageStore(hass, "e4")
        await store.async_load()
        store.add(_entry("last_message", "week", age_days=8))
        store.add(_entry("last_message", "today"))
        assert [e["text"] for e in store.entries(days=7)] == ["today"]
        assert len(store.entries(days=30)) == 2

    async def test_long_text_is_truncated(self, hass: HomeAssistant) -> None:
        store = msgs.MessageStore(hass, "e5")
        await store.async_load()
        store.add(_entry("last_alert_message", "x" * 5000))
        text = store.entries()[0]["text"]
        assert len(text) == msgs.MAX_TEXT_LENGTH + 1
        assert text.endswith("…")

    async def test_clear(self, hass: HomeAssistant) -> None:
        store = msgs.MessageStore(hass, "e6")
        await store.async_load()
        store.add(_entry("last_message", "a"))
        store.add(_entry("last_alert_message", "b"))
        store.clear("last_alert_message")
        assert [e["text"] for e in store.entries()] == ["a"]
        store.clear()
        assert store.entries() == []

    async def test_persisted_and_reloaded(
        self, hass: HomeAssistant, hass_storage: dict[str, Any]
    ) -> None:
        hass_storage[msgs.STORAGE_KEY_TPL.format(entry_id="e7")] = {
            "version": msgs.STORAGE_VERSION,
            "minor_version": 1,
            "key": msgs.STORAGE_KEY_TPL.format(entry_id="e7"),
            "data": {
                "entries": [
                    _entry("last_message", "kept"),
                    _entry("last_message", "expired", age_days=100),
                    {"ts": "not a date", "text": "broken"},
                    "garbage",
                ]
            },
        }
        store = msgs.MessageStore(hass, "e7")
        await store.async_load()
        assert [e["text"] for e in store.entries()] == ["kept"]

    async def test_shared_across_reloads_and_removed(self, hass: HomeAssistant) -> None:
        first = await msgs.async_get_message_store(hass, "e8", 31, 500)
        first.add(_entry("last_message", "a"))
        second = await msgs.async_get_message_store(hass, "e8", 5, 10)
        assert second is first
        assert (second.days, second.max_entries) == (5, 10)

        await msgs.async_remove_message_store(hass, "e8")
        assert "e8" not in hass.data[msgs.MESSAGES_DATA]
        assert first.entries() == []


@pytest.mark.asyncio
async def test_get_messages_service(hass: HomeAssistant) -> None:
    assert await redsea_init.async_setup(hass, {})

    resp = await hass.services.async_call(
        DOMAIN,
        "get_messages",
        {"device_id": "missing"},
        blocking=True,
        return_response=True,
    )
    assert resp == {"error": "Device not enabled", "messages": []}

    store = await msgs.async_get_message_store(hass, "dev1", 31, 500)
    store.add(_entry("last_message", "a"))
    store.add(_entry("last_alert_message", "b"))
    hass.data.setdefault(DOMAIN, {})["dev1"] = object()

    resp = await hass.services.async_call(
        DOMAIN,
        "get_messages",
        {"device_id": "dev1"},
        blocking=True,
        return_response=True,
    )
    assert resp is not None
    assert [m["text"] for m in resp["messages"]] == ["b", "a"]  # type: ignore[index,union-attr]
    assert resp["retention_days"] == 31
    assert resp["max_entries"] == 500

    resp = await hass.services.async_call(
        DOMAIN,
        "get_messages",
        {"device_id": "dev1", "msg_type": "last_message", "days": 7, "limit": 5},
        blocking=True,
        return_response=True,
    )
    assert resp is not None
    assert [m["text"] for m in resp["messages"]] == ["a"]  # type: ignore[index,union-attr]


def test_parse_ts_rejects_non_strings() -> None:
    assert msgs._parse_ts(None) is None
    assert msgs._parse_ts(1730000000) is None


async def test_load_only_once(hass: HomeAssistant) -> None:
    store = msgs.MessageStore(hass, "once")
    await store.async_load()
    store.add(_entry("last_message", "kept"))
    # A second load must not replace what was added since
    await store.async_load()
    assert [e["text"] for e in store.entries()] == ["kept"]
