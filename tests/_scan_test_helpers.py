"""Helpers for the tests going through the local scan progress step."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def drive_scan_to_end(
    hass: HomeAssistant, result: dict[str, Any]
) -> dict[str, Any]:
    """Follow the scan progress dialog until the flow shows something else.

    Home Assistant re-invokes a progress step by itself when its task ends;
    the follow-up ``async_configure`` without input is what the frontend does
    to fetch the step now showing.
    """
    for _ in range(50):
        if result["type"] not in (
            FlowResultType.SHOW_PROGRESS,
            FlowResultType.SHOW_PROGRESS_DONE,
        ):
            return result
        handler = cast(Any, hass.config_entries.flow)._progress.get(result["flow_id"])
        task = getattr(handler, "_scan_task", None)
        if isinstance(task, asyncio.Task) and not task.done():
            with contextlib.suppress(Exception):
                await task
        await hass.async_block_till_done()
        result = cast(
            dict[str, Any],
            await hass.config_entries.flow.async_configure(result["flow_id"]),
        )
    raise AssertionError(f"Scan never ended (last result: {result!r})")
