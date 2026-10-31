"""Strategies of the devices in Poseidon mode, chosen per device.

- ``spy``: polling unchanged. Every frame the device exchanges with Red Sea
  (both directions, decrypted), every HTTP request the integration sends it,
  and the comparison of each pushed ``state`` with the next poll go to one
  file, ``spy.jsonl``, with the same clock: what the device pushes on its own
  can be told from what a request triggered. The polling of a device in spy
  mode can be paused, for a baseline with no request at all.
- ``shadow``: polling unchanged, and each pushed ``state`` merged into the
  sources of its device when its family has a merger (``MERGERS``). Every
  comparison with the next poll goes to ``shadow.jsonl``, saying whether the
  state was merged: a merger is right when nothing differs anymore.
- ``poseidon``: polling slowed down (every N minutes), pushed states as the
  main source. A family without a merger yet gets its device refreshed on
  every pushed ``state`` instead (``telemetry``, every 60 s, triggers
  nothing). A device whose pushed messages cover every polled value that
  changes (``FULLY_PUSHED``) is only polled now and then, as a safety net
  (every M minutes).

The ``telemetry`` a device pushes every 60 s is merged too when its family
has a telemetry merger (``TELEMETRY_MERGERS``), and compared like a state:
only the last one waits for the next poll.

The mergers are written per family from the spy files (mergers.py).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .mergers import (
    dosing_fully_pushed,
    merge_reef_dosing,
    merge_reef_dosing_telemetry,
    merge_reef_lights_telemetry,
    merge_reef_mat,
    merge_reef_mat_telemetry,
    merge_reef_power,
    merge_reef_power_telemetry,
    power_fully_pushed,
)

# Topic suffix of the states a device pushes
STATE_SUFFIX = "/state"
# Topic suffix of the telemetry a device pushes every 60 s
TELEMETRY_SUFFIX = "/telemetry"


def is_state_topic(topic: str) -> bool:
    return topic.startswith("device/") and topic.endswith(STATE_SUFFIX)


def is_telemetry_topic(topic: str) -> bool:
    return topic.startswith("device/") and topic.endswith(TELEMETRY_SUFFIX)


def flatten(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Leaves of a JSON value as (dotted path, value); list items by index."""
    if isinstance(value, dict):
        if not value and prefix:
            yield prefix, value
        for key, item in value.items():
            yield from flatten(item, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        if not value and prefix:
            yield prefix, value
        for index, item in enumerate(value):
            yield from flatten(item, f"{prefix}.{index}" if prefix else str(index))
    else:
        yield prefix, value


def polled_leaves(coordinator: Any) -> list[tuple[str, str, Any]]:
    """Every value the last polls read: (source, path, value)."""
    api = getattr(coordinator, "my_api", None)
    sources = getattr(api, "data", {}).get("sources") if api is not None else None
    leaves: list[tuple[str, str, Any]] = []
    for source in sources if isinstance(sources, list) else []:
        if not isinstance(source, dict):
            continue
        name = str(source.get("name", ""))
        for path, value in flatten(source.get("data")):
            leaves.append((name, path, value))
    return leaves


def _suffix_match(polled_path: str, pushed_path: str) -> bool:
    """Whether a polled path ends with the pushed one, on path boundaries."""
    return polled_path == pushed_path or polled_path.endswith("." + pushed_path)


# Keys a pushed state wraps its values in, absent from the polled sources:
# {"specific_attributes": {"sockets": ...}} is "sockets..." of /dashboard.
STATE_WRAPPERS: tuple[str, ...] = ("specific_attributes",)


def _unwrap(path: str) -> str:
    """The pushed path without the wrapper of the state."""
    for wrapper in STATE_WRAPPERS:
        if path == wrapper:
            return ""
        if path.startswith(wrapper + "."):
            return path[len(wrapper) + 1 :]
    return path


def _candidates(
    path: str, leaves: list[tuple[str, str, Any]]
) -> tuple[list[tuple[str, str, Any]], str]:
    """The polled values matching a pushed path, and the suffix that did.

    The whole path first; then, when nothing matches, the path without its
    first segments, down to two segments ("sockets.0.mode" is "0.mode" of a
    source holding the list of sockets). The closest matches (the shortest
    polled paths) are kept.
    """
    parts = path.split(".")
    for start in range(max(1, len(parts) - 1)):
        suffix = ".".join(parts[start:])
        found = [leaf for leaf in leaves if _suffix_match(leaf[1], suffix)]
        if found:
            shortest = min(len(leaf[1]) for leaf in found)
            return [leaf for leaf in found if len(leaf[1]) == shortest], suffix
    return [], path


def compare(pushed: Any, leaves: list[tuple[str, str, Any]]) -> list[dict[str, Any]]:
    """Each pushed value against the polled values at the same path.

    A pushed path matches a polled one when it is a suffix of it (a state
    carries a subtree, the poll the whole source), once the wrapper of the
    state is dropped (``STATE_WRAPPERS``). A match found on a shorter suffix
    tells it (``via``).
    """
    results: list[dict[str, Any]] = []
    for full_path, value in flatten(pushed):
        path = _unwrap(full_path)
        if not path:
            continue
        candidates, via = _candidates(path, leaves)
        matches = [
            {"source": source, "path": polled_path, "polled": polled}
            for source, polled_path, polled in candidates
        ]
        if matches and via != path:
            for match in matches:
                match["via"] = via
        if not matches:
            verdict = "unknown"
        elif any(m["polled"] == value for m in matches):
            verdict = "same"
        else:
            verdict = "differs"
        results.append(
            {
                "path": full_path,
                "pushed": value,
                "verdict": verdict,
                "matches": matches,
            }
        )
    return results


# Device type (cloud namespace) -> merger of its pushed states into the
# sources of its coordinator: (coordinator, topic, payload) -> merged. They
# are written per family from the spy files (mergers.py).
Merger = Callable[[Any, str, Any], bool]
MERGERS: dict[str, Merger] = {
    "reef-power": merge_reef_power,
    "reef-dosing": merge_reef_dosing,
    "reef-mat": merge_reef_mat,
}
# Device type -> merger of its telemetry
TELEMETRY_MERGERS: dict[str, Merger] = {
    "reef-power": merge_reef_power_telemetry,
    "reef-dosing": merge_reef_dosing_telemetry,
    "reef-mat": merge_reef_mat_telemetry,
    "reef-lights": merge_reef_lights_telemetry,
}
# Device type -> topic suffixes of the events after which the poseidon
# strategy reads the device again: what changed is pushed by nothing (a
# dose changes the dosing queue)
READ_ON: dict[str, frozenset[str]] = {
    "reef-dosing": frozenset({"dosing-log"}),
}
# Device type -> whether a device of it has every changing value pushed
FULLY_PUSHED: dict[str, Callable[[Any], bool]] = {
    "reef-power": power_fully_pushed,
    "reef-dosing": dosing_fully_pushed,
}
# Device types the poseidon strategy reads again just after midnight: what
# changes then is pushed by nothing (the dosing queue of the new day)
READ_AT_MIDNIGHT: frozenset[str] = frozenset({"reef-dosing"})


# Device type -> topic suffixes of the events merged like a state (with the
# merger of the family)
MERGES_ON: dict[str, frozenset[str]] = {
    "reef-mat": frozenset({"rolling-log"}),
}


def merges_on(device_type: str, topic: str) -> bool:
    """Whether a pushed event of this topic is merged like a state."""
    return topic.rsplit("/", 1)[-1] in MERGES_ON.get(device_type, frozenset())


def reads_at_midnight(device_type: str) -> bool:
    """Whether the device is read again just after midnight."""
    return device_type in READ_AT_MIDNIGHT


def reads_on(device_type: str, topic: str) -> bool:
    """Whether a pushed event of this topic calls for a read of the device."""
    return topic.rsplit("/", 1)[-1] in READ_ON.get(device_type, frozenset())


def merge_telemetry(
    device_type: str, coordinator: Any, topic: str, payload: Any
) -> bool:
    """Merge a pushed telemetry into the sources; whether the family knows how."""
    merger = TELEMETRY_MERGERS.get(device_type)
    if merger is None:
        return False
    return merger(coordinator, topic, payload)


def fully_pushed(device_type: str, coordinator: Any) -> bool:
    """Whether the device needs polling only as a safety net."""
    check = FULLY_PUSHED.get(device_type)
    if check is None or device_type not in TELEMETRY_MERGERS:
        return False
    try:
        return bool(check(coordinator))
    except Exception:
        return False


def merge_state(device_type: str, coordinator: Any, topic: str, payload: Any) -> bool:
    """Merge a pushed state into the sources; whether the family knows how."""
    merger = MERGERS.get(device_type)
    if merger is None:
        return False
    return merger(coordinator, topic, payload)


@dataclass
class PendingState:
    topic: str
    payload: Any
    received: str
    merged: bool
    write: Callable[[dict[str, Any]], None]


@dataclass
class Comparisons:
    """Pushed states waiting for the next poll of their device."""

    pending: dict[str, list[PendingState]] = field(default_factory=dict)

    def add(
        self,
        hwid: str,
        topic: str,
        payload: Any,
        write: Callable[[dict[str, Any]], None],
        merged: bool = False,
        latest_only: bool = False,
    ) -> None:
        """Keep a pushed message; ``write`` gets its comparison.

        ``latest_only``: only the last message of this topic waits (a
        telemetry every 60 s would pile up while the polling is paused).
        """
        pending = self.pending.setdefault(hwid, [])
        if latest_only:
            pending[:] = [state for state in pending if state.topic != topic]
        pending.append(
            PendingState(topic, payload, dt_util.now().isoformat(), merged, write)
        )

    def drop(self, hwid: str) -> None:
        self.pending.pop(hwid, None)

    def polled(self, hwid: str, coordinator: Any) -> None:
        """The device was polled: compare and report what it pushed since."""
        states = self.pending.pop(hwid, [])
        if not states:
            return
        leaves = polled_leaves(coordinator)
        polled_at = dt_util.now().isoformat()
        for state in states:
            results = compare(state.payload, leaves)
            state.write(
                {
                    "ts": polled_at,
                    "kind": "compare",
                    "hwid": hwid,
                    "topic": state.topic,
                    "received": state.received,
                    "merged": state.merged,
                    "summary": {
                        verdict: sum(1 for r in results if r["verdict"] == verdict)
                        for verdict in ("same", "differs", "unknown")
                    },
                    "values": results,
                }
            )


class PollControl:
    """Changes the polling interval of some coordinators, and gives it back.

    ``None`` as interval pauses the polling (no refresh scheduled anymore).
    """

    def __init__(self) -> None:
        # hwid -> (coordinator, its own interval)
        self._original: dict[str, tuple[Any, timedelta | None]] = {}

    def set(self, hwid: str, coordinator: Any, interval: timedelta | None) -> None:
        if hwid not in self._original or self._original[hwid][0] is not coordinator:
            self._original[hwid] = (coordinator, coordinator.update_interval)
        coordinator.update_interval = interval
        if interval is None:
            # A refresh already scheduled would still run once: cancel it
            unschedule = getattr(coordinator, "_async_unsub_refresh", None)
            if callable(unschedule):
                unschedule()

    def interval(self, hwid: str) -> timedelta | None:
        """The interval set on a controlled device's coordinator."""
        saved = self._original.get(hwid)
        return saved[0].update_interval if saved is not None else None

    def restore(self, hwid: str) -> Any | None:
        """Give a device its own interval back; its coordinator, if it had
        been changed (a paused one needs a refresh to be scheduled again)."""
        saved = self._original.pop(hwid, None)
        if saved is None:
            return None
        coordinator, interval = saved
        coordinator.update_interval = interval
        return coordinator

    def restore_all(self) -> list[Any]:
        return [c for c in (self.restore(h) for h in list(self._original)) if c]

    @property
    def controlled(self) -> set[str]:
        return set(self._original)
