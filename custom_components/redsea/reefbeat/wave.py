"""ReefBeat ReefWave API wrapper.

Registers ReefWave-specific sources and provides a local preview payload used by
the UI for effect simulation.

Notes:
    ReefWave firmware differs from other ReefBeat devices:
      - device-info may be served at `/` rather than `/dashboard`
      - `/mode` is treated as a data source
"""

from __future__ import annotations

import logging

import aiohttp

from .api import ReefBeatAPI

_LOGGER = logging.getLogger(__name__)


class ReefWaveAPI(ReefBeatAPI):
    """ReefWave API wrapper (sources and preview defaults)."""

    def __init__(
        self,
        ip: str,
        live_config_update: bool,
        session: aiohttp.ClientSession,
    ) -> None:
        """Create a ReefWaveAPI instance.

        Args:
            ip: Device IP/host.
            live_config_update: Whether the base API performs live config updates.

        Notes:
            Adjusts default sources inherited from `ReefBeatAPI`:
                - Removes `/dashboard` (data) and `/mode` (config)
                - Adds `/` as `device-info`
                - Re-adds `/mode` as `data`
                - Adds feeding schedule, auto mode, device-settings, and preview sources
        """
        super().__init__(ip, live_config_update, session)

        # Remove sources that don't match ReefWave behavior (safe if absent).
        self.remove_source("/dashboard")
        self.remove_source("/mode")

        # Register ReefWave sources.
        self.add_source("/", "device-info", "")
        self.add_source("/mode", "data", "")
        self.add_source("/feeding/schedule", "config", "")
        self.add_source("/auto", "data", "")
        self.add_source("/device-settings", "config", "")

        # Local/UI preview defaults (not necessarily a device endpoint payload).
        self.add_source(
            "/preview",
            "preview",
            {
                "type": "ra",
                "direction": "fw",
                "frt": 10,
                "rrt": 2,
                "fti": 100,
                "rti": 100,
                "duration": 300000,
                "st": 3,
                "pd": 2,
                "sn": 3,
            },
        )

        self.data["local"] = {"use_cloud_api": None}
