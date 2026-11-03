"""Mergers of pushed messages into the polled sources, per device family.

A device in Poseidon mode pushes a ``state`` when something changes (a socket
switched, a schedule written, the device turned off) and a ``telemetry``
every 60 s (modes, consumptions, signal). For the shadow and poseidon
strategies, a merger writes what they carry into the sources its coordinator
polls, so the entities follow at once instead of at the next poll. Each one
is written from spy files (``response`` of the HTTP records against the
pushed values): only what was seen to match is merged.

A merger returns whether the message is fully taken into account. It returns
False when nothing in it could be merged, or when it tells something the
merger cannot write into the sources (a field it does not know, a schedule
pushed without its intervals): the poseidon strategy then reads the device
again, its config sources included (for a ``state``; a ``telemetry``
triggers nothing). What can be merged is merged anyway.

A family whose pushed messages cover every polled value that changes says so
for a device (``FULLY_PUSHED``): the poseidon strategy then only polls it
now and then, as a safety net.
"""

from __future__ import annotations

import copy
import math
import time
from datetime import datetime, timedelta
from typing import Any

# Wrapper of every pushed state
WRAPPER = "specific_attributes"

# Attribute of a coordinator holding the clock of its device, as its last
# telemetry told it: (device local time, time.monotonic() when received)
CLOCK_ATTR = "_poseidon_device_clock"

MINUTES_PER_DAY = 24 * 60


def _source(coordinator: Any, name: str) -> dict[str, Any] | None:
    """The polled data of one source, when it was read already."""
    api = getattr(coordinator, "my_api", None)
    sources = getattr(api, "data", {}).get("sources") if api is not None else None
    for source in sources if isinstance(sources, list) else []:
        if isinstance(source, dict) and source.get("name") == name:
            return source
    return None


def _data(coordinator: Any, name: str) -> dict[str, Any] | None:
    """The polled answer of a source, when it is a JSON object."""
    source = _source(coordinator, name)
    data = source.get("data") if source is not None else None
    return data if isinstance(data, dict) else None


def _socket_of(data: Any, number: int) -> dict[str, Any] | None:
    """The socket ``number`` in the ``sockets`` list of a polled source."""
    sockets = data.get("sockets") if isinstance(data, dict) else None
    for socket in sockets if isinstance(sockets, list) else []:
        if isinstance(socket, dict) and socket.get("number") == number:
            return socket
    return None


def _set_mode(holder: dict[str, Any], key: str, prev_key: str, mode: Any) -> bool:
    """Write a mode, keeping the old one in ``prev_key`` when it changes."""
    old = holder.get(key)
    if old == mode:
        return False
    if prev_key and old is not None:
        holder[prev_key] = old
    holder[key] = mode
    return True


def _unhandled(pushed: dict[str, Any], known: frozenset[str]) -> bool:
    """Whether a pushed object has a key no merger knows what to do with."""
    return any(key not in known for key in pushed)


def _set_device_clock(coordinator: Any, local_time: Any) -> None:
    """Keep the clock of the device (its own local time, its own offset)."""
    if not isinstance(local_time, str):
        return
    try:
        clock = datetime.fromisoformat(local_time)
    except ValueError:
        return
    setattr(coordinator, CLOCK_ATTR, (clock, time.monotonic()))


def device_now(coordinator: Any) -> datetime | None:
    """The local time of the device now, from its last telemetry."""
    clock = getattr(coordinator, CLOCK_ATTR, None)
    if not isinstance(clock, tuple) or len(clock) != 2:
        return None
    local, received = clock
    return local + timedelta(seconds=time.monotonic() - received)


# -- ReefControl Power (reef-power) ---------------------------------------------
#
# Seen on RSPOWER6 1.1.9 (spy, 2026-10-29), state:
#   mode                 -> /mode.mode and /dashboard.mode
#                           (/dashboard.previous_mode takes the old one)
#   sockets.N.<field>    -> the socket "number": N of /dashboard.sockets and
#                           /sockets/config.sockets, for the fields each has
#                           (its prev_mode takes the old mode when it changes)
#   sockets.N.state      -> /dashboard only, and not when "unknown": the push
#                           always says "unknown" where /dashboard tells
#                           "standby" or "on"
#   schedule.N.intervals -> /socket/N/config/schedule.intervals
#   feed_schedule        -> nothing polled matches it yet: not merged
#   connected_device     -> /dashboard.connected_device (the ReefControl it
#                           is paired with, spy run of 2026-11-02)
#   temperature: null    -> /dashboard.temperature (the probe removed); a
#                           probe installed or set up (temperature,
#                           device_settings.temperature) reads it again
# telemetry (every 60 s, no wrapper):
#   mode                 -> as in the state
#   battery_level        -> /dashboard.battery_level
#   sockets.N.consumption, mode, prev_mode -> the socket N of /dashboard
#                           (mode also in /sockets/config); null consumption
#                           of a socket in setup mode (removed) -> 0, as polled
#   wifi_signal          -> /wifi.signal_dBm
#   local_time           -> the clock of the device (see below)
#   pwr_temperature      -> /dashboard.temperature: its value, status and
#                           level (same values as the poll, not rounded;
#                           RSPOWER6 1.1.9 with a temperature probe, spy run
#                           of 2026-11-02); null without a probe. A probe
#                           installed or removed pushes a state with its
#                           settings (device_settings): the device is read
#                           again then
# Probe settings (/temperature/config: ranges, name, offset): pushed by a
# state after PUT /temperature/config, but not after POST /probe/offset (the
# offset set from the app): every write command of the app answered by the
# device reads it again (manager), so this one too.
#   active_shortcut, pairing_status, free_heap, metrics -> nothing polled
# Socket state (/dashboard.sockets.N.state), pushed by nothing: the ReefBeat
# app computes it from the schedules, so does Home Assistant. A socket in
# "schedule" mode is "on" while the local time of the device (its telemetry
# local_time, with its own offset) is in one of its intervals, "standby"
# otherwise; any other mode is "unknown". Checked 60 / 60 against the polled
# /dashboard. Only for a device in "auto" mode and a socket driven by nothing
# else (no power detector, no sensor): the others keep their polled state.

# Socket fields of each source
_DASHBOARD_SOCKET = ("name", "mode", "enabled", "user_config_mode", "state")
_CONFIG_SOCKET = (
    "name",
    "mode",
    "enabled",
    "user_config_mode",
    "power_detector_enabled",
    "sensor",
)


# Keys of a pushed state merged, or known to tell nothing polled
_POWER_STATE_KNOWN = frozenset(
    {
        "mode",
        "sockets",
        "schedule",
        "connected_device",
        # null: merged; else, with device_settings, read again (see below)
        "temperature",
        # Nothing polled matches them
        "feed_schedule",
        "timezone",
        "ntp_sync",
        "active_shortcut",
        "device_setup_date",
        "factory_reset_time",
        "feeding_type",
        "initial",
        "is_factory_reset",
    }
)
_POWER_SOCKET_KNOWN = frozenset(_DASHBOARD_SOCKET + _CONFIG_SOCKET)


def _merge_power_mode(coordinator: Any, mode: Any) -> bool:
    merged = False
    mode_data = _data(coordinator, "/mode")
    if mode_data is not None:
        mode_data["mode"] = mode
        merged = True
    dashboard = _data(coordinator, "/dashboard")
    if dashboard is not None:
        _set_mode(dashboard, "mode", "previous_mode", mode)
        merged = True
    return merged


def _merge_power_socket(coordinator: Any, number: int, pushed: dict[str, Any]) -> bool:
    merged = False
    socket = _socket_of(_data(coordinator, "/dashboard"), number)
    if socket is not None:
        for field in _DASHBOARD_SOCKET:
            if field not in pushed:
                continue
            value = pushed[field]
            if field == "state" and value == "unknown":
                continue
            if field == "mode":
                _set_mode(socket, "mode", "prev_mode", value)
            else:
                socket[field] = value
            merged = True
    socket = _socket_of(_data(coordinator, "/sockets/config"), number)
    if socket is not None:
        for field in _CONFIG_SOCKET:
            if field in pushed:
                socket[field] = pushed[field]
                merged = True
    return merged


def _socket_driven_elsewhere(coordinator: Any, number: Any) -> bool:
    """Whether a socket follows a power detector or a sensor (or is unknown)."""
    if not isinstance(number, int):
        return True
    config = _socket_of(_data(coordinator, "/sockets/config"), number)
    if config is None:
        return True
    return (
        bool(config.get("power_detector_enabled")) or config.get("sensor") is not None
    )


def _in_intervals(intervals: Any, minute: float) -> bool:
    """Whether a minute of the day is in one of the intervals of a schedule."""
    for interval in intervals if isinstance(intervals, list) else []:
        if not isinstance(interval, dict):
            continue
        try:
            start = float(interval["time"])
            end = start + float(interval["duration"])
        except (KeyError, TypeError, ValueError):
            continue
        # An interval may run past midnight
        if start <= minute < end or start <= minute + MINUTES_PER_DAY < end:
            return True
    return False


def derive_power_socket_states(coordinator: Any) -> bool:
    """Compute the state of the sockets, as the ReefBeat app does.

    Returns whether a state changed.
    """
    dashboard = _data(coordinator, "/dashboard")
    now = device_now(coordinator)
    if dashboard is None or now is None or dashboard.get("mode") != "auto":
        return False
    minute = now.hour * 60 + now.minute + now.second / 60
    changed = False
    sockets = dashboard.get("sockets")
    for socket in sockets if isinstance(sockets, list) else []:
        if not isinstance(socket, dict) or not isinstance(socket.get("number"), int):
            continue
        number = socket["number"]
        if _socket_driven_elsewhere(coordinator, number):
            continue
        if socket.get("mode") == "schedule":
            schedule = _data(coordinator, f"/socket/{number}/config/schedule")
            if schedule is None or "intervals" not in schedule:
                continue
            state = "on" if _in_intervals(schedule["intervals"], minute) else "standby"
        else:
            state = "unknown"
        if socket.get("state") != state:
            socket["state"] = state
            changed = True
    return changed


def merge_reef_power(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a pushed state of a ReefControl Power (see the table above)."""
    state = payload.get(WRAPPER) if isinstance(payload, dict) else None
    if not isinstance(state, dict):
        return False
    merged = False

    if "mode" in state:
        merged = _merge_power_mode(coordinator, state["mode"]) or merged

    sockets = state.get("sockets")
    if isinstance(sockets, dict):
        for key, pushed in sockets.items():
            if not isinstance(pushed, dict):
                continue
            try:
                number = int(key)
            except (TypeError, ValueError):
                continue
            merged = _merge_power_socket(coordinator, number, pushed) or merged

    schedules = state.get("schedule")
    if isinstance(schedules, dict):
        for key, pushed in schedules.items():
            if not isinstance(pushed, dict) or "intervals" not in pushed:
                continue
            source = _source(coordinator, f"/socket/{key}/config/schedule")
            if source is None:
                continue
            data = source.get("data")
            if not isinstance(data, dict):
                # Never read yet: the pushed schedule is the whole answer
                data = {}
                source["data"] = data
            data["intervals"] = copy.deepcopy(pushed["intervals"])
            merged = True

    dashboard = _data(coordinator, "/dashboard")
    if dashboard is not None and "connected_device" in state:
        # The ReefControl it is paired with, as /dashboard tells it
        dashboard["connected_device"] = state["connected_device"]
        merged = True
    probe_settings = state.get("device_settings")
    if dashboard is not None and state.get("temperature", 0) is None:
        # The temperature probe removed
        dashboard["temperature"] = None
        merged = True
        if (
            isinstance(probe_settings, dict)
            and probe_settings.get("temperature") is None
        ):
            # Nothing left to read again of it
            probe_settings = None

    if merged:
        # A mode or a schedule changed: the sockets may have changed state
        derive_power_socket_states(coordinator)
    # A probe installed or set up (device_settings, temperature): read again
    unsettled = probe_settings is not None or isinstance(state.get("temperature"), dict)
    unknown = (
        unsettled
        or _unhandled(state, _POWER_STATE_KNOWN | {"device_settings"})
        or any(
            isinstance(pushed, dict) and _unhandled(pushed, _POWER_SOCKET_KNOWN)
            for pushed in (sockets.values() if isinstance(sockets, dict) else ())
        )
    )
    return merged and not unknown


def merge_reef_power_telemetry(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a telemetry of a ReefControl Power (see the table above)."""
    if not isinstance(payload, dict):
        return False
    _set_device_clock(coordinator, payload.get("local_time"))
    merged = False

    if "mode" in payload:
        merged = _merge_power_mode(coordinator, payload["mode"]) or merged

    dashboard = _data(coordinator, "/dashboard")
    if dashboard is not None and "battery_level" in payload:
        dashboard["battery_level"] = payload["battery_level"]
        merged = True

    sockets = payload.get("sockets")
    if isinstance(sockets, dict):
        for key, pushed in sockets.items():
            if not isinstance(pushed, dict):
                continue
            try:
                number = int(key)
            except (TypeError, ValueError):
                continue
            socket = _socket_of(dashboard, number)
            if socket is not None:
                for field in ("consumption", "mode", "prev_mode"):
                    if field in pushed:
                        socket[field] = pushed[field]
                        merged = True
                if "consumption" in pushed and pushed["consumption"] is None:
                    # A socket in setup mode: null pushed, 0 polled
                    socket["consumption"] = 0
            config = _socket_of(_data(coordinator, "/sockets/config"), number)
            if config is not None and "mode" in pushed:
                config["mode"] = pushed["mode"]
                merged = True

    wifi = _data(coordinator, "/wifi")
    if wifi is not None and isinstance(payload.get("wifi_signal"), (int, float)):
        wifi["signal_dBm"] = payload["wifi_signal"]
        merged = True

    # The temperature probe: only into a probe the poll knows (its name and
    # uid are not pushed)
    probe = payload.get("pwr_temperature")
    polled = dashboard.get("temperature") if dashboard is not None else None
    if isinstance(probe, dict) and isinstance(polled, dict):
        for field in ("value", "status", "level"):
            if field in probe:
                polled[field] = probe[field]
                merged = True

    # Every minute: the schedules move on with the clock
    merged = derive_power_socket_states(coordinator) or merged
    return merged


def power_fully_pushed(coordinator: Any) -> bool:
    """Whether every polled value of this ReefControl Power that changes is
    pushed (or computed): its temperature probe, if any, pushed by the
    telemetry; no socket driven by a power detector or a sensor; all of them
    seen polled once."""
    dashboard = _data(coordinator, "/dashboard")
    if dashboard is None:
        return False
    if dashboard.get("temperature") is not None and not isinstance(
        dashboard.get("temperature"), dict
    ):
        return False
    sockets = dashboard.get("sockets")
    if not isinstance(sockets, list) or not sockets:
        return False
    return not any(
        _socket_driven_elsewhere(coordinator, socket.get("number"))
        for socket in sockets
        if isinstance(socket, dict)
    )


# -- ReefDose (reef-dosing) -------------------------------------------------------
#
# Seen on two RSDOSE4 3.0.1 (spy, 2026-10-30). The ReefBeat app reads
# /dashboard, /head/N/settings and /time through the relay; everything else
# comes pushed.
# telemetry (every 60 s, no wrapper), checked 396 / 396 against the polls:
#   mode                          -> /mode.mode
#   heads.N.auto_dosed_today      -> /dashboard.heads.N.auto_dosed_today and
#                                    /head/N/settings.today_auto_dosed_volume,
#                                    both rounded to 0.1 mL (6.909064 -> 6.9)
#   heads.N.manual_dosed_today    -> /dashboard (rounded the same way: only
#                                    seen at 0)
#   heads.N.doses_today, remaining_days, stock_level,
#     recalibration_required, missed_dose -> /dashboard.heads.N
#   heads.N.daily_doses           -> not merged: wrong for a moment (one
#                                    more right after each dose, 25 for 24,
#                                    and doses_today on connection; spy run of
#                                    2026-11-02/03). It only changes with the
#                                    schedule, which reads the device again
#   heads.N.container_volume      -> /head/N/settings.container_volume
#   heads.N.recalibration_required -> /head/N/settings too
#   wifi_signal                   -> /wifi.signal_dBm
#   total_dosed_steps, task_watermark, uptime, metrics... -> nothing polled
# state (specific_attributes):
#   mode                          -> /mode.mode
#   battery_level, time_error     -> /dashboard
#   stock_alert_days, dosing_waiting_period, missed_doses_reminder,
#     calibration_reminder*, daily_metrics_last_compute_time ->
#                                    /device-settings
#   device_settings.shortcut_off_delay -> /device-settings
#   device_settings.bundled_heads -> /dashboard.bundled_heads
#   heads.N.state, is_food_head, shortcut_code -> /dashboard and
#                                    /head/N/settings
#   heads.N.daily_dose            -> /dashboard.heads.N.daily_dose
#   heads.N.last_calibrated, schedule_enabled, show, dc, vps, slm,
#     enable_ratio, food_delay    -> /head/N/settings
#   heads.N.supplement            -> /head/N/settings.supplement (its fields)
#   heads.N.schedule_type, dd, nd, days -> only part of the schedule (never
#                                    its intervals nor its time: an interval
#                                    moved is told by the same fields) and the
#                                    dosing queue follows it: whenever they
#                                    are pushed, the device is read again
#                                    (pushed after a change of the head, and
#                                    on connection)
#   ntp_sync, timezone, attributes... -> nothing polled
#   any other key         -> read again
# /dosing-queue is pushed by nothing. It changes with each dose (a
# dosing-log: read again, READ_ON) and at midnight, when the queue of the new
# day replaces the empty one of the day ending (read again at 00:01,
# READ_AT_MIDNIGHT; seen on the spy runs of 2026-10-30/31). With both, a
# ReefDose is FULLY_PUSHED once its dashboard and queue were polled.

_DOSING_SETTINGS = (
    "stock_alert_days",
    "dosing_waiting_period",
    "missed_doses_reminder",
    "calibration_reminder_days",
    "calibration_reminder_steps",
    "calibration_reminder",
    "daily_metrics_last_compute_time",
)
_DOSING_HEAD_DASHBOARD = ("state", "daily_dose", "is_food_head", "shortcut_code")
_DOSING_HEAD_SETTINGS = (
    "state",
    "is_food_head",
    "shortcut_code",
    "last_calibrated",
    "schedule_enabled",
    "show",
    "dc",
    "vps",
    "slm",
    "enable_ratio",
    "food_delay",
)
_DOSING_TELEMETRY_DASHBOARD = (
    "doses_today",
    "remaining_days",
    "stock_level",
    "recalibration_required",
    "missed_dose",
)


def dosing_fully_pushed(coordinator: Any) -> bool:
    """Whether this ReefDose has been polled once (its dashboard and its
    dosing queue): everything that changes then comes pushed, or by a read
    after a dose and at midnight."""
    queue = _source(coordinator, "/dosing-queue")
    return (
        _data(coordinator, "/dashboard") is not None
        and queue is not None
        and isinstance(queue.get("data"), list)
    )


def _volume(value: Any) -> Any:
    """A dosed volume as the device answers it (0.1 mL)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(value, 1)
    return value


def _head_of(data: Any, key: str) -> dict[str, Any] | None:
    """The head ``key`` of the ``heads`` object of a polled source."""
    heads = data.get("heads") if isinstance(data, dict) else None
    head = heads.get(key) if isinstance(heads, dict) else None
    return head if isinstance(head, dict) else None


def _set_fields(
    holder: dict[str, Any] | None, pushed: dict[str, Any], fields: tuple[str, ...]
) -> bool:
    if holder is None:
        return False
    merged = False
    for name in fields:
        if name in pushed:
            holder[name] = copy.deepcopy(pushed[name])
            merged = True
    return merged


# What a pushed head tells of its schedule (never its intervals nor its time)
_DOSING_SCHEDULE = frozenset({"schedule_type", "dd", "nd", "days"})
_DOSING_STATE_KNOWN = frozenset(
    {
        "mode",
        "battery_level",
        "time_error",
        "device_settings",
        "heads",
        *_DOSING_SETTINGS,
        # Nothing polled matches them
        "ntp_sync",
        "timezone",
        "is_factory_reset",
        "active_shortcut",
        "start_of_schedule_for_next_day",
        "factory_reset_time",
        "food_head_schedule",
        "time_error_unixtime",
        "file_error",
    }
)
_DOSING_DEVICE_SETTINGS_KNOWN = frozenset(
    {"shortcut_off_delay", "bundled_heads", "auto_fill_schedule"}
)
_DOSING_HEAD_KNOWN = frozenset(
    {
        *_DOSING_HEAD_DASHBOARD,
        *_DOSING_HEAD_SETTINGS,
        *_DOSING_SCHEDULE,
        "supplement",
    }
)


def merge_reef_dosing(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a pushed state of a ReefDose (see the table above)."""
    state = payload.get(WRAPPER) if isinstance(payload, dict) else None
    if not isinstance(state, dict):
        return False
    merged = False
    reread = False

    mode_data = _data(coordinator, "/mode")
    if mode_data is not None and "mode" in state:
        mode_data["mode"] = state["mode"]
        merged = True

    dashboard = _data(coordinator, "/dashboard")
    merged = _set_fields(dashboard, state, ("battery_level", "time_error")) or merged

    settings = _data(coordinator, "/device-settings")
    merged = _set_fields(settings, state, _DOSING_SETTINGS) or merged
    device_settings = state.get("device_settings")
    if isinstance(device_settings, dict):
        merged = (
            _set_fields(settings, device_settings, ("shortcut_off_delay",)) or merged
        )
        merged = _set_fields(dashboard, device_settings, ("bundled_heads",)) or merged
        reread = _unhandled(device_settings, _DOSING_DEVICE_SETTINGS_KNOWN)
    reread = reread or _unhandled(state, _DOSING_STATE_KNOWN)

    heads = state.get("heads")
    for key, pushed in heads.items() if isinstance(heads, dict) else ():
        if not isinstance(pushed, dict):
            continue
        dashboard_head = _head_of(dashboard, str(key))
        head_settings = _data(coordinator, f"/head/{key}/settings")
        if any(k in pushed for k in _DOSING_SCHEDULE) or _unhandled(
            pushed, _DOSING_HEAD_KNOWN
        ):
            reread = True
        merged = _set_fields(dashboard_head, pushed, _DOSING_HEAD_DASHBOARD) or merged
        merged = _set_fields(head_settings, pushed, _DOSING_HEAD_SETTINGS) or merged
        supplement = pushed.get("supplement")
        if head_settings is not None and isinstance(supplement, dict):
            polled = head_settings.get("supplement")
            if isinstance(polled, dict):
                polled.update(copy.deepcopy(supplement))
            else:
                head_settings["supplement"] = copy.deepcopy(supplement)
            merged = True

    # A schedule told without its intervals, the dosing queue that follows
    # it, or what is not known: read the device again
    return merged and not reread


def merge_reef_dosing_telemetry(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a telemetry of a ReefDose (see the table above)."""
    if not isinstance(payload, dict):
        return False
    merged = False

    mode_data = _data(coordinator, "/mode")
    if mode_data is not None and "mode" in payload:
        mode_data["mode"] = payload["mode"]
        merged = True

    dashboard = _data(coordinator, "/dashboard")
    heads = payload.get("heads")
    for key, pushed in heads.items() if isinstance(heads, dict) else ():
        if not isinstance(pushed, dict):
            continue
        head = _head_of(dashboard, str(key))
        if head is not None:
            for name in ("auto_dosed_today", "manual_dosed_today"):
                if name in pushed:
                    head[name] = _volume(pushed[name])
                    merged = True
            merged = _set_fields(head, pushed, _DOSING_TELEMETRY_DASHBOARD) or merged
        settings = _data(coordinator, f"/head/{key}/settings")
        if settings is not None:
            if "auto_dosed_today" in pushed:
                settings["today_auto_dosed_volume"] = _volume(
                    pushed["auto_dosed_today"]
                )
                merged = True
            merged = (
                _set_fields(
                    settings, pushed, ("container_volume", "recalibration_required")
                )
                or merged
            )

    wifi = _data(coordinator, "/wifi")
    signal = payload.get("wifi_signal")
    if wifi is not None and isinstance(signal, (int, float)):
        wifi["signal_dBm"] = signal
        merged = True
    return merged


# -- ReefMat (reef-mat) -------------------------------------------------------------
#
# Seen on RSMAT (spy, 2026-10-30, 11 advances, one of them manual).
# /dashboard truncates its lengths to 0.1 (24.1696 -> 24.1, never rounded up):
# the pushed ones are truncated the same way.
# state (specific_attributes), at each advance:
#   is_advancing, last_advance_cause (manual advance) -> /dashboard
#   today_usage, total_usage, remaining_length -> /dashboard (truncated)
#   cumulative_steps, lifetime_steps -> /dashboard
#   internal_ec_average -> the average of the advance: /dashboard tells the
#                          live reading instead, not merged
# state after a setting changed in the app (PUT /configuration):
#   auto_advance          -> /dashboard.auto_advance
#   device_settings.<key> -> /configuration.<key> (a config source: never
#                            read again by the polling), for the keys it has
#   any other key         -> read again
# rolling-log, at each advance:
#   advance_cause         -> /dashboard.last_advance_cause (an advance by the
#                            EC sensor is told by nothing else)
# telemetry (every 60 s):
#   mode                  -> /mode.mode
#   roll_level, days_till_end_of_roll, cumulative_steps, lifetime_steps ->
#                            /dashboard
#   today_usage, daily_average_usage, total_usage, remaining_length ->
#                            /dashboard (truncated)
#   material_name         -> /dashboard.material.name
#   wifi_signal           -> /wifi.signal_dBm
#   setup_date            -> /dashboard tells it with "Z" for "+00:00"
# The EC readings of /dashboard are pushed by nothing: never FULLY_PUSHED.

_MAT_EXACT = (
    "roll_level",
    "days_till_end_of_roll",
    "cumulative_steps",
    "lifetime_steps",
)
_MAT_LENGTHS = ("today_usage", "daily_average_usage", "total_usage", "remaining_length")
_MAT_STATE_KNOWN = frozenset(
    {
        "is_advancing",
        "last_advance_cause",
        "auto_advance",
        "device_settings",
        *_MAT_EXACT,
        *_MAT_LENGTHS,
        # The average of the advance, not the live reading of /dashboard
        "internal_ec_average",
    }
)


def _truncated(value: Any) -> Any:
    """A length as /dashboard tells it (truncated to 0.1)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(math.floor(value * 10 + 1e-6) / 10, 1)
    return value


def _merge_mat_values(dashboard: dict[str, Any] | None, pushed: dict[str, Any]) -> bool:
    if dashboard is None:
        return False
    merged = _set_fields(dashboard, pushed, _MAT_EXACT)
    for name in _MAT_LENGTHS:
        if name in pushed:
            dashboard[name] = _truncated(pushed[name])
            merged = True
    return merged


def merge_reef_mat(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a pushed state or rolling-log of a ReefMat (see the table above)."""
    if not isinstance(payload, dict):
        return False
    dashboard = _data(coordinator, "/dashboard")
    if dashboard is None:
        return False
    if topic.endswith("/rolling-log"):
        cause = payload.get("advance_cause")
        if not isinstance(cause, str):
            return False
        dashboard["last_advance_cause"] = cause
        return True
    state = payload.get(WRAPPER)
    if not isinstance(state, dict):
        return False
    merged = _set_fields(
        dashboard, state, ("is_advancing", "last_advance_cause", "auto_advance")
    )
    merged = _merge_mat_values(dashboard, state) or merged
    unknown = _unhandled(state, _MAT_STATE_KNOWN)
    settings = state.get("device_settings")
    if isinstance(settings, dict):
        configuration = _data(coordinator, "/configuration")
        if configuration is None:
            # Never read: only a read tells the whole configuration
            unknown = True
        else:
            for key, value in settings.items():
                if key in configuration:
                    configuration[key] = copy.deepcopy(value)
                    merged = True
                else:
                    unknown = True
    return merged and not unknown


def merge_reef_mat_telemetry(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a telemetry of a ReefMat (see the table above)."""
    if not isinstance(payload, dict):
        return False
    merged = False
    mode_data = _data(coordinator, "/mode")
    if mode_data is not None and "mode" in payload:
        mode_data["mode"] = payload["mode"]
        merged = True
    dashboard = _data(coordinator, "/dashboard")
    merged = _merge_mat_values(dashboard, payload) or merged
    if dashboard is not None:
        material = dashboard.get("material")
        if isinstance(material, dict) and isinstance(payload.get("material_name"), str):
            material["name"] = payload["material_name"]
            merged = True
        setup = payload.get("setup_date")
        if isinstance(setup, str):
            dashboard["setup_date"] = (
                setup[: -len("+00:00")] + "Z" if setup.endswith("+00:00") else setup
            )
            merged = True
    return _merge_wifi(coordinator, payload) or merged


def _merge_wifi(coordinator: Any, payload: dict[str, Any]) -> bool:
    """The wifi signal of a telemetry into /wifi."""
    wifi = _data(coordinator, "/wifi")
    signal = payload.get("wifi_signal")
    if wifi is None or not isinstance(signal, (int, float)) or isinstance(signal, bool):
        return False
    wifi["signal_dBm"] = signal
    return True


# -- ReefLED (reef-lights) ----------------------------------------------------------
#
# Seen on a ReefLED G1 (spy, 2026-10-30, a morning: night, then blue and fan
# ramping up). Home Assistant reads the channels, the fan and the
# temperature of /manual; /dashboard.manual is the same object.
# telemetry (every 60 s, no state seen yet):
#   intensities.<channel> -> /manual.<channel> and /dashboard.manual.<channel>,
#                            for the channels they have (a G2 has others)
#   fan-speed             -> manual.fan
#   temperature           -> manual.temperature
#   moonphase             -> /dashboard.moon_phase.intensity
#   acclimation           -> /dashboard.acclimation.current_intensity_factor
#   active-program        -> /dashboard.current_program.name
#   mode                  -> /mode.mode and /dashboard.mode
#   wifi_signal           -> /wifi.signal_dBm
#   *_full, *_pwm of /manual: pushed by nothing (unused by Home Assistant)
#   colour and intensity of a G1 (light kelvin_intensity): derived from
#                            white/blue, derived again from the merged ones
#                            (as after a poll); else they stayed those of the
#                            last poll, far from the white/blue shown
#   overheat-reduction-factor, clouds -> nothing polled
# Checked against every poll of the run (differences only while ramping,
# between a telemetry and the next poll).


def _merge_led_manual(manual: Any, payload: dict[str, Any]) -> bool:
    if not isinstance(manual, dict):
        return False
    merged = False
    intensities = payload.get("intensities")
    for channel, value in intensities.items() if isinstance(intensities, dict) else ():
        if channel in manual:
            manual[channel] = value
            merged = True
    for pushed, polled in (("fan-speed", "fan"), ("temperature", "temperature")):
        if pushed in payload and polled in manual:
            manual[polled] = payload[pushed]
            merged = True
    return merged


def merge_reef_lights_telemetry(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a telemetry of a ReefLED (see the table above)."""
    if not isinstance(payload, dict):
        return False
    merged = _merge_led_manual(_data(coordinator, "/manual"), payload)
    api: Any = getattr(coordinator, "my_api", None)
    if merged and getattr(api, "_g1", False):
        # Kelvin and intensity of a G1 follow its white and blue
        api.update_light_wb()
    dashboard = _data(coordinator, "/dashboard")
    if dashboard is not None:
        merged = _merge_led_manual(dashboard.get("manual"), payload) or merged
        for pushed, holder, name in (
            ("moonphase", "moon_phase", "intensity"),
            ("acclimation", "acclimation", "current_intensity_factor"),
            ("active-program", "current_program", "name"),
        ):
            target = dashboard.get(holder)
            if pushed in payload and isinstance(target, dict):
                target[name] = payload[pushed]
                merged = True
        if "mode" in payload:
            dashboard["mode"] = payload["mode"]
            merged = True
    mode_data = _data(coordinator, "/mode")
    if mode_data is not None and "mode" in payload:
        mode_data["mode"] = payload["mode"]
        merged = True
    return _merge_wifi(coordinator, payload) or merged


# -- ReefControl (reef-control) -----------------------------------------------------
#
# Seen on a ReefControl, in setup mode (spy, 2026-11-01), then paired with a
# ReefControl Power and given an ORP, EC, pH, temperature, leak and ATO probe
# (spy, 2026-11-02). Home Assistant reads the mode of /mode and /dashboard,
# the probes and the link of /dashboard, the signal of /wifi.
# telemetry (every 60 s):
#   mode                  -> /mode.mode and /dashboard.mode
#   wifi_signal           -> /wifi.signal_dBm
#   probes.N              -> the probe of /dashboard.probes with its uid: name,
#                            status, value, level, ec, ppt, sg, temp_value,
#                            temp_level, detected, water_level (the values of
#                            the poll); an EC probe has no value: /dashboard
#                            tells the one of its measurement_unit (ppt...)
#   active_shortcut       -> nothing polled
# probe (an event, each time a reading changes): {type, uid, properties}
#   properties.<field>    -> the probe with its uid, as the telemetry; for an
#                            ATO probe, its level is the water_level; for an EC
#                            probe, the value is the one of its unit
# state:
#   mode                  -> as the telemetry
#   cable_connected, connected_device (the ReefControl Power it is paired
#                            with), leak.mode -> /dashboard
#   timezone, is_factory_reset, factory_reset_time, device_setup_date,
#     active_shortcut, attributes -> nothing polled
#   ports.N               -> the port "number": N of /dashboard.ports: mode,
#                            state (spy run of 2026-11-02 21:18); pushed too
#                            when its schedule switches it (23:00:00, "on")
#                            and when the app toggles it (POST
#                            /port/N/toggle, spy run of 2026-11-03); a port
#                            pushed "off" consumes 0 (polled so afterwards,
#                            its last consumption kept until then)
#   ports_settings.N      -> the same port: name, user_config_mode; and the
#                            port of /ports/config: name, user_config_mode,
#                            enabled, power_detector_enabled, sensor
#   a port of another type than polled (installed, removed) -> read again
#                            (its schedule source follows its type); its
#                            schedule (PUT /port/N/schedule) is pushed by
#                            nothing: read again after the command (manager)
#   probes, probes_settings, device_settings -> a probe installed, removed,
#                            set up: the device is read again
# A probe the poll does not know yet (being installed) is not merged: the
# state of its installation reads the device again. Never FULLY_PUSHED: the
# consumption of a port is pushed by nothing (6.8 W polled once its schedule
# switched it on, nothing in the telemetry).

_CONTROL_PROBE_FIELDS = (
    "name",
    "status",
    "value",
    "level",
    "ec",
    "ppt",
    "sg",
    "temp_value",
    "temp_level",
    "detected",
    "water_level",
    "last_calibration_date",
)
_CONTROL_STATE_IGNORED = frozenset(
    {
        "timezone",
        "is_factory_reset",
        "factory_reset_time",
        "device_setup_date",
        "active_shortcut",
    }
)


def _control_probe(coordinator: Any, uid: Any) -> dict[str, Any] | None:
    """The probe of /dashboard with this uid."""
    dashboard = _data(coordinator, "/dashboard")
    probes = dashboard.get("probes") if dashboard is not None else None
    for probe in probes if isinstance(probes, list) else ():
        if isinstance(probe, dict) and uid and probe.get("uid") == uid:
            return probe
    return None


def _merge_control_mode(coordinator: Any, mode: Any) -> bool:
    merged = False
    if isinstance(mode, str):
        for name in ("/mode", "/dashboard"):
            data = _data(coordinator, name)
            if data is not None:
                data["mode"] = mode
                merged = True
    return merged


def merge_reef_control_telemetry(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a telemetry of a ReefControl (see the table above)."""
    if not isinstance(payload, dict):
        return False
    merged = _merge_control_mode(coordinator, payload.get("mode"))
    probes = payload.get("probes")
    for pushed in probes if isinstance(probes, list) else ():
        if not isinstance(pushed, dict):
            continue
        probe = _control_probe(coordinator, pushed.get("uid"))
        if probe is None:
            continue
        for field in _CONTROL_PROBE_FIELDS:
            if field in pushed:
                probe[field] = pushed[field]
                merged = True
        unit = probe.get("measurement_unit")
        if isinstance(unit, str) and unit in pushed:
            probe["value"] = pushed[unit]
    return _merge_wifi(coordinator, payload) or merged


def _merge_control_probe_event(coordinator: Any, payload: Any) -> bool:
    """A probe event: its reading into the probe of /dashboard."""
    if not isinstance(payload, dict):
        return False
    properties = payload.get("properties")
    probe = _control_probe(coordinator, payload.get("uid"))
    if probe is None or not isinstance(properties, dict):
        return False
    pushed = dict(properties)
    if payload.get("type") == "ato" and "level" in pushed:
        pushed["water_level"] = pushed.pop("level")
    unit = pushed.pop("unit", None)
    if isinstance(unit, str) and unit in ("ec", "ppt", "sg") and "value" in pushed:
        pushed[unit] = pushed["value"]
    for field in _CONTROL_PROBE_FIELDS:
        if field in pushed:
            probe[field] = pushed[field]
    return True


def _control_port(data: Any, number: Any) -> dict[str, Any] | None:
    """The port "number" of a list of ports (/dashboard.ports, /ports/config)."""
    ports = data.get("ports") if isinstance(data, dict) else data
    for port in ports if isinstance(ports, list) else ():
        if isinstance(port, dict) and port.get("number") == number:
            return port
    return None


def _merge_control_ports(coordinator: Any, state: dict[str, Any]) -> tuple[bool, bool]:
    """The ports and ports_settings of a state: (merged, read again)."""
    merged = again = False
    dashboard = _data(coordinator, "/dashboard")
    # A bare list: not what _data gives
    source = _source(coordinator, "/ports/config")
    config = source.get("data") if source is not None else None
    for key, to_dashboard, to_config in (
        ("ports", ("mode", "state"), ()),
        (
            "ports_settings",
            ("name", "user_config_mode"),
            ("name", "user_config_mode", "enabled", "power_detector_enabled", "sensor"),
        ),
    ):
        pushed_ports = state.get(key)
        if key not in state:
            continue
        if not isinstance(pushed_ports, list):
            again = True
            continue
        for pushed in pushed_ports:
            if not isinstance(pushed, dict):
                continue
            port = _control_port(dashboard, pushed.get("number"))
            if port is None or pushed.get("type", port.get("type")) != port.get("type"):
                # Installed, removed, or never polled
                again = True
                continue
            for field in to_dashboard:
                if field in pushed:
                    port[field] = pushed[field]
                    merged = True
            if key == "ports" and pushed.get("mode") == "off" and "consumption" in port:
                port["consumption"] = 0
            configured = _control_port(config, pushed.get("number"))
            if configured is None:
                continue
            for field in to_config:
                if field in pushed:
                    configured[field] = pushed[field]
                    merged = True
    return merged, again


def merge_reef_control(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a pushed state, or a probe event, of a ReefControl (see the
    table above)."""
    if topic.endswith("/probe"):
        return _merge_control_probe_event(coordinator, payload)
    state = payload.get(WRAPPER) if isinstance(payload, dict) else None
    if not isinstance(state, dict):
        # The attributes pushed on connection: nothing polled
        return isinstance(payload, dict) and set(payload) == {"attributes"}
    merged = _merge_control_mode(coordinator, state.get("mode"))
    dashboard = _data(coordinator, "/dashboard")
    if dashboard is not None:
        for field in ("cable_connected", "connected_device"):
            if field in state:
                dashboard[field] = state[field]
                merged = True
        leak = state.get("leak")
        if isinstance(leak, dict) and isinstance(dashboard.get("leak"), dict):
            dashboard["leak"].update(leak)
            merged = True
    ports_merged, again = _merge_control_ports(coordinator, state)
    merged = merged or ports_merged
    known = _CONTROL_STATE_IGNORED | {
        "mode",
        "cable_connected",
        "connected_device",
        "ports",
        "ports_settings",
    }
    if dashboard is not None and isinstance(dashboard.get("leak"), dict):
        known = known | {"leak"}
    unknown = again or _unhandled(state, known)
    return (merged or not set(state) - _CONTROL_STATE_IGNORED) and not unknown


# -- ReefRun (reef-run) -------------------------------------------------------------
#
# Seen on a RSRUN 2.0.3 (a return pump and an RSK 900 skimmer, spy runs of
# 2026-10-30 to 2026-11-03), checked against every poll (2683 telemetry, 46
# states: differences only between a push and the next poll). Its pumps are
# "1", "2" in the pushes, pump_1, pump_2 in the polls.
# telemetry (every 60 s):
#   mode                  -> /mode.mode and /dashboard.mode
#   pumps.N.state, missing_pump, intensity, pulse, temperature ->
#                            /dashboard.pump_N (intensity: the real one, 35 for
#                            a skimmer driven by its EC sensor); a pump in
#                            calibration is left to the state telling its end
#   wifi_signal           -> /wifi.signal_dBm
#   pumps.N.start, baud_rate, rr_driver_data, the EC readings (maxavg_ec_*,
#     one_min_avg_cup, ec_skimmer_intensity), metrics -> nothing polled
# state (specific_attributes), pushed at each change of a pump (full cup,
# missing pump, schedule switched...) and of the settings:
#   pumps.N.name, type, model, state, reconnect_pump, sensor_controlled,
#     missing_pump, missing_sensor, schedule_enabled -> /dashboard.pump_N
#   pumps.N.name, type, model, sensor_controlled, schedule_enabled, schedule
#                         -> /pump/settings.pump_N
#   pumps.N.intensity     -> not merged: the one of its schedule (100), not
#                            the real one of /dashboard (35)
#   pumps.N.model_address -> nothing polled
#   a pump leaving "calibration" -> read again: the dates of /calibration are
#                            pushed by nothing
#   device_settings.linked, synced -> /dashboard and /pump/settings;
#     restore_settings -> /dashboard; overskimming, fullcup_enabled ->
#     /pump/settings; calibration (step counts), sync_subscription -> nothing
#     polled
#   mode                  -> /mode and /dashboard
#   ec_sensor_connected, battery_level, time_error -> /dashboard
#   shortcuts.pump_N      -> /pump/shortcuts.pump_N
#   attributes (on connection, with everything above) -> merged, then read
#                            again: what changed while it was away
#   initial, is_factory_reset, feeding_type, active_shortcut, timezone ->
#                            nothing polled
#   any other key         -> read again
# Never FULLY_PUSHED: is_internet_connected of /dashboard is pushed by
# nothing.

_RUN_TELEMETRY_PUMP = ("state", "missing_pump", "intensity", "pulse", "temperature")
_RUN_STATE_PUMP_DASHBOARD = (
    "name",
    "type",
    "model",
    "state",
    "reconnect_pump",
    "sensor_controlled",
    "missing_pump",
    "missing_sensor",
    "schedule_enabled",
)
_RUN_STATE_PUMP_SETTINGS = (
    "name",
    "type",
    "model",
    "sensor_controlled",
    "schedule_enabled",
    "schedule",
)
_RUN_STATE_PUMP_KNOWN = frozenset(
    _RUN_STATE_PUMP_DASHBOARD
    + _RUN_STATE_PUMP_SETTINGS
    + ("intensity", "model_address")
)
_RUN_SETTINGS_DASHBOARD = ("linked", "synced", "restore_settings")
_RUN_SETTINGS_PUMP = ("linked", "synced", "overskimming", "fullcup_enabled")
_RUN_SETTINGS_KNOWN = frozenset(
    _RUN_SETTINGS_DASHBOARD + _RUN_SETTINGS_PUMP + ("calibration", "sync_subscription")
)
_RUN_STATE_DASHBOARD = ("ec_sensor_connected", "battery_level", "time_error")
_RUN_STATE_IGNORED = frozenset(
    {"initial", "is_factory_reset", "feeding_type", "active_shortcut", "timezone"}
)
_RUN_STATE_KNOWN = _RUN_STATE_IGNORED | {
    "mode",
    "pumps",
    "device_settings",
    "shortcuts",
    *_RUN_STATE_DASHBOARD,
}
_RUN_CALIBRATION = "calibration"


def _run_pump(data: dict[str, Any] | None, number: Any) -> dict[str, Any] | None:
    """pump_N of a polled source of a ReefRun."""
    pump = data.get(f"pump_{number}") if data is not None else None
    return pump if isinstance(pump, dict) else None


def _merge_run_mode(coordinator: Any, mode: Any) -> bool:
    merged = False
    if isinstance(mode, str):
        for name in ("/mode", "/dashboard"):
            data = _data(coordinator, name)
            if data is not None:
                data["mode"] = mode
                merged = True
    return merged


def merge_reef_run_telemetry(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a telemetry of a ReefRun (see the table above)."""
    if not isinstance(payload, dict):
        return False
    merged = _merge_run_mode(coordinator, payload.get("mode"))
    dashboard = _data(coordinator, "/dashboard")
    pumps = payload.get("pumps")
    for number, pushed in pumps.items() if isinstance(pumps, dict) else ():
        pump = _run_pump(dashboard, number)
        if pump is None or not isinstance(pushed, dict):
            continue
        fields = _RUN_TELEMETRY_PUMP
        if pump.get("state") == _RUN_CALIBRATION:
            # Its end reads the device again (the state pushed then)
            fields = tuple(f for f in fields if f != "state")
        merged = _set_fields(pump, pushed, fields) or merged
    return _merge_wifi(coordinator, payload) or merged


def _merge_run_pumps(coordinator: Any, pumps: Any) -> tuple[bool, bool]:
    """The pumps of a state: (merged, read again)."""
    if not isinstance(pumps, dict):
        return False, True
    dashboard = _data(coordinator, "/dashboard")
    settings = _data(coordinator, "/pump/settings")
    merged = again = False
    for number, pushed in pumps.items():
        pump = _run_pump(dashboard, number)
        if pump is None or not isinstance(pushed, dict):
            again = True
            continue
        if (
            pump.get("state") == _RUN_CALIBRATION
            and pushed.get("state", _RUN_CALIBRATION) != _RUN_CALIBRATION
        ):
            # Calibrated: its new dates are in /calibration
            again = True
        merged = _set_fields(pump, pushed, _RUN_STATE_PUMP_DASHBOARD) or merged
        configured = _run_pump(settings, number)
        if configured is None:
            again = True
        else:
            merged = _set_fields(configured, pushed, _RUN_STATE_PUMP_SETTINGS) or merged
        again = again or _unhandled(pushed, _RUN_STATE_PUMP_KNOWN)
    return merged, again


def _merge_run_settings(coordinator: Any, settings: Any) -> tuple[bool, bool]:
    """device_settings of a state: (merged, read again)."""
    if not isinstance(settings, dict):
        return False, True
    dashboard = _data(coordinator, "/dashboard")
    pump_settings = _data(coordinator, "/pump/settings")
    if dashboard is None or pump_settings is None:
        return False, True
    merged = _set_fields(dashboard, settings, _RUN_SETTINGS_DASHBOARD)
    merged = _set_fields(pump_settings, settings, _RUN_SETTINGS_PUMP) or merged
    return merged, _unhandled(settings, _RUN_SETTINGS_KNOWN)


def _merge_run_shortcuts(coordinator: Any, shortcuts: Any) -> tuple[bool, bool]:
    """shortcuts of a state: (merged, read again)."""
    polled = _data(coordinator, "/pump/shortcuts")
    if not isinstance(shortcuts, dict) or polled is None:
        return False, True
    merged = again = False
    for key, pushed in shortcuts.items():
        if isinstance(polled.get(key), dict) and isinstance(pushed, dict):
            polled[key] = copy.deepcopy(pushed)
            merged = True
        else:
            again = True
    return merged, again


def merge_reef_run(coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a pushed state of a ReefRun (see the table above)."""
    if not isinstance(payload, dict):
        return False
    state = payload.get(WRAPPER)
    if not isinstance(state, dict):
        return False
    merged = _merge_run_mode(coordinator, state.get("mode"))
    dashboard = _data(coordinator, "/dashboard")
    merged = _set_fields(dashboard, state, _RUN_STATE_DASHBOARD) or merged
    again = _unhandled(state, _RUN_STATE_KNOWN) or "attributes" in payload
    for key, merge in (
        ("pumps", _merge_run_pumps),
        ("device_settings", _merge_run_settings),
        ("shortcuts", _merge_run_shortcuts),
    ):
        if key in state:
            part_merged, part_again = merge(coordinator, state[key])
            merged = merged or part_merged
            again = again or part_again
    return merged and not again
