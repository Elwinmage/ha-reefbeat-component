"""ReefBeat ReefPower API wrapper.

Provides helpers for the ReefControl Power smart center (RSPOWER6, RSPOWER8),
which exposes 6 or 8 AC sockets. All sockets share a common `sockets` array in
the `/dashboard` payload.

Endpoints observed on real devices (v2.3_25A firmware):
    - GET /dashboard        — mode, battery, connected control hub, sockets[]
    - GET /configuration    — LED config, current limits, max_sockets, model_type
    - GET /mode             — current device mode
    - GET /time, /wifi, /cloud, /device-info, /firmware, /logging (base)

Note:
    The write endpoints (per-socket on/off/mode change) are not yet
    reverse-engineered — only read access is implemented at this stage.
"""

from __future__ import annotations

import logging
from typing import cast

import aiohttp

from .api import ReefBeatAPI, SourceEntry

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Classes
# =============================================================================


class ReefPowerAPI(ReefBeatAPI):
    """Access to ReefPower information (read-only for now)."""

    def __init__(
        self,
        ip: str,
        live_config_update: bool,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the ReefPower API wrapper.

        Ensures `/configuration` is registered as a config source so that
        socket limits, LED colors and current thresholds are available.
        """
        super().__init__(ip, live_config_update, session)

        # Register the /configuration source so it is polled with config refreshes.
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        sources.insert(
            len(sources),
            {"name": "/configuration", "type": "config", "data": ""},
        )
        self.data["sources"] = sources
