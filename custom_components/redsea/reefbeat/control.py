"""ReefBeat ReefControl API wrapper.

Provides helpers for the ReefControl hub (RSCONTROLPRO, RSCONTROLLITE), which
acts as the central hub for ReefSense digital probes and exposes 1 (Lite) or
2 (Pro) 12V DC output ports.

Endpoints confirmed on a real RSCONTROLPRO (firmware 1.1.9, framework 4.3.2)
by packet capture and by direct probing of the device:
    - GET /dashboard        — mode, cable_connected, connected power center,
                              probes[], ports[], buzzer, leak_detector
    - GET /configuration    — shortcut_off_delay, leak_buzzer_config and
                              danger_buzzer_config ({enabled, frequency,
                              duty_cycle}), leak_detector,
                              danger_debounce_seconds
    - GET /leak/config      — {notify, buzzer, leak_detector}
    - PUT /leak/config      — same + write-only `emergency_shutdown`
    - GET /ports/config     — array: per-port name/mode/enabled/detector/percent
    - GET /probe/config     — array: [{name, type, uid}]  (PUT renames a probe)
    - GET /subscription-info— {external:[…sockets…], internal:[…ports…]}
    - GET /mode             — current device mode
    - GET /time, /wifi, /cloud, /device-info, /firmware, /logging (base)

`leak_detector` appears on both `/configuration` and `/leak/config`; the buzzer
tone parameters only exist on `/configuration`, while `notify` and
`emergency_shutdown` only exist on `/leak/config`. See
doc/api/reef-control-power.md.

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

        # Register the ReefControl config sources.
        #
        # `/configuration` carries the device-wide settings (buzzer tone and
        # duty cycle for both the leak and danger alarms, leak_detector,
        # danger_debounce_seconds, shortcut_off_delay). The other four are
        # confirmed by app traffic and were previously unpolled: `/leak/config`
        # duplicates `leak_detector` but adds `notify`, `/ports/config` carries
        # the per-port settings absent from `/dashboard`, `/probe/config` holds
        # the user-chosen probe names, and `/subscription-info` reports which
        # probes drive which sockets/ports.
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        for name in (
            "/configuration",
            "/leak/config",
            "/ports/config",
            "/probe/config",
            "/subscription-info",
        ):
            sources.insert(
                len(sources),
                {"name": name, "type": "config", "data": ""},
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

    # ------------------------------------------------------------------
    # Leak / buzzer configuration
    # ------------------------------------------------------------------

    async def set_leak_config(
        self,
        *,
        leak_detector: bool | None = None,
        buzzer: bool | None = None,
        notify: bool | None = None,
        emergency_shutdown: bool | None = None,
    ) -> None:
        """Push a partial leak-detection configuration via ``PUT /leak/config``.

        Every field of the firmware's model is nullable, so only the keys we
        pass are modified. Sending an empty body makes the firmware answer
        "No valid fields to update", hence the early return.

        `emergency_shutdown` cuts the paired power center when a leak is
        detected; it is accepted on write but is absent from the GET payload.
        """
        payload: dict[str, Any] = {}
        if leak_detector is not None:
            payload["leak_detector"] = bool(leak_detector)
        if buzzer is not None:
            payload["buzzer"] = bool(buzzer)
        if notify is not None:
            payload["notify"] = bool(notify)
        if emergency_shutdown is not None:
            payload["emergency_shutdown"] = bool(emergency_shutdown)
        if not payload:
            return
        await self.http_send("/leak/config", payload, "put")

    async def buzzer_dismiss(self) -> None:
        """Acknowledge the currently active buzzer alarm."""
        await self.http_send("/buzzer/dismiss", {}, "post")

    async def buzzer_test(self) -> None:
        """Sound the buzzer briefly to verify it works."""
        await self.http_send("/buzzer/test", {}, "post")

    # ------------------------------------------------------------------
    # Probe management
    # ------------------------------------------------------------------

    async def rename_probe(self, uid: str, ptype: str, name: str) -> None:
        """Rename one probe via ``PUT /probe/config``.

        The endpoint takes the *whole* probe array, so the cached
        `/probe/config` source is replayed with only the target entry edited.
        Falls back to a single-entry array when the cache is not populated yet.
        """
        cached = self.get_data(
            "$.sources[?(@.name=='/probe/config')].data", is_None_possible=True
        )
        probes: list[dict[str, Any]]
        if isinstance(cached, list) and cached:
            probes = [dict(p) for p in cached]
            for probe in probes:
                if probe.get("uid") == uid:
                    probe["name"] = name
                    break
            else:
                probes.append({"name": name, "uid": uid, "type": ptype})
        else:
            probes = [{"name": name, "uid": uid, "type": ptype}]
        await self.http_send("/probe/config", probes, "put")

    async def probe_ble_advertising(self, uid: str, ptype: str, on: bool) -> None:
        """Start or stop BLE advertising on a probe (visual identification)."""
        action = "on" if on else "off"
        await self.http_send(f"/ble/{action}?type={ptype}&uid={uid}", {}, "post")

    # ------------------------------------------------------------------
    # Power center pairing
    # ------------------------------------------------------------------

    async def power_discover(self, pair: bool = False) -> Any:
        """Discover (and optionally pair with) a ReefControl-Power center.

        With ``pair=False`` the firmware only reports what it can see:
        ``{"hwid": …, "pairing_status": "unpaired"}``. With ``pair=True`` it
        performs the pairing and answers ``{"hwid": …, "paired": true}``.
        """
        return await self.http_send("/power/discover", {"pair": bool(pair)}, "post")

    async def power_unpair(self) -> None:
        """Forget the currently paired ReefControl-Power center."""
        await self.http_send("/power/unpair", {}, "post")

    # ------------------------------------------------------------------
    # Sensor -> socket subscriptions (on the paired power center)
    # ------------------------------------------------------------------

    async def subscribe_socket(
        self,
        socket: int,
        uid: str,
        ptype: str,
        *,
        sensor: str = "primary",
        is_above: bool = True,
        trigger_op: bool = True,
        hysteresis: float = 0,
        value: float | None = None,
    ) -> None:
        """Bind one hub probe to a socket of the paired power center.

        `is_above` selects the comparison direction and `trigger_op` the
        resulting socket operation; `value` is the threshold and is omitted
        for binary probes such as the leak detector. The socket must already
        be in `sensor` mode and have a `default_state` declared on the power
        center, otherwise the firmware refuses the mode change.
        """
        payload: dict[str, Any] = {
            "uid": uid,
            "type": ptype,
            "sensor": sensor,
            "is_above": bool(is_above),
            "trigger_op": bool(trigger_op),
            "hysteresis": hysteresis,
        }
        if value is not None:
            payload["value"] = value
        await self.http_send(f"/socket/{int(socket)}/subscribe", payload, "put")

    async def unsubscribe_socket(self, socket: int) -> None:
        """Remove the sensor binding from a socket of the power center."""
        await self.http_send(f"/socket/{int(socket)}/unsubscribe", {}, "put")
