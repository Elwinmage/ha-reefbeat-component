"""Text platform for the Red Sea ReefBeat integration.

This module exposes configurable string fields as Home Assistant `text` entities.

Design notes (HA 2025.12):
- Entities are backed by the coordinator cache; we write to the cache on set.
- Avoid `type(x).__name__` checks; use `isinstance`.
- Avoid mutating shared `device_info` dicts; copy and return a new mapping.
- Avoid using `device._hass`; use `self.hass` (provided by Entity base).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from typing import Any, cast

from homeassistant.components.text import TextEntity, TextEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback

# (keep callback import; we’ll use it on the listener)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ReefBeatCoordinator, ReefDoseCoordinator
from .entity import ReefBeatRestoreEntity, RestoreSpec

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Entity descriptions
# -----------------------------------------------------------------------------


@dataclass(kw_only=True, frozen=True)

# =============================================================================
# Classes
# =============================================================================

class ReefBeatTextEntityDescription(TextEntityDescription):
    """Describes a ReefBeat text entity."""

    value_name: str
    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    dependency: str | None = None


@dataclass(kw_only=True, frozen=True)
class ReefDoseTextEntityDescription(ReefBeatTextEntityDescription):
    """Describes a ReefDose per-head text entity."""

    head: int


# -----------------------------------------------------------------------------
# Platform setup
# -----------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up text entities for a config entry."""
    device = cast(ReefBeatCoordinator, hass.data[DOMAIN][config_entry.entry_id])

    entities: list[TextEntity] = []
    _LOGGER.debug("TEXTS")

    if isinstance(device, ReefDoseCoordinator):
        dose_descs: list[ReefDoseTextEntityDescription] = []

        # `heads_nb` may be str/int in some coordinators; normalize to int.
        for head in range(1, int(device.heads_nb) + 1):
            dose_descs.extend(
                [
                    ReefDoseTextEntityDescription(
                        key="new_supplement_brand_name_" + str(head),
                        translation_key="new_supplement_brand_name",
                        value_name="$.local.head."
                        + str(head)
                        + ".new_supplement_brand_name",
                        icon="mdi:domain",
                        entity_category=EntityCategory.CONFIG,
                        dependency="$.local.head." + str(head) + ".new_supplement",
                        head=head,
                    ),
                    ReefDoseTextEntityDescription(
                        key="new_supplement_name_" + str(head),
                        translation_key="new_supplement_name",
                        value_name="$.local.head." + str(head) + ".new_supplement_name",
                        icon="mdi:tag-text-outline",
                        entity_category=EntityCategory.CONFIG,
                        dependency="$.local.head." + str(head) + ".new_supplement",
                        head=head,
                    ),
                    ReefDoseTextEntityDescription(
                        key="new_supplement_display_name_" + str(head),
                        translation_key="new_supplement_display_name",
                        value_name="$.local.head."
                        + str(head)
                        + ".new_supplement_display_name",
                        icon="mdi:tag-text-outline",
                        entity_category=EntityCategory.CONFIG,
                        dependency="$.local.head." + str(head) + ".new_supplement",
                        head=head,
                    ),
                    ReefDoseTextEntityDescription(
                        key="new_supplement_short_name_" + str(head),
                        translation_key="new_supplement_short_name",
                        value_name="$.local.head."
                        + str(head)
                        + ".new_supplement_short_name",
                        icon="mdi:text-short",
                        entity_category=EntityCategory.CONFIG,
                        dependency="$.local.head." + str(head) + ".new_supplement",
                        head=head,
                    ),
                ]
            )

        entities.extend(
            ReefDoseTextEntity(device, description)
            for description in dose_descs
            if description.exists_fn(device)
        )

    async_add_entities(entities, True)


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


# REEFBEAT
class ReefBeatTextEntity(ReefBeatRestoreEntity, TextEntity):  # type: ignore[reportIncompatibleVariableOverride]
    """A ReefBeat text entity backed by the coordinator cache.

    This entity listens to the coordinator's internal listener mechanism rather
    than using `CoordinatorEntity` to avoid MRO/type conflicts with HA stubs.
    """

    _attr_has_entity_name = True

    @staticmethod
    def _restore_value(state: str) -> str:
        return state

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefBeatTextEntityDescription,
    ) -> None:
        ReefBeatRestoreEntity.__init__(
            self,
            device,
            restore=RestoreSpec("_attr_native_value", self._restore_value),
        )
        self._device = device

        # Keep HA's expected type for `entity_description`, store typed description separately.
        self.entity_description = cast(TextEntityDescription, entity_description)
        self._desc: ReefBeatTextEntityDescription = entity_description

        self._device = device
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_available = True

        # Initial state from cache
        self._attr_native_value = cast(
            str | None, self._device.get_data(self._desc.value_name)
        )

    async def async_added_to_hass(self) -> None:
        """Restore last known value and prime from coordinator cache."""
        await super().async_added_to_hass()

        if self._attr_native_value is not None and not self._attr_available:
            self._attr_available = True

        if self._device.last_update_success:
            self._update_val()
            super()._handle_coordinator_update()

    def _update_val(self) -> None:
        #        self._attr_available = True
        self._attr_native_value = cast(
            str | None, self._device.get_data(self._desc.value_name)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update cached `_attr_*` values from coordinator data."""
        self._update_val()
        super()._handle_coordinator_update()

    async def async_set_value(self, value: str) -> None:
        """Set the text value and mirror into the coordinator cache."""
        self._attr_native_value = value
        self._device.set_data(self._desc.value_name, value)
        self._device.async_update_listeners()
        self.async_write_ha_state()

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info

    @cached_property
    def available(self) -> bool:
        if self._desc.dependency is not None:
            return self._device.get_data(self._desc.dependency)
        else:
            return True


# REEFDOSE
class ReefDoseTextEntity(ReefBeatTextEntity):
    """Per-head ReefDose text entity.

    Availability is controlled by an HA bus event emitted elsewhere in the integration
    (typically when the "dependency" select/switch changes).
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefDoseTextEntityDescription,
    ) -> None:
        super().__init__(device, entity_description)
        self._dose_desc: ReefDoseTextEntityDescription = entity_description
        self._head: int = entity_description.head
        self._attr_available = False

    async def async_added_to_hass(self) -> None:
        """Register event listener after HA has set `self.hass`."""
        await super().async_added_to_hass()
        self._attr_available = False
        if self._dose_desc.dependency:
            self.async_on_remove(
                self.hass.bus.async_listen(
                    self._dose_desc.dependency, self._handle_update
                )
            )

    @callback
    def _handle_update(self, event: Any) -> None:
        """Handle updated availability data from the integration."""
        # The integration fires event.data.get("other") as a boolean.
        other = event.data.get("other")
        if isinstance(other, bool):
            self._attr_available = other
        else:
            # Defensive: if payload is malformed, do not crash the entity update loop.
            self._attr_available = bool(other)
        self.async_write_ha_state()

    @cached_property
    def available(self) -> bool:
        return self._attr_available

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return device info extended with the head identifier (non-mutating)."""
        return cast(ReefDoseCoordinator, self._device).head_device_info(self._head)
