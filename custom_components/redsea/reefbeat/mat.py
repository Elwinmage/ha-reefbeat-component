"""ReefBeat ReefMat API wrapper.

Provides helpers for ReefMat-specific endpoints and local state, including
starting a new roll based on the configured device model.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from ..const import (
    MAT_MAX_ROLL_DIAMETERS,
    MAT_MIN_ROLL_DIAMETER,
    MAT_ROLL_THICKNESS,
    MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME,
)
from .api import ReefBeatAPI

_LOGGER = logging.getLogger(__name__)


class ReefMatAPI(ReefBeatAPI):
    """Access to ReefMat information and commands."""

    def __init__(self, ip: str, live_config_update: bool) -> None:
        """Initialize the ReefMat API wrapper.

        Ensures the configuration source exists and that local state contains
        a default for the started roll diameter.
        """
        super().__init__(ip, live_config_update)

        # Ensure configuration source exists
        self.data["sources"].insert(
            len(self.data["sources"]),
            {"name": "/configuration", "type": "config", "data": ""},
        )

        # Preserve any existing keys in local, but ensure started_roll_diameter exists
        local_any = self.data.get("local")
        if not isinstance(local_any, dict):
            self.data["local"] = {}
            local_any = self.data["local"]

        local = cast(dict[str, Any], local_any)
        local.setdefault("started_roll_diameter", MAT_MIN_ROLL_DIAMETER)

    @staticmethod
    def _as_float(value: Any, default: float) -> float:
        """Coerce a value to float if it is numeric; otherwise return a default.

        Notes:
            - Treats bool as non-numeric to avoid True/False becoming 1.0/0.0.
        """
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        return default

    async def new_roll(self) -> None:
        """Start a new (or started) roll on the ReefMat device.

        Reads current `started_roll_diameter` from local state:
          - If it equals the minimum diameter, creates a "New Roll" using the
            model-specific maximum roll diameter.
          - Otherwise creates a "Started Roll" using the provided diameter.

        Sends the resulting payload to the `/new-roll` endpoint.
        """
        model = self.get_data(
            "$.sources[?(@.name=='/configuration')].data.model",
            is_None_possible=True,
        )
        diameter_raw = self.get_data(
            MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME,
            is_None_possible=True,
        )
        diameter = self._as_float(diameter_raw, float(MAT_MIN_ROLL_DIAMETER))

        # New roll
        if diameter == float(MAT_MIN_ROLL_DIAMETER):
            name = "New Roll"
            is_partial = False

            if not isinstance(model, str) or model not in MAT_MAX_ROLL_DIAMETERS:
                _LOGGER.error(
                    "Unknown ReefMat model %r; cannot set new roll diameter",
                    model,
                )
                return

            diameter = float(MAT_MAX_ROLL_DIAMETERS[model])
        # Started roll
        else:
            name = "Started Roll"
            is_partial = True

        payload: dict[str, Any] = {
            "external_diameter": diameter,
            "name": name,
            "thickness": MAT_ROLL_THICKNESS,
            "is_partial": is_partial,
        }
        _LOGGER.info("New roll: %s", payload)
        await self._http_send(self._base_url + "/new-roll", payload, "post")
