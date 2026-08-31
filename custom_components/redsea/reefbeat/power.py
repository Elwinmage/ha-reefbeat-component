"""ReefBeat ReefPower API wrapper.

Provides helpers for the ReefControl Power smart center (RSPOWER6, RSPOWER8),
which exposes 6 or 8 AC sockets. All sockets share a common `sockets` array in
the `/dashboard` payload.

Endpoints observed on real devices (v2.3_25A firmware):
    - GET /dashboard                    — mode, battery, connected hub, sockets[]
    - GET /configuration                — LED config, current limits, max_sockets
    - GET /sockets/config               — per-socket mode/name/enabled/detector
    - GET /socket/<n>/config/schedule   — {"intervals":[{"time","duration"}]}
    - GET /mode                         — current device mode
    - GET /time, /wifi, /cloud, /device-info, /firmware, /logging (base)

Write endpoints (reverse-engineered from the ReefBeat app traffic):
    - PUT  /sockets/config              — {"sockets":[{"mode","number","name"?}]}
    - PUT  /socket/<n>/config/schedule  — {"intervals":[{"time","duration"}]}
    - POST /socket/<n>/toggle           — flip the socket state
    - POST /setup-finish                — leave setup mode (device switches to auto)

The device ships in ``setup`` mode: the app configures the first socket, then
POSTs ``/setup-finish`` to move the whole device to ``auto`` before configuring
the remaining sockets.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import aiohttp

from .api import HttpResult, ReefBeatAPI, SourceEntry

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Classes
# =============================================================================


class ReefPowerAPI(ReefBeatAPI):
    """Access to ReefPower information and per-socket control."""

    def __init__(
        self,
        ip: str,
        live_config_update: bool,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the ReefPower API wrapper.

        Registers `/configuration` and `/sockets/config` as config sources so
        that socket limits, LED colors, current thresholds and per-socket
        mode/name are polled with config refreshes.
        """
        super().__init__(ip, live_config_update, session)

        # Register extra config sources (polled on config refreshes).
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        for name in ("/configuration", "/sockets/config"):
            sources.insert(
                len(sources),
                {"name": name, "type": "config", "data": ""},
            )
        self.data["sources"] = sources

    async def set_socket_mode(
        self, number: int, mode: str, name: str | None = None
    ) -> HttpResult | None:
        """Set a socket's mode via ``PUT /sockets/config``.

        The device accepts a partial update: only the changed socket is sent.
        ``mode`` is one of ``off`` / ``on`` / ``schedule``. ``name`` is only
        included when renaming (the app omits it for plain mode changes).
        """
        socket: dict[str, Any] = {"mode": mode, "number": number}
        if name is not None:
            socket["name"] = name
        return await self.http_send("/sockets/config", {"sockets": [socket]}, "put")

    async def set_socket_schedule(
        self, number: int, intervals: list[dict[str, int]]
    ) -> HttpResult | None:
        """Set a socket's daily schedule via ``PUT /socket/<n>/config/schedule``.

        ``intervals`` is a list of ``{"time": <minutes from midnight>,
        "duration": <minutes>}`` entries, e.g. ``[{"time": 0, "duration":
        1439}]`` for "on all day" or ``[{"time": 0, "duration": 539},
        {"time": 1320, "duration": 119}]`` for two on-windows.
        """
        return await self.http_send(
            f"/socket/{number}/config/schedule",
            {"intervals": intervals},
            "put",
        )

    async def delete_socket(self, number: int) -> HttpResult | None:
        """Uninstall an AC socket via ``DELETE /socket/<n>/config``.

        The firmware answers ``{"success":true,"message":"Successfully deleted
        sockets"}`` and resets the entry: ``mode`` back to ``setup`` and the
        name to its factory value (``S1`` … ``S6``). Unlike the hub's 12V
        ports there is no "install" counterpart — a socket leaves ``setup``
        as soon as ``PUT /sockets/config`` gives it a real mode.
        """
        return await self.http_send(f"/socket/{int(number)}/config", None, "delete")

    async def unsubscribe_sockets(self, numbers: list[int]) -> HttpResult | None:
        """Drop the sensor binding of one or more sockets via ``PUT /unsubscribe``.

        Body is ``{"sockets": [<numbers>]}``. The ReefBeat app sends this
        right after deleting a socket that was in ``sensor`` mode, otherwise
        the binding outlives the socket it belonged to. The paired hub keeps
        its own copy of the subscription, which must be cleared separately
        with ``PUT /socket/<n>/unsubscribe`` on the hub.
        """
        return await self.http_send(
            "/unsubscribe", {"sockets": [int(n) for n in numbers]}, "put"
        )

    async def setup_finish(self) -> HttpResult | None:
        """Leave setup mode via ``POST /setup-finish`` (device switches to auto)."""
        return await self.http_send("/setup-finish", {}, "post")
