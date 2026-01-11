"""ReefBeat ReefATO+ API wrapper.

Provides ATO-specific helpers on top of the generic ReefBeat API.

Endpoints:
    - /resume: clear empty latch / resume operation
    - /update-volume: set remaining reservoir volume
    - /configuration: push `auto_fill` setting
"""

from __future__ import annotations

import logging
from typing import Any, cast

import aiohttp

from ..const import ATO_AUTO_FILL_INTERNAL_NAME
from .api import ReefBeatAPI, SourceEntry

_LOGGER = logging.getLogger(__name__)


class ReefATOAPI(ReefBeatAPI):
    """ReefATO+ API wrapper.

    Implements ATO-specific endpoints:
    - /resume: clear empty latch / resume operation
    - /update-volume: set remaining reservoir volume
    - /configuration: push auto_fill setting
    """

    def __init__(
        self,
        ip: str,
        live_config_update: bool,
        session: aiohttp.ClientSession,
    ) -> None:
        """Create a ReefATOAPI instance.

        Args:
            ip: Device IP/host.
            live_config_update: Whether the base API performs live config updates.

        Notes:
            Ensures the `/configuration` source exists so `push_values()` can PUT
            ATO configuration.
        """
        super().__init__(ip, live_config_update, session)

        # ATO is strictly local-only in this integration.
        # Populate the local flag so entities/coordinators can branch without
        # noisy jsonpath misses.
        self.data.setdefault("local", {})
        self.data["local"]["use_cloud_api"] = False

        # Ensure /configuration exists as a config source.
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        sources.insert(
            len(sources),
            {"name": "/configuration", "type": "config", "data": ""},
        )
        self.data["sources"] = sources

    async def resume(self) -> None:
        """Resume ATO operation.

        Clears the "empty" latch on supported devices by POSTing to `/resume`.
        """
        await self._http_send(self._base_url + "/resume", payload=None, method="post")

    async def push_values(
        self, source: str = "/configuration", method: str = "put"
    ) -> None:
        """Push ATO configuration values to the device.

        Args:
            source: Endpoint path to push to (defaults to `/configuration`).
            method: HTTP method (defaults to `put`).

        Notes:
            Currently only pushes the `auto_fill` option.
        """
        auto_fill = self.get_data(ATO_AUTO_FILL_INTERNAL_NAME, is_None_possible=True)
        payload: dict[str, Any] = {"auto_fill": auto_fill}
        await self._http_send(self._base_url + source, payload, method)

    async def set_volume_left(self, volume_ml: int) -> None:
        """Set the remaining reservoir volume (in milliliters).

        Args:
            volume_ml: Remaining volume in ml.
        """
        payload = {"volume": int(volume_ml)}
        await self._http_send(self._base_url + "/update-volume", payload, "post")
