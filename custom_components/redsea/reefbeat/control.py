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

Per-port configuration (mirrors the RSPOWER socket API, different wire shape):
    - GET  /ports/config      — bare array of port entries
    - PUT  /ports/config      — bare array, partial update per port
    - PUT  /port/<n>/schedule — {"intervals":[{"time","duration"}]}
    - POST /port/<n>/toggle   — flip the port state
    - POST /setup-finish      — leave setup mode (device switches to auto)

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

from .api import HttpResult, ReefBeatAPI, SourceEntry

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

        # Register the config sources polled with config refreshes.
        #
        # `/ports/config` is required (not merely nice to have) because
        # `PUT /ports/config` is a *whole-entry* write: the app always resends
        # `type`, `enabled`, `power_on_percent`, `power_detector_enabled` and
        # `is_btn_assigned` alongside the changed field, and `/dashboard`
        # carries none of those.
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        for name in ("/configuration", "/ports/config", "/subscription-info"):
            sources.insert(
                len(sources),
                {"name": name, "type": "config", "data": ""},
            )
        self.data["sources"] = sources

    # Wire values of `ControlPort$PortType` in the Red Sea app:
    #   NONE -> "unknown"  (port not installed yet)
    #   NON_RED_SEA_DEVICE -> "other"  (any third-party 12V device)
    #   ATO -> "ato"       (Red Sea ATO kit, installed by the app's wizard)
    PORT_TYPE_UNINSTALLED = "unknown"
    PORT_TYPE_OTHER = "other"
    PORT_TYPE_ATO = "ato"

    def port_config(self, number: int) -> dict[str, Any] | None:
        """Return the cached `/ports/config` entry for a port, if any."""
        entry = self.get_data(
            f"$.sources[?(@.name=='/ports/config')].data[?(@.number=={int(number)})]",
            is_None_possible=True,
        )
        return entry if isinstance(entry, dict) else None

    def port_is_installed(self, number: int) -> bool:
        """Whether a 12V port has been installed (assigned a device type).

        A factory-fresh port reports ``type == "unknown"`` and ``mode ==
        "setup"``. In that state the firmware rejects every write with
        ``503 "Failed configuring ports - port not installed …"`` and answers
        ``POST /port/<n>/toggle`` with ``"Failed to toggle port"``, so callers
        must not attempt either.
        """
        entry = self.port_config(number)
        if entry is None:
            # Fall back to /dashboard, which also carries the port type.
            entry = self.get_data(
                "$.sources[?(@.name=='/dashboard')].data.ports"
                f"[?(@.number=={int(number)})]",
                is_None_possible=True,
            )
        if not isinstance(entry, dict):
            return False
        return entry.get("type") not in (None, self.PORT_TYPE_UNINSTALLED)

    async def install_port(
        self, number: int, ptype: str = PORT_TYPE_OTHER
    ) -> HttpResult | None:
        """Install a 12V port via ``POST /port/<n>/install``.

        This is the step the ReefBeat app performs first in its port wizard,
        and the one without which every later write fails. Body is
        ``{"type": "other"}`` for a third-party device; the firmware answers
        ``{"success":true,"message":"Port installed successfully"}``.
        """
        return await self.http_send(
            f"/port/{int(number)}/install", {"type": ptype}, "post"
        )

    async def set_port_mode(
        self, number: int, mode: str, name: str | None = None
    ) -> HttpResult | None:
        """Set a 12V port's mode via ``PUT /ports/config``.

        Two things differ from :meth:`ReefPowerAPI.set_socket_mode`, and both
        were confirmed by capturing the app configuring a real port:

        1. The body is a **bare JSON array** of port entries, not a
           ``{"sockets": [...]}`` wrapper.
        2. The firmware wants the **whole entry**. The app resends ``type``,
           ``enabled``, ``power_on_percent``, ``power_detector_enabled`` and
           ``is_btn_assigned`` on every write, so we rebuild them from the
           cached ``/ports/config`` rather than sending a partial body and
           hoping the firmware preserves the omitted keys.

        The port must already be installed — see :meth:`install_port`.
        """
        entry = self.port_config(number) or {}
        port: dict[str, Any] = {"number": int(number), "mode": mode}
        for key in (
            "name",
            "type",
            "enabled",
            "power_on_percent",
            "power_detector_enabled",
            "is_btn_assigned",
        ):
            if key in entry:
                port[key] = entry[key]
        if name is not None:
            port["name"] = name
        result = await self.http_send("/ports/config", [port], "put")

        # Keep the cached entry in sync. `/ports/config` is a *config* source,
        # so it is only re-fetched on a config refresh; without this, renaming
        # a port and then changing its mode would resend the stale name and
        # silently revert the rename.
        if entry and (result is None or result.get("ok", True)):
            entry.update({k: v for k, v in port.items() if k != "number"})
        return result

    async def delete_port(self, number: int) -> HttpResult | None:
        """Uninstall a 12V port via ``DELETE /port/<n>``.

        The firmware answers ``{"success":true,"message":"Successfully deleted
        port"}`` and resets the whole entry: ``type`` back to ``unknown``,
        ``mode`` to ``setup``, the name to its factory value (``S1`` / ``S2``)
        and ``power_on_percent`` to 100. Any schedule or sensor subscription
        on that port is dropped with it.
        """
        return await self.http_send(f"/port/{int(number)}", None, "delete")

    async def set_port_button_assigned(self, number: int) -> HttpResult | None:
        """Point the hub's physical button at a port.

        The assignment is exclusive — one port at a time — and the firmware
        self-heals a bad state ("Multiple ports had button assigned, clearing
        port N" / "No port had button assigned, defaulting to port 0"). The
        ReefBeat app sends this right after deleting a port, to hand the
        button over to the port that is left.

        Note this is a genuinely **partial** write: the app sends only
        ``[{"number": n, "is_btn_assigned": true}]`` and the firmware accepts
        it, applying just the fields present.
        """
        return await self.http_send(
            "/ports/config", [{"number": int(number), "is_btn_assigned": True}], "put"
        )

    async def unsubscribe_socket(self, number: int) -> HttpResult | None:
        """Drop a hub probe's binding to a socket of the paired power center.

        Two sides hold the same subscription and both must be cleared: the
        power center via ``PUT /unsubscribe {"sockets":[n]}`` and the hub via
        this call. The ReefBeat app issues them back to back when a
        sensor-driven socket is deleted.
        """
        return await self.http_send(f"/socket/{int(number)}/unsubscribe", {}, "put")

    async def set_port_schedule(
        self, number: int, intervals: list[dict[str, int]]
    ) -> HttpResult | None:
        """Set a port's daily schedule via ``PUT /port/<n>/schedule``.

        Must be called before switching the port to ``schedule`` mode, which
        the firmware otherwise refuses. ``intervals`` uses the same shape as
        the power center: ``{"time": <minutes from midnight>, "duration":
        <minutes>}`` — e.g. ``[{"time": 0, "duration": 1439}]`` for all day.
        """
        return await self.http_send(
            f"/port/{int(number)}/schedule",
            {"intervals": intervals},
            "put",
        )

    async def setup_finish(self) -> HttpResult | None:
        """Leave setup mode via ``POST /setup-finish`` (device switches to auto)."""
        return await self.http_send("/setup-finish", {}, "post")

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
