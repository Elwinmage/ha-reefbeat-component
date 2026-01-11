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

from .api import ReefBeatAPI

_LOGGER = logging.getLogger(__name__)


class ReefRunAPI(ReefBeatAPI):
    """ReefRun API wrapper (pump settings and preview payload shaping)."""

    def __init__(self, ip: str, live_config_update: bool) -> None:
        """Create a ReefRunAPI instance.

        Args:
            ip: Device IP/host.
            live_config_update: Whether the base API performs live config updates.

        Notes:
            Registers:
              - `/pump/settings` (config)
              - `/preview` (preview) with default pump preview values
        """
        super().__init__(ip, live_config_update)

        # TODO: add feeding, maintenance, emergency, shortcut_off_delay, and pump_on_delayed.
        # Issue URL: https://github.com/Elwinmage/ha-reefbeat-component/issues/25
        # labels: enhancement, rsrun

        self.data["sources"].insert(
            len(self.data["sources"]),
            {"name": "/pump/settings", "type": "config", "data": ""},
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

        # TODO: calibration
        # Issue URL: https://github.com/Elwinmage/ha-reefbeat-component/issues/24
        # labels: enhancement, rsrun

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
