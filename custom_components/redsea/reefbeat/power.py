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

# Defaults pushed to a freshly installed local temperature probe via
# `PUT /temperature/config`. Without this push the probe stays in "config"
# limbo (mirrors sockets needing `/setup-finish`) and never reports data —
# these are exactly the values the ReefBeat app itself seeds on first pairing.
_TEMPERATURE_CONFIG_DEFAULTS: dict[str, Any] = {
    "desired_range_low": 25,
    "desired_range_high": 26,
    "acceptable_range_low": 24,
    "acceptable_range_high": 28,
    "name": "Temp",
    "notifications_enabled": True,
    "log_enabled": True,
}


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
        socket_count: int = 6,
    ) -> None:
        """Initialize the ReefPower API wrapper.

        Registers `/configuration` and `/sockets/config` as config sources so
        that socket limits, LED colors, current thresholds and per-socket
        mode/name are polled with config refreshes.

        Each socket's on/off programme is registered too, so it is already in
        hand when something asks for it. `socket_count` decides how many:
        polling a socket the model does not have would add a failing request
        to every config refresh.
        """
        super().__init__(ip, live_config_update, session)

        # Register extra config sources (polled on config refreshes).
        names = ["/configuration", "/sockets/config"]
        names.extend(f"/socket/{idx}/config/schedule" for idx in range(socket_count))

        sources = cast(list[SourceEntry], self.data.get("sources", []))
        for name in names:
            sources.insert(
                len(sources),
                {"name": name, "type": "config", "data": ""},
            )
        self.data["sources"] = sources

    # -- Local temperature probe (offset, ranges, name, notify/log) --------
    # ``/temperature/config`` and ``/temperature/subscriptions`` both answer
    # GET only once a probe is installed; with none present they 404. So
    # they are registered on demand (when ``/dashboard.temperature`` is
    # present) rather than up front — avoiding a wasted GET (404 + retry)
    # when there is nothing to read. They are registered as **data** sources
    # (not config): that way they keep refreshing on every regular poll
    # cycle, the same as /dashboard, rather than only when config sources
    # are polled (which may be far less frequent, or never, if
    # `live_config_update` is off).
    _TEMP_CONFIG_SOURCE = "/temperature/config"
    _TEMP_SUBSCRIPTIONS_SOURCE = "/temperature/subscriptions"

    def _reconcile_temperature_sources(self) -> None:
        present = (
            self.get_data(
                "$.sources[?(@.name=='/dashboard')].data.temperature",
                is_None_possible=True,
            )
            is not None
        )
        for name in (self._TEMP_CONFIG_SOURCE, self._TEMP_SUBSCRIPTIONS_SOURCE):
            sources = cast(list[SourceEntry], self.data.get("sources", []))
            exists = any(s.get("name") == name for s in sources)
            if present and not exists:
                self.add_source(name, "data", "")
            elif not present and exists:
                self.remove_source(name)
        # No cache invalidation needed: both are read non-positionally
        # (volatile paths) and fixed sources keep their slots.

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch, registering the local-temp sources on demand.

        Refresh the dashboard first so the presence of a local temperature probe
        is current, then reconcile the ``/temperature/config`` and
        ``/temperature/subscriptions`` sources before the full fetch — so a
        just-removed probe's endpoints are dropped before they would be polled
        (and 404 + retry), and a newly-detected probe's sources are picked up
        by this same full fetch.
        """
        if self.quick_refresh is None and self._live_config_update:
            self.quick_refresh = "/dashboard"
            await super().fetch_data()
            self._reconcile_temperature_sources()
        data = await super().fetch_data()
        self._reconcile_temperature_sources()
        return data

    def temperature_offset(self) -> float | None:
        """Cached local-temperature calibration offset, if known."""
        return self.get_data(
            "$.sources[?(@.name=='/temperature/config')].data.offset",
            is_None_possible=True,
        )

    async def set_temperature_offset(self, offset: float) -> HttpResult | None:
        """Set the local temperature offset (``POST /probe/offset``)."""
        return await self.http_send("/probe/offset", {"offset": offset}, "post")

    async def reset_temperature_offset(self) -> HttpResult | None:
        """Clear the local temperature offset (``DELETE /probe/offset``)."""
        return await self.http_send("/probe/offset", None, "delete")

    async def install_temperature(self) -> HttpResult | None:
        """Scan for and install the local temperature probe.

        The type is fixed (a strip takes only a temperature probe), so no type
        selection is needed. BLE advertising of the new probe is stopped after,
        then its info is polled once (mirrors the app; the response carries no
        state we track) and its configuration is seeded with defaults —
        otherwise the probe is left in "config" limbo and never reports data,
        the same way a socket needs `/setup-finish` to leave setup mode.
        """
        result = await self.http_send(
            "/sensor/install", {"type": "temperature"}, "post"
        )
        payload = result.get("json") if isinstance(result, dict) else None
        uid = payload.get("uid") if isinstance(payload, dict) else None
        if uid:
            await self.http_send("/ble/off", {"type": "temperature"}, "post")
            self.add_source("/temperature-probe-info", "config", "")
            await self.fetch_config("/temperature-probe-info")
            self.remove_source("/temperature-probe-info")
            await self.http_send(
                "/temperature/config", dict(_TEMPERATURE_CONFIG_DEFAULTS), "put"
            )
            # _reconcile_temperature_sources() gates on /dashboard's cached
            # temperature reading, which is still stale here (the dashboard
            # has not been re-fetched since the probe was installed) —
            # register both sources directly and fetch them now (fetch_config()
            # matches by name, so the "data" type does not stop this targeted
            # call), so the range/name/notification/log entities — and any
            # socket already subscribed to this probe — read back confirmed
            # values immediately, instead of showing nothing until the next
            # poll.
            sources = cast(list[SourceEntry], self.data.get("sources", []))
            existing_names = {s.get("name") for s in sources}
            for name in (self._TEMP_CONFIG_SOURCE, self._TEMP_SUBSCRIPTIONS_SOURCE):
                if name not in existing_names:
                    self.add_source(name, "data", "")
                await self.fetch_config(name)
        return result

    async def remove_temperature(self) -> HttpResult | None:
        """Remove the local temperature probe (``DELETE /sensor``).

        Drops ``/temperature/config`` and ``/temperature/subscriptions``
        immediately rather than waiting for the next refresh's reconciliation
        (gated on ``/dashboard.temperature``, which may lag behind the
        removal by a cycle or two) — otherwise they keep getting polled and
        erroring for a while after the probe is already gone.
        """
        result = await self.http_send("/sensor", None, "delete")
        for name in (self._TEMP_CONFIG_SOURCE, self._TEMP_SUBSCRIPTIONS_SOURCE):
            sources = cast(list[SourceEntry], self.data.get("sources", []))
            if any(s.get("name") == name for s in sources):
                self.remove_source(name)
        return result

    async def set_socket_mode(
        self, number: int, mode: str, name: str | None = None
    ) -> HttpResult | None:
        """Set a socket's mode via ``PUT /sockets/config``.

        The device accepts a partial update: only the changed socket is sent.
        ``mode`` is one of ``off`` / ``on`` / ``schedule`` / ``sensor``.
        ``name`` must always be included because the firmware requires it.
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
