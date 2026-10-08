"""Coverage for the use of the cloud account device list (cloud_devices.py).

- the account's devices proposed right after the account is validated, and
  from its options;
- the IP changes the account reports, applied automatically, proposed as a
  repair, or ignored;
- the repair flow moving an entry to its new address.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.selector import SelectSelector, SelectSelectorMode
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.auto_detect as ad
import custom_components.redsea.cloud_devices as cd
import custom_components.redsea.config_flow as cf
import custom_components.redsea.coordinator as coord
from custom_components.redsea import repairs
from custom_components.redsea.const import (
    ADD_CLOUD_API,
    CLOUD_DEVICE_TYPE,
    CLOUD_SCAN_INTERVAL,
    CLOUD_SERVER_ADDR,
    CONFIG_FLOW_ADD_TYPE,
    CONFIG_FLOW_CLOUD_DEVICES,
    CONFIG_FLOW_CLOUD_PASSWORD,
    CONFIG_FLOW_CLOUD_USERNAME,
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_DISABLE_SUPPLEMENT,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_IP_UPDATE,
    CONFIG_FLOW_SCAN_INTERVAL,
    DOMAIN,
    IP_UPDATE_AUTO,
    IP_UPDATE_OFF,
    IP_UPDATE_REPAIR,
    ISSUE_IP_CHANGED,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

WAVE = {
    "hwid": "bcddc285d9d3",
    "model": "RSWAVE45",
    "name": "RSWAVE45-8772051",
    "ip_address": "192.168.0.176",
    "connected": True,
}
RUN = {
    "hwid": "aabbccddeeff",
    "model": "RSRUN",
    "name": "RSRUN-1",
    "ip_address": "192.168.0.50",
    "connected": True,
}


def _info(device: dict[str, Any], uuid: str) -> ad.ReefBeatInfo:
    """What probing a device of the cloud list finds at its address."""
    return {
        "ip": str(device["ip_address"]),
        "hw_model": str(device["model"]),
        "friendly_name": str(device["name"]),
        "hwid": str(device["hwid"]),
        "uuid": uuid,
    }


def _patch_probe(
    monkeypatch: pytest.MonkeyPatch, by_ip: dict[str, ad.ReefBeatInfo | None]
) -> list[str]:
    """Probe answers from a {ip: info} table; returns the probed IPs."""
    probed: list[str] = []

    def _probe(ip: str) -> ad.ReefBeatInfo | None:
        probed.append(ip)
        return by_ip.get(ip)

    monkeypatch.setattr(cd, "probe_device", _probe)
    return probed


def _device_entry(
    hass: HomeAssistant, ip: str, uuid: str, model: str = "RSWAVE45"
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"{model}-dev",
        data={
            CONFIG_FLOW_IP_ADDRESS: ip,
            CONFIG_FLOW_HW_MODEL: model,
            CONFIG_FLOW_SCAN_INTERVAL: 60,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
        unique_id=uuid,
    )
    entry.add_to_hass(hass)
    return entry


def _cloud_entry(hass: HomeAssistant, **extra: Any) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="me@example.com",
        data={
            CONFIG_FLOW_IP_ADDRESS: CLOUD_SERVER_ADDR,
            CONFIG_FLOW_HW_MODEL: CLOUD_DEVICE_TYPE,
            CONFIG_FLOW_CLOUD_USERNAME: "me@example.com",
            CONFIG_FLOW_CLOUD_PASSWORD: "pw",
            CONFIG_FLOW_SCAN_INTERVAL: CLOUD_SCAN_INTERVAL,
            CONFIG_FLOW_CONFIG_TYPE: False,
            CONFIG_FLOW_DISABLE_SUPPLEMENT: True,
            **extra,
        },
        unique_id="me@example.com",
    )
    entry.add_to_hass(hass)
    return entry


# -----------------------------------------------------------------------------
# Cloud device list
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_account_devices(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The /device list is read with the account's token."""
    from custom_components.redsea.reefbeat import ReefBeatCloudAPI

    monkeypatch.setattr(ReefBeatCloudAPI, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(
        ReefBeatCloudAPI,
        "http_get",
        AsyncMock(return_value={"ok": True, "json": [WAVE, "junk"]}),
    )
    devices = await cd.async_fetch_account_devices(hass, "u", "p", CLOUD_SERVER_ADDR)
    assert devices == [WAVE]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "http_get",
    [
        AsyncMock(return_value=None),
        AsyncMock(return_value={"ok": False, "json": []}),
        AsyncMock(return_value={"ok": True, "json": {"not": "a list"}}),
        AsyncMock(side_effect=RuntimeError("boom")),
    ],
)
async def test_fetch_account_devices_unreadable(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, http_get: AsyncMock
) -> None:
    """Any failure gives None, never an exception."""
    from custom_components.redsea.reefbeat import ReefBeatCloudAPI

    monkeypatch.setattr(ReefBeatCloudAPI, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ReefBeatCloudAPI, "http_get", http_get)
    assert await cd.async_fetch_account_devices(hass, "u", "p", "x") is None


def test_local_devices_filters() -> None:
    """Only devices with an IP, a hwid and a known model are kept."""
    devices = [
        WAVE,
        {**WAVE, "ip_address": ""},
        {**WAVE, "model": "UNKNOWN"},
        {**WAVE, "hwid": None},
        "junk",
    ]
    assert cd.local_devices(devices) == [WAVE]
    assert cd.local_devices(None) == []


def test_probe_device(monkeypatch: pytest.MonkeyPatch) -> None:
    """probe_device reads /device-info and the UDN, hwid included."""
    response = MagicMock(status_code=200)
    response.json.return_value = {
        "hw_model": "RSWAVE45",
        "name": "Wave",
        "hwid": "BCDDC285D9D3",
    }
    monkeypatch.setattr(ad.requests, "get", MagicMock(return_value=response))
    monkeypatch.setattr(ad, "get_unique_id", lambda ip: "uuid-1")
    assert ad.probe_device("1.2.3.4") == {
        "ip": "1.2.3.4",
        "hw_model": "RSWAVE45",
        "friendly_name": "Wave",
        "hwid": "bcddc285d9d3",
        "uuid": "uuid-1",
    }

    # No UDN: no uuid key
    monkeypatch.setattr(ad, "get_unique_id", lambda ip: None)
    info = ad.probe_device("1.2.3.4")
    assert info is not None and "uuid" not in info

    # Unknown model, HTTP error, no answer
    response.json.return_value = {"hw_model": "TOASTER"}
    assert ad.probe_device("1.2.3.4") is None
    response.status_code = 404
    assert ad.probe_device("1.2.3.4") is None
    monkeypatch.setattr(ad.requests, "get", MagicMock(side_effect=OSError("down")))
    assert ad.probe_device("1.2.3.4") is None


# -----------------------------------------------------------------------------
# Adding the devices of an account
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_devices_split(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Configured devices are left out, unreachable ones listed apart."""
    moved = {**RUN, "hwid": "111111111111", "ip_address": "192.168.0.60"}
    other = {**RUN, "hwid": "222222222222", "ip_address": "192.168.0.61"}
    known_uid = {**RUN, "hwid": "333333333333", "ip_address": "192.168.0.62"}
    off = {**RUN, "hwid": "444444444444", "name": "", "ip_address": "192.168.0.63"}
    _device_entry(hass, str(RUN["ip_address"]), "uuid-run", "RSRUN")
    _device_entry(hass, "192.168.0.9", "uuid-known", "RSRUN")
    _patch_probe(
        monkeypatch,
        {
            str(WAVE["ip_address"]): _info(WAVE, "uuid-wave"),
            # another device answers at the reported address
            str(moved["ip_address"]): _info(other, "uuid-other"),
            str(known_uid["ip_address"]): _info(known_uid, "uuid-known"),
        },
    )
    # A loaded coordinator knows its hwid even when its IP changed
    hass.data.setdefault(DOMAIN, {})["x"] = MagicMock(model_id="555555555555")
    loaded = {**RUN, "hwid": "555555555555", "ip_address": "192.168.0.64"}

    found = await cd.async_account_devices(
        hass, [WAVE, RUN, moved, known_uid, off, loaded]
    )
    assert [d.get("hwid") for d in found.found] == [WAVE["hwid"]]
    assert found.unreachable == [
        f"{moved['name']} (192.168.0.60)",
        "444444444444 (192.168.0.63)",
    ]


def test_spawn_imports(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """One import flow per selected device."""
    init = AsyncMock()
    monkeypatch.setattr(hass.config_entries.flow, "async_init", init)
    created: list[Any] = []
    monkeypatch.setattr(hass, "async_create_task", lambda coro: created.append(coro))
    cd.spawn_imports(hass, ["1.1.1.1 RSRUN a", "2.2.2.2 RSRUN b"])
    assert len(created) == 2
    for coro in created:
        coro.close()
    assert [c.kwargs["data"] for c in init.call_args_list] == [
        {CONFIG_FLOW_IP_ADDRESS: "1.1.1.1 RSRUN a"},
        {CONFIG_FLOW_IP_ADDRESS: "2.2.2.2 RSRUN b"},
    ]


async def _start_cloud_flow(hass: HomeAssistant) -> dict[str, Any]:
    flow = cast(Any, hass.config_entries.flow)
    r1 = await flow.async_init(DOMAIN, context={"source": "user"})
    r2 = await flow.async_configure(
        r1["flow_id"], user_input={CONFIG_FLOW_ADD_TYPE: ADD_CLOUD_API}
    )
    return cast(
        dict[str, Any],
        await flow.async_configure(
            r2["flow_id"],
            user_input={
                CONFIG_FLOW_CLOUD_USERNAME: "me@example.com",
                CONFIG_FLOW_CLOUD_PASSWORD: "pw",
            },
        ),
    )


@pytest.fixture
def _cloud_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid credentials; the created cloud entry is not set up."""
    monkeypatch.setattr(cf, "validate_cloud_input", AsyncMock(return_value=True))
    monkeypatch.setattr(
        "custom_components.redsea.async_setup_entry", AsyncMock(return_value=True)
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("_cloud_ok")
async def test_cloud_flow_proposes_account_devices(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After login, reachable devices are proposed pre-checked, then added."""
    monkeypatch.setattr(
        cf, "async_fetch_account_devices", AsyncMock(return_value=[WAVE, RUN])
    )
    _patch_probe(monkeypatch, {str(WAVE["ip_address"]): _info(WAVE, "uuid-wave")})
    spawned: list[list[str]] = []
    monkeypatch.setattr(
        cf, "spawn_imports", lambda hass, values: spawned.append(values)
    )

    result = await _start_cloud_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    assert result["description_placeholders"] == {
        "count": "1",
        "unreachable": "RSRUN-1 (192.168.0.50)",
    }
    schema = result["data_schema"].schema
    selector = next(v for v in schema.values() if isinstance(v, SelectSelector))
    assert selector.config["mode"] == SelectSelectorMode.LIST
    value = cf._device_to_string(_info(WAVE, "uuid-wave"))
    assert [o["value"] for o in selector.config["options"]] == [value]
    key = next(k for k in schema if str(k) == CONFIG_FLOW_CLOUD_DEVICES)
    assert key.default() == [value]

    done = await cast(Any, hass.config_entries.flow).async_configure(
        result["flow_id"], user_input={CONFIG_FLOW_CLOUD_DEVICES: [value]}
    )
    assert done["type"] == FlowResultType.CREATE_ENTRY
    assert done["title"] == "me@example.com"
    assert done["data"][CONFIG_FLOW_IP_UPDATE] == IP_UPDATE_AUTO
    assert spawned == [[value]]


@pytest.mark.asyncio
@pytest.mark.usefixtures("_cloud_ok")
async def test_cloud_flow_without_devices_creates_entry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing to propose (or the list unreadable): the account is created."""
    monkeypatch.setattr(cf, "async_fetch_account_devices", AsyncMock(return_value=None))
    result = await _start_cloud_flow(hass)
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def _open_cloud_options(hass: HomeAssistant, entry: MockConfigEntry) -> Any:
    menu = cast(Any, await hass.config_entries.options.async_init(entry.entry_id))
    assert menu["type"] == FlowResultType.MENU
    return await hass.config_entries.options.async_configure(
        menu["flow_id"], user_input={"next_step_id": "cloud_devices"}
    )


@pytest.mark.asyncio
async def test_options_add_account_devices(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The options of the account add its new devices, without reloading it."""
    entry = _cloud_entry(hass)
    monkeypatch.setattr(
        cf, "async_fetch_account_devices", AsyncMock(return_value=[WAVE])
    )
    _patch_probe(monkeypatch, {str(WAVE["ip_address"]): _info(WAVE, "uuid-wave")})
    spawned: list[list[str]] = []
    monkeypatch.setattr(
        cf, "spawn_imports", lambda hass, values: spawned.append(values)
    )

    result = await _open_cloud_options(hass, entry)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    value = cf._device_to_string(_info(WAVE, "uuid-wave"))
    done = cast(
        Any,
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONFIG_FLOW_CLOUD_DEVICES: [value]}
        ),
    )
    assert done["type"] == FlowResultType.ABORT
    assert done["reason"] == "cloud_devices_added"
    assert spawned == [[value]]
    assert entry.options == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("devices", "reason"),
    [(None, "cloud_devices_unavailable"), ([], "cloud_devices_none")],
)
async def test_options_account_devices_nothing(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    devices: list[Any] | None,
    reason: str,
) -> None:
    entry = _cloud_entry(hass)
    monkeypatch.setattr(
        cf, "async_fetch_account_devices", AsyncMock(return_value=devices)
    )
    result = await _open_cloud_options(hass, entry)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == reason


@pytest.mark.asyncio
async def test_options_settings_offers_ip_update(hass: HomeAssistant) -> None:
    """The account settings choose how IP changes are handled."""
    entry = _cloud_entry(hass, **{CONFIG_FLOW_IP_UPDATE: IP_UPDATE_REPAIR})
    menu = cast(Any, await hass.config_entries.options.async_init(entry.entry_id))
    form = cast(
        Any,
        await hass.config_entries.options.async_configure(
            menu["flow_id"], user_input={"next_step_id": "settings"}
        ),
    )
    assert form["step_id"] == "settings"
    key = next(k for k in form["data_schema"].schema if str(k) == CONFIG_FLOW_IP_UPDATE)
    assert key.default() == IP_UPDATE_REPAIR


# -----------------------------------------------------------------------------
# Following IP changes
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ip_tracker_auto_updates_entry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A device answering at its new cloud IP gets its entry moved."""
    entry = _device_entry(hass, "192.168.0.10", "uuid-wave")
    probed = _patch_probe(
        monkeypatch, {str(WAVE["ip_address"]): _info(WAVE, "uuid-wave")}
    )
    tracker = cd.IpTracker(hass)

    await tracker.async_check([WAVE], IP_UPDATE_AUTO)
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == WAVE["ip_address"]

    # Now configured at that address: no probe any more
    await tracker.async_check([WAVE], IP_UPDATE_AUTO)
    assert probed == [WAVE["ip_address"]]


@pytest.mark.asyncio
async def test_ip_tracker_repair_mode_raises_issue(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In repair mode the move is proposed, not applied, and not re-probed."""
    entry = _device_entry(hass, "192.168.0.10", "uuid-wave")
    probed = _patch_probe(
        monkeypatch, {str(WAVE["ip_address"]): _info(WAVE, "uuid-wave")}
    )
    tracker = cd.IpTracker(hass)

    await tracker.async_check([WAVE], IP_UPDATE_REPAIR)
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == "192.168.0.10"
    issue = ir.async_get(hass).async_get_issue(DOMAIN, cd.ip_issue_id(entry.entry_id))
    assert issue is not None
    assert issue.translation_key == ISSUE_IP_CHANGED
    assert issue.translation_placeholders == {
        "device": entry.title,
        "old_ip": "192.168.0.10",
        "new_ip": WAVE["ip_address"],
    }
    await tracker.async_check([WAVE], IP_UPDATE_REPAIR)
    assert probed == [WAVE["ip_address"]]

    # Moved by hand meanwhile: the proposal goes away
    hass.config_entries.async_update_entry(
        cast(Any, entry),
        data={**entry.data, CONFIG_FLOW_IP_ADDRESS: WAVE["ip_address"]},
    )
    await tracker.async_check([WAVE], IP_UPDATE_REPAIR)
    assert (
        ir.async_get(hass).async_get_issue(DOMAIN, cd.ip_issue_id(entry.entry_id))
        is None
    )


@pytest.mark.asyncio
async def test_ip_tracker_ignores_untrusted_addresses(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Offline in the cloud, another device there, nobody there, unknown
    device, or tracking off: the entry is never touched."""
    entry = _device_entry(hass, "192.168.0.10", "uuid-wave")
    other_ip = "192.168.0.77"
    probed = _patch_probe(
        monkeypatch,
        {
            other_ip: _info({**RUN, "ip_address": other_ip}, "uuid-run"),
            str(RUN["ip_address"]): _info(RUN, "uuid-not-configured"),
        },
    )
    tracker = cd.IpTracker(hass)

    await tracker.async_check([{**WAVE, "connected": False}], IP_UPDATE_AUTO)
    assert probed == []
    await tracker.async_check([{**WAVE, "ip_address": other_ip}], IP_UPDATE_AUTO)
    await tracker.async_check([{**WAVE, "ip_address": "192.168.0.88"}], IP_UPDATE_AUTO)
    # Same device not configured in Home Assistant
    await tracker.async_check([RUN], IP_UPDATE_AUTO)
    await tracker.async_check([RUN], IP_UPDATE_AUTO)  # cached, not re-probed
    await tracker.async_check([WAVE], IP_UPDATE_OFF)
    assert probed == [other_ip, "192.168.0.88", RUN["ip_address"]]
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == "192.168.0.10"


@pytest.mark.asyncio
async def test_ip_tracker_single_run(hass: HomeAssistant) -> None:
    """A check still running is not started again."""
    tracker = cd.IpTracker(hass)
    tracker._running = True
    tracker._async_check = AsyncMock()  # type: ignore[method-assign]
    await tracker.async_check([WAVE], IP_UPDATE_AUTO)
    tracker._async_check.assert_not_called()


def test_cloud_coordinator_schedules_ip_check() -> None:
    """The account refresh starts the check in the background, unless off."""
    obj = cast(Any, object.__new__(coord.ReefBeatCloudCoordinator))
    obj._hass = MagicMock()
    obj._title = "me"
    obj._ip_tracker = MagicMock()
    obj.get_data = MagicMock(return_value=[WAVE])

    obj._entry = MagicMock(data={})
    coord.ReefBeatCloudCoordinator._check_device_ips(obj)
    obj._ip_tracker.async_check.assert_called_once_with([WAVE], IP_UPDATE_AUTO)
    obj._entry.async_create_background_task.assert_called_once()

    obj._entry = MagicMock(data={CONFIG_FLOW_IP_UPDATE: IP_UPDATE_OFF})
    coord.ReefBeatCloudCoordinator._check_device_ips(obj)
    obj._entry.async_create_background_task.assert_not_called()


# -----------------------------------------------------------------------------
# Repair flow
# -----------------------------------------------------------------------------


async def _fix_flow(hass: HomeAssistant, entry_id: str, new_ip: str) -> Any:
    flow = await repairs.async_create_fix_flow(
        hass,
        cd.ip_issue_id(entry_id),
        {"kind": ISSUE_IP_CHANGED, "entry_id": entry_id, "new_ip": new_ip},
    )
    flow.hass = hass
    flow.issue_id = cd.ip_issue_id(entry_id)
    return flow


@pytest.mark.asyncio
async def test_repair_flow_moves_entry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _device_entry(hass, "192.168.0.10", "uuid-wave")
    new_ip = str(WAVE["ip_address"])
    _patch_probe(monkeypatch, {new_ip: _info(WAVE, "uuid-wave")})
    await cd.IpTracker(hass).async_check([WAVE], IP_UPDATE_REPAIR)

    flow = await _fix_flow(hass, entry.entry_id, new_ip)
    assert isinstance(flow, repairs.IpChangedRepairFlow)
    form = cast(Any, await flow.async_step_init())
    assert form["step_id"] == "confirm"
    assert form["description_placeholders"]["new_ip"] == new_ip
    done = cast(Any, await flow.async_step_confirm({}))
    assert done["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == new_ip
    assert ir.async_get(hass).async_get_issue(DOMAIN, flow.issue_id) is None


@pytest.mark.asyncio
async def test_repair_flow_device_gone_or_entry_gone(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _device_entry(hass, "192.168.0.10", "uuid-wave")
    new_ip = str(WAVE["ip_address"])

    # Another device answers there now
    _patch_probe(monkeypatch, {new_ip: _info(WAVE, "uuid-other")})
    flow = await _fix_flow(hass, entry.entry_id, new_ip)
    done = await flow.async_step_confirm({})
    assert done["reason"] == "device_not_found"
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == "192.168.0.10"

    flow = await _fix_flow(hass, "missing", new_ip)
    done = await flow.async_step_confirm({})
    assert done["reason"] == "entry_gone"


@pytest.mark.asyncio
async def test_group_repairs_still_dispatched(hass: HomeAssistant) -> None:
    """Other issues keep their group fix flow."""
    flow = await repairs.async_create_fix_flow(
        hass, "x", {"kind": "group_no_cloud", "entry_id": "e"}
    )
    assert isinstance(flow, repairs.GroupRepairFlow)
