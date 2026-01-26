"""ReefBeat cloud API wrapper.

Handles authentication against the ReefBeat cloud and exposes a small set of
configured sources (`/user`, `/aquarium`, `/device`) plus cloud “library” sources
(lights, waves, supplements).

Notes:
    - Requests are sent via the base `_http_send` helper.
    - `http_send` retries once on expired token (HTTP 401) by refreshing the token.
"""

from __future__ import annotations

import logging
import time
from contextlib import suppress
from typing import Any, Optional, cast
from urllib.parse import quote_plus

import aiohttp
from homeassistant.exceptions import HomeAssistantError

from ..const import LIGHTS_LIBRARY, SUPPLEMENTS_LIBRARY, WAVES_LIBRARY
from .api import HttpResult, ReefBeatAPI, SourceEntry, parse

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Classes
# =============================================================================


class ReefBeatCloudAPI(ReefBeatAPI):
    """ReefBeat cloud API wrapper.

    Sources:
        - /user
        - /aquarium
        - /device
        - LIGHTS_LIBRARY / WAVES_LIBRARY / SUPPLEMENTS_LIBRARY (cloud libraries)
    """

    def __init__(
        self,
        username: str,
        password: str,
        live_config_update: bool,
        ip: str,
        session: aiohttp.ClientSession,
        disable_supplement: str,
    ) -> None:
        """Create a ReefBeatCloudAPI instance.

        Args:
            username: ReefBeat cloud username.
            password: ReefBeat cloud password.
            live_config_update: Whether the base API performs live config updates.
            ip: Cloud host to connect to (used for https://{ip}/oauth/token and API base).

        Notes:
            Initializes the default list of cloud sources in `self.data["sources"]`.
        """
        super().__init__(ip, live_config_update, session, secure=True)
        self._username = username
        self._password = password
        self._token: str | None = None
        self._header: dict[str, str] | None = None

        self.data["sources"] = cast(
            list[SourceEntry],
            [
                {"name": "/user", "type": "config", "data": ""},
                {"name": "/aquarium", "type": "config", "data": ""},
                {"name": "/device", "type": "config", "data": ""},
                {"name": LIGHTS_LIBRARY, "type": "config", "data": ""},
                {"name": WAVES_LIBRARY, "type": "config", "data": ""},
            ],
        )
        if not disable_supplement:
            self.add_source(SUPPLEMENTS_LIBRARY,"config","");

    async def http_send(
        self, action: str, payload: Any = None, method: str = "post"
    ) -> Optional[HttpResult]:
        """Send a cloud request.

        Args:
            action: API path (appended to `self._base_url`).
            payload: Request body (defaults to `{}`).
            method: HTTP method name passed to `_http_send`.

        Returns:
            The `HttpResult` when available, otherwise `None`.

        Notes:
            If the response is HTTP 401, tries to renew the token once and retries.
        """
        if payload is None:
            payload = {}

        res = await self._http_send(self._base_url + action, payload, method)
        if res is not None and res.get("status", 0) == 401:
            _LOGGER.warning("Try to renew token")
            await self.connect()
            res = await self._http_send(self._base_url + action, payload, method)
        return res

    async def connect(self) -> None:
        """Authenticate with the ReefBeat cloud and store the bearer token.

        Raises:
            InvalidAuth: When credentials are invalid or the token is missing.
        """
        if self._auth_date is None:
            _LOGGER.debug("Init cloud connection with username: %s", self._username)
        else:
            _LOGGER.debug("Renew cloud authentification %s", self._username)

        header = {
            "Authorization": "Basic Z0ZqSHRKcGE6Qzlmb2d3cmpEV09SVDJHWQ==",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {
            "grant_type": "password",
            "username": self._username,
            "password": quote_plus(self._password.encode("UTF-8")),
        }
        _LOGGER.debug("AUTH %s"%self._session);
        async with self._session.post(
            "https://" + self.ip + "/oauth/token",
            data=payload,
            headers=header,
            ssl=False,
        ) as resp:
            r_status = int(resp.status)
            r_text = await resp.text()
            r_json: Any | None = None
            with suppress(Exception):
                r_json = await resp.json(content_type=None)

        if r_status != 200:
            _LOGGER.error("Authentification fail. Verify your credentials")
            raise InvalidAuth(r_text)

        data: dict[str, Any] = {}
        if isinstance(r_json, dict):
            # r_json is parsed from JSON and may contain non-str keys at type level;
            # normalize to a dict[str, Any] for safe access.
            data = {str(k): v for k, v in cast(dict[Any, Any], r_json).items()}

        token: str | None = None
        val = data.get("access_token")
        if isinstance(val, str):
            token = val
        if not token:
            raise InvalidAuth("No access_token returned by cloud")

        self._token = token
        self._header = {"Authorization": f"Bearer {self._token}"}
        self._auth_date = time.time()

    def get_devices(self, device_name: str) -> list[Any]:
        """Return jsonpath-ng matches for devices of the given type.

        Args:
            device_name: Device `type` value to filter on (as found in `/device` payload).

        Returns:
            List of jsonpath-ng match objects.
        """
        query = parse(
            "$.sources[?(@.name=='/device')].data[?(@.type=='" + device_name + "')]"
        )
        res = query.find(self.data)
        return res


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""
