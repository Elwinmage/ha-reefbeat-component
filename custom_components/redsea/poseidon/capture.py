"""Key capture: the one-off, destructive retrieval of a device's keys.

A device masks its ``api_secret`` in ``GET /cloud``. The only way to get it
is to delete the device from the Red Sea cloud and create it again: the
creation answers a fresh ``{url, api_key, api_secret}``. Ported from
``reefbeat_god_mode.py`` (``acquire_keys`` and the verified restore
handlers), see ``reefbeat_restore_map.md`` for the write paths.

Sequence for one device:

1. snapshot its configuration, once (a pending snapshot is never
   overwritten: it holds the state from before);
2. ``DELETE /device/{hwid}`` then ``POST /device`` on the cloud account;
3. store the keys, push them to the device (Red Sea broker);
4. snapshot again and compare; RSRUN and RSWAVE get their configuration
   back automatically (verified handlers), the other families only report
   what changed — never guessed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import const
from .device_http import DeviceHttp
from .keystore import DeviceKeys, KeyStore

_LOGGER = logging.getLogger(__name__)

# Endpoints of a snapshot: the sources the integration reads, per family
COMMON_ENDPOINTS = [
    "/device-info",
    "/firmware",
    "/mode",
    "/cloud",
    "/wifi",
    "/dashboard",
]
TYPE_ENDPOINTS: dict[str, list[str]] = {
    "reef-lights": (
        ["/manual", "/acclimation", "/moonphase", "/preset_name"]
        + [f"/auto/{day}" for day in range(1, 8)]
        + [f"/clouds/{day}" for day in range(1, 8)]
        + [f"/preset_name/{day}" for day in range(1, 8)]
    ),
    "reef-wave": ["/auto", "/feeding/schedule", "/device-settings"],
    "reef-dosing": (
        ["/device-settings", "/configuration"]
        + [f"/head/{head}/settings" for head in range(1, 5)]
    ),
    "reef-run": ["/pump/settings", "/pump/shortcuts"],
    "reef-mat": ["/configuration"],
    "reef-ato": ["/configuration"],
    "reef-power": (
        ["/configuration", "/sockets/config"]
        + [f"/socket/{n}/config/schedule" for n in range(1, 7)]
    ),
    "reef-control": (
        ["/configuration", "/ports/config", "/subscription-info"]
        + [f"/port/{n}/schedule" for n in range(1, 5)]
    ),
}
FALLBACK_ENDPOINTS = [
    "/configuration",
    "/device-settings",
    "/schedule",
    "/auto",
    "/manual",
    "/moonphase",
    "/acclimation",
    "/pump/settings",
    "/feeding/schedule",
    "/sockets/config",
    "/ports/config",
]
# Changes on its own at every capture: the new keys are the point
IGNORED_IN_DIFF = frozenset({"/cloud"})
# Delete statuses after which the device can be created again
DELETE_OK = frozenset({200, 202, 204, 404})


def endpoints_for(device_type: str) -> list[str]:
    """Snapshot endpoints of a device type, deduplicated, in order."""
    extra = TYPE_ENDPOINTS.get(device_type) or FALLBACK_ENDPOINTS
    return list(dict.fromkeys(COMMON_ENDPOINTS + extra))


class CloudAccount(Protocol):
    """What capture needs of a cloud account: ReefBeatCloudAPI.http_send."""

    async def http_send(
        self, action: str, payload: Any = None, method: str = "post"
    ) -> Any: ...


# =============================================================================
# Snapshots
# =============================================================================


@dataclass
class Snapshot:
    """A device's configuration read from its local API at one point."""

    hwid: str
    taken_at: str
    ip: str
    type: str = ""
    model: str = ""
    name: str = ""
    endpoints: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "version": 1,
            "hwid": self.hwid,
            "taken_at": self.taken_at,
            "ip": self.ip,
            "type": self.type,
            "model": self.model,
            "name": self.name,
            "endpoints": self.endpoints,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Snapshot:
        return cls(
            hwid=str(data.get("hwid", "")),
            taken_at=str(data.get("taken_at", "")),
            ip=str(data.get("ip", "")),
            type=str(data.get("type", "")),
            model=str(data.get("model", "")),
            name=str(data.get("name", "")),
            endpoints=dict(data.get("endpoints") or {}),
        )

    @property
    def was_off(self) -> bool:
        """Whether the device was deliberately off when snapshotted."""
        mode = self.endpoints.get("/mode")
        return isinstance(mode, dict) and mode.get("mode") == "off"


class SnapshotStore:
    """Snapshots on disk: ``<base>/<hwid>/pending.json`` plus a history.

    The pending snapshot is the state from before a capture. It is written
    once and kept until the capture fully succeeded: a pending snapshot left
    behind means "to check or retry".
    """

    def __init__(self, hass: HomeAssistant, base: Path) -> None:
        self._hass = hass
        self.base = base

    def pending_path(self, hwid: str) -> Path:
        return self.base / hwid / "pending.json"

    def _write(self, snap: Snapshot) -> Path:
        directory = self.base / snap.hwid
        directory.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(snap.to_json(), indent=2, ensure_ascii=False)
        stamp = snap.taken_at.replace(":", "").replace("-", "")[:15]
        (directory / f"{stamp}.json").write_text(payload, encoding="utf-8")
        pending = self.pending_path(snap.hwid)
        pending.write_text(payload, encoding="utf-8")
        return pending

    def _read(self, hwid: str) -> Snapshot | None:
        path = self.pending_path(hwid)
        if not path.exists():
            return None
        try:
            return Snapshot.from_json(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return None

    def _drop(self, hwid: str) -> None:
        self.pending_path(hwid).unlink(missing_ok=True)

    async def async_save(self, snap: Snapshot) -> Path:
        return await self._hass.async_add_executor_job(self._write, snap)

    async def async_pending(self, hwid: str) -> Snapshot | None:
        return await self._hass.async_add_executor_job(self._read, hwid)

    async def async_drop(self, hwid: str) -> None:
        await self._hass.async_add_executor_job(self._drop, hwid)


async def take_snapshot(http: DeviceHttp, dev: DeviceKeys) -> Snapshot:
    """Read every snapshot endpoint of a device."""
    snap = Snapshot(
        hwid=dev.hwid,
        taken_at=dt_util.now().isoformat(),
        ip=dev.ip,
        type=dev.type,
        model=dev.model,
        name=dev.name,
    )
    endpoints = endpoints_for(dev.type)
    values = await asyncio.gather(*(http.get_json(e) for e in endpoints))
    snap.endpoints = {e: v for e, v in zip(endpoints, values) if v is not None}
    return snap


def diff_snapshots(before: Snapshot, after: Snapshot) -> list[str]:
    """Endpoints whose content changed between two snapshots."""
    return [
        endpoint
        for endpoint in sorted(set(before.endpoints) | set(after.endpoints))
        if endpoint not in IGNORED_IN_DIFF
        and before.endpoints.get(endpoint) != after.endpoints.get(endpoint)
    ]


# =============================================================================
# Verified restore handlers (from reefbeatEnergyBackup's PumpController)
# =============================================================================


@dataclass
class RestoreStep:
    """A write, an optional pause, an optional re-read (the device does not
    expose its new state at once)."""

    endpoint: str
    payload: Any
    method: str = "POST"
    wait: float = 0.0
    reread: str = ""


async def run_steps(http: DeviceHttp, steps: list[RestoreStep]) -> bool:
    """Run a sequence, stopping at the first refused write."""
    for step in steps:
        if not await http.write_json(step.endpoint, step.payload, step.method):
            return False
        if step.wait:
            await asyncio.sleep(step.wait)
        if step.reread:
            await http.get_json(step.reread)
    return True


def rsrun_steps(snap: Snapshot) -> list[RestoreStep]:
    """RSRUN: the schedule of each pump, one ``PUT /pump/settings`` each.

    Name, model and type belong to the pump installation, which the
    re-pairing does not touch.
    """
    settings = snap.endpoints.get("/pump/settings")
    if not isinstance(settings, dict):
        return []
    steps: list[RestoreStep] = []
    for pump, data in settings.items():
        if not str(pump).startswith("pump_") or not isinstance(data, dict):
            continue
        if data.get("schedule") is None:
            continue
        steps.append(
            RestoreStep(
                "/pump/settings",
                {
                    pump: {
                        "schedule_enabled": bool(data.get("schedule_enabled", True)),
                        "schedule": data["schedule"],
                    }
                },
                method="PUT",
                wait=const.STEP_WAIT_S,
                reread="/pump/settings",
            )
        )
    return steps


def rswave_steps(snap: Snapshot) -> list[RestoreStep]:
    """RSWAVE: the transactional ``/auto``, one interval per POST.

    The ESP8266 firmware rejects a POST carrying three intervals or more;
    the same path works on ESP32 ones.
    """
    auto = snap.endpoints.get("/auto")
    if not isinstance(auto, dict):
        return []
    intervals = auto.get("intervals")
    if not isinstance(intervals, list) or not intervals:
        return []
    op_uid = str(uuid.uuid4())
    return [
        RestoreStep("/auto/init", {"uid": op_uid}),
        *(RestoreStep("/auto", {"intervals": [i]}) for i in intervals),
        RestoreStep("/auto/complete", {"uid": op_uid}),
        RestoreStep(
            "/auto/apply", {"uid": op_uid}, wait=const.STEP_WAIT_S, reread="/auto"
        ),
    ]


RESTORE_STEPS: dict[str, Callable[[Snapshot], list[RestoreStep]]] = {
    "reef-run": rsrun_steps,
    "reef-wave": rswave_steps,
}


def can_restore(device_type: str) -> bool:
    return device_type in RESTORE_STEPS


async def restore_device(http: DeviceHttp, snap: Snapshot) -> bool:
    """Replay a snapshot, then switch the device on unless it was off."""
    builder = RESTORE_STEPS.get(snap.type)
    if builder is None:
        return False
    steps = builder(snap)
    succeeded = bool(steps) and await run_steps(http, steps)
    if not snap.was_off:
        mode = await http.get_json("/mode")
        if isinstance(mode, dict) and mode.get("mode") == "off":
            await http.write_json("/on", {})
    return succeeded


async def restore_with_retries(
    http: DeviceHttp,
    snap: Snapshot,
    retries: int = const.RESTORE_RETRIES,
    interval: float = const.RESTORE_INTERVAL_S,
) -> bool:
    """Retry while the device rejoins the network after its re-pairing."""
    for attempt in range(1, retries + 1):
        if await http.get_json("/mode") is not None and await restore_device(
            http, snap
        ):
            return True
        if attempt < retries:
            await asyncio.sleep(interval)
    return False


# =============================================================================
# Capture
# =============================================================================


@dataclass
class CaptureReport:
    """What happened to one device."""

    hwid: str
    name: str
    ok: bool = False
    # Translation key of what went wrong (or of a warning when ok)
    error: str = ""
    changes: list[str] = field(default_factory=list)
    # None: nothing to restore, True/False: restore result
    restored: bool | None = None
    snapshot: str = ""


def _cloud_status(res: Any) -> int:
    return int(res.get("status", 0)) if isinstance(res, dict) else 0


async def acquire_keys(
    cloud: CloudAccount,
    http: DeviceHttp,
    dev: DeviceKeys,
    keystore: KeyStore,
    snapshots: SnapshotStore,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
) -> CaptureReport:
    """Capture the keys of one device (see the module docstring)."""
    report = CaptureReport(hwid=dev.hwid, name=dev.name or dev.hwid)

    # 1. Snapshot, once
    before = await snapshots.async_pending(dev.hwid)
    if before is None:
        before = await take_snapshot(http, dev)
        if not before.endpoints:
            report.error = "snapshot_failed"
            return report
        dev.backup_file = str(await snapshots.async_save(before))
    else:
        dev.backup_file = str(snapshots.pending_path(dev.hwid))
    report.snapshot = dev.backup_file

    # 2. Delete then create again: the creation answers the keys
    res = await cloud.http_send(f"/device/{dev.hwid}", method="delete")
    if _cloud_status(res) not in DELETE_OK:
        report.error = "cloud_delete_failed"
        return report
    await sleep(const.CLOUD_SETTLE_S)
    res = await cloud.http_send(
        "/device",
        {
            "in_service": True,
            "aquarium_uid": dev.aquarium_uid,
            "name": dev.name,
            "type": dev.type,
            "model": dev.model,
            "hwid": dev.hwid,
        },
        "post",
    )
    created = res.get("json") if isinstance(res, dict) else None
    if not isinstance(created, dict):
        report.error = "cloud_create_failed"
        return report
    api_key = str(created.get("api_key") or "")
    api_secret = str(created.get("api_secret") or "")
    if not api_key or len(api_secret) != 16:
        report.error = "no_credentials"
        return report

    # 3. Store first: a capture must never be lost
    dev.api_key = api_key
    dev.api_secret = api_secret
    dev.mqtt_url = str(created.get("url") or const.NORMAL_MQTT_URL)
    await keystore.async_upsert(dev)
    report.ok = True
    if not await http.set_cloud(dev.mqtt_url, api_key, api_secret):
        report.error = "push_failed"
        return report

    # 4. Compare, and put back what can be
    await sleep(const.DEVICE_SETTLE_S)
    after = await take_snapshot(http, dev)
    if not after.endpoints:
        report.error = "reread_failed"
        return report
    report.changes = diff_snapshots(before, after)
    if report.changes and can_restore(dev.type):
        report.restored = await restore_with_retries(http, before)
    if not report.changes or report.restored:
        await snapshots.async_drop(dev.hwid)
    return report
