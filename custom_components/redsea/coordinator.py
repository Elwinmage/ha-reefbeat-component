"""ReefBeat coordinators.

This module defines the integration's coordinator layer: objects responsible for
fetching device state, exposing convenience helpers over the underlying API,
and providing device metadata for the Home Assistant device registry.

Coordinator structure:
- `ReefBeatCoordinator`: base class for all devices (wraps a single API instance).
- `ReefBeatCloudLinkedCoordinator`: base for local devices that can optionally
    link to a `ReefBeatCloudCoordinator` via HA bus events.
- Device-specific coordinators (LED/MAT/DOSE/ATO/RUN/WAVE) select the correct API
    and implement any device-specific behavior (e.g. schedule updates, aggregation).

Notes:
- Entities should depend on coordinator public APIs (`get_data`, `set_data`,
    `push_values`, `device_info`, and public properties like `title`, `serial`,
    `model_id`), and should avoid accessing protected members.
- JSONPath strings are interpreted by the API layer (`reefbeat.py`), not here.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from asyncio import timeout
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from time import time
from typing import Any, cast

from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY, ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.event_type import EventType

from .const import (
    CONF_GROUP_MEMBERS,
    CONFIG_FLOW_CLOUD_PASSWORD,
    CONFIG_FLOW_CLOUD_USERNAME,
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_DISABLE_SUPPLEMENT,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_INTENSITY_COMPENSATION,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_SCAN_INTERVAL,
    DEVICE_MANUFACTURER,
    DOMAIN,
    GROUP_MIN_MEMBERS,
    HTTP_DELAY_BETWEEN_RETRY,
    HTTP_MAX_RETRY,
    HW_ATO_IDS,
    HW_CONTROL_IDS,
    HW_DOSE_IDS,
    HW_G2_LED_IDS,
    HW_LED_IDS,
    HW_MAT_IDS,
    HW_POWER_IDS,
    HW_RUN_IDS,
    HW_WAVE_IDS,
    LED_BLUE_INTERNAL_NAME,
    LED_MODE_INTERNAL_NAME,
    LED_MODES,
    LED_OFFSET_INTERNAL_NAME,
    LED_OFFSET_SOURCE,
    LED_WHITE_INTERNAL_NAME,
    LIGHTS_DEFAULT_UID_PREFIX,
    LIGHTS_G1_DEFAULT_NAMES,
    LIGHTS_G2_DEFAULTS,
    LIGHTS_G2_LIBRARY,
    LIGHTS_LIBRARY,
    PROBE_REFRESH_DELAY,
    REFRESH_DEVICE_DELAY,
    SCAN_INTERVAL,
    SCHEDULE_REFRESH_DELAY,
    SIGNAL_GROUP_MEMBER_GONE,
    SIGNAL_GROUP_MEMBER_READY,
    VIRTUAL_LED,
    WAVE_DIRECTIONS,
    WAVE_SCHEDULE_PATH,
    WAVES_LIBRARY,
)
from .groups import (
    ISSUE_CONFLICT,
    ISSUE_MIXED,
    ISSUE_NO_CLOUD,
    SYNC_ADOPT,
    SYNC_CONFLICT,
    SYNC_PUSH,
    GroupState,
    GroupStore,
    cloud_group_name,
    cloud_group_state,
    cloud_groups,
    discovery_unique_id,
    find_group,
    group_dispatch,
    group_error,
    in_group_dispatch,
    led_group_path,
    led_path_is_shared,
    led_source_is_shared,
    set_issue,
    staggered_offsets,
    sync_action,
)
from .maintenance import CALIBRATION_TASKS, MaintenanceStore, probe_sub_id
from .reefbeat import (
    ReefATOAPI,
    ReefBeatAPI,
    ReefBeatCloudAPI,
    ReefControlAPI,
    ReefDoseAPI,
    ReefLedAPI,
    ReefMatAPI,
    ReefPowerAPI,
    ReefRunAPI,
    ReefWaveAPI,
    fusion,
    parse,
)
from .wave_library import (
    WaveLibraryError,
    check_name,
    check_settings,
    check_slots,
    library_payload,
    library_wave,
    merge_pump_settings,
    program_waves,
    pump_settings_of,
    schedule_intervals,
    uses_wave,
)

_LOGGER = logging.getLogger(__name__)


def _accepted(result: Any) -> bool:
    """Whether the device acknowledged a write (an ``HttpResult`` with ok)."""
    return isinstance(result, dict) and bool(cast(dict[str, Any], result).get("ok"))


# Base coordinator types and common helpers

# =============================================================================
# Classes
# =============================================================================


class ReefBeatCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Base coordinator for a ReefBeat device.

    This coordinator owns a single API instance (`self.my_api`) and is responsible for:
    - periodic data fetches (DataUpdateCoordinator)
    - exposing a small convenience surface over the API (get/set/push/press/delete)
    - providing HA `DeviceInfo` for the device
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator from a config entry."""
        self._entry = entry
        scan_interval = int(entry.data.get(CONFIG_FLOW_SCAN_INTERVAL, SCAN_INTERVAL))

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

        # Keep integration state
        self._hass = hass
        self._session = async_get_clientsession(hass)
        self._ip: str = str(entry.data[CONFIG_FLOW_IP_ADDRESS])
        self._hw: str = str(entry.data[CONFIG_FLOW_HW_MODEL])
        self._title: str = entry.title
        self._live_config_update: bool = bool(
            entry.data.get(CONFIG_FLOW_CONFIG_TYPE, False)
        )
        self._boot = True
        # Unsubscribe callbacks of the event-bus listeners this coordinator
        # registered (see _listen); all released by unload().
        self._unsubs: list[CALLBACK_TYPE] = []

        # Default API for a generic ReefBeat device (specialized coordinators override this).
        self.my_api = ReefBeatAPI(self._ip, self._live_config_update, self._session)
        _LOGGER.info("%s scan interval set to %d", self._title, scan_interval)
        _LOGGER.info(
            "%s live configuration update %s", self._title, self._live_config_update
        )

    def clean_message(self, msg_type) -> None:
        self.my_api.clean_message(msg_type)
        self.async_update_listeners()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch fresh data from the device.

        This is called by DataUpdateCoordinator. Any exception is wrapped into
        UpdateFailed so HA can handle retries/backoff.
        """
        try:
            # fetch_data() concurrently fetches multiple endpoints. Each endpoint has its
            # own per-request timeout and retry loop in the API layer.
            #
            # If this coordinator timeout is shorter than the API retry budget, HA will
            # cancel the update (CancelledError) and timeout will surface it as a
            # TimeoutError (exactly what we saw in logs). Compute an upper bound that
            # matches the API behavior.
            per_try_timeout = int(getattr(self.my_api, "_timeout", 10))
            overall_timeout = (
                (per_try_timeout + HTTP_DELAY_BETWEEN_RETRY) * HTTP_MAX_RETRY
            ) + 5  # small buffer
            async with timeout(overall_timeout):
                res = cast(dict[str, Any] | None, await self.my_api.fetch_data())
            if res is None:
                raise UpdateFailed(f"No data received from API: {self._title}")
            # Only a device that answered none of its sources is treated as
            # down. A partial failure (one flaky endpoint) keeps the previous
            # values of that source and the rest of the device available;
            # _call_url already logs which source gave up.
            failed, total = self.my_api.fetch_failures
            if total and failed >= total:
                raise UpdateFailed(f"{self._title} ({self._ip}) did not respond")
            if failed:
                _LOGGER.debug(
                    "%s (%s): %d/%d sources did not respond, keeping their previous values",
                    self._title,
                    self._ip,
                    failed,
                    total,
                )
            return res
        except UpdateFailed:
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.debug(
                "Coordinator update timed out for %s (%s): %s",
                self._title,
                self._ip,
                err.__class__.__name__,
            )
            raise UpdateFailed(
                f"{self._title} ({self._ip}) update failed: TimeoutError"
            ) from err
        except Exception as err:
            _LOGGER.debug(
                "Coordinator update failed for %s (%s): %s",
                self._title,
                self._ip,
                err,
                exc_info=True,
            )
            raise UpdateFailed(
                f"{self._title} ({self._ip}) update failed: {err.__class__.__name__}: {err}"
            ) from err

    async def update(self) -> None:
        """Legacy helper; prefer `async_request_refresh()`."""
        await self.my_api.fetch_data()

    async def fetch_config(self, config_path: str | None = None) -> None:
        """Fetch configuration endpoints and notify listeners."""
        await self.my_api.fetch_config(config_path)
        self.async_update_listeners()

    async def _async_setup(self) -> None:
        """Perform one-time initialization (initial data fetch)."""
        _LOGGER.debug("%s async_setup...", self._title)
        if self._boot:
            self._boot = False
            await self.my_api.get_initial_data()

    async def async_request_refresh(
        self,
        source: str | None = None,
        config: bool = False,
        wait: int = REFRESH_DEVICE_DELAY,
    ) -> None:
        """config to True to also fetch config data"""
        # wait for device to refresh state
        if wait > 0:
            await asyncio.sleep(wait)
        if source is not None:
            self.my_api.quick_refresh = source
        if config:
            await self.my_api.fetch_config()
        return await super().async_request_refresh()

    async def async_setup(self) -> None:
        """Public entry-point for one-time initialization."""
        await self._async_setup()

    @property
    def device_info(self) -> DeviceInfo:
        """Home Assistant device registry metadata."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.model_id)},
            name=self.title,
            manufacturer=DEVICE_MANUFACTURER,
            model=self.model,
            model_id=self.model_id,
            hw_version=self.hw_version,
            sw_version=self.sw_version,
        )

    async def push_values(
        self, source: str = "/configuration", method: str = "put"
    ) -> None:
        """Push changed values to the device."""
        await self.my_api.push_values(source, method)

    def get_data(
        self, name: str, is_None_possible: bool = False, cached: bool = True
    ) -> Any:
        """Read a value from the cached API payload (JSONPath supported by the API layer).

        Pass ``cached=False`` for reads into a volatile array (a probe matched by
        ``type``/``uid``) so the value is re-matched every call and follows the
        item across reorders/deletions instead of a stale positional index.
        """
        return self.my_api.get_data(name, is_None_possible, cached)

    def set_data(self, name: str, value: Any) -> None:
        """Write a value into the cached API payload."""
        self.my_api.set_data(name, value)

    def data_exist(self, name: str) -> bool:
        """Return True if the named top-level key exists in the cached payload."""
        return name in self.my_api.data

    async def press(self, action: str) -> None:
        """Trigger a device action (API-defined)."""
        await self.my_api.press(action)

    async def delete(self, source: str) -> None:
        """Delete a resource on the device (API-defined)."""
        await self.my_api.delete(source)

    @property
    def title(self) -> str:
        """Human-readable name for this entry/device."""
        return self._title

    @property
    def serial(self) -> str:
        """Stable unique portion used by entities for unique IDs."""
        # Current integration uses title as serial / unique portion
        return self._title

    @property
    def model(self) -> str:
        """Device model name."""
        model = self.get_data(
            "$.sources[?(@.name=='/device-info')].data.hw_model", True
        )
        return str(model) if model is not None else self._hw

    @property
    def model_id(self) -> str:
        """Stable model identifier (used for device registry identifiers)."""
        res = self.get_data("$.sources[?(@.name=='/device-info')].data.hwid", True)
        if res in (None, "null"):
            res = self.get_data("$.sources[?(@.name=='/')].data.uuid", True)
        return str(res) if res is not None else self._title

    @property
    def board(self) -> str:
        """Firmware board identifier used by cloud endpoints."""
        b = self.get_data("$.sources[?(@.name=='/firmware')].data.board", True)
        return str(b) if b else "esp32"

    @property
    def framework(self) -> str:
        """Firmware framework identifier used by cloud endpoints."""
        fwork = self.get_data("$.sources[?(@.name=='/firmware')].data.framework", True)
        return str(fwork) if fwork else "i"

    @property
    def hw_version(self) -> Any:
        """Hardware version/revision."""
        hw_vers = self.get_data(
            "$.sources[?(@.name=='/device-info')].data.hw_revision", True
        )
        if hw_vers is None:
            hw_vers = self.get_data(
                "$.sources[?(@.name=='/firmware')].data.chip_version", True
            )
        return hw_vers

    @property
    def sw_version(self) -> str:
        """Firmware/software version."""
        sv = self.get_data("$.sources[?(@.name=='/firmware')].data.version", True)
        return str(sv) if sv is not None else "unknown"

    @property
    def detected_id(self) -> str:
        """Debug-friendly identifier for this coordinator/device."""
        return f"{self._ip} {self._hw} {self._title}"

    def _listen(
        self, event_type: EventType[Any] | str, handler: Callable[[Event], Any]
    ) -> None:
        """Listen to an event-bus event for as long as this coordinator lives.

        A coordinator is rebuilt on every setup attempt (retries after
        ConfigEntryNotReady, reloads): a listener registered straight on the
        bus would outlive it and keep firing on a dead instance.
        """
        self._unsubs.append(self._hass.bus.async_listen(event_type, handler))

    def unload(self) -> None:
        """Release the event-bus listeners of this coordinator.

        Idempotent. Called on entry unload and after a failed setup.
        """
        while self._unsubs:
            self._unsubs.pop()()


# Cloud-linked base
class ReefBeatCloudLinkedCoordinator(ReefBeatCoordinator):
    """Base for local devices that can link to a ReefBeat cloud account.

    This coordinator listens for a cloud coordinator being available and then
    establishes a link, primarily used for firmware information and wave library.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize common cloud-link state and register HA listeners."""
        super().__init__(hass, entry)
        self._cloud_link: ReefBeatCloudCoordinator | None = None
        self.latest_firmware_url: str | None = None

        self._listen(EVENT_HOMEASSISTANT_STARTED, self._handle_ask_for_link)

    async def _async_setup(self) -> None:
        """Perform one-time initialization and request cloud link if needed."""
        _LOGGER.debug("%s async_setup...", self._title)
        if self._boot:
            self._boot = False
            await self.my_api.get_initial_data()

            if str(self._hass.state) == "RUNNING":
                self._ask_for_link()

            self._listen(
                "redsea_ask_for_cloud_link_ready", self._handle_ask_for_link_ready
            )

    async def async_setup(self) -> None:
        """Public entry-point for one-time initialization."""
        await self._async_setup()

    @callback
    def _handle_ask_for_link(self, event: Any) -> None:
        """Ask for cloud link once HA is started."""
        self._ask_for_link()

    @callback
    def _handle_ask_for_link_ready(self, event: Any) -> None:
        """Handle cloud coordinator availability / teardown notifications."""
        if (
            event.data.get("state") == "off"
            and self._cloud_link is not None
            and self._cloud_link.title == event.data.get("account")
        ):
            _LOGGER.info(
                "Link to cloud %s closed for %s", event.data.get("account"), self._title
            )
            self._cloud_link = None
        else:
            self._ask_for_link()

    def _ask_for_link(self) -> None:
        """Fire an event to request a cloud coordinator link."""
        _LOGGER.info("%s ask for cloud link", self._title)
        self._hass.bus.fire(
            "redsea_ask_for_cloud_link", {"device_id": self._entry.entry_id}
        )

    def get_model_type(self, model: str) -> str | None:
        """Map a hardware model identifier to the cloud "model type" string."""
        if model in HW_LED_IDS:
            return "reef-lights"
        if model in HW_DOSE_IDS:
            return "reef-dosing"
        if model in HW_MAT_IDS:
            return "reef-mat"
        if model in HW_ATO_IDS:
            return "reef-ato"
        if model in HW_RUN_IDS:
            return "reef-run"
        if model in HW_WAVE_IDS:
            return "reef-wave"
        if model in HW_POWER_IDS:
            return "reef-power"
        if model in HW_CONTROL_IDS:
            return "reef-control"
        _LOGGER.error("unknown model: %s", model)
        return None

    async def set_cloud_link(self, cloud: ReefBeatCloudCoordinator) -> None:
        """Attach a cloud coordinator and register firmware endpoint subscription."""
        _LOGGER.info(f"{self._title} linked to cloud {cloud._title}")
        self._cloud_link = cloud
        model_type = self.get_model_type(self.model)
        if model_type is None:
            self.latest_firmware_url = None
        else:
            self.latest_firmware_url = f"/firmware/api/{model_type}/latest?board={self.board}&framework={self.framework}"
        await cloud.listen_for_firmware(self.latest_firmware_url, self._title)

    @property
    def cloud_coordinator(self) -> ReefBeatCloudCoordinator | None:
        """Return the linked cloud coordinator (if any)."""
        return self._cloud_link

    def cloud_link(self) -> str:
        """Return linked cloud account name, or 'None'."""
        return self._cloud_link.title if self._cloud_link is not None else "none"


# REEFLED
class ReefLedCoordinator(ReefBeatCloudLinkedCoordinator):
    """Coordinator for ReefLED devices (G1 and G2)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize LED API and configuration."""
        super().__init__(hass, entry)
        intensity_compensation = bool(
            entry.data.get(CONFIG_FLOW_INTENSITY_COMPENSATION, False)
        )
        self.my_api = ReefLedAPI(
            self._ip,
            self._live_config_update,
            self._session,
            self._hw,
            intensity_compensation,
        )
        # Weather program settings of the lamp (a WeatherStore, attached at
        # setup); see the `weather` property for a lamp of a group
        self._weather: Any = None
        _LOGGER.info(
            "%s intensity compensation: %s", self._title, intensity_compensation
        )

    def force_status_update(self, state: bool = False) -> None:
        """Ask the API to force a light status recalculation."""
        self.my_api.force_status_update(state)

    # -- Group routing ------------------------------------------------------
    # A lamp of a group behaves as in the ReefBeat app: a shared value set on
    # it (manual channels, mode, programs, acclimation...) is set on every
    # lamp of the group. The group itself writes to its lamps inside
    # group_dispatch(), where no routing happens.

    def led_group(self) -> ReefVirtualLedCoordinator | None:
        """The group of this lamp; None when alone or written by its group."""
        if in_group_dispatch():
            return None
        return cast(
            "ReefVirtualLedCoordinator | None",
            find_group(self._hass, self._entry.entry_id),
        )

    def set_data(self, name: str, value: Any) -> None:
        """Write data, on the whole group when the value is shared by it."""
        group = self.led_group()
        if group is not None and led_path_is_shared(name):
            group.route_set_data(name, value)
            return
        self._set_data_local(name, value)

    async def push_values(
        self, source: str = "/configuration", method: str = "put"
    ) -> None:
        """Push a source, to the whole group when it is shared by it."""
        group = self.led_group()
        if group is not None and led_source_is_shared(source):
            await group.push_values(source, method)
            return
        await super().push_values(source, method)

    def _set_data_local(self, name: str, value: Any) -> None:
        """Write data and update derived LED channels for G1 payloads."""
        super().set_data(name, value)
        if name in (LED_WHITE_INTERNAL_NAME, LED_BLUE_INTERNAL_NAME):
            self.my_api.update_light_wb()
        elif name.startswith("$.local.manual_trick."):
            _LOGGER.debug(
                "set_data: %s", self.my_api.data.get("local", {}).get("manual_trick")
            )
            self.my_api.data["local"]["manual_trick"][name.split(".")[-1]] = value
            self.my_api.update_light_ki()

    def daily_prog(self) -> Any:
        """Legacy helper (may be unused)."""
        return self.my_api.daily_prog  # type: ignore[attr-defined]

    async def post_specific(self, source: str) -> None:
        """POST to a LED-specific endpoint, on the whole group when shared."""
        group = self.led_group()
        if group is not None and led_source_is_shared(source):
            await group.post_specific(source)
            return
        await self.my_api.post_specific(source)

    async def delete(self, source: str) -> None:
        """DELETE a source, on the whole group when it is shared by it
        (the acclimation or the moon phase turned off on one of its lamps)."""
        group = self.led_group()
        if group is not None and led_source_is_shared(source):
            await group.delete(source)
            return
        await super().delete(source)

    def _settings_lamps(self) -> list[ReefLedCoordinator]:
        """Lamps a shared setting written here went to: its group's, or itself."""
        group = self.led_group()
        return list(group._linked) if group is not None else [self]

    @callback
    def expect_settings(self, source: str, enabled: bool) -> None:
        """Show at once the acclimation or moon phase just written, on every
        lamp it went to (optimistic update): see ReefLedAPI.expect_settings."""
        group = self.led_group()
        for lamp in self._settings_lamps():
            cast(Any, lamp.my_api).expect_settings(source, enabled)
            lamp.async_update_listeners()
        if group is not None:
            group.async_update_listeners()

    # -- Weather program -----------------------------------------------------
    # The lamps of a group share one weather program: the one of the group.
    # Turned on (or set) on any lamp of the group, it is on (and set) for
    # all of them, and each lamp gets its own weather week.

    @property
    def weather(self) -> Any:
        """Weather settings of the lamp: its group's when it is grouped."""
        group = self.led_group()
        if group is not None and group._weather is not None:
            return group._weather
        return self._weather

    @weather.setter
    def weather(self, store: Any) -> None:
        """Attach the lamp's own weather settings."""
        self._weather = store

    # -- Staggered sunrise offset --------------------------------------------

    @property
    def supports_offset(self) -> bool:
        """Whether the lamp has the /offset endpoint (staggered sunrise)."""
        return self.get_data(LED_OFFSET_INTERNAL_NAME, True) is not None

    async def set_offset(self, minutes: int) -> None:
        """Start the lamp's day `minutes` later (POST /offset replaces it)."""
        if not self.supports_offset:
            _LOGGER.warning("%s has no /offset: offset not set", self._title)
            return
        self._set_data_local(LED_OFFSET_INTERNAL_NAME, int(minutes))
        await self.push_values(LED_OFFSET_SOURCE, "post")
        self.async_update_listeners()

    @property
    def is_g1(self) -> bool:
        """Return True if the underlying LED API is using G1 protocol."""
        return bool(getattr(self.my_api, "_g1", False))

    # Cloud light library
    def library_link(self) -> tuple[ReefBeatCloudCoordinator, str] | None:
        """Cloud account and aquarium this lamp's programs are kept under.

        The ReefBeat app keeps light programs in a per-aquarium library: the
        lamp's aquarium is found in the account's device list, by hwid.
        """
        cloud = self._cloud_link
        if cloud is None:
            return None
        aquarium = cloud.get_data(
            "$.sources[?(@.name=='/device')].data[?(@.hwid=='"
            + str(self.model_id)
            + "')].aquarium_uid",
            True,
        )
        if not isinstance(aquarium, str) or not aquarium:
            return None
        return cloud, aquarium

    def library_g2(self) -> bool:
        """Whether the programs are G2 ones (color/moon), in the G2 library."""
        return not self.is_g1

    def linked_leds(self) -> list[dict[str, Any]]:
        """The lamps of the lamp's group, in order (see the virtual LED's)."""
        group = self.led_group()
        return group.linked_leds() if group is not None else []

    def weather_targets(self) -> list[ReefLedCoordinator]:
        """Lamps a weather program is written to: this one, or its group's."""
        group = self.led_group()
        if group is not None:
            return group.weather_targets()
        return [self]

    def _library_entries(
        self, cloud: ReefBeatCloudCoordinator, source: str
    ) -> list[Any]:
        """Entries of a cloud library source (a single one comes unwrapped)."""
        entries = cloud.get_data("$.sources[?(@.name=='" + source + "')].data", True)
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            return []
        return [e for e in cast(list[Any], entries) if isinstance(e, dict)]

    def light_library(self) -> list[dict[str, Any]] | None:
        """Light programs the lamp can use, None when not linked.

        As in the ReefBeat app, G1 programs are kept per aquarium in
        `/reef-lights/library` ({uid, name, program: {white, blue, moon},
        clouds}); G2 programs in the user's `/v2/reef-lights/library`
        ({id, name, color, moon, clouds}), plus the Red Sea programs built
        into the app. All are given in one shape: {uid, name, program,
        clouds, default}; a default (Red Sea) program cannot be edited nor
        deleted.
        """
        link = self.library_link()
        if link is None:
            return None
        cloud, aquarium = link
        if self.library_g2():
            defaults = [
                {
                    "uid": LIGHTS_DEFAULT_UID_PREFIX + prog["name"],
                    "name": prog["name"],
                    "program": {"color": prog["color"], "moon": prog["moon"]},
                    "clouds": None,
                    "default": True,
                }
                for prog in LIGHTS_G2_DEFAULTS
            ]
            return defaults + [
                {
                    "uid": entry.get("id"),
                    "name": entry.get("name"),
                    "program": {
                        key: entry[key] for key in ("color", "moon") if key in entry
                    },
                    "clouds": entry.get("clouds"),
                    "default": False,
                }
                for entry in self._library_entries(cloud, LIGHTS_G2_LIBRARY)
            ]
        return [
            {
                "uid": entry.get("uid"),
                "name": entry.get("name"),
                "program": entry.get("program"),
                "clouds": entry.get("clouds"),
                "default": entry.get("name") in LIGHTS_G1_DEFAULT_NAMES,
            }
            for entry in self._library_entries(cloud, LIGHTS_LIBRARY)
            if entry.get("aquarium_uid") == aquarium
        ]

    def _library_payload(
        self,
        name: str,
        program: dict[str, Any],
        clouds: dict[str, Any] | None,
        aquarium: str | None,
    ) -> dict[str, Any]:
        """Body of a library program, as the ReefBeat app sends it.

        - G1: {aquarium_uid (creation only), name, program, clouds?}
          (LedsProgram.putOrPost)
        - G2: {name, color, moon, clouds?} (LedG2Program.PutOrPost)
        """
        payload: dict[str, Any]
        if self.library_g2():
            payload = {"name": name}
            payload.update(
                {key: program[key] for key in ("color", "moon") if key in program}
            )
        else:
            payload = {"name": name, "program": program}
            if aquarium is not None:
                payload = {"aquarium_uid": aquarium, **payload}
        if clouds:
            payload["clouds"] = clouds
        return payload

    def _library_source(self) -> str:
        """Cloud source of the lamp's library."""
        return LIGHTS_G2_LIBRARY if self.library_g2() else LIGHTS_LIBRARY

    def library_program(self, uid: str) -> dict[str, Any] | None:
        """A program of the lamp's library, by uid."""
        for entry in self.light_library() or []:
            if entry.get("uid") == uid:
                return entry
        return None

    async def save_light_program(
        self,
        name: str,
        program: dict[str, Any],
        clouds: dict[str, Any] | None,
        uid: str | None = None,
    ) -> str | None:
        """Add a program to the lamp's library, or update one of its own.

        The program is on a single day's timeline (no weekday offset), in the
        lamp's own format: white/blue/moon (G1) or color/moon (G2). As the
        ReefBeat app: POST to create, PUT <library>/<uid> to update; the Red
        Sea programs cannot be updated.
        @param uid: the program to update, None to create one
        @return the uid of the program, None when not linked, when the
                program cannot be updated, or when the new one is not found
        """
        link = self.library_link()
        if link is None:
            return None
        cloud, aquarium = link
        source = self._library_source()
        path = source.split("?")[0]
        if uid is not None:
            entry = self.library_program(uid)
            if entry is None or entry.get("default"):
                return None
            payload = self._library_payload(name, program, clouds, None)
            _LOGGER.debug("PUT light program %s to %s: %s", uid, path, payload)
            await cloud.send_cmd(f"{path}/{uid}", payload, "put")
            await cloud.fetch_config(source)
            return uid
        payload = self._library_payload(name, program, clouds, aquarium)
        _LOGGER.debug("POST light program to %s: %s", path, payload)
        await cloud.send_cmd(path, payload, "post")
        # Read the library again: the new entry and its uid
        await cloud.fetch_config(source)
        for entry in reversed(self.light_library() or []):
            if entry.get("name") == name and not entry.get("default"):
                return cast(str | None, entry.get("uid"))
        return None

    async def delete_light_program(self, uid: str) -> bool:
        """Delete one of the user's programs from the lamp's library.

        As the ReefBeat app: DELETE <library>/<uid>. The Red Sea programs
        cannot be deleted.
        @return whether the program was deleted
        """
        link = self.library_link()
        if link is None:
            return False
        cloud, _aquarium = link
        entry = self.library_program(uid)
        if entry is None or entry.get("default"):
            return False
        source = self._library_source()
        path = source.split("?")[0]
        _LOGGER.debug("DELETE light program %s from %s", uid, path)
        await cloud.send_cmd(f"{path}/{uid}", {}, "delete")
        await cloud.fetch_config(source)
        return True


class ReefLedG2Coordinator(ReefLedCoordinator):
    """Coordinator for ReefLED G2 devices (uses G2 write semantics)."""

    def _set_data_local(self, name: str, value: Any) -> None:
        """Write directly via API without G1-derived field updates."""
        self.my_api.set_data(name, value)


# Virtual LED
class ReefVirtualLedCoordinator(ReefLedCoordinator):
    """Group of physical ReefLEDs, driven as one lamp (the app's "grouped" LEDs).

    The members are the config entries listed, in order, in
    ``entry.data[CONF_GROUP_MEMBERS]``. Reads are aggregated; writes are
    applied to every member, and only when all of them are there (as in the
    ReefBeat app). A write made on a member, when shared by the group, is
    routed here (see ReefLedCoordinator.led_group).
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the group and resolve the members already loaded."""
        # Loaded member coordinators, in the group order, and their entry ids
        self._linked: list[Any] = []
        self._linked_entries: list[str] = []
        # Staggered sunrise and offsets written (a GroupStore, attached at setup)
        self.group_store: GroupStore | None = None
        # Last group the cloud refused (not sent again until it changes)
        self._push_failed: GroupState | None = None
        # Members taken from the cloud: the group is being set up again
        self._reloading = False
        # Every member of the group, loaded or not, in the group order
        self.member_ids: list[str] = [
            str(eid) for eid in entry.data.get(CONF_GROUP_MEMBERS, [])
        ]
        # Only G1 lamps: white/blue channels can be set on the whole group
        self._only_g1: bool = not any(
            self._member_hw_model(hass, eid) in HW_G2_LED_IDS for eid in self.member_ids
        )

        super().__init__(hass, entry)

        if len(self.member_ids) < GROUP_MIN_MEMBERS:
            _LOGGER.error(
                "%s: link at least %d LEDs to this virtual LED (configure it)",
                self._title,
                GROUP_MIN_MEMBERS,
            )

        # Presence of the members: re-resolve them whenever one is loaded or
        # unloaded (a member reloaded on its own gets a new coordinator).
        for signal in (SIGNAL_GROUP_MEMBER_READY, SIGNAL_GROUP_MEMBER_GONE):
            self._unsubs.append(
                async_dispatcher_connect(hass, signal, self._handle_member_signal)
            )
        self._link_leds()

    @staticmethod
    def _member_hw_model(hass: HomeAssistant, entry_id: str) -> str | None:
        """Hardware model of a member, from its config entry."""
        member_entry = hass.config_entries.async_get_entry(entry_id)
        if member_entry is None:
            return None
        return cast(str | None, member_entry.data.get(CONFIG_FLOW_HW_MODEL))

    async def async_setup(self) -> None:
        """Public entry-point for one-time initialization."""

    @callback
    def _handle_member_signal(self, entry_id: str) -> None:
        """A device entry was loaded or unloaded: follow it if it is a member."""
        if entry_id not in self.member_ids:
            return
        self._link_leds()
        # The group and its lamps (their list of the group) are shown again
        self._notify_members()
        self.async_reconcile_staggered()

    @callback
    def _link_leds(self) -> None:
        """Resolve the loaded member coordinators, in the group order."""
        loaded = self._hass.data.get(DOMAIN, {})
        self._linked = []
        self._linked_entries = []
        for entry_id in self.member_ids:
            led = loaded.get(entry_id)
            if led is None:
                continue
            self._linked.append(led)
            self._linked_entries.append(entry_id)
        _LOGGER.debug(
            "%s linked to %d/%d LEDs: %s",
            self._title,
            len(self._linked),
            len(self.member_ids),
            [getattr(led, "title", "?") for led in self._linked],
        )

    # -- Members: presence, service, what blocks a group write ---------------

    def _cloud_of(self, hwid: str) -> tuple[ReefBeatCloudCoordinator, dict] | None:
        """The loaded cloud account listing a device, with its entry there."""
        for coordinator in self._hass.data.get(DOMAIN, {}).values():
            if not isinstance(coordinator, ReefBeatCloudCoordinator):
                continue
            device = coordinator.get_data(
                "$.sources[?(@.name=='/device')].data[?(@.hwid=='" + hwid + "')]",
                True,
            )
            if isinstance(device, dict):
                return coordinator, device
        return None

    def in_service(self, led: Any) -> bool:
        """Whether a lamp takes part in the group (the app's in_service).

        A lamp put out of service in the ReefBeat app is left out of the
        group's writes and checks, as the app does.
        """
        cloud = self._cloud_of(str(getattr(led, "model_id", "")))
        return cloud is None or cloud[1].get("in_service", True) is not False

    def _targets(self) -> list[Any]:
        """Loaded lamps of the group taking part in its writes."""
        return [led for led in self._linked if self.in_service(led)]

    def unavailable_members(self) -> list[str]:
        """Lamps blocking a group write, with the reason when it is known.

        As the ReefBeat app: a lamp not loaded or not answering, or in a mode
        the group cannot drive (off, or held by a shortcut: emergency,
        maintenance...). A lamp out of service does not block.
        """
        loaded = self._hass.data.get(DOMAIN, {})
        names: list[str] = []
        for entry_id in self.member_ids:
            led = loaded.get(entry_id)
            if led is None:
                member_entry = self._hass.config_entries.async_get_entry(entry_id)
                names.append(member_entry.title if member_entry else entry_id)
                continue
            if not self.in_service(led):
                continue
            title = str(getattr(led, "title", entry_id))
            if not getattr(led, "last_update_success", True):
                names.append(title)
                continue
            mode = led.get_data(LED_MODE_INTERNAL_NAME, True)
            if mode is not None and mode not in LED_MODES:
                names.append(f"{title} ({mode})")
        return names

    def _check_ready(self) -> None:
        """Refuse a write when a member is missing, as the ReefBeat app does.

        A group half-applied would leave its lamps out of sync: nothing is
        sent, and the user is told which lamps are missing.
        """
        names = self.unavailable_members()
        if names:
            raise group_error(
                "group_member_unavailable",
                group=self._title,
                members=", ".join(names),
            )

    def _notify_members(self) -> None:
        """Refresh the entities of the members after a group write."""
        for led in self._targets():
            update = getattr(led, "async_update_listeners", None)
            if callable(update):
                update()
        self.async_update_listeners()

    def route_set_data(self, name: str, value: Any) -> None:
        """Set a shared value made on a member, on the whole group."""
        path = led_group_path(name, self._only_g1)
        if path is None:
            raise group_error("group_channel_unavailable", group=self._title)
        self.set_data(path, value)

    # -- Staggered sunrise ----------------------------------------------------

    def staggered_offsets(self) -> dict[str, int]:
        """Offset each member should hold (entry id -> minutes)."""
        store = self.group_store
        if store is None:
            return {}
        loaded = self._hass.data.get(DOMAIN, {})
        members = [
            entry_id
            for entry_id in self.member_ids
            if entry_id not in loaded or self.in_service(loaded[entry_id])
        ]
        return staggered_offsets(members, store.staggered, store.delay)

    def offsets_pending(self) -> bool:
        """Whether the lamps may not hold the offsets of the group.

        A group that never had its staggered sunrise turned on leaves the
        lamps' offsets alone (they may have been set by the ReefBeat app).
        """
        store = self.group_store
        if store is None or (not store.applied and not store.staggered):
            return False
        return store.applied != self.staggered_offsets()

    async def async_apply_staggered(self) -> None:
        """Write the offset of each lamp, once all of them are there.

        A lamp that left the group gets its offset back to 0.
        """
        store = self.group_store
        if store is None:
            return
        self._check_ready()
        targets = self.staggered_offsets()
        loaded = self._hass.data.get(DOMAIN, {})
        for entry_id, offset in store.applied.items():
            former = loaded.get(entry_id)
            if entry_id not in targets and offset and former is not None:
                await former.set_offset(0)
        for entry_id, offset in targets.items():
            await loaded[entry_id].set_offset(offset)
        store.applied = targets
        await store.async_save()
        self._notify_members()

    async def async_set_staggered(
        self, staggered: bool | None = None, delay: Any | None = None
    ) -> None:
        """Change the staggered sunrise and write it to the lamps.

        Refused (nothing changed) when a lamp of the group is missing.
        """
        if self.group_store is None:
            return
        self._check_ready()
        await self.group_store.async_set(staggered, delay)
        await self.async_apply_staggered()

    @callback
    def async_reconcile_staggered(self) -> None:
        """Write the offsets again when the lamps may no longer hold them.

        Done once all the lamps are there: after a change of the members or
        of their order, or when a missing lamp comes back.
        """
        if self.offsets_pending() and not self.unavailable_members():
            self._hass.async_create_task(self._async_apply_quietly())

    async def _async_apply_quietly(self) -> None:
        try:
            await self.async_apply_staggered()
        except HomeAssistantError as err:
            _LOGGER.warning("%s: staggered sunrise not written: %s", self._title, err)

    def force_status_update(self, state: bool = False) -> None:
        """Virtual device does not force status on a single hardware light."""
        return

    async def _async_update_data(self) -> dict[str, Any]:
        """Aggregate data updates from all linked LED coordinators.

        Then check the group against the cloud (see _async_group_checks).
        """
        data: dict[str, Any] = {}
        for led in self._linked:
            try:
                res = await led.my_api.fetch_data()
                if isinstance(res, dict):
                    data.update(cast(dict[str, Any], res))
            except Exception:
                _LOGGER.exception(
                    "Error updating linked LED for virtual %s", self._title
                )
        try:
            await self._async_group_checks()
        except Exception:
            _LOGGER.exception("%s: group checks failed", self._title)
        return data

    # -- Cloud: round trip and Repairs ----------------------------------------

    def _issue(
        self, kind: str, active: bool, placeholders: dict[str, str] | None = None
    ) -> None:
        set_issue(
            self._hass,
            kind,
            self._entry.entry_id,
            active,
            {"group": self._title, **(placeholders or {})},
        )

    def cloud_context(self) -> tuple[ReefBeatCloudCoordinator, str, str] | None:
        """(cloud account, aquarium uid, model) of a group the cloud can hold.

        As in the ReefBeat app: the lamps of one model, all in one aquarium
        of one account. None otherwise (the group is then local only).
        """
        if not self._linked or len(self._linked) != len(self.member_ids):
            return None
        if len({str(getattr(led, "model", "")) for led in self._linked}) != 1:
            return None
        clouds = [self._cloud_of(str(led.model_id)) for led in self._linked]
        if any(c is None for c in clouds):
            return None
        found = cast(list[tuple[ReefBeatCloudCoordinator, dict]], clouds)
        accounts = {id(cloud) for cloud, _ in found}
        aquariums = {device.get("aquarium_uid") for _, device in found}
        if len(accounts) != 1 or len(aquariums) != 1:
            return None
        return found[0][0], str(aquariums.pop()), str(self._linked[0].model)

    def local_state(self) -> GroupState:
        """The group as Home Assistant holds it."""
        store = cast(GroupStore, self.group_store)
        return GroupState(
            tuple(str(led.model_id) for led in self._linked),
            store.staggered,
            store.delay,
        )

    def _known_lamps(self) -> dict[str, str]:
        """hwid -> entry id of the lamps Home Assistant has."""
        return {
            str(led.model_id): entry_id
            for entry_id, led in self._hass.data.get(DOMAIN, {}).items()
            if isinstance(led, ReefLedCoordinator)
            and not isinstance(led, ReefVirtualLedCoordinator)
        }

    @staticmethod
    def _cloud_aquarium(
        cloud: ReefBeatCloudCoordinator, aquarium_uid: str
    ) -> dict[str, Any] | None:
        """An aquarium of the cloud account."""
        aquariums = cloud.get_data("$.sources[?(@.name=='/aquarium')].data", True)
        return next(
            (
                a
                for a in (aquariums if isinstance(aquariums, list) else [])
                if isinstance(a, dict) and a.get("uid") == aquarium_uid
            ),
            None,
        )

    def cloud_state(
        self, cloud: ReefBeatCloudCoordinator, aquarium_uid: str, model: str
    ) -> GroupState:
        """The group as the cloud holds it (lamps HA knows only)."""
        devices = cloud.get_data("$.sources[?(@.name=='/device')].data", True)
        return cloud_group_state(
            devices,
            self._cloud_aquarium(cloud, aquarium_uid),
            aquarium_uid,
            model,
            set(self._known_lamps()),
        )

    async def _async_group_checks(self) -> None:
        """Keep the group and the cloud together, raise the Repairs issues.

        - a group of several models cannot be held by the cloud: its lamps
          must not stay grouped in the ReefBeat app (issue, fixed by
          ungrouping them there);
        - a group the cloud could hold, without a cloud account listing its
          lamps: issue (add the account, or keep the group local);
        - otherwise the group is synchronized both ways (see _async_sync).
        """
        store = self.group_store
        if store is None or not self._linked or self._reloading:
            return
        if len(self._linked) != len(self.member_ids):
            return  # a lamp still missing: nothing sure to say
        if len({str(getattr(led, "model", "")) for led in self._linked}) > 1:
            self._issue(ISSUE_NO_CLOUD, False)
            self._issue(ISSUE_CONFLICT, False)
            grouped = [
                led.title
                for led in self._linked
                if (c := self._cloud_of(str(led.model_id))) and c[1].get("grouped")
            ]
            self._issue(ISSUE_MIXED, bool(grouped), {"leds": ", ".join(grouped)})
            return
        self._issue(ISSUE_MIXED, False)
        context = self.cloud_context()
        if context is None or store.local_only:
            self._issue(ISSUE_NO_CLOUD, context is None and not store.local_only)
            self._issue(ISSUE_CONFLICT, False)
            return
        self._issue(ISSUE_NO_CLOUD, False)
        await self._async_sync(*context)

    async def _async_sync(
        self, cloud: ReefBeatCloudCoordinator, aquarium_uid: str, model: str
    ) -> None:
        """Bring Home Assistant and the cloud together (see sync_action)."""
        store = cast(GroupStore, self.group_store)
        local = self.local_state()
        remote = self.cloud_state(cloud, aquarium_uid, model)
        snapshot = GroupState.from_dict(store.snapshot)
        action = sync_action(local, remote, snapshot)
        if action == SYNC_CONFLICT:
            self._issue(ISSUE_CONFLICT, True)
            return
        self._issue(ISSUE_CONFLICT, False)
        if action == SYNC_PUSH:
            await self._async_push(cloud, aquarium_uid, model, local, snapshot, remote)
        elif action == SYNC_ADOPT:
            await self._async_adopt(remote)
        elif snapshot != local:
            store.snapshot = local.as_dict()
            await store.async_save()

    async def _async_push(
        self,
        cloud: ReefBeatCloudCoordinator,
        aquarium_uid: str,
        model: str,
        local: GroupState,
        *former: GroupState | None,
    ) -> None:
        """Write the group to the cloud, as the ReefBeat app does.

        POST /device/manage (grouped, group_index; the lamps that left get
        grouped false), the staggered sunrise of the model, the offset of
        each lamp; then the cloud is read again.
        """
        store = cast(GroupStore, self.group_store)
        if local == self._push_failed:
            return  # already refused: tried again once something changes
        devices = cloud.get_data("$.sources[?(@.name=='/device')].data", True)
        by_hwid = {
            str(d.get("hwid")): d
            for d in (devices if isinstance(devices, list) else [])
            if isinstance(d, dict)
        }
        left = {
            hwid
            for state in former
            if state is not None
            for hwid in state.members
            if hwid not in local.members
        }
        manage = [
            {
                "hwid": hwid,
                "name": by_hwid.get(hwid, {}).get("name", ""),
                "in_service": by_hwid.get(hwid, {}).get("in_service", True),
                "grouped": hwid in local.members,
                "group_index": local.members.index(hwid)
                if hwid in local.members
                else 0,
            }
            for hwid in [*local.members, *sorted(left)]
        ]
        results = [await cloud.send_cmd("/device/manage", manage, "post")]
        results.append(
            await cloud.send_cmd(
                f"/aquarium/{aquarium_uid}/group/"
                + cloud_group_name(self._cloud_aquarium(cloud, aquarium_uid), model),
                {
                    "properties": {
                        "staggered": local.staggered,
                        "staggered_delay": local.delay,
                    }
                },
                "put",
            )
        )
        offsets = self.staggered_offsets()
        for entry_id, led in zip(self._linked_entries, self._linked, strict=False):
            if entry_id in offsets:
                results.append(
                    await cloud.send_cmd(
                        f"/device/{led.model_id}", {"offset": offsets[entry_id]}, "put"
                    )
                )
        if not all(_accepted(r) for r in results):
            _LOGGER.warning("%s: the cloud refused the group", self._title)
            self._push_failed = local
            return
        self._push_failed = None
        await cloud.fetch_config("/device")
        cloud.my_api.quick_refresh = "/aquarium"
        await cloud.my_api.fetch_data()
        store.snapshot = local.as_dict()
        await store.async_save()
        _LOGGER.info("%s: group written to the cloud", self._title)

    async def _async_adopt(self, remote: GroupState) -> None:
        """Take the group as the ReefBeat app left it.

        The lamps or their order changed: the group is set up again with them
        (its offsets are then written); only the staggered sunrise changed:
        the offsets are written.
        """
        store = cast(GroupStore, self.group_store)
        known = self._known_lamps()
        members = [known[hwid] for hwid in remote.members if hwid in known]
        store.staggered = remote.staggered
        store.delay = remote.delay
        store.snapshot = remote.as_dict()
        await store.async_save()
        _LOGGER.info("%s: group taken from the ReefBeat app", self._title)
        if members != self.member_ids:
            # The group is set up again with them: nothing more to check here
            self._reloading = True
            self._hass.config_entries.async_update_entry(
                self._entry, data={**self._entry.data, CONF_GROUP_MEMBERS: members}
            )
            return
        self.async_reconcile_staggered()

    # -- Repairs fixes ------------------------------------------------------------

    async def async_keep_local(self) -> None:
        """No cloud for this group: kept in Home Assistant only."""
        store = cast(GroupStore, self.group_store)
        store.local_only = True
        await store.async_save()
        self._issue(ISSUE_NO_CLOUD, False)

    async def async_ungroup_in_cloud(self) -> None:
        """Ungroup the lamps of this (multi-model) group in the ReefBeat app."""
        by_cloud: dict[int, tuple[ReefBeatCloudCoordinator, list[dict]]] = {}
        for led in self._linked:
            found = self._cloud_of(str(led.model_id))
            if found is None or not found[1].get("grouped"):
                continue
            cloud, device = found
            by_cloud.setdefault(id(cloud), (cloud, []))[1].append(
                {
                    "hwid": str(led.model_id),
                    "name": device.get("name", ""),
                    "in_service": device.get("in_service", True),
                    "grouped": False,
                    "group_index": 0,
                }
            )
        for cloud, manage in by_cloud.values():
            await cloud.send_cmd("/device/manage", manage, "post")
            await cloud.fetch_config("/device")
        self._issue(ISSUE_MIXED, False)

    async def async_resolve_conflict(self, keep_home_assistant: bool) -> None:
        """Settle a conflict: Home Assistant's group, or the ReefBeat app's."""
        context = self.cloud_context()
        if context is None or self.group_store is None:
            return
        remote = self.cloud_state(*context)
        if keep_home_assistant:
            self._push_failed = None
            await self._async_push(*context, self.local_state(), remote)
        else:
            await self._async_adopt(remote)
        self._issue(ISSUE_CONFLICT, False)

    def get_data(
        self, name: str, is_None_possible: bool = False, cached: bool = True
    ) -> Any:
        """Get aggregated value from linked LEDs.

        Behavior:
        - Kelvin/intensity paths may be provided as "g1_path g2_path"
        - For scalar types, values are averaged or AND'ed where appropriate

        ``cached`` is accepted only to match the base signature. It targets
        volatile probe arrays (re-matched on every read), which LEDs do not
        have, so it is inert for the aggregation performed here.
        """
        del cached  # unused: no volatile arrays in LED aggregation
        if not self._linked:
            return None

        # Kelvin path for G1 or G2 is passed as "g1_path g2_path"
        names = name.split(" ")
        if len(names) > 1:
            return self.get_data_kelvin(name)

        data = self._linked[0].get_data(name, is_None_possible)
        match type(data).__name__:
            case "bool":
                return self.get_data_bool(name)
            case "int":
                return self.get_data_int(name)
            case "float":
                return self.get_data_float(name)
            case "str":
                return self.get_data_str(name)
            case "NoneType":
                return None
            case "dict" | "list":
                # A whole source (a program, the list of the names...)
                return data
            case _:
                _LOGGER.warning(
                    "Not implemented %s: %s (%s)", name, data, type(data).__name__
                )
                return data

    def get_data_kelvin(self, name: str) -> dict[str, float]:
        """Return average kelvin/intensity from linked LEDs."""
        names = name.split(" ")
        kelvin = 0.0
        intensity = 0.0
        count = 0

        for led in self._linked:
            # For kelvin with G1 or G2
            # NOTE: use the coordinator-level property where available, fall back to API attribute.
            is_g1 = bool(getattr(led, "is_g1", bool(getattr(led.my_api, "_g1", False))))
            path = names[0] if is_g1 else names[1]

            k = led.get_data(path + ".kelvin", True)
            i = led.get_data(path + ".intensity", True)

            kelvin += float(k or 0)
            intensity += float(i or 0)
            count += 1

        if count:
            return {"kelvin": kelvin / count, "intensity": intensity / count}

        _LOGGER.warning("coordinator.virtualled.get_data_kelvin no light")
        return {"kelvin": 23000, "intensity": 0}

    def get_data_str(self, name: str) -> str:
        """Return string value from first linked device (best-effort)."""
        if self._linked:
            v = self._linked[0].get_data(name, True)
            return str(v) if v is not None else "Error"
        return "Error"

    def get_data_bool(self, name: str) -> bool:
        """Return True only if all linked devices report True."""
        for led in self._linked:
            if not bool(led.get_data(name, True)):
                return False
        return True

    def get_data_int(self, name: str) -> int:
        """Return average integer value from linked devices."""
        res = 0.0
        count = 0
        for led in self._linked:
            res += float(led.get_data(name, True) or 0)
            count += 1
        return int(res / count) if count else 0

    def get_data_float(self, name: str) -> float:
        """Return average float value from linked devices."""
        res = 0.0
        count = 0
        for led in self._linked:
            _LOGGER.debug("coordinator.get_data_float %s", name)
            res += float(led.get_data(name, True) or 0)
            count += 1
        return res / count if count else 0.0

    def set_data(self, name: str, value: Any) -> None:
        """Broadcast set data to all linked LEDs (resolving G1/G2 path when provided)."""
        names = name.split(" ")
        with group_dispatch():
            for led in self._targets():
                _LOGGER.debug("Setting DATA for virtual led %s", names)
                if len(names) > 1:
                    v_name = names[1].split(".")[-1]
                    is_g1 = bool(
                        getattr(led, "is_g1", bool(getattr(led.my_api, "_g1", False)))
                    )
                    name_to_set = names[0] + "." + v_name if is_g1 else names[1]
                else:
                    name_to_set = name
                led.set_data(name_to_set, value)

    async def push_values(
        self, source: str = "/configuration", method: str = "post"
    ) -> None:
        """Broadcast push to all linked LEDs, once all of them are there."""
        self._check_ready()
        with group_dispatch():
            for led in self._targets():
                await led.push_values(source, method)
        self._notify_members()

    def data_exist(self, name: str) -> bool:
        """Return True if any linked device has the named data."""
        for led in self._linked:
            if led.data_exist(name):
                _LOGGER.debug("data_exists: %s", name)
                return True
        _LOGGER.debug("not data_exists: %s", name)
        return False

    async def press(self, action: str) -> None:
        """Broadcast press to all linked LEDs, once all of them are there."""
        self._check_ready()
        with group_dispatch():
            for led in self._targets():
                await led.press(action)

    async def delete(self, source: str) -> None:
        """Broadcast delete to all linked LEDs, once all of them are there."""
        self._check_ready()
        with group_dispatch():
            for led in self._targets():
                await led.delete(source)

    async def fetch_config(self, config_path: str | None = None) -> None:
        """Fetch config from all linked LEDs."""
        for led in self._linked:
            await led.my_api.fetch_config(config_path)

    async def post_specific(self, source: str) -> None:
        """POST to LED-specific endpoint on all linked LEDs, once all are there."""
        self._check_ready()
        with group_dispatch():
            for led in self._targets():
                await led.post_specific(source)
        self._notify_members()

    async def async_request_refresh(
        self,
        source: str | None = None,
        config: bool = False,
        wait: int = REFRESH_DEVICE_DELAY,
    ) -> None:
        for led in self._linked:
            await led.async_request_refresh(source, config, wait)

    def _settings_lamps(self) -> list[ReefLedCoordinator]:
        """A setting written on the group went to each of its lamps."""
        return list(self._linked)

    @callback
    def expect_settings(self, source: str, enabled: bool) -> None:
        super().expect_settings(source, enabled)
        self.async_update_listeners()

    def library_g2(self) -> bool:
        """A group with a G2 is driven as a G2: it uses the G2 library."""
        return not self.only_g1

    def weather_targets(self) -> list[ReefLedCoordinator]:
        """A weather program goes to each lamp of the group (in service)."""
        return self._targets()

    def library_link(self) -> tuple[ReefBeatCloudCoordinator, str] | None:
        """Library of the first linked lamp bound to a cloud account."""
        for led in self._linked:
            link = getattr(led, "library_link", None)
            res = link() if callable(link) else None
            if res is not None:
                return cast(tuple[ReefBeatCloudCoordinator, str], res)
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Home Assistant device registry metadata for the virtual device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.title)},
            name=self.title,
            manufacturer=DEVICE_MANUFACTURER,
            model=VIRTUAL_LED,
        )

    @property
    def only_g1(self) -> bool:
        """True when all linked lights are G1 (enables per-channel white/blue)."""
        return self._only_g1

    def linked_leds(self) -> list[dict[str, Any]]:
        """Describe the linked LEDs for the card.

        The card lists them (with a link to each device) and writes the
        programs to each of them: it needs their hardware id (the device
        registry identifier), name, model, generation and config entry, and
        its sunrise offset (minutes, staggered sunrise; None for a lamp
        without /offset).
        """
        res: list[dict[str, Any]] = []
        for n, led in enumerate(self._linked):
            is_g1 = bool(getattr(led, "is_g1", bool(getattr(led.my_api, "_g1", False))))
            offset = led.get_data(LED_OFFSET_INTERNAL_NAME, True)
            res.append(
                {
                    "hwid": led.model_id,
                    "name": led.title,
                    "model": led.model,
                    "g2": not is_g1,
                    "offset": int(offset)
                    if isinstance(offset, (int, float)) and not isinstance(offset, bool)
                    else None,
                    "entry_id": self._linked_entries[n]
                    if n < len(self._linked_entries)
                    else None,
                }
            )
        return res


# REEFMAT
class ReefMatCoordinator(ReefBeatCloudLinkedCoordinator):
    """Coordinator for ReefMat devices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the ReefMat coordinator and its API."""
        super().__init__(hass, entry)
        self.my_api = ReefMatAPI(self._ip, self._live_config_update, self._session)

    async def new_roll(self) -> None:
        """Start a new roll on the device."""
        await self.my_api.new_roll()


# REEFDOSE
class ReefDoseCoordinator(ReefBeatCloudLinkedCoordinator):
    """Coordinator for ReefDose devices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the ReefDose coordinator and its API."""
        super().__init__(hass, entry)
        # HW model ends with the number of heads (e.g. "...4")
        self.heads_nb = int(str(entry.data[CONFIG_FLOW_HW_MODEL])[-1])
        self.my_api = ReefDoseAPI(
            self._ip, self._live_config_update, self._session, self.heads_nb
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch fresh data and prefill local editable supplement fields for each head."""
        res = await super()._async_update_data()

        # Prefill once: populate editable fields from current /head/<n>/settings values
        # only when the local fields are empty. This avoids constantly overwriting
        # user edits while still providing sensible defaults.
        local_any = res.setdefault("local", {})
        if not isinstance(local_any, dict):
            return res
        local = cast(dict[str, Any], local_any)

        head_local_any = local.setdefault("head", {})
        if not isinstance(head_local_any, dict):
            return res

        head_local = cast(dict[str, Any], head_local_any)

        for head in range(1, self.heads_nb + 1):
            head_key = str(head)
            head_dict_any = head_local.setdefault(head_key, {})
            if not isinstance(head_dict_any, dict):
                continue
            head_dict = cast(dict[str, Any], head_dict_any)

            # Read current supplement metadata from device settings
            base = (
                "$.sources[?(@.name=='/head/"
                + head_key
                + "/settings')].data.supplement."
            )
            cur_brand = self.get_data(base + "brand_name", True)
            cur_name = self.get_data(base + "name", True)
            cur_short = self.get_data(base + "short_name", True)

            # Only prefill if local editable fields are blank/missing.
            if (
                isinstance(cur_brand, str)
                and cur_brand
                and (head_dict.get("new_supplement_brand_name") in (None, ""))
            ):
                head_dict["new_supplement_brand_name"] = cur_brand
            if (
                isinstance(cur_name, str)
                and cur_name
                and (head_dict.get("new_supplement_name") in (None, ""))
            ):
                head_dict["new_supplement_name"] = cur_name
            if (
                isinstance(cur_short, str)
                and cur_short
                and (head_dict.get("new_supplement_short_name") in (None, ""))
            ):
                head_dict["new_supplement_short_name"] = cur_short

        return res

    async def calibration(self, action: str, head: int, param: Any) -> None:
        """Run a calibration step for the given dosing head."""
        await self.my_api.calibration(action, head, param)

    async def set_bundle(self, param: Any) -> None:
        """Set a dosing bundle/preset (API-defined payload)."""
        await self.my_api.set_bundle(param)

    async def press(self, action: str, head: int | None = None) -> None:  # type: ignore[override]
        """Trigger a dose-specific action (optionally head-scoped)."""
        await self.my_api.press(action, head)

    async def push_values(  # type: ignore[override]
        self,
        source: str = "/configuration",
        method: str = "put",
        head: int | None = None,
    ) -> None:
        """Push changed values to the device (optionally head-scoped)."""
        await self.my_api.push_values(source, method, head)

    @property
    def hw_version(self) -> None:  # type: ignore[override]
        """ReefDose has no meaningful hardware version mapping in current payload."""
        return None

    def head_device_info(self, head_id):
        """Return device info extended with the head identifier (non-mutating)."""
        if head_id <= 0:
            return self.device_info

        base_di = dict(self.device_info)
        base_identifiers = base_di.get("identifiers") or {(DOMAIN, self.serial)}
        domain, ident = next(iter(cast(set[tuple[str, str]], base_identifiers)))

        # DeviceInfo is a TypedDict; copying values from a generic dict makes mypy/pyright
        # widen types to object | None, so we guard and only assign strings (or omit keys).
        di_dict: dict[str, Any] = {
            "identifiers": {(domain, f"{ident}_head_{head_id}")},
            "name": f"{self.title} head {head_id}",
        }

        for key in ("manufacturer", "model", "model_id", "hw_version", "sw_version"):
            val = base_di.get(key)
            if isinstance(val, str) or val is None:
                di_dict[key] = val

        return cast(DeviceInfo, di_dict)


# REEFATO+
class ReefATOCoordinator(ReefBeatCloudLinkedCoordinator):
    """Coordinator for ReefATO+ devices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the ReefATO+ coordinator and its API."""
        super().__init__(hass, entry)
        self.my_api = ReefATOAPI(self._ip, self._live_config_update, self._session)

    async def set_volume_left(self, volume_ml: int) -> None:
        """Set remaining refill/container volume (in ml)."""
        await self.my_api.set_volume_left(volume_ml)

    async def resume(self) -> None:
        """Resume normal ATO operation after pause/alarm (API-defined)."""
        await self.my_api.resume()


# REEFRUN
class ReefRunCoordinator(ReefBeatCloudLinkedCoordinator):
    """Coordinator for ReefRun devices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the ReefRun coordinator and its API."""
        super().__init__(hass, entry)
        self.my_api = ReefRunAPI(self._ip, self._live_config_update, self._session)

    async def set_pump_intensity(self, pump: int, intensity: int) -> None:
        """Update the currently active schedule segment intensity for a pump."""
        _LOGGER.debug("coordinator.ReefRunCoordinator.set_pump_intensity pump=%s", pump)
        if intensity > 0 and intensity < 40:
            _LOGGER.warning(
                "coordinator.ReefRunCoordinator.set_pump_intensity %d value lower than min, setting it to 40",
                intensity,
            )
            intensity = 40
        await self.my_api.fetch_config()

        schedule_path = (
            "$.sources[?(@.name=='/pump/settings')].data.pump_"
            + str(pump)
            + ".schedule"
        )
        schedule = self.my_api.get_data(schedule_path)

        now = datetime.now()
        now_minutes = now.hour * 60 + now.minute

        cur_prog = schedule[0]
        for prog in schedule[1:]:
            if int(prog["st"]) < now_minutes:
                cur_prog = prog
            else:
                break

        cur_prog["ti"] = intensity

        # Persist back to coordinator data and push to device.
        self.set_data(schedule_path, schedule)
        await self.push_values(source="/pump/settings", method="put", pump=pump)
        await self.async_request_refresh()

    async def push_values(  # type: ignore[override]
        self,
        source: str = "/configuration",
        method: str = "put",
        pump: int | None = None,
    ) -> None:
        """Push changed values to the device (optionally pump-scoped)."""
        await self.my_api.push_values(source, method, pump)

    # -- EC calibration workflow ------------------------------------------------

    async def calibration_start(self, point: int = 2) -> None:
        """Start EC sensor calibration (2-point)."""
        await self.my_api.calibration_start(point)

    async def calibration_skim(self) -> None:
        """Run the overskimming calibration step."""
        await self.my_api.calibration_skim()

    async def calibration_cup(self) -> None:
        """Run the full-cup calibration step."""
        await self.my_api.calibration_cup()

    async def calibration_end(self) -> None:
        """Finish and save EC calibration."""
        await self.my_api.calibration_end()

    # -- Pump management -------------------------------------------------------

    async def detect_pump(self, pump: int) -> dict[str, Any] | None:
        """Detect which pump is physically connected to a channel."""
        return await self.my_api.detect_pump(pump)

    @staticmethod
    def default_pump_name(pump_type: str, model: str) -> str:
        """Build the name given to a freshly detected pump.

        The ReefBeat app asks the user for a name; here the model is turned
        into the same kind of label the app proposes, and the user can rename
        the pump afterwards through the `name` text entity.

        Args:
            pump_type: Detected type ("skimmer" or "return").
            model: Detected model (e.g. "rsk-900", "return-12000").

        Returns:
            A human readable pump name.
        """
        if pump_type == "skimmer" and model.startswith("rsk-"):
            return f"DC Skimmer {model[len('rsk-') :]}"
        if pump_type == "return" and model.startswith("return-"):
            return f"ReefRun {model[len('return-') :]}"
        return model

    def _schedule_entry_reload(self) -> None:
        """Reload the config entry so type-dependent entities are rebuilt.

        Which entities a pump owns depends on its type: the model select and
        the skimmer calibration buttons only exist for a skimmer. They are
        created at setup, so a pump added at runtime needs a reload to appear.
        """
        try:
            self.hass.config_entries.async_schedule_reload(self._entry.entry_id)
        except Exception:
            # Best effort: a failed reload must not abort the pump creation
            _LOGGER.debug("Could not schedule a reload after adding a pump")

    async def detect_and_add_pump(self, pump: int) -> dict[str, Any] | None:
        """Detect the pump plugged on a channel and register it in one step.

        A pump that is plugged in but never configured stays "unknown" in
        /dashboard: only a PUT /pump/settings names it. Detection alone
        therefore changes nothing visible, hence this combined action.

        Args:
            pump: Pump number (1 or 2).

        Returns:
            The detection result, or None when nothing usable was detected.
        """
        detection = await self.detect_pump(pump)
        if not detection:
            _LOGGER.warning("No pump detected on channel %d", pump)
            return None

        pump_type = detection.get("type")
        model = detection.get("model")
        if not pump_type or not model or "unknown" in (pump_type, model):
            _LOGGER.warning(
                "Unusable detection for pump %d: %s",
                pump,
                detection,
            )
            return None

        await self.configure_pump(
            pump,
            self.default_pump_name(pump_type, model),
            model,
            pump_type,
        )
        # /pump/settings and /dashboard are "data" sources: fetch_config() alone
        # would not pick up the new pump, the values would stay stale until the
        # next scan interval. The wait lets the device apply the PUT first.
        await self.async_request_refresh(config=True, wait=REFRESH_DEVICE_DELAY)
        self._schedule_entry_reload()
        return detection

    def _pump_field(self, pump: int, field: str) -> Any:
        """Read one /dashboard field of a pump."""
        return self.get_data(
            f"$.sources[?(@.name=='/dashboard')].data.pump_{pump}.{field}"
        )

    async def set_pump_name(self, pump: int, name: str) -> None:
        """Rename a pump.

        The ReefRun has no dedicated rename endpoint: PUT /pump/settings takes
        the whole pump entry, so the current type and model are resent with the
        new name. Renaming an unconfigured pump is refused, as it would write
        "unknown" as both type and model.

        Args:
            pump: Pump number (1 or 2).
            name: New pump name.
        """
        pump_type = self._pump_field(pump, "type")
        model = self._pump_field(pump, "model")
        if not pump_type or not model or "unknown" in (pump_type, model):
            _LOGGER.warning(
                "Cannot rename pump %d: it is not configured yet (type=%s, model=%s)",
                pump,
                pump_type,
                model,
            )
            return

        await self.configure_pump(pump, name, model, pump_type)
        await self.async_request_refresh(config=True, wait=REFRESH_DEVICE_DELAY)

    async def delete_pump(self, pump: int) -> None:
        """Reset a pump channel to factory defaults.

        The slot falls back to type "unknown", which changes both /dashboard
        and the set of entities the pump owns, so refresh and reload.
        """
        await self.my_api.delete_pump(pump)
        # Give the ReefRun time to settle before reading it back: the delete
        # rewrites the whole pump section, /dashboard lags behind it.
        await self.async_request_refresh(config=True, wait=REFRESH_DEVICE_DELAY)
        self._schedule_entry_reload()

    async def configure_pump(
        self, pump: int, name: str, model: str, pump_type: str
    ) -> None:
        """Configure a pump channel after detection or manual setup."""
        await self.my_api.configure_pump(pump, name, model, pump_type)

    def pump_device_info(self, pump_id: int):
        """Return per-pump device info for ReefRun."""
        if pump_id <= 0:
            return self.device_info

        base_di = dict(self.device_info)
        base_identifiers = base_di.get("identifiers") or {(DOMAIN, self.serial)}
        domain, ident = next(iter(cast(set[tuple[str, str]], base_identifiers)))

        di_dict: dict[str, Any] = {
            "identifiers": {(domain, f"{ident}_pump_{pump_id}")},
            "name": f"{self.title} pump {pump_id}",
        }

        for key in ("manufacturer", "model", "model_id", "hw_version", "sw_version"):
            val = base_di.get(key)
            if isinstance(val, str) or val is None:
                di_dict[key] = val

        return cast(DeviceInfo, di_dict)


# REEFWAVE
class ReefWaveCoordinator(ReefBeatCloudLinkedCoordinator):
    """Coordinator for ReefWave devices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the ReefWave coordinator and its API."""
        super().__init__(hass, entry)
        self.my_api = ReefWaveAPI(self._ip, self._live_config_update, self._session)

    async def set_wave(self) -> None:
        """Apply the current preview wave into the active schedule."""
        if self.get_data("$.sources[?(@.name=='/mode')].data.mode") == "preview":
            _LOGGER.debug("Stop preview")
            await self.delete("/preview")
            self.set_data("$.sources[?(@.name=='/mode')].data.mode", "auto")

        cur_schedule = await self._get_current_schedule()
        new_wave = await self._create_new_wave_from_preview(cur_schedule["cur_wave"])

        if self.get_data("$.local.use_cloud_api") is True:
            # For "no wave", prefer the library copy from cloud (aquarium-scoped)
            if self.get_data("$.sources[?(@.name=='/preview')].data.type") == "nw":
                nw = self._cloud_link.get_no_wave(self) if self._cloud_link else None
                if nw is not None:
                    new_wave = nw
                else:
                    _LOGGER.warning(
                        "No 'no wave' available from cloud for %s, using preview wave",
                        self._title,
                    )
            await self._set_wave_cloud_api(cur_schedule, new_wave)
        else:
            await self._set_wave_local_api(cur_schedule, new_wave)

        await self.async_request_refresh()

    async def _create_new_wave_from_preview(
        self, cur_wave: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a wave payload from the current preview settings."""
        return {
            "wave_uid": cur_wave["wave_uid"],
            "type": self.get_data("$.sources[?(@.name=='/preview')].data.type"),
            "name": "ha-" + str(int(time())),
            "direction": self.get_data(
                "$.sources[?(@.name=='/preview')].data.direction"
            ),
            "frt": self.get_data("$.sources[?(@.name=='/preview')].data.frt", True),
            "rrt": self.get_data("$.sources[?(@.name=='/preview')].data.rrt", True),
            "fti": self.get_data("$.sources[?(@.name=='/preview')].data.fti", True),
            "rti": self.get_data("$.sources[?(@.name=='/preview')].data.rti", True),
            "pd": self.get_data("$.sources[?(@.name=='/preview')].data.pd", True),
            "sn": self.get_data("$.sources[?(@.name=='/preview')].data.sn", True),
            "sync": True,
            "st": cur_wave["st"],
        }

    async def _get_current_schedule(self) -> dict[str, Any]:
        """Return the active '/auto' schedule and the currently effective interval."""
        auto = self.get_data("$.sources[?(@.name=='/auto')].data")
        waves = auto["intervals"]

        now = datetime.now()
        now_minutes = now.hour * 60 + now.minute

        cur_wave_idx = 0
        for idx, wave in enumerate(waves):
            if int(wave["st"]) < now_minutes:
                cur_wave_idx = idx
            else:
                break

        return {
            "schedule": auto,
            "cur_wave": waves[cur_wave_idx],
            "cur_wave_idx": cur_wave_idx,
        }

    async def _set_wave_cloud_api(
        self, cur_schedule: dict[str, Any], new_wave: dict[str, Any]
    ) -> None:
        """Update schedule via the ReefBeat cloud API and propagate to devices."""
        if self._cloud_link is None:
            raise TypeError(f"{self._title} - Not linked to cloud account")

        # No Wave: replace by cloud library wave (already has uid fields)
        if new_wave["type"] == "nw":
            new_wave["direction"] = "fw"
            new_wave["wave_uid"] = new_wave["uid"]

            for pos, wave in enumerate(cur_schedule["schedule"]["intervals"]):
                if wave["wave_uid"] == cur_schedule["cur_wave"]["wave_uid"]:
                    _LOGGER.debug(
                        "Replace %s with %s", wave["wave_uid"], new_wave["wave_uid"]
                    )
                    # Use a COPY: the same wave_uid can appear in several
                    # slots (e.g. a "nuit" wave used before AND after
                    # midnight). Assigning the shared new_wave object to
                    # multiple positions would make them alias each other,
                    # and the per-slot start/st below would then clobber
                    # each other (the first slot ends up with the last
                    # slot's start), corrupting the schedule.
                    cur_schedule["schedule"]["intervals"][pos] = dict(new_wave)
                # Keep both keys for compatibility (device expects start in cloud payload)
                cur_schedule["schedule"]["intervals"][pos]["start"] = wave["st"]
                cur_schedule["schedule"]["intervals"][pos]["st"] = wave["st"]

            await self._cloud_link.send_cmd(
                "/reef-wave/schedule/" + self.model_id, cur_schedule["schedule"], "post"
            )
            return

        c_wave = self._cloud_link.get_data(
            "$.sources[?(@.name=='"
            + WAVES_LIBRARY
            + "')].data[?(@.uid=='"
            + new_wave["wave_uid"]
            + "')]",
            True,
        )
        if c_wave is None:
            raise TypeError(f"{self._title} - Current wave not found in cloud library")

        is_cur_wave_default = c_wave.get("default")

        payload: dict[str, Any] = {
            "name": new_wave["name"],
            "type": new_wave["type"],
            "frt": new_wave["frt"],
            "rrt": new_wave["rrt"],
            "pd": new_wave["pd"],
            "sn": new_wave["sn"],
            "default": False,
            "pump_settings": [
                {
                    "hwid": self.model_id,
                    "fti": new_wave["fti"],
                    "rti": new_wave["rti"],
                    "sync": new_wave["sync"],
                }
            ],
        }

        must_create = (
            is_cur_wave_default is True
            or is_cur_wave_default is None
            or new_wave["type"] != c_wave.get("type")
        )

        if must_create:
            payload["aquarium_uid"] = c_wave["aquarium_uid"]
            _LOGGER.debug("POST new wave: %s", payload)

            res = await self._cloud_link.send_cmd("/reef-wave/library", payload, "post")
            _LOGGER.debug("POST new wave response: %s", getattr(res, "text", res))

            # Refresh cloud library then pick the just-created wave uid by name
            await self._cloud_link.fetch_config()
            await self.fetch_config()

            new_uid = self._cloud_link.get_data(
                "$.sources[?(@.name=='"
                + WAVES_LIBRARY
                + "')].data[?(@.name=='"
                + new_wave["name"]
                + "')].uid"
            )

            for pos, wave in enumerate(cur_schedule["schedule"]["intervals"]):
                if wave["wave_uid"] == new_wave["wave_uid"]:
                    _LOGGER.debug("Replace %s with %s", new_wave["wave_uid"], new_uid)
                    # Copy per slot (same wave_uid may occur in several
                    # slots); a shared object would alias and the per-slot
                    # start below would corrupt the earlier slot.
                    replacement = dict(new_wave)
                    replacement["wave_uid"] = new_uid
                    cur_schedule["schedule"]["intervals"][pos] = replacement
                cur_schedule["schedule"]["intervals"][pos]["start"] = wave["st"]
                cur_schedule["schedule"]["intervals"][pos]["st"] = wave["st"]

            _LOGGER.debug("POST new schedule %s", cur_schedule["schedule"])
            await self._cloud_link.send_cmd(
                "/reef-wave/schedule/" + self.model_id, cur_schedule["schedule"], "post"
            )
        else:
            payload["name"] = c_wave["name"]
            _LOGGER.debug("Edit wave %s", new_wave["wave_uid"])
            _LOGGER.debug("Existing: %s -> payload: %s", c_wave, payload)

            res = await self._cloud_link.send_cmd(
                "/reef-wave/library/" + new_wave["wave_uid"], payload, "put"
            )
            _LOGGER.debug("PUT wave response: %s", getattr(res, "text", res))

            for pos, wave in enumerate(cur_schedule["schedule"]["intervals"]):
                if wave["wave_uid"] == new_wave["wave_uid"]:
                    # Copy per slot: the same wave_uid may appear in several
                    # slots; a shared object would alias them and the
                    # per-slot start below would clobber the earlier slot.
                    cur_schedule["schedule"]["intervals"][pos] = dict(new_wave)
                cur_schedule["schedule"]["intervals"][pos]["start"] = wave["st"]
                cur_schedule["schedule"]["intervals"][pos]["st"] = wave["st"]

            _LOGGER.debug("POST new schedule %s", cur_schedule["schedule"])
            # TODO : When rswave are grouped, setting values do not work with standard API
            # Issue URL: https://github.com/Elwinmage/ha-reefbeat-component/issues/62
            # labels: rswave, bug
            await self._cloud_link.send_cmd(
                "/reef-wave/schedule/" + self.model_id, cur_schedule["schedule"], "post"
            )

            await self.fetch_config()

    async def _set_wave_local_api(
        self, cur_schedule: dict[str, Any], new_wave: dict[str, Any]
    ) -> None:
        """Update schedule using the local device API.

        Two fixes baked in here:

        1. Per-slot copy: the same wave_uid can appear in several slots
           (e.g. a "nuit" wave used before AND after midnight). Assigning
           the shared new_wave object to every matching slot would make them
           alias each other and collapse onto a single start time — the slot
           at st=0 would inherit the other slot's st and the device would
           reject the corrupted schedule. We copy per slot and preserve each
           slot's own start time.

        2. One interval at a time: the older ESP8266-based ReefWave firmware
           has a small JSON parse buffer and rejects a single POST /auto
           carrying 3+ intervals ("could not parse the received JSON"), even
           though it stores and runs 5+ intervals fine. Pushing them
           individually keeps each request tiny and the device appends them.
           This also works on newer ESP32 firmware, so it's one code path.
        """
        for pos, wave in enumerate(cur_schedule["schedule"]["intervals"]):
            if wave["wave_uid"] == new_wave["wave_uid"]:
                replacement = dict(new_wave)
                replacement["st"] = wave["st"]
                if "start" in wave:
                    replacement["start"] = wave["st"]
                cur_schedule["schedule"]["intervals"][pos] = replacement

        payload = {"uid": str(uuid.uuid4())}
        await self.my_api.http_send("/auto/init", payload)

        intervals = cur_schedule["schedule"].get("intervals", [])
        for interval in intervals:
            await self.my_api.http_send("/auto", {"intervals": [interval]})

        await self.my_api.http_send("/auto/complete", payload)
        await self.my_api.http_send("/auto/apply", payload)

    # -- Wave library and day program (program editor of the card) ----------

    def wave_link(self) -> tuple[ReefBeatCloudCoordinator, str] | None:
        """Cloud account and aquarium this pump's waves are kept under.

        As in the ReefBeat app, waves live in a per-aquarium library: the
        pump's aquarium is found in the account's device list, by hwid.
        """
        cloud = self._cloud_link
        if cloud is None:
            return None
        aquarium = cloud.get_data(
            "$.sources[?(@.name=='/device')].data[?(@.hwid=='"
            + str(self.model_id)
            + "')].aquarium_uid",
            True,
        )
        if not isinstance(aquarium, str) or not aquarium:
            return None
        return cloud, aquarium

    def _cloud_devices(self, cloud: ReefBeatCloudCoordinator) -> list[dict[str, Any]]:
        """Devices of the cloud account (a single one comes unwrapped)."""
        devices = cloud.get_data("$.sources[?(@.name=='/device')].data", True)
        if isinstance(devices, dict):
            devices = [devices]
        if not isinstance(devices, list):
            return []
        return [d for d in cast(list[Any], devices) if isinstance(d, dict)]

    def _library_entries(
        self, cloud: ReefBeatCloudCoordinator, aquarium: str
    ) -> list[dict[str, Any]]:
        """Raw waves of the aquarium's library."""
        entries = cloud.get_data(
            "$.sources[?(@.name=='" + WAVES_LIBRARY + "')].data", True
        )
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            return []
        return [
            e
            for e in cast(list[Any], entries)
            if isinstance(e, dict) and e.get("aquarium_uid") == aquarium
        ]

    def wave_group(self) -> list[dict[str, Any]]:
        """Pumps sharing this pump's program: its group, or itself alone.

        A ReefWave group of the app is the aquarium's grouped ReefWaves
        (cloud device list), in group order. Each is {hwid, name,
        in_service, coordinator}: the loaded coordinator, None when the pump
        is not loaded in Home Assistant.
        """
        own = {"hwid": self.model_id, "name": self.title, "in_service": True}
        members: list[dict[str, Any]] = []
        link = self.wave_link()
        if link is not None:
            cloud, aquarium = link
            devices = self._cloud_devices(cloud)
            mine = next((d for d in devices if d.get("hwid") == self.model_id), {})
            if mine.get("grouped") is True:
                members = sorted(
                    (
                        d
                        for d in devices
                        if d.get("aquarium_uid") == aquarium
                        and d.get("type") == "reef-wave"
                        and d.get("grouped") is True
                    ),
                    key=lambda d: int(d.get("group_index") or 0),
                )
        if not members:
            members = [own]
        loaded = {
            c.model_id: c
            for c in self._hass.data.get(DOMAIN, {}).values()
            if isinstance(c, ReefWaveCoordinator)
        }
        loaded[self.model_id] = self
        return [
            {
                "hwid": str(m.get("hwid")),
                "name": str(
                    getattr(loaded.get(str(m.get("hwid"))), "title", None)
                    or m.get("name")
                    or m.get("hwid")
                ),
                "in_service": m.get("in_service", True) is not False,
                "coordinator": loaded.get(str(m.get("hwid"))),
            }
            for m in members
        ]

    def linked_waves(self) -> list[dict[str, Any]]:
        """Pumps of this pump's group, for the card's list (empty alone).

        [{hwid, name, model, entry_id, available}], in group order: the card
        shows them and opens the card of the one tapped.
        """
        group = self.wave_group()
        if len(group) < 2:
            return []
        out: list[dict[str, Any]] = []
        for member in group:
            pump = member["coordinator"]
            out.append(
                {
                    "hwid": member["hwid"],
                    "name": member["name"],
                    "model": getattr(pump, "model", None),
                    "entry_id": pump._entry.entry_id if pump is not None else None,
                    "available": pump is not None
                    and bool(getattr(pump, "last_update_success", True)),
                }
            )
        return out

    # -- Grouping (as the ReefBeat app: the aquarium's grouped ReefWaves) ----

    def wave_grouped(self) -> bool | None:
        """Whether this pump is grouped in the app, None without cloud."""
        link = self.wave_link()
        if link is None:
            return None
        mine = next(
            (d for d in self._cloud_devices(link[0]) if d.get("hwid") == self.model_id),
            {},
        )
        return mine.get("grouped") is True

    def _notify_waves(self) -> None:
        """Refresh the entities of every loaded ReefWave (groups changed)."""
        for pump in self._hass.data.get(DOMAIN, {}).values():
            if isinstance(pump, ReefWaveCoordinator):
                pump.async_update_listeners()

    def _manage_entry(
        self, devices: list[dict[str, Any]], hwid: str, grouped: bool, index: int
    ) -> dict[str, Any]:
        """One device of a POST /device/manage, as the app sends it."""
        device = next((d for d in devices if d.get("hwid") == hwid), {})
        return {
            "hwid": hwid,
            "name": device.get("name", ""),
            "in_service": device.get("in_service", True),
            "grouped": grouped,
            "group_index": index,
        }

    async def set_wave_grouped(self, grouped: bool) -> None:
        """Group this pump with the aquarium's other ReefWaves, or ungroup it.

        As the ReefBeat app: POST /device/<hwid>/group or /ungroup. A pump
        joining the group goes last; the order is then written with POST
        /device/manage. The cloud device list is read again and every
        ReefWave refreshed (their group changed).
        """
        cloud, aquarium = self._require_link()
        devices = self._cloud_devices(cloud)
        # The aquarium's group as it stands, in order, this pump left out
        others = [
            str(d.get("hwid"))
            for d in sorted(
                (
                    d
                    for d in devices
                    if d.get("aquarium_uid") == aquarium
                    and d.get("type") == "reef-wave"
                    and d.get("grouped") is True
                    and d.get("hwid") != self.model_id
                ),
                key=lambda d: int(d.get("group_index") or 0),
            )
        ]
        action = "group" if grouped else "ungroup"
        _LOGGER.debug("%s: %s in the ReefBeat cloud", self.title, action)
        await cloud.send_cmd(f"/device/{self.model_id}/{action}", {}, "post")
        if grouped:
            manage = [
                self._manage_entry(devices, hwid, True, index)
                for index, hwid in enumerate([*others, self.model_id])
            ]
            await cloud.send_cmd("/device/manage", manage, "post")
        await cloud.fetch_config("/device")
        self._notify_waves()

    async def set_wave_group_order(self, hwids: Any) -> None:
        """Order the pumps of this pump's group (POST /device/manage)."""
        cloud, _aquarium = self._require_link()
        members = [m["hwid"] for m in self.wave_group()]
        if (
            not isinstance(hwids, list)
            or len(members) < 2
            or sorted(str(h) for h in hwids) != sorted(members)
        ):
            raise group_error("wave_group_bad_order")
        devices = self._cloud_devices(cloud)
        manage = [
            self._manage_entry(devices, str(hwid), True, index)
            for index, hwid in enumerate(hwids)
        ]
        await cloud.send_cmd("/device/manage", manage, "post")
        await cloud.fetch_config("/device")
        self._notify_waves()

    def unavailable_wave_members(self) -> list[str]:
        """Pumps of the group blocking a write, as the ReefBeat app does.

        A pump not loaded or not answering blocks; a pump out of service
        does not.
        """
        names: list[str] = []
        for member in self.wave_group():
            if not member["in_service"]:
                continue
            pump = member["coordinator"]
            if pump is None or not getattr(pump, "last_update_success", True):
                names.append(member["name"])
        return names

    def _check_group_ready(self) -> None:
        """Refuse a write when a pump of the group is missing.

        A group half-written would leave its pumps out of sync: nothing is
        sent, and the user is told which pumps are missing.
        """
        names = self.unavailable_wave_members()
        if names:
            raise group_error(
                "wave_group_member_unavailable",
                group=self.title,
                members=", ".join(names),
            )

    def wave_library(self) -> list[dict[str, Any]] | None:
        """Waves this pump can use, with its own intensities.

        None when the pump is not linked to a cloud account: the program
        editor then only offers the waves of the pump's own program.
        """
        link = self.wave_link()
        if link is None:
            return None
        cloud, aquarium = link
        return [
            library_wave(entry, self.model_id)
            for entry in self._library_entries(cloud, aquarium)
        ]

    def program_intervals(self) -> list[dict[str, Any]]:
        """Intervals of this pump's day program, as last read."""
        intervals = self.get_data(WAVE_SCHEDULE_PATH, True)
        return (
            cast(list[dict[str, Any]], intervals) if isinstance(intervals, list) else []
        )

    def wave_usage(self) -> dict[str, list[str]]:
        """Pumps using each wave, by uid, among the loaded ReefWaves."""
        usage: dict[str, list[str]] = {}
        pumps = [
            c
            for c in self._hass.data.get(DOMAIN, {}).values()
            if isinstance(c, ReefWaveCoordinator)
        ]
        if self not in pumps:
            pumps.append(self)
        for pump in pumps:
            for uid in {
                i.get("wave_uid")
                for i in pump.program_intervals()
                if isinstance(i.get("wave_uid"), str)
            }:
                usage.setdefault(cast(str, uid), []).append(pump.title)
        return usage

    def _require_link(self) -> tuple[ReefBeatCloudCoordinator, str]:
        """The cloud link, or a translated refusal."""
        link = self.wave_link()
        if link is None:
            raise group_error("wave_cloud_required", pump=self.title)
        return link

    @staticmethod
    def _refusal(err: WaveLibraryError) -> HomeAssistantError:
        """A translated error from a refused edit."""
        return group_error(err.key, **err.placeholders)

    async def save_wave(
        self, name: str, settings: dict[str, Any], uid: str | None = None
    ) -> str | None:
        """Add a wave to the aquarium's library, or update one.

        As the ReefBeat app: POST /reef-wave/library to create, PUT
        /reef-wave/library/<uid> to update; a Red Sea (default) wave cannot
        be updated. The shape is shared by every pump; the intensities are
        this pump's, and a new wave gives them to the whole group. Pumps
        using an updated wave get their program written again, so their
        intervals copy its new shape.
        @param uid: the wave to update, None to create one
        @return the uid of the wave
        """
        cloud, aquarium = self._require_link()
        entries = self._library_entries(cloud, aquarium)
        try:
            clean = check_name(name, entries, uid)
            checked = check_settings(settings)
        except WaveLibraryError as err:
            raise self._refusal(err) from err
        group = self.wave_group()
        self._check_group_ready()
        hwids = [m["hwid"] for m in group]
        if uid is None:
            payload = library_payload(
                clean,
                checked["shape"],
                merge_pump_settings([], hwids, checked["pump"]),
                aquarium,
            )
            _LOGGER.debug("POST wave: %s", payload)
            await cloud.send_cmd(WAVES_LIBRARY, payload, "post")
            await cloud.fetch_config(WAVES_LIBRARY)
            for entry in reversed(self._library_entries(cloud, aquarium)):
                if entry.get("name") == clean and entry.get("default") is not True:
                    return cast(str | None, entry.get("uid"))
            return None
        entry = next((e for e in entries if e.get("uid") == uid), None)
        if entry is None:
            raise group_error("wave_not_found", uid=uid)
        if entry.get("default") is True:
            raise group_error("wave_default_readonly", name=str(entry.get("name")))
        existing = entry.get("pump_settings") or []
        # This pump's intensities; a member without any gets the same ones
        have = {s.get("hwid") for s in existing if isinstance(s, dict)}
        targets = [self.model_id] + [h for h in hwids if h not in have]
        payload = library_payload(
            clean,
            checked["shape"],
            merge_pump_settings(existing, targets, checked["pump"]),
        )
        _LOGGER.debug("PUT wave %s: %s", uid, payload)
        await cloud.send_cmd(f"{WAVES_LIBRARY}/{uid}", payload, "put")
        await cloud.fetch_config(WAVES_LIBRARY)
        # Programs copy the wave: write again those that use it
        for member in group:
            pump = member["coordinator"]
            if pump is not None and uses_wave(pump.program_intervals(), uid):
                slots = [
                    {
                        "st": int(i.get("st", 0)),
                        "wave_uid": i.get("wave_uid"),
                        "direction": i.get("direction", "fw"),
                    }
                    for i in pump.program_intervals()
                ]
                await pump._post_program(cloud, aquarium, slots)
        return uid

    async def delete_wave(self, uid: str) -> bool:
        """Delete one of the user's waves from the aquarium's library.

        As the ReefBeat app: DELETE /reef-wave/library/<uid>. A Red Sea wave
        cannot be deleted, nor a wave a loaded pump's program uses.
        """
        cloud, aquarium = self._require_link()
        entry = next(
            (e for e in self._library_entries(cloud, aquarium) if e.get("uid") == uid),
            None,
        )
        if entry is None:
            raise group_error("wave_not_found", uid=uid)
        if entry.get("default") is True:
            raise group_error("wave_default_readonly", name=str(entry.get("name")))
        users = self.wave_usage().get(uid, [])
        if users:
            raise group_error(
                "wave_in_use", name=str(entry.get("name")), pumps=", ".join(users)
            )
        _LOGGER.debug("DELETE wave %s", uid)
        await cloud.send_cmd(f"{WAVES_LIBRARY}/{uid}", {}, "delete")
        await cloud.fetch_config(WAVES_LIBRARY)
        return True

    async def _post_program(
        self,
        cloud: ReefBeatCloudCoordinator,
        aquarium: str,
        slots: list[dict[str, Any]],
    ) -> None:
        """Post this pump's program to the cloud, then read the pump back."""
        waves = {
            str(entry.get("uid")): library_wave(entry, self.model_id)
            for entry in self._library_entries(cloud, aquarium)
        }
        try:
            intervals = schedule_intervals(slots, waves)
        except WaveLibraryError as err:
            raise self._refusal(err) from err
        _LOGGER.debug("POST program of %s: %s", self.title, intervals)
        await cloud.send_cmd(
            "/reef-wave/schedule/" + self.model_id, {"intervals": intervals}, "post"
        )
        await self.fetch_config()

    # -- Preview and per-pump settings of the current wave -------------------

    PREVIEW_PATH = "$.sources[?(@.name=='/preview')].data."

    async def start_preview(
        self, settings: dict[str, Any], direction: str, duration: int
    ) -> None:
        """Run a wave on this pump for a while, as the app's preview.

        The local /preview source is filled with the wave (type, shape,
        intensities, direction) and the duration (ms), then posted to the
        pump, which runs it and goes back to its program afterwards.
        """
        try:
            checked = check_settings(settings)
        except WaveLibraryError as err:
            raise self._refusal(err) from err
        if checked["shape"]["type"] == "nw":
            raise group_error("wave_preview_no_wave")
        if direction not in WAVE_DIRECTIONS:
            raise group_error("wave_program_bad_slot")
        values = {
            **checked["shape"],
            "fti": checked["pump"]["fti"],
            "rti": checked["pump"]["rti"],
            "direction": direction,
            "duration": max(60000, min(600000, int(duration))),
        }
        for key, value in values.items():
            self.set_data(self.PREVIEW_PATH + key, value)
        await self.push_values("/preview", "post")
        await self.async_request_refresh()

    async def stop_preview(self) -> None:
        """Stop a running preview: the pump goes back to its program."""
        await self.delete("/preview")
        await self.async_request_refresh()

    def current_slot(self, intervals: list[dict[str, Any]] | None = None) -> int:
        """Index of the slot of a program running now (-1: none).

        @param intervals: the program (this pump's by default)
        """
        if intervals is None:
            intervals = self.program_intervals()
        if not intervals:
            return -1
        now = datetime.now()
        minute = now.hour * 60 + now.minute
        index = 0
        for pos, interval in enumerate(intervals[1:], start=1):
            if int(interval.get("st", 0)) < minute:
                index = pos
            else:
                break
        return index

    async def set_current_pump(self, direction: str, fti: Any, rti: Any) -> None:
        """Change this pump's direction and intensities in the current wave.

        As in the app, a single pump of a group can run the current wave its
        own way: its intensities go to its own settings of the wave (library,
        even a Red Sea wave: only its pump_settings change), its direction
        to its own program. The other pumps are left as they are.
        """
        if direction not in WAVE_DIRECTIONS:
            raise group_error("wave_program_bad_slot")
        try:
            pump = check_settings({"type": "nw", "fti": fti, "rti": rti})["pump"]
        except WaveLibraryError as err:
            raise self._refusal(err) from err
        own = self.program_intervals()
        index = self.current_slot(own)
        if index < 0:
            raise group_error("wave_program_empty")
        intervals = [dict(i) for i in own]
        current = intervals[index]
        uid = str(current.get("wave_uid", ""))
        link = self.wave_link()
        if link is None:
            current.update(
                {"direction": direction, "fti": pump["fti"], "rti": pump["rti"]}
            )
            await self._write_local(intervals)
            return
        cloud, aquarium = link
        entry = next(
            (e for e in self._library_entries(cloud, aquarium) if e.get("uid") == uid),
            None,
        )
        if entry is None:
            raise group_error("wave_not_found", uid=uid)
        mine = pump_settings_of(entry, self.model_id) or {}
        settings = {**pump, "sync": mine.get("sync", pump["sync"])}
        payload = {
            k: v
            for k, v in entry.items()
            if k not in ("uid", "aquarium_uid", "pump_settings")
        }
        payload["pump_settings"] = merge_pump_settings(
            entry.get("pump_settings") or [], [self.model_id], settings
        )
        _LOGGER.debug("PUT pump settings of %s in wave %s", self.title, uid)
        await cloud.send_cmd(f"{WAVES_LIBRARY}/{uid}", payload, "put")
        await cloud.fetch_config(WAVES_LIBRARY)
        slots = [
            {
                "st": int(i.get("st", 0)),
                "wave_uid": i.get("wave_uid"),
                "direction": direction if pos == index else i.get("direction", "fw"),
            }
            for pos, i in enumerate(intervals)
        ]
        await self._post_program(cloud, aquarium, slots)

    async def _write_local(self, intervals: list[dict[str, Any]]) -> None:
        """Write a program to the pump itself (/auto handshake)."""
        for interval in intervals:
            interval.pop("start", None)
        payload = {"uid": str(uuid.uuid4())}
        await self.my_api.http_send("/auto/init", payload)
        for interval in intervals:
            await self.my_api.http_send("/auto", {"intervals": [interval]})
        await self.my_api.http_send("/auto/complete", payload)
        await self.my_api.http_send("/auto/apply", payload)
        await self.fetch_config()

    async def save_program(self, slots: Any) -> None:
        """Write the day program of this pump (of its group).

        With a cloud account (the usual case), the program goes through the
        cloud, which pushes it to the pump: written locally only, it would be
        overwritten by the cloud at the next reboot. Each pump of the group
        gets the same slots, with its own intensities; a pump of the group
        missing refuses the whole write.

        Without a cloud account, the program is written to the pump itself
        (local /auto handshake), with the waves of its current program.
        """
        try:
            checked = check_slots(slots)
        except WaveLibraryError as err:
            raise self._refusal(err) from err
        link = self.wave_link()
        if link is None:
            waves = {w["uid"]: w for w in program_waves(self.program_intervals())}
            try:
                intervals = schedule_intervals(checked, waves)
            except WaveLibraryError as err:
                raise self._refusal(err) from err
            await self._write_local(intervals)
            return
        cloud, aquarium = link
        group = self.wave_group()
        self._check_group_ready()
        for member in group:
            pump = member["coordinator"]
            if pump is not None and member["in_service"]:
                await pump._post_program(cloud, aquarium, checked)

    def get_current_value(self, value_basename: str, value_name: str) -> Any:
        """Return the current schedule segment value for a named key.

        Returns None when the schedule is absent or empty (e.g. /auto data: {}).
        """
        now = datetime.now()
        now_minutes = now.hour * 60 + now.minute
        schedule = self.my_api.get_data(value_basename)
        # Guard: schedule may be None or empty when the device returns no data yet.
        if not schedule:
            return None
        cur_prog = schedule[0]
        for prog in schedule[1:]:
            if int(prog["st"]) < now_minutes:
                cur_prog = prog
            else:
                break
        return cur_prog.get(value_name)

    def set_current_value(
        self, value_basename: str, value_name: str, value: Any
    ) -> None:
        """Set the current schedule segment value for a named key (in-memory only)."""
        now = datetime.now()
        now_minutes = now.hour * 60 + now.minute

        schedule = self.my_api.get_data(value_basename)
        cur_prog = schedule[0]
        for prog in schedule[1:]:
            if int(prog["st"]) < now_minutes:
                cur_prog = prog
            else:
                break
        cur_prog[value_name] = value


# REEFPOWER
class ReefPowerCoordinator(ReefBeatCloudLinkedCoordinator):
    """Coordinator for ReefControl Power devices (RSPOWER6, RSPOWER8).

    Owns a :class:`ReefPowerAPI` instance and exposes:
    - `socket_count`: number of AC sockets for this model (6 or 8)
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the ReefPower coordinator and its API."""
        super().__init__(hass, entry)

        # Derive socket count from the trailing digits of the hw_model
        # (RSPOWER6 -> 6, RSPOWER8 -> 8). Default to 6 for unknown variants.
        # Resolved before the API is built: it decides how many per-socket
        # schedule endpoints get registered as sources.
        hw_model = str(entry.data.get(CONFIG_FLOW_HW_MODEL, ""))
        try:
            self.socket_count: int = int(hw_model.replace("RSPOWER", "").strip() or "6")
        except (ValueError, TypeError):
            self.socket_count = 6

        self.my_api = ReefPowerAPI(
            self._ip,
            self._live_config_update,
            self._session,
            socket_count=self.socket_count,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch fresh data, then auto-leave setup mode if warranted.

        The hub starts in main mode "setup" with every socket individually
        in socket-mode "setup" too. The ReefBeat app calls `/setup-finish`
        (moving the hub to "auto") as soon as the first socket is configured
        away from "setup". This runs after every refresh rather than being
        tied to a particular write call, so it fires the same way whether a
        socket was configured through this integration or through a raw
        `redsea.request` service call (e.g. from a card) — neither of which
        the device itself distinguishes.
        """
        data = await super()._async_update_data()
        try:
            await self._maybe_finish_setup()
        except Exception:  # never let this check break a refresh
            _LOGGER.debug(
                "%s: auto setup-finish check failed", self._title, exc_info=True
            )
        return data

    async def _maybe_finish_setup(self) -> None:
        if (
            self.get_data(
                "$.sources[?(@.name=='/dashboard')].data.mode", is_None_possible=True
            )
            != "setup"
        ):
            return
        sockets = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.sockets", is_None_possible=True
        )
        if not isinstance(sockets, list):
            return
        if any(isinstance(s, dict) and s.get("mode") != "setup" for s in sockets):
            # Call the API directly (not the setup_finish() wrapper below,
            # which also requests a refresh) — we are already inside one.
            await cast(ReefPowerAPI, self.my_api).setup_finish()

    async def delete_socket(self, number: int) -> None:
        """Uninstall a socket, clearing any sensor binding it had.

        Mirrors the ReefBeat app: ``DELETE /socket/<n>/config`` then
        ``PUT /unsubscribe`` so a binding does not outlive the socket. The
        paired hub keeps its own copy of that subscription and clears it with
        ``PUT /socket/<n>/unsubscribe`` — that call belongs to the hub's
        config entry, so it is not issued from here.
        """
        api = cast(ReefPowerAPI, self.my_api)
        await api.delete_socket(number)
        await api.unsubscribe_sockets([number])
        await self.async_request_refresh(config=True)

    async def set_socket_name(self, number: int, name: str) -> None:
        """Rename a socket and refresh.

        The device always receives ``mode`` and ``name`` together in the
        ``PUT /sockets/config`` body (the app never sends a name on its own),
        so we resend the socket's current user-chosen mode alongside the new
        name. If the current mode isn't one of the writable modes (e.g. the
        socket is still in ``setup``), we fall back to ``off``.
        """
        mode = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.sockets"
            f"[?(@.number=={number})].user_config_mode",
            is_None_possible=True,
        )
        if mode not in ("off", "on", "schedule", "sensor"):
            mode = "off"
        await cast(ReefPowerAPI, self.my_api).set_socket_mode(number, mode, name=name)
        await self.async_request_refresh()

    async def set_socket_schedule(
        self, number: int, intervals: list[dict[str, int]]
    ) -> None:
        """Set a socket's daily schedule and refresh.

        The schedule lives on a config endpoint, so a plain refresh would not
        read it back; and the strip needs a moment before it serves the new
        programme rather than the previous one.
        """
        await cast(ReefPowerAPI, self.my_api).set_socket_schedule(number, intervals)
        await self.async_request_refresh(config=True, wait=SCHEDULE_REFRESH_DELAY)

    async def setup_finish(self) -> None:
        """Leave setup mode (device switches to auto) and refresh."""
        await cast(ReefPowerAPI, self.my_api).setup_finish()
        await self.async_request_refresh()

    async def unpair_control(self) -> None:
        """Unlink the paired RSControl hub and refresh.

        Optimistic: once the power center accepted it, both ends show the
        link gone at once (the hub's side too, when it is set up here); the
        read-back corrects them if the unpairing did not happen.
        """
        hub = self.connected_control()
        result = await cast(ReefPowerAPI, self.my_api).unpair_control()
        if _accepted(result):
            self.async_update_listeners()
            if hub is not None:
                hub.set_connected_device(None)
        await self.async_request_refresh(config=True)

    def connected_control(self) -> ReefControlCoordinator | None:
        """The RSCONTROL hub this power center is paired with, if set up here.

        Matched on the hub's hardware id, as reported by the power center's
        own ``/dashboard.connected_device.hwid``.
        """
        hwid = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.connected_device.hwid",
            is_None_possible=True,
        )
        if not hwid:
            return None
        for coordinator in self._hass.data.get(DOMAIN, {}).values():
            if (
                isinstance(coordinator, ReefControlCoordinator)
                and coordinator.model_id == hwid
            ):
                return coordinator
        return None

    def set_connected_device(self, device: dict[str, Any] | None) -> None:
        """Set the power center's cached pairing and show it (optimistic)."""
        dashboard = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data", is_None_possible=True
        )
        if isinstance(dashboard, dict):
            dashboard["connected_device"] = device
            self.async_update_listeners()

    def socket_sensor_config(self, socket: int) -> tuple[str | None, Any]:
        """Threshold rule driving a socket in sensor mode, and where it lives.

        Returns ``(source, rule)``:

        - ``("local", rule)``: the socket follows the power center's own
          temperature probe; the rule is its ``/temperature/subscriptions``
          entry (``value``, ``is_above``, ``turn_on``, ...).
        - ``("control", rule)``: the socket follows a probe of the paired
          RSCONTROL hub. The power center only keeps the probe type
          (``sensor.app_cache`` in ``/sockets/config``); the hub holds the
          rule under the socket number, in its ``/subscription-info``
          ``external`` list (``type``, ``uid``, ``sensor``, ``is_above``,
          ``value``, ``hysteresis``, ``trigger_op``, ``last_sock_op``).
        - ``(None, None)``: no rule known for this socket.
        """
        local = self.get_data(
            "$.sources[?(@.name=='/temperature/subscriptions')]"
            f".data.sockets[?(@.number=={socket})]",
            is_None_possible=True,
        )
        if local:
            return "local", local

        hub = self.connected_control()
        if hub is None:
            return None, None
        rules = hub.get_data(
            "$.sources[?(@.name=='/subscription-info')].data.external",
            is_None_possible=True,
        )
        if isinstance(rules, list):
            for rule in cast(list[Any], rules):
                if isinstance(rule, dict) and rule.get("number") == socket:
                    return "control", rule
        return None, None

    def has_local_temperature(self) -> bool:
        """Whether a local temperature probe is currently installed."""
        return (
            self.get_data(
                "$.sources[?(@.name=='/dashboard')].data.temperature",
                is_None_possible=True,
            )
            is not None
        )

    async def async_calibrate_temperature(self, reference: float) -> None:
        """Calibrate the local temperature against a reference, refresh."""
        await cast(ReefPowerAPI, self.my_api).calibrate_temperature(reference)
        self.async_update_listeners()
        await self.async_request_refresh(config=True)

    async def async_install_temperature(self) -> None:
        """Install the local temperature probe and refresh.

        Pairing over BLE takes a moment before the device reports the new
        probe, so wait a bit longer before reading it back (see
        PROBE_REFRESH_DELAY).
        """
        await cast(ReefPowerAPI, self.my_api).install_temperature()
        # The API already cached the new probe (optimistic): show it now
        self.async_update_listeners()
        await self.async_request_refresh(wait=PROBE_REFRESH_DELAY)

    async def async_remove_temperature(self) -> None:
        """Remove the local temperature probe and refresh.

        Same settle-time rationale as install: give the device a moment
        before reading /dashboard back (see PROBE_REFRESH_DELAY).
        """
        await cast(ReefPowerAPI, self.my_api).remove_temperature()
        # The API already dropped the probe from the cache (optimistic)
        self.async_update_listeners()
        await self.async_request_refresh(wait=PROBE_REFRESH_DELAY)

    async def get_current_temperature(self) -> None:
        """Read the local temperature now (``GET /temperature``).

        The fresh values are merged into the cached ``/dashboard.temperature``
        and pushed to the entities, without waiting for the next poll.
        """
        if await cast(ReefPowerAPI, self.my_api).get_current_temperature():
            self.async_update_listeners()


# REEFCONTROL
class ReefControlCoordinator(ReefBeatCloudLinkedCoordinator):
    """Coordinator for ReefControl hub devices (RSCONTROLPRO, RSCONTROLLITE).

    Owns a :class:`ReefControlAPI` instance and exposes:
    - `port_count`: number of 12V DC output ports (Lite=1, Pro=2)
    - per-port mode / name / schedule writes, mirroring
      :class:`ReefPowerCoordinator` so both device families behave the same

    Probe calibration write endpoints are not wired up yet.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the ReefControl coordinator and its API."""
        super().__init__(hass, entry)
        self.my_api = ReefControlAPI(self._ip, self._live_config_update, self._session)

        hw_model = str(entry.data.get(CONFIG_FLOW_HW_MODEL, ""))
        # Lite exposes 1 port, Pro exposes 2. Anything else falls back to Pro.
        self.port_count: int = 1 if "LITE" in hw_model.upper() else 2

        # A port's daily programme (``/port/<n>/schedule``) is polled only
        # while the port is in schedule mode: the API registers and drops
        # those sources as the ports' modes change (see
        # ReefControlAPI._reconcile_port_schedule_sources).

        # Local state backing the temperature-fusion config entities. Kept in
        # the API's ``local`` bag so get_data/set_data JSONPaths resolve and the
        # number/select persist across polls without a device round-trip.
        local = self.my_api.data.setdefault("local", {})
        local.setdefault(
            "fusion",
            {"method": fusion.DEFAULT_METHOD, "threshold": fusion.DEFAULT_THRESHOLD},
        )
        # Rolling per-source temperature history (uid -> list[(ts, value)]),
        # used to attribute an incoherence to the probe that drifted most over
        # the last hour. Populated lazily on reads (entities poll every cycle).
        self._temp_history: dict[str, list[tuple[float, float]]] = {}
        self._temp_history_last: float = 0.0
        # uids of probes the user put in maintenance: temporarily excluded from
        # fusion/coherence/anomaly so cleaning one does not raise a false alarm.
        self._probe_maintenance: set[str] = set()

    # -- Temperature fusion -------------------------------------------------
    def _probes(self) -> list[dict[str, Any]]:
        raw = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.probes", is_None_possible=True
        )
        return raw if isinstance(raw, list) else []

    def fusion_method(self) -> str:
        """Selected aggregation method (median/mean/min/max)."""
        val = self.get_data("$.local.fusion.method", is_None_possible=True)
        return val if val in fusion.FUSION_METHODS else fusion.DEFAULT_METHOD

    def fusion_threshold(self) -> float:
        """Coherence threshold in °C."""
        val = self.get_data("$.local.fusion.threshold", is_None_possible=True)
        try:
            return float(val)
        except (TypeError, ValueError):
            return fusion.DEFAULT_THRESHOLD

    # -- Per-probe maintenance ---------------------------------------------
    def probe_in_maintenance(self, uid: str) -> bool:
        return uid in self._probe_maintenance

    def set_probe_maintenance(self, uid: str, on: bool) -> None:
        """Put a probe in/out of maintenance and recompute dependents at once."""
        if on:
            self._probe_maintenance.add(uid)
        else:
            self._probe_maintenance.discard(uid)
        self.async_update_listeners()

    def temperature_maintenance_uids(self) -> list[str]:
        return sorted(self._probe_maintenance)

    def temperature_candidates(self) -> list[dict[str, Any]]:
        """All temperature-capable probes, each tagged with a maintenance flag.

        Used for display and for building the per-probe maintenance switches;
        the calc uses :meth:`_active_candidates`.
        """
        cands = fusion.temperature_candidates(self._probes())
        for c in cands:
            c["maintenance"] = c.get("uid") in self._probe_maintenance
        return cands

    def _active_candidates(self) -> list[dict[str, Any]]:
        """Candidates that participate in the calc (maintenance excluded)."""
        return [c for c in self.temperature_candidates() if not c.get("maintenance")]

    def temperature_sources(self) -> list[dict[str, Any]]:
        """The temperature readings currently usable (available, not in maint.)."""
        return [c for c in self._active_candidates() if c.get("available")]

    def temperature_source_count(self) -> int:
        """Number of temperature-capable probes (maintenance included).

        Entities gate on this so they exist as soon as two probes are present,
        even if one is being serviced.
        """
        return len(self.temperature_candidates())

    def _record_history(self, now: float | None = None) -> float:
        """Append the current readings to the rolling history (idempotent/cycle).

        Called from the read path; entities poll every coordinator cycle, so a
        short debounce keeps one sample per ~20s instead of one per entity.
        Prunes samples older than the window and uids no longer present.
        """
        import time as _time

        now = _time.time() if now is None else now
        if now - self._temp_history_last < 20:
            self._prune_history(now)
            return now
        self._temp_history_last = now
        for src in self.temperature_sources():
            uid = src.get("uid")
            if uid is None:
                continue
            hist = self._temp_history.setdefault(uid, [])
            hist.append((now, float(src["value"])))
        self._prune_history(now)
        return now

    def _prune_history(self, now: float) -> None:
        cutoff = now - fusion.HISTORY_WINDOW_S
        for uid in list(self._temp_history):
            self._temp_history[uid] = [
                (t, v) for (t, v) in self._temp_history[uid] if t >= cutoff
            ]
            if not self._temp_history[uid]:
                del self._temp_history[uid]

    def _anomalies(self, now: float | None = None) -> dict[str, Any]:
        now = self._record_history(now)
        return fusion.detect_anomalies(
            self._active_candidates(),
            self._temp_history,
            self.fusion_threshold(),
            now,
        )

    def fusion_temperature(self) -> float | None:
        """Aggregated temperature over the *healthy* sources only."""
        clean = self._anomalies()["clean"]
        values = [c["value"] for c in clean]
        return fusion.fuse(values, self.fusion_method())

    def temperature_spread(self) -> float | None:
        values = [s["value"] for s in self.temperature_sources()]
        return fusion.spread(values)

    def temperature_incoherent(self) -> bool | None:
        """True when readings disagree beyond threshold (a *problem*).

        None when fewer than two usable (non-maintenance) sources exist.
        """
        if len(self.temperature_sources()) < 2:
            return None
        return self._anomalies()["incoherent"]

    def temperature_anomaly_state(self) -> str:
        """Short provenance string for the anomaly sensor.

        ``ok`` when healthy; ``unknown`` when incoherent but unattributable;
        otherwise the culprit probe name(s).
        """
        result = self._anomalies()
        culprits = result["culprits"]
        if not culprits and not result["incoherent"]:
            return "ok"
        if not culprits:
            return "unknown" if result["incoherent"] else "ok"
        return ", ".join(str(c["name"]) for c in culprits)

    def fusion_attributes(self) -> dict[str, Any]:
        """Rich attributes for the fusion / coherence / anomaly entities."""
        now = self._record_history()
        result = self._anomalies(now)
        sources = self.temperature_candidates()
        for s in sources:
            s_change = fusion.change_over_window(
                self._temp_history.get(s["uid"], []), now
            )
            s["change_1h"] = round(s_change, 3) if s_change is not None else None
        values = [c["value"] for c in result["clean"]]
        return {
            "sources": sources,
            "source_names": [s["name"] for s in sources],
            "count": len(sources),
            "available": sum(
                1 for s in sources if s["available"] and not s["maintenance"]
            ),
            "maintenance_probes": self.temperature_maintenance_uids(),
            "fused": fusion.fuse(values, self.fusion_method()),
            "spread": self.temperature_spread(),
            "incoherent": result["incoherent"],
            "culprits": result["culprits"],
            "unknown_source": result["unknown"],
            "method": self.fusion_method(),
            "threshold": self.fusion_threshold(),
        }

    # -- Probe calibration against a reference (temperature, ORP) ----------
    async def async_calibrate_probe(
        self, ptype: str, uid: str, reference: float
    ) -> None:
        """Calibrate a probe's offset reading against a reference, refresh.

        The reading of a temperature or ORP probe, the embedded temperature
        of a pH, EC or ATO probe (see ReefControlAPI.calibrate_probe).
        """
        await cast(ReefControlAPI, self.my_api).calibrate_probe(ptype, uid, reference)
        self.async_update_listeners()
        await self.async_request_refresh(config=True)

    async def async_probe_calibration(
        self,
        action: str,
        ptype: str,
        uid: str,
        point: str | None = None,
        solution_value: float | None = None,
        rated_temp: float | None = None,
    ) -> dict[str, Any]:
        """Run one step of a pH or EC probe's multi-point calibration.

        See ReefControlAPI.probe_calibration. Leaving calibration reads the
        hub back, so the probe's calibration date (and its reminder) follow.
        """
        result = await cast(ReefControlAPI, self.my_api).probe_calibration(
            action, ptype, uid, point, solution_value, rated_temp
        )
        if action == "exit":
            await self.async_request_refresh(config=True)
        return result

    # -- Calibration reminders follow the hub --------------------------------
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch, then date the calibration reminders from the hub."""
        data = await super()._async_update_data()
        try:
            await self._sync_calibration_maintenance()
        except Exception:  # never let this break a refresh
            _LOGGER.debug(
                "%s: calibration reminder sync failed", self._title, exc_info=True
            )
        return data

    async def _sync_calibration_maintenance(self) -> None:
        """Mark a probe's calibration task done when the hub says it was.

        A probe calibrated from the ReefBeat app (or validated, for ORP)
        carries its date (see ReefControlAPI.calibration_date). The reminder
        moves forward to it, never back: a later press of the task's button
        is kept.
        """
        store = cast(MaintenanceStore | None, getattr(self, "maintenance", None))
        if store is None:
            return
        api = cast(ReefControlAPI, self.my_api)
        for probe in self._probes():
            if not isinstance(probe, dict):
                continue
            ptype = str(probe.get("type", "")).lower()
            uid = probe.get("uid")
            task_key = CALIBRATION_TASKS.get(ptype)
            if task_key is None or not isinstance(uid, str) or not uid:
                continue
            epoch = api.calibration_date(ptype, uid)
            if epoch is None:
                continue
            try:
                sub_id = probe_sub_id(uid)
            except ValueError:
                continue
            await store.async_record_reset(
                self.serial,
                sub_id,
                task_key,
                datetime.fromtimestamp(epoch, tz=timezone.utc),
            )

    # -- Probe add / remove (driven by the options flow) -------------------
    def probe_is_connected(self, ptype: str, uid: str) -> bool:
        """Whether a probe is on the hub's dashboard and not unplugged.

        While unplugged, the hub refuses every per-probe request with a 503,
        so the entities driving those requests are shown unavailable.
        """
        probe = self.my_api.dashboard_probe(ptype, uid)
        return probe is not None and not fusion.is_probe_disconnected(probe)

    async def async_read_probe(self, ptype: str, uid: str) -> None:
        """Read one probe now (``GET /probe``) and push it to the entities.

        The fresh values are written into the cached ``/dashboard.probes``
        entry, so every entity of that probe updates without a full poll.
        """
        if await self.my_api.read_probe(ptype, uid):
            self.async_update_listeners()

    def leak_status(self, uid: str) -> str | None:
        """Where a leak probe's water comes from (see ReefControlAPI)."""
        return self.my_api.leak_status(uid)

    def leak_conductivity(self, uid: str) -> float | None:
        """Conductivity a leak probe measured at its last reading."""
        return self.my_api.leak_conductivity(uid)

    def list_probes(self) -> list[dict[str, str]]:
        """Current probes as ``{type, uid, name}`` (for the delete picker)."""
        probes = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.probes", is_None_possible=True
        )
        out: list[dict[str, str]] = []
        if isinstance(probes, list):
            for p in probes:
                if isinstance(p, dict) and p.get("uid") and p.get("type"):
                    out.append(
                        {
                            "type": str(p["type"]),
                            "uid": str(p["uid"]),
                            "name": str(p.get("name") or p["uid"]),
                        }
                    )
        return out

    async def async_install_probe(self, ptype: str) -> str | None:
        """Scan for and install a probe of ``ptype``; return its uid or None.

        Returns the new probe's uid on success, or None when the hub found
        nothing to pair (so the flow can report it). Refreshes afterwards so the
        new probe (and its entities, after reload) reflect the device state.
        """
        result = await cast(ReefControlAPI, self.my_api).install_probe(ptype)
        payload = result.get("json") if isinstance(result, dict) else None
        uid = payload.get("uid") if isinstance(payload, dict) else None
        success = (
            bool(payload.get("success", bool(uid)))
            if isinstance(payload, dict)
            else False
        )
        await self.async_request_refresh()
        return uid if (success and uid) else None

    async def async_delete_probe(self, ptype: str, uid: str) -> None:
        """Remove a probe from the hub and refresh."""
        await cast(ReefControlAPI, self.my_api).delete_probe(ptype, uid)
        await self.async_request_refresh()

    async def set_probe_buzzer(self, ptype: str, uid: str, on: bool) -> None:
        """Toggle a probe's out-of-range buzzer and refresh its config."""
        await cast(ReefControlAPI, self.my_api).set_probe_buzzer(ptype, uid, on)
        await self.async_request_refresh(config=True)

    async def set_probe_notify(self, ptype: str, uid: str, on: bool) -> None:
        """Toggle a probe's out-of-range notification and refresh its config."""
        await cast(ReefControlAPI, self.my_api).set_probe_notify(ptype, uid, on)
        await self.async_request_refresh(config=True)

    async def set_probe_range(
        self, ptype: str, uid: str, field: str, value: float, *, is_temp: bool = False
    ) -> None:
        """Set one bound of a probe's acceptable/desired range and refresh."""
        await cast(ReefControlAPI, self.my_api).set_probe_range(
            ptype, uid, field, value, is_temp=is_temp
        )
        await self.async_request_refresh(config=True)

    async def set_probe_unit(self, uid: str, unit: str) -> None:
        """Set an EC probe's measurement unit and refresh."""
        await cast(ReefControlAPI, self.my_api).set_probe_unit(uid, unit)
        await self.async_request_refresh(config=True)

    def probe_buzzer(self, ptype: str, uid: str) -> bool | None:
        """Current buzzer state for a probe (from /probe/config or /leak/config)."""
        return cast(ReefControlAPI, self.my_api).get_data(
            cast(ReefControlAPI, self.my_api).buzzer_path(ptype, uid),
            is_None_possible=True,
        )

    def probe_notify(self, ptype: str, uid: str) -> bool | None:
        """Current notification state for a probe."""
        return cast(ReefControlAPI, self.my_api).get_data(
            cast(ReefControlAPI, self.my_api).notify_path(ptype, uid),
            is_None_possible=True,
        )

    async def set_probe_enabled(self, ptype: str, uid: str, on: bool) -> None:
        """Enable/disable a probe's monitoring (write-only; state kept locally)."""
        await cast(ReefControlAPI, self.my_api).set_probe_enabled(ptype, uid, on)

    def port_is_installed(self, number: int) -> bool:
        """Whether a 12V port has been assigned a device type.

        Entities gate their availability on this: an uninstalled port rejects
        every config write with a 503 and answers a toggle with a malformed
        ``HTTP/1.1 ?`` status line, so there is nothing useful to expose.
        """
        return cast(ReefControlAPI, self.my_api).port_is_installed(number)

    async def delete_port(self, number: int) -> None:
        """Uninstall a 12V port and hand the physical button over.

        Mirrors the ReefBeat app: after ``DELETE /port/<n>`` it reassigns
        ``is_btn_assigned`` to a port that is still installed, so the hub's
        button keeps doing something. With no other installed port (or on a
        RSCONTROLLITE) the firmware defaults on its own and we skip it.
        """
        api = cast(ReefControlAPI, self.my_api)
        await api.delete_port(number)
        # The API already reset the port in the cache (optimistic)
        self.async_update_listeners()

        for other in range(self.port_count):
            if other != number and api.port_is_installed(other):
                await api.set_port_button_assigned(other)
                break

        await self.async_request_refresh(config=True)

    async def set_port_name(self, number: int, name: str) -> None:
        """Rename a port and refresh.

        The mode is not passed here: ``ReefControlAPI.set_port_mode`` rebuilds
        the whole entry from the cached ``/ports/config``, so the port keeps
        its current mode. Falling back to the ``/dashboard`` mode (as the
        power center does) would be wrong here, because ``/dashboard`` does
        not carry ``type`` / ``power_on_percent`` / ``is_btn_assigned`` and
        the firmware wants those on every write.
        """
        entry = cast(ReefControlAPI, self.my_api).port_config(number) or {}
        mode = entry.get("mode") or entry.get("user_config_mode") or "off"
        await cast(ReefControlAPI, self.my_api).set_port_mode(
            number, str(mode), name=name
        )
        await self.async_request_refresh()

    def port_mode_attributes(self, number: int) -> dict[str, Any]:
        """What a card needs to edit a 12V port, carried by its mode sensor.

        Mirrors the power-center sockets (``socket_N_mode``), so the same
        editor serves both:

        - ``config``: the whole cached ``/ports/config`` entry — the firmware
          wants every field back on a write, ``power_on_percent`` included;
        - ``schedule``: the port's daily programme;
        - ``sensor_config``: the hub's probe rule for this port, from the
          ``internal`` part of ``/subscription-info`` (one entry per port,
          matched on its number) or else the ``sensor`` field of the port's
          own entry, with ``sensor_source`` set to ``control`` like a socket
          driven by the hub.
        """
        api = self.my_api
        rules = self.get_data(
            "$.sources[?(@.name=='/subscription-info')].data.internal",
            is_None_possible=True,
        )
        rule: dict[str, Any] | None = None
        if isinstance(rules, list):
            for raw in cast(list[Any], rules):
                if not isinstance(raw, dict):
                    continue
                entry = cast(dict[str, Any], raw)
                index = entry.get("number", entry.get("port"))
                if index == number:
                    rule = entry
                    break
        config = api.port_config(number)
        if rule is None and config is not None:
            # `/ports/config` entries carry a `sensor` field too (null on a
            # port that follows no probe). On a probe-driven port the app
            # only keeps `{default_state, app_cache}` there: it counts as a
            # rule only when it names the probe it follows.
            own: Any = config.get("sensor")
            if isinstance(own, dict) and ("uid" in own or "type" in own):
                rule = cast(dict[str, Any], own)
        schedule = self.get_data(
            f"$.sources[?(@.name=='/port/{number}/schedule')].data",
            is_None_possible=True,
        )
        return {
            "config": config,
            "schedule": schedule if isinstance(schedule, dict) else None,
            "sensor_config": rule,
            "sensor_source": "control",
        }

    async def unsubscribe_socket(self, number: int) -> None:
        """Clear the hub's binding of a probe to a power-center socket."""
        await cast(ReefControlAPI, self.my_api).unsubscribe_socket(number)
        await self.async_request_refresh(config=True)

    async def set_port_schedule(
        self, number: int, intervals: list[dict[str, int]]
    ) -> None:
        """Set a port's daily schedule and refresh."""
        await cast(ReefControlAPI, self.my_api).set_port_schedule(number, intervals)
        await self.async_request_refresh()

    async def setup_finish(self) -> None:
        """Leave setup mode (device switches to auto) and refresh."""
        await cast(ReefControlAPI, self.my_api).setup_finish()
        await self.async_request_refresh()

    def set_connected_device(self, device: dict[str, Any] | None) -> None:
        """Set the hub's cached pairing and show it (optimistic update)."""
        dashboard = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data", is_None_possible=True
        )
        if isinstance(dashboard, dict):
            dashboard["connected_device"] = device
            self.async_update_listeners()

    def connected_power(self) -> ReefPowerCoordinator | None:
        """The power center this hub is paired with, if set up here."""
        hwid = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.connected_device.hwid",
            is_None_possible=True,
        )
        if not hwid:
            return None
        for coordinator in self._hass.data.get(DOMAIN, {}).values():
            if (
                isinstance(coordinator, ReefPowerCoordinator)
                and coordinator.model_id == hwid
            ):
                return coordinator
        return None

    def _pairing_candidate(self) -> ReefPowerCoordinator | None:
        """The power center a pairing will link, when it can be told.

        Pairing links whichever power center answers nearby; the guess is
        only made when exactly one set up here is free (neither paired nor
        using a local probe, which excludes a hub).
        """
        free = [
            c
            for c in self._hass.data.get(DOMAIN, {}).values()
            if isinstance(c, ReefPowerCoordinator)
            and not c.get_data(
                "$.sources[?(@.name=='/dashboard')].data.connected_device.hwid",
                is_None_possible=True,
            )
            and not c.has_local_temperature()
        ]
        return free[0] if len(free) == 1 else None

    async def pair_power(self) -> None:
        """Pair with a nearby RSPower center and refresh.

        Optimistic when the power center can be told (see
        _pairing_candidate): both ends show the link at once, the read-back
        corrects them if the pairing did not happen.
        """
        power = self._pairing_candidate()
        result = await cast(ReefControlAPI, self.my_api).power_discover(pair=True)
        if power is not None and _accepted(result):
            self.set_connected_device(
                {
                    "state": "paired_connected",
                    "hwid": power.model_id,
                    "internet_connected": True,
                }
            )
            power.set_connected_device(
                {
                    "type": "control",
                    "hwid": self.model_id,
                    "status": "connected",
                    "internet_connected": True,
                }
            )
        await self.async_request_refresh(config=True)

    async def unpair_power(self) -> None:
        """Unlink the paired RSPower center and refresh.

        Optimistic: both ends show the link gone at once (the API clears the
        hub's side), the read-back corrects them if it did not happen.
        """
        power = self.connected_power()
        result = await cast(ReefControlAPI, self.my_api).power_unpair()
        if _accepted(result):
            self.async_update_listeners()
            if power is not None:
                power.set_connected_device(None)
        await self.async_request_refresh(config=True)


# CLOUD
class ReefBeatCloudCoordinator(ReefBeatCoordinator):
    """Coordinator for a ReefBeat Cloud account.

    This coordinator:
    - connects to the ReefBeat cloud API
    - exposes convenience helpers used by local device coordinators (firmware, wave library)
    - handles link requests from local coordinators via HA bus events
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the cloud coordinator and its API client."""
        super().__init__(hass, entry)
        self.my_api = ReefBeatCloudAPI(
            self._entry.data[CONFIG_FLOW_CLOUD_USERNAME],
            self._entry.data[CONFIG_FLOW_CLOUD_PASSWORD],
            self._entry.data[CONFIG_FLOW_CONFIG_TYPE],
            self._ip,
            self._session,
            self._entry.data[CONFIG_FLOW_DISABLE_SUPPLEMENT],
        )
        self.disable_supplement = self._entry.data[CONFIG_FLOW_DISABLE_SUPPLEMENT]
        # Whether the linked devices were told this account is available: only
        # then is there anything to withdraw on unload.
        self._announced = False
        # Groups of the ReefBeat app already proposed as a virtual LED
        # (discovery unique ids), while they still need one
        self._proposed: set[str] = set()

    async def _async_setup(self) -> None:
        """Connect and fetch initial cloud data; start link request listener."""
        if self._boot:
            self._boot = False
            await self.my_api.connect()
            await self.my_api.get_initial_data()
            self._listen("redsea_ask_for_cloud_link", self._handle_link_requests)
            self._hass.bus.fire("redsea_ask_for_cloud_link_ready", {})
            self._announced = True

    async def async_setup(self) -> None:
        """Public entry-point for one-time initialization."""
        await self._async_setup()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the account, then propose its groups Home Assistant lacks."""
        data = await super()._async_update_data()
        self._propose_groups()
        return data

    # Discovery of the groups of the ReefBeat app
    def app_groups(self) -> dict[tuple[str, str], list[str]]:
        """Groups of LEDs of the account Home Assistant could drive.

        By (aquarium uid, model): the entry ids of the loaded lamps of the
        group, in the app's order.
        """
        known = {
            str(led.model_id): entry_id
            for entry_id, led in self._hass.data.get(DOMAIN, {}).items()
            if isinstance(led, ReefLedCoordinator)
            and not isinstance(led, ReefVirtualLedCoordinator)
        }
        devices = self.get_data("$.sources[?(@.name=='/device')].data", True)
        return cloud_groups(devices, known)

    def _aquarium_name(self, aquarium_uid: str) -> str:
        """Name of an aquarium of the account (its uid when unnamed)."""
        aquarium = ReefVirtualLedCoordinator._cloud_aquarium(self, aquarium_uid)
        name = aquarium.get("name") if aquarium else None
        return str(name) if name else aquarium_uid

    @callback
    def _propose_groups(self) -> None:
        """Propose a virtual LED for each group of the app none drives yet.

        A group none of whose lamps is already in a virtual LED (of any
        config entry, loaded or not) is proposed once, as a discovered
        device; once a virtual LED takes it, it can be proposed again if
        that virtual LED goes away. An ignored proposal stays ignored (the
        flow aborts on its unique id).
        """
        taken = {
            str(member)
            for entry in self._hass.config_entries.async_entries(DOMAIN)
            for member in entry.data.get(CONF_GROUP_MEMBERS, []) or []
        }
        wanted: set[str] = set()
        for (aquarium_uid, model), members in self.app_groups().items():
            if taken.intersection(members):
                continue
            key = discovery_unique_id(aquarium_uid, model)
            wanted.add(key)
            if key in self._proposed:
                continue
            _LOGGER.info(
                "Group of %s %s found in the ReefBeat app: proposing a virtual LED",
                len(members),
                model,
            )
            self._hass.async_create_task(
                self._hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_INTEGRATION_DISCOVERY},
                    data={
                        "aquarium_uid": aquarium_uid,
                        "aquarium": self._aquarium_name(aquarium_uid),
                        "model": model,
                        CONF_GROUP_MEMBERS: members,
                    },
                )
            )
        self._proposed = wanted

    # Wave library helpers
    def get_no_wave(self, device: Any) -> dict[str, Any] | None:
        """Return the 'no wave' preset for the aquarium associated with `device`."""
        aquarium_uid = self.get_data(
            "$.sources[?(@.name=='/device')].data[?(@.hwid=='"
            + device.model_id
            + "')].aquarium_uid",
            True,
        )
        query = parse(
            "$.sources[?(@.name=='/reef-wave/library')].data[?(@.type=='nw')]"
        )
        res = query.find(self.my_api.data)
        for nw in res:
            if nw.value.get("aquarium_uid") == aquarium_uid:
                return nw.value
        return None

    # Local device linking
    async def _handle_link_requests(self, event: Any) -> None:
        """Handle requests from local coordinators to link to this cloud account."""
        device_id = event.data.get("device_id")
        if not device_id:
            return

        device = self._hass.data[DOMAIN][device_id]
        s_device = self.get_data(
            "$.sources[?(@.name=='/device')].data[?(@.hwid=='"
            + device.model_id
            + "')]",
            True,
        )
        if s_device is not None:
            await device.set_cloud_link(self)

    async def send_cmd(self, action: str, payload: Any, method: str = "post") -> Any:
        """Send an HTTP command through the cloud API client."""
        return await self.my_api.http_send(action, payload, method)

    def unload(self) -> None:
        """Withdraw this cloud account from the linked devices, then release.

        After a failed setup the account was never announced: firing "off"
        would only make every local device ask for a link again, on each
        ConfigEntryNotReady retry.
        """
        if self._announced:
            self._announced = False
            self._hass.bus.fire(
                "redsea_ask_for_cloud_link_ready",
                {"state": "off", "account": self._title},
            )
        super().unload()

    # Firmware helpers
    async def listen_for_firmware(self, url: str | None, device_name: str) -> None:
        """Ensure the cloud API payload contains the latest firmware endpoint and refresh it."""
        if not url:
            _LOGGER.debug("No firmware URL to listen for (%s)", device_name)
            return

        _LOGGER.debug("Listen for %s", url)
        self.my_api.data["sources"].insert(
            len(self.my_api.data["sources"]),
            {"name": url, "type": "data", "data": ""},
        )
        await self.my_api.fetch_data()
        self._hass.bus.fire("request_latest_firmware", {"device_name": device_name})

    # Cloud coordinator identity / device registry
    @property
    def title(self) -> str:
        """Human-readable name for this cloud account entry."""
        return self._entry.title

    @property
    def serial(self) -> str:
        """Stable unique portion used by entities for unique IDs."""
        return self._entry.title

    @property
    def model(self) -> str:
        """Device model shown in the device registry."""
        return "ReefBeat"

    @property
    def model_id(self) -> str:
        """Model identifier used as the device registry identifier suffix."""
        return "ReefBeat"

    @property
    def detected_id(self) -> str:
        """Debug-friendly identifier for this coordinator/account."""
        return self._entry.title

    @property
    def device_info(self) -> DeviceInfo:
        """Home Assistant device registry metadata for the cloud account."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.title)},
            model=self.model,
            name=self.title,
            manufacturer=DEVICE_MANUFACTURER,
        )

    def aquarium_device_info(self, aquarium_name: str | None):
        """Return per-pump device info for ReefRun."""
        if aquarium_name is None:
            return self.device_info

        base_di = dict(self.device_info)
        base_identifiers = base_di.get("identifiers") or {(DOMAIN, self.serial)}
        domain, ident = next(iter(cast(set[tuple[str, str]], base_identifiers)))

        di_dict: dict[str, Any] = {
            "identifiers": {(domain, f"{ident}_{aquarium_name}")},
            "name": f"{aquarium_name}",
        }

        for key in ("manufacturer", "model", "model_id", "hw_version", "sw_version"):
            val = base_di.get(key)
            if isinstance(val, str) or val is None:
                di_dict[key] = val

        return cast(DeviceInfo, di_dict)
