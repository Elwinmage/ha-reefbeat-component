"""ReefBeat ReefRun API wrapper.

Provides ReefRun-specific sources and payload shaping for pump settings and the
preview endpoint.

Notes:
    - `/pump/settings` accepts either a single pump payload (`pump_1` / `pump_2`)
        or a reduced payload without per-pump entries depending on context.
    - `/preview` is treated as a local-only preview source used for UI simulation.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, cast

import aiohttp

from .api import ReefBeatAPI

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Classes
# =============================================================================


class ReefRunAPI(ReefBeatAPI):
    """ReefRun API wrapper (pump settings and preview payload shaping)."""

    def __init__(
        self,
        ip: str,
        live_config_update: bool,
        session: aiohttp.ClientSession,
    ) -> None:
        """Create a ReefRunAPI instance.

        Args:
            ip: Device IP/host.
            live_config_update: Whether the base API performs live config updates.

        Notes:
            Registers:
                - `/pump/settings` (config)
                - `/preview` (preview) with default pump preview values
        """
        super().__init__(ip, live_config_update, session)

        # TODO: add feeding, maintenance, emergency, shortcut_off_delay, and pump_on_delayed.
        # Issue URL: https://github.com/Elwinmage/ha-reefbeat-component/issues/25
        # labels: enhancement, rsrun

        self.data["sources"].insert(
            len(self.data["sources"]),
            {"name": "/pump/settings", "type": "data", "data": ""},
        )
        self.data["sources"].insert(
            len(self.data["sources"]),
            {
                "name": "/preview",
                "type": "preview",
                "data": {
                    "pump_1": {"pd": 0, "ti": 100},
                    "pump_2": {"pd": 0, "ti": 100},
                },
            },
        )

        # Calibration data source (last calibration dates)
        self.data["sources"].insert(
            len(self.data["sources"]),
            {"name": "/calibration", "type": "data", "data": ""},
        )

        # Per-pump shortcuts (feeding, maintenance, emergency, etc.)
        self.data["sources"].insert(
            len(self.data["sources"]),
            {"name": "/pump/shortcuts", "type": "config", "data": ""},
        )

    async def calibration_start(self, point: int = 2) -> None:
        """Start EC sensor calibration.

        Args:
            point: Calibration point (default 2 for 2-point calibration).
        """
        _LOGGER.debug("Starting EC calibration (point=%d)", point)
        await self._http_send(self._base_url + f"/calibration/{point}", {}, "post")

    async def calibration_skim(self) -> None:
        """Start overskimming calibration step."""
        _LOGGER.debug("Starting overskimming calibration")
        await self._http_send(self._base_url + "/calibration/skim", {}, "post")

    async def calibration_cup(self) -> None:
        """Start full-cup calibration step."""
        _LOGGER.debug("Starting full-cup calibration")
        await self._http_send(self._base_url + "/calibration/cup", {}, "post")

    async def calibration_end(self) -> None:
        """End EC sensor calibration (DELETE /calibration)."""
        _LOGGER.debug("Ending EC calibration")
        await self._http_send(self._base_url + "/calibration", method="delete")

    async def detect_pump(self, pump: int) -> dict[str, Any] | None:
        """Detect which pump is physically connected to a channel.

        Args:
            pump: Pump number (1 or 2).

        Returns:
            Detection result dict (e.g. {"type": "skimmer", "model": "rsk-300"})
            or None on failure.
        """
        _LOGGER.debug("Detecting pump on channel %d", pump)
        result = await self.http_get(f"/pump/{pump}/detection")
        if result and result.get("ok"):
            return result.get("json")
        return None

    async def delete_pump(self, pump: int) -> None:
        """Reset a pump channel to factory defaults.

        Args:
            pump: Pump number (1 or 2).
        """
        _LOGGER.debug("Deleting pump %d settings (factory reset)", pump)
        await self._http_send(
            self._base_url + f"/pump/{pump}/settings", method="delete"
        )

    async def configure_pump(
        self, pump: int, name: str, model: str, pump_type: str
    ) -> None:
        """Configure a pump channel with name, model and type.

        Args:
            pump: Pump number (1 or 2).
            name: Display name for the pump.
            model: Model identifier (e.g. "rsk-900", "return-12000").
            pump_type: Pump type ("skimmer" or "return").
        """
        _LOGGER.debug(
            "Configuring pump %d: name=%s model=%s type=%s",
            pump,
            name,
            model,
            pump_type,
        )
        payload: dict[str, Any] = {
            f"pump_{pump}": {
                "name": name,
                "model": model,
                "type": pump_type,
            }
        }
        await self._http_send(self._base_url + "/pump/settings", payload, "put")

    async def push_values(
        self, source: str, method: str = "put", pump: Optional[int] = None
    ) -> None:
        """Push cached values to the device.

        Args:
            source: Endpoint path such as `/pump/settings` or `/preview`.
            method: HTTP method to use (default: PUT).
            pump: Optional pump number; when set, pushes only `pump_{pump}` for that source.

        Notes:
            - For `/pump/settings` and `/preview`, a per-pump update is wrapped as:
              `{"pump_1": {...}}` or `{"pump_2": {...}}`.
            - For `/pump/settings` without `pump`, the payload is copied and stripped of
              `pump_1` and `pump_2` keys (legacy behavior).
        """
        if source in ("/pump/settings", "/preview"):
            if pump is not None:
                pump_payload = self.get_data(
                    "$.sources[?(@.name=='" + source + "')].data.pump_" + str(pump),
                    is_None_possible=True,
                )
                payload: dict[str, Any] = {"pump_" + str(pump): pump_payload}
            else:
                raw = self.get_data(
                    "$.sources[?(@.name=='/pump/settings')].data",
                    is_None_possible=True,
                )
                if not isinstance(raw, dict):
                    _LOGGER.error(
                        "ReefRunAPI.push_values: no dict payload for %s", source
                    )
                    return
                payload_dict = cast(dict[str, Any], raw).copy()
                payload_dict.pop("pump_1", None)
                payload_dict.pop("pump_2", None)
                payload = payload_dict

            await self._http_send(self._base_url + source, payload, method)
            return

        payload_any: Any = self.get_data(
            "$.sources[?(@.name=='" + source + "')].data",
            is_None_possible=True,
        )
        if payload_any is None:
            _LOGGER.error(
                "ReefRunAPI.push_values: no payload found for source=%s", source
            )
            return
        payload = payload_any
        await self._http_send(self._base_url + source, payload, method)
