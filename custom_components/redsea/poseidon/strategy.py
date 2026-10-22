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
  nothing).

No family has a merger yet: they are written from the spy files.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util

# Topic suffix of the states a device pushes
STATE_SUFFIX = "/state"


def is_state_topic(topic: str) -> bool:
    return topic.startswith("device/") and topic.endswith(STATE_SUFFIX)


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


def compare(pushed: Any, leaves: list[tuple[str, str, Any]]) -> list[dict[str, Any]]:
    """Each pushed value against the polled values at the same path.

    A pushed path matches a polled one when it is a suffix of it (a state
    carries a subtree, the poll the whole source). The closest matches (the
    shortest polled paths) are kept.
    """
    results: list[dict[str, Any]] = []
    for path, value in flatten(pushed):
        if not path:
            continue
        candidates = [leaf for leaf in leaves if _suffix_match(leaf[1], path)]
        if candidates:
            shortest = min(len(leaf[1]) for leaf in candidates)
            candidates = [leaf for leaf in candidates if len(leaf[1]) == shortest]
        matches = [
            {"source": source, "path": polled_path, "polled": polled}
            for source, polled_path, polled in candidates
        ]
        if not matches:
            verdict = "unknown"
        elif any(m["polled"] == value for m in matches):
            verdict = "same"
        else:
            verdict = "differs"
        results.append(
            {"path": path, "pushed": value, "verdict": verdict, "matches": matches}
        )
    return results


# Device type (cloud namespace) -> merger of its pushed states into the
# sources of its coordinator: (coordinator, topic, payload) -> merged. None
# yet: they are written per family from the spy files.
Merger = Callable[[Any, str, Any], bool]
MERGERS: dict[str, Merger] = {}


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
    ) -> None:
        """Keep a pushed state; ``write`` gets its comparison."""
        self.pending.setdefault(hwid, []).append(
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
