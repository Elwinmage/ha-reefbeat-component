"""Config flow for the Red Sea ReefBeat integration.

Supports:
- Adding a ReefBeat Cloud account
- Auto-detecting local devices on the LAN
- Manually adding a local device by IP
- Creating a virtual LED entry
- Options flow (scan interval, config mode, etc.)
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import pathlib
from asyncio import timeout
from functools import partial
from time import time
from typing import Any, cast

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .auto_detect import (
    ReefBeatInfo,
    get_reefbeats,
    get_unique_id,
    is_reefbeat,
    is_valid_cidr,
    list_scannable_subnets,
)
from .const import (
    ADD_CLOUD_API,
    ADD_LOCAL_DETECT,
    ADD_MANUAL_MODE,
    ADD_TYPES,
    ATO_SCAN_INTERVAL,
    CLOUD_DEVICE_TYPE,
    CLOUD_SCAN_INTERVAL,
    CLOUD_SERVER_ADDR,
    CONF_GROUP_MEMBERS,
    CONF_GROUP_POSITION,
    CONFIG_FLOW_ADD_TYPE,
    CONFIG_FLOW_CLOUD_PASSWORD,
    CONFIG_FLOW_CLOUD_SERVER,
    CONFIG_FLOW_CLOUD_USERNAME,
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_DISABLE_SUPPLEMENT,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_INTENSITY_COMPENSATION,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_OLD_PROBE,
    CONFIG_FLOW_PROBE_TYPE,
    CONFIG_FLOW_PROBES,
    CONFIG_FLOW_SCAN_INTERVAL,
    CONFIG_FLOW_WIFI_MANUAL_SUBNET,
    CONFIG_FLOW_WIFI_PASSWORD,
    CONFIG_FLOW_WIFI_RESCAN,
    CONFIG_FLOW_WIFI_SSID,
    CONTROL_PROBE_TYPES,
    CONTROL_SCAN_INTERVAL,
    DOMAIN,
    DOSE_SCAN_INTERVAL,
    GROUP_MIN_MEMBERS,
    HTTP_DELAY_BETWEEN_RETRY,
    HTTP_MAX_RETRY,
    HW_ATO_IDS,
    HW_CONTROL_IDS,
    HW_DEVICES_IDS,
    HW_DOSE_IDS,
    HW_LED_IDS,
    HW_MAT_IDS,
    HW_POWER_IDS,
    HW_RUN_IDS,
    LED_SCAN_INTERVAL,
    LEDS_INTENSITY_COMPENSATION,
    MAT_SCAN_INTERVAL,
    OPTIONS_MENU_ADD_PROBE,
    OPTIONS_MENU_CHANGE_PROBE,
    OPTIONS_MENU_DEL_PROBE,
    OPTIONS_MENU_SETTINGS,
    OPTIONS_MENU_WIFI,
    POWER_SCAN_INTERVAL,
    RUN_SCAN_INTERVAL,
    SCAN_INTERVAL,
    VIRTUAL_LED,
    VIRTUAL_LED_SCAN_INTERVAL,
    WIFI_POST_CONNECT_WAIT,
    WIFI_POST_RESET_WAIT,
    WIFI_REDISCOVER_INTERVAL,
    WIFI_REDISCOVER_MAX_ATTEMPTS,
)
from .groups import cloud_groups, discovery_unique_id
from .reefbeat import parse
from .wifi import (
    connect_wifi,
    get_current_ssid,
    rediscover_device,
    reset_device,
    scan_wifi,
)

_LOGGER = logging.getLogger(__name__)

# Local file that lets the cloud account form ask for its server, to point it
# at a reefbeat-devices-simulator: create it to enable, delete it to
# disable. Git-ignored, never shipped (see simulator_enabled.example).
_SIM_FLAG = pathlib.Path(__file__).parent / ".simulator_enabled"


def _simulator_enabled() -> bool:
    """Return True if the local .simulator_enabled flag file exists."""
    return _SIM_FLAG.exists()


# Helpers
async def validate_cloud_input(
    hass: HomeAssistant,
    username: str,
    password: str,
    server: str = CLOUD_SERVER_ADDR,
) -> bool:
    """Validate ReefBeat cloud credentials.

    Notes:
        Uses OAuth password grant against the cloud server (CLOUD_SERVER_ADDR
        unless a simulator's was given, see _simulator_enabled).
    """
    _LOGGER.debug("Validating cloud credentials for user '%s'", username)

    headers = {
        "Authorization": "Basic Z0ZqSHRKcGE6Qzlmb2d3cmpEV09SVDJHWQ==",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }

    session = async_get_clientsession(hass)

    try:
        async with timeout(10):
            async with session.post(
                f"https://{server}/oauth/token",
                data=payload,
                headers=headers,
                ssl=False,
            ) as resp:
                status = int(resp.status)
    except Exception:
        _LOGGER.exception("Cloud credential validation failed due to request error")
        return False

    if status != 200:
        _LOGGER.warning("Cloud authentication failed (status=%s)", status)
        return False

    return True


# =============================================================================
# Helpers
# =============================================================================


def get_scan_interval(hw_model: str) -> int:
    """Return the default scan interval based on hardware model."""
    if hw_model in HW_DOSE_IDS:
        return DOSE_SCAN_INTERVAL
    if hw_model in HW_MAT_IDS:
        return MAT_SCAN_INTERVAL
    if hw_model in HW_ATO_IDS:
        return ATO_SCAN_INTERVAL
    if hw_model in HW_LED_IDS:
        return LED_SCAN_INTERVAL
    if hw_model in HW_RUN_IDS:
        return RUN_SCAN_INTERVAL
    if hw_model in HW_POWER_IDS:
        return POWER_SCAN_INTERVAL
    if hw_model in HW_CONTROL_IDS:
        return CONTROL_SCAN_INTERVAL
    if hw_model == CLOUD_DEVICE_TYPE:
        return CLOUD_SCAN_INTERVAL
    return SCAN_INTERVAL


def get_scan_interval_safe(hw_model: str | None) -> int:
    """Return scan interval for hw_model, defaulting safely when unknown/None."""
    if not hw_model:
        return SCAN_INTERVAL
    return get_scan_interval(hw_model)


def _is_cidr(address: str) -> bool:
    """Return True if the string looks like an IPv4 CIDR (e.g. 192.168.1.0/24)."""
    try:
        ipaddress.ip_network(address, strict=False)
        return True
    except Exception:
        return False


def _device_to_string(d: ReefBeatInfo) -> str:
    """Serialize a detected device into a selection string.

    ReefBeatInfo is a `TypedDict(total=False)`, so keys may be missing.
    """
    ip = d.get("ip", "")
    hw_model = d.get("hw_model", "")
    friendly_name = d.get("friendly_name", "")
    return f"{ip} {hw_model} {friendly_name}".strip()


# Config flow

# =============================================================================
# Classes
# =============================================================================


class ReefBeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ReefBeat config flow."""

    VERSION = 1
    # 1.2: virtual LED members kept as an ordered list (CONF_GROUP_MEMBERS)
    MINOR_VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def _unique_id(self, user_input: dict[str, Any]) -> str:
        """Resolve device UUID for a local device entry (retrying as needed)."""
        ip = str(user_input[CONFIG_FLOW_IP_ADDRESS]).split(" ")[0]
        retry = HTTP_MAX_RETRY
        while retry > 0:
            uuid = await self.hass.async_add_executor_job(partial(get_unique_id, ip=ip))
            if uuid is not None:
                return str(uuid)
            retry -= 1
            _LOGGER.warning("Could not get UUID for %s, retrying...", ip)
            await asyncio.sleep(HTTP_DELAY_BETWEEN_RETRY)

        _LOGGER.error("Could not get UUID for %s; falling back to IP as unique_id", ip)
        return ip

    # Discovered groups of the ReefBeat app (see ReefBeatCloudCoordinator)
    _discovered: dict[str, Any]

    def _discovered_members(self) -> list[str]:
        """Lamps of the discovered group, read again from the cloud accounts
        (a lamp loaded since the proposal joins it); the proposal's when
        no account lists the group anymore."""
        key = (
            str(self._discovered.get("aquarium_uid")),
            str(self._discovered.get("model")),
        )
        for cloud in self.hass.data.get(DOMAIN, {}).values():
            app_groups = getattr(cloud, "app_groups", None)
            if callable(app_groups):
                groups = cast(dict[tuple[str, str], list[str]], app_groups())
                members = groups.get(key)
                if members:
                    return list(members)
        return [str(m) for m in self._discovered.get(CONF_GROUP_MEMBERS, [])]

    def _lamp_label(self, entry_id: str) -> str:
        """A lamp as shown to the user: serial (model), else its entry title."""
        led = self.hass.data.get(DOMAIN, {}).get(entry_id)
        if led is not None:
            return f"{led.serial} ({led.model})"
        entry = self.hass.config_entries.async_get_entry(entry_id)
        return entry.title if entry is not None else entry_id

    async def async_step_integration_discovery(
        self, discovery_info: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """A group of the ReefBeat app no virtual LED drives: propose one."""
        members = discovery_info.get(CONF_GROUP_MEMBERS)
        model = discovery_info.get("model")
        aquarium_uid = discovery_info.get("aquarium_uid")
        if (
            not isinstance(members, list)
            or len(members) < GROUP_MIN_MEMBERS
            or not model
            or not aquarium_uid
        ):
            return self.async_abort(reason="cannot_create")
        await self.async_set_unique_id(
            discovery_unique_id(str(aquarium_uid), str(model))
        )
        self._abort_if_unique_id_configured()
        self._discovered = dict(discovery_info)
        self.context["title_placeholders"] = {
            "name": f"{VIRTUAL_LED} {model} × {len(members)}"
        }
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the lamps of the group, create its virtual LED on confirm."""
        members = self._discovered_members()
        if user_input is not None:
            taken = {
                str(member)
                for entry in self.hass.config_entries.async_entries(DOMAIN)
                for member in entry.data.get(CONF_GROUP_MEMBERS, []) or []
            }
            if len(members) < GROUP_MIN_MEMBERS or taken.intersection(members):
                return self.async_abort(reason="group_already_driven")
            title = f"{VIRTUAL_LED}-{int(time())}"
            return self.async_create_entry(
                title=title,
                data={
                    CONFIG_FLOW_IP_ADDRESS: title,
                    CONFIG_FLOW_HW_MODEL: VIRTUAL_LED,
                    CONFIG_FLOW_SCAN_INTERVAL: VIRTUAL_LED_SCAN_INTERVAL,
                    CONF_GROUP_MEMBERS: members,
                },
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "model": str(self._discovered.get("model")),
                "aquarium": str(self._discovered.get("aquarium")),
                "leds": "\n".join(
                    f"{pos + 1}. {self._lamp_label(entry_id)}"
                    for pos, entry_id in enumerate(members)
                ),
            },
        )

    def _cloud_schema(self, values: dict[str, Any]) -> vol.Schema:
        """Form of a cloud account, filled with what was typed.

        With the local .simulator_enabled flag file only, the cloud server
        can be changed (a simulator answering the ReefBeat API over HTTPS).
        """
        fields: dict[Any, Any] = {
            vol.Required(
                CONFIG_FLOW_CLOUD_USERNAME,
                default=values.get(CONFIG_FLOW_CLOUD_USERNAME, vol.UNDEFINED),
            ): str,
            vol.Required(
                CONFIG_FLOW_CLOUD_PASSWORD,
                default=values.get(CONFIG_FLOW_CLOUD_PASSWORD, vol.UNDEFINED),
            ): str,
        }
        if _simulator_enabled():
            fields[
                vol.Optional(
                    CONFIG_FLOW_CLOUD_SERVER,
                    default=values.get(CONFIG_FLOW_CLOUD_SERVER, CLOUD_SERVER_ADDR),
                )
            ] = str
        return vol.Schema(fields)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step and subsequent submissions."""
        subnetwork: str | None = None

        # Step 1: choose add type
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONFIG_FLOW_ADD_TYPE, default=ADD_LOCAL_DETECT
                        ): vol.In(ADD_TYPES)
                    }
                ),
            )

        # Step 2: branch by add type selection
        if CONFIG_FLOW_ADD_TYPE in user_input:
            add_type = user_input[CONFIG_FLOW_ADD_TYPE]

            if add_type == ADD_CLOUD_API:
                _LOGGER.info("Adding ReefBeat Cloud account")
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._cloud_schema({}),
                )

            if add_type == ADD_LOCAL_DETECT:
                return await self.auto_detect(subnetwork)

            if add_type == VIRTUAL_LED:
                title = f"{VIRTUAL_LED}-{int(time())}"
                user_input[CONFIG_FLOW_IP_ADDRESS] = title
                user_input[CONFIG_FLOW_HW_MODEL] = VIRTUAL_LED
                user_input[CONFIG_FLOW_SCAN_INTERVAL] = VIRTUAL_LED_SCAN_INTERVAL
                _LOGGER.debug("Creating virtual LED entry with unique_id '%s'", title)
                await self.async_set_unique_id(title)
                return self.async_create_entry(title=title, data=user_input)

            if add_type == ADD_MANUAL_MODE:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({vol.Required(CONFIG_FLOW_IP_ADDRESS): str}),
                )

        # Step 3: create entry from submitted values
        _LOGGER.debug("Config flow submission keys: %s", list(user_input.keys()))

        # CLOUD
        if CONFIG_FLOW_CLOUD_USERNAME in user_input:
            server = CLOUD_SERVER_ADDR
            typed = str(user_input.pop(CONFIG_FLOW_CLOUD_SERVER, "") or "").strip()
            if typed and _simulator_enabled():
                server = typed
            valid = await validate_cloud_input(
                self.hass,
                str(user_input[CONFIG_FLOW_CLOUD_USERNAME]),
                str(user_input[CONFIG_FLOW_CLOUD_PASSWORD]),
                server,
            )
            if not valid:
                errors = {"base": "auth_failed"}
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._cloud_schema(
                        {**user_input, CONFIG_FLOW_CLOUD_SERVER: server}
                    ),
                    errors=errors,
                )

            user_input[CONFIG_FLOW_SCAN_INTERVAL] = get_scan_interval(CLOUD_DEVICE_TYPE)
            user_input[CONFIG_FLOW_CONFIG_TYPE] = False
            # The account's API is on the server its token came from
            user_input[CONFIG_FLOW_IP_ADDRESS] = server
            user_input[CONFIG_FLOW_HW_MODEL] = CLOUD_DEVICE_TYPE
            user_input[CONFIG_FLOW_DISABLE_SUPPLEMENT] = True

            title = str(user_input[CONFIG_FLOW_CLOUD_USERNAME])
            await self.async_set_unique_id(title)
            return self.async_create_entry(title=title, data=user_input)

        # DETECT and MANUAL
        if CONFIG_FLOW_IP_ADDRESS in user_input:
            ip_value = str(user_input[CONFIG_FLOW_IP_ADDRESS])

            # # Allow "Virtual LED" via manual field as before
            # if ip_value == VIRTUAL_LED:
            #     title = f"{VIRTUAL_LED}-{int(time())}"
            #     user_input[CONFIG_FLOW_IP_ADDRESS] = title
            #     user_input[CONFIG_FLOW_HW_MODEL] = VIRTUAL_LED
            #     user_input[CONFIG_FLOW_SCAN_INTERVAL] = VIRTUAL_LED_SCAN_INTERVAL
            #     _LOGGER.debug("Creating virtual LED entry with unique_id '%s'", title)
            #     await self.async_set_unique_id(title)
            #     return self.async_create_entry(title=title, data=user_input)

            # If user provided a CIDR, run auto-detect
            if _is_cidr(ip_value):
                subnetwork = ip_value
                return await self.auto_detect(subnetwork)

            configuration = ip_value.split(" ")

            # Manual device: only IP provided -> attempt identify
            if len(configuration) < 2:
                ip = configuration[0]
                (
                    status,
                    ip,
                    hw_model,
                    friendly_name,
                    uuid,
                ) = await self.hass.async_add_executor_job(partial(is_reefbeat, ip=ip))
                _LOGGER.info(
                    "Manual probe: ip=%s hw=%s name=%s uuid=%s",
                    ip,
                    hw_model,
                    friendly_name,
                    uuid,
                )

                if status is True:
                    conf = _device_to_string(
                        {
                            "ip": ip,
                            "hw_model": hw_model or "",
                            "friendly_name": friendly_name or "",
                        }
                    )
                    configuration = conf.split(" ")
                else:
                    # Keep existing behavior: proceed, but unique_id will fall back to ip (below)
                    pass

            # Detected device string: resolve unique_id via description.xml
            uuid = await self._unique_id(user_input)
            _LOGGER.info("Resolved unique_id: %s", uuid)

            await self.async_set_unique_id(str(uuid))
            self._abort_if_unique_id_configured()

            title = (
                "-".join(configuration[2:])
                if len(configuration) >= 3
                else configuration[0]
            )
            user_input[CONFIG_FLOW_HW_MODEL] = (
                configuration[1] if len(configuration) >= 2 else ""
            )
            user_input[CONFIG_FLOW_IP_ADDRESS] = configuration[0]
            user_input[CONFIG_FLOW_SCAN_INTERVAL] = get_scan_interval(
                user_input[CONFIG_FLOW_HW_MODEL]
            )
            user_input[CONFIG_FLOW_CONFIG_TYPE] = False

            _LOGGER.info(
                "Creating entry: title=%s ip=%s hw=%s",
                title,
                user_input[CONFIG_FLOW_IP_ADDRESS],
                user_input[CONFIG_FLOW_HW_MODEL],
            )
            return self.async_create_entry(title=title, data=user_input)

        # Should not happen, but keep flow stable
        return self.async_abort(reason="unknown")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def auto_detect(
        self, subnetwork: str | None
    ) -> config_entries.ConfigFlowResult:
        """Auto-detect ReefBeat devices and present a bulk selection list.

        The form is a multi-select with every discovered device pre-checked, so
        the user can hit Submit once to add them all. Individual boxes can be
        unchecked to skip a device. The submission is handled by
        :meth:`async_step_select_devices`, which spawns one background import
        flow per extra device and finalises the current flow with the first
        selected device.
        """

        try:
            detected_devices: list[
                ReefBeatInfo
            ] = await self.hass.async_add_executor_job(
                partial(get_reefbeats, subnetwork=subnetwork)
            )
        except Exception:
            _LOGGER.exception("auto_detect: get_reefbeats failed")
            # Fall through to the manual IP form with a generic error
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONFIG_FLOW_IP_ADDRESS): str}),
                errors={"base": "nothing_detected"},
            )
        # No need for deepcopy; we only remove items from the "available" view.
        available_devices: list[ReefBeatInfo] = list(detected_devices)

        _LOGGER.info("Detected devices: %s", detected_devices)

        existing = {e.unique_id for e in self._async_current_entries() if e.unique_id}
        for device in detected_devices:
            if device.get("uuid") in existing:
                _LOGGER.info(
                    "%s skipped (already configured)", device.get("friendly_name")
                )
                if device in available_devices:
                    available_devices.remove(device)

        _LOGGER.info("Available devices: %s", available_devices)

        available_devices_s = list(map(_device_to_string, available_devices))
        # available_devices_s += [VIRTUAL_LED]

        # No device detected reask for IP or subnetwork
        if len(available_devices_s) == 0:
            errors = {"base": "nothing_detected"}
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONFIG_FLOW_IP_ADDRESS): str}),
                errors=errors,
            )
        # Propose detected devices as a multi-select. cv.multi_select needs a
        # {key: label} mapping; we re-use the encoded string as both because
        # the async_step_user parser already knows how to split it back.
        options = {value: value for value in available_devices_s}
        return self.async_show_form(
            step_id="select_devices",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONFIG_FLOW_IP_ADDRESS,
                        default=list(options.keys()),
                    ): cv.multi_select(options)
                }
            ),
        )

    async def async_step_select_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the multi-select submission from :meth:`auto_detect`.

        Config flows can only create one entry per flow (``async_create_entry``
        terminates the flow). To bulk-add N devices in a single user gesture we
        finish the *current* flow with the first selected device and spawn one
        background import flow per remaining device via
        ``hass.config_entries.flow.async_init``. Each imported flow enters
        through :meth:`async_step_import` which just delegates to the normal
        user path — so the create/validate/dedup logic lives in one place.
        """
        if not user_input:
            # Empty submission — bounce back to the picker.
            return await self.auto_detect(None)

        selected: list[str] = list(user_input.get(CONFIG_FLOW_IP_ADDRESS) or [])
        if not selected:
            # User unchecked every box. Nothing to do, abort cleanly.
            return self.async_abort(reason="nothing_detected")

        # Fan out: schedule an import flow for every device except the first.
        # The first one goes through the current flow to give the user visible
        # feedback (the "Success" dialog closes on that entry).
        for device_str in selected[1:]:
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": config_entries.SOURCE_IMPORT},
                    data={CONFIG_FLOW_IP_ADDRESS: device_str},
                )
            )

        # Finalise the current flow with the first device by re-entering the
        # user step with a single-IP payload — same code path as before.
        return await self.async_step_user({CONFIG_FLOW_IP_ADDRESS: selected[0]})

    async def async_step_import(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Entry point for the background flows spawned by bulk add.

        Delegates straight to :meth:`async_step_user` so all the create logic,
        unique-id resolution and dedup happen in exactly one place.
        """
        return await self.async_step_user(user_input)


# Options flow
class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle integration options.

    Structure:
        - init: dispatcher. For a plain local device (LED/DOSE/ATO/RUN/MAT/
          POWER/CONTROL/WAVE) it presents a menu offering either the classic
          settings form or a Wi-Fi provisioning flow. Cloud accounts skip
          the menu and go straight to their settings form; virtual LED
          entries go straight to their group steps.
        - settings: classic form (scan_interval, live_config_update, and
          optional intensity_compensation / cloud credentials).
        - group_members / group_order: the LEDs of a virtual LED, then their
          order (the group order of the ReefBeat app).
        - wifi_scan: scans the device's visible Wi-Fi networks, lets the
          user pick one and enter its password.
        - wifi_apply: runs connect → reset → rediscover as a background task
          with an async_show_progress spinner.
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        # Cached Wi-Fi scan results, keyed by SSID.
        self._wifi_networks: list[dict[str, Any]] = []
        # SSID the device is currently connected to (read from /wifi). Used
        # to pre-select the matching entry in the scan form so the user
        # doesn't have to hunt for their own network in the list.
        self._wifi_current_ssid: str | None = None
        # State for the async wifi apply background task. The task never
        # raises: it records its outcome in _wifi_outcome so that the step
        # can route deterministically. This avoids relying on
        # progress-task exception propagation, whose behaviour differs
        # across Home Assistant versions.
        self._wifi_task: asyncio.Task[None] | None = None
        self._wifi_outcome: str | None = None
        self._wifi_selected_ssid: str | None = None
        self._wifi_selected_password: str | None = None
        # Reason surfaced by the final abort step (success or specific failure).
        self._wifi_result_reason: str | None = None
        # New IP found after reboot, populated on success only.
        self._wifi_new_ip: str | None = None
        # Subnets already scanned automatically during _do_wifi_apply. Kept
        # around so the manual-subnet step can show the user which CIDRs
        # were tried in vain, avoiding pointless re-scans.
        self._wifi_manual_candidates: list[str] = []
        # Group (virtual LED): members chosen, waiting to be ordered
        self._new_group_members: list[str] = []

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def _entry_kind(self) -> str:
        """Classify the config entry: 'virtual', 'cloud' or 'local'."""
        if self._config_entry.title.startswith(VIRTUAL_LED + "-"):
            return "virtual"
        hw_model = self._config_entry.data.get(CONFIG_FLOW_HW_MODEL)
        if hw_model == CLOUD_DEVICE_TYPE:
            return "cloud"
        return "local"

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Route to the right sub-flow based on the entry kind."""
        kind = self._entry_kind()

        if kind == "virtual":
            # Virtual LEDs only choose and order their LEDs — no menu, no Wi-Fi.
            return await self.async_step_group_members()

        if kind == "cloud":
            # Cloud accounts have no local IP — no Wi-Fi provisioning either.
            return await self.async_step_settings(user_input)

        # Local device: only offer the menu if the hardware model looks
        # like a known ReefBeat device. Otherwise fall back to the plain
        # settings form so mis-configured entries stay recoverable.
        hw_model = self._config_entry.data.get(CONFIG_FLOW_HW_MODEL)
        if hw_model in HW_DEVICES_IDS:
            menu = [OPTIONS_MENU_SETTINGS, OPTIONS_MENU_WIFI]
            # The RSCONTROL hub can add/remove BLE probes, mirroring the app.
            if hw_model in HW_CONTROL_IDS:
                menu += [
                    OPTIONS_MENU_ADD_PROBE,
                    OPTIONS_MENU_CHANGE_PROBE,
                    OPTIONS_MENU_DEL_PROBE,
                ]
            return self.async_show_menu(
                step_id="init",
                menu_options=menu,
            )

        return await self.async_step_settings(user_input)

    # ------------------------------------------------------------------
    # Settings step (classic options form, unchanged behaviour)
    # ------------------------------------------------------------------

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the classic device settings (scan interval, live config, etc.)."""
        if user_input is not None:
            # Cloud API options
            if CONFIG_FLOW_CLOUD_USERNAME in user_input:
                user_input[CONFIG_FLOW_IP_ADDRESS] = self._config_entry.data[
                    CONFIG_FLOW_IP_ADDRESS
                ]
                user_input[CONFIG_FLOW_HW_MODEL] = self._config_entry.data[
                    CONFIG_FLOW_HW_MODEL
                ]
                user_input[CONFIG_FLOW_CONFIG_TYPE] = False

                valid = await validate_cloud_input(
                    self.hass,
                    str(user_input[CONFIG_FLOW_CLOUD_USERNAME]),
                    str(user_input[CONFIG_FLOW_CLOUD_PASSWORD]),
                    str(user_input[CONFIG_FLOW_IP_ADDRESS] or CLOUD_SERVER_ADDR),
                )
                if not valid:
                    errors = {"base": "auth_failed"}
                    schema = vol.Schema(
                        {
                            vol.Required(
                                CONFIG_FLOW_CLOUD_USERNAME,
                                default=user_input[CONFIG_FLOW_CLOUD_USERNAME],
                            ): str,
                            vol.Required(
                                CONFIG_FLOW_CLOUD_PASSWORD,
                                default=user_input[CONFIG_FLOW_CLOUD_PASSWORD],
                            ): str,
                            vol.Required(
                                CONFIG_FLOW_SCAN_INTERVAL,
                                default=user_input[CONFIG_FLOW_SCAN_INTERVAL],
                            ): int,
                            vol.Required(CONFIG_FLOW_CONFIG_TYPE, default=False): bool,
                        }
                    )
                    # Stay on the settings step so validation errors don't
                    # surface as a broken menu.
                    return self.async_show_form(
                        step_id="settings", data_schema=schema, errors=errors
                    )

                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=user_input,
                    options=self._config_entry.options,
                )
                res = self.async_create_entry(data=user_input)
                _LOGGER.debug("Scheduling reload for %s", res.get("handler"))
                self.hass.config_entries.async_schedule_reload(res["handler"])
                return res

            # Generic scan interval / config type options (local devices)
            if CONFIG_FLOW_SCAN_INTERVAL in user_input:
                data: dict[str, Any] = {
                    CONFIG_FLOW_IP_ADDRESS: self._config_entry.data[
                        CONFIG_FLOW_IP_ADDRESS
                    ],
                    CONFIG_FLOW_HW_MODEL: self._config_entry.data[CONFIG_FLOW_HW_MODEL],
                    CONFIG_FLOW_SCAN_INTERVAL: user_input[CONFIG_FLOW_SCAN_INTERVAL],
                    CONFIG_FLOW_CONFIG_TYPE: user_input[CONFIG_FLOW_CONFIG_TYPE],
                }
                if CONFIG_FLOW_INTENSITY_COMPENSATION in user_input:
                    data[CONFIG_FLOW_INTENSITY_COMPENSATION] = user_input[
                        CONFIG_FLOW_INTENSITY_COMPENSATION
                    ]

                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=data, options=self._config_entry.options
                )
                return self.async_create_entry(data=data)

        errors: dict[str, str] = {}
        options_schema: vol.Schema | None = None

        hw_model: str | None = None
        res = []
        try:
            hw_model = cast(str, self._config_entry.data[CONFIG_FLOW_HW_MODEL])
            query = parse('$[?(@.name=="' + hw_model + '")]')
            res = query.find(LEDS_INTENSITY_COMPENSATION)
        except Exception:
            hw_model = None
            res = []

        if len(res) > 0:
            options_schema = vol.Schema(
                {
                    vol.Required(
                        CONFIG_FLOW_SCAN_INTERVAL,
                        default=get_scan_interval_safe(hw_model),
                    ): int,
                    vol.Required(CONFIG_FLOW_CONFIG_TYPE, default=False): bool,
                    vol.Required(
                        CONFIG_FLOW_INTENSITY_COMPENSATION, default=False
                    ): bool,
                }
            )
        elif hw_model == CLOUD_DEVICE_TYPE:
            options_schema = vol.Schema(
                {
                    vol.Required(
                        CONFIG_FLOW_CLOUD_USERNAME,
                        default=self._config_entry.data[CONFIG_FLOW_CLOUD_USERNAME],
                    ): str,
                    vol.Required(
                        CONFIG_FLOW_CLOUD_PASSWORD,
                        default=self._config_entry.data[CONFIG_FLOW_CLOUD_PASSWORD],
                    ): str,
                    vol.Required(
                        CONFIG_FLOW_SCAN_INTERVAL,
                        default=self._config_entry.data.get(
                            CONFIG_FLOW_SCAN_INTERVAL,
                            get_scan_interval_safe(hw_model),
                        ),
                    ): int,
                    vol.Required(CONFIG_FLOW_CONFIG_TYPE, default=False): bool,
                    vol.Required(CONFIG_FLOW_DISABLE_SUPPLEMENT, default=True): bool,
                }
            )
        else:
            options_schema = vol.Schema(
                {
                    vol.Required(
                        CONFIG_FLOW_SCAN_INTERVAL,
                        default=get_scan_interval_safe(hw_model),
                    ): int,
                    vol.Required(CONFIG_FLOW_CONFIG_TYPE, default=False): bool,
                }
            )

        # We render the same form under two step ids: "init" for cloud
        # entries that skip the menu (preserving their long-standing UX and
        # translation strings), and "settings" for local devices coming from
        # the menu (so both branches can coexist in strings.json).
        step_id = "init" if self._entry_kind() != "local" else "settings"

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                options_schema, self._config_entry.options
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Group steps (virtual LED): choose the LEDs, then their order
    # ------------------------------------------------------------------

    def _group_members(self) -> list[str]:
        """Current members of the group entry, in the group order."""
        return [str(e) for e in self._config_entry.data.get(CONF_GROUP_MEMBERS, [])]

    def _group_candidates(self) -> dict[str, str]:
        """LEDs that can be members of this group: entry id -> label.

        Loaded ReefLEDs not already in another group, plus the current
        members even when not loaded (so an offline lamp is not dropped by
        saving the form).
        """
        loaded = self.hass.data.get(DOMAIN, {})
        taken: set[str] = set()
        for entry_id, coordinator in loaded.items():
            if entry_id == self._config_entry.entry_id:
                continue
            members = getattr(coordinator, "member_ids", None)
            if isinstance(members, list):
                taken.update(str(m) for m in members)

        candidates: dict[str, str] = {}
        for entry_id, led in loaded.items():
            if entry_id in taken:
                continue
            if type(led).__name__ in ("ReefLedCoordinator", "ReefLedG2Coordinator"):
                candidates[entry_id] = f"{led.serial} ({led.model})"
        for entry_id in self._group_members():
            if entry_id not in candidates:
                entry = self.hass.config_entries.async_get_entry(entry_id)
                title = entry.title if entry is not None else entry_id
                candidates[entry_id] = f"{title} (?)"
        return candidates

    def _cloud_grouped(self, candidates: dict[str, str]) -> list[str]:
        """Lamps already grouped in the ReefBeat app, in its order.

        Read from the loaded cloud accounts: the first group (lamps of one
        model in one aquarium) of at least two of the candidates.
        """
        loaded = self.hass.data.get(DOMAIN, {})
        entry_of = {
            str(getattr(loaded[entry_id], "model_id", "")): entry_id
            for entry_id in candidates
            if entry_id in loaded
        }
        for cloud in loaded.values():
            if type(cloud).__name__ != "ReefBeatCloudCoordinator":
                continue
            devices = cloud.get_data("$.sources[?(@.name=='/device')].data", True)
            groups = list(cloud_groups(devices, entry_of).values())
            if groups:
                return groups[0]
        return []

    async def async_step_group_members(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Choose the LEDs of the group (at least two).

        A new group starts with the lamps grouped in the ReefBeat app (in its
        order), when a cloud account lists some.
        """
        candidates = self._group_candidates()
        current = [
            e for e in self._group_members() if e in candidates
        ] or self._cloud_grouped(candidates)
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = [
                str(e)
                for e in user_input.get(CONF_GROUP_MEMBERS, [])
                if e in candidates
            ]
            if len(selected) < GROUP_MIN_MEMBERS:
                errors["base"] = "group_min_members"
            else:
                # Keep the order of the members kept, new ones at the end
                self._new_group_members = [e for e in current if e in selected] + [
                    e for e in selected if e not in current
                ]
                return await self.async_step_group_order()

        schema = vol.Schema(
            {
                vol.Required(CONF_GROUP_MEMBERS, default=current): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=entry_id, label=label)
                            for entry_id, label in candidates.items()
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="group_members", data_schema=schema, errors=errors
        )

    async def async_step_group_order(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Order the LEDs of the group: one LED per position.

        The order is the group order of the ReefBeat app (group_index): the
        staggered sunrise starts with the first LED.
        """
        members = self._new_group_members
        errors: dict[str, str] = {}
        if user_input is not None:
            ordered = [
                str(user_input.get(f"{CONF_GROUP_POSITION}{pos + 1}"))
                for pos in range(len(members))
            ]
            if sorted(ordered) != sorted(members):
                errors["base"] = "group_duplicate_position"
                members = ordered
            else:
                data = {
                    CONFIG_FLOW_IP_ADDRESS: self._config_entry.data[
                        CONFIG_FLOW_IP_ADDRESS
                    ],
                    CONFIG_FLOW_HW_MODEL: VIRTUAL_LED,
                    CONFIG_FLOW_SCAN_INTERVAL: VIRTUAL_LED_SCAN_INTERVAL,
                    CONF_GROUP_MEMBERS: ordered,
                }
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=data, options=self._config_entry.options
                )
                return self.async_create_entry(data=data)

        candidates = self._group_candidates()
        options = [
            SelectOptionDict(value=entry_id, label=candidates.get(entry_id, entry_id))
            for entry_id in self._new_group_members
        ]
        schema = vol.Schema(
            {
                vol.Required(
                    f"{CONF_GROUP_POSITION}{pos + 1}", default=entry_id
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=options, mode=SelectSelectorMode.DROPDOWN
                    )
                )
                for pos, entry_id in enumerate(members)
            }
        )
        return self.async_show_form(
            step_id="group_order", data_schema=schema, errors=errors
        )

    # ------------------------------------------------------------------
    # Probe add / remove steps (RSCONTROL hub only)
    # ------------------------------------------------------------------

    def _control_coordinator(self) -> Any:
        """The coordinator backing this options entry (an RSCONTROL hub)."""
        return self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)

    async def async_step_add_probe(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Install a new probe by type, mirroring the app's add-sensor flow.

        Pick a type → the hub BLE-scans → on success the entry is reloaded so the
        new probe's entities appear; if nothing is found, the form re-shows an
        error naming the type.
        """
        errors: dict[str, str] = {}
        coordinator = self._control_coordinator()
        if user_input is not None and coordinator is not None:
            ptype = user_input[CONFIG_FLOW_PROBE_TYPE]
            try:
                uid = await coordinator.async_install_probe(ptype)
            except Exception:
                _LOGGER.exception("Probe install failed")
                uid = None
            if uid:
                res = self.async_create_entry(
                    title="", data=dict(self._config_entry.options)
                )
                self.hass.config_entries.async_schedule_reload(res["handler"])
                return res
            errors["base"] = "no_probe_detected"
            self._last_probe_type = ptype

        return self.async_show_form(
            step_id="add_probe",
            data_schema=vol.Schema(
                {
                    vol.Required(CONFIG_FLOW_PROBE_TYPE): vol.In(
                        list(CONTROL_PROBE_TYPES)
                    )
                }
            ),
            errors=errors,
            description_placeholders={
                "probe_type": getattr(self, "_last_probe_type", "")
            },
        )

    async def async_step_del_probe(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Select probes to remove, then confirm (removal drops entities+stats)."""
        coordinator = self._control_coordinator()
        probes = coordinator.list_probes() if coordinator is not None else []
        if not probes:
            return self.async_abort(reason="no_probes")

        # value "type:uid" → label "name (type- uid)" — the uid disambiguates
        # two probes of the same type (e.g. two pH probes).
        options = {
            f"{p['type']}:{p['uid']}": f"{p['name']} ({p['type']}- {p['uid']})"
            for p in probes
        }

        if user_input is not None:
            self._del_tokens = list(user_input.get(CONFIG_FLOW_PROBES, []))
            if not self._del_tokens:
                return self.async_abort(reason="no_probes")
            return await self.async_step_del_probe_confirm()

        return self.async_show_form(
            step_id="del_probe",
            data_schema=vol.Schema(
                {vol.Required(CONFIG_FLOW_PROBES): cv.multi_select(options)}
            ),
        )

    async def async_step_del_probe_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Warn that removal deletes the probe's entities and their history.

        Submitting confirms; closing/going back cancels without any change.
        """
        coordinator = self._control_coordinator()
        tokens = getattr(self, "_del_tokens", [])
        if user_input is not None and coordinator is not None:
            for token in tokens:
                ptype, _, uid = token.partition(":")
                try:
                    await coordinator.async_delete_probe(ptype, uid)
                except Exception:
                    _LOGGER.exception("Probe delete failed for %s", token)
            res = self.async_create_entry(
                title="", data=dict(self._config_entry.options)
            )
            self.hass.config_entries.async_schedule_reload(res["handler"])
            return res

        return self.async_show_form(
            step_id="del_probe_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"probes": ", ".join(tokens)},
        )

    async def async_step_change_probe(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Replace a probe with a new one of the same type, keeping its history.

        Pick the probe to replace → the hub scans for a new probe of the same
        type → on success the old probe's entities are moved onto the new uid
        (so their history/statistics carry over), the old probe is removed and
        the entry reloaded. If nothing is found, an error is shown.
        """
        errors: dict[str, str] = {}
        coordinator = self._control_coordinator()
        probes = coordinator.list_probes() if coordinator is not None else []
        if not probes:
            return self.async_abort(reason="no_probes")

        # value "type:uid" → label "name (type- uid)" — the uid disambiguates
        # two probes of the same type (e.g. two pH probes).
        options = {
            f"{p['type']}:{p['uid']}": f"{p['name']} ({p['type']}- {p['uid']})"
            for p in probes
        }

        if user_input is not None and coordinator is not None:
            token = user_input[CONFIG_FLOW_OLD_PROBE]
            old_type, _, old_uid = token.partition(":")
            try:
                new_uid = await coordinator.async_install_probe(old_type)
            except Exception:
                _LOGGER.exception("Probe install (replace) failed")
                new_uid = None
            if new_uid:
                from . import _rename_probe_entities

                _rename_probe_entities(
                    self.hass,
                    self._config_entry,
                    coordinator,
                    old_type,
                    old_uid,
                    new_uid,
                )
                try:
                    await coordinator.async_delete_probe(old_type, old_uid)
                except Exception:
                    _LOGGER.exception("Old probe delete failed for %s", token)
                res = self.async_create_entry(
                    title="", data=dict(self._config_entry.options)
                )
                self.hass.config_entries.async_schedule_reload(res["handler"])
                return res
            errors["base"] = "no_probe_detected"

        return self.async_show_form(
            step_id="change_probe",
            data_schema=vol.Schema(
                {vol.Required(CONFIG_FLOW_OLD_PROBE): vol.In(options)}
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Wi-Fi provisioning steps
    # ------------------------------------------------------------------

    async def async_step_wifi_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Scan the device's Wi-Fi and let the user pick a network."""
        errors: dict[str, str] = {}
        ip = str(self._config_entry.data.get(CONFIG_FLOW_IP_ADDRESS, ""))
        session = async_get_clientsession(self.hass)

        # Trigger a scan on first entry or when the user asked to rescan.
        should_scan = user_input is None or bool(
            user_input.get(CONFIG_FLOW_WIFI_RESCAN, False)
        )

        if should_scan:
            try:
                self._wifi_networks = await scan_wifi(session, ip)
            except Exception as err:
                _LOGGER.warning("Wi-Fi scan failed for %s: %s", ip, err)
                errors["base"] = "wifi_scan_failed"
                self._wifi_networks = []

            if not errors and not self._wifi_networks:
                errors["base"] = "wifi_no_networks"

            # Best-effort: learn which SSID the device is on right now so the
            # form can pre-select it. Never fatal — get_current_ssid swallows
            # its own errors and returns None on older firmware.
            self._wifi_current_ssid = await get_current_ssid(session, ip)

        # Second submission: user picked a network and a password.
        if (
            user_input is not None
            and not user_input.get(CONFIG_FLOW_WIFI_RESCAN, False)
            and not errors
        ):
            ssid = str(user_input.get(CONFIG_FLOW_WIFI_SSID, "")).strip()
            password = str(user_input.get(CONFIG_FLOW_WIFI_PASSWORD, ""))

            if not ssid:
                errors["base"] = "wifi_no_ssid"
            else:
                # Keep the selection around for the apply step and hand off.
                self._wifi_selected_ssid = ssid
                self._wifi_selected_password = password
                return await self.async_step_wifi_apply()

        return self.async_show_form(
            step_id="wifi_scan",
            data_schema=self._build_wifi_scan_schema(),
            errors=errors,
            description_placeholders={
                "ip": ip,
                "count": str(len(self._wifi_networks)),
            },
        )

    def _build_wifi_scan_schema(self) -> vol.Schema:
        """Return the voluptuous schema for the ``wifi_scan`` form.

        The SSID dropdown maps SSID -> human label. When the last scan
        returned no networks (initial errors or empty scan) we still show the
        form so the user can trigger a rescan without leaving the flow.

        The SSID field is `Optional` (not `Required`) so the user can submit
        the rescan checkbox alone without picking a network — enforcement of
        "SSID required when not rescanning" happens in the step handler.
        """
        options: dict[str, str] = {}
        for net in self._wifi_networks:
            ssid = str(net.get("ssid", ""))
            if not ssid:
                continue
            signal = net.get("signal_dBm")
            security = str(net.get("security") or "open")
            channel = net.get("channel")
            signal_s = f"{signal} dBm" if isinstance(signal, (int, float)) else "?"
            channel_s = f"ch {channel}" if isinstance(channel, int) else ""
            label = f"{ssid} ({signal_s}, {channel_s}, {security})".replace(", ,", ",")
            options[ssid] = label

        schema: dict[Any, Any] = {}
        if options:
            # Pre-select the network the device is currently on, but only if
            # it actually appears in the scan results (the device can't see
            # its own SSID in some edge cases, and we must not default to a
            # value absent from the vol.In set or validation would fail).
            # getattr guards direct _build_wifi_scan_schema() callers that
            # bypass __init__ (e.g. schema-only unit tests).
            current_ssid = getattr(self, "_wifi_current_ssid", None)
            if current_ssid in options:
                ssid_field: Any = vol.Optional(
                    CONFIG_FLOW_WIFI_SSID, default=current_ssid
                )
            else:
                ssid_field = vol.Optional(CONFIG_FLOW_WIFI_SSID)
            schema[ssid_field] = vol.In(options)
            schema[vol.Optional(CONFIG_FLOW_WIFI_PASSWORD, default="")] = str
        # Rescan is always available so the user can retry after a bad scan
        # without having to close and reopen the options dialog.
        schema[vol.Optional(CONFIG_FLOW_WIFI_RESCAN, default=False)] = bool
        return vol.Schema(schema)

    async def async_step_wifi_apply(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Run connect → reset → rediscover as a background task with progress.

        The task returns the new IP address on success, or raises to signal
        the specific failure (wired to translated abort reasons).
        """
        # Kick off the background work on the first call, then let HA re-drive
        # this step until the task completes.
        if self._wifi_task is None:
            self._wifi_outcome = None
            self._wifi_task = self.hass.async_create_task(self._do_wifi_apply())

        if not self._wifi_task.done():
            return self.async_show_progress(
                step_id="wifi_apply",
                progress_action="applying",
                progress_task=self._wifi_task,
            )

        # Task done. It never raises by design, but guard against an
        # unexpected crash (cancellation or a bug in _do_wifi_apply) so the
        # flow still terminates cleanly instead of hanging.
        if self._wifi_task.cancelled() or self._wifi_task.exception() is not None:
            _LOGGER.exception(
                "Unexpected error during Wi-Fi apply",
                exc_info=None
                if self._wifi_task.cancelled()
                else self._wifi_task.exception(),
            )
            self._wifi_outcome = "failed_unknown"

        outcome = self._wifi_outcome
        # Reset task handle so the next step can proceed cleanly.
        self._wifi_task = None

        if outcome == "manual":
            # Every locally-attached subnet was scanned without success. The
            # device may sit on a network HA can only reach through a
            # router — offer a manual CIDR input step rather than aborting.
            return self.async_show_progress_done(next_step_id="wifi_manual_subnet")

        # Map the outcome onto the reason the finish step will abort with.
        reason_by_outcome = {
            "success": "wifi_change_success",
            "failed_connect": "wifi_change_failed_connect",
            "failed_reset": "wifi_change_failed_reset",
        }
        self._wifi_result_reason = reason_by_outcome.get(
            outcome or "", "wifi_change_failed_unknown"
        )
        return self.async_show_progress_done(next_step_id="wifi_finish")

    async def _do_wifi_apply(self) -> None:
        """Background worker: connect, reset, rediscover, update the entry.

        This coroutine never raises: it records the outcome in
        ``self._wifi_outcome`` (one of ``"success"``, ``"manual"``,
        ``"failed_connect"``, ``"failed_reset"``, ``"failed_unknown"``) and,
        on success, the new IP in ``self._wifi_new_ip``. Keeping the task
        exception-free makes routing deterministic regardless of how a given
        Home Assistant version propagates exceptions raised inside a
        progress task.

        Rediscovery is done on every subnet Home Assistant is directly
        reachable (via :func:`list_scannable_subnets`), which handles the
        common "device moved to a different LAN" case for multi-homed
        hosts. The unlucky case — device on a subnet HA can't reach
        directly — is reported as the ``"manual"`` outcome so the flow can
        offer a manual CIDR fallback.
        """
        ssid = self._wifi_selected_ssid or ""
        password = self._wifi_selected_password or ""
        entry = self._config_entry
        session = async_get_clientsession(self.hass)

        current_ip = str(entry.data.get(CONFIG_FLOW_IP_ADDRESS, ""))
        hw_model = entry.data.get(CONFIG_FLOW_HW_MODEL)
        friendly_name = entry.title
        # unique_id is the device UUID for local entries (see _unique_id()).
        uuid = entry.unique_id

        _LOGGER.info(
            "Wi-Fi apply starting: entry=%s current_ip=%s ssid=%r",
            entry.entry_id,
            current_ip,
            ssid,
        )

        try:
            # 1) Send the new credentials
            ok = await connect_wifi(session, current_ip, ssid, password)
            if not ok:
                self._wifi_outcome = "failed_connect"
                return

            # 2) Let the firmware persist the credentials before rebooting
            await asyncio.sleep(WIFI_POST_CONNECT_WAIT)

            # 3) Reboot the device to apply the new Wi-Fi credentials
            ok = await reset_device(session, current_ip)
            if not ok:
                self._wifi_outcome = "failed_reset"
                return

            # 4) Give the device time to reboot and re-join the network
            # before scanning. Too short causes false negatives; too long
            # frustrates the user.
            await asyncio.sleep(WIFI_POST_RESET_WAIT)

            # 5) Enumerate every reachable subnet so we can find the device
            # even if the Wi-Fi change moved it to another LAN — including a
            # subnet reached through a router (gateway routes), not just the
            # directly-attached interfaces. get_reefbeats(None) already scans
            # all of them, but we keep the explicit list to show the user
            # which CIDRs were tried if we fall back to the manual step.
            scannable = await self.hass.async_add_executor_job(list_scannable_subnets)
            self._wifi_manual_candidates = list(scannable)
            subnetworks: list[str | None] = [None, *scannable]

            # 6) Rediscover by UUID (primary) or hw_model + friendly_name.
            new_ip = await rediscover_device(
                self.hass,
                uuid=uuid,
                hw_model=str(hw_model) if hw_model else None,
                friendly_name=friendly_name,
                max_attempts=WIFI_REDISCOVER_MAX_ATTEMPTS,
                interval=WIFI_REDISCOVER_INTERVAL,
                subnetworks=subnetworks,
            )
        except Exception:
            _LOGGER.exception("Unexpected error during Wi-Fi apply")
            self._wifi_outcome = "failed_unknown"
            return

        if not new_ip:
            # We scanned every reachable subnet with no luck: let the flow
            # offer a manual CIDR fallback instead of giving up.
            self._wifi_outcome = "manual"
            return

        # 7) Persist the new IP; the update listener reloads the entry and
        # recreates the coordinator against the new IP.
        self._update_entry_ip(new_ip)
        self._wifi_new_ip = new_ip
        self._wifi_outcome = "success"
        _LOGGER.info(
            "Wi-Fi apply succeeded: entry=%s new_ip=%s (was %s)",
            entry.entry_id,
            new_ip,
            current_ip,
        )

    def _update_entry_ip(self, new_ip: str) -> None:
        """Persist the new IP address into the config entry data.

        Extracted so both the automatic and manual-subnet paths update the
        entry the same way. The update listener registered by
        :func:`async_setup_entry` picks up the change and reloads the entry,
        which recreates the coordinator against the new IP.
        """
        entry = self._config_entry
        new_data = {**dict(entry.data), CONFIG_FLOW_IP_ADDRESS: new_ip}
        self.hass.config_entries.async_update_entry(entry, data=new_data)

    async def async_step_wifi_manual_subnet(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask the user for a subnet CIDR to scan, when auto-discovery gave up.

        Reached only via ``async_step_wifi_apply`` after every locally
        attached subnet was scanned without finding the device. This step
        supports three outcomes:

        - **Cancel**: the user submits the form with an empty CIDR → abort
          the flow with the ``wifi_change_failed_rediscover`` reason so the
          user keeps the same "give up" feedback they would have received
          had we aborted directly.
        - **Invalid input**: the CIDR does not parse → re-show the form with
          ``wifi_bad_cidr`` inline error.
        - **Found**: the given CIDR contains the device → persist the new IP
          into the entry data and abort with ``wifi_change_success``.
        - **Not found**: the CIDR parses but does not contain the device →
          re-show the form with ``wifi_manual_not_found`` inline error so
          the user can try another CIDR.

        We treat the call as a form submission only when our own field is
        present in ``user_input``. When Home Assistant re-invokes this step
        as part of the progress → form transition it may pass a non-None
        ``user_input`` that does not contain our field (its exact content
        varies across HA versions); in that case we must show the form, not
        interpret a missing field as an empty "give up" submission.
        """
        errors: dict[str, str] = {}
        entry = self._config_entry
        hw_model = entry.data.get(CONFIG_FLOW_HW_MODEL)
        friendly_name = entry.title
        uuid = entry.unique_id

        if user_input is not None and CONFIG_FLOW_WIFI_MANUAL_SUBNET in user_input:
            cidr = str(user_input.get(CONFIG_FLOW_WIFI_MANUAL_SUBNET, "")).strip()

            if not cidr:
                # Empty submission = user chose to give up.
                return self.async_abort(
                    reason="wifi_change_failed_rediscover",
                    description_placeholders={
                        "ssid": self._wifi_selected_ssid or "",
                    },
                )

            if not is_valid_cidr(cidr):
                errors["base"] = "wifi_bad_cidr"
            else:
                # Single-pass scan on the user-provided CIDR. No retry loop
                # here: at this point the device has been rebooted for well
                # over a minute, so if it's on that subnet the first scan
                # will find it.
                new_ip = await rediscover_device(
                    self.hass,
                    uuid=uuid,
                    hw_model=str(hw_model) if hw_model else None,
                    friendly_name=friendly_name,
                    max_attempts=1,
                    interval=0,
                    subnetworks=[cidr],
                )
                if new_ip:
                    self._update_entry_ip(new_ip)
                    self._wifi_new_ip = new_ip
                    return self.async_abort(
                        reason="wifi_change_success",
                        description_placeholders={
                            "new_ip": new_ip,
                            "ssid": self._wifi_selected_ssid or "",
                        },
                    )
                errors["base"] = "wifi_manual_not_found"

        tried = ", ".join(self._wifi_manual_candidates) or "-"
        return self.async_show_form(
            step_id="wifi_manual_subnet",
            data_schema=vol.Schema(
                {vol.Optional(CONFIG_FLOW_WIFI_MANUAL_SUBNET, default=""): str},
            ),
            errors=errors,
            description_placeholders={
                "ssid": self._wifi_selected_ssid or "",
                "tried_subnets": tried,
            },
        )

    async def async_step_wifi_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Terminate the flow with an abort reason describing the outcome."""
        reason = self._wifi_result_reason or "wifi_change_failed_unknown"
        placeholders: dict[str, str] = {}
        if self._wifi_new_ip:
            placeholders["new_ip"] = self._wifi_new_ip
        if self._wifi_selected_ssid:
            placeholders["ssid"] = self._wifi_selected_ssid
        return self.async_abort(
            reason=reason,
            description_placeholders=placeholders or None,
        )
