"""ReefBeat base API client.

This module provides `ReefBeatAPI`, the shared base used by device-specific and
cloud-specific API wrappers. It stores a unified state dict (`self.data`) and
offers JSONPath-based getters/setters as well as async-safe HTTP helpers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Protocol, TypedDict, cast

import httpx
from jsonpath_ng.ext import parse as _parse  # type: ignore

from ..const import DEFAULT_TIMEOUT, HTTP_DELAY_BETWEEN_RETRY, HTTP_MAX_RETRY

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Typed jsonpath-ng helpers
# -----------------------------------------------------------------------------


class Match(Protocol):
    """Subset protocol for jsonpath-ng match objects."""

    value: Any
    context: Optional[Any]
    path: Any


class JSONPathExpr(Protocol):
    """Subset protocol for parsed JSONPath expressions."""

    def find(self, data: Any) -> List[Match]: ...
    def update(self, data: Any, value: Any) -> Any: ...


def parse(expr: str) -> JSONPathExpr:
    """Typed wrapper around jsonpath_ng.ext.parse."""
    return cast(JSONPathExpr, _parse(expr))


# -----------------------------------------------------------------------------
# Data typing helpers
# -----------------------------------------------------------------------------


class SourceEntry(TypedDict):
    """A cached API source entry in `self.data["sources"]`."""

    name: str
    type: str
    data: Any


class ReefBeatAPI:
    """Base API client for ReefBeat local devices and cloud endpoints.

    Responsibilities:
        - Maintain a unified cached state dict in `self.data`:
            - `sources`: list of registered endpoint sources and their last decoded JSON
            - `local`: integration-maintained derived state
            - `message`: last response message/alert decoded from push calls
        - Provide JSONPath-based getters/setters (`get_data`, `set_data`)
        - Provide async HTTP fetch/push with retry/backoff (`fetch_*`, `_http_send`)

    Notes:
        - Subclasses may override `connect()` for authentication (cloud and secure devices).
        - `get_data()` uses an internal cache of eval()-able paths for speed.
    """

    def __init__(self, ip: str, live_config_update: bool, secure: bool = False) -> None:
        """Initialize the base API client.

        Args:
            ip: Device host/IP (or cloud host when `secure=True`).
            live_config_update: If True, `fetch_data()` also refreshes config sources.
            secure: If True, use https and allow subclasses to renew auth tokens.
        """
        self.ip = ip
        self._secure = secure
        self._auth_date: Optional[float] = None
        self._in_error = False

        self._base_url = ("https://" if secure else "http://") + ip

        self.data: Dict[str, Any] = {
            "sources": cast(
                list[SourceEntry],
                [
                    {"name": "/device-info", "type": "device-info", "data": ""},
                    {"name": "/firmware", "type": "config", "data": ""},
                    {"name": "/mode", "type": "config", "data": ""},
                    {"name": "/cloud", "type": "config", "data": ""},
                    {"name": "/wifi", "type": "data", "data": ""},
                    {"name": "/dashboard", "type": "data", "data": ""},
                ],
            )
        }
        self.data["local"] = {}
        self.data["message"] = {}

        # Cache mapping JSONPath expression -> "self.data[...]..." eval string
        self._data_db: Dict[str, str] = {}

        self.last_update_success: Optional[bool] = None
        self.quick_refresh: Optional[str] = None
        self._live_config_update = bool(live_config_update)
        self._header: Optional[Dict[str, str]] = None

    async def connect(self) -> None:
        """Perform authentication/handshake if needed.

        Subclasses override this for:
            - cloud authentication (token issuance)
            - secure local devices that require a session/token

        The base implementation is a no-op.
        """
        return

    async def http_get(self, access_path: str) -> Optional[httpx.Response]:
        """Perform a one-off GET request to `access_path`.

        This is a legacy convenience wrapper. Prefer registering a source and using
        `fetch_data()` / `fetch_config()` for consistent caching behavior.
        """
        try:
            async with httpx.AsyncClient(
                verify=False, timeout=DEFAULT_TIMEOUT
            ) as client:
                return await client.get(
                    self._base_url + access_path, headers=self._header
                )
        except Exception as e:
            _LOGGER.error(e)
            return None

    async def _http_get(
        self, client: httpx.AsyncClient, source: Match
    ) -> Optional[bool]:
        """Fetch one registered source and cache its decoded JSON.

        Args:
            client: Shared `httpx.AsyncClient` instance.
            source: jsonpath-ng match object for a source entry.

        Returns:
            True on success (data updated), False on hard failure, None when the caller
            should retry (e.g., after token renewal on HTTP 401).
        """
        name = cast(str, source.value["name"])
        _LOGGER.debug("_http_get: %s", self._base_url + name)
        now = time.time()

        # Renew authentication token for secure connections.
        if (
            self._secure
            and self._auth_date is not None
            and (now - self._auth_date) > 2700
        ):
            await self.connect()

        r = await client.get(
            self._base_url + name,
            timeout=DEFAULT_TIMEOUT,
            headers=self._header,
        )

        if r.status_code == 200 or (r.status_code == 503 and name == "/"):
            response = r.json()
            query = parse("$.sources[?(@.name=='" + name + "')]")
            s = query.find(self.data)
            if not s:
                _LOGGER.debug("Source %s not registered; ignoring response", name)
                return True
            s[0].value["data"] = response
            return True

        if r.status_code == 401:
            _LOGGER.warning("Authorization failed for %s, try to renew token", name)
            await self.connect()
            return None

        _LOGGER.error("Can not get data: %s from %s", name, self.ip)
        return False

    async def _call_url(self, client: httpx.AsyncClient, source: Match) -> None:
        """Fetch one source with retries.

        Marks the instance in error (`self._in_error=True`) if all retries fail.
        """
        status_ok = False
        error_count = 0
        while status_ok is False and error_count < HTTP_MAX_RETRY:
            try:
                status_ok = bool(await self._http_get(client, source))
            except Exception as e:
                error_count += 1
                _LOGGER.debug(
                    "Can not get data: %s, retry nb %d/%d",
                    source.value.get("name"),
                    error_count,
                    HTTP_MAX_RETRY,
                )
                _LOGGER.debug(e)
            if not status_ok:
                await asyncio.sleep(HTTP_DELAY_BETWEEN_RETRY)

        if not status_ok:
            _LOGGER.error(
                "Can not get data from %s%s after %s try",
                self.ip,
                source.value.get("name"),
                HTTP_MAX_RETRY,
            )
            self._in_error = True

    async def get_initial_data(self) -> Dict[str, Any]:
        """Fetch initial device data.

        Fetches:
            1) device-info sources
            2) config sources (unless live config update is enabled)
            3) data sources

        Returns:
            The internal `self.data` dict.
        """
        _LOGGER.debug("Reefbeat.get_initial_data")
        query = parse("$.sources[?(@.type=='device-info')]")
        sources = query.find(self.data)

        async with httpx.AsyncClient(verify=False) as client:
            await asyncio.gather(*(self._call_url(client, s) for s in sources))

        if self._in_error:
            raise Exception("Initialization failed, is your device on?")

        if not self._live_config_update:
            await self.fetch_config()
        await self.fetch_data()
        _LOGGER.debug("Initial data loaded for %s", self.ip)
        return self.data

    async def fetch_config(self, config_path: Optional[str] = None) -> None:
        """Fetch cached configuration sources.

        Args:
            config_path: If provided, fetch only that specific source name.
                         Otherwise fetch all sources where `type == "config"`.
        """
        _LOGGER.debug("reefbeat.fetch_config")
        if config_path is None:
            query = parse("$.sources[?(@.type=='config')]")
        else:
            query = parse("$.sources[?(@.name=='" + config_path + "')]")
        sources = query.find(self.data)

        async with httpx.AsyncClient(verify=False) as client:
            await asyncio.gather(*(self._call_url(client, s) for s in sources))

    async def fetch_data(self) -> None:
        """Fetch cached data sources.

        Behavior:
            - If `quick_refresh` is set, fetch only that source once.
            - If live config update is enabled, fetch most non-device-info sources.
            - Otherwise fetch only sources where `type == "data"`.
        """
        if self.quick_refresh is not None:
            query = parse("$.sources[?(@.name=='" + self.quick_refresh + "')]")
            sources = query.find(self.data)
            self.quick_refresh = None
        else:
            if self._live_config_update:
                query = parse("$.sources[?(@.type!='device-info' & @.type!='preview')]")
            else:
                query = parse("$.sources[?(@.type=='data')]")
            sources = query.find(self.data)

        async with httpx.AsyncClient(verify=False) as client:
            await asyncio.gather(*(self._call_url(client, s) for s in sources))

    async def press(self, action: str, head: Optional[int] = None) -> None:
        """Trigger a button-like action.

        Args:
            action: Action segment (without leading slash).
            head: Optional head index for devices that support it (Dose).
        """
        suffix = f"/{action}"
        if head is not None:
            suffix += f"/{head}"
        _LOGGER.debug("Sending: %s", suffix)
        await self._http_send(self._base_url + suffix, payload="", method="post")

    async def delete(self, source: str) -> None:
        """DELETE a resource by source path (e.g. '/something')."""
        await self._http_send(self._base_url + source, method="delete")

    def get_path(self, obj: Any) -> str:
        """Return a Python-access path for a JSONPath match context.

        This builds a string such as `["sources"][0]["data"]` which is later used
        to build a cached `eval()` expression for fast `get_data()` access.
        """
        res = ""
        if hasattr(obj, "context") and obj.context is not None:
            res += self.get_path(obj.context)
        if hasattr(obj, "path"):
            if str(obj.path) != "$":
                res += (
                    '["' + str(obj.path) + '"]'
                    if str(obj.path)[0] != "["
                    else str(obj.path)
                )
        return res

    def get_data_link(self, data_name: str) -> Optional[str]:
        """Compute an eval()-able expression path into `self.data` for a JSONPath expression."""
        query = parse(data_name)
        res = query.find(self.data)
        if not res:
            return None
        path = self.get_path(res[0])
        return "data" + path

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        """Read a cached value via JSONPath.

        Args:
            name: JSONPath expression into `self.data`.
            is_None_possible: If True, missing paths return None without logging.

        Notes:
            For performance, successful JSONPath resolutions are cached as eval()-able
            strings in `self._data_db`. Structure changes can invalidate cached paths;
            `set_data()` will clear the cache entry on update failures.
        """
        if name not in self._data_db:
            r = self.get_data_link(name)
            if r is not None:
                self._data_db[name] = "self." + r
            else:
                if not is_None_possible:
                    _LOGGER.error("reefbeat.get_data('%s') %s", name, self._base_url)
                    _LOGGER.error("%s", self.data)
                return None

        try:
            return eval(self._data_db[name])
        except Exception as e:
            if is_None_possible:
                return None
            raise e

    def _get_data(self, data_name: str, is_None_possible: bool = False) -> Any:
        """Slow-path getter that evaluates JSONPath every call (debug/legacy)."""
        query = parse(data_name)
        res = query.find(self.data)
        if not res:
            if not is_None_possible:
                _LOGGER.error("reefbeat.get_data('%s') %s", data_name, self._base_url)
                _LOGGER.error("%s", self.data)
            return None
        return res[0].value

    def set_data(self, data_name: str, value: Any) -> None:
        """Set a value via JSONPath update.

        Clears the cached eval-path for this JSONPath if the update fails because the
        underlying structure changed.
        """
        query = parse(data_name)
        try:
            query.update(self.data, value)
        except Exception:
            _LOGGER.error("reefbeat.set_data('%s')", data_name)
            # If a cached path is now wrong due to structure changes, force a rebuild.
            self._data_db.pop(data_name, None)

    async def http_send(
        self, action: str, payload: Any = None, method: str = "post"
    ) -> Optional[httpx.Response]:
        """Send an HTTP request to an action path relative to this API base URL.

        Args:
            action: Endpoint path beginning with '/', appended to `self._base_url`.
            payload: JSON payload to send (or None).
            method: HTTP method ('post', 'put', 'delete').

        Returns:
            The final `httpx.Response` if a request was performed, else None.
        """
        return await self._http_send(self._base_url + action, payload, method)

    async def _http_send(
        self, url: str, payload: Any = None, method: str = "post"
    ) -> Optional[httpx.Response]:
        """Send an HTTP request with retries.

        Args:
            url: Absolute URL.
            payload: JSON payload (for POST/PUT). Ignored for DELETE.
            method: HTTP method ('post', 'put', 'delete').

        Returns:
            The final `httpx.Response` if a request was performed, else None.

        Side effects:
            - Updates `self.data["message"]` on success if the response contains JSON.
        """
        status_ok = False
        error_count = 0
        _LOGGER.debug("%s data: %s to %s", method, payload, url)

        r: Optional[httpx.Response] = None
        async with httpx.AsyncClient(verify=False, timeout=DEFAULT_TIMEOUT) as client:
            while status_ok is False and error_count < HTTP_MAX_RETRY:
                try:
                    if method == "post":
                        r = await client.post(url, json=payload, headers=self._header)
                    elif method == "put":
                        r = await client.put(url, json=payload, headers=self._header)
                    elif method == "delete":
                        r = await client.delete(url, headers=self._header)
                    else:
                        raise ValueError(f"Unsupported method: {method}")

                    status_code = getattr(r, "status_code", None)
                    status_ok = status_code in (200, 201, 202)

                    if status_code in (400, 404):
                        error_count = HTTP_MAX_RETRY

                    if not status_ok:
                        _LOGGER.error("%d: %s", status_code, getattr(r, "text", ""))
                        error_count += 1
                    else:
                        _LOGGER.debug("%d: %s", status_code, getattr(r, "text", ""))
                        try:
                            raw = r.json()
                            msg: dict[str, Any]
                            if isinstance(raw, dict):
                                # json() returns dict[str, Any] in practice, but type is Any
                                msg = cast(dict[str, Any], raw)
                            else:
                                msg = {"data": raw}
                            if "alert" not in msg:
                                msg["alert"] = ""
                            self.data["message"] = msg
                        except Exception:
                            self.data["message"] = {}
                except Exception as e:
                    error_count += 1
                    _LOGGER.debug(
                        "Can not %s data: %s to %s, retry nb %d/%d",
                        method,
                        payload,
                        url,
                        error_count,
                        HTTP_MAX_RETRY,
                    )
                    _LOGGER.debug(e)

                if status_ok is False:
                    await asyncio.sleep(HTTP_DELAY_BETWEEN_RETRY)

        if status_ok is False:
            _LOGGER.error("Can not push data to %s", url)
        return r

    async def push_values(self, source: str, method: str = "post") -> None:
        """Push the currently cached payload for `source` to the device."""
        payload = self.get_data(
            "$.sources[?(@.name=='" + source + "')].data", is_None_possible=True
        )
        if payload is None:
            _LOGGER.error("push_values: no payload found for source=%s", source)
            return
        await self._http_send(self._base_url + source, payload, method)

    @property
    def live_config_update(self) -> bool:
        """Whether live configuration update is enabled."""
        return bool(self._live_config_update)

    def set_live_config_update(self, enabled: bool) -> None:
        """Enable/disable live config updates.

        When disabled, `fetch_data()` will only load sources marked as `type=="data"`.
        When enabled, `fetch_data()` will also refresh most config sources.
        """
        self._live_config_update = bool(enabled)

    def add_source(self, name: str, source_type: str, data: Any = "") -> None:
        """Register a new source entry in `self.data["sources"]`.

        Args:
            name: Endpoint path (e.g. '/dashboard').
            source_type: One of 'device-info', 'config', 'data', 'preview', etc.
            data: Initial cached value.
        """
        if "sources" not in self.data or not isinstance(self.data["sources"], list):
            self.data["sources"] = cast(list[SourceEntry], [])

        sources = cast(list[SourceEntry], self.data["sources"])
        sources.insert(
            len(sources),
            {"name": name, "type": source_type, "data": data},
        )

    def remove_source(self, name: str) -> None:
        """Remove a source entry by name (no error if not present)."""
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        self.data["sources"] = [s for s in sources if s.get("name") != name]

    def clear_cache(self) -> None:
        """Clear the internal JSONPath eval cache used by `get_data()`."""
        self._data_db.clear()

    def reset_error_state(self) -> None:
        """Clear the internal error flag set during fetch retries."""
        self._in_error = False
