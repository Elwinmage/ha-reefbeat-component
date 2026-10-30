"""The running Poseidon: relay, keystore and the devices it manages.

One instance per Poseidon config entry, kept in
``hass.data[DATA_POSEIDON]``. It never switches a device *to* Poseidon mode
on its own: only the user does, from the switch or the options flow. The
only automatic switch goes back to normal mode, for every device at once,
when the entry is disabled or removed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from ..const import CONFIG_FLOW_CLOUD_USERNAME, DOMAIN, VIRTUAL_LED
from ..reefbeat.api import add_http_observer, http_origin
from . import const
from .anomalies import AnomalyMonitor, check_frame
from .capture import CaptureReport, SnapshotStore, acquire_keys
from .crypto import decrypt_payload
from .debug import DebugLog, frame_record, http_record, mark_record
from .device_http import ORIGIN, DeviceHttp
from .keystore import DeviceKeys, KeyStore
from .mqtt import PACKET_PUBLISH, MqttFrame
from .relay import UP, Relay, Traffic
from .strategy import (
    TELEMETRY_MERGERS,
    Comparisons,
    PollControl,
    fully_pushed,
    is_state_topic,
    is_telemetry_topic,
    merge_state,
    merge_telemetry,
)
from .watchdog import WATCHDOG_USERNAME, WatchdogSession

_LOGGER = logging.getLogger(__name__)

# Statuses of a device in the "add devices" menu
STATUS_UNREACHABLE = "unreachable"
STATUS_NO_CLOUD = "no_cloud_credentials"
STATUS_NOT_IN_ACCOUNT = "not_in_account"
STATUS_POSEIDON = "poseidon"
STATUS_KEYS_OK = "keys_ok"
STATUS_KEYS_NEEDED = "keys_needed"
SELECTABLE = frozenset({STATUS_KEYS_OK, STATUS_KEYS_NEEDED})

# Throttle of the update signal on relayed traffic
TRAFFIC_SIGNAL_S = 5.0


def is_poseidon_entry(entry: ConfigEntry) -> bool:
    """Whether a config entry of the integration is the Poseidon one."""
    return bool(entry.data.get(const.CONF_POSEIDON))


def broker_of(cloud: dict[str, Any] | None) -> str:
    """Broker a /cloud payload points at, normalised ("" when unknown)."""
    if not isinstance(cloud, dict):
        return ""
    url = str(cloud.get("url") or "").strip().lower()
    return url.split("://", 1)[-1].rstrip("/")


def get_poseidon(hass: HomeAssistant) -> Poseidon | None:
    """The running Poseidon, if any."""
    return cast(Poseidon | None, hass.data.get(const.DATA_POSEIDON))


def _belongs_to(device: dr.DeviceEntry, entry_id: str) -> bool:
    """Whether a registry device belongs to a config entry.

    Home Assistant 2026.10 gives a device a single config entry
    (``config_entry_id``) and deprecates the ``config_entries`` set, which
    stops working in 2027.10. Older versions only have the set.
    """
    owner = getattr(device, "config_entry_id", None)
    if owner is not None:
        return owner == entry_id
    return entry_id in (getattr(device, "config_entries", None) or set())


class Poseidon:
    """Relay, keys and switches of the Poseidon entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.port = int(entry.data[const.CONF_PORT])
        self.host = str(entry.data[const.CONF_HOST])
        self.cloud_entry_id = str(entry.data.get(const.CONF_CLOUD_ACCOUNT) or "")
        self.keystore = KeyStore(hass)
        self.snapshots = SnapshotStore(
            hass, Path(hass.config.path(const.FILES_DIR, "snapshots"))
        )
        self.relay = Relay(
            self.port,
            on_connect=self._on_connect,
            on_traffic=self._on_traffic,
            on_frame=self._on_frame,
        )
        self.relay.local_handlers[WATCHDOG_USERNAME] = WatchdogSession(
            lambda: self.watchdog_key, self.is_alive
        )
        logs = Path(hass.config.path(const.FILES_DIR, "logs"))
        self.debug_log = DebugLog(logs)
        # Strategies (see strategy.py): one file each, created on first write
        self.spy_log = DebugLog(logs, const.SPY_FILE)
        self.shadow_log = DebugLog(logs, const.SHADOW_FILE)
        # Messages nothing expected (anomalies.py)
        self.anomaly_log = DebugLog(logs, const.ANOMALY_FILE)
        self.anomalies = AnomalyMonitor(
            hass, self.anomaly_log.write, lambda: self.anomaly_search
        )
        self.comparisons = Comparisons()
        self.poll_control = PollControl()
        # Strategy of each device in Poseidon mode, as last applied
        self.active: dict[str, str] = {}
        # Devices in spy mode whose polling is paused (not kept on restart:
        # a restart always gives the polling back)
        self.paused: set[str] = set()
        # Spy mode: device address -> hwid, for the HTTP requests
        self._spy_hosts: dict[str, str] = {}
        # Spy mode: last answer written per request, not repeated (debug.py)
        self._http_seen: dict[tuple[str, str, str], str] = {}
        self._unsub_http: Callable[[], None] | None = None
        # Coordinator listeners of the comparisons, per device
        self._poll_unsubs: dict[str, Callable[[], None]] = {}
        # Devices whose listeners are called for a merge, not a poll
        self._merging: set[str] = set()
        # Last refresh asked by a pushed state, per device (monotonic)
        self._push_refresh: dict[str, float] = {}
        # Last read of /cloud, per device (monotonic)
        self._cloud_read: dict[str, float] = {}
        # A device is not silent before the relay had the time to see it
        self._started_at = dt_util.utcnow()
        self._unsub_refresh: Callable[[], None] | None = None
        self._last_signal = 0.0
        # Platform callbacks of the per-device entities, and the devices that
        # have them, per platform
        self._adders: dict[str, Callable[[dict[str, dr.DeviceEntry]], None]] = {}
        self._added: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def advertised_url(self) -> str:
        """What a device in Poseidon mode has as /cloud url."""
        return f"{self.host}:{self.port}"

    async def async_load(self) -> None:
        await self.keystore.async_load()

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    @property
    def debug(self) -> bool:
        return bool(self.entry.options.get(const.CONF_DEBUG, False))

    @property
    def anomaly_detection(self) -> bool:
        """Messages nothing expected are logged and reported."""
        return bool(
            self.entry.options.get(const.CONF_ANOMALIES, const.DEFAULT_ANOMALIES)
        )

    @property
    def anomaly_search(self) -> bool:
        """The reports of an anomaly are looked for on GitHub."""
        return self.anomaly_detection and bool(
            self.entry.options.get(
                const.CONF_ANOMALY_SEARCH, const.DEFAULT_ANOMALY_SEARCH
            )
        )

    @property
    def silent_minutes(self) -> int:
        return int(
            self.entry.options.get(
                const.CONF_SILENT_MINUTES, const.DEFAULT_SILENT_MINUTES
            )
        )

    @property
    def watchdog_key(self) -> str:
        return str(self.entry.options.get(const.CONF_WATCHDOG_KEY) or "")

    @staticmethod
    def _valid_strategy(value: Any) -> str | None:
        strategy = str(value or "")
        strategy = const.LEGACY_STRATEGIES.get(strategy, strategy)
        return strategy if strategy in const.STRATEGIES else None

    @property
    def default_strategy(self) -> str:
        return (
            self._valid_strategy(self.entry.options.get(const.CONF_STRATEGY))
            or const.DEFAULT_STRATEGY
        )

    def strategy_of(self, hwid: str) -> str:
        """Strategy chosen for a device: its own, or the default."""
        own = self.entry.options.get(const.CONF_DEVICE_STRATEGIES) or {}
        value = own.get(hwid) if isinstance(own, dict) else None
        return self._valid_strategy(value) or self.default_strategy

    @callback
    def async_set_strategy(self, hwid: str, strategy: str) -> None:
        """Choose the strategy of one device (applied by the options listener)."""
        if strategy not in const.STRATEGIES:
            raise ValueError(strategy)
        options = dict(self.entry.options)
        own = dict(options.get(const.CONF_DEVICE_STRATEGIES) or {})
        own[hwid] = strategy
        options[const.CONF_DEVICE_STRATEGIES] = own
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    @property
    def reduced_minutes(self) -> int:
        return int(
            self.entry.options.get(
                const.CONF_REDUCED_MINUTES, const.DEFAULT_REDUCED_MINUTES
            )
        )

    @property
    def safety_minutes(self) -> int:
        """Polling of a device whose pushed messages cover everything."""
        return int(
            self.entry.options.get(
                const.CONF_SAFETY_MINUTES, const.DEFAULT_SAFETY_MINUTES
            )
        )

    def poseidon_interval(self, hwid: str, coordinator: Any) -> timedelta:
        """Polling interval of a device with the poseidon strategy."""
        dev = self.keystore.get(hwid)
        if fully_pushed(dev.type if dev else "", coordinator):
            return timedelta(minutes=max(self.safety_minutes, self.reduced_minutes))
        return timedelta(minutes=self.reduced_minutes)

    async def async_apply_options(self) -> None:
        """Options saved: applied at once, without restarting the relay."""
        await self._run_log(self.debug_log, self.debug)
        await self._run_log(self.anomaly_log, self.anomaly_detection)
        if not self.anomaly_detection:
            self.anomalies.clear()
        self._apply_polling()
        self._update_silent_issues()
        self._signal(force=True)

    async def _run_log(self, log: DebugLog, wanted: bool) -> None:
        if wanted and not log.running:
            await self.hass.async_add_executor_job(log.start)
        elif not wanted and log.running:
            await self.hass.async_add_executor_job(log.stop)

    async def async_start(self) -> None:
        """Load the keys and listen; OSError when the port is taken."""
        await self.async_load()
        self._started_at = dt_util.utcnow()
        with suppress(Exception):
            integration = await async_get_integration(self.hass, DOMAIN)
            self.anomalies.version = str(integration.version or "")
        await self.relay.async_start()
        await self._run_log(self.spy_log, True)
        await self._run_log(self.shadow_log, True)
        self._unsub_http = add_http_observer(self._on_http)
        await self.async_apply_options()
        self._unsub_refresh = async_track_time_interval(
            self.hass,
            self._refresh_tick,
            timedelta(seconds=const.CLOUD_REFRESH_S),
        )

    async def async_stop(self) -> None:
        if self._unsub_refresh is not None:
            self._unsub_refresh()
            self._unsub_refresh = None
        if self._unsub_http is not None:
            self._unsub_http()
            self._unsub_http = None
        await self.relay.async_stop()
        # Every device gets its own polling back
        self.paused.clear()
        for hwid in list(self.poll_control.controlled):
            self._restore_polling(hwid)
        for unsub in self._poll_unsubs.values():
            unsub()
        self._poll_unsubs.clear()
        self.comparisons.pending.clear()
        self.active.clear()
        self._spy_hosts.clear()
        await self._run_log(self.debug_log, False)
        await self._run_log(self.spy_log, False)
        await self._run_log(self.shadow_log, False)
        await self._run_log(self.anomaly_log, False)

    # ------------------------------------------------------------------
    # Devices of the integration
    # ------------------------------------------------------------------

    def local_devices(self) -> list[Any]:
        """Coordinators of the local devices (no cloud account, no group)."""
        devices: list[Any] = []
        for coordinator in self.hass.data.get(DOMAIN, {}).values():
            entry = getattr(coordinator, "_entry", None)
            data = getattr(entry, "data", {}) or {}
            if CONFIG_FLOW_CLOUD_USERNAME in data:
                continue
            if str(getattr(coordinator, "title", "")).startswith(VIRTUAL_LED):
                continue
            if not hasattr(coordinator, "model_id"):
                continue
            devices.append(coordinator)
        return devices

    def coordinator(self, hwid: str) -> Any | None:
        """Coordinator of a device, by hardware id."""
        for coordinator in self.local_devices():
            if str(coordinator.model_id).lower() == hwid:
                return coordinator
        return None

    def device_entry(self, hwid: str) -> dr.DeviceEntry | None:
        """Registry entry of a device, as its own config entry created it.

        Identifiers are only unique within a config entry: the device is the
        one owned by another entry than Poseidon's.
        """
        for device in dr.async_get(self.hass).async_get_devices(
            identifiers={(DOMAIN, hwid)}
        ):
            if not _belongs_to(device, self.entry.entry_id):
                return device
        return None

    def switch_devices(self) -> dict[str, dr.DeviceEntry]:
        """Devices getting a switch: keys known and already in the device
        registry (a switch must never create a device of its own)."""
        devices: dict[str, dr.DeviceEntry] = {}
        for dev in self.keystore.with_keys():
            device = self.device_entry(dev.hwid)
            if device is not None:
                devices[dev.hwid] = device
        return devices

    @callback
    def async_set_entity_adder(
        self, platform: str, adder: Callable[[dict[str, dr.DeviceEntry]], None]
    ) -> None:
        """Called by a platform: create its entities now and later."""
        self._adders[platform] = adder
        self.async_add_new_switches()

    @callback
    def async_set_switch_adder(
        self, adder: Callable[[dict[str, dr.DeviceEntry]], None]
    ) -> None:
        self.async_set_entity_adder("switch", adder)

    @property
    def _switched(self) -> set[str]:
        """Devices that have their Poseidon switch."""
        return self._added.get("switch", set())

    @callback
    def async_add_new_switches(self) -> None:
        """Create the entities (switches, select) of the devices that got
        keys since."""
        devices = self.switch_devices()
        for platform, adder in self._adders.items():
            added = self._added.setdefault(platform, set())
            new = {
                hwid: device for hwid, device in devices.items() if hwid not in added
            }
            if new:
                added.update(new)
                adder(new)

    def http(self, ip: str) -> DeviceHttp:
        return DeviceHttp(async_get_clientsession(self.hass), ip)

    def cloud_coordinator(self) -> Any | None:
        """Coordinator of the cloud account used for key capture."""
        return self.hass.data.get(DOMAIN, {}).get(self.cloud_entry_id)

    def cloud_device(self, hwid: str) -> dict[str, Any] | None:
        """The account's record of a device (aquarium, type, name)."""
        cloud = self.cloud_coordinator()
        if cloud is None:
            return None
        devices = cloud.get_data(
            "$.sources[?(@.name=='/device')].data", is_None_possible=True
        )
        for device in devices if isinstance(devices, list) else []:
            if isinstance(device, dict) and str(device.get("hwid", "")).lower() == hwid:
                return device
        return None

    def device_keys(self, coordinator: Any) -> DeviceKeys:
        """Keystore record of a device, completed with what is known now."""
        hwid = str(coordinator.model_id).lower()
        dev = self.keystore.get(hwid) or DeviceKeys(hwid=hwid)
        dev.ip = str(getattr(coordinator, "_ip", "") or dev.ip)
        dev.model = str(coordinator.model or dev.model)
        dev.type = dev.type or const.type_from_model(dev.model)
        record = self.cloud_device(hwid) or {}
        dev.name = str(record.get("name") or dev.name or coordinator.title)
        dev.aquarium_uid = str(record.get("aquarium_uid") or dev.aquarium_uid)
        dev.type = str(record.get("type") or dev.type)
        return dev

    def cached_cloud(self, hwid: str) -> dict[str, Any] | None:
        """The /cloud of a device as its coordinator last read it."""
        coordinator = self.coordinator(hwid)
        if coordinator is None:
            return None
        cloud = coordinator.get_data(
            "$.sources[?(@.name=='/cloud')].data", is_None_possible=True
        )
        return cloud if isinstance(cloud, dict) else None

    def in_poseidon(self, cloud: dict[str, Any] | None) -> bool:
        return broker_of(cloud) == self.advertised_url.lower()

    def traffic(self, hwid: str) -> Traffic:
        return self.relay.traffic.get(hwid) or Traffic()

    def silent(self, hwid: str) -> bool:
        """In Poseidon mode, but nothing went through the relay for a while."""
        if not self.in_poseidon(self.cached_cloud(hwid)):
            return False
        traffic = self.traffic(hwid)
        seen = [t for t in (traffic.last_up, traffic.last_down) if t is not None]
        last = max([*seen, self._started_at])
        return dt_util.utcnow() - last > timedelta(minutes=self.silent_minutes)

    @callback
    def _update_silent_issues(self) -> None:
        """One repair issue per silent device; it goes when traffic resumes."""
        for hwid in self._switched:
            issue_id = f"{const.ISSUE_DEVICE_SILENT}_{hwid}"
            if self.silent(hwid):
                dev = self.keystore.get(hwid)
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key=const.ISSUE_DEVICE_SILENT,
                    translation_placeholders={
                        "name": (dev.name if dev else "") or hwid,
                        "minutes": str(self.silent_minutes),
                    },
                )
            else:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    @callback
    def async_clear_issues(self) -> None:
        """Poseidon stopped: its silent-device issues mean nothing anymore."""
        for hwid in self._switched:
            ir.async_delete_issue(
                self.hass, DOMAIN, f"{const.ISSUE_DEVICE_SILENT}_{hwid}"
            )

    # ------------------------------------------------------------------
    # Keystore export / import (CLI format)
    # ------------------------------------------------------------------

    @property
    def files_dir(self) -> Path:
        return Path(self.hass.config.path(const.FILES_DIR))

    def _write_export(self, data: dict[str, Any]) -> Path:
        stamp = dt_util.now().strftime("%Y%m%d-%H%M%S")
        path = self.files_dir / f"keystore-{stamp}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Secrets: readable by the owner only, from the very first byte
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        return path

    async def async_export(self) -> Path:
        """Write the keystore to a new file; its path."""
        return await self.hass.async_add_executor_job(
            self._write_export, self.keystore.as_json()
        )

    def rescue_data(self) -> dict[str, Any]:
        """What the rescue script embeds: relay address and every device with
        keys, with the broker of its normal mode."""
        return {
            "relay": self.advertised_url,
            "generated": dt_util.now().isoformat(),
            "devices": [
                {
                    "hwid": dev.hwid,
                    "name": dev.name,
                    "type": dev.type,
                    "model": dev.model,
                    "ip": str(getattr(self.coordinator(dev.hwid), "_ip", "") or dev.ip),
                    "api_key": dev.api_key,
                    "api_secret": dev.api_secret,
                    "mqtt_url": self.normal_url(dev),
                }
                for dev in self.keystore.with_keys()
            ],
        }

    def rescue_script(self) -> str:
        """The rescue script with the devices embedded (blocking: reads the
        template)."""
        template = (Path(__file__).parent / "rescue_script.py").read_text(
            encoding="utf-8"
        )
        payload = json.dumps(self.rescue_data(), ensure_ascii=False)
        line = f"EMBEDDED = json.loads({payload!r})"
        if "\nEMBEDDED = None\n" not in template:
            raise ValueError("rescue template without its EMBEDDED line")
        return template.replace("\nEMBEDDED = None\n", f"\n{line}\n", 1)

    def signed_url(self, path: str) -> str:
        """A short-lived signed link to one of Poseidon's downloads.

        Signed for the user of the current request (the options flow), so it
        works in a plain browser tab, without the auth header, and expires.
        """
        return async_sign_path(
            self.hass, path, timedelta(minutes=const.EXPORT_LINK_MINUTES)
        )

    def export_url(self) -> str:
        """A short-lived signed link to download the keystore."""
        return self.signed_url(const.EXPORT_VIEW_URL)

    def export_filename(self) -> str:
        return f"keystore-{dt_util.now().strftime('%Y%m%d-%H%M%S')}.json"

    async def async_import(self, path: Path) -> tuple[int, int, int]:
        """Merge a keystore file (see KeyStore.merge), then add the switches.

        Raises:
            OSError: the file cannot be read.
            ValueError: it is not a keystore.
        """

        def _read() -> Any:
            return json.loads(path.read_text(encoding="utf-8"))

        return await self._merge_keystore(await self.hass.async_add_executor_job(_read))

    async def async_import_upload(self, file_id: str) -> tuple[int, int, int]:
        """Merge a keystore sent with the file selector of the options flow.

        Raises:
            OSError: the upload is gone (sent too long ago, or twice).
            ValueError: it is not a keystore.
        """

        def _read() -> Any:
            try:
                with process_uploaded_file(self.hass, file_id) as path:
                    return json.loads(path.read_text(encoding="utf-8"))
            except ValueError as err:
                if "does not exist" in str(err):
                    raise FileNotFoundError(file_id) from err
                raise

        return await self._merge_keystore(await self.hass.async_add_executor_job(_read))

    async def _merge_keystore(self, data: Any) -> tuple[int, int, int]:
        counts = self.keystore.merge(data)
        if counts[0] or counts[1]:
            await self.keystore.async_save()
            self.async_add_new_switches()
            self._signal(force=True)
        return counts

    # ------------------------------------------------------------------
    # Watchdog
    # ------------------------------------------------------------------

    def is_alive(self, request: dict[str, Any]) -> dict[str, Any]:
        """Response to a watchdog request (see watchdog.py)."""
        try:
            minutes = max(1, int(request.get("minutes") or 10))
        except (TypeError, ValueError):
            minutes = 10
        cutoff = dt_util.utcnow() - timedelta(minutes=minutes)

        def recent(hwid: str) -> bool:
            traffic = self.traffic(hwid)
            return bool(
                traffic.last_up
                and traffic.last_down
                and traffic.last_up >= cutoff
                and traffic.last_down >= cutoff
            )

        devices: dict[str, Any] = {}
        for dev in self.keystore.with_keys():
            if not self.in_poseidon(self.cached_cloud(dev.hwid)):
                continue
            traffic = self.traffic(dev.hwid)
            devices[dev.hwid] = {
                "name": dev.name,
                "type": dev.type,
                "ip": dev.ip,
                "api_key": dev.api_key,
                "api_secret": dev.api_secret,
                # Where to switch it back to
                "mqtt_url": self.normal_url(dev),
                "last_up": traffic.last_up.isoformat() if traffic.last_up else None,
                "last_down": (
                    traffic.last_down.isoformat() if traffic.last_down else None
                ),
            }
        return {
            "id": request.get("id"),
            "ts": dt_util.now().isoformat(),
            "ok": any(recent(hwid) for hwid in devices),
            "devices": devices,
        }

    async def async_status(self, coordinator: Any) -> str:
        """Where a device stands for the "add devices" menu (read live)."""
        dev = self.device_keys(coordinator)
        cloud = await self.http(dev.ip).get_cloud()
        if cloud is None:
            return STATUS_UNREACHABLE
        if self.in_poseidon(cloud):
            return STATUS_POSEIDON
        if dev.has_keys:
            return STATUS_KEYS_OK
        if not str(cloud.get("api_key") or ""):
            # Bound to a local-only aquarium: no broker to come back to
            return STATUS_NO_CLOUD
        if not dev.aquarium_uid:
            return STATUS_NOT_IN_ACCOUNT
        return STATUS_KEYS_NEEDED

    # ------------------------------------------------------------------
    # Switching
    # ------------------------------------------------------------------

    def normal_url(self, dev: DeviceKeys) -> str:
        """Broker of the normal mode: the one the keys were issued for."""
        url = dev.mqtt_url.strip()
        if not url or url.lower() == self.advertised_url.lower():
            return const.NORMAL_MQTT_URL
        return url

    async def async_switch(self, hwid: str, poseidon: bool) -> bool:
        """Point a device at the relay, or back at the Red Sea broker."""
        coordinator = self.coordinator(hwid)
        stored = self.keystore.get(hwid)
        if coordinator is None or stored is None or not stored.has_keys:
            return False
        old_ip = stored.ip
        dev = self.device_keys(coordinator)
        url = self.advertised_url if poseidon else self.normal_url(dev)
        done = await self.http(dev.ip).set_cloud(url, dev.api_key, dev.api_secret)
        if done and dev.ip != old_ip:
            # The device moved: the watchdog will need its new address
            await self.keystore.async_upsert(dev)
        await asyncio.sleep(const.SWITCH_SETTLE_S)
        await self._refresh_cloud(coordinator)
        self._apply_polling()
        self._signal(force=True)
        return done

    async def async_revert_all(self) -> list[str]:
        """Every device in Poseidon mode back to normal mode.

        Reads each device itself (the relay may already be stopped).
        Returns the names of the devices that could not be switched back.
        """
        failed: list[str] = []
        for dev in self.keystore.with_keys():
            coordinator = self.coordinator(dev.hwid)
            ip = str(getattr(coordinator, "_ip", "") or dev.ip)
            if not ip:
                continue
            http = self.http(ip)
            cloud = await http.get_cloud()
            if cloud is None:
                failed.append(dev.name or dev.hwid)
                continue
            if not self.in_poseidon(cloud):
                continue
            if not await http.set_cloud(
                self.normal_url(dev), dev.api_key, dev.api_secret
            ):
                failed.append(dev.name or dev.hwid)
        return failed

    # ------------------------------------------------------------------
    # Key capture
    # ------------------------------------------------------------------

    async def async_add_devices(
        self,
        hwids: list[str],
        on_device: Callable[[CaptureReport], Awaitable[None] | None] | None = None,
    ) -> list[CaptureReport]:
        """Capture the keys of the devices lacking them, then switch them all.

        One device after the other: a capture re-pairs the device with the
        cloud, better not done on several at once.
        """
        reports: list[CaptureReport] = []
        cloud = self.cloud_coordinator()
        for hwid in hwids:
            coordinator = self.coordinator(hwid)
            if coordinator is None:
                continue
            dev = self.device_keys(coordinator)
            if dev.has_keys:
                report = CaptureReport(hwid=hwid, name=dev.name, ok=True)
            elif cloud is None:
                report = CaptureReport(
                    hwid=hwid, name=dev.name, error="no_cloud_account"
                )
            else:
                report = await acquire_keys(
                    cloud.my_api, self.http(dev.ip), dev, self.keystore, self.snapshots
                )
            if report.ok and not await self.async_switch(hwid, True):
                report.error = report.error or "switch_failed"
            reports.append(report)
            if on_device is not None:
                result = on_device(report)
                if result is not None:
                    await result
        return reports

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _refresh_cloud(self, coordinator: Any) -> None:
        self._cloud_read[str(coordinator.model_id).lower()] = time.monotonic()
        try:
            # Read through the coordinator, but sent for Poseidon
            with http_origin(ORIGIN):
                await coordinator.fetch_config("/cloud")
        except Exception:
            _LOGGER.debug("Could not read /cloud of %s", coordinator.title)

    def talking(self, hwid: str) -> bool:
        """In Poseidon mode and exchanging through the relay right now."""
        if not self.in_poseidon(self.cached_cloud(hwid)):
            return False
        traffic = self.traffic(hwid)
        seen = [t for t in (traffic.last_up, traffic.last_down) if t is not None]
        if not seen:
            return False
        return dt_util.utcnow() - max(seen) < timedelta(seconds=const.TALKING_S)

    def _cloud_due(self, hwid: str) -> bool:
        """Whether /cloud of a device is to be read on this tick.

        Every tick, except for a device talking to the relay: it is in
        Poseidon mode, its traffic says so, so /cloud is only read now and
        then (``safety_minutes``). As soon as it goes quiet (rebooting,
        pointed back at Red Sea), it is read on every tick again.
        """
        last = self._cloud_read.get(hwid)
        if last is None or not self.talking(hwid):
            return True
        return time.monotonic() - last >= self.safety_minutes * 60

    async def _refresh_tick(self, _now: Any = None) -> None:
        """Read /cloud of the managed devices again (it is a config source,
        not refreshed by the regular polling)."""
        for dev in self.keystore.with_keys():
            coordinator = self.coordinator(dev.hwid)
            # A paused device gets no request at all, this one included
            if (
                coordinator is not None
                and dev.hwid not in self.paused
                and self._cloud_due(dev.hwid)
            ):
                await self._refresh_cloud(coordinator)
        self._apply_polling()
        self._update_silent_issues()
        self._signal(force=True)

    @callback
    def async_set_paused(self, hwid: str, paused: bool) -> None:
        """Pause the polling of a device in spy mode, or resume it."""
        if paused and self.active.get(hwid) != const.STRATEGY_SPY:
            raise ValueError(hwid)
        if paused == (hwid in self.paused):
            return
        if paused:
            self.paused.add(hwid)
        else:
            self.paused.discard(hwid)
        self.spy_log.write(mark_record(hwid, "poll_paused", paused))
        self._apply_polling()
        self._signal(force=True)

    @callback
    def _apply_polling(self) -> None:
        """Apply each device's strategy while it is in Poseidon mode; every
        other device gets its own polling back."""
        active: dict[str, str] = {}
        coordinators: dict[str, Any] = {}
        for dev in self.keystore.with_keys():
            coordinator = self.coordinator(dev.hwid)
            if coordinator is None or not self.in_poseidon(self.cached_cloud(dev.hwid)):
                continue
            active[dev.hwid] = self.strategy_of(dev.hwid)
            coordinators[dev.hwid] = coordinator
        changed: set[str] = set()
        for hwid, strategy in active.items():
            if self.active.get(hwid) != strategy:
                self.spy_log.write(mark_record(hwid, "strategy", strategy))
                changed.add(hwid)
        for hwid in set(self.active) - set(active):
            self.spy_log.write(mark_record(hwid, "strategy", None))
            changed.add(hwid)
        # A new run starts with whole answers, never "unchanged" ones
        self._http_seen = {
            key: digest
            for key, digest in self._http_seen.items()
            if key[0] not in changed
        }
        self.active = active
        # A pause only exists in spy mode
        self.paused &= {h for h, s in active.items() if s == const.STRATEGY_SPY}

        for hwid, strategy in active.items():
            coordinator = coordinators[hwid]
            if strategy == const.STRATEGY_POSEIDON:
                self.poll_control.set(
                    hwid, coordinator, self.poseidon_interval(hwid, coordinator)
                )
            elif hwid in self.paused:
                self.poll_control.set(hwid, coordinator, None)
            else:
                self._restore_polling(hwid)
            if hwid not in self._poll_unsubs:
                self._poll_unsubs[hwid] = coordinator.async_add_listener(
                    self._polled_callback(hwid)
                )
        for hwid in self.poll_control.controlled - set(active):
            self._restore_polling(hwid)
        for hwid in set(self._poll_unsubs) - set(active):
            self._poll_unsubs.pop(hwid)()
            self.comparisons.drop(hwid)
        self._spy_hosts = {
            str(getattr(coordinators[hwid], "_ip", "") or ""): hwid
            for hwid, strategy in active.items()
            if strategy == const.STRATEGY_SPY
        }
        self._spy_hosts.pop("", None)
        self.relay.log_frames = self.debug or bool(active)

    @callback
    def _restore_polling(self, hwid: str) -> None:
        paused = (
            hwid in self.poll_control.controlled
            and self.poll_control.interval(hwid) is None
        )
        coordinator = self.poll_control.restore(hwid)
        if paused and coordinator is not None:
            # Nothing is scheduled anymore: a refresh schedules the next one
            self.hass.async_create_task(coordinator.async_request_refresh(wait=0))

    def _polled_callback(self, hwid: str) -> Callable[[], None]:
        @callback
        def _polled() -> None:
            if hwid in self._merging:
                return
            coordinator = self.coordinator(hwid)
            if coordinator is not None:
                self.comparisons.polled(hwid, coordinator)

        return _polled

    @callback
    def _merge(self, hwid: str, coordinator: Any, topic: str, payload: Any) -> bool:
        """Merge a pushed state into the sources of its device, and tell its
        entities (that is no poll: the comparison waits for the next one)."""
        dev = self.keystore.get(hwid)
        merge = merge_telemetry if is_telemetry_topic(topic) else merge_state
        if not merge(dev.type if dev else "", coordinator, topic, payload):
            return False
        self._merging.add(hwid)
        try:
            coordinator.async_update_listeners()
        finally:
            self._merging.discard(hwid)
        return True

    @callback
    def _on_state(self, hwid: str, topic: str, payload: Any) -> None:
        """A device in Poseidon mode pushed a state."""
        strategy = self.active.get(hwid)
        coordinator = self.coordinator(hwid)
        if strategy is None or coordinator is None:
            return
        if strategy == const.STRATEGY_SPY:
            self.comparisons.add(hwid, topic, payload, self.spy_log.write)
            return
        merged = self._merge(hwid, coordinator, topic, payload)
        if strategy == const.STRATEGY_SHADOW:
            self.comparisons.add(hwid, topic, payload, self.shadow_log.write, merged)
            return
        if merged:
            return
        # Poseidon strategy, family without a merger: read the device again
        now = time.monotonic()
        if now - self._push_refresh.get(hwid, 0.0) < const.PUSH_REFRESH_MIN_S:
            return
        self._push_refresh[hwid] = now
        self.hass.async_create_task(
            coordinator.async_request_refresh(wait=const.PUSH_REFRESH_WAIT_S)
        )

    @callback
    def _on_telemetry(self, hwid: str, topic: str, payload: Any) -> None:
        """A device in Poseidon mode pushed its telemetry (every 60 s)."""
        strategy = self.active.get(hwid)
        coordinator = self.coordinator(hwid)
        dev = self.keystore.get(hwid)
        if strategy is None or coordinator is None or dev is None:
            return
        if dev.type not in TELEMETRY_MERGERS:
            # Nothing to learn from it yet: no comparison every minute either
            return
        if strategy == const.STRATEGY_SPY:
            self.comparisons.add(
                hwid, topic, payload, self.spy_log.write, latest_only=True
            )
            return
        merged = self._merge(hwid, coordinator, topic, payload)
        if strategy == const.STRATEGY_SHADOW:
            self.comparisons.add(
                hwid, topic, payload, self.shadow_log.write, merged, latest_only=True
            )

    @callback
    def _on_http(self, record: dict[str, Any]) -> None:
        """An HTTP request to a host (any API instance): kept when the host
        is a device in spy mode."""
        hwid = self._spy_hosts.get(str(record.get("host") or ""))
        if hwid is not None:
            self.spy_log.write(http_record(hwid, record, self._http_seen))

    @callback
    def _on_connect(self, hwid: str, fields: dict[str, str]) -> None:
        """The CONNECT password is the api_key: keep the keystore right."""
        dev = self.keystore.get(hwid)
        password = fields.get("password", "")
        if dev is not None and password and dev.api_key != password:
            _LOGGER.warning("%s: api_key changed on the wire, keystore updated", hwid)
            dev.api_key = password
            self.hass.async_create_task(self.keystore.async_upsert(dev))
        self._signal(force=True)

    @callback
    def _on_traffic(self, hwid: str, direction: str) -> None:
        self._signal()

    @callback
    def _on_frame(self, hwid: str, direction: str, frame: MqttFrame) -> None:
        """A relayed frame: debug and spy logs, and the states a device
        pushes."""
        dev = self.keystore.get(hwid)
        secret = dev.api_secret if dev else ""
        strategy = self.active.get(hwid)
        if self.debug or strategy == const.STRATEGY_SPY:
            record = frame_record(hwid, direction, frame, secret)
            if self.debug:
                self.debug_log.write(record)
            if strategy == const.STRATEGY_SPY:
                self.spy_log.write(record)
        if strategy is None:
            return
        if frame.packet_type != PACKET_PUBLISH:
            self._check_anomalies(hwid, direction, frame.packet_type, None, None)
            return
        topic, payload = frame.parse_publish()
        message: Any = None
        if len(secret) == 16:
            try:
                message = decrypt_payload(
                    payload.decode("utf-8", errors="replace"), secret
                )
            except Exception:
                _LOGGER.debug("Poseidon: %s of %s does not decrypt", topic, hwid)
        self._check_anomalies(hwid, direction, PACKET_PUBLISH, topic, message)
        if direction != UP or message is None:
            return
        if is_telemetry_topic(topic):
            self._on_telemetry(hwid, topic, message)
        elif is_state_topic(topic):
            self._on_state(hwid, topic, message)

    @callback
    def _check_anomalies(
        self,
        hwid: str,
        direction: str,
        packet_type: int,
        topic: str | None,
        message: Any,
    ) -> None:
        """Report what a frame carried that nothing expected."""
        if not self.anomaly_detection:
            return
        dev = self.keystore.get(hwid)
        try:
            found = check_frame(
                dev.type if dev else "", direction, packet_type, topic, message, hwid
            )
        except Exception:
            _LOGGER.debug("Poseidon: anomaly check failed", exc_info=True)
            return
        if not found:
            return
        coordinator = self.coordinator(hwid)
        self.anomalies.report(
            hwid,
            found,
            model=str(getattr(coordinator, "model", "") or ""),
            firmware=str(getattr(coordinator, "sw_version", "") or ""),
        )

    @callback
    def _signal(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_signal < TRAFFIC_SIGNAL_S:
            return
        self._last_signal = now
        async_dispatcher_send(self.hass, const.SIGNAL_POSEIDON_UPDATE)
