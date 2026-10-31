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
# telemetry (every 60 s, no wrapper):
#   mode                 -> as in the state
#   battery_level        -> /dashboard.battery_level
#   sockets.N.consumption, mode, prev_mode -> the socket N of /dashboard
#                           (mode also in /sockets/config)
#   wifi_signal          -> /wifi.signal_dBm
#   local_time           -> the clock of the device (see below)
#   pwr_temperature      -> probably /dashboard.temperature, not seen with a
#                           probe yet: not merged (a device with a probe is
#                           not FULLY_PUSHED)
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
        # Nothing polled matches them
        "feed_schedule",
        "timezone",
        "ntp_sync",
        "active_shortcut",
        "device_setup_date",
        "factory_reset_time",
        "feeding_type",
        "temperature",
        "connected_device",
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

    if merged:
        # A mode or a schedule changed: the sockets may have changed state
        derive_power_socket_states(coordinator)
    unknown = _unhandled(state, _POWER_STATE_KNOWN) or any(
        isinstance(pushed, dict) and _unhandled(pushed, _POWER_SOCKET_KNOWN)
        for pushed in (sockets.values() if isinstance(sockets, dict) else ())
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
            config = _socket_of(_data(coordinator, "/sockets/config"), number)
            if config is not None and "mode" in pushed:
                config["mode"] = pushed["mode"]
                merged = True

    wifi = _data(coordinator, "/wifi")
    if wifi is not None and isinstance(payload.get("wifi_signal"), (int, float)):
        wifi["signal_dBm"] = payload["wifi_signal"]
        merged = True

    # Every minute: the schedules move on with the clock
    merged = derive_power_socket_states(coordinator) or merged
    return merged


def power_fully_pushed(coordinator: Any) -> bool:
    """Whether every polled value of this ReefControl Power that changes is
    pushed (or computed): no temperature probe, no socket driven by a power
    detector or a sensor, all of them seen polled once."""
    dashboard = _data(coordinator, "/dashboard")
    if dashboard is None or dashboard.get("temperature") is not None:
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
#   heads.N.doses_today, daily_doses, remaining_days, stock_level,
#     recalibration_required, missed_dose -> /dashboard.heads.N
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
    "daily_doses",
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
