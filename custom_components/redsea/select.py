"""Select entities for the Red Sea ReefBeat integration.

This module registers Home Assistant `select` entities for supported devices:
- ReefMat (model/position)
- ReefLED (mode)
- ReefDose (per-head supplement selection)
- ReefWave (preview wave settings)
- ReefRun (skimmer model per pump)
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import cached_property
from typing import Any, cast

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    HW_MAT_MODEL,
    LED_MODE_INTERNAL_NAME,
    LED_MODES,
    MAT_MODEL_INTERNAL_NAME,
    MAT_POSITION_INTERNAL_NAME,
    SKIMMER_MODELS,
    WAVE_DIRECTIONS,
    WAVE_TYPES,
)
from .coordinator import (
    ReefBeatCoordinator,
    ReefDoseCoordinator,
    ReefLedCoordinator,
    ReefLedG2Coordinator,
    ReefMatCoordinator,
    ReefRunCoordinator,
    ReefVirtualLedCoordinator,
    ReefWaveCoordinator,
)
from .entity import ReefBeatRestoreEntity, RestoreSpec
from .i18n import translate, translate_list
from .supplements_list import SUPPLEMENTS as SUPPLEMENTS_LIST

# Keep the imported constant intact; use a local name for the sorted view.
_SORTED_SUPPLEMENTS: list[dict[str, Any]] = sorted(
    SUPPLEMENTS_LIST, key=lambda d: d.get("fullname", "")
)

_LOGGER = logging.getLogger(__name__)


# Entity descriptions
@dataclass(kw_only=True, frozen=True)

# =============================================================================
# Classes
# =============================================================================

class ReefBeatSelectEntityDescription(SelectEntityDescription):
    """Describes a generic ReefBeat select entity."""

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    entity_registry_visible_default: bool = True
    value_name: str = ""
    # Must match HA's SelectEntityDescription.options type.
    options: list[str] | None = None
    method: str = "put"


@dataclass(kw_only=True, frozen=True)
class ReefRunSelectEntityDescription(SelectEntityDescription):
    """Describes a ReefRun select entity (scoped to a pump)."""

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    entity_registry_visible_default: bool = True
    value_name: str = ""
    pump: int = 0
    options: list[str] | None = None
    method: str = "put"


@dataclass(kw_only=True, frozen=True)
class ReefWaveSelectEntityDescription(SelectEntityDescription):
    """Describes a ReefWave preview select entity."""

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = ""
    options: list[str] | None = None
    method: str = "post"


@dataclass(kw_only=True, frozen=True)
class ReefDoseSelectEntityDescription(SelectEntityDescription):
    """Describes a ReefDose select entity (scoped to a head)."""

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    value_name: str = ""
    options: list[str] | None = None
    head: int = 0
    method: str = "post"


DescriptionT = (
    ReefBeatSelectEntityDescription
    | ReefRunSelectEntityDescription
    | ReefWaveSelectEntityDescription
    | ReefDoseSelectEntityDescription
)


# Select definitions
MAT_SELECTS: tuple[ReefBeatSelectEntityDescription, ...] = (
    ReefBeatSelectEntityDescription(
        key="model",
        translation_key="model",
        value_name=MAT_MODEL_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:movie-roll",
        options=list(HW_MAT_MODEL),
        entity_category=EntityCategory.CONFIG,
        entity_registry_visible_default=False,
    ),
    ReefBeatSelectEntityDescription(
        key="position",
        translation_key="position",
        value_name=MAT_POSITION_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:set-left-right",
        options=["left", "right"],
        entity_category=EntityCategory.CONFIG,
        entity_registry_visible_default=False,
    ),
)

LED_SELECTS: tuple[ReefBeatSelectEntityDescription, ...] = (
    ReefBeatSelectEntityDescription(
        key="mode",
        translation_key="mode",
        value_name=LED_MODE_INTERNAL_NAME,
        exists_fn=lambda _: True,
        icon="mdi:auto-mode",
        options=list(LED_MODES),
        entity_category=EntityCategory.CONFIG,
        method="post",
    ),
)

# TODO : Add speed change management
#  labels: enhancement, rsdose


# Setup
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ReefBeat select entities from a config entry."""
    device = cast(ReefBeatCoordinator, hass.data[DOMAIN][config_entry.entry_id])

    entities: list[SelectEntity] = []
    _LOGGER.debug("Setting up select entities")

    # Keep this as a single chain; device coordinators are mutually exclusive.
    if isinstance(device, ReefMatCoordinator):
        entities.extend(
            ReefBeatSelectEntity(device, description)
            for description in MAT_SELECTS
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefDoseCoordinator):
        dn: list[ReefDoseSelectEntityDescription] = []
        for head in range(1, int(device.heads_nb) + 1):
            dn.append(
                ReefDoseSelectEntityDescription(
                    key="supplements_" + str(head),
                    translation_key="supplements",
                    value_name="$.local.head." + str(head) + ".new_supplement",
                    exists_fn=lambda _: True,
                    icon="mdi:shaker",
                    options=translate_list(_SORTED_SUPPLEMENTS, "fullname"),
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                )
            )

        entities.extend(
            ReefDoseSelectEntity(device, description)
            for description in dn
            if description.exists_fn(device)
        )

    elif isinstance(
        device, (ReefLedCoordinator, ReefLedG2Coordinator, ReefVirtualLedCoordinator)
    ):
        entities.extend(
            ReefBeatSelectEntity(device, description)
            for description in LED_SELECTS
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefWaveCoordinator):
        waves: tuple[ReefWaveSelectEntityDescription, ...] = (
            ReefWaveSelectEntityDescription(
                key="preview_wave_type",
                translation_key="preview_wave_type",
                value_name="$.sources[?(@.name=='/preview')].data.type",
                exists_fn=lambda _: True,
                icon="mdi:wave",
                options=WAVE_TYPES,
                entity_category=EntityCategory.CONFIG,
            ),
            ReefWaveSelectEntityDescription(
                key="preview_wave_direction",
                translation_key="preview_wave_direction",
                value_name="$.sources[?(@.name=='/preview')].data.direction",
                exists_fn=lambda _: True,
                icon="mdi:waves-arrow-right",
                options=WAVE_DIRECTIONS,
                entity_category=EntityCategory.CONFIG,
            ),
        )
        entities.extend(
            ReefWaveSelectEntity(device, description)
            for description in waves
            if description.exists_fn(device)
        )

    elif isinstance(device, ReefRunCoordinator):
        ds: list[ReefRunSelectEntityDescription] = []
        for pump in range(1, 3):
            if (
                device.get_data(
                    "$.sources[?(@.name=='/pump/settings')].data.pump_"
                    + str(pump)
                    + ".type"
                )
                == "skimmer"
            ):
                ds.append(
                    ReefRunSelectEntityDescription(
                        key="model_skimmer_pump_" + str(pump),
                        translation_key="model",
                        value_name="$.sources[?(@.name=='/pump/settings')].data.pump_"
                        + str(pump)
                        + ".model",
                        exists_fn=lambda _: True,
                        icon="mdi:raspberry-pi",
                        options=list(SKIMMER_MODELS),
                        entity_category=EntityCategory.CONFIG,
                        pump=pump,
                        method="put",
                    )
                )

        entities.extend(
            ReefRunSelectEntity(device, description)
            for description in ds
            if description.exists_fn(device)
        )

    async_add_entities(entities, True)


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


# REEFBEAT
class ReefBeatSelectEntity(ReefBeatRestoreEntity, SelectEntity):  # type: ignore[reportIncompatibleVariableOverride]
    """Generic ReefBeat-backed select entity.

    We intentionally do not subclass `CoordinatorEntity` (see number.py rationale).
    Instead we subscribe to the coordinator via `async_add_listener`.
    """

    _attr_has_entity_name = True

    @staticmethod
    def _restore_value(state: str) -> str:
        return state

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: DescriptionT,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(
            device,
            restore=RestoreSpec("_attr_current_option", self._restore_value),
        )
        self._device = device
        self.entity_description = entity_description
        self._description: DescriptionT = entity_description
        self._attr_available = True

        self._attr_unique_id = f"{device.serial}_{self._description.key}"

        self._value_name = cast(str, getattr(self._description, "value_name", ""))
        self._attr_current_option = self._device.get_data(self._value_name)

        self._source = self._extract_source_from_value_name(self._value_name)
        self._method = cast(str, getattr(self._description, "method", "put"))

    async def async_added_to_hass(self) -> None:
        """Restore last known option and prime from coordinator cache."""
        await super().async_added_to_hass()

        if self._attr_current_option is not None and not self._attr_available:
            self._attr_available = True

        if self._device.last_update_success:
            self._update_val()
            super()._handle_coordinator_update()

    def _update_val(self) -> None:
        self._attr_current_option = self._device.get_data(self._value_name)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update cached `_attr_*` values from coordinator data."""
        self._update_val()
        super()._handle_coordinator_update()

    @staticmethod
    def _extract_source_from_value_name(value_name: str) -> str | None:
        """Extract the `/source` segment from a JSONPath value_name like:
        "$.sources[?(@.name=='/pump/settings')].data.foo"
        """
        marker = "@.name=='"
        i = value_name.find(marker)
        if i == -1:
            return None
        start = i + len(marker)
        end = value_name.find("'", start)
        if end == -1:
            return None
        return value_name[start:end]

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option and push to the device when applicable."""
        self._attr_current_option = option
        self._device.set_data(self._value_name, option)
        self.async_write_ha_state()

        if self._source is None:
            return

        await self._device.push_values(self._source, self._method)

        refresh = getattr(self._device, "async_request_refresh", None)
        if callable(refresh):
            await cast(Callable[[], Awaitable[None]], refresh)()

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device.device_info


# REEFRUN
class ReefRunSelectEntity(ReefBeatSelectEntity):
    """Select entity for ReefRun (per-pump setting)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefRunSelectEntityDescription,
    ) -> None:
        """Initialize the per-pump select."""
        super().__init__(device, entity_description)
        self._pump: int = entity_description.pump

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option and push pump-specific settings."""
        self._attr_current_option = option
        self._device.set_data(self._value_name, option)
        self.async_write_ha_state()

        # Base coordinator doesn't type `pump`, but ReefRun coordinator supports it.
        await cast(Any, self._device).push_values(
            source="/pump/settings", method="put", pump=self._pump
        )

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return device info extended with the pump identifier."""
        return cast(ReefRunCoordinator, self._device).pump_device_info(self._pump)


# REEFDOSE
class ReefDoseSelectEntity(ReefBeatSelectEntity):
    """Select entity for ReefDose (supplement selection per head)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefDoseSelectEntityDescription,
    ) -> None:
        """Initialize the per-head supplement select."""
        super().__init__(device, entity_description)
        self._head: int = entity_description.head
        self._attr_current_option = translate(
            self._device.get_data(self._value_name),
            "fullname",
            dictionary=_SORTED_SUPPLEMENTS,
            src_lang="uid",
        )
        self._attr_options = list(getattr(self._description, "options", None) or []) + [
            "other"
        ]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_available = True
        value = self._device.get_data(self._value_name)
        if value == "other":
            self._attr_current_option = "other"
        else:
            self._attr_current_option = translate(
                self._device.get_data(self._value_name),
                "fullname",
                dictionary=_SORTED_SUPPLEMENTS,
                src_lang="uid",
            )
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Update the selected supplement and update local cache."""
        hass = self._device.hass

        self._attr_current_option = option
        event_type = self._value_name

        if option == "other":
            value = "other"
            hass.bus.fire(event_type, {"other": True})
        else:
            value = translate(
                option, "uid", dictionary=_SORTED_SUPPLEMENTS, src_lang="fullname"
            )
            hass.bus.fire(event_type, {"other": False})

        _LOGGER.debug("Setting new supplement %s", value)
        self._device.set_data(self._value_name, value)
        self.async_write_ha_state()

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return device info extended with the head identifier."""
        return cast(ReefDoseCoordinator, self._device).head_device_info(self._head)


# REEFWAVE
class ReefWaveSelectEntity(ReefBeatSelectEntity):
    """Select entity for ReefWave preview values."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefWaveSelectEntityDescription,
    ) -> None:
        """Initialize the preview select."""
        super().__init__(device, entity_description)
        self._attr_current_option = self._device.get_data(self._value_name)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._handle_device_update()

    @callback
    def _handle_device_update(self) -> None:
        """Sync HA state from coordinator cached data."""
        self._attr_current_option = self._device.get_data(self._value_name)
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Update the preview setting locally (and notify listeners)."""
        self._attr_current_option = option
        value = option
        self._device.set_data(self._value_name, value)

        # Preview changes are local; update listeners without pushing to the device.
        self._device.async_update_listeners()
        self.async_write_ha_state()
