"""Coverage for the RSCONTROL probe add / delete / replace options-flow steps.

The steps are exercised directly on an ``OptionsFlowHandler`` (flow-id/handler
primed so ``async_show_form`` / ``async_create_entry`` / ``async_abort`` work
without the flow manager). A fake RSCONTROL coordinator stands in for the hub,
and ``async_schedule_reload`` is neutralised so a create step doesn't try to
reload an entry that was never set up.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea import config_flow
from custom_components.redsea.const import (
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_OLD_PROBE,
    CONFIG_FLOW_PROBE_TYPE,
    CONFIG_FLOW_PROBES,
    DOMAIN,
)


def _flow(hass: Any, coordinator: Any) -> config_flow.OptionsFlowHandler:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ctl",
        data={CONFIG_FLOW_HW_MODEL: "RSCONTROLPRO"},
        options={},
        unique_id="ctl-of",
    )
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    flow = config_flow.OptionsFlowHandler(cast(Any, entry))
    flow.hass = hass
    flow.handler = entry.entry_id
    flow.flow_id = "test-flow"
    flow.context = {}
    return flow


@pytest.fixture(autouse=True)
def _no_reload(monkeypatch: pytest.MonkeyPatch, hass: Any) -> None:
    monkeypatch.setattr(
        hass.config_entries, "async_schedule_reload", lambda *a, **k: None
    )


# ---------------------------------------------------------------------------
# add_probe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_probe_form_then_success(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.async_install_probe = AsyncMock(return_value="0xNEW")
    flow = _flow(hass, coordinator)

    # No input -> the type-picker form.
    form = cast(dict[str, Any], await flow.async_step_add_probe())
    assert form["type"] == FlowResultType.FORM
    assert form["step_id"] == "add_probe"

    # A type that pairs -> entry created (and a reload scheduled).
    res = cast(
        dict[str, Any],
        await flow.async_step_add_probe({CONFIG_FLOW_PROBE_TYPE: "temperature"}),
    )
    assert res["type"] == FlowResultType.CREATE_ENTRY
    coordinator.async_install_probe.assert_awaited_once_with("temperature")


@pytest.mark.asyncio
async def test_add_probe_nothing_found_shows_error(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.async_install_probe = AsyncMock(return_value=None)
    flow = _flow(hass, coordinator)

    res = cast(
        dict[str, Any], await flow.async_step_add_probe({CONFIG_FLOW_PROBE_TYPE: "ph"})
    )
    assert res["type"] == FlowResultType.FORM
    assert res["errors"] == {"base": "no_probe_detected"}
    assert res["description_placeholders"]["probe_type"] == "ph"


@pytest.mark.asyncio
async def test_add_probe_install_raises_is_handled(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.async_install_probe = AsyncMock(side_effect=RuntimeError("boom"))
    flow = _flow(hass, coordinator)

    res = cast(
        dict[str, Any], await flow.async_step_add_probe({CONFIG_FLOW_PROBE_TYPE: "ec"})
    )
    assert res["type"] == FlowResultType.FORM
    assert res["errors"] == {"base": "no_probe_detected"}


# ---------------------------------------------------------------------------
# del_probe / del_probe_confirm
# ---------------------------------------------------------------------------


def _probes() -> list[dict[str, str]]:
    return [
        {"type": "temperature", "uid": "0xT", "name": "Sump Temp"},
        {"type": "ph", "uid": "0xP", "name": "pH"},
    ]


@pytest.mark.asyncio
async def test_del_probe_abends_without_probes(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.list_probes.return_value = []
    flow = _flow(hass, coordinator)

    res = cast(dict[str, Any], await flow.async_step_del_probe())
    assert res["type"] == FlowResultType.ABORT
    assert res["reason"] == "no_probes"


@pytest.mark.asyncio
async def test_del_probe_form_and_empty_selection(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.list_probes.return_value = _probes()
    flow = _flow(hass, coordinator)

    form = cast(dict[str, Any], await flow.async_step_del_probe())
    assert form["type"] == FlowResultType.FORM

    # Submitting an empty selection aborts.
    res = cast(
        dict[str, Any], await flow.async_step_del_probe({CONFIG_FLOW_PROBES: []})
    )
    assert res["type"] == FlowResultType.ABORT


@pytest.mark.asyncio
async def test_del_probe_confirm_deletes_selected(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.list_probes.return_value = _probes()
    coordinator.async_delete_probe = AsyncMock()
    flow = _flow(hass, coordinator)

    # Choose a probe -> routed to the confirm step (a form).
    confirm = cast(
        dict[str, Any],
        await flow.async_step_del_probe({CONFIG_FLOW_PROBES: ["ph:0xP"]}),
    )
    assert confirm["type"] == FlowResultType.FORM
    assert confirm["step_id"] == "del_probe_confirm"

    # Confirming performs the deletion and creates the entry.
    res = cast(dict[str, Any], await flow.async_step_del_probe_confirm({}))
    assert res["type"] == FlowResultType.CREATE_ENTRY
    coordinator.async_delete_probe.assert_awaited_once_with("ph", "0xP")


@pytest.mark.asyncio
async def test_del_probe_confirm_tolerates_delete_error(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.list_probes.return_value = _probes()
    coordinator.async_delete_probe = AsyncMock(side_effect=RuntimeError("boom"))
    flow = _flow(hass, coordinator)

    await flow.async_step_del_probe({CONFIG_FLOW_PROBES: ["ph:0xP"]})
    res = cast(dict[str, Any], await flow.async_step_del_probe_confirm({}))
    # The error is swallowed; the flow still completes.
    assert res["type"] == FlowResultType.CREATE_ENTRY


# ---------------------------------------------------------------------------
# change_probe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_change_probe_abends_without_probes(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.list_probes.return_value = []
    flow = _flow(hass, coordinator)

    res = cast(dict[str, Any], await flow.async_step_change_probe())
    assert res["type"] == FlowResultType.ABORT


@pytest.mark.asyncio
async def test_change_probe_form_and_success(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.serial = "CTL123"
    coordinator.list_probes.return_value = _probes()
    coordinator.async_install_probe = AsyncMock(return_value="0xNEW")
    coordinator.async_delete_probe = AsyncMock()
    flow = _flow(hass, coordinator)

    form = cast(dict[str, Any], await flow.async_step_change_probe())
    assert form["type"] == FlowResultType.FORM

    res = cast(
        dict[str, Any],
        await flow.async_step_change_probe({CONFIG_FLOW_OLD_PROBE: "ph:0xP"}),
    )
    assert res["type"] == FlowResultType.CREATE_ENTRY
    coordinator.async_install_probe.assert_awaited_once_with("ph")
    coordinator.async_delete_probe.assert_awaited_once_with("ph", "0xP")


@pytest.mark.asyncio
async def test_change_probe_nothing_found_shows_error(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.list_probes.return_value = _probes()
    coordinator.async_install_probe = AsyncMock(return_value=None)
    flow = _flow(hass, coordinator)

    res = cast(
        dict[str, Any],
        await flow.async_step_change_probe({CONFIG_FLOW_OLD_PROBE: "ph:0xP"}),
    )
    assert res["type"] == FlowResultType.FORM
    assert res["errors"] == {"base": "no_probe_detected"}


@pytest.mark.asyncio
async def test_change_probe_install_raises_is_handled(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.list_probes.return_value = _probes()
    coordinator.async_install_probe = AsyncMock(side_effect=RuntimeError("boom"))
    flow = _flow(hass, coordinator)

    res = cast(
        dict[str, Any],
        await flow.async_step_change_probe({CONFIG_FLOW_OLD_PROBE: "ph:0xP"}),
    )
    assert res["type"] == FlowResultType.FORM
    assert res["errors"] == {"base": "no_probe_detected"}


# ---------------------------------------------------------------------------
# init menu — RSCONTROL exposes the probe management entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_menu_offers_probe_management_for_control(hass: Any) -> None:
    flow = _flow(hass, MagicMock())
    res = cast(dict[str, Any], await flow.async_step_init())
    assert res["type"] == FlowResultType.MENU
    for opt in ("add_probe", "change_probe", "del_probe"):
        assert opt in res["menu_options"]


@pytest.mark.asyncio
async def test_change_probe_delete_error_still_completes(hass: Any) -> None:
    coordinator = MagicMock()
    coordinator.serial = "CTL123"
    coordinator.list_probes.return_value = _probes()
    coordinator.async_install_probe = AsyncMock(return_value="0xNEW")
    # The old-probe delete raises -> swallowed, the flow still finishes.
    coordinator.async_delete_probe = AsyncMock(side_effect=RuntimeError("boom"))
    flow = _flow(hass, coordinator)

    res = cast(
        dict[str, Any],
        await flow.async_step_change_probe({CONFIG_FLOW_OLD_PROBE: "ph:0xP"}),
    )
    assert res["type"] == FlowResultType.CREATE_ENTRY
