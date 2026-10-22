"""Poseidon mode: a transparent MQTT relay between the devices and Red Sea.

See README.md in this folder for the design. This package holds everything
specific to it; the integration only wires the Poseidon config entry in.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import issue_registry as ir

from ..const import DOMAIN
from . import const
from .http_view import PoseidonKeystoreView, PoseidonRescueView
from .manager import Poseidon, get_poseidon, is_poseidon_entry

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.SWITCH]

__all__ = [
    "PLATFORMS",
    "Poseidon",
    "async_register_poseidon_services",
    "async_remove_poseidon",
    "async_setup_poseidon",
    "async_unload_poseidon",
    "get_poseidon",
    "is_poseidon_entry",
]


def async_register_poseidon_services(hass: HomeAssistant) -> None:
    """``redsea.poseidon_export``: the keystore to a file, CLI format; and
    the download views of the options flow (keystore, rescue script)."""
    if hass.http is not None:
        hass.http.register_view(PoseidonKeystoreView())
        hass.http.register_view(PoseidonRescueView())

    async def _export(call: ServiceCall) -> ServiceResponse:
        poseidon = get_poseidon(hass)
        if poseidon is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="poseidon_not_running"
            )
        path = await poseidon.async_export()
        return {"path": str(path), "devices": len(poseidon.keystore.with_keys())}

    hass.services.async_register(
        DOMAIN,
        const.SERVICE_EXPORT,
        _export,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def async_setup_poseidon(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start the relay and create the switches.

    Devices are never touched here: they reconnect on their own once the
    relay listens again (after a restart or a reload).
    """
    poseidon = Poseidon(hass, entry)
    try:
        await poseidon.async_start()
    except OSError as err:
        await poseidon.async_stop()
        ir.async_create_issue(
            hass,
            DOMAIN,
            const.ISSUE_PORT_IN_USE,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=const.ISSUE_PORT_IN_USE,
            translation_placeholders={"port": str(poseidon.port)},
        )
        raise ConfigEntryNotReady(
            f"Poseidon: port {poseidon.port} is not available ({err})"
        ) from err
    ir.async_delete_issue(hass, DOMAIN, const.ISSUE_PORT_IN_USE)
    hass.data[const.DATA_POSEIDON] = poseidon
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _options_updated(_hass: HomeAssistant, _entry: ConfigEntry) -> None:
        # Applied live: restarting the relay would cut every device
        await poseidon.async_apply_options()

    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def async_unload_poseidon(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop the relay; switch every device back only when disabling.

    A reload or a Home Assistant restart unloads the entry too: devices are
    left as they are then, or every update would wear their flash and need
    a manual switch again.
    """
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    poseidon = hass.data.pop(const.DATA_POSEIDON, None)
    if poseidon is None:
        return True
    await poseidon.async_stop()
    poseidon.async_clear_issues()
    if entry.disabled_by is not None:
        await _revert(hass, poseidon)
    return True


async def async_remove_poseidon(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Entry removed: every device back to normal mode. Keys are kept."""
    poseidon = Poseidon(hass, entry)
    await poseidon.async_load()
    await _revert(hass, poseidon)


async def _revert(hass: HomeAssistant, poseidon: Poseidon) -> None:
    failed = await poseidon.async_revert_all()
    if failed:
        _LOGGER.error(
            "Poseidon: could not switch back to normal mode: %s", ", ".join(failed)
        )
        from homeassistant.components import persistent_notification

        persistent_notification.async_create(
            hass,
            "These devices could not be switched back to the Red Sea broker "
            "(unreachable): they stay cut off from the Red Sea cloud until "
            f"switched back. {', '.join(failed)}",
            title="Poseidon",
            notification_id="redsea_poseidon_revert",
        )
