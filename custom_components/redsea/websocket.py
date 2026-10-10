"""WebSocket commands of the Red Sea integration.

`redsea/aquariums` lists the aquariums of every ReefBeat cloud account with
the Home Assistant devices that belong to them. The aquarium view of
ha-reef-card (with the reeftank integration) uses it to pre-fill a new
aquarium and to filter its device tree; the join between the cloud device
list and the device registry is done here so the card does not repeat it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import websocket_command
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import ReefBeatCloudCoordinator

# Home Assistant validates with probatio, voluptuous being only an alias of it
# at runtime (2026.9), and types its WebSocket helpers with probatio schemas
# since 2026.10. Older versions only have voluptuous.
if TYPE_CHECKING:
    import probatio as vol
else:
    try:
        import probatio as vol
    except ImportError:  # pragma: no cover - depends on the installed HA version
        import voluptuous as vol

_AQUARIUMS = "$.sources[?(@.name=='/aquarium')].data"
_DEVICES = "$.sources[?(@.name=='/device')].data"

# Feeding shortcuts of an aquarium (switch.py: shortcut_feeding_1..3)
_FEEDING_SHORTCUTS = (1, 2, 3)


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _dimensions(aquarium: dict[str, Any]) -> dict[str, float] | None:
    """Tank dimensions in cm: length = X (front), width = Y (depth)."""
    dims = {k: _number(aquarium.get(k)) for k in ("length", "width", "height")}
    if any(v is None for v in dims.values()):
        return None
    return {k: round(v, 2) for k, v in dims.items() if v is not None}


def cloud_aquariums(hass: HomeAssistant) -> list[dict[str, Any]]:
    """The aquariums of every cloud account, with their HA devices."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    result: list[dict[str, Any]] = []
    for coordinator in list(hass.data.get(DOMAIN, {}).values()):
        if not isinstance(coordinator, ReefBeatCloudCoordinator):
            continue
        aquariums = coordinator.get_data(_AQUARIUMS, True)
        devices = coordinator.get_data(_DEVICES, True)
        if not isinstance(aquariums, list):
            continue
        devices = devices if isinstance(devices, list) else []
        for aquarium in aquariums:
            if not isinstance(aquarium, dict) or not aquarium.get("uid"):
                continue
            uid = str(aquarium["uid"])
            device_ids: list[str] = []
            for device in devices:
                if not isinstance(device, dict) or device.get("aquarium_uid") != uid:
                    continue
                entry = dev_reg.async_get_device(
                    identifiers={(DOMAIN, str(device.get("hwid", "")))}
                )
                if entry is not None:
                    device_ids.append(entry.id)
            feeding = [
                entity_id
                for n in _FEEDING_SHORTCUTS
                if (
                    entity_id := ent_reg.async_get_entity_id(
                        "switch",
                        DOMAIN,
                        f"{coordinator.serial}_{uid}_shortcut_feeding_{n}",
                    )
                )
            ]
            result.append(
                {
                    "provider": DOMAIN,
                    "account": coordinator.title,
                    "uid": uid,
                    "name": str(aquarium.get("name") or uid),
                    "system_model": aquarium.get("system_model"),
                    "system_series": aquarium.get("system_series"),
                    "system_type": aquarium.get("system_type"),
                    "dimensions_cm": _dimensions(aquarium),
                    "water_volume": aquarium.get("water_volume"),
                    "net_water_volume": aquarium.get("net_water_volume"),
                    "measuring_unit": aquarium.get("measuring_unit"),
                    "device_ids": device_ids,
                    "feeding_entities": feeding,
                }
            )
    return result


@websocket_command({vol.Required("type"): "redsea/aquariums"})
@callback
def ws_aquariums(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """List the cloud aquariums and their devices."""
    connection.send_result(msg["id"], cloud_aquariums(hass))


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    """Register the commands (once, at integration setup)."""
    async_register_command(hass, ws_aquariums)
