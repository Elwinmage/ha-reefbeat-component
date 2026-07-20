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

Note:
    Write endpoints for probe calibration and per-port control are not yet
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


class ReefControlAPI(ReefBeatAPI):
    """Access to ReefControl information (read-only for now)."""

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
