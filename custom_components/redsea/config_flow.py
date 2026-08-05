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

from .auto_detect import ReefBeatInfo, get_reefbeats, get_unique_id, is_reefbeat
from .auto_detect import is_valid_cidr, list_scannable_subnets
from .const import (
    ADD_CLOUD_API,
    ADD_LOCAL_DETECT,
    ADD_MANUAL_MODE,
    ADD_TYPES,
    ATO_SCAN_INTERVAL,
    CLOUD_DEVICE_TYPE,
    CLOUD_SCAN_INTERVAL,
    CLOUD_SERVER_ADDR,
    CONFIG_FLOW_ADD_TYPE,
    CONFIG_FLOW_CLOUD_PASSWORD,
    CONFIG_FLOW_CLOUD_USERNAME,
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_DISABLE_SUPPLEMENT,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_INTENSITY_COMPENSATION,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_SCAN_INTERVAL,
    CONFIG_FLOW_WIFI_PASSWORD,
    CONFIG_FLOW_WIFI_RESCAN,
    CONFIG_FLOW_WIFI_SSID,
    CONFIG_FLOW_WIFI_MANUAL_SUBNET,
    CONTROL_SCAN_INTERVAL,
    DOMAIN,
    DOSE_SCAN_INTERVAL,
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
    LINKED_LED,
    MAT_SCAN_INTERVAL,
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
from .reefbeat import parse
from .wifi import (
    connect_wifi,
    get_current_ssid,
    rediscover_device,
    reset_device,
    scan_wifi,
)

_LOGGER = logging.getLogger(__name__)


# Helpers
async def validate_cloud_input(
    hass: HomeAssistant, username: str, password: str
) -> bool:
    """Validate ReefBeat cloud credentials.

    Notes:
        Uses OAuth password grant against CLOUD_SERVER_ADDR.
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
                f"https://{CLOUD_SERVER_ADDR}/oauth/token",
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
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONFIG_FLOW_CLOUD_USERNAME): str,
                            vol.Required(CONFIG_FLOW_CLOUD_PASSWORD): str,
                        }
                    ),
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
            valid = await validate_cloud_input(
                self.hass,
                str(user_input[CONFIG_FLOW_CLOUD_USERNAME]),
                str(user_input[CONFIG_FLOW_CLOUD_PASSWORD]),
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
                    }
                )
                return self.async_show_form(
                    step_id="user", data_schema=schema, errors=errors
                )

            user_input[CONFIG_FLOW_SCAN_INTERVAL] = get_scan_interval(CLOUD_DEVICE_TYPE)
            user_input[CONFIG_FLOW_CONFIG_TYPE] = False
            user_input[CONFIG_FLOW_IP_ADDRESS] = CLOUD_SERVER_ADDR
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
          settings form or a Wi-Fi provisioning flow. Cloud accounts and
          virtual LED entries skip the menu and go straight to their
          dedicated form to preserve their existing UX.
        - settings: classic form (scan_interval, live_config_update, and
          optional intensity_compensation / cloud credentials / linked-LEDs).
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
            # Virtual LEDs only expose a linking form — no menu, no Wi-Fi.
            return await self.async_step_settings(user_input)

        if kind == "cloud":
            # Cloud accounts have no local IP — no Wi-Fi provisioning either.
            return await self.async_step_settings(user_input)

        # Local device: only offer the menu if the hardware model looks
        # like a known ReefBeat device. Otherwise fall back to the plain
        # settings form so mis-configured entries stay recoverable.
        hw_model = self._config_entry.data.get(CONFIG_FLOW_HW_MODEL)
        if hw_model in HW_DEVICES_IDS:
            return self.async_show_menu(
                step_id="init",
                menu_options=[OPTIONS_MENU_SETTINGS, OPTIONS_MENU_WIFI],
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

            # Virtual LED linking options
            leds: dict[str, bool] = {}
            for led_key, enabled in user_input.items():
                if enabled:
                    leds[led_key] = True

            data = {
                CONFIG_FLOW_IP_ADDRESS: self._config_entry.data[CONFIG_FLOW_IP_ADDRESS],
                CONFIG_FLOW_HW_MODEL: VIRTUAL_LED,
                CONFIG_FLOW_SCAN_INTERVAL: VIRTUAL_LED_SCAN_INTERVAL,
                LINKED_LED: leds,
            }
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=data, options=self._config_entry.options
            )
            return self.async_create_entry(data=data)

        errors: dict[str, str] = {}
        options_schema: vol.Schema | None = None

        if not self._config_entry.title.startswith(VIRTUAL_LED + "-"):
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
                        vol.Required(
                            CONFIG_FLOW_DISABLE_SUPPLEMENT, default=True
                        ): bool,
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
        else:
            leds_schema: dict[Any, Any] = {}
            for dev_id in self.hass.data.get(DOMAIN, {}):
                led = self.hass.data[DOMAIN][dev_id]
                if type(led).__name__ in ("ReefLedCoordinator", "ReefLedG2Coordinator"):
                    key = f"LED-{led.model}-: {led.serial} ({dev_id})"
                    leds_schema[vol.Required(key)] = bool
            options_schema = vol.Schema(leds_schema)

        # We render the same form under two step ids: "init" for cloud/virtual
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
