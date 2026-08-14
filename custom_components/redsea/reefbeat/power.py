"""ReefBeat ReefPower API wrapper.

Provides helpers for the ReefControl Power smart center (RSPOWER6, RSPOWER8),
which exposes 6 or 8 AC sockets. All sockets share a common `sockets` array in
the `/dashboard` payload.

Endpoints observed on real devices (v2.3_25A firmware):
    - GET /dashboard                    — mode, battery, connected hub, sockets[]
    - GET /configuration                — LED config, current limits, max_sockets
    - GET /sockets/config               — per-socket mode/name/enabled/detector
    - GET /socket/<n>/config/schedule   — {"intervals":[{"time","duration"}]}
    - GET /socket/<n>/consumption/log   — 96 buckets x `interval` min of
                                          avg/min/max/count power (24 h window)
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
        ``mode`` is one of ``off`` / ``on`` / ``schedule`` / ``sensor``
        (``sensor`` drives the socket from a probe of the paired ReefControl
        hub and requires a prior ``PUT /subscribe``). ``name`` is only
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

    async def setup_finish(self) -> HttpResult | None:
        """Leave setup mode via ``POST /setup-finish`` (device switches to auto)."""
        return await self.http_send("/setup-finish", {}, "post")

    # ------------------------------------------------------------------
    # Per-socket consumption history
    # ------------------------------------------------------------------

    def register_consumption_logs(self, socket_count: int) -> None:
        """Register one ``/socket/<n>/consumption/log`` data source per socket.

        Called once the socket count is known (6 on RSPOWER6, 8 on RSPOWER8).
        The endpoint returns a rolling 24 h window of 96 buckets of
        `interval` minutes each, so polling it with the regular data refresh
        is cheap enough and gives the Energy dashboard real history instead of
        the single instantaneous `consumption` value from `/dashboard`.
        """
        for number in range(int(socket_count)):
            name = f"/socket/{number}/consumption/log"
            if not any(
                s.get("name") == name
                for s in cast(list[SourceEntry], self.data.get("sources", []))
            ):
                self.add_source(name, "data")

    def socket_energy_wh(self, number: int) -> float | None:
        """Return the energy (Wh) accumulated by a socket over the logged window.

        The payload gives, per bucket, the average power in watts (`avg`) and
        how many samples were actually collected (`count`, out of `interval`
        expected at one sample per minute). Partial buckets are therefore
        weighted by `count / interval` so a half-filled bucket does not count
        as a full one.
        """
        log = self.get_data(
            f"$.sources[?(@.name=='/socket/{int(number)}/consumption/log')].data",
            is_None_possible=True,
        )
        if not isinstance(log, dict):
            return None
        avg = log.get("avg")
        count = log.get("count")
        interval = log.get("interval")
        if not isinstance(avg, list) or not isinstance(interval, (int, float)):
            return None
        if not interval:
            return None
        if not isinstance(count, list) or len(count) != len(avg):
            count = [interval] * len(avg)

        total = 0.0
        for power, samples in zip(avg, count):
            if not isinstance(power, (int, float)) or not isinstance(
                samples, (int, float)
            ):
                continue
            # Wh = W * hours, prorated by how full the bucket is.
            total += float(power) * (interval / 60.0) * (float(samples) / interval)
        return round(total, 3)
