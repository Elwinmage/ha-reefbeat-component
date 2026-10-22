"""Keys of the devices managed by Poseidon.

Stored with Home Assistant's ``Store`` in ``.storage/redsea.poseidon``,
independently of the Poseidon entry: removing it never deletes keys, since
getting them again means a new destructive capture. Same schema as the
``keystore.json`` of the CLI, so both tools can exchange it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import STORE_KEY, STORE_VERSION


def _when(stamp: str) -> datetime:
    """An ``updated_at``, comparable whatever its offset (oldest if unknown)."""
    parsed = dt_util.parse_datetime(stamp) if stamp else None
    if parsed is None:
        return datetime.min.replace(tzinfo=UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


@dataclass
class DeviceKeys:
    """One device: cloud identity, MQTT credentials and local address."""

    hwid: str
    type: str = ""  # cloud namespace: reef-wave, reef-run...
    model: str = ""
    name: str = ""
    aquarium_uid: str = ""
    ip: str = ""
    mqtt_url: str = ""  # broker the credentials were issued for
    api_key: str = ""  # MQTT password
    api_secret: str = ""  # AES-128 key, 16 characters
    updated_at: str = ""
    backup_file: str = ""  # snapshot taken before the capture
    local_hosted: bool = False  # mirror mode (CLI only for now)

    @property
    def has_keys(self) -> bool:
        return bool(self.api_key and len(self.api_secret) == 16)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceKeys:
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


class KeyStore:
    """Persistent hwid -> DeviceKeys mapping."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, STORE_KEY)
        self.devices: dict[str, DeviceKeys] = {}

    async def async_load(self) -> None:
        raw = await self._store.async_load() or {}
        devices = raw.get("devices") or {}
        self.devices = {
            str(hwid): DeviceKeys.from_dict({**data, "hwid": str(hwid)})
            for hwid, data in devices.items()
            if isinstance(data, dict)
        }

    def as_json(self) -> dict[str, Any]:
        """The CLI keystore format."""
        return {
            "version": STORE_VERSION,
            "updated_at": dt_util.now().isoformat(),
            "devices": {hwid: asdict(dev) for hwid, dev in self.devices.items()},
        }

    async def async_save(self) -> None:
        await self._store.async_save(self.as_json())

    def get(self, hwid: str) -> DeviceKeys | None:
        return self.devices.get(hwid)

    async def async_upsert(self, dev: DeviceKeys) -> None:
        dev.updated_at = dt_util.now().isoformat()
        self.devices[dev.hwid] = dev
        await self.async_save()

    def with_keys(self) -> list[DeviceKeys]:
        return [d for d in self.devices.values() if d.has_keys]

    def merge(self, data: Any) -> tuple[int, int, int]:
        """Merge a keystore in the CLI format, by hardware id.

        A device without keys is skipped, and a stored device is only
        replaced by a more recent record (``updated_at``).
        Returns the numbers of added, updated and skipped devices.

        Raises:
            ValueError: when ``data`` is not a keystore.
        """
        devices = data.get("devices") if isinstance(data, dict) else None
        if not isinstance(devices, dict):
            raise ValueError("not a keystore: no 'devices' mapping")
        added = updated = skipped = 0
        for hwid, record in devices.items():
            if not isinstance(record, dict):
                skipped += 1
                continue
            incoming = DeviceKeys.from_dict(
                {**record, "hwid": str(record.get("hwid") or hwid).lower()}
            )
            current = self.devices.get(incoming.hwid)
            if not incoming.has_keys:
                skipped += 1
            elif current is None:
                self.devices[incoming.hwid] = incoming
                added += 1
            elif current.has_keys and _when(current.updated_at) >= _when(
                incoming.updated_at
            ):
                skipped += 1
            else:
                # Keep what this side knows better than an old export
                incoming.ip = incoming.ip or current.ip
                self.devices[incoming.hwid] = incoming
                updated += 1
        return added, updated, skipped
