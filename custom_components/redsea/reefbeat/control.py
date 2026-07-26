"""ReefBeat ReefControl API wrapper.

Provides helpers for the ReefControl hub (RSCONTROLPRO, RSCONTROLLITE), which
acts as the central hub for ReefSense digital probes and exposes 1 (Lite) or
2 (Pro) 12V DC output ports.

Endpoints observed on real devices (v1.3_25A firmware):
    - GET /dashboard        — mode, cable_connected, connected power center,
                              probes[], ports[], buzzer, leak_detector
    - GET /configuration    — buzzer configs, leak_detector, danger debounce
    - GET /mode             — current device mode
    - GET /time, /wifi, /cloud, /device-info, /firmware, /logging (base)

ATO endpoints (globally-scoped, port disambiguation via body):
    - POST /ato/manual-pump   — one manual dose on the ATO port
    - POST /ato/stop          — cancel ongoing fill / stop pump
    - POST /ato/resume        — clear an empty latch, resume automation
    - POST /ato/update-volume — set remaining reservoir volume (mL)
    - PUT  /ato/configuration — push per-port config (auto_fill flag)

Evidence:
    The Red Sea Android app's decompiled DEX (com.hippotec.redsea) uses the
    un-prefixed ``/ato/*`` paths and models the PUT body via
    ``ServerAtoConfiguration$Put``. All fields on that class are boxed
    (Boolean/Integer/Double, i.e. nullable), which means GSON omits nulls
    on the wire and the firmware accepts partial updates — so sending just
    ``{"port_index": N, "auto_fill": <bool>}`` preserves every other setting
    (hose, notify, debug, pump_override, etc.). The ``port_index`` field is
    named ``portIndex`` in the Kotlin class; the wire form uses snake_case,
    consistent with every other field name observed on the /dashboard
    payload.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import aiohttp

from .api import ReefBeatAPI, SourceEntry

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Classes
# =============================================================================


class ReefControlAPI(ReefBeatAPI):
    """Access to ReefControl information with per-port ATO controls."""

    def __init__(
        self,
        ip: str,
        live_config_update: bool,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the ReefControl API wrapper.

        Ensures `/configuration` is registered as a config source so that
        buzzer settings and leak-detector flag are available.
        """
        super().__init__(ip, live_config_update, session)

        # Register the /configuration source so it is polled with config refreshes.
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        sources.insert(
            len(sources),
            {"name": "/configuration", "type": "config", "data": ""},
        )
        self.data["sources"] = sources

    # ------------------------------------------------------------------
    # Per-port ATO helpers
    # ------------------------------------------------------------------
    #
    # All ATO endpoints are global; the port is passed as a `port_index`
    # body field. On a hub with a single ATO port the field is either
    # ignored or defaulted, which keeps the behaviour safe for RSCONTROLLITE
    # / single-ATO RSCONTROLPRO setups.

    async def ato_manual_pump(self, port: int) -> None:
        """Trigger one manual ATO dose on the given port.

        The firmware pumps until either the "desired" water-level sensor is
        satisfied or the internal safety timer fires. This is the
        equivalent of pressing the "fill" button on a standalone RSATO+.
        """
        await self._http_send(
            f"{self._base_url}/ato/manual-pump",
            payload={"port_index": int(port)},
            method="post",
        )

    async def ato_stop(self, port: int) -> None:
        """Cancel any ongoing ATO fill and stop the pump on the given port."""
        await self._http_send(
            f"{self._base_url}/ato/stop",
            payload={"port_index": int(port)},
            method="post",
        )

    async def ato_resume(self, port: int) -> None:
        """Clear an "empty" latch and resume automated ATO operation.

        Called after refilling the reservoir when the firmware has stopped
        pumping because of an empty-tank detection.
        """
        await self._http_send(
            f"{self._base_url}/ato/resume",
            payload={"port_index": int(port)},
            method="post",
        )

    async def ato_set_volume_left(self, port: int, volume_ml: int) -> None:
        """Overwrite the reservoir "volume left" counter (in mL).

        Used after a manual refill to tell the firmware how much fresh water
        is available. Matches the RSATO+ `POST /update-volume` payload shape,
        with `port_index` added for RSCONTROLPRO dual-ATO cases.
        """
        payload: dict[str, Any] = {
            "port_index": int(port),
            "volume": int(volume_ml),
        }
        await self._http_send(
            f"{self._base_url}/ato/update-volume",
            payload,
            "post",
        )

    async def push_ato_configuration(self, port: int, auto_fill: bool) -> None:
        """Push the `auto_fill` flag for a specific ATO port.

        Uses `PUT /ato/configuration` to atomically toggle the firmware's
        auto-fill behaviour on the requested port.
        """
        payload: dict[str, Any] = {
            "port_index": int(port),
            "auto_fill": bool(auto_fill),
        }
        await self._http_send(
            f"{self._base_url}/ato/configuration",
            payload,
            "put",
        )
