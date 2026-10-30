"""Config and options flow steps of the Poseidon entry.

Mixed into the integration's ReefBeatConfigFlow and OptionsFlowHandler, so
config_flow.py only routes to them.
"""

from __future__ import annotations

import asyncio
import html
import ipaddress
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import persistent_notification
from homeassistant.helpers.selector import (
    BooleanSelector,
    FileSelector,
    FileSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from ..const import CONFIG_FLOW_CLOUD_USERNAME, DOMAIN
from . import const
from .capture import CaptureReport
from .manager import (
    SELECTABLE,
    STATUS_KEYS_NEEDED,
    STATUS_NO_CLOUD,
    STATUS_NOT_IN_ACCOUNT,
    STATUS_POSEIDON,
    STATUS_UNREACHABLE,
    get_poseidon,
)
from .ports import find_free_port, local_ip, port_free
from .watchdog import generate_key, valid_key

_LOGGER = logging.getLogger(__name__)

# Shown in the description when a list is empty
NONE = "—"


def _cloud_accounts(hass: Any) -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=entry.entry_id, label=entry.title)
        for entry in hass.config_entries.async_entries(DOMAIN)
        if CONFIG_FLOW_CLOUD_USERNAME in entry.data
    ]


def _valid_host(host: str) -> bool:
    try:
        ipaddress.IPv4Address(host)
    except ValueError:
        return False
    return True


def _default_strategy(options: Any) -> str:
    """Default strategy as stored, earlier values mapped to the new ones."""
    value = str(options.get(const.CONF_STRATEGY) or "")
    value = const.LEGACY_STRATEGIES.get(value, value)
    return value if value in const.STRATEGIES else const.DEFAULT_STRATEGY


def export_link(url: str) -> dict[str, str]:
    """Placeholders opening and closing the download link of the export.

    An anchor of its own, opened in a new tab: the frontend takes any plain
    link to its own host for one of its pages (a markdown link to /api/...
    lands on the dashboard), but leaves a link with a target to the browser.
    """
    return {
        "link_start": f'<a href="{html.escape(url, quote=True)}" target="_blank">',
        "link_end": "</a>",
    }


class PoseidonConfigFlowMixin:
    """Creation of the Poseidon entry: port, address, cloud account."""

    async def async_step_poseidon(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        flow: Any = self
        await flow.async_set_unique_id(const.POSEIDON_UNIQUE_ID)
        flow._abort_if_unique_id_configured()
        accounts = _cloud_accounts(flow.hass)
        if not accounts:
            # Key capture re-creates devices in a cloud account
            return flow.async_abort(reason="poseidon_no_cloud_account")

        errors: dict[str, str] = {}
        if user_input is not None:
            port = int(user_input[const.CONF_PORT])
            host = str(user_input[const.CONF_HOST]).strip()
            if not _valid_host(host):
                errors[const.CONF_HOST] = "invalid_host"
            elif not await flow.hass.async_add_executor_job(port_free, port):
                errors[const.CONF_PORT] = "port_in_use"
            else:
                return flow.async_create_entry(
                    title=const.POSEIDON_TITLE,
                    data={
                        const.CONF_POSEIDON: True,
                        const.CONF_PORT: port,
                        const.CONF_HOST: host,
                        const.CONF_CLOUD_ACCOUNT: user_input.get(
                            const.CONF_CLOUD_ACCOUNT, accounts[0]["value"]
                        ),
                    },
                )
            defaults = user_input
        else:
            port = await flow.hass.async_add_executor_job(find_free_port)
            defaults = {
                const.CONF_PORT: port or const.DEFAULT_PORT,
                const.CONF_HOST: await flow.hass.async_add_executor_job(local_ip),
                const.CONF_CLOUD_ACCOUNT: accounts[0]["value"],
            }

        schema = vol.Schema(
            {
                vol.Required(
                    const.CONF_PORT, default=defaults[const.CONF_PORT]
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1024, max=65535, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    const.CONF_HOST, default=defaults[const.CONF_HOST]
                ): TextSelector(),
                vol.Required(
                    const.CONF_CLOUD_ACCOUNT,
                    default=defaults.get(
                        const.CONF_CLOUD_ACCOUNT, accounts[0]["value"]
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=accounts, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
            }
        )
        return flow.async_show_form(
            step_id="poseidon", data_schema=schema, errors=errors
        )


def _label(dev: Any, status: str) -> str:
    """A device in the list: name · model · IP, a key when keys are needed."""
    parts = [dev.name or dev.hwid, dev.model, dev.ip]
    label = " · ".join(str(p) for p in parts if p)
    return f"{label} 🔑" if status == STATUS_KEYS_NEEDED else label


def _report_line(report: CaptureReport) -> str:
    if not report.ok:
        return f"✗ {report.name}: {report.error}"
    if report.error:
        return f"⚠ {report.name}: {report.error}"
    return f"✓ {report.name}"


class PoseidonOptionsFlowMixin:
    """Options of the Poseidon entry: adding devices, settings."""

    _poseidon_selected: list[str]
    _poseidon_names: dict[str, str]
    _poseidon_needing_keys: list[str]
    _poseidon_task: asyncio.Task[list[CaptureReport]] | None
    _poseidon_reports: list[CaptureReport]

    def _poseidon_init(self) -> None:
        self._poseidon_selected = []
        self._poseidon_names = {}
        self._poseidon_needing_keys = []
        self._poseidon_task = None
        self._poseidon_reports = []

    async def async_step_poseidon_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Adding devices or the settings."""
        flow: Any = self
        return flow.async_show_menu(
            step_id="init",
            menu_options=[
                const.OPTIONS_MENU_ADD_DEVICES,
                const.OPTIONS_MENU_SETTINGS,
                const.OPTIONS_MENU_EXPORT,
                const.OPTIONS_MENU_IMPORT,
                const.OPTIONS_MENU_RESCUE,
            ],
        )

    async def async_step_export_keystore(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """A short-lived link downloading the keystore, in the CLI format."""
        flow: Any = self
        poseidon = get_poseidon(flow.hass)
        if poseidon is None:
            return flow.async_abort(reason="poseidon_not_running")
        return flow.async_abort(
            reason="poseidon_export_link",
            description_placeholders={
                **export_link(poseidon.export_url()),
                "count": str(len(poseidon.keystore.with_keys())),
                "minutes": str(const.EXPORT_LINK_MINUTES),
            },
        )

    async def async_step_rescue_script(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """A short-lived link downloading the rescue script (keys embedded)."""
        flow: Any = self
        poseidon = get_poseidon(flow.hass)
        if poseidon is None:
            return flow.async_abort(reason="poseidon_not_running")
        return flow.async_abort(
            reason="poseidon_rescue_link",
            description_placeholders={
                **export_link(poseidon.signed_url(const.RESCUE_VIEW_URL)),
                "count": str(len(poseidon.keystore.with_keys())),
                "minutes": str(const.EXPORT_LINK_MINUTES),
                "file": const.RESCUE_FILE,
            },
        )

    async def async_step_import_keystore(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Merge a keystore file of the CLI (or of an export), sent from the
        browser."""
        flow: Any = self
        poseidon = get_poseidon(flow.hass)
        if poseidon is None:
            return flow.async_abort(reason="poseidon_not_running")
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                added, updated, skipped = await poseidon.async_import_upload(
                    str(user_input[const.CONF_FILE])
                )
            except OSError:
                errors[const.CONF_FILE] = "upload_missing"
            except ValueError:
                errors[const.CONF_FILE] = "invalid_keystore"
            else:
                return flow.async_abort(
                    reason="poseidon_imported",
                    description_placeholders={
                        "added": str(added),
                        "updated": str(updated),
                        "skipped": str(skipped),
                    },
                )
        return flow.async_show_form(
            step_id="import_keystore",
            data_schema=vol.Schema(
                {
                    vol.Required(const.CONF_FILE): FileSelector(
                        FileSelectorConfig(accept=".json,application/json")
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_settings_poseidon(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Debug mode, silent-device delay, default strategy, watchdog key."""
        flow: Any = self
        options = dict(flow.config_entry.options)
        errors: dict[str, str] = {}
        if user_input is not None:
            key = str(user_input.get(const.CONF_WATCHDOG_KEY) or "").strip()
            if key and not valid_key(key):
                errors[const.CONF_WATCHDOG_KEY] = "invalid_watchdog_key"
            else:
                return flow.async_create_entry(
                    data={
                        **options,
                        const.CONF_DEBUG: bool(user_input.get(const.CONF_DEBUG)),
                        const.CONF_SILENT_MINUTES: int(
                            user_input.get(
                                const.CONF_SILENT_MINUTES,
                                const.DEFAULT_SILENT_MINUTES,
                            )
                        ),
                        const.CONF_WATCHDOG_KEY: key,
                        const.CONF_STRATEGY: str(
                            user_input.get(const.CONF_STRATEGY)
                            or const.DEFAULT_STRATEGY
                        ),
                        const.CONF_REDUCED_MINUTES: int(
                            user_input.get(
                                const.CONF_REDUCED_MINUTES,
                                const.DEFAULT_REDUCED_MINUTES,
                            )
                        ),
                        const.CONF_SAFETY_MINUTES: int(
                            user_input.get(
                                const.CONF_SAFETY_MINUTES,
                                const.DEFAULT_SAFETY_MINUTES,
                            )
                        ),
                    }
                )
        current = user_input or options
        schema = vol.Schema(
            {
                vol.Required(
                    const.CONF_DEBUG, default=bool(current.get(const.CONF_DEBUG, False))
                ): BooleanSelector(),
                vol.Required(
                    const.CONF_SILENT_MINUTES,
                    default=int(
                        current.get(
                            const.CONF_SILENT_MINUTES, const.DEFAULT_SILENT_MINUTES
                        )
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=240, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    const.CONF_STRATEGY, default=_default_strategy(current)
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=list(const.STRATEGIES),
                        mode=SelectSelectorMode.LIST,
                        translation_key="poseidon_strategy",
                    )
                ),
                vol.Required(
                    const.CONF_REDUCED_MINUTES,
                    default=int(
                        current.get(
                            const.CONF_REDUCED_MINUTES, const.DEFAULT_REDUCED_MINUTES
                        )
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=60, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    const.CONF_SAFETY_MINUTES,
                    default=int(
                        current.get(
                            const.CONF_SAFETY_MINUTES, const.DEFAULT_SAFETY_MINUTES
                        )
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5, max=1440, step=5, mode=NumberSelectorMode.BOX
                    )
                ),
                # A new key is proposed while none is set: the watchdog needs
                # the same one in its configuration
                vol.Optional(
                    const.CONF_WATCHDOG_KEY,
                    default=str(options.get(const.CONF_WATCHDOG_KEY) or generate_key()),
                ): TextSelector(),
            }
        )
        return flow.async_show_form(
            step_id="settings_poseidon",
            data_schema=schema,
            description_placeholders={"logs": const.FILES_DIR + "/logs"},
            errors=errors,
        )

    async def async_step_add_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """The devices of the integration with their status; pick some."""
        flow: Any = self
        poseidon = get_poseidon(flow.hass)
        if poseidon is None:
            return flow.async_abort(reason="poseidon_not_running")

        coordinators = poseidon.local_devices()
        statuses = await asyncio.gather(
            *(poseidon.async_status(c) for c in coordinators)
        )
        groups: dict[str, list[str]] = {}
        options: list[SelectOptionDict] = []
        needing: set[str] = set()
        for coordinator, status in zip(coordinators, statuses):
            dev = poseidon.device_keys(coordinator)
            self._poseidon_names[dev.hwid] = dev.name or dev.hwid
            groups.setdefault(status, []).append(dev.name or dev.hwid)
            if status in SELECTABLE:
                options.append(
                    SelectOptionDict(value=dev.hwid, label=_label(dev, status))
                )
            if status == STATUS_KEYS_NEEDED:
                needing.add(dev.hwid)

        placeholders = {
            key: ", ".join(sorted(groups.get(status, []))) or NONE
            for key, status in (
                ("poseidon", STATUS_POSEIDON),
                ("no_cloud", STATUS_NO_CLOUD),
                ("not_in_account", STATUS_NOT_IN_ACCOUNT),
                ("unreachable", STATUS_UNREACHABLE),
            )
        }
        if not options:
            return flow.async_abort(
                reason="poseidon_nothing_to_add", description_placeholders=placeholders
            )

        errors: dict[str, str] = {}
        if user_input is not None:
            selected = [str(h) for h in user_input.get(const.CONF_DEVICES) or [] if h]
            if selected:
                self._poseidon_selected = selected
                self._poseidon_needing_keys = [h for h in selected if h in needing]
                if self._poseidon_needing_keys:
                    return await self.async_step_add_devices_confirm()
                return await self.async_step_add_devices_run()
            errors["base"] = "nothing_selected"

        schema = vol.Schema(
            {
                vol.Optional(const.CONF_DEVICES, default=[]): SelectSelector(
                    SelectSelectorConfig(
                        options=options, multiple=True, mode=SelectSelectorMode.LIST
                    )
                )
            }
        )
        return flow.async_show_form(
            step_id="add_devices",
            data_schema=schema,
            description_placeholders=placeholders,
            errors=errors,
        )

    async def async_step_add_devices_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """The key capture is destructive: say what it does, and confirm."""
        flow: Any = self
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(const.CONF_CONFIRM):
                return await self.async_step_add_devices_run()
            errors["base"] = "confirm_required"
        names = ", ".join(
            self._poseidon_names.get(h, h) for h in self._poseidon_needing_keys
        )
        return flow.async_show_form(
            step_id="add_devices_confirm",
            data_schema=vol.Schema(
                {vol.Required(const.CONF_CONFIRM, default=False): BooleanSelector()}
            ),
            description_placeholders={"devices": names},
            errors=errors,
        )

    async def async_step_add_devices_run(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Capture and switch, in the background."""
        flow: Any = self
        poseidon = get_poseidon(flow.hass)
        if poseidon is None:
            return flow.async_abort(reason="poseidon_not_running")
        task = self._poseidon_task
        if task is None:
            task = self._poseidon_task = flow.hass.async_create_task(
                poseidon.async_add_devices(list(self._poseidon_selected))
            )
        if not task.done():
            return flow.async_show_progress(
                step_id="add_devices_run",
                progress_action="poseidon_adding",
                progress_task=task,
            )
        self._poseidon_task = None
        if task.cancelled() or task.exception() is not None:
            _LOGGER.error(
                "Poseidon: adding devices failed",
                exc_info=None if task.cancelled() else task.exception(),
            )
            self._poseidon_reports = []
        else:
            self._poseidon_reports = task.result()
        poseidon.async_add_new_switches()
        return flow.async_show_progress_done(next_step_id="add_devices_done")

    async def async_step_add_devices_done(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Summary; the details of what changed go to a notification."""
        flow: Any = self
        reports = self._poseidon_reports
        if not reports:
            return flow.async_abort(reason="poseidon_add_failed")
        details = [
            f"- {r.name} ({r.hwid}): "
            + (", ".join(r.changes) or "—")
            + (
                ""
                if r.restored is None
                else (" → restored" if r.restored else " → NOT restored")
            )
            + (f"\n  snapshot: {r.snapshot}" if r.snapshot else "")
            for r in reports
            if r.changes or (r.snapshot and not r.ok)
        ]
        if details:
            persistent_notification.async_create(
                flow.hass,
                "Configuration changed by the key capture (endpoints):\n"
                + "\n".join(details),
                title="Poseidon",
                notification_id="redsea_poseidon_capture",
            )
        return flow.async_abort(
            reason="poseidon_devices_added",
            description_placeholders={
                "report": "\n".join(_report_line(r) for r in reports)
            },
        )
