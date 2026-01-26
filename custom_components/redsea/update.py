"""Update platform for the Red Sea ReefBeat integration.

Exposes firmware updates as Home Assistant `update` entities.

HA 2025.12 notes:
- Avoid `type(x).__name__` / base-class-name checks; use `isinstance` or Protocols.
- Prefer `entities.extend(...)` over `+= [...]`.
- Do not use protected attributes like `_hass`, `_title`, `_cloud_link`.
- Subscribe to coordinator updates via the coordinator listener mechanism.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ReefBeatCoordinator
from .entity import ReefBeatRestoreEntity

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from .coordinator import (
        ReefBeatCloudCoordinator,
        )
# Protocols (capability-based typing)
from .coordinator import (
    ReefVirtualLedCoordinator,
)

@runtime_checkable

# =============================================================================
# Classes
# =============================================================================

class _CloudLinkedCoordinator(Protocol):
    """Coordinator capability: is linked to cloud data and exposes firmware info."""

    serial: str
    device_info: DeviceInfo
    sw_version: str | None
    latest_firmware_url: str | None

    cloud_coordinator: "ReefBeatCloudCoordinator | None"

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]: ...
    def get_data(self, name: str, use_cache: bool = True) -> Any: ...
    def set_data(self, name: str, value: Any) -> None: ...

    @property
    def cloud_link(self) -> Any: ...

    @property
    def my_api(self) -> Any: ...


# -----------------------------------------------------------------------------
# Entity descriptions
# -----------------------------------------------------------------------------


@dataclass(kw_only=True, frozen=True)
class ReefBeatUpdateEntityDescription(UpdateEntityDescription):
    """Describes a ReefBeat update entity."""

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True

    # JSONPath to the installed firmware version (in the local device cache)
    version_path: str


FIRMWARE_UPDATES: tuple[ReefBeatUpdateEntityDescription, ...] = (
    ReefBeatUpdateEntityDescription(
        key="firmware_update",
        translation_key="firmware_update",
        version_path="$.sources[?(@.name=='/firmware')].data.version",
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
        device_class=UpdateDeviceClass.FIRMWARE,
    ),
)


# -----------------------------------------------------------------------------
# Platform setup
# -----------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up update entities for a config entry."""
    device = cast(ReefBeatCoordinator, hass.data[DOMAIN][config_entry.entry_id])

    entities: list[UpdateEntity] = []
    _LOGGER.debug("UPDATES")

    if isinstance(device, _CloudLinkedCoordinator) and not isinstance(device,ReefVirtualLedCoordinator):
        entities.extend(
            ReefBeatUpdateEntity(device, description)
            for description in FIRMWARE_UPDATES
            if description.exists_fn(device)
        )

    async_add_entities(entities, True)


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


# REEFBEAT
class ReefBeatUpdateEntity(ReefBeatRestoreEntity, UpdateEntity):  # type: ignore[reportIncompatibleVariableOverride]
    """Firmware update entity backed by coordinator + cloud version discovery."""

    _attr_has_entity_name = True
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefBeatUpdateEntityDescription,
    ) -> None:
        ReefBeatRestoreEntity.__init__(self, device)
        self._device = cast(_CloudLinkedCoordinator, device)

        self.entity_description = cast(UpdateEntityDescription, entity_description)
        self._desc: ReefBeatUpdateEntityDescription = entity_description

        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_available = True

        installed = self._get_installed_from_cache()
        self._attr_installed_version = installed
        self._attr_latest_version = self._get_latest_from_cloud() or installed

    def _get_latest_from_cloud(self) -> str | None:
        """Best-effort lookup of latest version from cloud link."""
        if not self._device.latest_firmware_url:
            return None
        link = self._device.cloud_coordinator
        if link is None:
            return None
        new_version = link.get_data(
            "$.sources[?(@.name=='"
            + self._device.latest_firmware_url
            + "')].data.version",
            True,
        )
        return cast(str | None, new_version)

    async def async_added_to_hass(self) -> None:
        """Register coordinator and event listeners after added to HA."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            # Restore versions if we don't have anything yet.
            if (
                not self._attr_installed_version
                and "installed_version" in last_state.attributes
            ):
                self._attr_installed_version = cast(
                    str, last_state.attributes["installed_version"]
                )
            if (
                not self._attr_latest_version
                and "latest_version" in last_state.attributes
            ):
                self._attr_latest_version = cast(
                    str, last_state.attributes["latest_version"]
                )
        # CoordinatorEntity already listens for coordinator updates.
        self.async_on_remove(
            self.hass.bus.async_listen(
                "request_latest_firmware", self._handle_ask_for_latest_firmware
            )
        )
        self._handle_device_update()

    def _get_installed_from_cache(self) -> str | None:
        raw = self._device.get_data(self._desc.version_path, True)
        return cast(str | None, raw) if raw else self._device.sw_version

    @callback
    def _handle_coordinator_update(self) -> None:
        self._handle_device_update()

    @callback
    def _handle_device_update(self) -> None:
        """Update installed/latest versions from cache/cloud."""
        self._attr_installed_version = self._get_installed_from_cache()
        self._attr_latest_version = (
            self._get_latest_from_cloud() or self._attr_installed_version
        )
        self.async_write_ha_state()

    @callback
    def _handle_ask_for_latest_firmware(self, event: Any) -> None:
        """Log latest firmware when asked (debug helper)."""
        device_name = event.data.get("device_name")
        if device_name and device_name != self._attr_unique_id:
            return

        _LOGGER.info(
            "Latest firmware for %s is %s (installed: %s)",
            self._attr_unique_id,
            self._attr_latest_version,
            self._attr_installed_version,
        )

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Trigger firmware update installation on the device."""
        # Device API endpoint is integration-specific; keep as-is but avoid protected attrs.
        await self._device.my_api.press("firmware")

        _LOGGER.info(
            "Installing firmware for %s: %s",
            self._attr_unique_id,
            self.latest_version,
        )

        # Mirror the version into the cache so HA updates quickly
        self._device.set_data(self._desc.version_path, self.latest_version)
        self._attr_installed_version = self.latest_version
        self.async_write_ha_state()

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info
