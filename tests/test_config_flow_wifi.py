"""Integration tests for the Wi-Fi provisioning options flow.

These tests exercise the OptionsFlowHandler steps introduced by the Wi-Fi
provisioning feature:

- init dispatcher (menu vs. classic form based on entry kind)
- wifi_scan step (scan, form rendering, error handling, rescan checkbox)
- wifi_apply step (background task orchestration, all failure modes)
- wifi_finish abort with translation-friendly reasons

The Wi-Fi HTTP helpers themselves (scan_wifi/connect_wifi/reset_device/
rediscover_device) are covered by test_wifi_unit.py; here we mock them at the
module boundary and focus on flow shape.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.config_flow as cf
from custom_components.redsea.const import (
    CLOUD_DEVICE_TYPE,
    CLOUD_SERVER_ADDR,
    CONFIG_FLOW_CLOUD_PASSWORD,
    CONFIG_FLOW_CLOUD_USERNAME,
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_SCAN_INTERVAL,
    CONFIG_FLOW_WIFI_MANUAL_SUBNET,
    CONFIG_FLOW_WIFI_PASSWORD,
    CONFIG_FLOW_WIFI_RESCAN,
    CONFIG_FLOW_WIFI_SSID,
    DOMAIN,
    LINKED_LED,
    VIRTUAL_LED,
    VIRTUAL_LED_SCAN_INTERVAL,
)


@pytest.fixture(autouse=True)
def _mock_aiohttp_client_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out ``async_get_clientsession`` in the flow module.

    The real helper would allocate an aiohttp ``ClientSession`` (and its DNS
    resolver thread) — those are unused here since we patch every helper that
    would touch the network, but they would leak a background thread and
    fail pytest-homeassistant-custom-component's lingering-thread check.
    """
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        cf, "async_get_clientsession", lambda hass: MagicMock(name="stub-session")
    )


@pytest.fixture(autouse=True)
def _stub_get_current_ssid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default ``get_current_ssid`` to None so it never touches the network.

    Tests that specifically exercise pre-selection override this with their
    own fake returning a concrete SSID. Everything else gets "no current
    SSID", which keeps the SSID field un-defaulted exactly as before this
    feature existed.
    """

    async def _no_current_ssid(session: Any, ip: str) -> str | None:
        return None

    monkeypatch.setattr(cf, "get_current_ssid", _no_current_ssid)


# =============================================================================
# Helpers
# =============================================================================


def _sample_networks() -> list[dict[str, Any]]:
    """Two networks; one is the strong home SSID, one is a neighbour."""
    return [
        {
            "ssid": "ELWINMAGE",
            "channel": 9,
            "bssid": "9A:18:65:72:D8:70",
            "signal_dBm": -36,
            "security": "WPA2_PSK",
        },
        {
            "ssid": "NEIGHBOUR",
            "channel": 1,
            "bssid": "AA:BB:CC:DD:EE:FF",
            "signal_dBm": -85,
            "security": "WPA2_PSK",
        },
    ]


def _local_led_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="My LED",
        data={
            CONFIG_FLOW_IP_ADDRESS: "192.0.2.10",
            CONFIG_FLOW_HW_MODEL: "RSLED160",
            CONFIG_FLOW_SCAN_INTERVAL: 120,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
        unique_id="uuid-of-my-led",
    )
    entry.add_to_hass(hass)
    return entry


async def _patch_no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass all real sleeps in the config_flow module to keep tests instant."""

    async def _no_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(cf.asyncio, "sleep", _no_sleep)


# =============================================================================
# init dispatcher
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_local_device_shows_menu(hass: HomeAssistant) -> None:
    """Local devices with a known hw_model land on the settings/wifi menu."""
    entry = _local_led_entry(hass)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    assert result["type"] == FlowResultType.MENU
    assert set(result["menu_options"]) == {"settings", "wifi_scan"}


@pytest.mark.asyncio
async def test_options_flow_cloud_skips_menu(hass: HomeAssistant) -> None:
    """Cloud accounts go straight to the classic form (no Wi-Fi option)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Cloud",
        data={
            CONFIG_FLOW_IP_ADDRESS: CLOUD_SERVER_ADDR,
            CONFIG_FLOW_HW_MODEL: CLOUD_DEVICE_TYPE,
            CONFIG_FLOW_CLOUD_USERNAME: "u",
            CONFIG_FLOW_CLOUD_PASSWORD: "p",
            CONFIG_FLOW_SCAN_INTERVAL: 60,
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
        unique_id="cloud-uid",
    )
    entry.add_to_hass(hass)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    assert result["type"] == FlowResultType.FORM
    # No menu payload.
    assert "menu_options" not in result


@pytest.mark.asyncio
async def test_options_flow_virtual_led_skips_menu(hass: HomeAssistant) -> None:
    """Virtual LED entries also skip the menu."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"{VIRTUAL_LED}-42",
        data={
            CONFIG_FLOW_IP_ADDRESS: VIRTUAL_LED,
            CONFIG_FLOW_HW_MODEL: VIRTUAL_LED,
            CONFIG_FLOW_SCAN_INTERVAL: VIRTUAL_LED_SCAN_INTERVAL,
            LINKED_LED: {},
        },
        unique_id="vled-uid",
    )
    entry.add_to_hass(hass)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    assert result["type"] == FlowResultType.FORM


@pytest.mark.asyncio
async def test_options_flow_menu_settings_shows_settings_form(
    hass: HomeAssistant,
) -> None:
    """Selecting 'settings' from the menu shows the classic settings form."""
    entry = _local_led_entry(hass)
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    assert result["type"] == FlowResultType.MENU

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "settings"}
        ),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "settings"


# =============================================================================
# wifi_scan step — form rendering and errors
# =============================================================================


@pytest.mark.asyncio
async def test_wifi_scan_success_shows_form_with_ssids(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Successful scan populates the SSID dropdown."""
    entry = _local_led_entry(hass)

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        assert ip == "192.0.2.10"
        return _sample_networks()

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "wifi_scan"
    schema_keys = {str(k) for k in result["data_schema"].schema}
    assert CONFIG_FLOW_WIFI_SSID in " ".join(schema_keys)
    assert CONFIG_FLOW_WIFI_PASSWORD in " ".join(schema_keys)
    assert CONFIG_FLOW_WIFI_RESCAN in " ".join(schema_keys)


def _ssid_field_default(result: dict[str, Any]) -> Any:
    """Return the voluptuous default value of the SSID field, or None.

    voluptuous stores an ``Optional`` default as a zero-arg callable on the
    marker; ``vol.UNDEFINED`` means no default was set.
    """
    import voluptuous as vol

    for key in result["data_schema"].schema:
        if str(key) == CONFIG_FLOW_WIFI_SSID:
            if key.default is vol.UNDEFINED:
                return None
            return key.default()
    return None


@pytest.mark.asyncio
async def test_wifi_scan_preselects_current_ssid(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The SSID the device is currently on is pre-selected in the dropdown."""
    entry = _local_led_entry(hass)

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return _sample_networks()

    async def _fake_current(session: Any, ip: str) -> str | None:
        return "ELWINMAGE"

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)
    monkeypatch.setattr(cf, "get_current_ssid", _fake_current)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )

    assert result["type"] == FlowResultType.FORM
    # The current SSID (present in the scan results) is the field default.
    assert _ssid_field_default(result) == "ELWINMAGE"


@pytest.mark.asyncio
async def test_wifi_scan_no_default_when_current_ssid_absent_from_scan(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the current SSID isn't in the scan list, no default is set.

    Defaulting to a value absent from the ``vol.In`` option set would make
    the form fail validation, so the field must stay un-defaulted.
    """
    entry = _local_led_entry(hass)

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return _sample_networks()  # ELWINMAGE + NEIGHBOR_5G

    async def _fake_current(session: Any, ip: str) -> str | None:
        # A network the scan did not return (device can't always see its own).
        return "HIDDEN_NET"

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)
    monkeypatch.setattr(cf, "get_current_ssid", _fake_current)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )

    assert result["type"] == FlowResultType.FORM
    assert _ssid_field_default(result) is None


@pytest.mark.asyncio
async def test_wifi_scan_no_default_when_current_ssid_unknown(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the device doesn't report a current SSID, no default is set."""
    entry = _local_led_entry(hass)

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return _sample_networks()

    async def _fake_current(session: Any, ip: str) -> str | None:
        return None

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)
    monkeypatch.setattr(cf, "get_current_ssid", _fake_current)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )

    assert result["type"] == FlowResultType.FORM
    assert _ssid_field_default(result) is None


@pytest.mark.asyncio
async def test_wifi_scan_http_error_shows_error(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scan failure surfaces as a base error on the same form."""
    entry = _local_led_entry(hass)

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        raise RuntimeError("device offline")

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "wifi_scan_failed"}


@pytest.mark.asyncio
async def test_wifi_scan_empty_shows_no_networks_error(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the device reports zero networks, we tell the user."""
    entry = _local_led_entry(hass)

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return []

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "wifi_no_networks"}


@pytest.mark.asyncio
async def test_wifi_scan_rescan_reruns_scan(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ticking the rescan checkbox triggers a fresh scan."""
    entry = _local_led_entry(hass)

    scan_calls = {"n": 0}

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        scan_calls["n"] += 1
        return _sample_networks()

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)

    # Reach the form
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )
    assert scan_calls["n"] == 1

    # Submit with rescan=True and empty ssid — expect a new scan, same form back.
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_WIFI_RESCAN: True},
        ),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "wifi_scan"
    assert scan_calls["n"] == 2


# =============================================================================
# wifi_apply — full apply flow with progress
# =============================================================================


@pytest.mark.asyncio
async def test_wifi_apply_success_updates_entry_ip(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Happy path: connect → reset → rediscover → entry.data.ip updated."""
    entry = _local_led_entry(hass)

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return _sample_networks()

    connect_args: dict[str, Any] = {}

    async def _fake_connect(session: Any, ip: str, ssid: str, pw: str) -> bool:
        connect_args.update({"ip": ip, "ssid": ssid, "pw": pw})
        return True

    async def _fake_reset(session: Any, ip: str) -> bool:
        return True

    rediscover_call: dict[str, Any] = {}

    async def _fake_rediscover(
        hass: Any,
        uuid: str | None,
        hw_model: str | None,
        friendly_name: str | None,
        max_attempts: int,
        interval: int,
        subnetworks: list[str | None] | None = None,
    ) -> str | None:
        rediscover_call.update(
            {
                "uuid": uuid,
                "hw_model": hw_model,
                "friendly_name": friendly_name,
                "subnetworks": subnetworks,
            }
        )
        return "192.0.2.99"

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)
    monkeypatch.setattr(cf, "connect_wifi", _fake_connect)
    monkeypatch.setattr(cf, "reset_device", _fake_reset)
    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover)
    # Ensure the executor call returns a deterministic subnet list; without
    # this the test would depend on the CI host's actual interfaces.
    monkeypatch.setattr(cf, "list_scannable_subnets", lambda: ["192.0.2.0/24"])
    await _patch_no_sleep(monkeypatch)

    # Drive the flow to wifi_scan
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )
    # Submit the SSID + password
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONFIG_FLOW_WIFI_SSID: "ELWINMAGE",
                CONFIG_FLOW_WIFI_PASSWORD: "sup3rs3cret",
                CONFIG_FLOW_WIFI_RESCAN: False,
            },
        ),
    )
    # Progress -> keep driving until the task settles
    await _drive_progress_to_end(hass, result)

    # Entry should now carry the new IP
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == "192.0.2.99"
    # And the helper calls received the expected arguments, including the
    # composed subnetworks list (default + enumerated locals).
    assert connect_args == {
        "ip": "192.0.2.10",
        "ssid": "ELWINMAGE",
        "pw": "sup3rs3cret",
    }
    assert rediscover_call["uuid"] == "uuid-of-my-led"
    assert rediscover_call["hw_model"] == "RSLED160"
    assert rediscover_call["friendly_name"] == "My LED"
    assert rediscover_call["subnetworks"] == [None, "192.0.2.0/24"]


@pytest.mark.asyncio
async def test_wifi_apply_connect_failure_aborts(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed /wifi/connect leaves the entry alone and aborts with the right reason."""
    entry = _local_led_entry(hass)
    original_ip = entry.data[CONFIG_FLOW_IP_ADDRESS]

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return _sample_networks()

    async def _fake_connect(session: Any, ip: str, ssid: str, pw: str) -> bool:
        return False

    called: dict[str, bool] = {"reset": False, "rediscover": False}

    async def _fake_reset(session: Any, ip: str) -> bool:
        called["reset"] = True
        return True

    async def _fake_rediscover(hass: Any, **kwargs: Any) -> str | None:
        called["rediscover"] = True
        return "10.0.0.99"

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)
    monkeypatch.setattr(cf, "connect_wifi", _fake_connect)
    monkeypatch.setattr(cf, "reset_device", _fake_reset)
    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover)
    monkeypatch.setattr(cf, "list_scannable_subnets", list)
    await _patch_no_sleep(monkeypatch)

    result = await _drive_to_apply(hass, entry.entry_id)
    result = await _drive_progress_to_end(hass, result)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "wifi_change_failed_connect"
    # Downstream helpers must not run when connect fails.
    assert called["reset"] is False
    assert called["rediscover"] is False
    # IP is left untouched.
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == original_ip


@pytest.mark.asyncio
async def test_wifi_apply_reset_failure_aborts(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed /reset yields the reset-specific abort reason."""
    entry = _local_led_entry(hass)

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return _sample_networks()

    async def _fake_connect(session: Any, ip: str, ssid: str, pw: str) -> bool:
        return True

    async def _fake_reset(session: Any, ip: str) -> bool:
        return False

    async def _fake_rediscover(hass: Any, **kwargs: Any) -> str | None:
        pytest.fail("rediscover must not be called when reset fails")

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)
    monkeypatch.setattr(cf, "connect_wifi", _fake_connect)
    monkeypatch.setattr(cf, "reset_device", _fake_reset)
    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover)
    monkeypatch.setattr(cf, "list_scannable_subnets", list)
    await _patch_no_sleep(monkeypatch)

    result = await _drive_to_apply(hass, entry.entry_id)
    result = await _drive_progress_to_end(hass, result)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "wifi_change_failed_reset"


@pytest.mark.asyncio
async def test_wifi_apply_rediscover_failure_shows_manual_subnet(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When auto-discovery fails, the flow offers the manual subnet form."""
    entry = _local_led_entry(hass)
    original_ip = entry.data[CONFIG_FLOW_IP_ADDRESS]

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return _sample_networks()

    async def _fake_connect(session: Any, ip: str, ssid: str, pw: str) -> bool:
        return True

    async def _fake_reset(session: Any, ip: str) -> bool:
        return True

    async def _fake_rediscover(hass: Any, **kwargs: Any) -> str | None:
        return None

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)
    monkeypatch.setattr(cf, "connect_wifi", _fake_connect)
    monkeypatch.setattr(cf, "reset_device", _fake_reset)
    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover)
    monkeypatch.setattr(cf, "list_scannable_subnets", lambda: ["192.0.2.0/24"])
    await _patch_no_sleep(monkeypatch)

    result = await _drive_to_apply(hass, entry.entry_id)
    result = await _drive_progress_to_end(hass, result)

    # No abort yet — we present the manual subnet form so the user can try
    # entering a CIDR HA can only reach through a router.
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "wifi_manual_subnet"
    schema_keys = {str(k) for k in result["data_schema"].schema}
    assert CONFIG_FLOW_WIFI_MANUAL_SUBNET in " ".join(schema_keys)
    # Placeholders expose the subnets we already tried, so the user can
    # avoid entering the same ones again.
    placeholders = result.get("description_placeholders") or {}
    assert "192.0.2.0/24" in placeholders.get("tried_subnets", "")
    assert placeholders.get("ssid") == "ELWINMAGE"
    # IP is left untouched until the user succeeds (or gives up).
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == original_ip


@pytest.mark.asyncio
async def test_wifi_apply_unknown_exception_aborts(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Any other exception yields the unknown-error abort."""
    entry = _local_led_entry(hass)

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return _sample_networks()

    async def _fake_connect(session: Any, ip: str, ssid: str, pw: str) -> bool:
        # Simulate an unexpected code path, e.g. a bug in a downstream helper.
        raise ValueError("boom")

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)
    monkeypatch.setattr(cf, "connect_wifi", _fake_connect)
    monkeypatch.setattr(cf, "reset_device", AsyncStub(True))
    monkeypatch.setattr(cf, "rediscover_device", AsyncStub("10.0.0.5"))
    monkeypatch.setattr(cf, "list_scannable_subnets", list)
    await _patch_no_sleep(monkeypatch)

    result = await _drive_to_apply(hass, entry.entry_id)
    result = await _drive_progress_to_end(hass, result)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "wifi_change_failed_unknown"


# =============================================================================
# Direct step exercises — targeted coverage for edge branches HA smooths over
# =============================================================================


@pytest.mark.asyncio
async def test_wifi_scan_missing_ssid_on_submit_shows_error(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Submitting the form with rescan=False and no ssid yields wifi_no_ssid."""
    entry = _local_led_entry(hass)

    scan_calls = {"n": 0}

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        scan_calls["n"] += 1
        return _sample_networks()

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)

    # Reach the form (first scan)
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry.entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )
    assert result["type"] == FlowResultType.FORM

    # Submit with rescan=False and NO ssid at all (matches real UI behaviour
    # where the field is omitted from the payload when unset). This should
    # surface the wifi_no_ssid error rather than proceeding to the apply step.
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONFIG_FLOW_WIFI_PASSWORD: "",
                CONFIG_FLOW_WIFI_RESCAN: False,
            },
        ),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "wifi_no_ssid"}


def test_wifi_scan_schema_skips_empty_ssid_entries() -> None:
    """Malformed cached networks (empty ssid) are skipped by the schema builder.

    This exercises the defensive `continue` in :meth:`_build_wifi_scan_schema`
    that guards against feeding an empty SSID into the vol.In options.
    """
    handler = cf.OptionsFlowHandler.__new__(cf.OptionsFlowHandler)
    handler._wifi_networks = [
        {"ssid": "", "signal_dBm": -50, "security": "WPA2_PSK"},
        {"ssid": "GOOD", "signal_dBm": -40, "security": "WPA2_PSK"},
    ]
    handler._wifi_current_ssid = None

    schema = handler._build_wifi_scan_schema()
    keys = " ".join(str(k) for k in schema.schema)
    assert CONFIG_FLOW_WIFI_SSID in keys
    # The vol.In options should have exactly one entry, the good one.
    ssid_marker = next(k for k in schema.schema if str(k) == CONFIG_FLOW_WIFI_SSID)
    validator = schema.schema[ssid_marker]
    # vol.In stores the mapping in `container`.
    assert list(validator.container.keys()) == ["GOOD"]


def test_wifi_scan_schema_defaults_to_current_ssid() -> None:
    """The schema builder defaults the SSID field to the device's current SSID."""
    import voluptuous as vol

    handler = cf.OptionsFlowHandler.__new__(cf.OptionsFlowHandler)
    handler._wifi_networks = [
        {"ssid": "GOOD", "signal_dBm": -40, "security": "WPA2_PSK"},
        {"ssid": "OTHER", "signal_dBm": -70, "security": "WPA2_PSK"},
    ]
    handler._wifi_current_ssid = "GOOD"

    schema = handler._build_wifi_scan_schema()
    ssid_marker = next(k for k in schema.schema if str(k) == CONFIG_FLOW_WIFI_SSID)
    assert ssid_marker.default is not vol.UNDEFINED
    assert ssid_marker.default() == "GOOD"


@pytest.mark.asyncio
async def test_wifi_apply_returns_show_progress_when_task_pending() -> None:
    """Directly exercise the ``async_show_progress`` branch of async_step_wifi_apply.

    Under the normal HA options-flow driver the show-progress state is
    invisible to callers — HA awaits the progress task and re-invokes the
    step before returning to :meth:`async_configure`. We call the step
    method directly on a handler with a still-pending task to prove the
    branch works.
    """
    from unittest.mock import MagicMock

    handler = cf.OptionsFlowHandler.__new__(cf.OptionsFlowHandler)
    handler._config_entry = MagicMock()
    handler._wifi_networks = []
    handler._wifi_task = None
    handler._wifi_selected_ssid = "SSID"
    handler._wifi_selected_password = "pw"
    handler._wifi_result_reason = None
    handler._wifi_new_ip = None
    handler.hass = MagicMock()

    async def _slow() -> str:
        await asyncio.sleep(1000)  # deliberately never finishes during this test
        return "unreached"

    pending_task = asyncio.create_task(_slow())

    def _fake_create_task(coro: Any) -> asyncio.Task[Any]:
        # The handler passes _do_wifi_apply() here; we don't run it in this
        # unit test, so close the coroutine to avoid a "never awaited"
        # RuntimeWarning, and hand back our controlled pending task.
        coro.close()
        return pending_task

    handler.hass.async_create_task = MagicMock(side_effect=_fake_create_task)

    sentinel = {"type": "progress", "step_id": "wifi_apply"}
    handler.async_show_progress = MagicMock(return_value=sentinel)

    try:
        result = await handler.async_step_wifi_apply()
        assert result is sentinel
        # Cleanup: cancel the never-finishing task the handler created.
    finally:
        pending_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await pending_task


# =============================================================================
# Manual subnet fallback step
# =============================================================================


async def _drive_to_manual_subnet(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, entry_id: str
) -> dict[str, Any]:
    """Advance an options flow to the ``wifi_manual_subnet`` form.

    Bootstraps the same monkeypatches every manual-subnet test needs
    (successful connect/reset, failed automatic rediscovery, no sleeps)
    and returns the result at the point the manual form is shown.
    """

    async def _fake_scan(session: Any, ip: str) -> list[dict[str, Any]]:
        return _sample_networks()

    async def _fake_connect(session: Any, ip: str, ssid: str, pw: str) -> bool:
        return True

    async def _fake_reset(session: Any, ip: str) -> bool:
        return True

    async def _fake_rediscover(hass: Any, **kwargs: Any) -> str | None:
        return None

    monkeypatch.setattr(cf, "scan_wifi", _fake_scan)
    monkeypatch.setattr(cf, "connect_wifi", _fake_connect)
    monkeypatch.setattr(cf, "reset_device", _fake_reset)
    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover)
    monkeypatch.setattr(cf, "list_scannable_subnets", lambda: ["192.0.2.0/24"])
    await _patch_no_sleep(monkeypatch)

    result = await _drive_to_apply(hass, entry_id)
    return await _drive_progress_to_end(hass, result)


@pytest.mark.asyncio
async def test_wifi_manual_subnet_found_updates_entry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Providing a CIDR that contains the device updates the entry and aborts success."""
    entry = _local_led_entry(hass)

    result = await _drive_to_manual_subnet(hass, monkeypatch, entry.entry_id)
    assert result["step_id"] == "wifi_manual_subnet"

    # Replace the rediscover fake with one that succeeds for the specific
    # CIDR the user is about to submit.
    called_with: dict[str, Any] = {}

    async def _fake_rediscover_found(hass: Any, **kwargs: Any) -> str | None:
        called_with.update(kwargs)
        return "10.0.0.42"

    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover_found)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_WIFI_MANUAL_SUBNET: "10.0.0.0/24"},
        ),
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "wifi_change_success"
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == "10.0.0.42"
    # Manual-step rediscovery is single-pass on the user-provided CIDR only.
    assert called_with["subnetworks"] == ["10.0.0.0/24"]
    assert called_with["max_attempts"] == 1


@pytest.mark.asyncio
async def test_wifi_manual_subnet_bad_cidr_reshows_form(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unparseable CIDR keeps the user on the form with an inline error."""
    entry = _local_led_entry(hass)

    result = await _drive_to_manual_subnet(hass, monkeypatch, entry.entry_id)

    # Rediscover must NOT be called when the CIDR is syntactically invalid.
    async def _fake_rediscover_forbidden(hass: Any, **kwargs: Any) -> str | None:
        pytest.fail(
            "rediscover_device must not be called for an invalid CIDR",
        )

    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover_forbidden)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_WIFI_MANUAL_SUBNET: "not-a-cidr"},
        ),
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "wifi_manual_subnet"
    assert result["errors"] == {"base": "wifi_bad_cidr"}


@pytest.mark.asyncio
async def test_wifi_manual_subnet_not_found_reshows_form(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid CIDR that doesn't contain the device keeps the form open for retry."""
    entry = _local_led_entry(hass)
    original_ip = entry.data[CONFIG_FLOW_IP_ADDRESS]

    result = await _drive_to_manual_subnet(hass, monkeypatch, entry.entry_id)

    async def _fake_rediscover_empty(hass: Any, **kwargs: Any) -> str | None:
        return None

    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover_empty)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_WIFI_MANUAL_SUBNET: "10.0.0.0/24"},
        ),
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "wifi_manual_subnet"
    assert result["errors"] == {"base": "wifi_manual_not_found"}
    # IP is left untouched until the user provides a working CIDR.
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == original_ip


@pytest.mark.asyncio
async def test_wifi_manual_subnet_empty_cancels(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Submitting an empty CIDR is the "give up" signal → abort the flow."""
    entry = _local_led_entry(hass)
    original_ip = entry.data[CONFIG_FLOW_IP_ADDRESS]

    result = await _drive_to_manual_subnet(hass, monkeypatch, entry.entry_id)

    # Whether or not rediscover would find something, an empty CIDR must
    # short-circuit before calling it.
    async def _fake_rediscover_never_called(hass: Any, **kwargs: Any) -> str | None:
        pytest.fail("rediscover_device must not be called when CIDR is empty")

    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover_never_called)

    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONFIG_FLOW_WIFI_MANUAL_SUBNET: ""},
        ),
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "wifi_change_failed_rediscover"
    assert entry.data[CONFIG_FLOW_IP_ADDRESS] == original_ip


@pytest.mark.asyncio
async def test_wifi_manual_subnet_shows_form_when_input_lacks_cidr_key(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-None user_input without our field must show the form, not cancel.

    During the progress -> form transition, Home Assistant re-invokes this
    step and (depending on the HA version) may pass a non-None ``user_input``
    that does not contain the manual-subnet field. That must NOT be treated
    as an empty "give up" submission — the step should render the form so the
    user can actually type a CIDR. Regression guard for the abort-instead-of
    -form bug seen on newer HA cores.
    """
    entry = _local_led_entry(hass)
    handler = cf.OptionsFlowHandler.__new__(cf.OptionsFlowHandler)
    handler._config_entry = cast(Any, entry)
    handler._wifi_selected_ssid = "ELWINMAGE"
    handler._wifi_manual_candidates = ["192.0.2.0/24"]

    async def _fake_rediscover_forbidden(hass: Any, **kwargs: Any) -> str | None:
        pytest.fail("rediscover_device must not run on a non-submission call")

    monkeypatch.setattr(cf, "rediscover_device", _fake_rediscover_forbidden)

    # Simulate HA re-invoking the step with a stray dict that lacks our field.
    result = cast(
        dict[str, Any],
        await handler.async_step_wifi_manual_subnet(user_input={"some_other": "x"}),
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "wifi_manual_subnet"
    # No inline error: this is a fresh form, not a rejected submission.
    assert not result.get("errors")


class AsyncStub:
    """Callable that returns a fixed value from an awaited call."""

    def __init__(self, value: Any) -> None:
        self._value = value

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._value


async def _drive_to_apply(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    """Advance an options flow through menu -> wifi_scan -> submit."""
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_init(entry_id),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "wifi_scan"}
        ),
    )
    result = cast(
        dict[str, Any],
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONFIG_FLOW_WIFI_SSID: "ELWINMAGE",
                CONFIG_FLOW_WIFI_PASSWORD: "pw",
                CONFIG_FLOW_WIFI_RESCAN: False,
            },
        ),
    )
    return result


async def _drive_progress_to_end(
    hass: HomeAssistant, result: dict[str, Any]
) -> dict[str, Any]:
    """Loop while the flow keeps returning a progress state.

    HA's flow manager re-drives progress steps automatically when the
    ``progress_task`` completes; in unit tests we need to await the flow
    manager scheduling one more iteration. Wait on ``progress_task`` if
    available, then poll ``async_configure`` until we reach a terminal state.

    We also call ``hass.async_block_till_done()`` between iterations so
    that the done-callbacks HA registers on the progress task fire before
    the next ``async_configure``. Without this, the flow can stay stuck on
    SHOW_PROGRESS even after the task has finished.
    """
    for _ in range(20):
        if result["type"] not in (
            FlowResultType.SHOW_PROGRESS,
            FlowResultType.SHOW_PROGRESS_DONE,
        ):
            return result

        task = result.get("progress_task")
        if isinstance(task, asyncio.Task) and not task.done():
            # Let the background work finish. Failures are meant to be
            # surfaced through the flow's abort reason, not raised out of
            # the driver.
            with contextlib.suppress(Exception):
                await task

        # Give HA a chance to run the task's done-callbacks (which is how
        # the flow manager notices the task finished and schedules the
        # step re-invocation).
        await hass.async_block_till_done()

        # Progress steps carry no user input; a follow-up async_configure is
        # what tells HA "please re-invoke the step now".
        result = cast(
            dict[str, Any],
            await hass.config_entries.options.async_configure(
                result["flow_id"], user_input=None
            ),
        )

    raise AssertionError(f"Progress step never terminated (last result: {result!r})")
