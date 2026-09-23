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
from datetime import datetime, timedelta
from time import time
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
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
    LED_WHITE_INTERNAL_NAME,
    LINKED_LED,
    PROBE_REFRESH_DELAY,
    REFRESH_DEVICE_DELAY,
    SCAN_INTERVAL,
    SCHEDULE_REFRESH_DELAY,
    VIRTUAL_LED,
    WAVES_LIBRARY,
)
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

_LOGGER = logging.getLogger(__name__)


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

    def unload(self) -> None:
        """Hook for teardown if needed."""
        return


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

        self._hass.bus.async_listen(
            EVENT_HOMEASSISTANT_STARTED, self._handle_ask_for_link
        )

    async def _async_setup(self) -> None:
        """Perform one-time initialization and request cloud link if needed."""
        _LOGGER.debug("%s async_setup...", self._title)
        if self._boot:
            self._boot = False
            await self.my_api.get_initial_data()

            if str(self._hass.state) == "RUNNING":
                self._ask_for_link()

            self._hass.bus.async_listen(
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
        _LOGGER.info(
            "%s intensity compensation: %s", self._title, intensity_compensation
        )

    def force_status_update(self, state: bool = False) -> None:
        """Ask the API to force a light status recalculation."""
        self.my_api.force_status_update(state)

    def set_data(self, name: str, value: Any) -> None:
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
        """POST to a LED-specific endpoint."""
        await self.my_api.post_specific(source)

    @property
    def is_g1(self) -> bool:
        """Return True if the underlying LED API is using G1 protocol."""
        return bool(getattr(self.my_api, "_g1", False))


class ReefLedG2Coordinator(ReefLedCoordinator):
    """Coordinator for ReefLED G2 devices (uses G2 write semantics)."""

    def set_data(self, name: str, value: Any) -> None:
        """Write directly via API without G1-derived field updates."""
        self.my_api.set_data(name, value)


# Virtual LED
class ReefVirtualLedCoordinator(ReefLedCoordinator):
    """Virtual LED that aggregates multiple physical ReefLEDs into one entity.

    The virtual LED can represent an aquarium with multiple ReefLED devices.
    Read operations are aggregated; write operations are broadcast to all linked LEDs.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the virtual LED and discover linked devices."""
        self._linked: list[Any] = []
        self._only_g1: bool = True
        if LINKED_LED not in entry.data:
            _LOGGER.error(
                "You have no LED setup, please add at minimum two real LEDs before configuring a virtual LED "
            )
            super().__init__(hass, entry)
            return

        for led in entry.data.get(LINKED_LED, {}):
            if str(led).split("-")[1] in HW_G2_LED_IDS:
                _LOGGER.debug("G2 light detected")
                self._only_g1 = False
                break

        super().__init__(hass, entry)

        if str(self._hass.state) == "RUNNING":
            self._link_leds()
        else:
            self._hass.bus.async_listen(EVENT_HOMEASSISTANT_STARTED, self._link_leds)

    async def async_setup(self) -> None:
        """Public entry-point for one-time initialization."""

    @callback
    def _link_leds(self, event: Any | None = None) -> None:
        """Resolve linked LED coordinators from entry data."""
        if LINKED_LED not in self._entry.data:
            _LOGGER.error("%s has no led linked, please configure them", self._title)
            return

        _LOGGER.info("Linking leds to %s", self._title)
        self._linked = []
        for led in self._entry.data[LINKED_LED]:
            name = str(led).split(" ")[1]
            entry_id = str(led).split("(")[1][:-1]
            self._linked.append(self._hass.data[DOMAIN][entry_id])
            _LOGGER.info(" - %s", name)

        if len(self._linked) == 0:
            _LOGGER.error("%s has no led linked, please configure them", self._title)
        elif len(self._linked) == 1:
            _LOGGER.error(
                "%s has only one led linked (%s), please configure one more",
                self._title,
                getattr(
                    self._linked[0],
                    "title",
                    getattr(self._linked[0], "_title", "unknown"),
                ),
            )

    def force_status_update(self, state: bool = False) -> None:
        """Virtual device does not force status on a single hardware light."""
        return

    async def _async_update_data(self) -> dict[str, Any]:
        """Aggregate data updates from all linked LED coordinators."""
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
        return data

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
            case "dict":
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
        for led in self._linked:
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
        """Broadcast push to all linked LEDs."""
        for led in self._linked:
            await led.push_values(source, method)

    def data_exist(self, name: str) -> bool:
        """Return True if any linked device has the named data."""
        for led in self._linked:
            if led.data_exist(name):
                _LOGGER.debug("data_exists: %s", name)
                return True
        _LOGGER.debug("not data_exists: %s", name)
        return False

    async def press(self, action: str) -> None:
        """Broadcast press to all linked LEDs."""
        for led in self._linked:
            await led.press(action)

    async def delete(self, source: str) -> None:
        """Broadcast delete to all linked LEDs."""
        for led in self._linked:
            await led.delete(source)

    async def fetch_config(self, config_path: str | None = None) -> None:
        """Fetch config from all linked LEDs."""
        for led in self._linked:
            await led.my_api.fetch_config(config_path)

    async def post_specific(self, source: str) -> None:
        """POST to LED-specific endpoint on all linked LEDs."""
        for led in self._linked:
            await led.post_specific(source)

    async def async_request_refresh(
        self,
        source: str | None = None,
        config: bool = False,
        wait: int = REFRESH_DEVICE_DELAY,
    ) -> None:
        for led in self._linked:
            await led.async_request_refresh(source, config, wait)

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
        """Unlink the paired RSControl hub and refresh."""
        await cast(ReefPowerAPI, self.my_api).unpair_control()
        await self.async_request_refresh(config=True)

    def has_local_temperature(self) -> bool:
        """Whether a local temperature probe is currently installed."""
        return (
            self.get_data(
                "$.sources[?(@.name=='/dashboard')].data.temperature",
                is_None_possible=True,
            )
            is not None
        )

    def temperature_offset(self) -> float | None:
        """Cached local-temperature calibration offset."""
        return cast(ReefPowerAPI, self.my_api).temperature_offset()

    async def set_temperature_offset(self, offset: float) -> None:
        """Set the local temperature offset and refresh so it reflects back."""
        await cast(ReefPowerAPI, self.my_api).set_temperature_offset(offset)
        await self.async_request_refresh(config=True)

    async def reset_temperature_offset(self) -> None:
        """Clear the local temperature offset and refresh."""
        await cast(ReefPowerAPI, self.my_api).reset_temperature_offset()
        await self.async_request_refresh(config=True)

    async def async_install_temperature(self) -> None:
        """Install the local temperature probe and refresh.

        Pairing over BLE takes a moment before the device reports the new
        probe, so wait a bit longer before reading it back (see
        PROBE_REFRESH_DELAY).
        """
        await cast(ReefPowerAPI, self.my_api).install_temperature()
        await self.async_request_refresh(wait=PROBE_REFRESH_DELAY)

    async def async_remove_temperature(self) -> None:
        """Remove the local temperature probe and refresh.

        Same settle-time rationale as install: give the device a moment
        before reading /dashboard back (see PROBE_REFRESH_DELAY).
        """
        await cast(ReefPowerAPI, self.my_api).remove_temperature()
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

    # -- Temperature probe calibration offset ------------------------------
    def probe_offset(self, uid: str) -> float | None:
        """Cached calibration offset for a temperature probe."""
        return cast(ReefControlAPI, self.my_api).probe_offset(uid)

    async def set_probe_offset(self, uid: str, offset: float) -> None:
        """Set a temperature probe's offset and refresh so it reflects back."""
        await cast(ReefControlAPI, self.my_api).set_probe_offset(uid, offset)
        await self.async_request_refresh(config=True)

    async def reset_probe_offset(self, uid: str) -> None:
        """Clear a temperature probe's offset and refresh."""
        await cast(ReefControlAPI, self.my_api).reset_probe_offset(uid)
        await self.async_request_refresh(config=True)

    # -- Probe add / remove (driven by the options flow) -------------------
    async def async_read_probe(self, ptype: str, uid: str) -> None:
        """Read one probe now (``GET /probe``) and push it to the entities.

        The fresh values are written into the cached ``/dashboard.probes``
        entry, so every entity of that probe updates without a full poll.
        """
        if await self.my_api.read_probe(ptype, uid):
            self.async_update_listeners()

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

    async def pair_power(self) -> None:
        """Pair with a nearby RSPower center and refresh."""
        await cast(ReefControlAPI, self.my_api).power_discover(pair=True)
        await self.async_request_refresh(config=True)

    async def unpair_power(self) -> None:
        """Unlink the paired RSPower center and refresh."""
        await cast(ReefControlAPI, self.my_api).power_unpair()
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

    async def _async_setup(self) -> None:
        """Connect and fetch initial cloud data; start link request listener."""
        if self._boot:
            self._boot = False
            await self.my_api.connect()
            await self.my_api.get_initial_data()
            self._hass.bus.async_listen(
                "redsea_ask_for_cloud_link", self._handle_link_requests
            )
            self._hass.bus.fire("redsea_ask_for_cloud_link_ready", {})

    async def async_setup(self) -> None:
        """Public entry-point for one-time initialization."""
        await self._async_setup()

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
        """Notify listeners that this cloud account coordinator is shutting down."""
        self._hass.bus.fire(
            "redsea_ask_for_cloud_link_ready",
            {"state": "off", "account": self._title},
        )

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
