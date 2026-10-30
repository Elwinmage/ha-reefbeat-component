"""Mergers of pushed messages into the polled sources, per device family.

A device in Poseidon mode pushes a ``state`` when something changes (a socket
switched, a schedule written, the device turned off) and a ``telemetry``
every 60 s (modes, consumptions, signal). For the shadow and poseidon
strategies, a merger writes what they carry into the sources its coordinator
polls, so the entities follow at once instead of at the next poll. Each one
is written from spy files (``response`` of the HTTP records against the
pushed values): only what was seen to match is merged.

A merger returns whether it merged something. Nothing known in the message
returns False: the poseidon strategy then reads the device again (for a
``state``; a ``telemetry`` triggers nothing).

A family whose pushed messages cover every polled value that changes says so
for a device (``FULLY_PUSHED``): the poseidon strategy then only polls it
now and then, as a safety net.
"""

from __future__ import annotations

import copy
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
    return merged


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
