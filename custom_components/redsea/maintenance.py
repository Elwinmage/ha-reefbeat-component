"""Maintenance tracking for Red Sea ReefBeat devices.

This module centralises:

- The static catalogue of maintenance tasks for each supported hardware model
  (see ``TASKS`` and ``tasks_for(...)``).
- The persistent storage of "last reset" timestamps via Home Assistant's
  ``helpers.storage.Store`` (one JSON file per config entry, under
  ``.storage/redsea_maintenance_<entry_id>``).
- The helpers exposed to entities (button, number) to read/write maintenance
  state and compute derived values such as ``days_left`` and ``overdue``.

Design notes
------------
- One ``MaintenanceStore`` per config entry, created in ``async_setup_entry``
  and attached to the coordinator as ``coordinator.maintenance`` so platforms
  can fetch it without going through ``hass.data`` again.
- A maintenance "instance" is identified by a triple
  ``(device_serial, sub_id, task_key)``. ``sub_id`` is the head id for RSDOSE,
  the pump id for RSRUN, or ``0`` for whole-device tasks.
- Per-instance interval (in days) is also stored here, so the number entity
  is a thin wrapper. Falls back to ``task.default_days`` when not set.
- Listeners are notified on every reset / interval change so dependent
  entities (the button's computed attributes) refresh immediately.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

# Storage format: bump when the JSON shape changes incompatibly.
STORAGE_VERSION: Final[int] = 1
STORAGE_KEY_TPL: Final[str] = "redsea_maintenance_{entry_id}"

# Stable role prefix for the entity attribute `reef_role`, used by the
# blueprint and the custom card to detect maintenance entities.
ROLE_PREFIX: Final[str] = "maint_"


# =============================================================================
# Task catalogue
# =============================================================================


@dataclass(frozen=True, slots=True)
class MaintenanceTask:
    """Definition of a single maintenance task.

    Attributes
    ----------
    key:
        Stable identifier, used in the entity unique_id and the storage key.
        Must not change once released, or users will lose their reset history.
    translation_key:
        translation_key suffix used both for entity naming and for the
        ``reef_role`` attribute exposed to templates. The mixin reads the
        entity's ``translation_key`` directly, so this value flows naturally.
    default_days / min_days / max_days:
        Interval bounds in days, used to populate the number entity. The
        catalogue widens the manufacturer's recommended ranges by +/-1 unit.
    unit:
        Display unit shown on the configuration number entity:
        "weeks" or "months". Storage stays in days for consistent
        `days_left` calculations across the blueprint and the card.
        Conversion uses 7 days/week and 30 days/month.
    applies_to_sub:
        For multi-device coordinators (RSDOSE heads, RSRUN pumps), set to:
          - "head" to instantiate one task per head
          - "pump_return" to instantiate only for pumps whose type == "return"
          - "pump_skimmer" to instantiate only for pumps whose type == "skimmer"
          - None for a single instance attached to the main device.
    """

    key: str
    translation_key: str
    default_days: int
    min_days: int
    max_days: int
    applies_to_sub: str | None = None
    # MDI icon shown on the button entity; defaults to a generic wrench.
    icon: str = "mdi:wrench-check"
    # Display unit on the configuration number entity. "weeks" or "months".
    unit: str = "weeks"


# Catalogue per hardware model id (matches CONFIG_FLOW_HW_MODEL values).
# Ranges below correspond to manufacturer recommendations widened by +/-1
# unit (see README). Defaults are the median of the widened range.
TASKS: Final[dict[str, tuple[MaintenanceTask, ...]]] = {
    # --- RSATO+ -------------------------------------------------------------
    "RSATO+": (
        MaintenanceTask(
            key="ato_ec_sensor",
            translation_key="maint_ato_ec_sensor",
            default_days=42,  # 6 weeks (median of 3-9w)
            min_days=21,
            max_days=63,
            icon="mdi:water-check",
            unit="weeks",
        ),
        MaintenanceTask(
            key="ato_return_pump",
            translation_key="maint_ato_return_pump",
            default_days=135,  # ~4.5 months (median of 2-7m)
            min_days=60,
            max_days=210,
            icon="mdi:pump",
            unit="months",
        ),
    ),
    # --- RSDOSE (heads) -----------------------------------------------------
    # The "monthly visual check" is intentionally omitted (informal task,
    # poor fit for a button). RSDOSE "recalibration" is omitted because the
    # device already exposes `last_calibration` natively.
    "RSDOSE2": (
        MaintenanceTask(
            key="dose_heads_replace",
            translation_key="maint_dose_heads_replace",
            default_days=450,  # 15 months (median of 11-19m)
            min_days=330,
            max_days=570,
            applies_to_sub="head",
            icon="mdi:hose",
            unit="months",
        ),
    ),
    "RSDOSE4": (
        MaintenanceTask(
            key="dose_heads_replace",
            translation_key="maint_dose_heads_replace",
            default_days=450,
            min_days=330,
            max_days=570,
            applies_to_sub="head",
            icon="mdi:hose",
            unit="months",
        ),
    ),
    # --- RSRUN (per pump, type-dependent) -----------------------------------
    "RSRUN": (
        # Return pump tasks
        MaintenanceTask(
            key="run_pump_motor",
            translation_key="maint_run_pump_motor",
            default_days=135,
            min_days=60,
            max_days=210,
            applies_to_sub="pump_return",
            icon="mdi:engine",
            unit="months",
        ),
        MaintenanceTask(
            key="run_pump_strainer",
            translation_key="maint_run_pump_strainer",
            default_days=42,
            min_days=21,
            max_days=63,
            applies_to_sub="pump_return",
            icon="mdi:filter-variant",
            unit="weeks",
        ),
        # Skimmer pump tasks
        MaintenanceTask(
            key="run_skim_venturi",
            translation_key="maint_run_skim_venturi",
            default_days=35,  # 5 weeks (median of 3-7w)
            min_days=21,
            max_days=49,
            applies_to_sub="pump_skimmer",
            icon="mdi:weather-windy",
            unit="weeks",
        ),
        MaintenanceTask(
            key="run_skim_rotor",
            translation_key="maint_run_skim_rotor",
            default_days=135,
            min_days=60,
            max_days=210,
            applies_to_sub="pump_skimmer",
            icon="mdi:fan",
            unit="months",
        ),
    ),
    # --- RSWAVE -------------------------------------------------------------
    "RSWAVE25": (
        MaintenanceTask(
            key="wave_rotor_cages",
            translation_key="maint_wave_rotor_cages",
            default_days=60,  # 2 months (median of 1-3m, floored at 1m)
            min_days=30,
            max_days=90,
            icon="mdi:fan",
            unit="months",
        ),
    ),
    "RSWAVE45": (
        MaintenanceTask(
            key="wave_rotor_cages",
            translation_key="maint_wave_rotor_cages",
            default_days=60,
            min_days=30,
            max_days=90,
            icon="mdi:fan",
            unit="months",
        ),
    ),
    # --- RSMAT --------------------------------------------------------------
    "RSMAT": (
        MaintenanceTask(
            key="mat_carbon_replace",
            translation_key="maint_mat_carbon_replace",
            default_days=25,  # median of 2-5 weeks
            min_days=14,
            max_days=35,
            icon="mdi:filter",
            unit="weeks",
        ),
    ),
}

# RSLED is added programmatically below to share the same tasks across all
# RSLED hardware ids (G1, G2, virtual).
_RSLED_TASKS: tuple[MaintenanceTask, ...] = (
    MaintenanceTask(
        key="led_lens",
        translation_key="maint_led_lens",
        default_days=21,  # 3 weeks (median of 1-5w)
        min_days=7,
        max_days=35,
        icon="mdi:spray-bottle",
        unit="weeks",
    ),
    MaintenanceTask(
        key="led_fan",
        translation_key="maint_led_fan",
        default_days=180,  # 6 months (single value widened to 5-7m)
        min_days=150,
        max_days=210,
        icon="mdi:fan",
        unit="months",
    ),
)


def register_led_tasks(led_hw_ids: tuple[str, ...]) -> None:
    """Register the shared RSLED task list against every RSLED hw_id.

    Called once from __init__ to avoid hardcoding the list of RSLED model
    ids here (kept in const.py as the single source of truth).
    """
    for hw_id in led_hw_ids:
        TASKS.setdefault(hw_id, _RSLED_TASKS)


def tasks_for(hw_model: str) -> tuple[MaintenanceTask, ...]:
    """Return the maintenance task list for a hardware model, or empty."""
    return TASKS.get(hw_model, ())


# =============================================================================
# Persistent storage
# =============================================================================


# Storage shape (JSON):
# {
#   "instances": {
#     "<serial>:<sub_id>:<task_key>": {
#       "last_reset": "2025-12-15T10:30:00+00:00",  # ISO-8601 UTC
#       "interval_days": 60                          # optional override
#     },
#     ...
#   }
# }


def _instance_id(serial: str, sub_id: int, task_key: str) -> str:
    """Build the storage key for a maintenance instance."""
    return f"{serial}:{sub_id}:{task_key}"


@dataclass(slots=True)
class MaintenanceState:
    """In-memory state for a single maintenance instance."""

    last_reset: datetime | None = None
    interval_days: int | None = None  # None means "use task.default_days"


class MaintenanceStore:
    """Persistent maintenance state for one config entry.

    Wraps ``helpers.storage.Store`` with a typed API and a tiny listener
    mechanism so entities can refresh when state changes.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TPL.format(entry_id=entry_id)
        )
        self._data: dict[str, MaintenanceState] = {}
        self._listeners: dict[str, list[Callable[[], None]]] = {}
        self._loaded = False

    async def async_load(self) -> None:
        """Load persisted state (no-op if already loaded).

        Section: loading / saving.
        """
        if self._loaded:
            return
        raw = await self._store.async_load() or {}
        instances = raw.get("instances", {})
        for iid, payload in instances.items():
            self._data[iid] = MaintenanceState(
                last_reset=_parse_dt(payload.get("last_reset")),
                interval_days=payload.get("interval_days"),
            )
        self._loaded = True
        _LOGGER.debug("MaintenanceStore loaded %d instances", len(self._data))

    async def _async_save(self) -> None:
        out_instances: dict[str, dict[str, Any]] = {}
        for iid, state in self._data.items():
            entry: dict[str, Any] = {}
            if state.last_reset is not None:
                entry["last_reset"] = state.last_reset.isoformat()
            if state.interval_days is not None:
                entry["interval_days"] = state.interval_days
            if entry:
                out_instances[iid] = entry
        await self._store.async_save({"instances": out_instances})

    # ---- public read API -------------------------------------------------

    def get_state(self, serial: str, sub_id: int, task_key: str) -> MaintenanceState:
        """Return the state for an instance (auto-created if absent)."""
        iid = _instance_id(serial, sub_id, task_key)
        state = self._data.get(iid)
        if state is None:
            state = MaintenanceState()
            self._data[iid] = state
        return state

    def get_last_reset(
        self, serial: str, sub_id: int, task_key: str
    ) -> datetime | None:
        return self.get_state(serial, sub_id, task_key).last_reset

    def get_interval(
        self, serial: str, sub_id: int, task_key: str, default: int
    ) -> int:
        val = self.get_state(serial, sub_id, task_key).interval_days
        return val if val is not None else default

    # ---- public write API ------------------------------------------------

    async def async_reset(self, serial: str, sub_id: int, task_key: str) -> datetime:
        """Mark a maintenance task done now, persist, and notify listeners."""
        now = datetime.now(timezone.utc)
        state = self.get_state(serial, sub_id, task_key)
        state.last_reset = now
        await self._async_save()
        self._notify(_instance_id(serial, sub_id, task_key))
        return now

    async def async_set_interval(
        self, serial: str, sub_id: int, task_key: str, days: int
    ) -> None:
        """Override the interval for an instance, persist, and notify."""
        state = self.get_state(serial, sub_id, task_key)
        state.interval_days = int(days)
        await self._async_save()
        self._notify(_instance_id(serial, sub_id, task_key))

    # ---- listener plumbing ----------------------------------------------

    @callback
    def async_add_listener(
        self, serial: str, sub_id: int, task_key: str, cb: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a no-arg callback for changes to a specific instance.

        Returns an unsubscribe callable.
        """
        iid = _instance_id(serial, sub_id, task_key)
        self._listeners.setdefault(iid, []).append(cb)

        def _unsub() -> None:
            lst = self._listeners.get(iid)
            if lst and cb in lst:
                lst.remove(cb)

        return _unsub

    def _notify(self, iid: str) -> None:
        for cb in list(self._listeners.get(iid, [])):
            try:
                cb()
            except Exception:  # pragma: no cover - defensive
                _LOGGER.exception("MaintenanceStore listener raised")


# =============================================================================
# Derived calculations (pure helpers, no side effects)
# =============================================================================


def compute_days_left(
    last_reset: datetime | None, interval_days: int, now: datetime | None = None
) -> int | None:
    """Compute remaining days before the task becomes overdue.

    Returns ``None`` if no reset has ever been recorded (the task is
    considered "pending first reset" - the UI should show it as such rather
    than as overdue, since the user may have just installed the integration).
    Returns a negative number when overdue.
    """
    if last_reset is None:
        return None
    ref = now or datetime.now(timezone.utc)
    elapsed = (ref - last_reset).total_seconds() / 86400.0
    # Floor: a partially-used day still counts. Use int() with sign handling.
    remaining = interval_days - elapsed
    return int(remaining) if remaining >= 0 else -int(-remaining + 0.999999)


def is_overdue(
    last_reset: datetime | None, interval_days: int, now: datetime | None = None
) -> bool:
    """Return True if the task is past its interval."""
    dl = compute_days_left(last_reset, interval_days, now)
    return dl is not None and dl < 0


def _parse_dt(value: Any) -> datetime | None:
    """Parse an ISO-8601 string into an aware datetime, or return None."""
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
