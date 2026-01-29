"""Shared entity base classes for the Red Sea ReefBeat integration.

This module standardizes entity structure across platforms:

- Use Home Assistant's CoordinatorEntity everywhere (best practice).
- Add an optional RestoreEntity helper so platforms can restore last state at startup
  without re-implementing boilerplate.

Strict typing note:
CoordinatorEntity and Entity define `available` with different descriptor types in
some HA type stubs. Multiple inheritance can trigger Pylance errors even though
runtime behavior is correct. To keep strict typing happy, we explicitly override
`available` here with a simple `@property` returning `bool`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Generic, TypeVar

from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ReefBeatCoordinator

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)

# =============================================================================
# Classes
# =============================================================================

class RestoreSpec(Generic[_T]):
    """Describe how to restore a single value from the last state."""

    # Name of the `_attr_*` attribute to set, e.g. "_attr_native_value" or "_attr_is_on".
    attr_name: str
    # Convert last_state.state (string) into the desired type.
    parser: Callable[[str], _T]


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------


# REEFBEAT
class ReefBeatEntity(CoordinatorEntity[ReefBeatCoordinator]):
    """CoordinatorEntity base for all entities."""


# RESTORE
class ReefBeatRestoreEntity(ReefBeatEntity, RestoreEntity):
    """CoordinatorEntity + RestoreEntity with a small standardized restore helper."""

    def __init__(
        self,
        coordinator: ReefBeatCoordinator,
        *,
        restore: RestoreSpec[Any] | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._restore_spec = restore

    @cached_property
    def available(self) -> bool:  # type: ignore[override]
        # Use CoordinatorEntity's behavior (based on coordinator success) but provide
        # a plain `property` to satisfy strict type checkers.
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if self._restore_spec is None:
            return

        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        if last_state.state in ("unknown", "unavailable"):
            return

        try:
            restored = self._restore_spec.parser(last_state.state)
        except Exception:
            # Best-effort restore only; coordinator update will correct shortly.
            return

        setattr(self, self._restore_spec.attr_name, restored)
