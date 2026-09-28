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

ATO module — the Red Sea ATO kit (pump + ATO probe) on a 12V port, captured
while the app installed one on port 1 (port type ``ato``):
    - POST /port/<n>/install   {"uid": <ATO probe uid>, "type": "ato"}
    - POST /ato/update-volume  {"volume": <mL>} — reservoir volume left
    - PUT  /ato/configuration  {"volume_left", "port_index", "hose":
                               {"length", "height"} (cm), "auto_fill",
                               "notify", "rvm_enabled"}; answers the whole
                               configuration (also read by GET)
    - PUT  /ports/config       [{"number", "name": "ATO Module", "type":
                               "ato", "is_btn_assigned": true}, {other port,
                               "is_btn_assigned": false}]
    - PUT  /ato/configuration  {"pump_override": {"speed_override",
                               "flow_rate_override"}, "port_index"} — the
                               pump flow rate (mL/min, -1 back to default)
    - POST /ato/resume         {} — clear a fault (empty, stalled…)
    - POST /ato/manual-pump    {} / POST /ato/stop {} (app code, not captured)
The ``/dashboard`` entry of such a port carries ``auto_fill``,
``temp_log_enabled``, ``uid``, ``today_volume``, ``is_pump_on``,
``last_pump_on_cause`` and ``volume_left``; its ``mode`` reports the module's
faults (``missing_pump``, ``stalled``, ``empty``, ``timeout``, ``leak``,
``port_malfunction``), as the app's ``ControlPort.getAtoError`` reads them.
``PUT /ato/configuration`` is partial (the app sends only changed fields,
``ServerAtoConfiguration$Put`` has nullable fields only).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, cast

import aiohttp

from ..const import EC_UNIT_DEFAULT_RANGES
from .api import HttpResult, ReefBeatAPI, SourceEntry
from .fusion import is_probe_disconnected

_LOGGER = logging.getLogger(__name__)


def _as_dict(value: Any) -> dict[str, Any] | None:
    """A JSON object from the cache, typed, or None for anything else."""
    return cast(dict[str, Any], value) if isinstance(value, dict) else None


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
        for name in (
            "/configuration",
            "/ports/config",
            "/probe/config",
        ):
            sources.insert(
                len(sources),
                {"name": name, "type": "config", "data": ""},
            )
        # `/subscription-info` holds the probe -> socket rules of the paired
        # power center (`external`) and of the hub's own ports (`internal`).
        # Polled as data, not config: a rule may be changed outside Home
        # Assistant (ReefBeat app), and the RSPower socket_N_mode sensors
        # expose it as their `sensor_config`.
        sources.insert(
            len(sources),
            {"name": "/subscription-info", "type": "data", "data": ""},
        )
        self.data["sources"] = sources

    # -- Dynamic per-probe offset sources ------------------------------------
    # A single-point calibration offset is read via
    # ``GET /probe/offset?type=<type>&uid=<uid>`` — one endpoint per probe
    # (``{"offset", "last_adjustment_date"}``): the reading of a temperature
    # or ORP probe, the embedded temperature of a pH, EC or ATO probe.
    # Probes come and go at runtime, so these sources are reconciled after
    # every dashboard fetch rather than registered up front.
    _OFFSET_PREFIX = "/probe/offset?type="
    # pH, EC and ATO probes: the offset of their embedded temperature sensor
    # (captured: ``/probe/offset?type=ph`` and ``?type=ec`` move
    # ``temp_value``).
    _OFFSET_TYPES: tuple[str, ...] = ("temperature", "orp", "ph", "ec", "ato")
    # Probe types whose own reading has no offset, only their temperature
    _TEMPERATURE_OFFSET_TYPES: frozenset[str] = frozenset({"ph", "ec", "ato"})
    # Decimals an offset is kept with, per probe type (whole millivolts).
    _OFFSET_DIGITS: dict[str, int] = {"orp": 0}

    @classmethod
    def _offset_source_name(cls, uid: str, ptype: str = "temperature") -> str:
        return f"{cls._OFFSET_PREFIX}{ptype}&uid={uid}"

    def _reconcile_probe_offset_sources(self) -> None:
        """Keep dynamic probe-dependent sources in sync with the probes.

        Two kinds: one ``/probe/offset`` source per temperature or ORP probe, and
        ``/leak/config`` when a leak probe exists (its buzzer/notify live there,
        not in ``/probe/config``). These are read non-positionally, so no cache
        invalidation is needed and the fixed sources keep their front slots.
        """
        probes = (
            self.get_data(
                "$.sources[?(@.name=='/dashboard')].data.probes", is_None_possible=True
            )
            or []
        )
        # An unplugged probe answers 503 to its offset endpoint: drop its
        # source while it is disconnected (no pointless request every poll),
        # it is registered again as soon as the dashboard reports it back.
        wanted = {
            self._offset_source_name(p["uid"], str(p.get("type", "")).lower())
            for p in probes
            if isinstance(p, dict)
            and str(p.get("type", "")).lower() in self._OFFSET_TYPES
            and p.get("uid")
            and not is_probe_disconnected(p)
        }
        has_leak = any(
            isinstance(p, dict) and str(p.get("type", "")).lower() == "leak"
            for p in probes
        )
        if has_leak:
            wanted.add("/leak/config")
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        existing = {
            s.get("name")
            for s in sources
            if str(s.get("name", "")).startswith(self._OFFSET_PREFIX)
            or s.get("name") == "/leak/config"
        }
        if wanted == existing:
            return
        for name in wanted - existing:
            self.add_source(name, "config", "")
        for name in existing - wanted:
            self.remove_source(name)

    # ── Optimistic updates ─────────────────────────────────────────────

    _PORT_PATH = re.compile(r"^/port/(\d+)(/install)?$")
    _SOCKET_UNSUBSCRIBE = re.compile(r"^/socket/(\d+)/unsubscribe$")

    def _source(self, name: str) -> Any:
        """Cached payload of a source (the live object, not a copy)."""
        return self.get_data(
            f"$.sources[?(@.name=='{name}')].data", is_None_possible=True
        )

    def _dashboard_port(self, number: int) -> dict[str, Any] | None:
        ports = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.ports", is_None_possible=True
        )
        if isinstance(ports, list):
            for raw in cast(list[Any], ports):
                entry = _as_dict(raw)
                if entry is not None and entry.get("number") == number:
                    return entry
        return None

    def dashboard_port(self, number: int) -> dict[str, Any] | None:
        """Live ``/dashboard`` entry of a 12V port, None when not listed."""
        return self._dashboard_port(number)

    def _update_port(self, number: int, fields: dict[str, Any]) -> None:
        """Set fields of a port in `/ports/config` and `/dashboard`."""
        entry = self.port_config(number)
        if entry is not None:
            entry.update(fields)
        dash = self._dashboard_port(number)
        if dash is not None:
            for key in ("mode", "type", "name"):
                if key in fields:
                    dash[key] = fields[key]
            if "mode" in fields:
                dash["user_config_mode"] = fields["mode"]

    def _replace_rules(
        self, kind: str, number: int, rule: dict[str, Any] | None
    ) -> None:
        """Replace a port's (``internal``) or socket's (``external``) rule."""
        info = self._source("/subscription-info")
        if not isinstance(info, dict):
            return
        rules: Any = cast(dict[str, Any], info).get(kind)
        kept: list[Any] = []
        for raw in cast(list[Any], rules) if isinstance(rules, list) else []:
            entry = _as_dict(raw)
            if entry is None or entry.get("number") != number:
                kept.append(raw)
        if rule is not None:
            kept.append(rule)
        info[kind] = kept

    def _mirror_write(
        self, action: str, payload: Any, method: str, result: HttpResult
    ) -> None:
        """Apply the hub's port and pairing writes to the cache at once.

        Covers what the card writes through ``redsea.request`` as much as the
        integration's own calls: a port's mode, name or power
        (``PUT /ports/config``), its probe rule (``PUT /ports/subscribe``),
        installing or uninstalling it, and unpairing the power center.
        """
        if action.startswith("/ato/"):
            self._mirror_ato_write(action, payload, method, result)
            return
        if method == "put" and action == "/ports/config":
            for raw in cast(list[Any], payload) if isinstance(payload, list) else []:
                entry = _as_dict(raw)
                if entry is not None and isinstance(entry.get("number"), int):
                    self._update_port(
                        entry["number"],
                        {k: v for k, v in entry.items() if k != "number"},
                    )
            return
        if method == "put" and action == "/ports/subscribe":
            ports: Any = (
                cast(dict[str, Any], payload).get("ports")
                if isinstance(payload, dict)
                else None
            )
            for raw in cast(list[Any], ports) if isinstance(ports, list) else []:
                rule = _as_dict(raw)
                if rule is not None and isinstance(rule.get("number"), int):
                    self._replace_rules("internal", rule["number"], dict(rule))
            return
        if method == "post" and action == "/power/unpair":
            dashboard = self._source("/dashboard")
            if isinstance(dashboard, dict):
                dashboard["connected_device"] = None
            return
        match = self._SOCKET_UNSUBSCRIBE.match(action)
        if match and method == "put":
            self._replace_rules("external", int(match.group(1)), None)
            return
        match = self._PORT_PATH.match(action)
        if match is None:
            return
        number = int(match.group(1))
        if match.group(2) and method == "post" and isinstance(payload, dict):
            ptype: Any = cast(dict[str, Any], payload).get("type")
            if isinstance(ptype, str):
                self._update_port(number, {"type": ptype})
                if ptype == self.PORT_TYPE_ATO:
                    dash = self._dashboard_port(number)
                    if dash is not None:
                        dash["uid"] = cast(dict[str, Any], payload).get("uid")
                        dash.pop("state", None)
        elif not match.group(2) and method == "delete":
            # What the firmware resets the port to (see delete_port)
            self._update_port(
                number,
                {
                    "type": self.PORT_TYPE_UNINSTALLED,
                    "mode": "setup",
                    "name": f"S{number + 1}",
                    "power_on_percent": 100,
                    "sensor": None,
                },
            )
            self._replace_rules("internal", number, None)

    # ── Port schedules ──────────────────────────────────────────────────

    _PORT_SCHEDULE = "/port/{}/schedule"

    def _port_modes(self, from_config: bool) -> dict[int, str]:
        """Mode of each 12V port, keyed by its 0-based number.

        Read from ``/ports/config`` right after a config fetch (fresh there),
        else from ``/dashboard`` (fresh on every poll); the other source is
        the fallback when the preferred one is not cached yet.
        """
        paths = [
            "$.sources[?(@.name=='/dashboard')].data.ports",
            "$.sources[?(@.name=='/ports/config')].data",
        ]
        if from_config:
            paths.reverse()
        for path in paths:
            ports = self.get_data(path, is_None_possible=True)
            if not isinstance(ports, list):
                continue
            modes: dict[int, str] = {}
            for idx, raw in enumerate(cast(list[Any], ports)):
                if not isinstance(raw, dict):
                    continue
                entry = cast(dict[str, Any], raw)
                number = entry.get("number", idx)
                if isinstance(number, int):
                    modes[number] = str(entry.get("mode", ""))
            return modes
        return {}

    def _reconcile_port_schedule_sources(self, from_config: bool) -> list[str]:
        """Poll a port's schedule only while the port runs on it.

        An uninstalled port (mode ``setup``) answers ``503`` to
        ``GET /port/<n>/schedule``, and a port that is on, off or driven by a
        probe does not use its schedule: its source is registered only while
        the port is in ``schedule`` mode. Returns the sources just added, for
        the caller to fetch at once (they would otherwise wait for the next
        config refresh).
        """
        wanted = {
            self._PORT_SCHEDULE.format(number)
            for number, mode in self._port_modes(from_config).items()
            if mode == "schedule"
        }
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        existing = {
            str(s.get("name"))
            for s in sources
            if str(s.get("name", "")).startswith("/port/")
            and str(s.get("name", "")).endswith("/schedule")
        }
        added = sorted(wanted - existing)
        for name in added:
            self.add_source(name, "config", "")
        for name in existing - wanted:
            self.remove_source(name)
        return added

    async def _sync_port_schedules(self, from_config: bool) -> None:
        """Reconcile the schedule sources and fetch the new ones."""
        for name in self._reconcile_port_schedule_sources(from_config):
            await super().fetch_config(name)

    async def fetch_config(self, config_path: str | None = None) -> None:
        """Fetch config sources, then the schedules the ports now use."""
        await super().fetch_config(config_path)
        if config_path is None:
            await self._sync_port_schedules(from_config=True)

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch, keeping per-probe offset sources in sync with the probes.

        The dashboard is refreshed first (cheap, single source) so probe
        presence is current, then the offset sources are reconciled *before* the
        full fetch. This drops the endpoint of a just-removed probe before it
        would be polled — otherwise it 404s and burns the retry budget.
        """
        if self.quick_refresh is None and self._live_config_update:
            self.quick_refresh = "/dashboard"
            await super().fetch_data()
            self._reconcile_probe_offset_sources()
        data = await super().fetch_data()
        self._reconcile_probe_offset_sources()
        await self._sync_port_schedules(from_config=False)
        if self._reconcile_ato_source():
            await self.fetch_config(self.ATO_CONFIG)
        await self._read_new_leaks()
        await self._refresh_config_on_probe_install()
        return data

    # -- Probe (re)installed elsewhere -----------------------------------------
    # Installing a probe (again) resets its settings on the hub: a reinstalled
    # ORP probe is back to its default ranges. Config sources are only read at
    # startup and after the integration's own writes, so a probe installed
    # from the ReefBeat app would keep its old ranges here while the hub
    # judges its level against the new ones. Every probe carries
    # `last_installation_date` in /dashboard: when a probe appears or that
    # date changes, /probe/config is read again.

    def _probe_install_dates(self) -> dict[str, Any]:
        probes = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.probes", is_None_possible=True
        )
        dates: dict[str, Any] = {}
        for raw in cast(list[Any], probes) if isinstance(probes, list) else []:
            probe = _as_dict(raw)
            if probe is not None and probe.get("uid"):
                key = f"{str(probe.get('type', '')).lower()}:{probe['uid']}"
                dates[key] = probe.get("last_installation_date")
        return dates

    async def _refresh_config_on_probe_install(self) -> None:
        dates = self._probe_install_dates()
        known: dict[str, Any] | None = getattr(self, "_known_install_dates", None)
        self._known_install_dates = dates
        # The first poll comes with a full config read already
        if known is None:
            return
        if any(key not in known or known[key] != date for key, date in dates.items()):
            _LOGGER.debug("Probe installed or reinstalled: reading /probe/config")
            await self.fetch_config("/probe/config")

    # -- Leak origin ---------------------------------------------------------
    # `/dashboard` only says whether a leak probe is wet (`detected`). Where
    # the water comes from is in the probe's own reading, `GET /probe`:
    #   {"name", "status", "ec", "leak_status"}
    # `leak_status` is `dry`, `aquarium_water_leak` or `rodi_water_leak` (the
    # ReefBeat app's ControlLeakStatus, the same values as the RSATO+ leak
    # sensor) and `ec` the conductivity the probe measures — salt water
    # conducts, RO/DI water hardly does. The reading is kept apart from the
    # dashboard, which each poll replaces whole.
    _LEAK_SOURCES: tuple[str, ...] = ("aquarium_water_leak", "rodi_water_leak")

    def _leak_readings(self) -> dict[str, dict[str, Any]]:
        """Last reading of each leak probe, by uid."""
        return cast(
            dict[str, dict[str, Any]], self.__dict__.setdefault("_leak_cache", {})
        )

    def _wet_leaks(self) -> set[str]:
        """Leak probes already read since they got wet."""
        return cast(set[str], self.__dict__.setdefault("_leak_wet", set()))

    async def _read_new_leaks(self) -> None:
        """Read a leak probe as soon as it turns wet, to learn the origin.

        Once per leak: a probe is read again only after it dried.
        """
        probes = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.probes",
            is_None_possible=True,
            cached=False,
        )
        wet = self._wet_leaks()
        for raw in cast(list[Any], probes) if isinstance(probes, list) else []:
            probe = _as_dict(raw)
            if probe is None or str(probe.get("type", "")).lower() != "leak":
                continue
            uid = str(probe.get("uid"))
            if probe.get("detected") is True:
                if uid not in wet:
                    wet.add(uid)
                    await self.read_probe("leak", uid)
            else:
                wet.discard(uid)

    def leak_status(self, uid: str) -> str | None:
        """Where a leak probe's water comes from.

        ``dry`` while the dashboard says the probe is dry, the origin of the
        last reading while it is wet, None while wet and not read yet.
        """
        probe = self.dashboard_probe("leak", uid)
        if probe is None or not isinstance(probe.get("detected"), bool):
            return None
        if not probe["detected"]:
            return "dry"
        status = self._leak_readings().get(uid, {}).get("leak_status")
        return status if status in self._LEAK_SOURCES else None

    def leak_conductivity(self, uid: str) -> float | None:
        """Conductivity a leak probe measured at its last reading."""
        value: Any = self._leak_readings().get(uid, {}).get("ec")
        return float(cast(float, value)) if self._is_number(value) else None

    async def calibrate_probe(
        self, ptype: str, uid: str, reference: float
    ) -> HttpResult | None:
        """Calibrate a probe's offset reading against a known reference.

        The reading of a temperature or ORP probe, the embedded temperature
        of a pH, EC or ATO probe. The probe is in a solution (ORP, mV) or
        water (°C) of known value: it is read now, and its offset is moved by
        ``reference - reading`` (the reading includes the current offset),
        so the probe then reads the reference. As the ReefBeat app's ORP
        validation does.
        """
        field = "temp_value" if ptype in self._TEMPERATURE_OFFSET_TYPES else "value"
        read = await self.read_probe(ptype, uid)
        probe = self.dashboard_probe(ptype, uid)
        reading: Any = probe.get(field) if probe else None
        if not read or not self._is_number(reading):
            _LOGGER.warning("%s probe %s: no reading, calibration skipped", ptype, uid)
            return None
        name = self._offset_source_name(uid, ptype)
        result = await self.shift_offset(
            name, name, reference - float(reading), self._OFFSET_DIGITS.get(ptype, 1)
        )
        if result is not None and result.get("ok"):
            # Until the next poll reads it back
            fresh = self.dashboard_probe(ptype, uid)
            if fresh is not None:
                fresh[field] = reference
        return result

    def calibration_date(self, ptype: str, uid: str) -> float | None:
        """Epoch of a probe's last calibration, None when never or unknown.

        pH and EC report it in ``/dashboard.probes[].last_adjustment_date``
        (null until calibrated). ORP has no such field there: its date is
        the offset's, ``GET /probe/offset`` -> ``last_adjustment_date``,
        updated by every ORP validation, even one leaving the offset as is.
        """
        value: Any
        # The offset of a temperature probe, or the embedded temperature of
        # a pH / EC one, is not their calibration
        if ptype == "orp":
            value = self.get_data(
                f"$.sources[?(@.name=='{self._offset_source_name(uid, ptype)}')]"
                ".data.last_adjustment_date",
                is_None_possible=True,
            )
        else:
            probe = self.dashboard_probe(ptype, uid)
            value = probe.get("last_adjustment_date") if probe else None
        return float(value) if self._is_number(value) and value > 0 else None

    # -- Probe install / delete --------------------------------------------
    # Seeded on ``PUT /probe/config`` right after install — otherwise the
    # probe answers but stays unconfigured (no ranges/buzzer/notify set),
    # mirroring RSPower's local temperature probe needing its own config
    # seeded on install. ``leak`` is set up apart (see _setup_leak_probe):
    # its ``/probe/config`` entry is just ``{name, type, uid}`` and its
    # buzzer/notify live in ``/leak/config`` (see ``_BUZZER_LOC``/
    # ``_NOTIFY_LOC``). Values mirror what a real hub reports for a probe
    # fresh off `/probe/install`.
    _PROBE_INSTALL_DEFAULTS: dict[str, dict[str, Any]] = {
        "ec": {
            "name": "EC",
            "buzzer": True,
            "notify": True,
            "unit": "ec",
            "ranges": [46.2, 49, 54.4, 59.7],
            "temp": {"ranges": [21, 23, 26, 28], "notify": True},
        },
        "ph": {
            "name": "pH",
            "buzzer": False,
            "notify": True,
            "ranges": [7.6, 7.9, 8.4, 8.6],
            "temp": {"ranges": [21, 23, 26, 28], "notify": True},
        },
        "orp": {
            "name": "ORP",
            "buzzer": False,
            "notify": True,
            "ranges": [100, 200, 400, 480],
        },
        "temperature": {
            "name": "Temperature",
            "buzzer": True,
            "notify": True,
            "ranges": [21, 23, 26, 28],
        },
        "ato": {
            # Replaced by _probe_default_name (uid digits, as the app does)
            "name": "ATO",
            "buzzer": False,
            "notify": True,
            "temp": {"ranges": [21, 23, 26, 28], "notify": True},
        },
    }

    # What the app writes to ``/leak/config`` when it installs a leak probe
    _LEAK_INSTALL_CONFIG: dict[str, bool] = {
        "buzzer": True,
        "leak_detector": True,
        "notify": True,
        "emergency_shutdown": False,
    }

    @staticmethod
    def _uid_digits(uid: str) -> str:
        """Significant digits of a probe uid: ``0x0032B`` gives ``32B``."""
        digits = uid.lower().removeprefix("0x").lstrip("0").upper()
        return digits or "0"

    @classmethod
    def _leak_probe_name(cls, uid: str) -> str:
        """Default name of a leak probe, as the app gives it: its uid digits.

        ``0x0032B`` gives ``Leak 32B`` (the app writes ``Fuite 32B`` in
        French), which tells two leak probes apart from the start.
        """
        return f"Leak {cls._uid_digits(uid)}"

    @classmethod
    def _ato_probe_name(cls, uid: str) -> str:
        """Default name of an ATO probe: its temperature and uid digits.

        Captured from the app in French, ``Temp. osmolateur 24E`` for
        ``0x0024E``: the probe is shown by its temperature, the water level
        belonging to the ATO module that uses it.
        """
        return f"ATO Temp. {cls._uid_digits(uid)}"

    async def _setup_leak_probe(self, uid: str) -> None:
        """Finish installing a leak probe the way the app does.

        Captured from the app: ``PUT /leak/config`` with the alarm settings,
        then ``PUT /probe/config`` with the probe's name. Until then the hub
        lists it with ``status: setup``, the app does not show it and it
        reports nothing; after it, ``status: auto``.
        """
        await self.http_send("/leak/config", dict(self._LEAK_INSTALL_CONFIG), "put")
        await self.http_send(
            "/probe/config",
            [{"name": self._leak_probe_name(uid), "uid": uid, "type": "leak"}],
            "put",
        )

    async def install_probe(self, ptype: str) -> HttpResult | None:
        """Ask the hub to scan for and install a new probe of ``ptype``.

        The device performs a BLE scan during the request and returns
        ``{"uid": ..., "success": true}`` on success or ``success: false`` /
        no uid when nothing is found. On success the BLE advertising of the
        new probe is stopped, then its config is seeded with defaults (see
        ``_PROBE_INSTALL_DEFAULTS``) and read back immediately — ``/probe/
        config`` is always registered (unlike RSPower's per-probe offset
        sources), so no on-demand registration is needed to refresh it.

        Same order as the app: install, read the probe's info, stop its BLE
        advertising, then configure it.
        """
        result = await self.http_send(f"/probe/install?type={ptype}", {}, "post")
        payload = _as_dict(result.get("json")) if isinstance(result, dict) else None
        uid: Any = payload.get("uid") if payload is not None else None
        if uid:
            # The answer (hwid, versions) is not kept: the app reads it too
            await self.http_get(f"/probe/info?type={ptype}&uid={uid}")
            await self.http_send(f"/ble/off?type={ptype}&uid={uid}", {}, "post")
            defaults = self._PROBE_INSTALL_DEFAULTS.get(ptype.lower())
            if ptype.lower() == "leak":
                await self._setup_leak_probe(str(uid))
                await self.fetch_config("/probe/config")
            elif defaults is not None:
                body = dict(defaults)
                body["type"] = ptype
                body["uid"] = uid
                if ptype.lower() == "ato":
                    body["name"] = self._ato_probe_name(str(uid))
                await self.http_send("/probe/config", [body], "put")
                await self.fetch_config("/probe/config")
        return result

    async def delete_probe(self, ptype: str, uid: str) -> HttpResult | None:
        """Remove a probe from the hub (``DELETE /probe?type&uid``).

        For a temperature or ORP probe, its calibration-offset source is dropped
        immediately rather than waiting for the next refresh's reconciliation
        (gated on the dashboard's probes list, which can lag behind the
        removal by a cycle or two) — otherwise it keeps getting polled (and
        erroring) for a while after the probe is already gone.
        """
        result = await self.http_send(f"/probe?type={ptype}&uid={uid}", None, "delete")
        if ptype.lower() in self._OFFSET_TYPES:
            name = self._offset_source_name(uid, ptype.lower())
            sources = cast(list[SourceEntry], self.data.get("sources", []))
            if any(s.get("name") == name for s in sources):
                self.remove_source(name)
        return result

    # -- On-demand probe reading -------------------------------------------
    # ``GET /probe?type=<type>&uid=<uid>`` asks the hub for a fresh reading of
    # one probe, without waiting for the next ``/dashboard`` poll. The answer
    # does not share the dashboard's shape (observed on a real RSCONTROLPRO):
    #   temperature: {"name", "status", "value"}
    #   ph / orp:    {"name", "status", "value", "temperature": {"value"}}
    #   ec:          {"name", "status", "ec", "ppt", "sg", "temperature": {...}}
    #   ato:         {"name", "status", "ato_sensor_status", "temperature": {...}}
    #   leak:        {"name", "status", "ec", "leak_status"}
    # so it is mapped onto the cached ``/dashboard.probes`` entry field by field.
    _EC_UNITS: tuple[str, ...] = ("ec", "ppt", "sg")
    _LEAK_STATUS_DETECTED: dict[str, bool] = {
        "dry": False,
        "aquarium_water_leak": True,
        "rodi_water_leak": True,
        # Older guesses, kept in case a firmware answers so
        "wet": True,
        "leak": True,
        "detected": True,
    }

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @classmethod
    def probe_reading_updates(
        cls,
        ptype: str,
        payload: dict[str, Any],
        measurement_unit: str | None = None,
    ) -> dict[str, Any]:
        """Translate a ``GET /probe`` answer into ``/dashboard.probes`` fields.

        Only fields actually present (and well-typed) in the answer are
        returned, so a partial or unexpected payload never blanks a cached
        value. ``measurement_unit`` is the EC probe's displayed unit: its
        dashboard ``value`` mirrors the reading in that unit.
        """
        kind = ptype.lower()
        updates: dict[str, Any] = {}

        status = payload.get("status")
        if isinstance(status, str):
            updates["status"] = status

        if cls._is_number(payload.get("value")):
            updates["value"] = payload["value"]

        # Embedded temperature compensation (ec / ph / ato probes).
        temp: Any = payload.get("temperature")
        if isinstance(temp, dict):
            temp_value: Any = cast(dict[str, Any], temp).get("value")
            if cls._is_number(temp_value):
                updates["temp_value"] = temp_value

        if kind == "ec":
            for unit in cls._EC_UNITS:
                if cls._is_number(payload.get(unit)):
                    updates[unit] = payload[unit]
            unit = str(measurement_unit or "").lower()
            if unit in updates:
                updates["value"] = updates[unit]
        elif kind == "ato":
            level = payload.get("ato_sensor_status")
            if isinstance(level, str):
                updates["water_level"] = level
        elif kind == "leak":
            leak = payload.get("leak_status")
            if isinstance(leak, str) and leak.lower() in cls._LEAK_STATUS_DETECTED:
                updates["detected"] = cls._LEAK_STATUS_DETECTED[leak.lower()]

        return updates

    def dashboard_probe(self, ptype: str, uid: str) -> dict[str, Any] | None:
        """Live reference to a probe's entry in the cached ``/dashboard``."""
        probes = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.probes",
            is_None_possible=True,
            cached=False,
        )
        if not isinstance(probes, list):
            return None
        for item in cast(list[Any], probes):
            if not isinstance(item, dict):
                continue
            probe = cast(dict[str, Any], item)
            if (
                probe.get("uid") == uid
                and str(probe.get("type", "")).lower() == ptype.lower()
            ):
                return probe
        return None

    # -- Multi-point calibration (pH, EC) ---------------------------------------
    # As the ReefBeat app drives it (``BaseControlProbeCalibrationActivity``,
    # not captured yet): enter calibration once, then per point start it with
    # the solution and poll its status until it succeeds or fails, then exit.
    #   POST /probe/calibration-enter?type&uid        {"time": <epoch s>}
    #   POST /probe/calibration-point-start?type&uid  {"point": "LOW"|"MID"|
    #        "HIGH", "solution_value": <float>, "solution_rated_temp": <°C>}
    #        (rated temperature for pH only)
    #   GET  /probe/calibration-status?type&uid
    #        -> {"calibration_status", "time_left", "stability_progress"}
    #   POST /probe/calibration-exit?type&uid         {}
    CALIBRATION_ACTIONS: tuple[str, ...] = ("enter", "point", "status", "exit")
    CALIBRATION_POINTS: tuple[str, ...] = ("LOW", "MID", "HIGH")

    async def probe_calibration(
        self,
        action: str,
        ptype: str,
        uid: str,
        point: str | None = None,
        solution_value: float | None = None,
        rated_temp: float | None = None,
    ) -> dict[str, Any]:
        """Run one step of a probe's multi-point calibration.

        Returns ``{"ok", "status_code", "json"}``; for ``status``, ``json``
        is the calibration status. A malformed step is refused without a
        request: ``{"ok": False, "error"}``.
        """
        query = f"?type={ptype}&uid={uid}"
        result: HttpResult | None
        if action == "enter":
            result = await self.http_send(
                f"/probe/calibration-enter{query}", {"time": int(time.time())}, "post"
            )
        elif action == "point":
            name = str(point or "").upper()
            if name not in self.CALIBRATION_POINTS or not self._is_number(
                solution_value
            ):
                return {"ok": False, "error": "point and solution_value required"}
            body: dict[str, Any] = {"point": name, "solution_value": solution_value}
            if self._is_number(rated_temp):
                body["solution_rated_temp"] = int(cast(float, rated_temp))
            result = await self.http_send(
                f"/probe/calibration-point-start{query}", body, "post"
            )
        elif action == "status":
            result = await self.http_get(f"/probe/calibration-status{query}")
        elif action == "exit":
            result = await self.http_send(f"/probe/calibration-exit{query}", {}, "post")
        else:
            return {"ok": False, "error": f"unknown action {action!r}"}
        if result is None:
            return {"ok": False, "status_code": None, "json": None}
        return {
            "ok": bool(result.get("ok")),
            "status_code": result.get("status"),
            "json": result.get("json"),
        }

    async def read_probe(self, ptype: str, uid: str) -> bool:
        """Read one probe now and patch the cached ``/dashboard`` with it.

        Returns True when the cache was updated. The dashboard entry is looked
        up *after* the request: a poll may have replaced the whole payload
        while waiting, and patching the old dict would be lost.
        """
        result = await self.http_get(f"/probe?type={ptype}&uid={uid}")
        if not result or not result.get("ok"):
            _LOGGER.warning(
                "Reading probe %s/%s failed: %s",
                ptype,
                uid,
                result.get("status") if result else "no response",
            )
            return False
        raw: Any = result.get("json")
        if not isinstance(raw, dict):
            return False
        payload = cast(dict[str, Any], raw)

        probe = self.dashboard_probe(ptype, uid)
        if probe is None:
            _LOGGER.debug("Probe %s/%s not in cached dashboard", ptype, uid)
            return False

        if ptype.lower() == "leak":
            # The origin and conductivity outlive the next dashboard poll
            self._leak_readings()[uid] = {
                key: payload[key] for key in ("leak_status", "ec") if key in payload
            }

        updates = self.probe_reading_updates(
            ptype, payload, probe.get("measurement_unit")
        )
        if not updates:
            return False
        probe.update(updates)
        return True

    # -- Per-probe buzzer / notify (config, readable via /probe/config) ----
    # Where each probe type's primary buzzer / notify lives:
    #   "top"  -> top-level field in the /probe/config entry
    #   "temp" -> under the entry's temp:{} block (ATO has no primary buzzer)
    #   "leak" -> /leak/config (leak has no /probe/config entry)
    _BUZZER_LOC = {
        "temperature": "top",
        "ec": "top",
        "ph": "top",
        "orp": "top",
        "ato": "temp",
        "leak": "leak",
    }
    _NOTIFY_LOC = {
        "temperature": "top",
        "ec": "top",
        "ph": "top",
        "orp": "top",
        "ato": "top",
        "leak": "leak",
    }

    @staticmethod
    def probe_config_path(ptype: str, uid: str, field: str, loc: str) -> str:
        """JSONPath to a probe's buzzer/notify, per its config location."""
        if loc == "leak":
            return f"$.sources[?(@.name=='/leak/config')].data.{field}"
        entry = (
            "$.sources[?(@.name=='/probe/config')]"
            f".data[?(@.type=='{ptype}' & @.uid=='{uid}')]"
        )
        return f"{entry}.temp.{field}" if loc == "temp" else f"{entry}.{field}"

    def buzzer_path(self, ptype: str, uid: str) -> str:
        return self.probe_config_path(
            ptype, uid, "buzzer", self._BUZZER_LOC.get(ptype, "top")
        )

    def notify_path(self, ptype: str, uid: str) -> str:
        return self.probe_config_path(
            ptype, uid, "notify", self._NOTIFY_LOC.get(ptype, "top")
        )

    async def _set_probe_flag(
        self, ptype: str, uid: str, field: str, on: bool, loc: str
    ) -> HttpResult | None:
        # Leak buzzer/notify live in /leak/config, not /probe/config (a
        # /probe/config write for a leak probe is rejected with HTTP 503). The
        # firmware merges a partial body, confirmed on device:
        #   PUT /leak/config {"buzzer": true} -> "Leak config updated".
        if loc == "leak":
            return await self.http_send("/leak/config", {field: on}, "put")
        # Partial PUT (merged by the firmware); temp flags nest under temp:{}.
        if loc == "temp":
            probe_body: dict[str, Any] = {
                "type": ptype,
                "uid": uid,
                "temp": {field: on},
            }
        else:
            probe_body = {"type": ptype, "uid": uid, field: on}
        return await self.http_send("/probe/config", [probe_body], "put")

    async def set_probe_buzzer(
        self, ptype: str, uid: str, on: bool
    ) -> HttpResult | None:
        """Toggle a probe's out-of-range buzzer (partial ``PUT /probe/config``)."""
        return await self._set_probe_flag(
            ptype, uid, "buzzer", on, self._BUZZER_LOC.get(ptype, "top")
        )

    async def set_probe_notify(
        self, ptype: str, uid: str, on: bool
    ) -> HttpResult | None:
        """Toggle a probe's out-of-range push notification."""
        return await self._set_probe_flag(
            ptype, uid, "notify", on, self._NOTIFY_LOC.get(ptype, "top")
        )

    async def set_probe_enabled(
        self, ptype: str, uid: str, on: bool
    ) -> HttpResult | None:
        """Enable (``DELETE``) or disable (``POST``) a probe's monitoring."""
        method = "delete" if on else "post"
        return await self.http_send(
            f"/probe/disable?type={ptype}&uid={uid}", None, method
        )

    # -- Per-probe acceptable/desired range (config, readable via
    # /probe/config) --------------------------------------------------------
    # `ranges` (primary reading) and `temp.ranges` (embedded temperature
    # compensation, on ec/ph/ato probes) are each a 4-element array:
    # [acceptable_min, desired_min, desired_max, acceptable_max]. The
    # firmware has no element-wise update for it — same contract as
    # `ranges`/`buzzer`/`notify` above — so every write resends the whole
    # 4-element array with just the changed bound replaced.
    RANGE_FIELD_INDEX: dict[str, int] = {
        "acceptable_range_low": 0,
        "desired_range_low": 1,
        "desired_range_high": 2,
        "acceptable_range_high": 3,
    }

    def probe_entry(self, ptype: str, uid: str) -> dict[str, Any] | None:
        """Return the cached ``/probe/config`` entry for a probe, if any."""
        entry = self.get_data(
            "$.sources[?(@.name=='/probe/config')]"
            f".data[?(@.type=='{ptype}' & @.uid=='{uid}')]",
            is_None_possible=True,
        )
        return entry if isinstance(entry, dict) else None

    async def set_probe_range(
        self, ptype: str, uid: str, field: str, value: float, *, is_temp: bool = False
    ) -> HttpResult | None:
        """Set one bound of a probe's acceptable/desired range.

        ``is_temp`` targets the embedded temperature-compensation threshold
        (``temp.ranges``) instead of the probe's own primary range.
        """
        idx = self.RANGE_FIELD_INDEX[field]
        entry = self.probe_entry(ptype, uid) or {}
        current = (
            entry.get("temp", {}).get("ranges") if is_temp else entry.get("ranges")
        )
        ranges = (
            list(current)
            if isinstance(current, list) and len(current) == 4
            else [0.0, 0.0, 0.0, 0.0]
        )
        ranges[idx] = value
        body: dict[str, Any] = {"type": ptype, "uid": uid}
        if is_temp:
            body["temp"] = {"ranges": ranges}
        else:
            body["ranges"] = ranges
        return await self.http_send("/probe/config", [body], "put")

    async def set_probe_unit(self, uid: str, unit: str) -> HttpResult | None:
        """Set an EC probe's measurement unit (``ec``/``ppt``/``sg``).

        Also resets ``ranges`` to that unit's own default acceptable/desired
        band (see ``EC_UNIT_DEFAULT_RANGES``): the device does not rescale
        the existing numeric range when the unit changes, so leaving it as
        is would keep, say, an EC-scale value like 54 labelled as SG.
        """
        return await self.http_send(
            "/probe/config",
            [
                {
                    "type": "ec",
                    "uid": uid,
                    "unit": unit,
                    "ranges": list(EC_UNIT_DEFAULT_RANGES[unit]),
                }
            ],
            "put",
        )

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
    # ATO module (the Red Sea ATO kit on a 12V port, port type "ato")
    # ------------------------------------------------------------------
    #
    # See the module docstring for the captured sequence. The module's
    # configuration (hose, auto fill, volume monitoring, flow rate…) is read
    # from ``GET /ato/configuration``, registered as a config source only
    # while a port is of type ``ato`` (the hub has one module at most).

    ATO_CONFIG = "/ato/configuration"
    # Port name the app gives the module
    ATO_PORT_NAME = "ATO Module"
    # Port modes reporting a fault of the module (``ControlPortMode`` wire
    # values mapped by ``ControlPort.getAtoError`` in the app), each cleared
    # by ``POST /ato/resume``
    ATO_FAULT_MODES: tuple[str, ...] = (
        "port_malfunction",
        "stalled",
        "empty",
        "missing_pump",
        "timeout",
        "leak",
    )
    # Flow rate override meaning "back to the pump's default" (app's
    # ``ATOModule.defaultFlowRate``); the app accepts 0.2 to 4 L/min
    ATO_DEFAULT_FLOW_RATE = -1

    def ato_port_number(self) -> int | None:
        """0-based number of the port the ATO module is on, None without one."""
        ports = self.get_data(
            "$.sources[?(@.name=='/dashboard')].data.ports", is_None_possible=True
        )
        for raw in cast(list[Any], ports) if isinstance(ports, list) else []:
            entry = _as_dict(raw)
            if (
                entry is not None
                and entry.get("type") == self.PORT_TYPE_ATO
                and isinstance(entry.get("number"), int)
            ):
                return int(entry["number"])
        return None

    def _reconcile_ato_source(self) -> bool:
        """Poll ``/ato/configuration`` only while an ATO module is installed.

        Returns True when the source was just added, for the caller to read
        it at once rather than at the next config refresh.
        """
        wanted = self.ato_port_number() is not None
        sources = cast(list[SourceEntry], self.data.get("sources", []))
        present = any(s.get("name") == self.ATO_CONFIG for s in sources)
        if wanted and not present:
            self.add_source(self.ATO_CONFIG, "config", "")
            return True
        if present and not wanted:
            self.remove_source(self.ATO_CONFIG)
        return False

    def ato_config(self) -> dict[str, Any] | None:
        """Cached ``/ato/configuration``, None when not read (yet)."""
        return _as_dict(self._source(self.ATO_CONFIG))

    def ato_dashboard(self) -> dict[str, Any] | None:
        """``/dashboard`` entry of the ATO module's port, None without one."""
        number = self.ato_port_number()
        return None if number is None else self._dashboard_port(number)

    def _mirror_ato_write(
        self, action: str, payload: Any, method: str, result: HttpResult
    ) -> None:
        """Optimistic updates of the ATO module's writes.

        ``PUT /ato/configuration`` answers the whole configuration: it
        replaces the cached one. The fields the dashboard also carries are
        set there, as is the volume left after ``POST /ato/update-volume``,
        and ``POST /ato/resume`` gives the port back its configured mode.
        """
        dash = self.ato_dashboard()
        if method == "put" and action == self.ATO_CONFIG:
            answer = _as_dict(result.get("json"))
            if answer is not None and "port_index" in answer:
                sources = cast(list[SourceEntry], self.data.get("sources", []))
                for source in sources:
                    if source.get("name") == self.ATO_CONFIG:
                        source["data"] = answer
            body = _as_dict(payload) or {}
            if dash is not None:
                for key in ("auto_fill", "temp_log_enabled", "volume_left"):
                    if key in body:
                        dash[key] = body[key]
            return
        if dash is None:
            return
        if method == "post" and action == "/ato/update-volume":
            volume: Any = (_as_dict(payload) or {}).get("volume")
            if self._is_number(volume):
                dash["volume_left"] = volume
        elif method == "post" and action == "/ato/resume":
            if dash.get("mode") in self.ATO_FAULT_MODES:
                dash["mode"] = dash.get("user_config_mode", "auto")
        elif method == "post" and action == "/ato/stop":
            dash["is_pump_on"] = False

    async def install_ato_port(
        self,
        number: int,
        uid: str,
        volume_ml: float,
        hose_length_cm: float,
        hose_height_cm: float,
        *,
        auto_fill: bool = True,
        volume_monitor: bool = True,
        notify: bool = True,
        port_count: int = 2,
    ) -> HttpResult | None:
        """Install the ATO module on a 12V port, in the app's order.

        The ATO probe ``uid`` must be installed already. The port gets the
        module's name and the hub's physical button (the app hands it over
        from the other port). Stops at the first refused request.
        """
        n = int(number)
        result = await self.http_send(
            f"/port/{n}/install", {"uid": uid, "type": self.PORT_TYPE_ATO}, "post"
        )
        if result is None or not result.get("ok"):
            return result
        if volume_monitor:
            await self.update_ato_volume(volume_ml)
        result = await self.http_send(
            self.ATO_CONFIG,
            {
                "volume_left": volume_ml,
                "port_index": n,
                "hose": {"length": hose_length_cm, "height": hose_height_cm},
                "auto_fill": auto_fill,
                "notify": notify,
                "rvm_enabled": volume_monitor,
            },
            "put",
        )
        if result is None or not result.get("ok"):
            return result
        ports: list[dict[str, Any]] = [
            {
                "number": n,
                "name": self.ATO_PORT_NAME,
                "type": self.PORT_TYPE_ATO,
                "is_btn_assigned": True,
            }
        ]
        ports += [
            {"number": other, "is_btn_assigned": False}
            for other in range(int(port_count))
            if other != n
        ]
        result = await self.http_send("/ports/config", ports, "put")
        self._reconcile_ato_source()
        await self.fetch_config(self.ATO_CONFIG)
        await self.fetch_config("/ports/config")
        return result

    async def set_ato_config(self, fields: dict[str, Any]) -> HttpResult | None:
        """Change settings of the ATO module (partial ``PUT``).

        ``port_index`` is added, as the app always sends it. Nothing is sent
        without a module.
        """
        number = self.ato_port_number()
        if number is None:
            _LOGGER.warning("No ATO module installed: %s not sent", fields)
            return None
        return await self.http_send(
            self.ATO_CONFIG, {**fields, "port_index": number}, "put"
        )

    async def set_ato_hose(
        self, length_cm: float | None = None, height_cm: float | None = None
    ) -> HttpResult | None:
        """Set the hose length and/or height (cm); the other one is resent."""
        hose: Any = (self.ato_config() or {}).get("hose")
        current = _as_dict(hose) or {}
        return await self.set_ato_config(
            {
                "hose": {
                    "length": length_cm
                    if length_cm is not None
                    else current.get("length", 0),
                    "height": height_cm
                    if height_cm is not None
                    else current.get("height", 0),
                }
            }
        )

    async def set_ato_flow_rate(self, flow_ml_min: float) -> HttpResult | None:
        """Override the pump flow rate (mL/min); 0 or less: back to default."""
        override: Any = (self.ato_config() or {}).get("pump_override")
        speed: Any = (_as_dict(override) or {}).get("speed_override", 0)
        rate = (
            round(float(flow_ml_min)) if flow_ml_min > 0 else self.ATO_DEFAULT_FLOW_RATE
        )
        return await self.set_ato_config(
            {
                "pump_override": {
                    "speed_override": speed if self._is_number(speed) else 0,
                    "flow_rate_override": rate,
                }
            }
        )

    async def update_ato_volume(self, volume_ml: float) -> HttpResult | None:
        """Set the volume left in the reservoir (``POST /ato/update-volume``)."""
        return await self.http_send(
            "/ato/update-volume", {"volume": round(float(volume_ml))}, "post"
        )

    async def ato_resume(self) -> HttpResult | None:
        """Clear a fault of the ATO module (``POST /ato/resume``)."""
        return await self.http_send("/ato/resume", {}, "post")

    async def ato_manual_pump(self) -> HttpResult | None:
        """Start a manual fill (``POST /ato/manual-pump``)."""
        return await self.http_send("/ato/manual-pump", {}, "post")

    async def ato_stop(self) -> HttpResult | None:
        """Stop the ATO pump (``POST /ato/stop``)."""
        return await self.http_send("/ato/stop", {}, "post")

    # ------------------------------------------------------------------
    # RSPower center pairing
    # ------------------------------------------------------------------
    #
    # The paired power center shows up in this hub's own /dashboard as
    # `connected_device` (hwid/type/state) — and, once paired, the link is
    # visible from the power center's side too, as ITS /dashboard
    # `connected_device` (hwid/type/status). There is no separate "pair"
    # call on the power center's side: pairing is only ever initiated here.

    async def power_discover(self, pair: bool = False) -> HttpResult | None:
        """Scan for (``pair=False``) or pair with (``pair=True``) a nearby
        RSPower center (``POST /power/discover``).

        The app always does a scan first to show the device before
        confirming, but a scan on its own commits nothing — only
        ``pair=True`` actually links the two devices.
        """
        return await self.http_send("/power/discover", {"pair": pair}, "post")

    async def power_unpair(self) -> HttpResult | None:
        """Unlink the paired RSPower center (``POST /power/unpair``)."""
        return await self.http_send("/power/unpair", {}, "post")
