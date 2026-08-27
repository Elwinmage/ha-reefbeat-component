"""ReefBeat ReefATO+ API wrapper.

Provides ATO-specific helpers on top of the generic ReefBeat API.

Endpoints:
    - /resume: clear empty latch / resume operation
    - /update-volume: set remaining reservoir volume
    - /configuration: push `auto_fill`, leak probe and buzzer settings
"""

from __future__ import annotations

import logging
from typing import Any, cast

import aiohttp

from ..const import (
    ATO_AUTO_FILL_INTERNAL_NAME,
    ATO_BUZZER_ENABLED_INTERNAL_NAME,
    ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME,
)
from .api import ReefBeatAPI, SourceEntry

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Classes
# =============================================================================


class ReefATOAPI(ReefBeatAPI):
    """ReefATO+ API wrapper.

    Implements ATO-specific endpoints:
    - /resume: clear empty latch / resume operation
    - /update-volume: set remaining reservoir volume
    - /configuration: push auto_fill, leak probe and buzzer settings
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
            ATO configuration, and seeds the local-only keys.
        """
        super().__init__(ip, live_config_update, session)

        # Ensure /configuration exists as a config source.
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        sources.insert(
            len(sources),
            {"name": "/configuration", "type": "config", "data": ""},
        )
        self.data["sources"] = sources

        # Seed integration-owned keys: jsonpath update() cannot create a
        # missing key, so `$.local.tank_volume` has to exist before the number
        # entity restores into it. Same reason the doser seeds its per-head
        # local values.
        local = cast(dict[str, Any], self.data.setdefault("local", {}))
        local.setdefault("tank_volume", None)

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
            Pushes `auto_fill` and, when the device reported them, the leak
            probe's arming flag and the leak alarm buzzer. Both of the latter
            are read from `/dashboard` (see the two INTERNAL_NAME constants)
            and written here, which is where the firmware accepts them.

            The firmware accepts a partial configuration -- the Red Sea app
            only ever sends the keys the user changed -- so a value the device
            has not reported is left out entirely rather than sent as null,
            which would clear the setting.

            `leak` carries only `sensor_enabled`: the sibling
            `emergency_shutdown` is not on `/dashboard`, so there is no value
            to echo back and a partial `leak` object leaves it untouched.
        """
        auto_fill = self.get_data(ATO_AUTO_FILL_INTERNAL_NAME, is_None_possible=True)
        payload: dict[str, Any] = {"auto_fill": auto_fill}

        buzzer = self.get_data(ATO_BUZZER_ENABLED_INTERNAL_NAME, is_None_possible=True)
        if buzzer is not None:
            payload["buzzer"] = {"enabled": bool(buzzer)}

        leak = self.get_data(
            ATO_LEAK_SENSOR_ENABLED_INTERNAL_NAME, is_None_possible=True
        )
        if leak is not None:
            payload["leak"] = {"sensor_enabled": bool(leak)}

        await self._http_send(self._base_url + source, payload, method)

    async def set_volume_left(self, volume_ml: int) -> None:
        """Set the remaining reservoir volume (in milliliters).

        Args:
            volume_ml: Remaining volume in ml.
        """
        payload = {"volume": int(volume_ml)}
        await self._http_send(self._base_url + "/update-volume", payload, "post")
