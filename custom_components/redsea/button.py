"""Button platform for the Red Sea ReefBeat integration.

This module defines Home Assistant Button entities and their descriptions for
ReefBeat devices (LED, Mat, ATO) and cloud-linked devices (Wave, Run, Dose).

Buttons are created from `ButtonEntityDescription` dataclasses and wired to
coordinator methods (press, delete, push_values, calibration, etc.).
"""

import inspect
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import cached_property
from typing import Any, cast

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import (
    HomeAssistant,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    WAVE_SCHEDULE_PATH,
    WAVES_DATA_NAMES,
)
from .coordinator import (
    ReefATOCoordinator,
    ReefBeatCoordinator,
    ReefBeatCloudCoordinator,
    ReefDoseCoordinator,
    ReefLedCoordinator,
    ReefLedG2Coordinator,
    ReefMatCoordinator,
    ReefRunCoordinator,
    ReefVirtualLedCoordinator,
    ReefWaveCoordinator,
)
from .supplements_list import SUPPLEMENTS

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Helpers
# =============================================================================


def _get_supplement(uid: str) -> dict[str, Any]:
    """Return the supplement dict for a given uid.

    Raises:
        ValueError: If the uid is not present in `SUPPLEMENTS`.
    """
    supplement = next((item for item in SUPPLEMENTS if item.get("uid") == uid), None)
    if supplement is None:
        raise ValueError(f"Unknown supplement uid: {uid}")
    return supplement


def _get_supplement_bundle(uid: str) -> dict[str, Any]:
    """Return the supplement 'bundle' dict for a given uid.

    Raises:
        ValueError: If the uid is unknown or does not contain a valid bundle dict.
    """
    supplement = _get_supplement(uid)
    bundle = supplement.get("bundle")
    if not isinstance(bundle, dict):
        raise ValueError(f"Supplement uid '{uid}' has no valid bundle")
    return cast(dict[str, Any], bundle)


def _add_described_entities(
    entities: list[ButtonEntity],
    device: Any,
    entity_cls: Callable[[Any, Any], ButtonEntity],
    descriptions: tuple[Any, ...],
) -> None:
    """Append entities for descriptions whose `exists_fn()` returns True."""
    entities.extend(
        entity_cls(device, description)
        for description in descriptions
        if description.exists_fn(device)
    )


@dataclass(kw_only=True, frozen=True)

# =============================================================================
# Classes
# =============================================================================

class ReefBeatButtonEntityDescription(ButtonEntityDescription):
    """Entity description for generic ReefBeat buttons.

    Used for devices where a simple `press_fn(device)` callback is sufficient.
    """

    exists_fn: Callable[[ReefBeatCoordinator], bool] = lambda _: True
    press_fn: (
        Callable[[ReefBeatCoordinator], StateType | Awaitable[StateType]] | None
    ) = None


@dataclass(kw_only=True, frozen=True)
class ReefDoseButtonEntityDescription(ButtonEntityDescription):
    """Entity description for ReefDose head-specific buttons.

    Includes per-head metadata and an `action` field interpreted by
    `ReefDoseButtonEntity.async_press()`.
    """

    exists_fn: Callable[[ReefDoseCoordinator], bool] = lambda _: True
    action: list[str] | str = "manual"
    delete: bool = False
    head: int = 0


@dataclass(kw_only=True, frozen=True)
class ReefRunButtonEntityDescription(ButtonEntityDescription):
    """Entity description for ReefRun pump-specific buttons."""

    exists_fn: Callable[[ReefRunCoordinator], bool] = lambda _: True
    press_fn: (
        Callable[[ReefRunCoordinator], StateType | Awaitable[StateType]] | None
    ) = None
    pump: int = 0


@dataclass(kw_only=True, frozen=True)
class ReefWaveButtonEntityDescription(ButtonEntityDescription):
    """Entity description for ReefWave (schedule/preview) buttons."""

    exists_fn: Callable[[ReefWaveCoordinator], bool] = lambda _: True
    press_fn: (
        Callable[[ReefWaveCoordinator], StateType | Awaitable[StateType]] | None
    ) = None


FETCH_CONFIG_BUTTON: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key="fetch_config",
        translation_key="fetch_config",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.fetch_config(),
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
    ),
)

FIRMWARE_UPDATE_BUTTON: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key="firmware_update",
        translation_key="firmware_update",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("firmware"),
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
        entity_registry_visible_default=False,
    ),
    ReefBeatButtonEntityDescription(
        key="reset",
        translation_key="reset",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("reset"),
        icon="mdi:restart",
        entity_category=EntityCategory.CONFIG,
    ),
)

LED_BUTTONS: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key="led_identify",
        translation_key="led_identify",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("identify"),
        icon="mdi:lightbulb-question-outline",
        entity_category=EntityCategory.CONFIG,
    ),
)

PREVIEW_BUTTONS: tuple[ReefWaveButtonEntityDescription, ...] = (
    ReefWaveButtonEntityDescription(
        key="preview_start",
        translation_key="preview_start",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.push_values(source="/preview", method="post"),
        icon="mdi:play-speed",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefWaveButtonEntityDescription(
        key="preview_stop",
        translation_key="preview_stop",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.delete("/preview"),
        icon="mdi:stop-circle-outline",
        entity_category=EntityCategory.CONFIG,
    ),
)

MAT_BUTTONS: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key="advance",
        translation_key="advance",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("advance"),
        icon="mdi:paper-roll-outline",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatButtonEntityDescription(
        key="new_roll",
        translation_key="new_roll",
        exists_fn=lambda _: True,
        press_fn=lambda device: cast(ReefMatCoordinator, device).new_roll(),
        icon="mdi:paper-roll-outline",
        entity_category=EntityCategory.CONFIG,
    ),
)

EMERGENCY_BUTTON: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key="delete_emergency",
        translation_key="delete_emergency",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.delete("/emergency"),
        icon="mdi:alert",
        entity_category=EntityCategory.CONFIG,
    ),
)

ATO_BUTTONS: tuple[ReefBeatButtonEntityDescription, ...] = (
    ReefBeatButtonEntityDescription(
        key="fill",
        translation_key="fill",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("manual-pump"),
        icon="mdi:water-pump",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatButtonEntityDescription(
        key="stop_fill",
        translation_key="stop_fill",
        exists_fn=lambda _: True,
        press_fn=lambda device: device.press("stop"),
        icon="mdi:water-pump-off",
        entity_category=EntityCategory.CONFIG,
    ),
    ReefBeatButtonEntityDescription(
        key="resume",
        translation_key="resume",
        exists_fn=lambda _: True,
        press_fn=lambda device: cast(ReefATOCoordinator, device).resume(),
        icon="mdi:play-circle-outline",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ReefBeat button entities for a config entry."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[ButtonEntity] = []
    _LOGGER.debug("BUTTONS")
    if isinstance(device, (ReefLedCoordinator, ReefLedG2Coordinator)):
        _add_described_entities(entities, device, ReefBeatButtonEntity, LED_BUTTONS)

    if isinstance(device, ReefMatCoordinator):
        _add_described_entities(entities, device, ReefBeatButtonEntity, MAT_BUTTONS)
        _add_described_entities(
            entities, device, ReefBeatButtonEntity, EMERGENCY_BUTTON
        )

    elif isinstance(device, ReefATOCoordinator):
        _add_described_entities(entities, device, ReefBeatButtonEntity, ATO_BUTTONS)

    elif isinstance(device, ReefWaveCoordinator):
        _add_described_entities(entities, device, ReefWaveButtonEntity, PREVIEW_BUTTONS)
        WAVE_SAVE_PREVIEW_BUTTONS: tuple[ReefWaveButtonEntityDescription, ...] = (
            ReefWaveButtonEntityDescription(
                key="preview_save",
                translation_key="preview_save",
                exists_fn=lambda _: True,
                press_fn=lambda device: device.delete("/preview"),
                icon="mdi:content-save-cog",
                entity_category=EntityCategory.CONFIG,
            ),
            ReefWaveButtonEntityDescription(
                key="preview_set_from_current",
                translation_key="preview_set_from_current",
                exists_fn=lambda _: True,
                press_fn=None,
                icon="mdi:content-save-cog",
                entity_category=EntityCategory.CONFIG,
            ),
        )
        _add_described_entities(
            entities, device, ReefWaveButtonEntity, WAVE_SAVE_PREVIEW_BUTTONS
        )

    elif isinstance(device, ReefRunCoordinator):
        _add_described_entities(
            entities, device, ReefBeatButtonEntity, EMERGENCY_BUTTON
        )
        if not device.my_api.live_config_update:
            for pump in range(1, 3):
                CONFIG_PREVIEW_BUTTONS: tuple[ReefRunButtonEntityDescription, ...] = (
                    ReefRunButtonEntityDescription(
                        key="fetch_config_" + str(pump),
                        translation_key="fetch_config",
                        icon="mdi:update",
                        press_fn=lambda device, pump=pump: device.fetch_config(),
                        entity_category=EntityCategory.CONFIG,
                        pump=pump,
                    ),
                    ReefRunButtonEntityDescription(
                        key="preview_start_" + str(pump),
                        translation_key="preview_start",
                        exists_fn=lambda _: True,
                        press_fn=lambda device, pump=pump: device.push_values(
                            source="/preview", method="post", pump=pump
                        ),
                        icon="mdi:play-speed",
                        entity_category=EntityCategory.CONFIG,
                        pump=pump,
                    ),
                    ReefRunButtonEntityDescription(
                        key="preview_stop_" + str(pump),
                        translation_key="preview_stop",
                        exists_fn=lambda _: True,
                        press_fn=lambda device, pump=pump: device.delete("/preview"),
                        icon="mdi:stop-circle-outline",
                        entity_category=EntityCategory.CONFIG,
                        pump=pump,
                    ),
                    ReefRunButtonEntityDescription(
                        key="preview_save_" + str(pump),
                        translation_key="preview_save",
                        exists_fn=lambda _: True,
                        press_fn=lambda device, pump=pump: device.delete("/preview"),
                        icon="mdi:content-save-cog",
                        entity_category=EntityCategory.CONFIG,
                        pump=pump,
                    ),
                )
                _add_described_entities(
                    entities, device, ReefRunButtonEntity, CONFIG_PREVIEW_BUTTONS
                )

    elif isinstance(device, ReefDoseCoordinator):
        db: list[ReefDoseButtonEntityDescription] = []
        for head in range(1, device.heads_nb + 1):
            db.append(
                ReefDoseButtonEntityDescription(
                    key="set_supplement_head_" + str(head),
                    translation_key="set_supplement",
                    icon="mdi:bottle-soda",
                    action="setup-supplement",
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                    entity_registry_visible_default=False,
                )
            )
            db.append(
                ReefDoseButtonEntityDescription(
                    key="start_calibration_head_" + str(head),
                    translation_key="start_calibration",
                    icon="mdi:play-box-edit-outline",
                    action=["start-calibration", "calibration/start"],
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                    entity_registry_visible_default=False,
                )
            )
            db.append(
                ReefDoseButtonEntityDescription(
                    key="set_calibration_value_head_" + str(head),
                    translation_key="set_calibration_value",
                    icon="mdi:vector-polyline-edit",
                    action="end-calibration",
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                    entity_registry_visible_default=False,
                )
            )
            db.append(
                ReefDoseButtonEntityDescription(
                    key="test_calibration_head_" + str(head),
                    translation_key="test_calibration",
                    icon="mdi:test-tube",
                    action="calibration-manual",
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                    entity_registry_visible_default=False,
                )
            )
            db.append(
                ReefDoseButtonEntityDescription(
                    key="end_calibration_head_" + str(head),
                    translation_key="end_calibration",
                    icon="mdi:stop-circle-outline",
                    action=["end-setup"],
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                    entity_registry_visible_default=False,
                )
            )
            db.append(
                ReefDoseButtonEntityDescription(
                    key="manual_head_" + str(head),
                    translation_key="manual_head",
                    icon="mdi:cup-water",
                    action="manual",
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                )
            )
            db.append(
                ReefDoseButtonEntityDescription(
                    key="start_priming_" + str(head),
                    translation_key="start_priming",
                    icon="mdi:cup-water",
                    action=["start-calibration", "priming/start"],
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                    entity_registry_visible_default=False,
                )
            )
            db.append(
                ReefDoseButtonEntityDescription(
                    key="stop_priming_" + str(head),
                    translation_key="stop_priming",
                    icon="mdi:cup-off",
                    action=["priming/stop", "end-priming"],
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                    entity_registry_visible_default=False,
                )
            )
            db.append(
                ReefDoseButtonEntityDescription(
                    key="delete_supplement_" + str(head),
                    translation_key="delete_supplement",
                    icon="mdi:delete",
                    action="/head/" + str(head) + "/settings",
                    delete=True,
                    entity_category=EntityCategory.CONFIG,
                    head=head,
                )
            )

            if not device.my_api.live_config_update:
                CONFIG_BUTTONS: tuple[ReefDoseButtonEntityDescription, ...] = (
                    ReefDoseButtonEntityDescription(
                        key="fetch_config_" + str(head),
                        translation_key="fetch_config",
                        icon="mdi:update",
                        action="fetch_config",
                        entity_category=EntityCategory.CONFIG,
                        head=head,
                    ),
                )
                _add_described_entities(
                    entities, device, ReefDoseButtonEntity, CONFIG_BUTTONS
                )

        entities.extend(ReefDoseButtonEntity(device, description) for description in db)

    if not device.my_api.live_config_update:
        _add_described_entities(
            entities, device, ReefBeatButtonEntity, FETCH_CONFIG_BUTTON
        )

    if not isinstance(device, ReefBeatCloudCoordinator) and not isinstance(
        device, ReefVirtualLedCoordinator
    ):
        _add_described_entities(
            entities, device, ReefBeatButtonEntity, FIRMWARE_UPDATE_BUTTON
        )
    async_add_entities(entities, True)


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


# REEFBEAT
class ReefBeatButtonEntity(ButtonEntity):
    """Generic button entity for ReefBeat coordinators.

    The action is provided by `ReefBeatButtonEntityDescription.press_fn`.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefBeatCoordinator,
        entity_description: ReefBeatButtonEntityDescription,
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_device_info = device.device_info

    @property
    def desc(self) -> ReefBeatButtonEntityDescription:
        return cast(ReefBeatButtonEntityDescription, self.entity_description)

    async def async_press(self) -> None:
        if self.desc.press_fn is None:
            _LOGGER.debug("No press_fn for %s", self.desc.key)
            return
        result = self.desc.press_fn(self._device)
        if inspect.isawaitable(result):
            await result


# REEFDOSE
class ReefDoseButtonEntity(ButtonEntity):
    """Button entity for ReefDose, scoped to a dosing head.

    The behavior is driven by `ReefDoseButtonEntityDescription.action` and
    may call calibration / priming / deletion endpoints.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefDoseCoordinator,
        entity_description: ReefDoseButtonEntityDescription,
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._head = entity_description.head

    @property
    def desc(self) -> ReefDoseButtonEntityDescription:
        return cast(ReefDoseButtonEntityDescription, self.entity_description)

    async def async_press(self) -> None:
        """Handle the button press."""
        desc = self.desc
        if desc.delete:
            bundled_heads = self._device.get_data(
                "$.sources[?(@.name=='/dashboard')].data.bundled_heads"
            )
            if bundled_heads:
                await self._device.delete("/head/settings")
            else:
                await self._device.delete(str(desc.action))
        elif desc.translation_key == "set_supplement":
            await self._set_supplement()
        elif desc.action == "fetch_config":
            await self._device.fetch_config("/head/" + str(self._head) + "/settings")
        elif desc.action == "end-calibration":
            payload: dict[str, Any] = {
                "volume": self._device.get_data(
                    "$.local.head." + str(self._head) + ".calibration_dose"
                )
            }
            await self._device.calibration(str(desc.action), self._head, payload)
        elif desc.action == "calibration-manual":
            await self._device.calibration(str(desc.action), self._head, {"volume": 4})
        elif isinstance(desc.action, list):
            for act in desc.action:
                await self._device.calibration(act, self._head, {})
        else:
            await self._device.press(desc.action, self._head)
        await self._device.async_request_refresh()

    async def _set_supplement(self) -> None:
        desc = self.desc
        uid = self._device.get_data(
            "$.local.head." + str(self._head) + ".new_supplement"
        )
        _LOGGER.debug("Set supplement %s", uid)
        if uid == "redsea-reefcare":
            payload: dict[str, Any] = _get_supplement_bundle(uid)
            await self._device.set_bundle(payload)
            return
        elif uid == "other":
            payload: dict[str, Any] = {
                "uid": str(uuid.uuid4()),
                "name": self._device.get_data(
                    "$.local.head." + str(self._head) + ".new_supplement_name"
                ),
                "display name": None,
                "short_name": self._device.get_data(
                    "$.local.head." + str(self._head) + ".new_supplement_short_name"
                ),
                "brand_name": self._device.get_data(
                    "$.local.head." + str(self._head) + ".new_supplement_brand_name"
                ),
                "type": None,
                "concentration": None,
                "made_by_redsea": False,
            }
            for label in ["name", "short_name", "brand_name"]:
                if len(payload[label]) == 0:
                    raise Exception(
                        "Setting supplement: " + label + " text box can not be empty"
                    )
        else:
            payload = _get_supplement(uid)

        _LOGGER.debug("_set_supplement %s %s", desc.action, payload)
        action = desc.action
        if isinstance(action, (list, tuple)):
            for act in action:
                await self._device.calibration(str(act), self._head, payload)
        else:
            await self._device.calibration(str(action), self._head, payload)

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return per-head device info for ReefDose."""
        return self._device.head_device_info(self._head)


# REEFRUN
class ReefRunButtonEntity(ButtonEntity):
    """Button entity for ReefRun, scoped to a pump channel.

    Provides preview/save actions and a fetch-config button when live config
    update is disabled.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefRunCoordinator,
        entity_description: ReefRunButtonEntityDescription,
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_device_info = device.device_info
        self._pump = entity_description.pump

    @property
    def desc(self) -> ReefRunButtonEntityDescription:
        return cast(ReefRunButtonEntityDescription, self.entity_description)

    async def async_press(self) -> None:
        """Handle the button press."""
        desc = self.desc

        if desc.key.startswith("preview_save_"):
            _LOGGER.debug("Saving current preview in prog")
            preview_intensity = self._device.get_data(
                "$.sources[?(@.name=='/preview')].data.pump_" + str(self._pump) + ".ti"
            )
            # stop preview
            if (
                self._device.get_data(
                    "$.sources[?(@.name=='/dashboard')].data.pump_"
                    + str(self._pump)
                    + ".state"
                )
                == "preview"
            ):
                _LOGGER.debug("Stopping preview")
                await self._device.delete("/preview")

            await self._device.set_pump_intensity(self._pump, int(preview_intensity))
            self.async_write_ha_state()
            await self._device.push_values(source="/pump/settings", pump=self._pump)
            await self._device.async_request_refresh()

        elif desc.key.startswith("fetch_config_") or desc.key == "fetch_config":
            await self._device.fetch_config()

        else:
            if desc.press_fn is None:
                _LOGGER.debug("No press_fn for %s", desc.key)
                return
            result = desc.press_fn(self._device)
            if inspect.isawaitable(result):
                await result

        # Refresh preview/dashboard state when starting or stopping preview
        if desc.key.startswith(("preview_start_", "preview_stop_")):
            _LOGGER.debug("Refresh preview state")
            await self._device.async_request_refresh(source="/dashboard")

    @cached_property  # type: ignore[reportIncompatibleVariableOverride]
    def device_info(self) -> DeviceInfo:
        """Return per-pump device info for ReefRun."""
        return self._device.pump_device_info(self._pump)


# REEFWAVE
class ReefWaveButtonEntity(ButtonEntity):
    """Button entity for ReefWave schedule preview actions."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: ReefWaveCoordinator,
        entity_description: ReefWaveButtonEntityDescription,
    ) -> None:
        """Set up the instance."""
        self._device = device
        self.entity_description = entity_description
        self._attr_available = True
        self._attr_unique_id = f"{device.serial}_{entity_description.key}"
        self._attr_device_info = device.device_info

    @property
    def desc(self) -> ReefWaveButtonEntityDescription:
        return cast(ReefWaveButtonEntityDescription, self.entity_description)

    async def async_press(self) -> None:
        """Handle the button press."""
        desc = self.desc

        # Special-case: cannot preview "No Wave"
        if (
            desc.key == "preview_start"
            and self._device.get_data("$.sources[?(@.name=='/preview')].data.type")
            == "nw"
        ):
            _LOGGER.info("'No Wave' is the only type of waves that can't be previewed")
            return

        if desc.key == "preview_set_from_current":
            _LOGGER.debug("Set Preview from Current values")
            for dn in WAVES_DATA_NAMES:
                v = self._device.get_current_value(WAVE_SCHEDULE_PATH, dn)
                if v is not None:
                    self._device.set_data(
                        "$.sources[?(@.name=='/preview')].data." + dn, v
                    )
            self._device.async_update_listeners()
            self.async_write_ha_state()
            return

        if desc.key == "preview_save":
            await self._device.set_wave()
            for dn in WAVES_DATA_NAMES:
                v = self._device.get_data("$.sources[?(@.name=='/preview')].data." + dn)
                if v is not None:
                    self._device.set_current_value(WAVE_SCHEDULE_PATH, dn, v)

            if (
                self._device.get_data("$.sources[?(@.name=='/preview')].data.type")
                == "nw"
            ):
                self._device.set_current_value(WAVE_SCHEDULE_PATH, "name", "No Wave")

            self._device.async_update_listeners()
            self.async_write_ha_state()
            await self._device.async_request_refresh()
            return

        # Default: call press_fn if provided
        if desc.press_fn is None:
            _LOGGER.debug("No press_fn for %s", desc.key)
            return

        result = desc.press_fn(self._device)
        if inspect.isawaitable(result):
            await result

        # Update device mode for preview start/stop
        if desc.key == "preview_start":
            self._device.set_data("$.sources[?(@.name=='/mode')].data.mode", "preview")
        elif desc.key == "preview_stop":
            self._device.set_data("$.sources[?(@.name=='/mode')].data.mode", "auto")

        await self._device.async_request_refresh()
