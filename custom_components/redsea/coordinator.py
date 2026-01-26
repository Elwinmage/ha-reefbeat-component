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
from datetime import datetime, timedelta
from time import time
from typing import Any, cast

import async_timeout
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
    HW_DOSE_IDS,
    HW_G2_LED_IDS,
    HW_LED_IDS,
    HW_MAT_IDS,
    HW_RUN_IDS,
    HW_WAVE_IDS,
    LED_BLUE_INTERNAL_NAME,
    LED_WHITE_INTERNAL_NAME,
    LINKED_LED,
    REFRESH_DEVICE_DELAY,
    SCAN_INTERVAL,
    VIRTUAL_LED,
    WAVES_LIBRARY,
)
from .reefbeat import (
    ReefATOAPI,
    ReefBeatAPI,
    ReefBeatCloudAPI,
    ReefDoseAPI,
    ReefLedAPI,
    ReefMatAPI,
    ReefRunAPI,
    ReefWaveAPI,
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
            # cancel the update (CancelledError) and async_timeout will surface it as a
            # TimeoutError (exactly what we saw in logs). Compute an upper bound that
            # matches the API behavior.
            per_try_timeout = int(getattr(self.my_api, "_timeout", 10))
            overall_timeout = (
                (per_try_timeout + HTTP_DELAY_BETWEEN_RETRY) * HTTP_MAX_RETRY
            ) + 5  # small buffer
            async with async_timeout.timeout(overall_timeout):
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
        self, source: str = None, config: bool = False, wait: int = REFRESH_DEVICE_DELAY
    ) -> None:
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

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        """Read a value from the cached API payload (JSONPath supported by the API layer)."""
        return self.my_api.get_data(name, is_None_possible)

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
        return None


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
        _LOGGER.error("unknown model: %s", model)
        return None

    async def set_cloud_link(self, cloud: ReefBeatCloudCoordinator) -> None:
        """Attach a cloud coordinator and register firmware endpoint subscription."""
        _LOGGER.info("%s linked to cloud %s" % (self._title, cloud._title))
        self._cloud_link = cloud
        model_type = self.get_model_type(self.model)
        if model_type is None:
            self.latest_firmware_url = None
        else:
            self.latest_firmware_url = f"/firmware/api/{model_type}/latest?board={self.board}&framework={self.framework}"
        await cloud.listen_for_firmware(self.latest_firmware_url, self._title)

    @property
    def cloud_coordinator(self) -> "ReefBeatCloudCoordinator | None":
        """Return the linked cloud coordinator (if any)."""
        return self._cloud_link

    def cloud_link(self) -> str:
        """Return linked cloud account name, or 'None'."""
        return self._cloud_link.title if self._cloud_link is not None else "None"


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
        pass

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
        return None

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

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        """Get aggregated value from linked LEDs.

        Behavior:
        - Kelvin/intensity paths may be provided as "g1_path g2_path"
        - For scalar types, values are averaged or AND'ed where appropriate
        """
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
        self, source: str = None, config: bool = False, wait: int = REFRESH_DEVICE_DELAY
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
            raise TypeError("%s - Not linked to cloud account" % self._title)

        # No Wave: replace by cloud library wave (already has uid fields)
        if new_wave["type"] == "nw":
            new_wave["direction"] = "fw"
            new_wave["wave_uid"] = new_wave["uid"]

            for pos, wave in enumerate(cur_schedule["schedule"]["intervals"]):
                if wave["wave_uid"] == cur_schedule["cur_wave"]["wave_uid"]:
                    _LOGGER.debug(
                        "Replace %s with %s", wave["wave_uid"], new_wave["wave_uid"]
                    )
                    cur_schedule["schedule"]["intervals"][pos] = new_wave
                # Keep both keys for compatibility (device expects start in cloud payload)
                cur_schedule["schedule"]["intervals"][pos]["start"] = wave["st"]

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
                    cur_schedule["schedule"]["intervals"][pos] = new_wave
                    cur_schedule["schedule"]["intervals"][pos]["wave_uid"] = new_uid
                cur_schedule["schedule"]["intervals"][pos]["start"] = wave["st"]

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
            await self.fetch_config()

    async def _set_wave_local_api(
        self, cur_schedule: dict[str, Any], new_wave: dict[str, Any]
    ) -> None:
        """Update schedule using the local device API."""
        for pos, wave in enumerate(cur_schedule["schedule"]["intervals"]):
            if wave["wave_uid"] == new_wave["wave_uid"]:
                cur_schedule["schedule"]["intervals"][pos] = new_wave

        payload = {"uid": str(uuid.uuid4())}
        await self.my_api.http_send("/auto/init", payload)

        auto_copy = cur_schedule["schedule"].copy()
        auto_copy.pop("uid", None)

        await self.my_api.http_send("/auto", auto_copy)
        await self.my_api.http_send("/auto/complete", payload)
        await self.my_api.http_send("/auto/apply", payload)

    def get_current_value(self, value_basename: str, value_name: str) -> Any:
        """Return the current schedule segment value for a named key."""
        now = datetime.now()
        now_minutes = now.hour * 60 + now.minute
        schedule = self.my_api.get_data(value_basename)
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
