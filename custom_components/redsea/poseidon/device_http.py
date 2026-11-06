"""Local HTTP calls of Poseidon to a device.

Kept apart from the device's ReefBeatAPI on purpose: the switch sequence and
the key capture read and write endpoints raw, without touching the cached
sources or the messages the device's entities show.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from ..reefbeat.api import notify_http

_LOGGER = logging.getLogger(__name__)

# Origin of these requests in the spy file
ORIGIN = "poseidon"
TIMEOUT_S = 5.0
WRITE_TIMEOUT_S = 8.0


class DeviceHttp:
    """Raw access to one device's local API."""

    def __init__(self, session: aiohttp.ClientSession, ip: str) -> None:
        self._session = session
        self.ip = ip
        self.base = f"http://{ip}"

    async def get_json(self, endpoint: str, timeout: float = TIMEOUT_S) -> Any:
        """GET one endpoint: its JSON (or text), None when it fails."""
        started = time.time()
        status = 0
        try:
            async with asyncio.timeout(timeout):
                async with self._session.get(self.base + endpoint) as resp:
                    status = resp.status
                    if resp.status != 200:
                        return None
                    text = await resp.text()
                    try:
                        return await resp.json(content_type=None)
                    except ValueError:
                        return text or None
        except (aiohttp.ClientError, TimeoutError, OSError):
            return None
        finally:
            notify_http(self.ip, "get", endpoint, status, started, origin=ORIGIN)

    async def write_json(
        self,
        endpoint: str,
        payload: Any = None,
        method: str = "POST",
        timeout: float = WRITE_TIMEOUT_S,
    ) -> bool:
        """POST or PUT a JSON payload; whether the device accepted it."""
        call = self._session.put if method.upper() == "PUT" else self._session.post
        started = time.time()
        status = 0
        try:
            async with asyncio.timeout(timeout):
                async with call(self.base + endpoint, json=payload) as resp:
                    status = resp.status
                    if 200 <= resp.status < 300:
                        return True
                    _LOGGER.warning(
                        "%s %s%s -> %s %s",
                        method,
                        self.ip,
                        endpoint,
                        resp.status,
                        (await resp.text())[:120],
                    )
                    return False
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.warning("%s %s%s failed: %s", method, self.ip, endpoint, err)
            return False
        finally:
            # Payloads of /cloud carry the keys: never in the spy file
            notify_http(self.ip, method, endpoint, status, started, origin=ORIGIN)

    async def get_cloud(self) -> dict[str, Any] | None:
        """The device's /cloud: url, enabled, connected, api_key..."""
        data = await self.get_json("/cloud")
        return data if isinstance(data, dict) else None

    async def set_cloud(self, url: str, api_key: str, api_secret: str) -> bool:
        """Point the device at an MQTT broker.

        The sequence validated in reefbeat_god_mode.py (taken from the app):
        disable, write the url and both keys, enable again. The firmware
        needs the three fields together.
        """
        disabled = await self.write_json("/cloud/disable")
        written = await self.write_json(
            "/cloud", {"url": url, "api_key": api_key, "api_secret": api_secret}
        )
        # Enabled again even after a failed write: never leave the device
        # cut off from every broker
        enabled = await self.write_json("/cloud/enable")
        return disabled and written and enabled
