"""Coverage for the multi-select bulk-add flow in `async_step_select_devices`.

The bulk-add path is triggered when auto-detect finds several devices at once:
instead of the historic single-choice dropdown, the picker now shows every
device pre-checked so the user can submit them all in one gesture. The current
flow finalises with the *first* selected device, and each remaining device is
scheduled as a background import flow via
``hass.config_entries.flow.async_init(source=IMPORT)``.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_validation as cv

import custom_components.redsea.config_flow as cf
from custom_components.redsea.const import (
    ADD_LOCAL_DETECT,
    CONFIG_FLOW_ADD_TYPE,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
)


def _fake_devices() -> list[dict[str, str]]:
    """Three unrelated discovered devices — enough to check the fan-out size."""
    return [
        {
            "ip": "192.0.2.10",
            "hw_model": "RSLED50",
            "friendly_name": "Sump-LED",
            "uuid": "uuid-a",
        },
        {
            "ip": "192.0.2.11",
            "hw_model": "RSMAT",
            "friendly_name": "Mat",
            "uuid": "uuid-b",
        },
        {
            "ip": "192.0.2.12",
            "hw_model": "RSATO",
            "friendly_name": "ATO",
            "uuid": "uuid-c",
        },
    ]


@pytest.mark.asyncio
async def test_auto_detect_presents_all_devices_precchecked(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every discovered device shows up as a multi-select option, all checked."""
    monkeypatch.setattr(cf, "get_reefbeats", lambda *, subnetwork=None: _fake_devices())

    flow = cast(Any, hass.config_entries.flow)
    r1 = cast(dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"}))
    r2 = cast(
        dict[str, Any],
        await flow.async_configure(
            r1["flow_id"], user_input={CONFIG_FLOW_ADD_TYPE: ADD_LOCAL_DETECT}
        ),
    )

    assert r2["type"] == FlowResultType.FORM
    assert r2["step_id"] == "select_devices"

    # `str(schema)` prints the multi_select's <object at 0x...> repr, not its
    # options. Walk into the schema to extract the actual set of choices.
    schema = r2["data_schema"].schema
    multi = next(v for v in schema.values() if isinstance(v, cv.multi_select))
    options: dict[str, str] = cast(dict[str, str], multi.options)
    for dev in _fake_devices():
        assert cf._device_to_string(cast(Any, dev)) in options

    # Every option is pre-checked: the Required key carries a `default` list
    # equal to the full set of option keys.
    default_holder = next(
        k for k in schema if getattr(k, "schema", None) == CONFIG_FLOW_IP_ADDRESS
    )
    assert set(default_holder.default()) == set(options.keys())


@pytest.mark.asyncio
async def test_bulk_submit_fans_out_import_flows(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Submitting the multi-select must trigger one import flow per extra device.

    The three-device fixture should:
      - finish the current flow (or continue it via ``async_step_user``) with
        the first selected device
      - schedule two background ``async_init`` calls for the remaining two
    """
    monkeypatch.setattr(cf, "get_reefbeats", lambda *, subnetwork=None: _fake_devices())

    # Neutralise the per-device unique_id resolution so the "first device"
    # branch does not try to hit the network. The device string carries
    # `ip hw name` — the flow parses that itself, so we just short-circuit the
    # unique-id call to a stable value.
    monkeypatch.setattr(
        cf.ReefBeatConfigFlow, "_unique_id", AsyncMock(return_value="uuid-a")
    )

    # Capture the background fan-out. We wrap the real async_init so that the
    # first-device path still completes; the spy gives us call arguments and
    # the count.
    captured: list[dict[str, Any]] = []
    real_async_init: Any = hass.config_entries.flow.async_init

    async def _spy(
        domain: str,
        *,
        context: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        captured.append({"context": context, "data": data})
        # For import flows we don't need to actually run the import — the
        # scheduling itself is what we assert on.
        if context and context.get("source") == config_entries.SOURCE_IMPORT:
            return None
        return await real_async_init(domain, context=context, data=data)

    monkeypatch.setattr(hass.config_entries.flow, "async_init", _spy)

    flow = cast(Any, hass.config_entries.flow)
    r1 = cast(dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"}))
    r2 = cast(
        dict[str, Any],
        await flow.async_configure(
            r1["flow_id"], user_input={CONFIG_FLOW_ADD_TYPE: ADD_LOCAL_DETECT}
        ),
    )
    assert r2["step_id"] == "select_devices"

    # Rebuild the device strings the picker offered, in the same order.
    devices = _fake_devices()
    selected = [cf._device_to_string(cast(Any, d)) for d in devices]

    # Submit the multi-select with everything checked. The current flow
    # commits the first device (which we don't strictly assert on here because
    # ``async_create_entry`` returns a CREATE_ENTRY result, but the important
    # invariant is the fan-out below).
    await flow.async_configure(
        r2["flow_id"], user_input={CONFIG_FLOW_IP_ADDRESS: selected}
    )
    # Allow the scheduled background tasks to run so the spy sees them.
    await hass.async_block_till_done()

    import_calls = [
        c
        for c in captured
        if c["context"] and c["context"].get("source") == config_entries.SOURCE_IMPORT
    ]
    assert len(import_calls) == len(devices) - 1  # first device via current flow

    # Each import must ship a single-IP payload built from the raw device
    # string — so the reused user step can go through its unique_id resolution.
    imported_ips = {c["data"][CONFIG_FLOW_IP_ADDRESS] for c in import_calls}
    assert imported_ips == set(selected[1:])


@pytest.mark.asyncio
async def test_bulk_submit_with_empty_selection_aborts(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unchecking every box should abort the flow, not create a broken entry."""
    monkeypatch.setattr(cf, "get_reefbeats", lambda *, subnetwork=None: _fake_devices())

    flow = cast(Any, hass.config_entries.flow)
    r1 = cast(dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"}))
    r2 = cast(
        dict[str, Any],
        await flow.async_configure(
            r1["flow_id"], user_input={CONFIG_FLOW_ADD_TYPE: ADD_LOCAL_DETECT}
        ),
    )
    assert r2["step_id"] == "select_devices"

    # Submitting with an explicit empty list — voluptuous validates
    # `cv.multi_select` as any subset of the options including empty.
    r3 = cast(
        dict[str, Any],
        await flow.async_configure(
            r2["flow_id"], user_input={CONFIG_FLOW_IP_ADDRESS: []}
        ),
    )
    assert r3["type"] == FlowResultType.ABORT
    assert r3["reason"] == "nothing_detected"


@pytest.mark.asyncio
async def test_async_step_import_delegates_to_user_step(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The IMPORT entrypoint must forward its user_input to ``async_step_user``.

    The step is a one-line delegate; a full end-to-end IMPORT flow would call
    ``is_reefbeat`` via ``async_add_executor_job`` and thus a real
    ``requests.get()``, which pytest-socket blocks and treats as a leak.
    Instead we assert the delegation contract at the class level: replace
    ``async_step_user`` on the config-flow class with a spy that returns a
    terminal result (``async_abort``), then check that the IMPORT invocation
    routes through it with the exact payload we handed to ``async_init``.
    """
    captured: list[dict[str, Any] | None] = []

    async def _spy_user(
        self: cf.ReefBeatConfigFlow,
        user_input: dict[str, Any] | None = None,
    ) -> Any:
        captured.append(user_input)
        return self.async_abort(reason="mocked_by_test")

    monkeypatch.setattr(cf.ReefBeatConfigFlow, "async_step_user", _spy_user)

    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any],
        await flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONFIG_FLOW_IP_ADDRESS: "192.0.2.99"},
        ),
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "mocked_by_test"
    assert captured == [{CONFIG_FLOW_IP_ADDRESS: "192.0.2.99"}]
