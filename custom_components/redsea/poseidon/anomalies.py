"""Messages nothing expected, on the relay of the devices in Poseidon mode.

The mergers (mergers.py) rely on what the spy runs showed. A firmware that
adds a field, changes a structure or brings a new topic would make them
wrong without a word: this module tells it instead.

Each frame of a device in Poseidon mode is checked against a catalogue of
what is known (``COMMON_*`` for every device, ``CATALOGS`` per family, built
from the spy runs like the mergers). What does not match is an anomaly:

1. an MQTT packet type or a topic nothing knows;
2. a command of the cloud to an endpoint nothing knows (a new feature of
   the ReefBeat app);
3. a ``state`` with a key nothing knows, or of another type: the merger
   would miss or misread it;
4. a ``telemetry`` with a key nothing knows, missing or of another type
   (typically a firmware update).

An anomaly has a signature: a short hash of what is not personal in it (the
family, the topic, the keys and their types; never an id, a name or a
value), so that two users seeing the same novelty get the same one. Its
first occurrence goes to ``anomalies.jsonl`` with an anonymised sample, then
it is counted. An unknown command first waits ``CONTEXT_S`` for what the
device made of it: its answer (``command-response`` of the same ``uuid``) and
the states it pushed meanwhile, logged and reported with it as its context.

Then the reports of the repository are searched for the signature
(``poseidon-sig:<signature>`` in their title):

- none: a repair issue offers to report it (a GitHub issue prefilled with
  the signature, the model, the firmware and the sample); for level 4 only
  when the search did answer;
- an open one: levels 1-3 get a repair issue pointing at it, level 4 is
  only logged;
- a closed one: levels 1-3 get a repair issue telling it was handled (and
  in which version, from a ``fixed-in-<version>`` label), level 4 is only
  logged.

The search only sends the signature. It can be turned off (the repair
issues then offer to report levels 1-3); the whole detection too.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import aiohttp
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from ..const import DOMAIN
from . import const
from .debug import redact
from .relay import UP

_LOGGER = logging.getLogger(__name__)

# -- catalogue -------------------------------------------------------------------

# MQTT 3.1.1 packet types (1 CONNECT .. 14 DISCONNECT): 0 and 15 are reserved
COMMON_PACKETS: frozenset[int] = frozenset(range(1, 15))
# Topics: device/<family>/<hwid>/<suffix>, by direction
# rolling-log: pushed by a ReefMat when its roll advances; dosing-log: by a
# ReefDose after a dose (spy runs of 2026-10-30)
COMMON_UP_TOPICS: frozenset[str] = frozenset(
    {"telemetry", "state", "command-response", "rolling-log", "dosing-log"}
)
COMMON_DOWN_TOPICS: frozenset[str] = frozenset({"command"})
# Commands every device answers. POST /time {"timezone": <minutes>}: sent by
# the ReefBeat app when its daylight saving setting changes (seen on RSPOWER6
# 1.1.9, 2026-10-30)
COMMON_COMMANDS: frozenset[str] = frozenset({"GET /time", "POST /time"})
TOPIC_RE = re.compile(r"^device/([^/]+)/([^/]+)/([^/]+)$")
# Messages between the devices of a group (ReefWave pumps synced together):
# group/<family>/<group uid>, both ways, sent in clear
GROUP_RE = re.compile(r"^group/([^/]+)/([^/]+)$")
COMMON_GROUP_COMMANDS: frozenset[str] = frozenset({"POST /group/sync"})

# Value types of a catalogue: "any" accepts any value, and anything under it
NUMBER, STR, BOOL, LIST, DICT, NULL, ANY = (
    "number",
    "str",
    "bool",
    "list",
    "dict",
    "null",
    "any",
)


@dataclass(frozen=True)
class FamilyCatalog:
    """What the spy runs showed of one family of devices.

    Paths are dotted, list indexes and numbered keys (sockets, heads) as
    ``*``. ``null`` is always accepted: devices send it for "nothing".
    """

    telemetry: dict[str, frozenset[str]]
    telemetry_required: frozenset[str]
    # None: not known enough yet, not checked
    state: dict[str, frozenset[str]] | None
    # "METHOD /path", numbered segments as *; None: not checked
    commands: frozenset[str] | None


def _types(*names: str) -> frozenset[str]:
    return frozenset(names)


# Connection metrics of the telemetry: not always all of them
_METRICS = {
    "metrics.wifi_sig": _types(NUMBER),
    "metrics.ping": _types(NUMBER),
    # Only after a disconnection, a restart
    "metrics.mqtt_dis": _types(NUMBER),
    "metrics.res": _types(NUMBER),
    "metrics.wifi_dis": _types(NUMBER),
    # Once after a loss of the internet access (RSMAT 1.10.2, 2026-10-31)
    "metrics.int_dis": _types(NUMBER),
}


# ReefControl Power, RSPOWER6 1.1.9 (spy runs of 2026-10-29)
REEF_POWER = FamilyCatalog(
    telemetry={
        "mode": _types(STR),
        "active_shortcut": _types(STR),
        "battery_level": _types(STR),
        "pairing_status": _types(STR),
        "sockets.*.consumption": _types(NUMBER),
        "sockets.*.mode": _types(STR),
        "sockets.*.prev_mode": _types(STR),
        "pwr_temperature": _types(NUMBER),
        "local_time": _types(STR),
        "utc_time": _types(STR),
        "hwid": _types(STR),
        "wifi_signal": _types(NUMBER),
        "free_heap": _types(NUMBER),
        **_METRICS,
    },
    telemetry_required=frozenset(
        {
            "mode",
            "active_shortcut",
            "battery_level",
            "pairing_status",
            "sockets.*.consumption",
            "sockets.*.mode",
            "sockets.*.prev_mode",
            "pwr_temperature",
            "local_time",
            "utc_time",
            "hwid",
            "wifi_signal",
            "free_heap",
        }
    ),
    state={
        "specific_attributes.mode": _types(STR),
        "specific_attributes.sockets.*.mode": _types(STR),
        "specific_attributes.sockets.*.user_config_mode": _types(STR),
        "specific_attributes.sockets.*.enabled": _types(BOOL),
        "specific_attributes.sockets.*.name": _types(STR),
        "specific_attributes.sockets.*.power_detector_enabled": _types(BOOL),
        "specific_attributes.sockets.*.state": _types(STR),
        # Never seen other than null: what a sensor looks like is unknown
        "specific_attributes.sockets.*.sensor": _types(ANY),
        "specific_attributes.schedule.*.intervals": _types(LIST),
        "specific_attributes.schedule.*.intervals.*.time": _types(NUMBER),
        "specific_attributes.schedule.*.intervals.*.duration": _types(NUMBER),
        "specific_attributes.feed_schedule": _types(ANY),
        # Pushed on connection (spy run of 2026-10-29 15:20)
        "attributes": _types(ANY),
        "specific_attributes.device_setup_date": _types(NUMBER),
        "specific_attributes.factory_reset_time": _types(NUMBER),
        "specific_attributes.active_shortcut": _types(STR),
        "specific_attributes.feeding_type": _types(STR),
        "specific_attributes.device_settings.feed_schedule_shortcut_code": _types(STR),
        "specific_attributes.device_settings.temp_hysteresis": _types(NUMBER),
        # Only null without a temperature probe: unknown otherwise
        "specific_attributes.device_settings.temperature": _types(ANY),
        "specific_attributes.temperature": _types(ANY),
        "specific_attributes.connected_device": _types(ANY),
        "specific_attributes.initial": _types(BOOL),
        "specific_attributes.is_factory_reset": _types(BOOL),
        "specific_attributes.timezone": _types(NUMBER),
        "specific_attributes.ntp_sync": _types(BOOL),
    },
    commands=frozenset(
        {
            "GET /mode",
            "POST /off",
            "DELETE /off",
            "POST /socket/*/toggle",
            "GET /socket/*/config/schedule",
            "PUT /socket/*/config/schedule",
            "PUT /sockets/config",
        }
    ),
)

# ReefDose, RSDOSE4 3.0.1 (spy run of 2026-10-30, two devices)
_DOSING_TELEMETRY_REQUIRED = {
    "mode": _types(STR),
    "active_shortcut": _types(STR),
    "heads.*.total_dosed_steps": _types(NUMBER),
    "heads.*.auto_dosed_today": _types(NUMBER),
    "heads.*.manual_dosed_today": _types(NUMBER),
    "heads.*.doses_today": _types(NUMBER),
    "heads.*.container_volume": _types(NUMBER),
    "heads.*.remaining_days": _types(NUMBER),
    "heads.*.stock_level": _types(STR),
    "heads.*.recalibration_required": _types(BOOL),
    "heads.*.missed_dose.missed_volume": _types(NUMBER),
    "heads.*.missed_dose.total_volume": _types(NUMBER),
    "heads.*.daily_doses": _types(NUMBER),
    "local_time": _types(STR),
    "utc_time": _types(STR),
    "hwid": _types(STR),
    "wifi_signal": _types(NUMBER),
    "free_heap": _types(NUMBER),
    "largest_free_block": _types(NUMBER),
    "uptime": _types(STR),
}
REEF_DOSING = FamilyCatalog(
    telemetry={
        **_DOSING_TELEMETRY_REQUIRED,
        "backup_restore": _types(NUMBER),
        # Stack watermarks of the firmware tasks: their list may change
        "task_watermark": _types(ANY),
        **_METRICS,
    },
    telemetry_required=frozenset(_DOSING_TELEMETRY_REQUIRED),
    state={
        # Pushed on connection only: system, firmware, network
        "attributes": _types(ANY),
        "specific_attributes.ntp_sync": _types(BOOL),
        "specific_attributes.timezone": _types(NUMBER),
        "specific_attributes.mode": _types(STR),
        "specific_attributes.is_factory_reset": _types(BOOL),
        "specific_attributes.active_shortcut": _types(STR),
        "specific_attributes.stock_alert_days": _types(NUMBER),
        "specific_attributes.dosing_waiting_period": _types(NUMBER),
        "specific_attributes.missed_doses_reminder": _types(BOOL),
        "specific_attributes.calibration_reminder_days": _types(NUMBER),
        "specific_attributes.calibration_reminder_steps": _types(NUMBER),
        "specific_attributes.calibration_reminder": _types(BOOL),
        "specific_attributes.daily_metrics_last_compute_time": _types(NUMBER),
        "specific_attributes.start_of_schedule_for_next_day": _types(NUMBER),
        "specific_attributes.factory_reset_time": _types(NUMBER),
        "specific_attributes.device_settings.shortcut_off_delay": _types(NUMBER),
        "specific_attributes.device_settings.bundled_heads": _types(BOOL),
        "specific_attributes.device_settings.auto_fill_schedule": _types(BOOL),
        "specific_attributes.heads.*.state": _types(STR),
        "specific_attributes.heads.*.last_calibrated": _types(NUMBER),
        "specific_attributes.heads.*.daily_dose": _types(NUMBER),
        "specific_attributes.heads.*.schedule_type": _types(STR),
        "specific_attributes.heads.*.nd": _types(NUMBER),
        "specific_attributes.heads.*.dd": _types(NUMBER),
        "specific_attributes.heads.*.days": _types(LIST),
        "specific_attributes.heads.*.days.*": _types(NUMBER),
        "specific_attributes.heads.*.supplement.uid": _types(STR),
        "specific_attributes.heads.*.supplement.name": _types(STR),
        "specific_attributes.heads.*.supplement.display_name": _types(STR),
        "specific_attributes.heads.*.supplement.short_name": _types(STR),
        "specific_attributes.heads.*.supplement.brand_name": _types(STR),
        "specific_attributes.heads.*.supplement.type": _types(STR),
        "specific_attributes.heads.*.supplement.concentration": _types(NUMBER),
        "specific_attributes.heads.*.supplement.made_by_redsea": _types(BOOL),
        "specific_attributes.heads.*.schedule_enabled": _types(BOOL),
        "specific_attributes.heads.*.show": _types(BOOL),
        "specific_attributes.heads.*.is_food_head": _types(BOOL),
        "specific_attributes.heads.*.shortcut_code": _types(STR),
        "specific_attributes.heads.*.food_delay": _types(NUMBER),
        "specific_attributes.heads.*.dc": _types(BOOL),
        "specific_attributes.heads.*.vps": _types(NUMBER),
        "specific_attributes.heads.*.slm": _types(BOOL),
        "specific_attributes.heads.*.enable_ratio": _types(BOOL),
        # Never seen other than empty: what a food head schedule looks like
        # is unknown
        "specific_attributes.food_head_schedule": _types(ANY),
        "specific_attributes.battery_level": _types(STR),
        "specific_attributes.time_error": _types(BOOL),
        "specific_attributes.time_error_unixtime": _types(NUMBER),
        "specific_attributes.file_error": _types(BOOL),
    },
    commands=frozenset(
        {
            "GET /dashboard",
            "GET /head/*/settings",
            # A head changed in the app (spy run of 2026-10-30 15:27)
            "POST /head/*/validate-settings",
            "PUT /head/*/settings",
            "POST /head/*/compensate/cancel",
            "GET /bundle/settings",
            # The food head restored by the cloud at connection
            "POST /food-head",
        }
    ),
)

# Telemetry only for now (spy run of 2026-10-30, ~40 minutes each): their
# states and commands are not checked yet
_MAT_TELEMETRY_REQUIRED = {
    "mode": _types(STR),
    "active_shortcut": _types(STR),
    "roll_level": _types(STR),
    "days_till_end_of_roll": _types(NUMBER),
    "today_usage": _types(NUMBER),
    "daily_average_usage": _types(NUMBER),
    "total_usage": _types(NUMBER),
    "remaining_length": _types(NUMBER),
    "cumulative_steps": _types(NUMBER),
    "setup_date": _types(STR),
    "material_name": _types(STR),
    "material_start_diameter": _types(NUMBER),
    "material_start_length": _types(NUMBER),
    "maxavg_ec_ext": _types(NUMBER),
    "maxavg_ec_int": _types(NUMBER),
    "lifetime_steps": _types(NUMBER),
    "max_motor_current": _types(NUMBER),
    "local_time": _types(STR),
    "utc_time": _types(STR),
    "hwid": _types(STR),
    "wifi_signal": _types(NUMBER),
    "free_heap": _types(NUMBER),
}
# ReefMat, RSMAT
REEF_MAT = FamilyCatalog(
    telemetry={**_MAT_TELEMETRY_REQUIRED, **_METRICS},
    telemetry_required=frozenset(_MAT_TELEMETRY_REQUIRED),
    state=None,
    commands=None,
)
_LIGHTS_TELEMETRY_REQUIRED = {
    "mode": _types(STR),
    "active_shortcut": _types(STR),
    # Its channels depend on the model: not checked one by one
    "intensities": _types(ANY),
    "temperature": _types(NUMBER),
    "overheat-reduction-factor": _types(NUMBER),
    "fan-speed": _types(NUMBER),
    "active-program": _types(STR),
    "clouds": _types(NUMBER),
    "acclimation": _types(NUMBER),
    "moonphase": _types(NUMBER),
    "local_time": _types(STR),
    "utc_time": _types(STR),
    "hwid": _types(STR),
    "wifi_signal": _types(NUMBER),
    "free_heap": _types(NUMBER),
}
# ReefLED (G1)
REEF_LIGHTS = FamilyCatalog(
    telemetry={**_LIGHTS_TELEMETRY_REQUIRED, **_METRICS},
    telemetry_required=frozenset(_LIGHTS_TELEMETRY_REQUIRED),
    state=None,
    commands=None,
)
_WAVE_TELEMETRY_REQUIRED = {
    "mode": _types(STR),
    "active_shortcut": _types(STR),
    "controlling-mode": _types(STR),
    "uptime": _types(STR),
    "local_time": _types(STR),
    "utc_time": _types(STR),
    "hwid": _types(STR),
    "wifi_signal": _types(NUMBER),
    "free_heap": _types(NUMBER),
}
# ReefWave
REEF_WAVE = FamilyCatalog(
    telemetry={
        **_WAVE_TELEMETRY_REQUIRED,
        # Its fields depend on the type of wave; missing while the pump is off
        "active-wave": _types(ANY),
        **_METRICS,
    },
    telemetry_required=frozenset(_WAVE_TELEMETRY_REQUIRED),
    state=None,
    commands=None,
)

CATALOGS: dict[str, FamilyCatalog] = {
    "reef-power": REEF_POWER,
    "reef-dosing": REEF_DOSING,
    "reef-mat": REEF_MAT,
    "reef-lights": REEF_LIGHTS,
    "reef-wave": REEF_WAVE,
}


# -- checks --------------------------------------------------------------------------

LEVEL_PACKET = 1
LEVEL_COMMAND = 2
LEVEL_STATE = 3
LEVEL_TELEMETRY = 4

KIND_PACKET = "unknown_packet"
KIND_TOPIC = "unknown_topic"
KIND_COMMAND = "unknown_command"
KIND_STATE = "state_keys"
KIND_TELEMETRY = "telemetry_keys"


@dataclass(frozen=True)
class Anomaly:
    """Something a frame carried that nothing expected."""

    level: int
    kind: str
    family: str
    topic: str  # the suffix of the topic, or the packet type
    # What differs, sorted: "+path:type" unknown, "-path" missing,
    # "~path:type" of another type, or the unknown endpoint / topic
    details: tuple[str, ...]
    sample: Any = None

    @property
    def signature(self) -> str:
        """Short hash of what is not personal: same for every user."""
        key = json.dumps(
            [self.kind, self.family, self.topic, list(self.details)], sort_keys=True
        )
        return hashlib.sha256(key.encode()).hexdigest()[:10]


def value_type(value: Any) -> str:
    if value is None:
        return NULL
    if isinstance(value, bool):
        return BOOL
    if isinstance(value, (int, float)):
        return NUMBER
    if isinstance(value, str):
        return STR
    if isinstance(value, list):
        return LIST
    return DICT


def normalize(path: str) -> str:
    """A path with its numbered segments (list indexes, sockets) as ``*``."""
    return ".".join("*" if part.isdigit() else part for part in path.split("."))


def _leaves(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        if not value and prefix:
            yield prefix, value
        for key, item in value.items():
            yield from _leaves(item, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        if not value and prefix:
            yield prefix, value
        for index, item in enumerate(value):
            yield from _leaves(item, f"{prefix}.{index}" if prefix else str(index))
    else:
        yield prefix, value


def leaf_types(payload: Any) -> dict[str, set[str]]:
    """Normalized leaf paths of a payload and the types seen at each."""
    types: dict[str, set[str]] = {}
    for path, value in _leaves(payload):
        if path:
            types.setdefault(normalize(path), set()).add(value_type(value))
    return types


def _known(path: str, catalog: dict[str, frozenset[str]]) -> frozenset[str] | None:
    """The types the catalogue accepts at a path (ANY under an ANY)."""
    if path in catalog:
        return catalog[path]
    parts = path.split(".")
    for end in range(len(parts) - 1, 0, -1):
        if ANY in catalog.get(".".join(parts[:end]), frozenset()):
            return frozenset({ANY})
    return None


def _key_differences(
    payload: Any,
    catalog: dict[str, frozenset[str]],
    required: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    seen = leaf_types(payload)
    details: set[str] = set()
    for path, types in seen.items():
        accepted = _known(path, catalog)
        if accepted is None:
            # An empty object or list where the catalogue knows its items
            if types <= {DICT, LIST} and any(p.startswith(path + ".") for p in catalog):
                continue
            details.add(f"+{path}:{'|'.join(sorted(types))}")
            continue
        if ANY in accepted:
            continue
        # null is "nothing"; an empty list or object stands for its items
        odd = types - accepted - {NULL}
        if odd == {LIST} and any(p.startswith(path + ".") for p in catalog):
            odd = set()
        if odd == {DICT} and any(p.startswith(path + ".") for p in catalog):
            odd = set()
        if odd:
            details.add(f"~{path}:{'|'.join(sorted(odd))}")
    for path in required - set(seen):
        # An object seen through its leaves is there
        if not any(p.startswith(path + ".") for p in seen):
            details.add(f"-{path}")
    return tuple(sorted(details))


def command_key(payload: Any) -> str | None:
    """ "METHOD /path" of a cloud command, numbered segments as *."""
    if not isinstance(payload, dict):
        return None
    method = str(payload.get("method") or "").upper()
    url = str(payload.get("url") or "")
    if not method or not url:
        return None
    path = url.split("?", 1)[0]
    path = "/".join("*" if part.isdigit() else part for part in path.split("/"))
    return f"{method} {path}"


def anonymize(payload: Any, hwid: str = "") -> Any:
    """A sample fit for a public issue: no key, no id, no name, no address."""
    personal = {
        "hwid",
        "uuid",
        "name",
        "display_name",
        "ssid",
        "bssid",
        "mac",
        "ip",
        "gateway",
        "dns",
    }

    def walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: ("<…>" if k in personal and isinstance(v, str) and v else walk(v))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, str) and hwid and hwid.lower() in value.lower():
            return re.sub(re.escape(hwid), "<hwid>", value, flags=re.IGNORECASE)
        return value

    return walk(redact(payload))


def check_frame(
    family: str,
    direction: str,
    packet_type: int,
    topic: str | None,
    payload: Any,
    hwid: str = "",
) -> list[Anomaly]:
    """What a frame of a device carried that nothing expected.

    Args:
        family: the cloud type of the device (reef-power...)
        direction: relay.UP for device -> cloud, anything else the other way
        packet_type: MQTT packet type
        topic: topic of a PUBLISH, None otherwise
        payload: decrypted payload of a PUBLISH (None when it does not
            decrypt: then only the topic is checked)
        hwid: the device, to take it out of the samples
    """
    if packet_type not in COMMON_PACKETS:
        return [Anomaly(LEVEL_PACKET, KIND_PACKET, family, f"type {packet_type}", ())]
    if topic is None:
        return []
    up = direction == UP
    group = GROUP_RE.match(topic)
    if group is not None:
        key = command_key(payload) if payload is not None else None
        if key is not None and key not in COMMON_GROUP_COMMANDS:
            return [
                Anomaly(
                    LEVEL_COMMAND,
                    KIND_COMMAND,
                    family,
                    "group",
                    (key,),
                    anonymize(payload, hwid),
                )
            ]
        return []
    match = TOPIC_RE.match(topic)
    suffix = match.group(3) if match else ""
    known_topics = COMMON_UP_TOPICS if up else COMMON_DOWN_TOPICS
    if suffix not in known_topics:
        # The topic, without the id of the device
        shown = topic.replace(hwid, "<hwid>") if hwid else topic
        shown = re.sub(r"^device/[^/]+/[^/]+/", "device/<family>/<hwid>/", shown)
        return [
            Anomaly(
                LEVEL_PACKET,
                KIND_TOPIC,
                family,
                ("up " if up else "down ") + (suffix or "?"),
                (shown,),
                anonymize(payload, hwid),
            )
        ]
    catalog = CATALOGS.get(family)
    if catalog is None or payload is None:
        # No catalogue yet for this family: nothing more is expected
        return []
    if suffix == "command":
        key = command_key(payload)
        if catalog.commands is None:
            return []
        if key is not None and key not in catalog.commands | COMMON_COMMANDS:
            return [
                Anomaly(
                    LEVEL_COMMAND,
                    KIND_COMMAND,
                    family,
                    suffix,
                    (key,),
                    anonymize(payload, hwid),
                )
            ]
        return []
    if suffix == "state":
        if catalog.state is None:
            return []
        details = _key_differences(payload, catalog.state)
        if details:
            return [
                Anomaly(
                    LEVEL_STATE,
                    KIND_STATE,
                    family,
                    suffix,
                    details,
                    anonymize(payload, hwid),
                )
            ]
        return []
    if suffix == "telemetry":
        details = _key_differences(
            payload, catalog.telemetry, catalog.telemetry_required
        )
        if details:
            return [
                Anomaly(
                    LEVEL_TELEMETRY,
                    KIND_TELEMETRY,
                    family,
                    suffix,
                    details,
                    anonymize(payload, hwid),
                )
            ]
    # command-response: the answer of an HTTP endpoint, checked by nothing
    return []


# -- GitHub ------------------------------------------------------------------------------


@dataclass
class Report:
    """What the repository says of a signature."""

    status: str  # "none", "open", "closed"
    url: str = ""
    number: int = 0
    fixed_in: str = ""


def parse_search(answer: Any) -> Report:
    """The best report of a GitHub search answer: open first, then fixed."""
    items = answer.get("items") if isinstance(answer, dict) else None
    if not isinstance(items, list) or not items:
        return Report("none")
    reports: list[Report] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        labels = [
            str(label.get("name", ""))
            for label in item.get("labels") or []
            if isinstance(label, dict)
        ]
        fixed = next(
            (
                name[len(const.FIXED_LABEL_PREFIX) :]
                for name in labels
                if name.startswith(const.FIXED_LABEL_PREFIX)
            ),
            "",
        )
        reports.append(
            Report(
                "open" if item.get("state") == "open" else "closed",
                str(item.get("html_url") or ""),
                int(item.get("number") or 0),
                fixed,
            )
        )
    if not reports:
        return Report("none")
    for report in reports:
        if report.status == "open":
            return report
    return max(reports, key=lambda r: (bool(r.fixed_in), r.number))


def issue_title(anomaly: Anomaly) -> str:
    return (
        f"Poseidon: {anomaly.kind} on {anomaly.family} "
        f"[poseidon-sig:{anomaly.signature}]"
    )


MAX_BODY = 5000


def new_issue_url(
    anomaly: Anomaly,
    model: str,
    firmware: str,
    version: str,
    context: list[dict[str, Any]] | None = None,
) -> str:
    """A GitHub issue prefilled with the anomaly (the user sends it or not)."""
    details = "\n".join(f"- `{d}`" for d in anomaly.details[:30])
    sample = json.dumps(anomaly.sample, indent=1, ensure_ascii=False, default=str)
    if context:
        # What the device made of it, in the same block: cut together
        sample += "\n\n// What the device sent next\n" + json.dumps(
            context, indent=1, ensure_ascii=False, default=str
        )
    head = (
        f"Poseidon met a message nothing expected.\n\n"
        f"- Signature: `poseidon-sig:{anomaly.signature}`\n"
        f"- Level: {anomaly.level} ({anomaly.kind})\n"
        f"- Family: `{anomaly.family}` / model `{model}` / firmware `{firmware}`\n"
        f"- Integration: {version}\n"
        f"- Topic: `{anomaly.topic}`\n\n"
        f"Differences:\n{details}\n\n"
    )
    room = MAX_BODY - len(head) - 200
    if len(sample) > room:
        sample = sample[: max(0, room)] + "\n…"
        tail = (
            "\n\nThe sample is cut: please attach the line of this signature "
            "from `redsea/poseidon/logs/anomalies.jsonl`."
        )
    else:
        tail = ""
    body = f"{head}Sample (anonymised):\n```json\n{sample}\n```{tail}"
    query = urlencode(
        {"title": issue_title(anomaly), "body": body, "labels": const.ANOMALY_LABEL}
    )
    return f"{const.GITHUB_NEW_ISSUE_URL}?{query}"


# -- monitor -----------------------------------------------------------------------------


# How long an unknown command waits for what the device answers and pushes
CONTEXT_S = 5.0
# At most this many messages of context
CONTEXT_MAX = 5


@dataclass
class Seen:
    anomaly: Anomaly
    first: str
    count: int = 1
    model: str = ""
    firmware: str = ""
    # What the device sent after it (unknown commands), anonymised
    context: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _Waiting:
    """An unknown command waiting for what the device makes of it."""

    hwid: str
    uuid: str
    start: float
    cancel: Callable[[], None] | None = None


@dataclass
class AnomalyMonitor:
    """Logs the anomalies, looks them up and raises their repair issues."""

    hass: HomeAssistant
    write: Callable[[dict[str, Any]], None]
    search_enabled: Callable[[], bool]
    version: str = ""
    seen: dict[str, Seen] = field(default_factory=dict)
    # signature -> (report, monotonic time) of the last search
    _searches: dict[str, tuple[Report | None, float]] = field(default_factory=dict)
    _issues: set[str] = field(default_factory=set)
    # signature -> unknown command waiting for its context
    _waiting: dict[str, _Waiting] = field(default_factory=dict)

    @callback
    def report(
        self,
        hwid: str,
        anomalies: list[Anomaly],
        model: str = "",
        firmware: str = "",
        message: Any = None,
    ) -> None:
        """Anomalies of a frame: logged once, counted, looked up.

        ``message`` is the decrypted frame (not anonymised): the ``uuid`` of a
        command matches its answer.
        """
        for anomaly in anomalies:
            signature = anomaly.signature
            known = self.seen.get(signature)
            if known is not None:
                known.count += 1
                continue
            self.seen[signature] = Seen(
                anomaly, dt_util.now().isoformat(), 1, model, firmware
            )
            uuid = message.get("uuid") if isinstance(message, dict) else None
            if anomaly.kind == KIND_COMMAND and isinstance(uuid, str) and uuid:
                waiting = _Waiting(hwid, uuid, time.monotonic())
                self._waiting[signature] = waiting
                waiting.cancel = async_call_later(
                    self.hass, CONTEXT_S, self._publish_later(signature)
                )
                continue
            self._publish(signature)

    def _publish_later(self, signature: str) -> Callable[[Any], None]:
        """The timer callback publishing a waiting command (in the loop)."""

        @callback
        def _done(_now: Any) -> None:
            self._publish(signature)

        return _done

    @callback
    def observe(self, hwid: str, topic: str, message: Any) -> None:
        """A decrypted message of a device: the context of the unknown
        commands it is answering (their answer, the states pushed meanwhile)."""
        if not self._waiting:
            return
        suffix = topic.rsplit("/", 1)[-1]
        if suffix not in ("command-response", "state"):
            return
        for signature, waiting in list(self._waiting.items()):
            if waiting.hwid != hwid:
                continue
            if suffix == "command-response" and (
                not isinstance(message, dict) or message.get("uuid") != waiting.uuid
            ):
                continue
            seen = self.seen[signature]
            if len(seen.context) >= CONTEXT_MAX:
                continue
            seen.context.append(
                {
                    "after_s": round(time.monotonic() - waiting.start, 1),
                    "topic": suffix,
                    "payload": anonymize(message, hwid),
                }
            )

    @callback
    def _publish(self, signature: str) -> None:
        """Log an anomaly (with its context) and look it up."""
        self._waiting.pop(signature, None)
        seen = self.seen.get(signature)
        if seen is None:
            return
        anomaly = seen.anomaly
        record: dict[str, Any] = {
            "ts": dt_util.now().isoformat(),
            "kind": "anomaly",
            "signature": signature,
            "level": anomaly.level,
            "anomaly": anomaly.kind,
            "family": anomaly.family,
            "model": seen.model,
            "firmware": seen.firmware,
            "topic": anomaly.topic,
            "details": list(anomaly.details),
            "sample": anomaly.sample,
        }
        if anomaly.kind == KIND_COMMAND:
            record["context"] = seen.context
        self.write(record)
        _LOGGER.info(
            "Poseidon: %s on %s (%s): %s",
            anomaly.kind,
            anomaly.family,
            signature,
            ", ".join(anomaly.details[:5]),
        )
        self.hass.async_create_task(self.async_resolve(signature))

    async def async_search(self, signature: str) -> Report | None:
        """The report of a signature on GitHub, None when unknown (off,
        unreachable). Answers are kept ANOMALY_SEARCH_TTL_S."""
        if not self.search_enabled():
            return None
        cached = self._searches.get(signature)
        now = time.monotonic()
        if cached is not None and now - cached[1] < const.ANOMALY_SEARCH_TTL_S:
            return cached[0]
        query = f'repo:{const.GITHUB_REPO} "poseidon-sig:{signature}" in:title'
        report: Report | None = None
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                const.GITHUB_SEARCH_URL,
                params={"q": query},
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "ha-reefbeat-component",
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    report = parse_search(await resp.json(content_type=None))
                else:
                    _LOGGER.debug("GitHub search answered %s", resp.status)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            _LOGGER.debug("GitHub search failed: %s", err)
        self._searches[signature] = (report, now)
        return report

    async def async_resolve(self, signature: str) -> None:
        """Raise (or not) the repair issue of a signature."""
        seen = self.seen.get(signature)
        if seen is None:
            return
        anomaly = seen.anomaly
        report = await self.async_search(signature)
        level4 = anomaly.level == LEVEL_TELEMETRY
        if report is None:
            # Search off or unreachable: telemetry drift is only logged
            if level4:
                return
            key, url = "new", self._new_issue_url(seen)
        elif report.status == "none":
            key, url = "new", self._new_issue_url(seen)
        elif level4:
            # Already known: one report is enough
            return
        elif report.status == "open":
            key, url = "reported", report.url
        elif report.fixed_in:
            key, url = "fixed", report.url
        else:
            key, url = "closed", report.url
        issue_id = f"{const.ISSUE_ANOMALY}_{signature}"
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            is_persistent=False,
            learn_more_url=url,
            severity=ir.IssueSeverity.WARNING,
            translation_key=f"{const.ISSUE_ANOMALY}_{key}",
            translation_placeholders={
                "signature": signature,
                "kind": anomaly.kind,
                "family": anomaly.family,
                "model": seen.model or "?",
                "firmware": seen.firmware or "?",
                "details": ", ".join(f"`{d}`" for d in anomaly.details[:5])
                + (" …" if len(anomaly.details) > 5 else ""),
                "url": url,
                "number": str(report.number if report else 0),
                "version": report.fixed_in if report else "",
            },
        )
        self._issues.add(issue_id)

    def _new_issue_url(self, seen: Seen) -> str:
        return new_issue_url(
            seen.anomaly, seen.model, seen.firmware, self.version, seen.context
        )

    @callback
    def clear(self) -> None:
        """Detection turned off: its repair issues go."""
        for waiting in self._waiting.values():
            if waiting.cancel is not None:
                waiting.cancel()
        self._waiting.clear()
        for issue_id in self._issues:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        self._issues.clear()
