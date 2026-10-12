"""Entities of the dose regulation of the ReefDose heads (dose_regulation.py).

Per head, on the head's device:

- select  regulation_mode            off / assisted / brine
- select  regulation_parameter       parameter regulated in assisted mode
- select  brine_salinity_source      salinity sensor of the brine mode
- number  regulation_target ... salinity_check_tolerance (settings)
- number  regulation_measurement     test result to record
- button  regulation_record          record the test result
- button  regulation_apply           send the proposed dose to the doser
- button  regulation_dismiss         forget the proposed dose
- sensor  regulation_status          state of the regulation (enum)
- sensor  regulation_proposed_dose   proposed daily dose (mL)
- sensor  regulation_consumption     consumption (unit/day) or salt loss
- sensor  regulation_last_measurement  last test result, with the history
- sensor  regulation_tank_volume_used  water volume used and its source
- sensor  brine_salinity             salinity average the brine works on
- sensor  brine_daily_volume         brine planned per day (mL)
- binary_sensor regulation_alarm     problem, with the reason

They read and write the doser's RegulationStore, not the doser itself
(except the "apply" and the brine doses).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,  # pyright: ignore[reportPrivateImportUsage]
    BinarySensorEntity,
)
from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity

from .dose_regulation import (
    ALARMS,
    MODES,
    PARAMETER_OPTIONS,
    PARAMETERS,
    REGULATOR_ATTR,
    SETTING_BOUNDS,
    STATUSES,
    DoseRegulator,
    HeadState,
    salinity_unit_supported,
)

# Value of the source select when no sensor is chosen
NO_SOURCE = "none"
# Measurements and dose changes listed in the attributes (card chart)
HISTORY_SHOWN = 60


class RegulationEntity(Entity):
    """An entity of the regulation of one head."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device: Any, head: int, key: str) -> None:
        self._device = device
        self._head = head
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{device.serial}_{key}_head_{head}"
        self._attr_device_info = device.head_device_info(head)
        # Stable role for the card and blueprints (see ReefRoleMixin)
        self._attr_extra_state_attributes = {"reef_role": key}
        self._unsub: Callable[[], None] | None = None

    @property
    def regulator(self) -> DoseRegulator:
        return getattr(self._device, REGULATOR_ATTR)

    @property
    def state_data(self) -> HeadState:
        return self.regulator.head_state(self._head)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = self.regulator.store.async_add_listener(self._changed)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()

    @callback
    def _changed(self) -> None:
        self.async_write_ha_state()

    async def _async_set(self, key: str, value: Any) -> None:
        try:
            await self.regulator.async_set(self._head, key, value)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err


# =============================================================================
# Settings
# =============================================================================


class RegulationSelect(RegulationEntity, SelectEntity):
    """Mode or parameter of the regulation."""

    def __init__(
        self, device: Any, head: int, key: str, setting: str, options: list[str]
    ) -> None:
        super().__init__(device, head, key)
        self._setting = setting
        self._attr_options = list(options)

    @property
    def current_option(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        return str(getattr(self.state_data.settings, self._setting))

    async def async_select_option(self, option: str) -> None:
        await self._async_set(self._setting, option)


class RegulationModeSelect(RegulationSelect):
    """Regulation mode, the entry point of the feature (not a config).

    Offers the modes of the head's supplement: the brine supplement is
    regulated on the salinity, any other on a test result. A mode set before
    the supplement changed stays shown, so the change is visible.
    """

    _attr_entity_category = None
    _attr_icon = "mdi:auto-mode"

    @property
    def options(self) -> list[str]:  # pyright: ignore[reportIncompatibleVariableOverride]
        offered = self.regulator.modes(self._head)
        current = self.state_data.settings.mode
        return offered if current in offered else [*offered, current]


class SalinitySourceSelect(RegulationEntity, SelectEntity):
    """Salinity sensor driving the brine regulation.

    Offers every sensor whose unit is a salinity or a conductivity.
    """

    _attr_icon = "mdi:water-percent"

    @property
    def options(self) -> list[str]:  # pyright: ignore[reportIncompatibleVariableOverride]
        found = sorted(
            state.entity_id
            for state in self.hass.states.async_all("sensor")
            if salinity_unit_supported(state.attributes.get("unit_of_measurement"))
        )
        current = self.state_data.settings.salinity_source
        if current and current not in found:
            found.append(current)
        return [NO_SOURCE, *found]

    @property
    def current_option(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self.state_data.settings.salinity_source or NO_SOURCE

    async def async_select_option(self, option: str) -> None:
        await self._async_set("salinity_source", "" if option == NO_SOURCE else option)


class RegulationNumber(RegulationEntity, NumberEntity):
    """A numeric setting of the regulation."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        device: Any,
        head: int,
        key: str,
        setting: str,
        step: float,
        unit: str | None = None,
        icon: str = "mdi:tune-vertical",
    ) -> None:
        super().__init__(device, head, key)
        self._setting = setting
        self._attr_native_min_value, self._attr_native_max_value = SETTING_BOUNDS[
            setting
        ]
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self) -> float:  # pyright: ignore[reportIncompatibleVariableOverride]
        return float(getattr(self.state_data.settings, self._setting))

    async def async_set_native_value(self, value: float) -> None:
        await self._async_set(self._setting, value)


class ParameterNumber(RegulationNumber):
    """Setting expressed in the unit of the regulated parameter."""

    def __init__(self, *args: Any, per: str = "", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._per = per

    @property
    def native_unit_of_measurement(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        return PARAMETERS[self.state_data.settings.parameter].unit + self._per

    @property
    def native_step(self) -> float:  # pyright: ignore[reportIncompatibleVariableOverride]
        return PARAMETERS[self.state_data.settings.parameter].step


class MeasurementNumber(ParameterNumber):
    """Test result typed in before pressing "record" (not a config)."""

    _attr_entity_category = None


class TankVolumeNumber(RegulationNumber):
    """Water volume set by the user; 0 to find it automatically."""

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        volume, source = self.regulator.volume(self._head)
        return {"reef_role": self._key, "volume_used": volume, "volume_source": source}


# =============================================================================
# Actions
# =============================================================================


class RegulationButton(RegulationEntity, ButtonEntity):
    """Record a test result, apply or dismiss the proposed dose."""

    _attr_entity_category = None

    def __init__(self, device: Any, head: int, key: str, icon: str) -> None:
        super().__init__(device, head, key)
        self._attr_icon = icon

    async def async_press(self) -> None:
        regulator = self.regulator
        try:
            if self._key == "regulation_record":
                await regulator.async_record(self._head)
            elif self._key == "regulation_apply":
                await regulator.async_apply(self._head)
            else:
                await regulator.async_dismiss(self._head)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err


# =============================================================================
# Results
# =============================================================================


class RegulationSensor(RegulationEntity, SensorEntity):
    """Result of the regulation."""

    _attr_entity_category = None

    def __init__(
        self,
        device: Any,
        head: int,
        key: str,
        icon: str,
        value: Callable[[DoseRegulator, int], Any],
        unit: Callable[[DoseRegulator, int], str | None] | None = None,
        attributes: Callable[[DoseRegulator, int], dict[str, Any]] | None = None,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
        precision: int | None = None,
    ) -> None:
        super().__init__(device, head, key)
        self._attr_icon = icon
        self._value = value
        self._unit = unit
        self._attributes = attributes
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_suggested_display_precision = precision

    @property
    def native_value(self) -> Any:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._value(self.regulator, self._head)

    @property
    def native_unit_of_measurement(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._unit(self.regulator, self._head) if self._unit else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        extra = self._attributes(self.regulator, self._head) if self._attributes else {}
        return {"reef_role": self._key, **extra}


class StatusSensor(RegulationSensor):
    """State of the regulation (translated enum)."""

    def __init__(
        self, device: Any, head: int, key: str, icon: str, options: list[str]
    ) -> None:
        super().__init__(
            device,
            head,
            key,
            icon,
            lambda r, h: r.head_state(h).status,
            attributes=_status_attributes,
            device_class=SensorDeviceClass.ENUM,
        )
        self._attr_options = list(options)


class AlarmBinarySensor(RegulationEntity, BinarySensorEntity):
    """A problem the regulation cannot solve by itself."""

    _attr_entity_category = None
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        return self.state_data.alarm in ALARMS

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        return {"reef_role": self._key, "reason": self.state_data.alarm}


# ---- value helpers ------------------------------------------------------


def _status_attributes(regulator: DoseRegulator, head: int) -> dict[str, Any]:
    state = regulator.head_state(head)
    settings = state.settings
    return {
        "mode": settings.mode,
        "parameter": settings.parameter,
        "unit": PARAMETERS[settings.parameter].unit,
        "target": settings.target,
        **state.details,
    }


def _proposed(regulator: DoseRegulator, head: int) -> float | None:
    proposal = regulator.head_state(head).proposal
    return proposal.dose if proposal else None


def _proposal_attributes(regulator: DoseRegulator, head: int) -> dict[str, Any]:
    proposal = regulator.head_state(head).proposal
    out = proposal.as_dict() if proposal else {}
    out.pop("dose", None)
    out["current_dose"] = regulator.current_dose(head)
    return out


def _consumption(regulator: DoseRegulator, head: int) -> float | None:
    state = regulator.head_state(head)
    if state.settings.mode == "brine":
        loss = regulator.loss(head)
        return None if loss is None else round(loss, 3)
    last: dict[str, Any] = state.details.get("last_proposal") or {}
    value = last.get("consumption")
    return value if isinstance(value, (int, float)) else None


def _consumption_unit(regulator: DoseRegulator, head: int) -> str:
    return PARAMETERS[regulator.head_state(head).settings.parameter].unit + "/d"


def _last_measurement(regulator: DoseRegulator, head: int) -> float | None:
    state = regulator.head_state(head)
    same = [m for m in state.measurements if m.parameter == state.settings.parameter]
    return same[-1].value if same else None


def _measurement_unit(regulator: DoseRegulator, head: int) -> str:
    return PARAMETERS[regulator.head_state(head).settings.parameter].unit


def _history(regulator: DoseRegulator, head: int) -> dict[str, Any]:
    """Measurements, dose changes and dosed volumes, for the card's chart."""
    state = regulator.head_state(head)
    same = [m for m in state.measurements if m.parameter == state.settings.parameter]
    last = same[-1] if same else None
    days = sorted(state.daily)[-HISTORY_SHOWN:]
    return {
        "measured_at": last.at.isoformat() if last else None,
        "suspect": last.suspect if last else None,
        "measurements": [m.as_dict() for m in same[-HISTORY_SHOWN:]],
        "dose_changes": state.history[-HISTORY_SHOWN:],
        "daily_volumes": {day: state.daily[day] for day in days},
        "last_check": (
            state.last_check.isoformat() if state.last_check is not None else None
        ),
    }


def _volume_used(regulator: DoseRegulator, head: int) -> float | None:
    return regulator.volume(head)[0]


def _volume_source(regulator: DoseRegulator, head: int) -> dict[str, Any]:
    return {"source": regulator.volume(head)[1]}


def _salinity(regulator: DoseRegulator, head: int) -> float | None:
    """The 24 h average, else (too few samples yet) the current reading."""
    value = regulator.average(head)
    if value is None:
        value = regulator.read_salinity(head)
    return None if value is None else round(value, 2)


def _salinity_attributes(regulator: DoseRegulator, head: int) -> dict[str, Any]:
    current = regulator.read_salinity(head)
    return {
        "current": None if current is None else round(current, 2),
        "samples": len(regulator.head_state(head).samples),
        "averaged": regulator.average(head) is not None,
    }


def _brine_volume(regulator: DoseRegulator, head: int) -> float | None:
    value = regulator.head_state(head).details.get("plan_ml_day")
    return round(value, 1) if isinstance(value, (int, float)) else None


# =============================================================================
# Builder
# =============================================================================


def _head_entities(device: Any, head: int, platform: str) -> list[Any]:
    builders: dict[str, Callable[[], list[Any]]] = {
        "select": lambda: [
            RegulationModeSelect(device, head, "regulation_mode", "mode", MODES),
            RegulationSelect(
                device,
                head,
                "regulation_parameter",
                "parameter",
                PARAMETER_OPTIONS,
            ),
            SalinitySourceSelect(device, head, "brine_salinity_source"),
        ],
        "number": lambda: [
            ParameterNumber(
                device, head, "regulation_target", "target", 0.01, icon="mdi:target"
            ),
            ParameterNumber(
                device,
                head,
                "regulation_potency",
                "potency",
                0.001,
                icon="mdi:flask",
                per="/mL/100L",
            ),
            ParameterNumber(
                device,
                head,
                "regulation_tolerance",
                "tolerance",
                0.01,
                icon="mdi:plus-minus-variant",
            ),
            TankVolumeNumber(
                device,
                head,
                "regulation_tank_volume",
                "tank_volume",
                1,
                UnitOfVolume.LITERS,
                "mdi:fishbowl-outline",
            ),
            RegulationNumber(
                device,
                head,
                "regulation_max_change",
                "max_change_pct",
                1,
                PERCENTAGE,
                "mdi:arrow-expand-vertical",
            ),
            RegulationNumber(
                device,
                head,
                "regulation_correction_days",
                "correction_days",
                1,
                UnitOfTime.DAYS,
                "mdi:calendar-range",
            ),
            RegulationNumber(
                device,
                head,
                "brine_concentration",
                "brine_concentration",
                1,
                "g/L",
                "mdi:shaker-outline",
            ),
            RegulationNumber(
                device,
                head,
                "brine_max_rise",
                "brine_max_rise",
                0.05,
                "ppt/d",
                "mdi:chart-line-variant",
            ),
            RegulationNumber(
                device,
                head,
                "brine_doses_per_day",
                "brine_doses_per_day",
                1,
                None,
                "mdi:counter",
            ),
            RegulationNumber(
                device,
                head,
                "salinity_check_tolerance",
                "salinity_check_tolerance",
                0.1,
                "ppt",
                "mdi:plus-minus-variant",
            ),
            MeasurementNumber(
                device,
                head,
                "regulation_measurement",
                "measurement",
                0.01,
                icon="mdi:test-tube",
            ),
        ],
        "button": lambda: [
            RegulationButton(device, head, "regulation_record", "mdi:clipboard-check"),
            RegulationButton(device, head, "regulation_apply", "mdi:check-bold"),
            RegulationButton(device, head, "regulation_dismiss", "mdi:close-thick"),
        ],
        "sensor": lambda: [
            StatusSensor(
                device, head, "regulation_status", "mdi:state-machine", STATUSES
            ),
            RegulationSensor(
                device,
                head,
                "regulation_proposed_dose",
                "mdi:cup-water",
                _proposed,
                lambda r, h: UnitOfVolume.MILLILITERS,
                _proposal_attributes,
                precision=1,
            ),
            RegulationSensor(
                device,
                head,
                "regulation_consumption",
                "mdi:trending-down",
                _consumption,
                _consumption_unit,
                precision=3,
            ),
            RegulationSensor(
                device,
                head,
                "regulation_last_measurement",
                "mdi:test-tube",
                _last_measurement,
                _measurement_unit,
                _history,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            RegulationSensor(
                device,
                head,
                "regulation_tank_volume_used",
                "mdi:fishbowl-outline",
                _volume_used,
                lambda r, h: UnitOfVolume.LITERS,
                _volume_source,
            ),
            RegulationSensor(
                device,
                head,
                "brine_salinity",
                "mdi:water-percent",
                _salinity,
                lambda r, h: "ppt",
                _salinity_attributes,
                state_class=SensorStateClass.MEASUREMENT,
                precision=2,
            ),
            RegulationSensor(
                device,
                head,
                "brine_daily_volume",
                "mdi:cup-water",
                _brine_volume,
                lambda r, h: UnitOfVolume.MILLILITERS,
                precision=1,
            ),
        ],
        "binary_sensor": lambda: [AlarmBinarySensor(device, head, "regulation_alarm")],
    }
    build = builders.get(platform)
    return build() if build else []


def regulation_entities(device: Any, platform: str) -> list[Any]:
    """Regulation entities of a platform, for a doser holding a regulator."""
    if not isinstance(getattr(device, REGULATOR_ATTR, None), DoseRegulator):
        return []
    out: list[Any] = []
    for head in device.regulation.store.heads:
        out.extend(_head_entities(device, head, platform))
    return out
