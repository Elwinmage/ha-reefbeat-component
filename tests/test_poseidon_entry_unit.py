"""Poseidon entry lifecycle and its switches, through Home Assistant."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryDisabler, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.poseidon import const
from custom_components.redsea.poseidon.keystore import DeviceKeys, KeyStore
from custom_components.redsea.poseidon.manager import Poseidon, get_poseidon
from tests._poseidon_fakes import HWID, SECRET, FakeCoordinator

DOMAIN = "redsea"
RELAY_URL = "192.0.2.1:1884"
ENTITY = "switch.wave_left_poseidon_mode"


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Poseidon",
        unique_id="poseidon",
        data={
            "poseidon": True,
            "port": 1884,
            "host": "192.0.2.1",
            "cloud_account": "c",
        },
    )


@pytest.fixture
async def setup(hass: HomeAssistant) -> Any:
    """A device in the registry with keys, and a Poseidon entry."""
    # The device's own entry (another domain: it must not be set up here)
    device_entry = MockConfigEntry(domain="test", data={})
    device_entry.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=device_entry.entry_id,
        identifiers={(DOMAIN, HWID)},
        name="Wave left",
    )
    store = KeyStore(hass)
    await store.async_upsert(
        DeviceKeys(hwid=HWID, api_key="key", api_secret=SECRET, ip="192.0.2.10")
    )
    entry = _entry()
    entry.add_to_hass(hass)
    with (
        patch.object(Poseidon, "async_start", AsyncMock()),
        patch.object(Poseidon, "async_stop", AsyncMock()),
    ):
        yield entry


async def _set_up(hass: HomeAssistant, entry: MockConfigEntry) -> Poseidon:
    # A real start loads the keys (async_start is mocked here)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    poseidon = get_poseidon(hass)
    assert poseidon is not None
    await poseidon.async_load()
    poseidon.async_add_new_switches()
    await hass.async_block_till_done()
    return poseidon


async def test_setup_creates_switches(
    hass: HomeAssistant, setup: MockConfigEntry
) -> None:
    poseidon = await _set_up(hass, setup)
    assert setup.state is ConfigEntryState.LOADED
    state = hass.states.get(ENTITY)
    # The device's coordinator is not loaded: unavailable
    assert state is not None and state.state == "unavailable"

    wave = FakeCoordinator(cloud={"url": RELAY_URL, "connection_state": "CONNECTED"})
    hass.data.setdefault(DOMAIN, {})["wave"] = wave
    async_dispatcher_send(hass, const.SIGNAL_POSEIDON_UPDATE)
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == "on"
    assert state.attributes["connection_state"] == "CONNECTED"
    assert state.attributes["last_up"] is None
    assert state.attributes["icon"] == "redsea:trident"

    poseidon.relay._seen(HWID, "up")
    poseidon.relay._seen(HWID, "down")
    wave.cloud = {"url": "mqtt.reef-beat.com:1883"}
    async_dispatcher_send(hass, const.SIGNAL_POSEIDON_UPDATE)
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY)
    assert state is not None and state.state == "off"
    assert state.attributes["last_up"] and state.attributes["last_down"]

    with patch.object(Poseidon, "async_switch", AsyncMock(return_value=True)) as switch:
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": ENTITY}, blocking=True
        )
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": ENTITY}, blocking=True
        )
    assert [c.args for c in switch.await_args_list] == [(HWID, True), (HWID, False)]


async def test_port_taken_retries_with_issue(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    with (
        patch.object(Poseidon, "async_start", AsyncMock(side_effect=OSError("in use"))),
        patch.object(Poseidon, "async_stop", AsyncMock()),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    issue = ir.async_get(hass).async_get_issue(DOMAIN, const.ISSUE_PORT_IN_USE)
    assert issue is not None and issue.translation_placeholders == {"port": "1884"}
    assert get_poseidon(hass) is None


async def test_reload_leaves_devices(
    hass: HomeAssistant, setup: MockConfigEntry
) -> None:
    await _set_up(hass, setup)
    with patch.object(
        Poseidon, "async_revert_all", AsyncMock(return_value=[])
    ) as revert:
        assert await hass.config_entries.async_reload(setup.entry_id)
        await hass.async_block_till_done()
    revert.assert_not_called()


async def test_disable_switches_devices_back(
    hass: HomeAssistant, setup: MockConfigEntry
) -> None:
    await _set_up(hass, setup)
    with (
        patch.object(
            Poseidon, "async_revert_all", AsyncMock(return_value=["Wave"])
        ) as revert,
        patch(
            "homeassistant.components.persistent_notification.async_create"
        ) as notify,
    ):
        await hass.config_entries.async_set_disabled_by(
            setup.entry_id, ConfigEntryDisabler.USER
        )
        await hass.async_block_till_done()
    revert.assert_awaited_once()
    assert get_poseidon(hass) is None
    # The devices that could not be switched back are named
    assert "Wave" in notify.call_args.args[1]
    assert notify.call_args.kwargs["notification_id"] == "redsea_poseidon_revert"


async def test_remove_switches_devices_back(
    hass: HomeAssistant, setup: MockConfigEntry
) -> None:
    await _set_up(hass, setup)
    with patch.object(
        Poseidon, "async_revert_all", AsyncMock(return_value=[])
    ) as revert:
        assert (await hass.config_entries.async_remove(setup.entry_id))[
            "require_restart"
        ] is False
        await hass.async_block_till_done()
    revert.assert_awaited_once()
    # The keys stay
    store = KeyStore(hass)
    await store.async_load()
    assert store.get(HWID) is not None


async def test_unload_without_running_poseidon(
    hass: HomeAssistant, setup: MockConfigEntry
) -> None:
    await _set_up(hass, setup)
    hass.data.pop(const.DATA_POSEIDON)
    assert await hass.config_entries.async_unload(setup.entry_id)


async def test_switch_platform_without_poseidon(hass: HomeAssistant) -> None:
    from custom_components.redsea import switch

    added: list[Any] = []
    await switch.async_setup_entry(hass, _entry(), added.append)  # type: ignore[arg-type]
    assert added == []


async def test_export_service(
    hass: HomeAssistant, setup: MockConfigEntry, tmp_path: Any
) -> None:
    from homeassistant.exceptions import ServiceValidationError

    await _set_up(hass, setup)
    poseidon = get_poseidon(hass)
    assert poseidon is not None
    exported = tmp_path / "keystore.json"
    with patch.object(Poseidon, "async_export", AsyncMock(return_value=exported)):
        response = await hass.services.async_call(
            DOMAIN, const.SERVICE_EXPORT, {}, blocking=True, return_response=True
        )
    assert response == {"path": str(exported), "devices": 1}
    # Without a running Poseidon: refused
    hass.data.pop(const.DATA_POSEIDON)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, const.SERVICE_EXPORT, {}, blocking=True, return_response=True
        )


async def test_options_applied_live(
    hass: HomeAssistant, setup: MockConfigEntry
) -> None:
    await _set_up(hass, setup)
    with patch.object(Poseidon, "async_apply_options", AsyncMock()) as apply:
        hass.config_entries.async_update_entry(setup, options={const.CONF_DEBUG: True})
        await hass.async_block_till_done()
    apply.assert_awaited_once()


async def test_unload_stops_when_platforms_refuse(
    hass: HomeAssistant, setup: MockConfigEntry
) -> None:
    from custom_components.redsea.poseidon import async_unload_poseidon

    await _set_up(hass, setup)
    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    ):
        assert await async_unload_poseidon(hass, setup) is False
    # Still running
    assert get_poseidon(hass) is not None
