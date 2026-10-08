"""Use the device list of a ReefBeat cloud account (`GET /device`).

Each device of the account carries its last reported `ip_address`. It is
used twice:

- **Adding devices**: right after a cloud account is validated (and from its
  options), the account's devices not configured yet are proposed, without a
  network scan. That also finds devices on subnets the scan does not sweep.
- **Following IP changes**: on every refresh of the cloud account, a
  configured device reported at another address is looked up there and, if it
  is really the same device, its entry is updated (or a repair proposes it).

The cloud IP is only a hint (DHCP lease renewed since, device off, device on
a backup hotspot...): an address is always probed first, and only trusted
when the device answering there has the expected hwid. Configured entries
are matched on their unique id, the UPnP UDN read from `/description.xml`.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from functools import partial
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auto_detect import ReefBeatInfo, probe_device
from .const import (
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
    HW_DEVICES_IDS,
    IP_UPDATE_AUTO,
    IP_UPDATE_OFF,
    IP_UPDATE_REPAIR,
    ISSUE_IP_CHANGED,
)
from .reefbeat import ReefBeatCloudAPI

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Cloud device list
# =============================================================================


async def async_fetch_account_devices(
    hass: HomeAssistant, username: str, password: str, server: str
) -> list[dict[str, Any]] | None:
    """The `/device` list of a cloud account, None when it cannot be read."""
    api = ReefBeatCloudAPI(
        username, password, False, server, async_get_clientsession(hass), True
    )
    try:
        await api.connect()
        res = await api.http_get("/device")
    except Exception as err:
        _LOGGER.warning("Could not read the devices of %s: %s", username, err)
        return None
    body = res.get("json") if res and res.get("ok") else None
    if not isinstance(body, list):
        _LOGGER.warning("Could not read the devices of %s", username)
        return None
    return [
        cast(dict[str, Any], d) for d in cast(list[Any], body) if isinstance(d, dict)
    ]


def local_devices(devices: Any) -> list[dict[str, Any]]:
    """Devices of the list that have an IP and a model the integration drives."""
    if not isinstance(devices, list):
        return []
    return [
        d
        for d in devices
        if isinstance(d, dict)
        and d.get("ip_address")
        and d.get("hwid")
        and d.get("model") in HW_DEVICES_IDS
    ]


async def async_probe(hass: HomeAssistant, ip: str) -> ReefBeatInfo | None:
    """Identify the device answering at `ip` (blocking probe in the executor)."""
    return await hass.async_add_executor_job(partial(probe_device, ip))


def _local_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    """Config entries of physical devices (not cloud accounts nor virtual)."""
    return [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.data.get(CONFIG_FLOW_HW_MODEL) in HW_DEVICES_IDS
    ]


def _loaded_hwids(hass: HomeAssistant) -> set[str]:
    """Hwids of the devices whose coordinator is loaded."""
    hwids: set[str] = set()
    for coordinator in hass.data.get(DOMAIN, {}).values():
        model_id = getattr(coordinator, "model_id", None)
        if isinstance(model_id, str):
            hwids.add(model_id.lower())
    return hwids


def _same_device(info: ReefBeatInfo | None, hwid: str) -> bool:
    """Whether the probed device is the cloud's (an address can be reused)."""
    return info is not None and info.get("hwid", "") == hwid.lower()


# =============================================================================
# Adding the devices of an account
# =============================================================================


@dataclass
class AccountDevices:
    """Devices of an account not configured yet."""

    # Answering at their cloud address: can be added
    found: list[ReefBeatInfo] = field(default_factory=list)
    # Not answering there (off, moved, other subnet): shown, not addable
    unreachable: list[str] = field(default_factory=list)


async def async_account_devices(
    hass: HomeAssistant, devices: list[dict[str, Any]]
) -> AccountDevices:
    """Split the account's devices not configured yet by reachability."""
    entries = _local_entries(hass)
    known_ips = {str(e.data.get(CONFIG_FLOW_IP_ADDRESS)) for e in entries}
    known_uids = {e.unique_id for e in entries if e.unique_id}
    known_hwids = _loaded_hwids(hass)

    pending = [
        d
        for d in local_devices(devices)
        if str(d["hwid"]).lower() not in known_hwids
        and str(d["ip_address"]) not in known_ips
    ]
    probes = await asyncio.gather(
        *(async_probe(hass, str(d["ip_address"])) for d in pending)
    )

    result = AccountDevices()
    for device, info in zip(pending, probes, strict=True):
        if not _same_device(info, str(device["hwid"])):
            label = f"{device.get('name') or device['hwid']} ({device['ip_address']})"
            result.unreachable.append(label)
            continue
        assert info is not None
        if info.get("uuid") in known_uids:
            continue
        result.found.append(info)
    return result


def spawn_imports(hass: HomeAssistant, values: list[str]) -> None:
    """Start one background import flow per encoded device string."""
    for value in values:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data={CONFIG_FLOW_IP_ADDRESS: value},
            )
        )


# =============================================================================
# Following IP changes
# =============================================================================


def ip_issue_id(entry_id: str) -> str:
    """Repair issue id of an IP change of one device entry."""
    return f"{ISSUE_IP_CHANGED}_{entry_id}"


def apply_new_ip(hass: HomeAssistant, entry: ConfigEntry, new_ip: str) -> None:
    """Persist the new IP; the entry's update listener reloads it."""
    _LOGGER.info(
        "%s moved from %s to %s: updating its entry",
        entry.title,
        entry.data.get(CONFIG_FLOW_IP_ADDRESS),
        new_ip,
    )
    hass.config_entries.async_update_entry(
        entry, data={**dict(entry.data), CONFIG_FLOW_IP_ADDRESS: new_ip}
    )
    ir.async_delete_issue(hass, DOMAIN, ip_issue_id(entry.entry_id))


class IpTracker:
    """Follow the IP changes reported by one cloud account.

    Probing costs a request per address, so an address already checked for a
    device is not probed again until the cloud reports another one.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        # hwid -> cloud IP already handled (nothing to do, or done)
        self._checked: dict[str, str] = {}
        self._running = False

    async def async_check(self, devices: Any, mode: str) -> None:
        """Compare the cloud IPs with the configured ones and act on changes."""
        if mode == IP_UPDATE_OFF or self._running:
            return
        self._running = True
        try:
            await self._async_check(devices, mode)
        finally:
            self._running = False

    async def _async_check(self, devices: Any, mode: str) -> None:
        entries = _local_entries(self._hass)
        by_ip = {str(e.data.get(CONFIG_FLOW_IP_ADDRESS)): e for e in entries}
        by_uid = {e.unique_id: e for e in entries if e.unique_id}

        for device in local_devices(devices):
            hwid = str(device["hwid"]).lower()
            ip = str(device["ip_address"])
            # A device the cloud sees offline reports a stale address
            if device.get("connected") is False:
                continue
            entry = by_ip.get(ip)
            if entry is not None:
                # Configured at that address: a pending proposal is moot
                ir.async_delete_issue(self._hass, DOMAIN, ip_issue_id(entry.entry_id))
                self._checked[hwid] = ip
                continue
            if self._checked.get(hwid) == ip:
                continue

            info = await async_probe(self._hass, ip)
            if not _same_device(info, hwid):
                # Not there (yet): try again on the next refresh
                continue
            self._checked[hwid] = ip
            assert info is not None
            entry = by_uid.get(info.get("uuid", ""))
            if entry is None:
                continue  # not configured in Home Assistant
            self._handle_move(entry, ip, mode)

    def _handle_move(self, entry: ConfigEntry, new_ip: str, mode: str) -> None:
        """A configured device answers at a new address."""
        if mode == IP_UPDATE_AUTO:
            apply_new_ip(self._hass, entry, new_ip)
            return
        if mode == IP_UPDATE_REPAIR:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                ip_issue_id(entry.entry_id),
                is_fixable=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_IP_CHANGED,
                translation_placeholders={
                    "device": entry.title,
                    "old_ip": str(entry.data.get(CONFIG_FLOW_IP_ADDRESS)),
                    "new_ip": new_ip,
                },
                data={
                    "kind": ISSUE_IP_CHANGED,
                    "entry_id": entry.entry_id,
                    "new_ip": new_ip,
                },
            )
