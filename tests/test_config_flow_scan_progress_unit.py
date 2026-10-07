"""Local scan of the config flow: one progress task per subnet.

The scan dialog names the subnet being scanned and how many devices were
found so far, and pushes an overall 0..1 progress to the frontend.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import pytest
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.data_entry_flow import (
    EVENT_DATA_ENTRY_FLOW_PROGRESS_UPDATE,
    EVENT_DATA_ENTRY_FLOW_PROGRESSED,
    FlowResultType,
)

import custom_components.redsea.config_flow as cf
from custom_components.redsea.const import (
    ADD_LOCAL_DETECT,
    CONFIG_FLOW_ADD_TYPE,
    DOMAIN,
)
from tests._scan_test_helpers import drive_scan_to_end

SUBNETS = ["192.0.2.0/24", "198.51.100.0/24"]


def _device(ip: str, name: str) -> dict[str, str]:
    return {"ip": ip, "hw_model": "RSMAT", "friendly_name": name, "uuid": f"u-{ip}"}


async def _start_scan(hass: HomeAssistant) -> dict[str, Any]:
    flow = cast(Any, hass.config_entries.flow)
    r1 = cast(dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"}))
    return cast(
        dict[str, Any],
        await flow.async_configure(
            r1["flow_id"], user_input={CONFIG_FLOW_ADD_TYPE: ADD_LOCAL_DETECT}
        ),
    )


@pytest.mark.asyncio
async def test_scan_names_each_subnet_and_reports_progress(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each subnet gets its own progress dialog; the progress goes up to 1."""
    # The progress reports, shown when the test fails
    caplog.set_level(logging.DEBUG, logger=cf.__name__)
    by_subnet = {
        SUBNETS[0]: [_device("192.0.2.10", "A")],
        # The same address seen again from another subnet is kept once.
        SUBNETS[1]: [_device("198.51.100.7", "B"), _device("192.0.2.10", "A")],
    }

    def _get_rb(*, subnetwork: str, progress_cb: Any) -> list[dict[str, str]]:
        progress_cb(0, 4)
        progress_cb(2, 4)
        progress_cb(4, 4)
        return by_subnet[subnetwork]

    monkeypatch.setattr(cf, "list_scan_targets", lambda _s=None: list(SUBNETS))
    monkeypatch.setattr(cf, "get_reefbeats", _get_rb)

    updates: list[float] = []

    @callback
    def _on_update(event: Event) -> None:
        updates.append(event.data["progress"])

    hass.bus.async_listen(EVENT_DATA_ENTRY_FLOW_PROGRESS_UPDATE, _on_update)

    flow = cast(Any, hass.config_entries.flow)
    result = await _start_scan(hass)
    assert result["type"] == FlowResultType.SHOW_PROGRESS
    assert result["step_id"] == "scan"
    assert result["progress_action"] == "scanning"
    assert result["description_placeholders"] == {
        "subnet": SUBNETS[0],
        "current": "1",
        "total": "2",
        "found": "0",
    }

    # Home Assistant moves on by itself to the second subnet, telling the
    # frontend to refresh the dialog: record what it shows at that time.
    handler = flow._progress[result["flow_id"]]
    shown: list[dict[str, Any]] = []

    @callback
    def _on_progressed(_event: Event) -> None:
        shown.append(dict(handler.cur_step))

    hass.bus.async_listen(EVENT_DATA_ENTRY_FLOW_PROGRESSED, _on_progressed)
    await handler._scan_task
    await hass.async_block_till_done()

    assert shown[0]["type"] == FlowResultType.SHOW_PROGRESS
    assert shown[0]["description_placeholders"] == {
        "subnet": SUBNETS[1],
        "current": "2",
        "total": "2",
        "found": "1",
    }

    # The second subnet's scan, and its reports, done before going on
    if handler._scan_task is not None:
        await handler._scan_task
    await hass.async_block_till_done()

    final = cast(dict[str, Any], await flow.async_configure(result["flow_id"]))
    assert final["type"] == FlowResultType.FORM
    assert final["step_id"] == "select_devices"
    key = next(iter(final["data_schema"].schema))
    assert key.default() == ["192.0.2.10 RSMAT A", "198.51.100.7 RSMAT B"]

    assert updates == sorted(updates)
    assert updates[0] == 0.0
    assert {0.25, 0.5, 0.75} <= set(updates), updates
    assert updates[-1] == 1.0
    # A report is only sent when the displayed percent changes.
    assert len(updates) == len(set(updates))


@pytest.mark.asyncio
async def test_scan_keeps_going_when_a_subnet_fails(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A subnet whose scan raises is skipped, the others are still scanned."""

    def _get_rb(*, subnetwork: str, progress_cb: Any) -> list[dict[str, str]]:
        if subnetwork == SUBNETS[0]:
            raise RuntimeError("network failure")
        return [_device("198.51.100.7", "B")]

    monkeypatch.setattr(cf, "list_scan_targets", lambda _s=None: list(SUBNETS))
    monkeypatch.setattr(cf, "get_reefbeats", _get_rb)

    result = await drive_scan_to_end(hass, await _start_scan(hass))
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "select_devices"


@pytest.mark.asyncio
async def test_scan_without_any_subnet_shows_the_manual_form(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No subnet to scan (or listing them fails): manual form, no dialog."""

    def _raise(_s: Any = None) -> list[str]:
        raise OSError("no interface")

    monkeypatch.setattr(cf, "list_scan_targets", _raise)

    result = await _start_scan(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "nothing_detected"}


@pytest.mark.asyncio
async def test_nothing_detected_form_survives_the_refresh_after_progress(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The manual form and its error stay when the step is re-invoked.

    Then choosing an add type again works as on a fresh flow.
    """
    monkeypatch.setattr(cf, "list_scan_targets", lambda _s=None: [SUBNETS[0]])
    monkeypatch.setattr(cf, "get_reefbeats", lambda **_kwargs: [])

    flow = cast(Any, hass.config_entries.flow)
    result = await drive_scan_to_end(hass, await _start_scan(hass))
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "nothing_detected"}

    again = cast(dict[str, Any], await flow.async_configure(result["flow_id"]))
    assert again["errors"] == {"base": "nothing_detected"}
    assert "ip_address" in str(again["data_schema"])


@pytest.mark.asyncio
async def test_scan_step_reentered_while_running_shows_progress_again(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-entering the step during a scan keeps the same task and dialog."""
    import asyncio

    gate = asyncio.Event()

    handler = cf.ReefBeatConfigFlow()
    handler.hass = hass

    async def _scan_one(_index: int, _cidr: str) -> list[Any]:
        await gate.wait()
        return []

    monkeypatch.setattr(cf, "list_scan_targets", lambda _s=None: [SUBNETS[0]])
    monkeypatch.setattr(handler, "_scan_one", _scan_one)

    first = cast(dict[str, Any], await handler.auto_detect(None))
    again = cast(dict[str, Any], await handler.async_step_scan())
    assert again["type"] == FlowResultType.SHOW_PROGRESS
    assert again["progress_task"] is first["progress_task"]

    # A report for a subnet that is not the current one is ignored, and a
    # cancelled scan is skipped like a failed one.
    handler._scan_report(5, 1, 1)
    assert handler._scan_last_percent == -1
    first["progress_task"].cancel()
    await asyncio.gather(first["progress_task"], return_exceptions=True)
    done = cast(dict[str, Any], await handler.async_step_scan())
    assert done["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert done["step_id"] == "scan_result"
