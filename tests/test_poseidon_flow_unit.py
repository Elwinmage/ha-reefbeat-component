"""Poseidon config flow (creation) and options flow (menu, settings, adding
devices), through the mixins and through Home Assistant's flow manager."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import (
    ADD_POSEIDON,
    CONFIG_FLOW_ADD_TYPE,
    CONFIG_FLOW_CLOUD_USERNAME,
)
from custom_components.redsea.poseidon import const
from custom_components.redsea.poseidon import flow as flow_mod
from custom_components.redsea.poseidon.capture import CaptureReport
from custom_components.redsea.poseidon.flow import (
    PoseidonConfigFlowMixin,
    PoseidonOptionsFlowMixin,
)
from custom_components.redsea.poseidon.keystore import DeviceKeys
from custom_components.redsea.poseidon.manager import (
    STATUS_KEYS_NEEDED,
    STATUS_KEYS_OK,
    STATUS_NO_CLOUD,
    STATUS_POSEIDON,
    STATUS_UNREACHABLE,
)

DOMAIN = "redsea"
KEY = "abcdefghij012345"


def _result(kind: str, **kwargs: Any) -> dict[str, Any]:
    return {"type": kind, **kwargs}


class _ConfigFlow(PoseidonConfigFlowMixin):
    """The creation mixin with the FlowHandler methods its step calls."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.unique_ids: list[str] = []

    async def async_set_unique_id(self, unique_id: str) -> None:
        self.unique_ids.append(unique_id)

    def _abort_if_unique_id_configured(self) -> None:
        return

    def async_abort(self, **kwargs: Any) -> dict[str, Any]:
        return _result("abort", **kwargs)

    def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
        return _result("form", **kwargs)

    def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
        return _result("create_entry", **kwargs)


class _OptionsFlow(PoseidonOptionsFlowMixin):
    """The options mixin with the FlowHandler methods its steps call."""

    def __init__(self, hass: HomeAssistant, options: dict[str, Any] | None = None):
        self.hass = hass
        self.config_entry = SimpleNamespace(options=options or {})
        self._poseidon_init()

    def async_abort(self, **kwargs: Any) -> dict[str, Any]:
        return _result("abort", **kwargs)

    def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
        return _result("form", **kwargs)

    def async_show_menu(self, **kwargs: Any) -> dict[str, Any]:
        return _result("menu", **kwargs)

    def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
        return _result("create_entry", **kwargs)

    def async_show_progress(self, **kwargs: Any) -> dict[str, Any]:
        return _result("progress", **kwargs)

    def async_show_progress_done(self, **kwargs: Any) -> dict[str, Any]:
        return _result("progress_done", **kwargs)


class _Poseidon:
    """Stands for the manager in the options steps."""

    def __init__(self, devices: dict[str, tuple[DeviceKeys, str]]) -> None:
        # coordinator name -> (keys, status)
        self.devices = devices
        self.release = asyncio.Event()
        self.release.set()
        self.reports: list[CaptureReport] | BaseException = []
        self.added: list[list[str]] = []
        self.switches_added = 0

    def local_devices(self) -> list[str]:
        return list(self.devices)

    async def async_status(self, coordinator: str) -> str:
        return self.devices[coordinator][1]

    def device_keys(self, coordinator: str) -> DeviceKeys:
        return self.devices[coordinator][0]

    async def async_add_devices(self, hwids: list[str]) -> list[CaptureReport]:
        self.added.append(hwids)
        await self.release.wait()
        if isinstance(self.reports, BaseException):
            raise self.reports
        return self.reports

    def async_add_new_switches(self) -> None:
        self.switches_added += 1


def _keys(hwid: str, name: str = "", model: str = "", ip: str = "") -> DeviceKeys:
    return DeviceKeys(hwid=hwid, name=name, model=model, ip=ip)


def _cloud_account(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="me@example.com",
        data={CONFIG_FLOW_CLOUD_USERNAME: "me@example.com"},
    )
    entry.add_to_hass(hass)
    return entry


# ── Helpers ─────────────────────────────────────────────────────────────────


def test_helpers() -> None:
    assert flow_mod._valid_host("192.0.2.1")
    assert not flow_mod._valid_host("wave.local")
    assert flow_mod._default_strategy({}) == const.DEFAULT_STRATEGY
    assert flow_mod._default_strategy({const.CONF_STRATEGY: "reduced"}) == (
        const.STRATEGY_POSEIDON
    )
    assert flow_mod._default_strategy({const.CONF_STRATEGY: "bogus"}) == (
        const.DEFAULT_STRATEGY
    )
    assert flow_mod._default_strategy({const.CONF_STRATEGY: "shadow"}) == "shadow"
    dev = _keys("aa", name="Wave", model="RSWAVE45", ip="10.0.0.2")
    assert flow_mod._label(dev, STATUS_KEYS_OK) == "Wave · RSWAVE45 · 10.0.0.2"
    assert flow_mod._label(_keys("bb"), STATUS_KEYS_NEEDED) == "bb 🔑"
    assert flow_mod._report_line(CaptureReport("a", "A", ok=False, error="e")) == (
        "✗ A: e"
    )
    assert flow_mod._report_line(CaptureReport("a", "A", ok=True, error="w")) == (
        "⚠ A: w"
    )
    assert flow_mod._report_line(CaptureReport("a", "A", ok=True)) == "✓ A"


# ── Creation ────────────────────────────────────────────────────────────────


async def test_creation_needs_a_cloud_account(hass: HomeAssistant) -> None:
    flow: Any = _ConfigFlow(hass)
    result = await flow.async_step_poseidon()
    assert result["reason"] == "poseidon_no_cloud_account"
    assert flow.unique_ids == [const.POSEIDON_UNIQUE_ID]


async def test_creation_form_and_errors(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    account = _cloud_account(hass)
    monkeypatch.setattr(flow_mod, "find_free_port", lambda: 0)
    monkeypatch.setattr(flow_mod, "local_ip", lambda: "192.0.2.1")
    monkeypatch.setattr(flow_mod, "port_free", lambda port: port != 1885)
    flow: Any = _ConfigFlow(hass)

    # No free port found: the default one is proposed
    form = await flow.async_step_poseidon()
    assert form["type"] == "form" and form["errors"] == {}
    assert form["data_schema"]({}) == {
        const.CONF_PORT: const.DEFAULT_PORT,
        const.CONF_HOST: "192.0.2.1",
        const.CONF_CLOUD_ACCOUNT: account.entry_id,
    }

    base = {const.CONF_PORT: 1884, const.CONF_CLOUD_ACCOUNT: account.entry_id}
    form = await flow.async_step_poseidon({**base, const.CONF_HOST: "not-an-ip"})
    assert form["errors"] == {const.CONF_HOST: "invalid_host"}
    # The form keeps what was typed
    assert form["data_schema"]({})[const.CONF_HOST] == "not-an-ip"

    form = await flow.async_step_poseidon(
        {**base, const.CONF_PORT: 1885, const.CONF_HOST: "192.0.2.1"}
    )
    assert form["errors"] == {const.CONF_PORT: "port_in_use"}

    # The cloud account defaults to the first one
    created = await flow.async_step_poseidon(
        {const.CONF_PORT: 1884.0, const.CONF_HOST: " 192.0.2.1 "}
    )
    assert created["type"] == "create_entry"
    assert created["title"] == const.POSEIDON_TITLE
    assert created["data"] == {
        const.CONF_POSEIDON: True,
        const.CONF_PORT: 1884,
        const.CONF_HOST: "192.0.2.1",
        const.CONF_CLOUD_ACCOUNT: account.entry_id,
    }


async def test_user_step_routes_to_poseidon(hass: HomeAssistant) -> None:
    """The add-type choice of the integration's own flow leads here."""
    flow = cast(Any, hass.config_entries.flow)
    result = cast(
        dict[str, Any], await flow.async_init(DOMAIN, context={"source": "user"})
    )
    result = cast(
        dict[str, Any],
        await flow.async_configure(
            result["flow_id"], user_input={CONFIG_FLOW_ADD_TYPE: ADD_POSEIDON}
        ),
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "poseidon_no_cloud_account"


# ── Options: menu and settings ──────────────────────────────────────────────


async def test_options_of_the_entry_open_its_menu(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=const.POSEIDON_TITLE,
        unique_id=const.POSEIDON_UNIQUE_ID,
        data={
            const.CONF_POSEIDON: True,
            const.CONF_PORT: 1884,
            const.CONF_HOST: "192.0.2.1",
        },
    )
    entry.add_to_hass(hass)
    options = hass.config_entries.options
    menu = cast(dict[str, Any], await options.async_init(entry.entry_id))
    assert menu["type"] == FlowResultType.MENU
    assert menu["menu_options"] == [
        const.OPTIONS_MENU_ADD_DEVICES,
        const.OPTIONS_MENU_SETTINGS,
        const.OPTIONS_MENU_EXPORT,
        const.OPTIONS_MENU_IMPORT,
        const.OPTIONS_MENU_RESCUE,
    ]
    form = cast(
        dict[str, Any],
        await options.async_configure(
            menu["flow_id"], user_input={"next_step_id": const.OPTIONS_MENU_SETTINGS}
        ),
    )
    assert form["type"] == FlowResultType.FORM
    assert form["step_id"] == "settings_poseidon"
    done = cast(
        dict[str, Any],
        await options.async_configure(
            form["flow_id"],
            user_input={
                const.CONF_DEBUG: True,
                const.CONF_SILENT_MINUTES: 30,
                const.CONF_STRATEGY: const.STRATEGY_SHADOW,
                const.CONF_REDUCED_MINUTES: 5,
                const.CONF_WATCHDOG_KEY: KEY,
            },
        ),
    )
    assert done["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[const.CONF_STRATEGY] == const.STRATEGY_SHADOW
    assert entry.options[const.CONF_WATCHDOG_KEY] == KEY


async def test_settings(hass: HomeAssistant) -> None:
    flow: Any = _OptionsFlow(
        hass, {"other": 1, const.CONF_STRATEGY: "normal", const.CONF_DEBUG: True}
    )
    form = await flow.async_step_settings_poseidon()
    assert form["type"] == "form" and form["errors"] == {}
    assert form["description_placeholders"] == {"logs": const.FILES_DIR + "/logs"}
    defaults = form["data_schema"]({})
    assert defaults[const.CONF_DEBUG] is True
    assert defaults[const.CONF_SILENT_MINUTES] == const.DEFAULT_SILENT_MINUTES
    assert defaults[const.CONF_REDUCED_MINUTES] == const.DEFAULT_REDUCED_MINUTES
    assert defaults[const.CONF_SAFETY_MINUTES] == const.DEFAULT_SAFETY_MINUTES
    assert defaults[const.CONF_ANOMALIES] is const.DEFAULT_ANOMALIES
    assert defaults[const.CONF_ANOMALY_SEARCH] is const.DEFAULT_ANOMALY_SEARCH
    assert defaults[const.CONF_CONNECT_GUARD] is const.DEFAULT_CONNECT_GUARD
    # An earlier value, mapped to the new strategies
    assert defaults[const.CONF_STRATEGY] == const.STRATEGY_SPY
    # No key yet: a new one is proposed
    assert flow_mod.valid_key(defaults[const.CONF_WATCHDOG_KEY])

    form = await flow.async_step_settings_poseidon({const.CONF_WATCHDOG_KEY: "short"})
    assert form["errors"] == {const.CONF_WATCHDOG_KEY: "invalid_watchdog_key"}

    # Without a key nor values: the defaults, the other options kept
    done = await flow.async_step_settings_poseidon({const.CONF_WATCHDOG_KEY: ""})
    assert done["type"] == "create_entry"
    assert done["data"] == {
        "other": 1,
        const.CONF_DEBUG: False,
        const.CONF_SILENT_MINUTES: const.DEFAULT_SILENT_MINUTES,
        const.CONF_WATCHDOG_KEY: "",
        const.CONF_STRATEGY: const.DEFAULT_STRATEGY,
        const.CONF_REDUCED_MINUTES: const.DEFAULT_REDUCED_MINUTES,
        const.CONF_SAFETY_MINUTES: const.DEFAULT_SAFETY_MINUTES,
        const.CONF_ANOMALIES: const.DEFAULT_ANOMALIES,
        const.CONF_ANOMALY_SEARCH: const.DEFAULT_ANOMALY_SEARCH,
        const.CONF_CONNECT_GUARD: const.DEFAULT_CONNECT_GUARD,
    }

    # A key set is proposed as is
    flow = _OptionsFlow(hass, {const.CONF_WATCHDOG_KEY: KEY})
    form = await flow.async_step_settings_poseidon()
    assert form["data_schema"]({})[const.CONF_WATCHDOG_KEY] == KEY


# ── Options: adding devices ─────────────────────────────────────────────────


def _devices() -> dict[str, tuple[DeviceKeys, str]]:
    return {
        "c1": (
            _keys("aa", name="Wave", model="RSWAVE45", ip="10.0.0.2"),
            STATUS_KEYS_OK,
        ),
        "c2": (_keys("bb", name="Run"), STATUS_KEYS_NEEDED),
        "c3": (_keys("cc", name="Led"), STATUS_POSEIDON),
        "c4": (_keys("dd"), STATUS_UNREACHABLE),
    }


async def test_steps_without_poseidon(hass: HomeAssistant) -> None:
    flow: Any = _OptionsFlow(hass)
    assert (await flow.async_step_add_devices())["reason"] == "poseidon_not_running"
    assert (await flow.async_step_add_devices_run())["reason"] == (
        "poseidon_not_running"
    )
    assert (await flow.async_step_rescue_script())["reason"] == "poseidon_not_running"


async def test_add_devices_nothing_to_add(hass: HomeAssistant) -> None:
    hass.data[const.DATA_POSEIDON] = _Poseidon(
        {
            "c1": (_keys("aa", name="Wave"), STATUS_POSEIDON),
            "c2": (_keys("bb"), STATUS_NO_CLOUD),
        }
    )
    flow: Any = _OptionsFlow(hass)
    result = await flow.async_step_add_devices()
    assert result["reason"] == "poseidon_nothing_to_add"
    assert result["description_placeholders"] == {
        "poseidon": "Wave",
        "no_cloud": "bb",
        "not_in_account": flow_mod.NONE,
        "unreachable": flow_mod.NONE,
    }


async def test_add_devices_form_and_selection(hass: HomeAssistant) -> None:
    poseidon = _Poseidon(_devices())
    hass.data[const.DATA_POSEIDON] = poseidon
    flow: Any = _OptionsFlow(hass)

    form = await flow.async_step_add_devices()
    assert form["type"] == "form" and form["errors"] == {}
    assert form["description_placeholders"]["poseidon"] == "Led"
    assert form["description_placeholders"]["unreachable"] == "dd"
    assert form["data_schema"]({}) == {const.CONF_DEVICES: []}

    form = await flow.async_step_add_devices({const.CONF_DEVICES: ["", None]})
    assert form["errors"] == {"base": "nothing_selected"}

    # Keys already there: straight to the run
    progress = await flow.async_step_add_devices({const.CONF_DEVICES: ["aa"]})
    assert progress["type"] == "progress_done"
    assert poseidon.added == [["aa"]]


async def test_add_devices_needing_keys_are_confirmed(hass: HomeAssistant) -> None:
    poseidon = _Poseidon(_devices())
    hass.data[const.DATA_POSEIDON] = poseidon
    flow: Any = _OptionsFlow(hass)
    await flow.async_step_add_devices()

    confirm = await flow.async_step_add_devices({const.CONF_DEVICES: ["aa", "bb"]})
    assert confirm["step_id"] == "add_devices_confirm"
    assert confirm["description_placeholders"] == {"devices": "Run"}
    assert confirm["data_schema"]({}) == {const.CONF_CONFIRM: False}

    confirm = await flow.async_step_add_devices_confirm({const.CONF_CONFIRM: False})
    assert confirm["errors"] == {"base": "confirm_required"}
    assert poseidon.added == []

    done = await flow.async_step_add_devices_confirm({const.CONF_CONFIRM: True})
    assert done["type"] == "progress_done"
    assert poseidon.added == [["aa", "bb"]]


async def test_add_devices_run_in_background(hass: HomeAssistant) -> None:
    poseidon = _Poseidon(_devices())
    poseidon.release.clear()
    poseidon.reports = [CaptureReport("aa", "Wave", ok=True)]
    hass.data[const.DATA_POSEIDON] = poseidon
    flow: Any = _OptionsFlow(hass)
    flow._poseidon_selected = ["aa"]

    progress = await flow.async_step_add_devices_run()
    assert progress["type"] == "progress"
    assert progress["progress_action"] == "poseidon_adding"
    task = progress["progress_task"]
    # Shown again while it runs: the same task
    again = await flow.async_step_add_devices_run()
    assert again["progress_task"] is task and poseidon.added == [["aa"]]

    poseidon.release.set()
    await task
    done = await flow.async_step_add_devices_run()
    assert done == {"type": "progress_done", "next_step_id": "add_devices_done"}
    assert flow._poseidon_task is None
    assert flow._poseidon_reports == poseidon.reports
    assert poseidon.switches_added == 1


@pytest.mark.parametrize("cancel", [False, True])
async def test_add_devices_run_failing(hass: HomeAssistant, cancel: bool) -> None:
    poseidon = _Poseidon(_devices())
    poseidon.release.clear()
    poseidon.reports = RuntimeError("boom")
    hass.data[const.DATA_POSEIDON] = poseidon
    flow: Any = _OptionsFlow(hass)
    flow._poseidon_selected = ["aa"]
    flow._poseidon_reports = [CaptureReport("old", "Old")]

    task = (await flow.async_step_add_devices_run())["progress_task"]
    if cancel:
        task.cancel()
    else:
        poseidon.release.set()
    with pytest.raises((RuntimeError, asyncio.CancelledError)):
        await task
    done = await flow.async_step_add_devices_run()
    assert done["type"] == "progress_done"
    assert flow._poseidon_reports == []
    # Nothing to report: the add failed
    assert (await flow.async_step_add_devices_done())["reason"] == (
        "poseidon_add_failed"
    )


async def test_add_devices_done(hass: HomeAssistant) -> None:
    flow: Any = _OptionsFlow(hass)
    flow._poseidon_reports = [
        CaptureReport("aa", "Wave", ok=True, changes=["/auto"], restored=True),
        CaptureReport("bb", "Run", ok=True, changes=["/mode"], restored=False),
        CaptureReport(
            "cc", "Mat", ok=True, changes=["/configuration"], snapshot="/s/cc.json"
        ),
        CaptureReport("dd", "Led", ok=False, error="cloud", snapshot="/s/dd.json"),
        CaptureReport("ee", "Dose", ok=True, error="warn"),
    ]
    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as notify:
        result = await flow.async_step_add_devices_done()
    assert result["reason"] == "poseidon_devices_added"
    assert result["description_placeholders"]["report"] == (
        "✓ Wave\n✓ Run\n✓ Mat\n✗ Led: cloud\n⚠ Dose: warn"
    )
    message = notify.call_args.args[1]
    assert "- Wave (aa): /auto → restored" in message
    assert "- Run (bb): /mode → NOT restored" in message
    assert "- Mat (cc): /configuration\n  snapshot: /s/cc.json" in message
    assert "- Led (dd): —\n  snapshot: /s/dd.json" in message
    assert "Dose" not in message
    assert notify.call_args.kwargs["notification_id"] == "redsea_poseidon_capture"

    # Nothing changed anywhere: no notification
    flow._poseidon_reports = [CaptureReport("aa", "Wave", ok=True)]
    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as notify:
        result = await flow.async_step_add_devices_done()
    notify.assert_not_called()
    assert result["description_placeholders"]["report"] == "✓ Wave"
